import os
import requests
from typing import List, Dict
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")
SEARCH_ENGINE_ID = os.getenv("GOOGLE_CX")

def search_web(query: str, num_results: int = 5) -> List[Dict]:
    """
    Search the web using Google Custom Search JSON API.
    
    Args:
        query (str): Search query
        num_results (int): Number of results to return (max 10 per request)
    
    Returns:
        List[Dict]: Search results with title, url, snippet
    """
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": API_KEY,
        "cx": SEARCH_ENGINE_ID,
        "q": query,
        "num": num_results
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        results = []
        for item in data.get("items", []):
            results.append({
                "title": item.get("title"),
                "url": item.get("link"),
                "snippet": item.get("snippet"),
                "source": "Google"
            })
        
        return results
    
    except Exception as e:
        return [{"error": f"Google Search failed: {str(e)}"}]

# Example usage
if __name__ == "__main__":
    results = search_web("OpenAI GPT-4 info", 5)
    for r in results:
        print(f"{r['title']} -> {r['url']}")


