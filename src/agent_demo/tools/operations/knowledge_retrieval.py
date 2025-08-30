from crewai_tools import BaseTool
import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

class KnowledgeRetrievalTool(BaseTool):
    name: str = "KnowledgeRetrievalTool"
    description: str = (
        "Retrieves explanations or information about a given topic "
        "using a knowledge base or web search."
    )

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
                return "API key or URL is missing. Please check your .env file."

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
    
    
    def retrieve_knowledge(query: str) -> str:
        # TODO: replace with real logic
        return f"Knowledge retrieval placeholder for query: {query}"