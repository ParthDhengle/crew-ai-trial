import requests
import webbrowser
import os
from urllib.parse import urlparse
import json
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from crewai import Agent, Crew, Process, Task, LLM

# Global session for reusing connections
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

def search_web(query: str, num_results: int = 10) -> List[Dict]:
    """
    Searches the internet using DuckDuckGo API
    
    Args:
        query (str): Search query
        num_results (int): Number of results to return
        
    Returns:
        List[Dict]: Search results with title, url, snippet
    """
    try:
        # Using DuckDuckGo Instant Answer API (free, no API key needed)
        url = "https://api.duckduckgo.com/"
        params = {
            'q': query,
            'format': 'json',
            'no_html': '1',
            'skip_disambig': '1'
        }
        
        response = session.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = []
        
        # Get instant answer if available
        if data.get('Answer'):
            results.append({
                'title': 'Instant Answer',
                'url': data.get('AnswerURL', ''),
                'snippet': data.get('Answer', ''),
                'source': 'DuckDuckGo'
            })
        
        # Get related topics
        for topic in data.get('RelatedTopics', [])[:num_results-1]:
            if isinstance(topic, dict) and 'Text' in topic:
                results.append({
                    'title': topic.get('FirstURL', '').split('/')[-1].replace('_', ' '),
                    'url': topic.get('FirstURL', ''),
                    'snippet': topic.get('Text', ''),
                    'source': 'DuckDuckGo'
                })
        
        # If no results from DuckDuckGo, try alternative search
        if not results:
            return _alternative_search(query, num_results)
        
        return results[:num_results]
        
    except Exception as e:
        print(f"Search error: {e}")
        return [{'error': f'Search failed: {str(e)}'}]

def _alternative_search(query: str, num_results: int) -> List[Dict]:
    """Alternative search method using web scraping"""
    try:
        # This is a simplified example - in production, use proper search APIs
        search_url = f"https://html.duckduckgo.com/html/?q={query}"
        response = session.get(search_url, timeout=10)
        
        # Basic parsing (you'd want to use BeautifulSoup for real implementation)
        return [{
            'title': f'Search results for: {query}',
            'url': search_url,
            'snippet': 'Alternative search method used. Consider using Google Custom Search API or Bing Search API for better results.',
            'source': 'Alternative'
        }]
        
    except Exception as e:
        return [{'error': f'Alternative search failed: {str(e)}'}]

def download_file(url: str, save_path: str, chunk_size: int = 8192) -> Dict:
    """
    Downloads a file from a URL
    
    Args:
        url (str): URL of the file to download
        save_path (str): Local path to save the file
        chunk_size (int): Size of chunks to download at a time
        
    Returns:
        Dict: Status information about the download
    """
    try:
        # Validate URL
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            return {'success': False, 'error': 'Invalid URL'}
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else '.', exist_ok=True)
        
        # Start download
        response = session.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(save_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    file.write(chunk)
                    downloaded += len(chunk)
                    
                    # Progress indicator
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        print(f"\rDownloading: {progress:.1f}%", end='', flush=True)
        
        print(f"\nDownload completed: {save_path}")
        return {
            'success': True,
            'file_path': save_path,
            'file_size': downloaded,
            'content_type': response.headers.get('content-type', 'unknown')
        }
        
    except Exception as e:
        return {'success': False, 'error': f'Download failed: {str(e)}'}

def open_website(url: str) -> Dict:
    """
    Opens a website in the default browser
    
    Args:
        url (str): URL to open
        
    Returns:
        Dict: Status of the operation
    """
    try:
        # Validate URL
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        parsed_url = urlparse(url)
        if not parsed_url.netloc:
            return {'success': False, 'error': 'Invalid URL'}
        
        # Open in browser
        webbrowser.open(url)
        
        return {
            'success': True,
            'message': f'Opened {url} in default browser',
            'url': url
        }
        
    except Exception as e:
        return {'success': False, 'error': f'Failed to open website: {str(e)}'}

def get_weather(location: str, api_key: Optional[str] = None) -> Dict:
    """
    Fetches weather data for a location
    
    Args:
        location (str): Location name or coordinates
        api_key (str, optional): OpenWeatherMap API key
        
    Returns:
        Dict: Weather information
    """
    try:
        if api_key:
            # Use OpenWeatherMap API if API key provided
            return _get_weather_openweather(location, api_key)
        else:
            # Use free weather service (weatherapi.com has free tier)
            return _get_weather_free(location)
            
    except Exception as e:
        return {'success': False, 'error': f'Weather fetch failed: {str(e)}'}

def _get_weather_openweather(location: str, api_key: str) -> Dict:
    """Get weather from OpenWeatherMap"""
    url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        'q': location,
        'appid': api_key,
        'units': 'metric'
    }
    
    response = session.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    return {
        'success': True,
        'location': data['name'],
        'country': data['sys']['country'],
        'temperature': data['main']['temp'],
        'description': data['weather'][0]['description'],
        'humidity': data['main']['humidity'],
        'pressure': data['main']['pressure'],
        'wind_speed': data.get('wind', {}).get('speed', 0),
        'source': 'OpenWeatherMap'
    }

def _get_weather_free(location: str) -> Dict:
    """Get weather from free service"""
    try:
        # Using wttr.in - a free weather service
        url = f"https://wttr.in/{location}?format=j1"
        response = session.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        current = data['current_condition'][0]
        return {
            'success': True,
            'location': location,
            'temperature': int(current['temp_C']),
            'description': current['weatherDesc'][0]['value'],
            'humidity': int(current['humidity']),
            'pressure': int(current['pressure']),
            'wind_speed': float(current['windspeedKmph']) / 3.6,  # Convert to m/s
            'source': 'wttr.in'
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Free weather service failed: {str(e)}',
            'note': 'Consider getting an API key from OpenWeatherMap for reliable weather data'
        }

def get_news(topic: str = "general", country: str = "us", api_key: Optional[str] = None) -> List[Dict]:
    """
    Retrieves latest news articles
    
    Args:
        topic (str): News topic/category
        country (str): Country code (us, uk, etc.)
        api_key (str, optional): News API key
        
    Returns:
        List[Dict]: List of news articles
    """
    try:
        if api_key:
            return _get_news_newsapi(topic, country, api_key)
        else:
            return _get_news_free(topic)
            
    except Exception as e:
        return [{'error': f'News fetch failed: {str(e)}'}]

def _get_news_newsapi(topic: str, country: str, api_key: str) -> List[Dict]:
    """Get news from NewsAPI"""
    url = "https://newsapi.org/v2/top-headlines"
    params = {
        'category': topic,
        'country': country,
        'apiKey': api_key,
        'pageSize': 10
    }
    
    response = session.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    articles = []
    for article in data.get('articles', []):
        articles.append({
            'title': article.get('title', ''),
            'description': article.get('description', ''),
            'url': article.get('url', ''),
            'source': article.get('source', {}).get('name', ''),
            'published_at': article.get('publishedAt', ''),
            'author': article.get('author', '')
        })
    
    return articles

def _get_news_free(topic: str) -> List[Dict]:
    """Get news from free sources"""
    try:
        # Using RSS feeds as free alternative
        rss_urls = {
            'general': 'https://rss.cnn.com/rss/edition.rss',
            'technology': 'https://feeds.feedburner.com/TechCrunch',
            'business': 'https://feeds.feedburner.com/businessinsider',
            'science': 'https://www.sciencedaily.com/rss/all.xml'
        }
        
        rss_url = rss_urls.get(topic.lower(), rss_urls['general'])
        
        # Simple RSS parsing (in production, use feedparser library)
        response = session.get(rss_url, timeout=10)
        response.raise_for_status()
        
        return [{
            'title': f'News for topic: {topic}',
            'description': f'Retrieved from RSS feed: {rss_url}',
            'url': rss_url,
            'source': 'RSS Feed',
            'note': 'Install feedparser library for proper RSS parsing: pip install feedparser'
        }]
        
    except Exception as e:
        return [{
            'error': f'Free news service failed: {str(e)}',
            'note': 'Consider getting an API key from NewsAPI for reliable news data'
        }]


def browse_url(url, max_chars=3000):
    try:
        # Step 1: Fetch webpage with headers
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/115.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # Step 2: Parse & clean HTML
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.extract()

        text = " ".join(soup.get_text(separator=" ", strip=True).split())
        raw_text = text[:max_chars]

        if not raw_text:
            return "❌ No readable text found on the page."

        # Step 3: Pick available LLM
        llm = None
        if os.getenv("GROQ_API_KEY"):
            llm = LLM(model="groq/llama3-8b-8192", api_key=os.getenv("GROQ_API_KEY"))
        elif os.getenv("OPENAI_API_KEY"):
            llm = LLM(model="openai/gpt-3.5-turbo", api_key=os.getenv("OPENAI_API_KEY"))
        elif os.getenv("GOOGLE_API_KEY"):
            llm = LLM(model="gemini/gemini-1.5-flash", api_key=os.getenv("GOOGLE_API_KEY"))
        elif os.getenv("ANTHROPIC_API_KEY"):
            llm = LLM(model="anthropic/claude-3-haiku-20240307", api_key=os.getenv("ANTHROPIC_API_KEY"))

        if not llm:
            return "❌ No valid LLM API key found."

        # Step 4: Prompt
        prompt = f"""
Summarize the following webpage content:

----
{raw_text}
----

Guidelines:
- Keep it concise (5-7 sentences max).
- Highlight only useful info.
- Ignore ads, nav, junk.
- Output only the summary text.
"""
        # Step 5: Call LLM (use correct method)
        summary = llm.call(prompt).strip()

        return summary

    except Exception as e:
        return f"❌ Error fetching {url}: {e}" 
def main():
    print(browse_url("https://en.wikipedia.org/wiki/Artificial_intelligence"))
if __name__ == "__main__":
    main()