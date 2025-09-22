from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from typing import Type, ClassVar, Optional
import os
import json

from common_functions.Find_project_root import find_project_root


class RagToolInput(BaseModel):
    """Input schema for RagTool."""
    query: str = Field(..., description="Semantic query to find relevant operations")
    k: int = Field(default=5, description="Number of top results to return (default 5)")


class RagTool(BaseTool):
    """Semantic search tool for operations.json"""

    name: str = "RagOperationsSearch"
    description: str = (
        "Semantically searches and retrieves the most relevant operations from knowledge/operations.json "
        "based on the user's query intent. Use this instead of reading the full operations file to reduce context size. "
        "Returns a string with the top-k matching operations (format: 'name | parameters: ... | description')."
    )
    args_schema: Type[BaseModel] = RagToolInput

    # Class-level cache of FAISS vectorstore
    vectorstore: ClassVar[Optional[FAISS]] = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if not RagTool.vectorstore:
            # Load operations file
            project_root = find_project_root()
            ops_path = os.path.join(project_root, "knowledge", "operations.json")
            if not os.path.exists(ops_path):
                raise FileNotFoundError(f"Operations file not found: {ops_path}")

            with open(ops_path, "r", encoding="utf-8") as f:
                ops_data = json.load(f)

            # Convert ops into searchable strings
            ops = [
                f"{op['name']} | parameters: {', '.join(op['required_parameters'] + [f'{p}=None' for p in op.get('optional_parameters', [])])} | {op['description']}"
                for op in ops_data.get('operations', [])  # <-- Fix: Access the 'operations' list, default to empty list
            ]

            if not ops:
                raise ValueError("No operations found in operations.json")

            # Initialize embedder (lightweight, good for short texts)
            embedder = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_kwargs={"device": "cpu"}  # keep portable
            )

            # Build FAISS vectorstore
            RagTool.vectorstore = FAISS.from_texts(ops, embedder)
            print(f"✅ RAG vectorstore initialized with {len(ops)} operations.")

    def _run(self, query: str, k: int = 5) -> str:
        """Perform semantic search on operations and return top matches."""
        if not self.vectorstore:
            raise RuntimeError("Vectorstore not initialized.")
        results = self.vectorstore.similarity_search(query, k=k)
        return "\n".join([doc.page_content for doc in results])
