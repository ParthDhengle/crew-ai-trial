import os
import json
from datetime import date, timedelta
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.docstore.in_memory import InMemoryDocstore
import faiss  # For manual index
from common_functions.Find_project_root import find_project_root
from firebase_client import add_fact, search_facts, log_mood, get_recent_moods, add_document, query_collection  # Integrate Firebase

PROJECT_ROOT = find_project_root()
MEMORY_DIR = os.path.join(PROJECT_ROOT, 'knowledge', 'memory')
CONFIG_DIR = os.path.join(PROJECT_ROOT, 'knowledge', 'configs')
LONG_TERM_DIR = os.path.join(MEMORY_DIR, 'long_term')
VECTOR_INDEX_DIR = os.path.join(LONG_TERM_DIR, 'vector_index')
USER_ID = "default_user"  # From user_profile or session

class MemoryManager:
    def __init__(self):
        self.policy = self.safe_load_json(os.path.join(CONFIG_DIR, 'memory_policy.json'), default={})
        self.rag_config = self.safe_load_json(os.path.join(CONFIG_DIR, 'rag_config.json'), default={})
        self.embedder = HuggingFaceEmbeddings(
            model_name=self.rag_config.get('embedding_model', 'sentence-transformers/all-MiniLM-L6-v2'),
            model_kwargs={"device": "cpu"}
        )
        self.vectorstore = self.load_or_create_vectorstore()
        self.user_id = USER_ID  # Set dynamically if needed

    def safe_load_json(self, path, default=None):
        if default is None:
            default = [] if any(x in os.path.basename(path) for x in ['facts', 'logs', 'summaries']) else {}
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        return json.loads(content)
        except Exception as e:
            print(f"Warning: Error loading {path}: {e}")
        print(f"Using default for {path}")
        return default

    def safe_save_json(self, path, data):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def load_or_create_vectorstore(self):
        index_file = os.path.join(VECTOR_INDEX_DIR, 'index.faiss')
        if os.path.exists(VECTOR_INDEX_DIR) and os.path.exists(index_file) and os.stat(index_file).st_size > 0:
            try:
                return FAISS.load_local(VECTOR_INDEX_DIR, self.embedder, allow_dangerous_deserialization=True)
            except Exception as e:
                print(f"Failed to load FAISS: {e}. Recreating.")
        # Recreate from Firestore facts (hybrid local/remote)
        texts, metadatas = self.get_long_term_texts()
        if texts:
            vs = FAISS.from_texts(texts, self.embedder, metadatas=metadatas)
        else:
            # Empty index
            dummy_embedding = self.embedder.embed_query("dummy")
            dimension = len(dummy_embedding)
            index = faiss.IndexFlatL2(dimension)
            vs = FAISS(self.embedder.embed_query, index, InMemoryDocstore({}), {})
        os.makedirs(VECTOR_INDEX_DIR, exist_ok=True)
        vs.save_local(VECTOR_INDEX_DIR)
        return vs

    def get_long_term_texts(self):
        texts = []
        metadatas = []
        # From Firestore facts
        facts = query_collection("facts", user_id=self.user_id)
        for fact in facts:
            texts.append(fact.get('fact', ''))
            metadatas.append({'type': 'fact', 'source': fact.get('source', ''), 'id': fact.get('id')})
        # From local projects_and_tasks.json (keep hybrid; migrate later)
        pt_path = os.path.join(LONG_TERM_DIR, 'projects_and_tasks.json')
        pt = self.safe_load_json(pt_path)
        for proj in pt.get('projects', []):
            texts.append(f"Project: {proj.get('name', '')} goal: {proj.get('goal', '')} status: {proj.get('status', '')}")
            metadatas.append({'type': 'project', 'name': proj.get('name', '')})
        for task in pt.get('tasks', []):  # Note: Tasks now in Firebase; this is legacy
            texts.append(f"Task: {task.get('title', '')} due: {task.get('due', '')} status: {task.get('status', '')}")
            metadatas.append({'type': 'task', 'id': task.get('id', '')})
        return texts, metadatas

    def update_vectorstore(self):
        try:
            texts, metadatas = self.get_long_term_texts()
            if texts:
                self.vectorstore = FAISS.from_texts(texts, self.embedder, metadatas=metadatas)
            os.makedirs(VECTOR_INDEX_DIR, exist_ok=True)
            self.vectorstore.save_local(VECTOR_INDEX_DIR)
        except Exception as e:
            print(f"Error updating vectorstore: {e}")

    def retrieve_long_term(self, query, k=None):
        try:
            k = k or self.rag_config.get('top_k', 5)
            results = self.vectorstore.similarity_search_with_score(query, k=k)
            relevant = [doc.page_content for doc, score in results if score >= self.rag_config.get('min_similarity', 0.7)]
            # Truncate
            total_len = 0
            truncated = []
            max_tokens = self.policy.get('long_term_tokens', 800) * 1.33
            for r in relevant:
                if total_len + len(r) > max_tokens:
                    break
                truncated.append(r)
                total_len += len(r)
            return '\n'.join(truncated)
        except Exception as e:
            print(f"Error retrieving: {e}")
            # Fallback to Firestore text search
            facts = search_facts(query, self.user_id, k)
            return '\n'.join([f['fact'] for f in facts])

    def get_narrative_summary(self):
        # From Firestore mood_logs and summaries
        summaries = query_collection("summaries", user_id=self.user_id)
        if summaries:
            latest = summaries[-1].get('summary', '')
            max_len = int(self.policy.get('narrative_tokens', 300) * 1.33)
            return latest[:max_len] + "..." if len(latest) > max_len else latest
        return ""

    def update_long_term(self, extracted):
        try:
            # Facts to Firestore
            for fact_data in extracted.get('facts', []):
                add_fact(fact_data.get('fact'), fact_data.get('source', ''), self.user_id)
            # Projects/tasks: Keep local for now, or migrate to Firestore
            pt_path = os.path.join(LONG_TERM_DIR, 'projects_and_tasks.json')
            pt = self.safe_load_json(pt_path)
            pt.setdefault('projects', []).extend(extracted.get('projects', []))
            pt.setdefault('tasks', []).extend(extracted.get('tasks', []))  # Sync to Firebase tasks if needed
            self.safe_save_json(pt_path, pt)
            # Mood to Firestore
            if 'mood' in extracted:
                log_mood(extracted['mood'], self.user_id)
            self.update_vectorstore()
        except Exception as e:
            print(f"Error updating long-term: {e}")

    def create_narrative_summary(self, history_summary):
        # Use LLM stub; integrate with crew if needed
        narrative = f"Narrative summary based on history: {history_summary[:200]}..."
        add_document("summaries", {"summary": narrative, "date": date.today().isoformat()}, user_id=self.user_id)
        return narrative

    def assemble_prompt_context(self, summarized_history, user_profile, narrative_summary, relevant_long_term):
        context = f"Short-term: {summarized_history}\nProfile: {json.dumps(user_profile)}\nNarrative: {narrative_summary}\nLong-term: {relevant_long_term}\n"
        total_budget = sum(self.policy.values()) * 1.33 if self.policy else 2000
        if len(context) > total_budget:
            context = context[:int(total_budget)] + "... (truncated)"
        return context