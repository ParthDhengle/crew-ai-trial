# src/crew.py (updated)
import json
import os
import traceback
from typing import List, Dict, Any
from datetime import date
import json5
import platform
import re
from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from litellm.exceptions import RateLimitError, APIError
from tools.file_manager_tool import FileManagerTool
from tools.operations_tool import OperationsTool
from tools.rag_tool import RagTool
from tools.long_term_rag_tool import LongTermRagTool
from chat_history import ChatHistory 
from common_functions.Find_project_root import find_project_root
from memory_manager import MemoryManager 
from operations_store import queue_operation_local, update_operation_local, get_operation_local, publish_event;
import asyncio
from firebase_client import add_summary  # For storing summaries
from datetime import datetime

PROJECT_ROOT = find_project_root()
MEMORY_DIR = os.path.join(PROJECT_ROOT, "knowledge", "memory")
@CrewBase
class AiAgent:
    agents: List[Agent]
    tasks: List[Task]
    def __init__(self):
        self.classifier_llm = LLM(model="groq/llama-3.3-70b-versatile", api_key=os.getenv("GROQ_API_KEY1"))
        self.classifier_fallback1_llm = LLM(model="gemini/gemini-1.5-flash-latest", api_key=os.getenv("GEMINI_API_KEY2"))
        self.classifier_fallback2_llm = LLM(model="openrouter/deepseek/deepseek-chat-v3.1:free", api_key=os.getenv("OPENROUTER_API_KEY2"))
       
        self.synthesizer_llm = LLM(model="openrouter/openai/gpt-oss-120b:free", api_key=os.getenv("OPENROUTER_API_KEY4"))
        self.synthesizer_fallback1_llm = LLM(model="openrouter/deepseek/deepseek-chat-v3.1:free", api_key=os.getenv("OPENROUTER_API_KEY2"))
        self.synthesizer_fallback2_llm = LLM(model="gemini/gemini-1.5-flash-latest", api_key=os.getenv("GEMINI_API_KEY4"))
       
        self.summarizer_llm = LLM(model="cohere/command-r-plus", api_key=os.getenv("COHERE_API_KEY")) 
        self.summarizer_fallback1_llm = LLM(model="openrouter/openai/gpt-oss-20b:free", api_key=os.getenv("OPENROUTER_API_KEY1"))
        self.summarizer_fallback2_llm = LLM(model="gemini/gemini-1.5-flash-latest", api_key=os.getenv("GEMINI_API_KEY1"))
        self.memory_manager = MemoryManager()
        super().__init__()

    @agent
    def classifier(self) -> Agent:
        return Agent(config=self.agents_config['classifier'], llm=self.classifier_llm, verbose=True)
    
    @agent
    def synthesizer(self) -> Agent:
        return Agent(config=self.agents_config['synthesizer'], llm=self.synthesizer_llm, verbose=True)
    
    @agent
    def summarizer(self) -> Agent:
        return Agent(config=self.agents_config['summarizer'], llm=self.summarizer_llm, verbose=True)
    
    @task
    def classify_query(self) -> Task:
        return Task(config=self.tasks_config['classify_query'])
    
    @task
    def synthesize_response(self) -> Task:
        return Task(config=self.tasks_config['synthesize_response'])
    
    @task
    def summarize_history(self) -> Task:
        return Task(config=self.tasks_config['summarize_history'])
    
    def _execute_task_with_fallbacks(self, agent, task, fallbacks):
        try:
            return agent.execute_task(task)
        except (RateLimitError, APIError) as e:
            if isinstance(e, APIError) and getattr(e, 'status_code', None) != 429:
                raise e
            if not fallbacks:
                print(f"Exhausted fallbacks for {agent.llm.model}. Returning error message.")
                return "Error: LLM request failed. Please try again later."
            print(f"Rate limit or API error with {agent.llm.model}. Switching to fallback.")
            agent.llm = fallbacks[0]
            return self._execute_task_with_fallbacks(agent, task, fallbacks[1:])

    def _process_file(self, file_path: str) -> str:
        if not file_path or not os.path.exists(file_path):
            return ""
        ext = os.path.splitext(file_path)[1].lower()
        file_tool = FileManagerTool()
        if ext in ['.txt', '.doc', '.ppt']:
            content = file_tool._run(file_path)
        elif ext == '.pdf':
            try:
                content = file_tool._run(file_path) 
            except:
                content = f"PDF file detected: {file_path} (full extraction pending lib integration)."
        else:
            return f"Unsupported file type: {ext}."
        
        if len(content) > 2000:
            from langchain_community.vectorstores import FAISS
            from langchain_huggingface import HuggingFaceEmbeddings
            embedder = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            chunks = [content[i:i+500] for i in range(0, len(content), 400)]  # Overlap for better RAG
            vs = FAISS.from_texts(chunks, embedder)
            results = vs.similarity_search("relevant to query", k=5)
            return "\n".join([doc.page_content for doc in results])
        return content

    async def run_workflow(self, user_query: str, file_path: str = None, session_id: str = None, uid: str = None) :
        user_query = user_query.strip()
        if not user_query:
            return "No query provided."
       
        history = ChatHistory.load_history(session_id)
        user_profile = self.memory_manager.get_user_profile() 
        file_content = self._process_file(file_path)
       
        file_tool = FileManagerTool()
        ops_path = os.path.join(PROJECT_ROOT, 'knowledge', 'operations.json')
        available_operations_raw = file_tool._run(ops_path)
        json_match = re.search(r'\{.*\}', available_operations_raw, re.DOTALL)
        available_operations_content = json_match.group(0) if json_match else "{}"
        try:
            available_operations = json.loads(available_operations_content.strip()).get("operations", [])
        except json.JSONDecodeError:
            available_operations = []
       
        available_ops_info = "\n".join([f"{op['name']}: {op['description']} | Required params: {', '.join(op['required_parameters'])} | Optional params: {', '.join(op.get('optional_parameters', []))}" for op in available_operations])
        
        full_history = json.dumps(history[-8:])
        if len(full_history) > 2000: 
            history_summary = ChatHistory.summarize(history[-8:])
            full_history = f"Summary: {history_summary}"
        
        relevant_facts = self.memory_manager.retrieve_long_term(user_query)
        
        os_info = f"{platform.system()} {platform.release()}"
        inputs = {
            'user_query': user_query,
            'file_content': file_content,
            'full_history': full_history,
            'available_ops_info': available_ops_info,
            'user_profile': json.dumps(user_profile),
            'relevant_facts': relevant_facts,
            'os_info': os_info
        }
        
        classify_task = self.classify_query()
        classify_task.description = classify_task.description.format(**inputs)
        classify_agent = self.classifier()
        classification_raw = self._execute_task_with_fallbacks(
            classify_agent, classify_task, [self.classifier_fallback1_llm, self.classifier_fallback2_llm]
        )
       
        def parse_json_with_retry(raw: str, retries: int = 1) -> Dict:
            for _ in range(retries):
                cleaned = re.sub(r'```json|```', '', raw).strip()
                try:
                    return json5.loads(cleaned)
                except:
                    pass
            return {'mode': 'direct', 'display_response': f"Classification failed: {raw[:100]}... Please rephrase."}
       
        classification = parse_json_with_retry(classification_raw)
       
        mode = classification.get('mode', 'direct')
        if mode == 'direct':
            final_response = classification.get('display_response', 'No response generated.')
        else: 
            operations = classification.get('operations', [])
            if not isinstance(operations, list) or not all(isinstance(op, dict) and 'name' in op for op in operations):
                final_response = "Invalid operations plan generated. Please rephrase your query."
                mode = 'direct' 
            else:
                user_summarized_requirements = classification.get('user_summarized_query', 'User intent unclear.')
                if user_summarized_requirements:
                    # Store in summaries.json or Firebase
                    summary_data = {"date": datetime.now().isoformat().split('T')[0], "summary": user_summarized_requirements}
                    add_summary(summary_data['date'], summary_data['summary'])
                
                from operations_store import queue_operation_local
                for op in operations:
                    op_id = await queue_operation_local(op['name'], op.get('parameters', {}), session_id)
                    op['op_id'] = op_id
                
                await publish_event(session_id, {
                    "type": "agentic_mode_activated", 
                    "message": "Nova agentic mode activated",
                    "operations_count": len(operations)
                })
            
                op_results = await self.perform_operations_with_realtime_updates(operations, session_id, uid)
               
                synth_task = self.synthesize_response()
                synth_task.description = synth_task.description.format(
                    user_summarized_requirements=user_summarized_requirements,
                    op_results=op_results
                )
                synth_agent = self.synthesizer()
                synth_raw = self._execute_task_with_fallbacks(
                    synth_agent, synth_task, [self.synthesizer_fallback1_llm, self.synthesizer_fallback2_llm]
                )
                synth = parse_json_with_retry(synth_raw)
               
                final_response = synth.get('display_response', 'Synthesis failed.')
               
                await publish_event(session_id, {
                    "type": "synthesis_complete",
                    "response": final_response
                })

                extracted_facts = synth.get('extracted_fact', [])
                if extracted_facts:
                    self.memory_manager.update_long_term({'facts': extracted_facts if isinstance(extracted_facts, list) else [extracted_facts]})
       
        history = []
        history.append({"role": "user", "content": user_query + (f" [File: {file_path}]" if file_path else "")})
        history.append({"role": "assistant", "content": final_response})
        ChatHistory.save_history(history, session_id, uid=uid)
       
        if len(history) % 10 == 0:
            try:
                narrative = self.memory_manager.create_narrative_summary(json.dumps(history[-5:]))
            except Exception as e:
                print(f"Warning: Narrative summary failed: {e}")
       
        return {"display_response": final_response, "mode": mode, **({"operations": operations} if mode == "agentic" else {})}
    

    async def perform_operations_with_realtime_updates(self, 
                                                    operations: List[Dict[str, Any]], 
                                                    session_id: str = None, 
                                                    uid: str = None) -> str:
        if not operations:
            return "No operations to execute."
        
        ops_tool = OperationsTool()
        lines = []
        
        for i, op in enumerate(operations):
            name = op.get('name')
            params = op.get('parameters', {})
            op_id = op.get('op_id')
            
            if not op_id:
                print(f"Warning: Operation {name} has no op_id, skipping real-time updates")
                continue
                
            db_op = await get_operation_local(op_id)
            if db_op and db_op.get('status') == 'cancel_requested':
                msg = f"Operation '{name}' cancelled before start."
                lines.append(msg)
                await update_operation_local(op_id, status="cancelled", result=msg, 
                                        extra_fields={"completedAt": datetime.now().isoformat()})
                continue
            
            await update_operation_local(op_id, status="running", 
                                    extra_fields={"startedAt": datetime.now().isoformat()})
            
            await publish_event(session_id, {
                "type": "operation_started",
                "operation_id": op_id,
                "operation_name": name,
                "progress": f"{i+1}/{len(operations)}"
            })
            
            try:
                single_op = [{'name': name, 'parameters': params}]
                result = ops_tool._run(single_op)  
                result_text = str(result)
                lines.append(f"Operation '{name}': {result_text}")
                
                await update_operation_local(op_id, status="success", result=result_text, 
                                        extra_fields={
                                            "completedAt": datetime.now().isoformat(), 
                                            "progress": 100
                                        })
                
                await publish_event(session_id, {
                    "type": "operation_completed",
                    "operation_id": op_id,
                    "operation_name": name,
                    "result": result_text,
                    "progress": f"{i+1}/{len(operations)}"
                })
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                err = f"Operation '{name}' failed: {str(e)}"
                lines.append(err)
                
                await update_operation_local(op_id, status="failed", result=str(e), 
                                        extra_fields={"completedAt": datetime.now().isoformat()})
                
                await publish_event(session_id, {
                    "type": "operation_failed",
                    "operation_id": op_id,
                    "operation_name": name,
                    "error": str(e),
                    "progress": f"{i+1}/{len(operations)}"
                })
                continue
        
        await publish_event(session_id, {
            "type": "all_operations_complete",
            "total_operations": len(operations),
            "results_summary": "\n".join(lines)
        })
        
        return "\n".join(lines)

    @crew
    def crew(self) -> Crew:
        return Crew(agents=self.agents, tasks=self.tasks, process=Process.sequential, verbose=True)