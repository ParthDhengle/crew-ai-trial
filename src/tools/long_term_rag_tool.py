from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from typing import Type
import os
import json

from common_functions.Find_project_root import find_project_root


class LongTermRagInput(BaseModel):
    """Schema for Long-Term RAG input."""
    query: str = Field(..., description="Query for long-term memory retrieval")
    k: int = Field(default=5, description="Number of top results to fetch")


class LongTermRagTool(BaseTool):
    """Tool for semantic search in long-term memory (facts, projects, tasks)."""

    name: str = "LongTermMemorySearch"
    description: str = "Searches long-term memory (facts, projects, tasks) semantically."
    args_schema: Type[BaseModel] = LongTermRagInput

    def _run(self, query: str, k: int = 5) -> str:
        """Perform semantic search on stored long-term memory."""
        try:
            # Find project root
            project_root = find_project_root()

            # Load config
            config_path = os.path.join(project_root, "knowledge", "configs", "rag_config.json")
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            # Load embedder
            embedder = HuggingFaceEmbeddings(model_name=config["embedding_model"])

            # Load FAISS vectorstore
            vector_index_path = os.path.join(
                project_root, "knowledge", "memory", "long_term", "vector_index"
            )
            vectorstore = FAISS.load_local(
                vector_index_path,
                embedder,
                allow_dangerous_deserialization=True,
            )

            # Perform similarity search
            results = vectorstore.similarity_search(query, k=k)
            return "\n".join([doc.page_content for doc in results])

        except Exception as e:
            return f"❌ Error in LongTermMemorySearch: {str(e)}"