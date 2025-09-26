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


    def _format_user_profile_for_llm(self, profile_data: dict) -> str:
        """Format user profile data into comprehensive context for the LLM"""
        if not profile_data:
            return "No user profile data available."
        
        name = profile_data.get('Name') or profile_data.get('display_name', 'User')
        role = profile_data.get('role', 'Not specified')
        location = profile_data.get('location', 'Not specified')
        productive_time = profile_data.get('productive_time', 'Not specified')
        top_motivation = profile_data.get('top_motivation', 'Not specified')
        ai_tone = profile_data.get('ai_tone', 'neutral')
        
        # Map values to human-readable text
        productive_time_map = {
            'morning': 'Most productive in the morning (6AM-12PM)',
            'afternoon': 'Most productive in the afternoon (12PM-6PM)', 
            'evening': 'Most productive in the evening (6PM-10PM)',
            'night': 'Most productive at night (10PM-6AM)'
        }
        
        motivation_map = {
            'achieving_goals': 'Motivated by achieving goals and completing tasks',
            'recognition_praise': 'Motivated by recognition and praise from others',
            'learning_growth': 'Motivated by learning new things and personal growth',
            'personal_satisfaction': 'Motivated by inner satisfaction and fulfillment'
        }
        
        tone_map = {
            'casual_friendly': 'Prefers casual, friendly, and warm communication',
            'professional_formal': 'Prefers professional, formal, and structured communication',
            'neutral': 'Prefers balanced, neutral, and informative communication'
        }
        
        return f"""USER PROFILE CONTEXT:
    Name: {name}
    Role/Occupation: {role.title() if role != 'Not specified' else role}
    Location: {location}
    {productive_time_map.get(productive_time, f'Productive time: {productive_time}')}
    {motivation_map.get(top_motivation, f'Primary motivation: {top_motivation}')}
    {tone_map.get(ai_tone, f'Communication preference: {ai_tone}')}

    PERSONALIZATION GUIDELINES:
    - Address the user by name when appropriate
    - Consider their role/occupation context in responses
    - Adapt communication style based on their preferred tone
    - Consider their productive time when suggesting scheduling or time-sensitive tasks
    - Frame responses to align with their primary motivation
    - Use location context for time zones, local references, or regional considerations"""

    async def run_workflow(self, user_query: str, file_path: str = None, session_id: str = None, uid: str = None):
        """
        Enhanced workflow with proper error handling and uid management
        """
        user_query = user_query.strip()
        if not user_query:
            return {"display_response": "No query provided.", "mode": "direct"}
        
        if not uid:
            return {"display_response": "User authentication required.", "mode": "direct"}
        
        try:
            # Load chat history
            history = ChatHistory.load_history(session_id)
            user_profile_raw = self.memory_manager.get_user_profile(uid)
            user_profile = self._format_user_profile_for_llm(user_profile_raw)

            file_content = self._process_file(file_path) if file_path else None
            
            # Load available operations
            file_tool = FileManagerTool()
            ops_path = os.path.join(PROJECT_ROOT, 'knowledge', 'operations.json')
            available_operations_raw = file_tool._run(ops_path)
            json_match = re.search(r'\{.*\}', available_operations_raw, re.DOTALL)
            available_operations_content = json_match.group(0) if json_match else "{}"
            
            try:
                available_operations = json.loads(available_operations_content.strip()).get("operations", [])
            except json.JSONDecodeError:
                available_operations = []
            
            available_ops_info = "\n".join([
                f"{op['name']}: {op['description']} | Required params: {', '.join(op['required_parameters'])} | Optional params: {', '.join(op.get('optional_parameters', []))}"
                for op in available_operations
            ])
            
            # Prepare history
            full_history = json.dumps(history[-8:])
            if len(full_history) > 2000:
                history_summary = ChatHistory.summarize(history[-8:])
                full_history = f"Summary: {history_summary}"
            
            # Get relevant facts
            relevant_facts = self.memory_manager.retrieve_long_term(user_query)
            
            # System info
            os_info = f"{platform.system()} {platform.release()}"
            
            inputs = {
                'user_query': user_query,
                'file_content': file_content or "",
                'full_history': full_history,
                'user_profile': json.dumps(user_profile),
                'available_ops_info': available_ops_info,
                'relevant_facts': relevant_facts,
                'os_info': os_info
            }
            
            # Classify query
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
                        parsed = json5.loads(cleaned)
                        if not isinstance(parsed, dict):  # Force dict if parsed is not (e.g., str/list)
                            parsed = {'error': 'Invalid JSON structure', 'raw': str(parsed)}
                        return parsed
                    except:
                        pass
                return {'mode': 'direct', 'display_response': f"Classification failed: {raw[:100]}... Please rephrase.", 'extracted_fact': []}  # Always dict with safe defaults
            
            classification = parse_json_with_retry(raw=classification_raw)
            
            # Handle user summary
            user_summarized_query = classification.get('user_summarized_query', 'User intent unclear.')
            if user_summarized_query and user_summarized_query != 'User intent unclear.':
                try:
                    summary_data = {
                        "date": datetime.now().isoformat().split('T')[0], 
                        "summary": user_summarized_query
                    }
                    add_summary(uid, summary_data['date'], summary_data['summary'])
                    print(f"Summary added for user {uid}")
                except Exception as e:
                    print(f"Warning: Failed to add summary: {e}")
            
            # Extract facts early
            extracted_facts = classification.get('facts', [])
            if extracted_facts:
                try:
                    self.memory_manager.update_long_term({
                        'facts': extracted_facts if isinstance(extracted_facts, list) else [extracted_facts]
                    })
                except Exception as e:
                    print(f"Warning: Failed to update long-term memory: {e}")
            
            mode = classification.get('mode', 'direct')
            
            if mode == 'direct':
                final_response = classification.get('display_response', 'No response generated.')
            else:
                operations = classification.get('operations', [])
                if not isinstance(operations, list) or not all(isinstance(op, dict) and 'name' in op for op in operations):
                    final_response = "Invalid operations plan generated. Please rephrase your query."
                    mode = 'direct'
                else:
                    try:
                        # Queue operations
                        from operations_store import queue_operation_local
                        for op in operations:
                            op_id = await queue_operation_local(op['name'], op.get('parameters', {}), session_id)
                            op['op_id'] = op_id
                        
                        # Publish event
                        await publish_event(session_id, {
                            "type": "agentic_mode_activated",
                            "message": "Nova agentic mode activated",
                            "operations_count": len(operations)
                        })
                        
                        # Perform operations
                        op_results = await self.perform_operations_with_realtime_updates(operations, session_id, uid)
                        
                        # Synthesize response
                        synth_task = self.synthesize_response()
                        synth_task.description = synth_task.description.format(
                            user_summarized_requirements=user_summarized_query,
                            op_results=op_results
                        )
                        synth_agent = self.synthesizer()
                        synth_raw = self._execute_task_with_fallbacks(
                            synth_agent, synth_task, [self.synthesizer_fallback1_llm, self.synthesizer_fallback2_llm]
                        )
                        synth = parse_json_with_retry(synth_raw)
                        
                        final_response = synth.get('display_response', 'Synthesis failed.')
                        
                        # Publish completion event
                        await publish_event(session_id, {
                            "type": "synthesis_complete",
                            "response": final_response
                        })
                        
                        # Extract facts from synthesis
                        extracted_facts = synth.get('extracted_fact', [])
                        if extracted_facts:
                            try:
                                self.memory_manager.update_long_term({
                                    'facts': extracted_facts if isinstance(extracted_facts, list) else [extracted_facts]
                                })
                            except Exception as e:
                                print(f"Warning: Failed to update long-term memory from synthesis: {e}")
                                
                    except Exception as e:
                        print(f"Error in agentic mode: {e}")
                        final_response = f"Error executing operations: {str(e)}"
                        mode = 'direct'
            
            # Save chat history
            try:
                new_history = [
                    {"role": "user", "content": user_query + (f" [File: {file_path}]" if file_path else "")},
                    {"role": "assistant", "content": final_response}
                ]
                ChatHistory.save_history(new_history, session_id, uid=uid)
                
                # Create narrative summary periodically
                current_history = ChatHistory.load_history(session_id)
                if len(current_history) % 10 == 0:
                    try:
                        narrative = self.memory_manager.create_narrative_summary(json.dumps(current_history[-5:]))
                        print(f"Narrative summary created for session {session_id}")
                    except Exception as e:
                        print(f"Warning: Narrative summary failed: {e}")
                        
            except Exception as e:
                print(f"Error saving chat history: {e}")
            
            # Return response
            result = {
                "display_response": final_response,
                "mode": mode
            }
            
            if mode == "agentic":
                result["operations"] = operations
                
            return result
            
        except Exception as e:
            print(f"Error in run_workflow: {e}")
            return {
                "display_response": f"An error occurred while processing your request: {str(e)}",
                "mode": "direct"
            }
       
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