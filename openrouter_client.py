import os
import requests
from typing import Dict, Optional

class OpenRouterClient:
    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OpenRouter API key not provided and not found in environment variables")
    
    def generate_code(
        self, 
        prompt: str, 
        model: str = "openai/gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        system_prompt: str = None,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        stop: list = None
    ) -> str:
        """
        Generate code using the specified model with advanced parameters
        
        Args:
            prompt: The prompt to send to the model
            model: The model to use (e.g., 'openai/gpt-4', 'mistralai/mixtral-8x7b-instruct')
            temperature: Controls randomness (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate
            system_prompt: Optional system message to guide the model
            top_p: Nucleus sampling parameter (0.0 to 1.0)
            frequency_penalty: Penalize new tokens based on frequency (-2.0 to 2.0)
            presence_penalty: Penalize new tokens based on presence (-2.0 to 2.0)
            stop: List of strings that stop generation when encountered
            
        Returns:
            str: The generated code
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/yourusername/ai-code-generator",
            "X-Title": "AI Code Generator"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        data = {
            "model": model,
            "messages": messages,
            "temperature": max(0.1, min(1.0, temperature)),
            "max_tokens": max(100, min(8000, max_tokens)),
            "top_p": max(0.1, min(1.0, top_p)),
            "frequency_penalty": max(-2.0, min(2.0, frequency_penalty)),
            "presence_penalty": max(-2.0, min(2.0, presence_penalty)),
        }
        
        if stop:
            data["stop"] = stop[:4]  # Limit to 4 stop sequences
        
        try:
            response = requests.post(
                self.BASE_URL,
                headers=headers,
                json=data
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error generating code: {str(e)}")

if __name__ == "__main__":
    # Example usage
    client = OpenRouterClient()
    response = client.generate_code("Write a Python function that adds two numbers")
    print(response)
