from pydantic import BaseModel, Field
from crewai.tools import BaseTool  # Correct import from crewai
import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Define schema for tool arguments
class KnowledgeRetrievalToolSchema(BaseModel):
    query: str = Field(..., description="The topic or question to retrieve information for.")

class KnowledgeRetrievalTool(BaseTool):
    name: str = "KnowledgeRetrievalTool"
    description: str = (
        "Retrieves explanations or information about a given topic "
        "using a knowledge base or web search."
    )
    args_schema = KnowledgeRetrievalToolSchema

    def _run(self, query: str) -> str:
        """
        Retrieve information based on the query.
        Args:
            query: The topic or question to retrieve information for.
        Returns:
            A string containing the retrieved information.
        """
        try:
            api_key = os.getenv("CUSTOM_SEARCH_API_KEY")
            api_url = os.getenv("CUSTOM_SEARCH_API_URL")

            if not api_key or not api_url:
                # Mock response for testing
                return f"Mock response: Information about '{query}' would be retrieved here."

            response = requests.get(
                api_url,
                params={"q": query, "format": "json", "api_key": api_key}
            )
            response.raise_for_status()
            data = response.json()

            # Extract relevant information (simplified example)
            if "Abstract" in data and data["Abstract"]:
                return data["Abstract"]
            else:
                return "Sorry, I couldn't find information on that topic."
        except Exception as e:
            return f"Error retrieving information: {str(e)}"
    
    def retrieve_knowledge(self, query: str) -> str:
        """
        Wrapper method to retrieve knowledge.
        Args:
            query: The topic or question to retrieve information for.
        Returns:
            A string containing the retrieved information.
        """
        return self._run(query)