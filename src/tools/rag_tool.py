# Modified: src/agent_demo/tools/rag_tool.py
# Changes:
# - Updated imports to use langchain_community to fix deprecations
# - Annotated vectorstore as ClassVar[Optional[FAISS]] to fix Pydantic error
# - Added imports for ClassVar and Optional
# - Added PROJECT_ROOT to use absolute path for ops_path to fix FileNotFoundError
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from typing import Type, ClassVar, Optional
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

class RagToolInput(BaseModel):
    """Input schema for RagTool."""
    query: str = Field(..., description="Semantic query to find relevant operations")
    k: int = Field(default=5, description="Number of top results to return (default 5)")

class RagTool(BaseTool):
    name: str = "RagOperationsSearch"
    description: str = (
        "Semantically searches and retrieves the most relevant operations from knowledge/operations.txt "
        "based on the user's query intent. Use this instead of reading the full operations file to reduce context size. "
        "Returns a string with the top-k matching operations (format: 'name | parameters: ... | description')."
    )
    args_schema: Type[BaseModel] = RagToolInput
    vectorstore: ClassVar[Optional[FAISS]] = None # Class-level cache with annotation

    def __init__(self):
        super().__init__()
        if not RagTool.vectorstore:
            # Load and embed operations once
            ops_path = os.path.join(PROJECT_ROOT, "knowledge", "operations.txt")
            if not os.path.exists(ops_path):
                raise FileNotFoundError(f"Operations file not found: {ops_path}")
           
            with open(ops_path, "r", encoding="utf-8") as f:
                # Extract non-comment, non-empty ops lines
                ops = [line.strip() for line in f if line.strip() and not line.startswith("#") and "|" in line]
           
            if not ops:
                raise ValueError("No operations found in operations.txt")
           
            # Use lightweight, fast embedding model (all-MiniLM-L6-v2: ~80MB, good for short texts)
            embedder = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_kwargs={"device": "cpu"} # CPU for portability
            )
           
            # Create vectorstore (FAISS: efficient for small-medium datasets)
            RagTool.vectorstore = FAISS.from_texts(ops, embedder)
            print(f"✅ RAG vectorstore initialized with {len(ops)} operations.")

    def _run(self, query: str, k: int = 5) -> str:
        # Perform semantic search
        results = self.vectorstore.similarity_search(query, k=k)
        # Return as newline-separated string for easy LLM consumption
        return "\n".join([doc.page_content for doc in results])