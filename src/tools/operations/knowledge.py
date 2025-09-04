import os
import requests
from dotenv import load_dotenv

# Load environment variables from a .env file at the start
load_dotenv()

def knowledge_retrieval(query: str) -> str:
    """
    Retrieves information on a topic using a custom search API.

    To use this function, you must have a .env file in the same directory
    with the following variables:
    - CUSTOM_SEARCH_API_KEY: Your API key for the search service.
    - CUSTOM_SEARCH_API_URL: The base URL of the search service endpoint.

    Args:
        query (str): The topic or question to search for.

    Returns:
        str: A string containing the retrieved information or an error message.
    """
    api_key = os.getenv("CUSTOM_SEARCH_API_KEY")
    api_url = os.getenv("CUSTOM_SEARCH_API_URL")

    if not api_key or not api_url:
        return "Error: CUSTOM_SEARCH_API_KEY or CUSTOM_SEARCH_API_URL is missing. Please check your .env file."

    # Define the parameters for the API request
    params = {
        "q": query,
        "api_key": api_key,
        "format": "json"  # Assuming the API accepts a format parameter
    }

    try:
        response = requests.get(api_url, params=params)
        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()
        data = response.json()

        # --- IMPORTANT ---
        # The following logic is an EXAMPLE. You must adapt it to match the
        # actual structure of the JSON response from YOUR specific API.
        # For example, if your API returns a list under a 'results' key:
        #
        # if data.get("results"):
        #     return data["results"][0]["snippet"]

        if "Abstract" in data and data["Abstract"]:
            return data["Abstract"]
        elif "definition" in data and data["definition"]:
            return data["definition"]
        else:
            return "Sorry, I couldn't find a direct answer for that topic from the knowledge base."

    except requests.exceptions.RequestException as e:
        return f"Error connecting to the knowledge API: {e}"
    except Exception as e:
        return f"An unexpected error occurred during knowledge retrieval: {e}"

# --- Example of how to use the function ---
if __name__ == '__main__':
    # This block will only run when you execute this file directly.
    # It's useful for testing your function.

    # 1. Make sure you have a .env file in the same directory with:
    #    CUSTOM_SEARCH_API_KEY="your_actual_api_key"
    #    CUSTOM_SEARCH_API_URL="http://your.api.url/search"

    # 2. Test the function with a query
    search_query = "What is the capital of India?"
    result = knowledge_retrieval(query=search_query)

    print(f"Query: {search_query}")
    print(f"Result: {result}")
