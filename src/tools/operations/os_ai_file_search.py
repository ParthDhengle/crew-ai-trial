import os
import glob
from typing import List, Dict, Tuple
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from PyPDF2 import PdfReader
from docx import Document
import pickle  # For saving/loading index

# Supported file extensions
SUPPORTED_EXTS = ['.pdf', '.docx', '.txt']

class OSFileSearcher:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize the searcher with a sentence transformer model for embeddings.
        """
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.file_metadata = []  # List of (file_path, title, chunks)
        self.dimension = 384  # Default embedding dim for MiniLM

    def extract_text_from_file(self, file_path: str) -> str:
        """
        Extract text from a supported file.
        """
        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext == '.pdf':
                reader = PdfReader(file_path)
                text = ''.join(page.extract_text() or '' for page in reader.pages)
            elif ext == '.docx':
                doc = Document(file_path)
                text = '\n'.join(para.text for para in doc.paragraphs)
            elif ext == '.txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
            else:
                return ''
            if not isinstance(text, str):
                print(f"Non-string text extracted from {file_path}: {type(text)}")
                return ''
            text = ''.join(c for c in text if c.isprintable() or c.isspace())
            if not text.strip():
                print(f"No valid text after cleaning from {file_path}")
                return ''
            print(f"Extracted {len(text)} characters from {file_path}")
            return text
        except Exception as e:
            print(f"Error extracting text from {file_path}: {e}")
            return ''

    def chunk_text(self, text: str, chunk_size: int = 500) -> List[str]:
        """
        Split text into overlapping chunks for better semantic coverage.
        """
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size):
            chunk = ' '.join(words[i:i + chunk_size])
            chunks.append(chunk)
        return chunks

    def build_index(self, root_dir: str, save_path: str = None) -> None:
        """
        Recursively find supported files, extract text, generate embeddings, and build FAISS index.
        """
        exclude_dirs = ['AppData', 'Program Files', 'Windows', '.cache', '.local']
        file_paths = []
        for ext in SUPPORTED_EXTS:
            pattern = os.path.join(root_dir, '**', f'*{ext}')
            for path in glob.glob(pattern, recursive=True):
                if not any(exclude in path for exclude in exclude_dirs):
                    file_paths.append(path)

        embeddings = []
        metadata = []

        for file_path in file_paths:
            text = self.extract_text_from_file(file_path)
            if not text or not isinstance(text, str) or text.strip() == '':
                print(f"Skipping {file_path}: No valid text extracted")
                continue
            chunks = self.chunk_text(text)
            title = os.path.basename(file_path)
            for chunk in chunks:
                if not chunk.strip():
                    print(f"Skipping empty chunk in {file_path}")
                    continue
                try:
                    embedding = self.model.encode(chunk)
                    embeddings.append(embedding)
                    metadata.append((file_path, title, chunk[:100] + '...' if len(chunk) > 100 else chunk))
                except Exception as e:
                    print(f"Error encoding chunk in {file_path}: {e}")
                    continue

        if embeddings:
            self.index = faiss.IndexFlatIP(self.dimension)
            self.index.add(np.array(embeddings).astype('float32'))
            self.file_metadata = metadata
            print(f"Indexed {len(metadata)} chunks from {len(set([m[0] for m in metadata]))} files.")

            if save_path:
                faiss.write_index(self.index, save_path + '_index.faiss')
                with open(save_path + '_metadata.pkl', 'wb') as f:
                    pickle.dump(metadata, f)
        else:
            print("No valid embeddings generated. Index not created.")

    def load_index(self, index_path: str, metadata_path: str) -> None:
        """
        Load pre-built index (for faster startup).
        """
        self.index = faiss.read_index(index_path)
        with open(metadata_path, 'rb') as f:
            self.file_metadata = pickle.load(f)
        print(f"Loaded index with {len(self.file_metadata)} chunks.")

    def semantic_search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Perform semantic search using natural language query.
        Returns top_k results with file path, title, snippet, and score.
        """
        if self.index is None:
            raise ValueError("Index not built. Call build_index() first.")

        query_embedding = self.model.encode([query])
        scores, indices = self.index.search(query_embedding.astype('float32'), top_k * 10)

        results = []
        seen_files = set()
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            file_path, title, snippet = self.file_metadata[idx]
            if file_path not in seen_files:
                results.append({
                    'path': file_path,
                    'title': title,
                    'snippet': snippet,
                    'relevance_score': float(score)
                })
                seen_files.add(file_path)
                if len(results) >= top_k:
                    break

        return results

    def keyword_search(self, query: str, root_dir: str, top_k: int = 5) -> List[Dict]:
        """
        Simple keyword-based file search (filename or content).
        Useful for quick OS file finding without full indexing.
        """
        pattern = os.path.join(root_dir, '**', f'*{query}*')
        matches = glob.glob(pattern, recursive=True)

        results = []
        for match in matches[:top_k * 2]:
            if any(match.endswith(ext) for ext in SUPPORTED_EXTS):
                text = self.extract_text_from_file(match)
                if query.lower() in text.lower() or query.lower() in match.lower():
                    results.append({
                        'path': match,
                        'title': os.path.basename(match),
                        'snippet': text[:100] + '...' if text else 'No preview',
                        'relevance_score': 1.0
                    })
                    if len(results) >= top_k:
                        break

        return results

def ai_assistant_file_query(query: str, root_dir: str = os.path.join(os.path.expanduser('~'), 'Downloads'), use_semantic: bool = True, top_k: int = 3):
    """
    High-level function for your AI assistant to handle file queries.
    Determines if query is semantic (e.g., contains phrases) or keyword-based.
    """
    searcher = OSFileSearcher()
    
    index_path = os.path.join(os.path.expanduser('~'), '.ai_assistant', 'file_index.faiss')
    metadata_path = os.path.join(os.path.expanduser('~'), '.ai_assistant', 'file_metadata.pkl')
    if os.path.exists(index_path):
        searcher.load_index(index_path, metadata_path)
    else:
        os.makedirs(os.path.join(os.path.expanduser('~'), '.ai_assistant'), exist_ok=True)
        searcher.build_index(root_dir, os.path.join(os.path.expanduser('~'), '.ai_assistant', 'file_index'))
    
    if use_semantic and len(query.split()) > 2:
        results = searcher.semantic_search(query, top_k)
    else:
        results = searcher.keyword_search(query, root_dir, top_k)
    
    return results



# if __name__ == "__main__":
#     query = "document related to parth dhengle"
#     results = ai_assistant_file_query(query, use_semantic=True, top_k=3)
#     for res in results:
#         print(f"Title: {res['title']}\nPath: {res['path']}\nSnippet: {res['snippet']}\nScore: {res['relevance_score']}\n---")
