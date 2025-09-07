import os
import json
from datetime import date
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.docstore.in_memory import InMemoryDocstore

import faiss  # Direct import for manual index creation
from common_functions.Find_project_root import find_project_root

PROJECT_ROOT = find_project_root()
MEMORY_DIR = os.path.join(PROJECT_ROOT, 'knowledge', 'memory')
CONFIG_DIR = os.path.join(PROJECT_ROOT, 'knowledge', 'configs')
LONG_TERM_DIR = os.path.join(MEMORY_DIR, 'long_term')
VECTOR_INDEX_DIR = os.path.join(LONG_TERM_DIR, 'vector_index')

class MemoryManager:
    def __init__(self):
        self.policy = self.safe_load_json(os.path.join(CONFIG_DIR, 'memory_policy.json'), default={})
        self.rag_config = self.safe_load_json(os.path.join(CONFIG_DIR, 'rag_config.json'), default={})
        self.embedder = HuggingFaceEmbeddings(
            model_name=self.rag_config.get('embedding_model', 'sentence-transformers/all-MiniLM-L6-v2'),
            model_kwargs={"device": "cpu"}
        )
        self.vectorstore = self.load_or_create_vectorstore()

    def safe_load_json(self, path, default=None):
        """Safely load JSON, handling empty/invalid/missing files."""
        if default is None:
            default = [] if any(x in os.path.basename(path) for x in ['facts', 'logs', 'summaries']) else {}
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        return json.loads(content)
                    else:
                        print(f"Warning: Empty file {path}. Returning default: {default}")
                        return default
            else:
                print(f"Warning: File not found {path}. Returning default: {default}")
                return default
        except json.JSONDecodeError as e:
            print(f"Warning: Invalid JSON in {path} ({e}). Returning default: {default}")
            return default
        except Exception as e:
            print(f"Error loading {path}: {e}. Returning default: {default}")
            return default

    def load_or_create_vectorstore(self):
        """Load or create FAISS vectorstore, handling empty/corrupted cases."""
        index_file = os.path.join(VECTOR_INDEX_DIR, 'index.faiss')
        if os.path.exists(VECTOR_INDEX_DIR) and os.path.exists(index_file) and os.stat(index_file).st_size > 0:
            try:
                return FAISS.load_local(
                    VECTOR_INDEX_DIR,
                    self.embedder,
                    allow_dangerous_deserialization=True
                )
            except Exception as e:
                print(f"Warning: Failed to load FAISS index ({e}). Recreating from scratch.")
        
        # Recreate if missing, empty, or load failed
        try:
            texts, metadatas = self.get_long_term_texts()
            if texts:
                vs = FAISS.from_texts(texts, self.embedder, metadatas=metadatas)
            else:
                # Create empty FAISS index safely
                print("Warning: No long-term texts available. Creating empty FAISS index.")
                # Get embedding dimension dynamically
                dummy_embedding = self.embedder.embed_query("dummy")
                dimension = len(dummy_embedding)
                index = faiss.IndexFlatL2(dimension)
                vs = FAISS(
                    embedding_function=self.embedder.embed_query,
                    index=index,
                    docstore=InMemoryDocstore({}),
                    index_to_docstore_id={},
                )
            os.makedirs(VECTOR_INDEX_DIR, exist_ok=True)
            vs.save_local(VECTOR_INDEX_DIR)
            return vs
        except Exception as e:
            print(f"Critical error creating vectorstore: {e}. Using minimal empty index.")
            # Fallback to absolute minimal empty index
            dimension = 384  # Default for all-MiniLM-L6-v2 if dummy fails
            index = faiss.IndexFlatL2(dimension)
            return FAISS(
                embedding_function=self.embedder.embed_query,
                index=index,
                docstore=InMemoryDocstore({}),
                index_to_docstore_id={},
            )

    def get_long_term_texts(self):
        texts = []
        metadatas = []
        # Extracted facts
        facts = self.safe_load_json(os.path.join(LONG_TERM_DIR, 'extracted_facts.json'))
        for fact in facts:
            texts.append(fact.get('fact', ''))
            metadatas.append({'type': 'fact', 'source': fact.get('source', '')})
        # Projects and tasks
        pt = self.safe_load_json(os.path.join(LONG_TERM_DIR, 'projects_and_tasks.json'))
        for proj in pt.get('projects', []):
            texts.append(f"Project: {proj.get('name', '')} goal: {proj.get('goal', '')} status: {proj.get('status', '')}")
            metadatas.append({'type': 'project', 'name': proj.get('name', '')})
        for task in pt.get('tasks', []):
            texts.append(f"Task: {task.get('title', '')} due: {task.get('due', '')} status: {task.get('status', '')}")
            metadatas.append({'type': 'task', 'id': task.get('id', '')})
        return texts, metadatas

    def update_vectorstore(self):
        try:
            texts, metadatas = self.get_long_term_texts()
            if texts:
                self.vectorstore = FAISS.from_texts(texts, self.embedder, metadatas=metadatas)
            else:
                # Reuse empty creation logic
                self.vectorstore = self.load_or_create_vectorstore()  # Will create empty
            os.makedirs(VECTOR_INDEX_DIR, exist_ok=True)
            self.vectorstore.save_local(VECTOR_INDEX_DIR)
        except Exception as e:
            print(f"Error updating vectorstore: {e}. Keeping existing index.")

    def retrieve_long_term(self, query, k=None):
        try:
            k = k or self.rag_config.get('top_k', 5)
            results = self.vectorstore.similarity_search_with_score(query, k=k)
            relevant = [doc.page_content for doc, score in results if score >= self.rag_config.get('min_similarity', 0.7)]
            # Truncate to token budget
            total_len = 0
            truncated = []
            for r in relevant:
                if total_len + len(r) > self.policy.get('long_term_tokens', 800) * 1.33:
                    break
                truncated.append(r)
                total_len += len(r)
            return '\n'.join(truncated)
        except Exception as e:
            print(f"Error retrieving long-term: {e}. Returning empty string.")
            return ''

    def get_narrative_summary(self):
        summaries = self.safe_load_json(os.path.join(MEMORY_DIR, 'narrative', 'summaries.json'))
        if summaries:
            latest = summaries[-1].get('summary', '')
            max_len = int(self.policy.get('narrative_tokens', 300) * 1.33)
            return latest[:max_len] + "..." if len(latest) > max_len else latest
        return ""

    def update_long_term(self, extracted):
        try:
            # Update facts
            facts_path = os.path.join(LONG_TERM_DIR, 'extracted_facts.json')
            facts = self.safe_load_json(facts_path)
            facts.extend(extracted.get('facts', []))
            os.makedirs(os.path.dirname(facts_path), exist_ok=True)
            with open(facts_path, 'w', encoding='utf-8') as f:
                json.dump(facts, f, indent=2)
            # Update projects and tasks
            pt_path = os.path.join(LONG_TERM_DIR, 'projects_and_tasks.json')
            pt = self.safe_load_json(pt_path)
            pt.setdefault('projects', []).extend(extracted.get('projects', []))
            pt.setdefault('tasks', []).extend(extracted.get('tasks', []))
            os.makedirs(os.path.dirname(pt_path), exist_ok=True)
            with open(pt_path, 'w', encoding='utf-8') as f:
                json.dump(pt, f, indent=2)
            # Update mood logs
            mood_logs_path = os.path.join(MEMORY_DIR, 'narrative', 'mood_logs.json')
            moods = self.safe_load_json(mood_logs_path)
            if 'mood' in extracted:
                moods.append({"date": date.today().isoformat(), "mood": extracted['mood']})
            os.makedirs(os.path.dirname(mood_logs_path), exist_ok=True)
            with open(mood_logs_path, 'w', encoding='utf-8') as f:
                json.dump(moods, f, indent=2)
            # Refresh vector index
            self.update_vectorstore()
        except Exception as e:
            print(f"Error updating long-term memory: {e}. Changes may not be saved.")

    def create_narrative_summary(self, history_summary):
        # Would use LLM, but simulate here; in code, use generate_content
        return "Narrative summary based on history."

    def assemble_prompt_context(self, summarized_history, user_profile, narrative_summary, relevant_long_term):
        try:
            context = f"Short-term history: {summarized_history}\n"
            context += f"User profile: {json.dumps(user_profile)}\n"
            context += f"Narrative context: {narrative_summary}\n"
            context += f"Relevant long-term: {relevant_long_term}\n"
            # Truncate if exceeding total budget
            total_budget = sum(self.policy.values()) * 1.33 if self.policy else 2000
            if len(context) > total_budget:
                context = context[:int(total_budget)] + "... (memory truncated)"
            return context
        except Exception as e:
            print(f"Error assembling prompt context: {e}. Returning minimal context.")
            return f"User profile: {json.dumps(user_profile)}"