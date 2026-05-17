import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

# 1. Load the secret API keys from our .env file
load_dotenv()

class LLMEngine:
    """
    The Brain's Connection Hub.
    This class handles talking to the Groq API so we don't have to 
    write raw API requests every time.
    """
    
    def __init__(self, model_name: str = "llama-3.3-70b-versatile", temperature: float = 0.0):
        # 2. Get the API key from the environment
        api_key = os.getenv("GROQ_API_KEY")
        
        if not api_key:
            raise ValueError("❌ GROQ_API_KEY not found in .env file!")
            
        # 3. Initialize the LangChain 'Adapter' for Groq
        self.llm = ChatGroq(
            groq_api_key=api_key,
            model_name=model_name,
            temperature=temperature
        )
        
    def test_connection(self):
        """A simple method to verify the AI can hear us."""
        try:
            response = self.llm.invoke("Hello! Are you ready to analyze some real estate data?")
            return response.content
        except Exception as e:
            return f"❌ Connection Error: {str(e)}"

if __name__ == "__main__":
    # Test it out!
    engine = LLMEngine()
    print("Connecting to Groq...")
    print(f"AI Response: {engine.test_connection()}")
