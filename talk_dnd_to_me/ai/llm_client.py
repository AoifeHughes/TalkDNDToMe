"""LLM client wrapper for OpenAI-compatible APIs."""

from typing import List, Dict, Any, Optional
from openai import OpenAI

from ..config.settings import AIConfig


class LLMClient:
    """Wrapper around OpenAI client for LLM interactions."""
    
    def __init__(self, config: AIConfig):
        """Initialize LLM client.
        
        Args:
            config: AI configuration
        """
        self.config = config
        self.client: Optional[OpenAI] = None
    
    def initialize(self) -> bool:
        """Initialize the OpenAI client.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client = OpenAI(
                base_url=self.config.base_url,
                api_key=self.config.api_key
            )
            print(f"✓ LLM client initialized ({self.config.base_url})")
            return True
        except Exception as e:
            print(f"✗ Error initializing LLM client: {e}")
            return False
    
    def chat_completion(self, messages: List[Dict[str, Any]], 
                       tools: Optional[List[Dict[str, Any]]] = None,
                       tool_choice: str = "auto") -> Any:
        """Generate chat completion.
        
        Args:
            messages: List of conversation messages
            tools: Optional list of tool definitions
            tool_choice: Tool choice strategy
            
        Returns:
            Chat completion response
        """
        if not self.client:
            raise RuntimeError("LLM client not initialized")
        
        kwargs = {
            "model": self.config.model_name,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens
        }
        
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice
        
        return self.client.chat.completions.create(**kwargs)
