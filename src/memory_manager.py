import os
import json
from datetime import date
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from common_functions.Find_project_root import find_project_root

PROJECT_ROOT = find_project_root()
MEMORY_DIR = os.path.join(PROJECT_ROOT, 'knowledge', 'memory')
CONFIG_DIR = os.path.join(PROJECT_ROOT, 'knowledge', 'configs')
LONG_TERM_DIR = os.path.join(MEMORY_DIR, 'long_term')
VECTOR_INDEX_DIR = os.path.join(LONG_TERM_DIR, 'vector_index')


class MemoryManager:
    def __init__(self):
        self.policy = self.load_json(os.path.join(CONFIG_DIR, 'memory_policy.json'))
        self.rag_config = self.load_json(os.path.join(CONFIG_DIR, 'rag_config.json'))
        self.embedder = HuggingFaceEmbeddings(
            model_name=self.rag_config['embedding_model'],
            model_kwargs={"device": "cpu"}
        )
        self.vectorstore = self.load_or_create_vectorstore()

    def load_json(self, path):
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def load_or_create_vectorstore(self):
        if os.path.exists(VECTOR_INDEX_DIR):
            return FAISS.load_local(
                VECTOR_INDEX_DIR,
                self.embedder,
                allow_dangerous_deserialization=True
            )

        texts, metadatas = self.get_long_term_texts()
        vs = FAISS.from_texts(texts, self.embedder, metadatas=metadatas)
        vs.save_local(VECTOR_INDEX_DIR)
        return vs

    def get_long_term_texts(self):
        texts = []
        metadatas = []

        # Extracted facts
        facts = self.load_json(os.path.join(LONG_TERM_DIR, 'extracted_facts.json'))
        for fact in facts:
            texts.append(fact['fact'])
            metadatas.append({'type': 'fact', 'source': fact['source']})

        # Projects and tasks
        pt = self.load_json(os.path.join(LONG_TERM_DIR, 'projects_and_tasks.json'))
        for proj in pt.get('projects', []):
            texts.append(
                f"Project: {proj['name']} goal: {proj['goal']} status: {proj['status']}"
            )
            metadatas.append({'type': 'project', 'name': proj['name']})

        for task in pt.get('tasks', []):
            texts.append(
                f"Task: {task['title']} due: {task['due']} status: {task['status']}"
            )
            metadatas.append({'type': 'task', 'id': task['id']})

        return texts, metadatas

    def update_vectorstore(self):
        texts, metadatas = self.get_long_term_texts()
        self.vectorstore = FAISS.from_texts(texts, self.embedder, metadatas=metadatas)
        self.vectorstore.save_local(VECTOR_INDEX_DIR)

    def retrieve_long_term(self, query, k=None):
        k = k or self.rag_config['top_k']
        results = self.vectorstore.similarity_search_with_score(query, k=k)

        relevant = [
            doc.page_content for doc, score in results
            if score >= self.rag_config['min_similarity']
        ]

        # Truncate to token budget
        total_len = 0
        truncated = []
        for r in relevant:
            if total_len + len(r) > self.policy['long_term_tokens'] * 1.33:  # ~chars
                break
            truncated.append(r)
            total_len += len(r)

        return '\n'.join(truncated)

    def get_narrative_summary(self):
        summaries = self.load_json(os.path.join(MEMORY_DIR, 'narrative', 'summaries.json'))
        if summaries:
            latest = summaries[-1]['summary']
            if len(latest) > self.policy['narrative_tokens'] * 1.33:
                latest = latest[:int(self.policy['narrative_tokens'] * 1.33)] + "..."
            return latest
        return ""

    def update_long_term(self, extracted):
        # Update facts
        facts_path = os.path.join(LONG_TERM_DIR, 'extracted_facts.json')
        facts = self.load_json(facts_path)
        facts.extend(extracted.get('facts', []))
        with open(facts_path, 'w', encoding='utf-8') as f:
            json.dump(facts, f, indent=2)

        # Update projects and tasks
        pt_path = os.path.join(LONG_TERM_DIR, 'projects_and_tasks.json')
        pt = self.load_json(pt_path)
        pt.setdefault('projects', []).extend(extracted.get('projects', []))
        pt.setdefault('tasks', []).extend(extracted.get('tasks', []))
        with open(pt_path, 'w', encoding='utf-8') as f:
            json.dump(pt, f, indent=2)

        # Update mood logs
        mood_logs_path = os.path.join(MEMORY_DIR, 'narrative', 'mood_logs.json')
        moods = self.load_json(mood_logs_path)
        if 'mood' in extracted:
            moods.append({"date": date.today().isoformat(), "mood": extracted['mood']})
        with open(mood_logs_path, 'w', encoding='utf-8') as f:
            json.dump(moods, f, indent=2)

        # Refresh vector index
        self.update_vectorstore()

    def create_narrative_summary(self, history_summary):
        # Would use LLM, but simulate here; in code, use generate_content
        return "Narrative summary based on history."

    def assemble_prompt_context(self, summarized_history, user_profile, narrative_summary, relevant_long_term):
        context = f"Short-term history: {summarized_history}\n"
        context += f"User profile: {json.dumps(user_profile)}\n"
        context += f"Narrative context: {narrative_summary}\n"
        context += f"Relevant long-term: {relevant_long_term}\n"

        # Truncate if exceeding total budget
        if len(context) > sum(self.policy.values()) * 1.33:
            context = context[:int(sum(self.policy.values()) * 1.33)] + "... (memory truncated)"

        return context
