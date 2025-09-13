import os
import re
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def custom_search(query: str, num_results: int = 10, site_restrict: str = None) -> tuple[bool, str]:
    """
    Perform a web search using Google Custom Search JSON API.
    
    Args:
        query (str): The search query string.
        num_results (int, optional): Number of results to return (default: 10).
        site_restrict (str, optional): Restrict search to a specific site (e.g., 'example.com').
    
    Returns:
        tuple[bool, str]: (success, result message)
    """
    try:
        api_key = os.getenv("GOOGLE_CUSTOM_SEARCH_API_KEY")
        cse_id = os.getenv("GOOGLE_CSE_ID")
        
        if not api_key or not cse_id:
            return False, "Missing GOOGLE_CUSTOM_SEARCH_API_KEY or GOOGLE_CSE_ID in environment variables."
        
        # Build the Custom Search service
        service = build("customsearch", "v1", developerKey=api_key)
        
        # Construct the search request
        search_params = {
            "q": query,
            "cx": cse_id,
            "num": min(num_results, 10)  # API limits to 10 results per request
        }
        if site_restrict:
            search_params["siteSearch"] = site_restrict
        
        # Execute the search
        result = service.cse().list(**search_params).execute()
        
        # Parse results
        items = result.get("items", [])
        if not items:
            return True, f"No results found for query: '{query}'."
        
        # Format results with improvements: clean snippets, limit length, remove Unicode artifacts
        formatted_results = []
        for item in items:
            title = item.get("title", "No title")[:100]  # Limit title length
            link = item.get("link", "No link")
            snippet = item.get("snippet", "No snippet")
            # Clean up: Remove \xa0 and other common artifacts, limit to 200 chars
            snippet = re.sub(r'\xa0', ' ', snippet)  # Replace non-breaking spaces
            snippet = re.sub(r'[^\x00-\x7F]+', ' ', snippet)  # Remove other non-ASCII if needed
            snippet = snippet[:200] + "..." if len(snippet) > 200 else snippet
            formatted_results.append(f"{title} | {link} | {snippet}")
        
        return True, f"Search results for '{query}':\n" + "\n".join(formatted_results)
    
    except HttpError as e:
        error_details = e.content.decode('utf-8') if hasattr(e, 'content') else str(e)
        return False, f"HTTP error during search ({e.resp.status}): {error_details}"
    except Exception as e:
        return False, f"Error during search: {str(e)}"

# Test the function
if __name__ == "__main__":
    query = "information about keven hearts from wikipedia"
    success, result = custom_search(query=query, num_results=5)  # Reduced for brevity
    print(f"Success: {success}")
    print(result)