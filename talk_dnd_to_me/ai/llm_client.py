"""LLM client wrapper for OpenAI-compatible APIs."""

from typing import List, Dict, Any, Optional, Generator, Tuple
from openai import OpenAI
import json

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
    
    def chat_completion_stream(self, messages: List[Dict[str, Any]], 
                              tools: Optional[List[Dict[str, Any]]] = None,
                              tool_choice: str = "auto") -> Generator[str, None, Tuple[str, Any]]:
        """Generate streaming chat completion.
        
        Args:
            messages: List of conversation messages
            tools: Optional list of tool definitions
            tool_choice: Tool choice strategy
            
        Yields:
            Content chunks as they arrive
            
        Returns:
            Tuple of (complete_content, final_response) when streaming is complete
        """
        if not self.client:
            raise RuntimeError("LLM client not initialized")
        
        kwargs = {
            "model": self.config.model_name,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": True
        }
        
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice
        
        try:
            stream = self.client.chat.completions.create(**kwargs)
            
            complete_content = ""
            tool_calls = []
            final_response = None
            
            for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    choice = chunk.choices[0]
                    
                    # Handle content streaming
                    if choice.delta and choice.delta.content:
                        content = choice.delta.content
                        complete_content += content
                        yield content
                    
                    # Handle tool calls
                    if choice.delta and choice.delta.tool_calls:
                        for tool_call in choice.delta.tool_calls:
                            # Extend tool_calls list if needed
                            while len(tool_calls) <= tool_call.index:
                                tool_calls.append({
                                    "id": "",
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""}
                                })
                            
                            # Update tool call data
                            if tool_call.id:
                                tool_calls[tool_call.index]["id"] = tool_call.id
                            if tool_call.function:
                                if tool_call.function.name:
                                    tool_calls[tool_call.index]["function"]["name"] = tool_call.function.name
                                if tool_call.function.arguments:
                                    tool_calls[tool_call.index]["function"]["arguments"] += tool_call.function.arguments
                    
                    # Store the final response structure
                    if choice.finish_reason:
                        # Create a mock response object similar to non-streaming
                        class MockChoice:
                            def __init__(self, content, tool_calls, finish_reason):
                                self.message = MockMessage(content, tool_calls)
                                self.finish_reason = finish_reason
                        
                        class MockMessage:
                            def __init__(self, content, tool_calls):
                                self.content = content
                                self.tool_calls = [MockToolCall(tc) for tc in tool_calls] if tool_calls else None
                        
                        class MockToolCall:
                            def __init__(self, tool_call_data):
                                self.id = tool_call_data["id"]
                                self.type = tool_call_data["type"]
                                self.function = MockFunction(tool_call_data["function"])
                        
                        class MockFunction:
                            def __init__(self, function_data):
                                self.name = function_data["name"]
                                self.arguments = function_data["arguments"]
                        
                        class MockResponse:
                            def __init__(self, choices):
                                self.choices = choices
                        
                        final_response = MockResponse([MockChoice(complete_content, tool_calls, choice.finish_reason)])
            
            return complete_content, final_response
            
        except Exception as e:
            raise RuntimeError(f"Streaming completion failed: {e}")
    
    def chat_completion_with_streaming(self, messages: List[Dict[str, Any]], 
                                     tools: Optional[List[Dict[str, Any]]] = None,
                                     tool_choice: str = "auto",
                                     use_streaming: Optional[bool] = None,
                                     force_streaming: bool = False) -> Tuple[str, Any, bool]:
        """Generate chat completion with optional streaming.
        
        Args:
            messages: List of conversation messages
            tools: Optional list of tool definitions
            tool_choice: Tool choice strategy
            use_streaming: Whether to use streaming (uses config default if None)
            force_streaming: Force streaming even when tools are present
            
        Returns:
            Tuple of (content, response, was_streamed)
        """
        # Use config default if not specified
        if use_streaming is None:
            use_streaming = self.config.enable_streaming
        
        # If tools are present and streaming is requested, check fallback setting
        # But allow force_streaming to override this behavior
        if tools and use_streaming and self.config.streaming_fallback_on_tools and not force_streaming:
            use_streaming = False  # Fall back to non-streaming for tool calls
        
        if use_streaming:
            try:
                stream_generator = self.chat_completion_stream(messages, tools, tool_choice)
                complete_content = ""
                final_response = None
                
                # Process the generator
                try:
                    while True:
                        content_chunk = next(stream_generator)
                        print(content_chunk, end='', flush=True)
                        complete_content += content_chunk
                except StopIteration as e:
                    # Generator finished, get the return value
                    if hasattr(e, 'value') and e.value:
                        complete_content, final_response = e.value
                
                return complete_content, final_response, True
                
            except Exception as e:
                print(f"\n⚠ Streaming failed, falling back to non-streaming: {e}")
                # Fall back to non-streaming
                response = self.chat_completion(messages, tools, tool_choice)
                return response.choices[0].message.content or "", response, False
        else:
            # Use non-streaming
            response = self.chat_completion(messages, tools, tool_choice)
            return response.choices[0].message.content or "", response, False
