import os
import json
from datetime import date, timedelta
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.docstore.in_memory import InMemoryDocstore
import faiss
from common_functions.Find_project_root import find_project_root
from firebase_client import (
    query_collection, add_kb_entry, search_kb, add_summary, get_summaries,
    get_tasks, add_task, get_projects, add_project, get_user_profile
)

PROJECT_ROOT = find_project_root()
CONFIG_DIR = os.path.join(PROJECT_ROOT, "knowledge", "configs")
LONG_TERM_DIR = os.path.join(PROJECT_ROOT, "knowledge", "memory", "long_term")
VECTOR_INDEX_DIR = os.path.join(LONG_TERM_DIR, "vector_index")

class MemoryManager:
    def __init__(self):
        self.policy = self.safe_load_json(os.path.join(CONFIG_DIR, "memory_policy.json"), default={})
        self.rag_config = self.safe_load_json(os.path.join(CONFIG_DIR, "rag_config.json"), default={})
        self.embedder = HuggingFaceEmbeddings(
            model_name=self.rag_config.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2"),
            model_kwargs={"device": "cpu"}
        )
        self.vectorstore = self.load_or_create_vectorstore()

    def safe_load_json(self, path, default=None):
        default = default or {}
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        return json.loads(content)
        except Exception as e:
            print(f"Error loading {path}: {e}")
        return default

    def load_or_create_vectorstore(self):
        index_file = os.path.join(VECTOR_INDEX_DIR, "index.faiss")
        if os.path.exists(VECTOR_INDEX_DIR) and os.path.exists(index_file) and os.stat(index_file).st_size > 0:
            try:
                return FAISS.load_local(VECTOR_INDEX_DIR, self.embedder, allow_dangerous_deserialization=True)
            except Exception as e:
                print(f"Failed to load FAISS: {e}. Recreating from Firestore.")
        texts, metadatas = self.get_long_term_texts()
        if texts:
            vs = FAISS.from_texts(texts, self.embedder, metadatas=metadatas)
        else:
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
        # Knowledge Base (facts/notes)
        kb = query_collection("knowledge_base")
        for entry in kb:
            texts.append(entry.get("content_md", ""))
            metadatas.append({"type": "kb", "title": entry.get("title", ""), "id": entry.get("id", "")})
        # Tasks
        tasks = get_tasks()
        for task in tasks:
            texts.append(f"Task: {task.get('title', '')} due: {task.get('due_date', '')} status: {task.get('status', '')}")
            metadatas.append({"type": "task", "id": task.get("id", "")})
        # Projects
        projects = get_projects()
        for proj in projects:
            texts.append(f"Project: {proj.get('name', '')} description: {proj.get('description', '')}")
            metadatas.append({"type": "project", "id": proj.get("id", "")})
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
            k = k or self.rag_config.get("top_k", 5)
            results = self.vectorstore.similarity_search_with_score(query, k=k)
            relevant = [doc.page_content for doc, score in results if score >= self.rag_config.get("min_similarity", 0.7)]
            total_len = 0
            truncated = []
            max_tokens = self.policy.get("long_term_tokens", 800) * 1.33
            for r in relevant:
                if total_len + len(r) > max_tokens:
                    break
                truncated.append(r)
                total_len += len(r)
            return "\n".join(truncated)
        except Exception as e:
            print(f"FAISS error: {e}. Fallback to Firestore KB search.")
            kb_matches = search_kb(query, k)
            return "\n".join([m.get("content_md", "") for m in kb_matches])

    def get_narrative_summary(self):
        summaries = get_summaries()
        if summaries:
            latest = summaries[-1].get("summary_text", "")
            max_len = int(self.policy.get("narrative_tokens", 300) * 1.33)
            return latest[:max_len] + "..." if len(latest) > max_len else latest
        return ""

    def update_long_term(self, extracted):
        try:
            if not isinstance(extracted, dict):  # Guard: If not dict, skip or convert
                print(f"Warning: Extracted is not dict ({type(extracted)}), skipping long-term update.")
                return
            # Facts/KB
            facts = extracted.get("facts", [])
            if not isinstance(facts, list):
                facts = [facts] if facts else []
            for fact in facts:
                add_kb_entry(
                    title="Extracted Fact",
                    content_md=str(fact.get("fact", "")) if isinstance(fact, dict) else str(fact),
                    tags=["fact"],
                    references=[fact.get("source", "")] if isinstance(fact, dict) and fact.get("source") else []
                )
            # ... (rest unchanged: tasks, projects, etc.)
            self.update_vectorstore()
        except Exception as e:
            print(f"Update long-term failed: {e}")
            

    def create_narrative_summary(self, history_summary):
        narrative = f"Narrative: {history_summary[:200]}..."
        add_summary(date=date.today().isoformat(), summary_text=narrative)
        return narrative

    def get_user_profile(self, uid: str):  # <- Add uid parameter
        return get_user_profile(uid)

    def assemble_prompt_context(self, summarized_history, user_profile, narrative_summary, relevant_long_term):
        context = f"Short-term: {summarized_history}\nProfile: {json.dumps(user_profile)}\nNarrative: {narrative_summary}\nLong-term: {relevant_long_term}\n"
        total_budget = sum(self.policy.values()) * 1.33 if self.policy else 2000
        if len(context) > total_budget:
            context = context[:int(total_budget)] + "... (truncated)"
        return context