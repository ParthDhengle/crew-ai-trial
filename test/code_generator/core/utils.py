import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables from .env file
load_dotenv()

# Set up Gemini API key from .env
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def llm_call(prompt, model="gemini-1.5-flash", max_tokens=2000):
    """
    Abstracted LLM call using Gemini API for reusability and potential caching.
    Uses gemini-1.5-flash for cost efficiency; system message is minimal to save tokens.
    Could add caching: hash prompt + model and store responses.
    """
    try:
        # Initialize the Gemini model
        gemini_model = genai.GenerativeModel(model)
        
        # System message for consistency with original OpenAI setup
        system_message = "You are a precise coding assistant. Follow instructions exactly."
        
        # Combine system and user prompt
        full_prompt = f"{system_message}\n\n{prompt}"
        
        # Make the API call
        response = gemini_model.generate_content(
            full_prompt,
            generation_config={
                "max_output_tokens": max_tokens,
                "temperature": 0.2  # Low for deterministic outputs
            }
        )
        
        content = response.text.strip()
        return content
    except Exception as e:
        raise RuntimeError(f"Gemini API call failed: {str(e)}")

def choose_model(est_size):
    """
    Selects model based on estimated size/complexity for cost optimization.
    Using gemini-1.5-flash for tiny/small, gemini-1.5-pro for medium/large.
    """
    if est_size in ["tiny", "small"]:
        return "gemini-1.5-flash"  # Cheap
    else:
        return "gemini-1.5-pro"  # Stronger for medium/large