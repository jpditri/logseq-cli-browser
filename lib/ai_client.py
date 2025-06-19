#!/usr/bin/env python3
"""
AI Client - Handles API calls to Claude and OpenAI
"""

import os
import json
import requests
import time
from typing import Dict, Any, Optional
from datetime import datetime


class AIClient:
    def __init__(self):
        self.claude_key = os.getenv('ANTHROPIC_API_KEY')
        self.openai_key = os.getenv('OPENAI_API_KEY')
        self.default_retry_attempts = 3
        self.default_retry_delay = 1.0
        
        # OpenAI model definitions with capabilities
        self.openai_models = {
            # GPT-4 Models
            "gpt-4o": {
                "endpoint": "/v1/chat/completions",
                "max_tokens": 128000,
                "supports_vision": True,
                "supports_function_calling": True,
                "cost_per_1k_input": 0.005,
                "cost_per_1k_output": 0.015
            },
            "gpt-4o-mini": {
                "endpoint": "/v1/chat/completions", 
                "max_tokens": 128000,
                "supports_vision": True,
                "supports_function_calling": True,
                "cost_per_1k_input": 0.00015,
                "cost_per_1k_output": 0.0006
            },
            "gpt-4-turbo": {
                "endpoint": "/v1/chat/completions",
                "max_tokens": 128000,
                "supports_vision": True,
                "supports_function_calling": True,
                "cost_per_1k_input": 0.01,
                "cost_per_1k_output": 0.03
            },
            "gpt-4": {
                "endpoint": "/v1/chat/completions",
                "max_tokens": 8192,
                "supports_vision": False,
                "supports_function_calling": True,
                "cost_per_1k_input": 0.03,
                "cost_per_1k_output": 0.06
            },
            "gpt-4-32k": {
                "endpoint": "/v1/chat/completions",
                "max_tokens": 32768,
                "supports_vision": False,
                "supports_function_calling": True,
                "cost_per_1k_input": 0.06,
                "cost_per_1k_output": 0.12
            },
            
            # GPT-3.5 Models
            "gpt-3.5-turbo": {
                "endpoint": "/v1/chat/completions",
                "max_tokens": 16385,
                "supports_vision": False,
                "supports_function_calling": True,
                "cost_per_1k_input": 0.0015,
                "cost_per_1k_output": 0.002
            },
            "gpt-3.5-turbo-16k": {
                "endpoint": "/v1/chat/completions",
                "max_tokens": 16385,
                "supports_vision": False, 
                "supports_function_calling": True,
                "cost_per_1k_input": 0.003,
                "cost_per_1k_output": 0.004
            },
            
            # O1 Reasoning Models
            "o1-preview": {
                "endpoint": "/v1/chat/completions",
                "max_tokens": 128000,
                "supports_vision": False,
                "supports_function_calling": False,
                "cost_per_1k_input": 0.015,
                "cost_per_1k_output": 0.06,
                "reasoning_model": True
            },
            "o1-mini": {
                "endpoint": "/v1/chat/completions",
                "max_tokens": 128000,
                "supports_vision": False,
                "supports_function_calling": False,
                "cost_per_1k_input": 0.003,
                "cost_per_1k_output": 0.012,
                "reasoning_model": True
            },
            
            # Codex Models (Code Generation)
            "code-davinci-002": {
                "endpoint": "/v1/completions",
                "max_tokens": 8000,
                "supports_vision": False,
                "supports_function_calling": False,
                "cost_per_1k_tokens": 0.0,  # Free during beta
                "code_model": True
            },
            "code-cushman-001": {
                "endpoint": "/v1/completions", 
                "max_tokens": 2048,
                "supports_vision": False,
                "supports_function_calling": False,
                "cost_per_1k_tokens": 0.0,  # Free during beta
                "code_model": True
            },
            "codex-mini-latest": {
                "endpoint": "/v1/completions",
                "max_tokens": 4096,
                "supports_vision": False,
                "supports_function_calling": False,
                "cost_per_1k_tokens": 0.0,  # Free during beta
                "code_model": True
            },
            
            # Text Generation Models (Legacy)
            "text-davinci-003": {
                "endpoint": "/v1/completions",
                "max_tokens": 4000,
                "supports_vision": False,
                "supports_function_calling": False,
                "cost_per_1k_tokens": 0.02
            },
            "text-davinci-002": {
                "endpoint": "/v1/completions",
                "max_tokens": 4000,
                "supports_vision": False,
                "supports_function_calling": False,
                "cost_per_1k_tokens": 0.02
            },
            "text-curie-001": {
                "endpoint": "/v1/completions",
                "max_tokens": 2048,
                "supports_vision": False,
                "supports_function_calling": False,
                "cost_per_1k_tokens": 0.002
            },
            "text-babbage-001": {
                "endpoint": "/v1/completions",
                "max_tokens": 2048,
                "supports_vision": False,
                "supports_function_calling": False,
                "cost_per_1k_tokens": 0.0005
            },
            "text-ada-001": {
                "endpoint": "/v1/completions",
                "max_tokens": 2048,
                "supports_vision": False,
                "supports_function_calling": False,
                "cost_per_1k_tokens": 0.0004
            },
            
            # Embedding Models
            "text-embedding-3-large": {
                "endpoint": "/v1/embeddings",
                "dimensions": 3072,
                "cost_per_1k_tokens": 0.00013,
                "embedding_model": True
            },
            "text-embedding-3-small": {
                "endpoint": "/v1/embeddings", 
                "dimensions": 1536,
                "cost_per_1k_tokens": 0.00002,
                "embedding_model": True
            },
            "text-embedding-ada-002": {
                "endpoint": "/v1/embeddings",
                "dimensions": 1536,
                "cost_per_1k_tokens": 0.0001,
                "embedding_model": True
            },
            
            # Audio Models
            "whisper-1": {
                "endpoint": "/v1/audio/transcriptions",
                "cost_per_minute": 0.006,
                "audio_model": True
            },
            "tts-1": {
                "endpoint": "/v1/audio/speech",
                "cost_per_1k_chars": 0.015,
                "tts_model": True
            },
            "tts-1-hd": {
                "endpoint": "/v1/audio/speech",
                "cost_per_1k_chars": 0.03,
                "tts_model": True
            },
            
            # Image Models
            "dall-e-3": {
                "endpoint": "/v1/images/generations",
                "cost_standard": 0.04,  # 1024x1024
                "cost_hd": 0.08,       # 1024x1024 HD
                "image_model": True
            },
            "dall-e-2": {
                "endpoint": "/v1/images/generations", 
                "cost_1024": 0.02,     # 1024x1024
                "cost_512": 0.018,     # 512x512
                "cost_256": 0.016,     # 256x256
                "image_model": True
            }
        }
        
    def chat_completion(self, prompt: str, platform: str = None, model: str = None, 
                       retry_attempts: int = None, retry_delay: float = None) -> Dict[str, Any]:
        """Send a chat completion request to the specified platform with retry logic"""
        
        if retry_attempts is None:
            retry_attempts = self.default_retry_attempts
        if retry_delay is None:
            retry_delay = self.default_retry_delay
        
        # Auto-detect platform if not specified
        if not platform:
            if self.claude_key:
                platform = 'claude'
            elif self.openai_key:
                platform = 'openai'
            else:
                raise ValueError("No API keys available. Set ANTHROPIC_API_KEY or OPENAI_API_KEY")
        
        last_error = None
        
        for attempt in range(retry_attempts):
            try:
                if platform.lower() == 'claude':
                    return self._claude_completion(prompt, model)
                elif platform.lower() == 'openai':
                    return self._openai_completion(prompt, model)
                else:
                    raise ValueError(f"Unsupported platform: {platform}")
                    
            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < retry_attempts - 1:
                    print(f"API request failed (attempt {attempt + 1}/{retry_attempts}): {e}")
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    return {
                        "success": False,
                        "platform": platform,
                        "model": model or "default",
                        "error": f"All {retry_attempts} attempts failed. Last error: {str(e)}",
                        "content": "",
                        "timestamp": datetime.now().isoformat()
                    }
            except Exception as e:
                return {
                    "success": False,
                    "platform": platform,
                    "model": model or "default", 
                    "error": f"Unexpected error: {str(e)}",
                    "content": "",
                    "timestamp": datetime.now().isoformat()
                }
    
    def _claude_completion(self, prompt: str, model: str = None) -> Dict[str, Any]:
        """Send completion request to Claude API"""
        if not self.claude_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        
        if not model:
            model = "claude-3-5-sonnet-20241022"
        
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.claude_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        data = {
            "model": model,
            "max_tokens": 4000,
            "messages": [
                {
                    "role": "user", 
                    "content": prompt
                }
            ]
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=60)
            
            # Handle specific HTTP status codes
            if response.status_code == 429:
                raise requests.exceptions.RequestException(f"Rate limit exceeded (429). Headers: {dict(response.headers)}")
            elif response.status_code == 401:
                raise requests.exceptions.RequestException("Invalid API key (401)")
            elif response.status_code == 500:
                raise requests.exceptions.RequestException("Server error (500). Please try again later.")
            
            response.raise_for_status()
            
            result = response.json()
            
            return {
                "success": True,
                "platform": "claude",
                "model": model,
                "content": result["content"][0]["text"],
                "usage": result.get("usage", {}),
                "raw_response": result,
                "timestamp": datetime.now().isoformat()
            }
            
        except requests.exceptions.RequestException as e:
            # Re-raise for retry logic in chat_completion
            raise e
        except Exception as e:
            return {
                "success": False,
                "platform": "claude", 
                "model": model,
                "error": f"JSON parsing or unexpected error: {str(e)}",
                "content": "",
                "timestamp": datetime.now().isoformat()
            }
    
    def _openai_completion(self, prompt: str, model: str = None) -> Dict[str, Any]:
        """Send completion request to OpenAI API with support for all model types"""
        if not self.openai_key:
            raise ValueError("OPENAI_API_KEY not set")
        
        if not model:
            model = "gpt-4o-mini"  # Updated default to latest efficient model
        
        # Get model configuration
        model_config = self.openai_models.get(model, {})
        if not model_config:
            # Fallback for unknown models - assume chat completion
            model_config = {
                "endpoint": "/v1/chat/completions",
                "max_tokens": 4000,
                "supports_vision": False,
                "supports_function_calling": False
            }
        
        endpoint = model_config.get("endpoint", "/v1/chat/completions")
        max_tokens = min(model_config.get("max_tokens", 4000), 4000)  # Cap at 4000 for this implementation
        
        url = f"https://api.openai.com{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json"
        }
        
        # Handle different endpoint types
        if endpoint == "/v1/chat/completions":
            # Chat completions (GPT-4, GPT-3.5, O1 models)
            data = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7
            }
            
            # O1 models don't support temperature or system messages
            if model_config.get("reasoning_model"):
                del data["temperature"]
                
        elif endpoint == "/v1/completions":
            # Text completions (Davinci, Codex models)
            data = {
                "model": model,
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": 0.7
            }
            
        else:
            # For other endpoints (embeddings, audio, images), provide basic structure
            # These would need specific handling in separate methods
            data = {
                "model": model,
                "input": prompt
            }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=60)
            
            # Handle specific HTTP status codes
            if response.status_code == 429:
                raise requests.exceptions.RequestException(f"Rate limit exceeded (429). Headers: {dict(response.headers)}")
            elif response.status_code == 401:
                raise requests.exceptions.RequestException("Invalid API key (401)")
            elif response.status_code == 500:
                raise requests.exceptions.RequestException("Server error (500). Please try again later.")
            
            response.raise_for_status()
            
            result = response.json()
            
            # Extract content based on endpoint type
            if endpoint == "/v1/chat/completions":
                content = result["choices"][0]["message"]["content"]
            elif endpoint == "/v1/completions":
                content = result["choices"][0]["text"]
            else:
                content = str(result)  # Fallback for other endpoints
            
            return {
                "success": True,
                "platform": "openai",
                "model": model,
                "content": content,
                "usage": result.get("usage", {}),
                "model_config": model_config,
                "endpoint": endpoint,
                "raw_response": result,
                "timestamp": datetime.now().isoformat()
            }
            
        except requests.exceptions.RequestException as e:
            # Re-raise for retry logic in chat_completion
            raise e
        except Exception as e:
            return {
                "success": False,
                "platform": "openai",
                "model": model, 
                "error": f"JSON parsing or unexpected error: {str(e)}",
                "content": "",
                "timestamp": datetime.now().isoformat()
            }
    
    def list_openai_models(self, filter_type: str = None) -> Dict[str, Any]:
        """List available OpenAI models with optional filtering"""
        if filter_type:
            if filter_type == "chat":
                models = {k: v for k, v in self.openai_models.items() 
                         if v.get("endpoint") == "/v1/chat/completions"}
            elif filter_type == "completion":
                models = {k: v for k, v in self.openai_models.items() 
                         if v.get("endpoint") == "/v1/completions"}
            elif filter_type == "code":
                models = {k: v for k, v in self.openai_models.items() 
                         if v.get("code_model", False)}
            elif filter_type == "embedding":
                models = {k: v for k, v in self.openai_models.items() 
                         if v.get("embedding_model", False)}
            elif filter_type == "audio":
                models = {k: v for k, v in self.openai_models.items() 
                         if v.get("audio_model", False) or v.get("tts_model", False)}
            elif filter_type == "image":
                models = {k: v for k, v in self.openai_models.items() 
                         if v.get("image_model", False)}
            elif filter_type == "reasoning":
                models = {k: v for k, v in self.openai_models.items() 
                         if v.get("reasoning_model", False)}
            else:
                models = self.openai_models
        else:
            models = self.openai_models
        
        return {
            "total_models": len(models),
            "filter": filter_type,
            "models": models
        }
    
    def get_model_info(self, model: str) -> Dict[str, Any]:
        """Get detailed information about a specific model"""
        if model in self.openai_models:
            return {
                "model": model,
                "available": True,
                "platform": "openai",
                **self.openai_models[model]
            }
        else:
            return {
                "model": model,
                "available": False,
                "platform": "openai",
                "error": "Model not found in configuration"
            }
    
    def get_recommended_model(self, task_type: str = "general") -> str:
        """Get recommended model for different task types"""
        recommendations = {
            "general": "gpt-4o-mini",           # Best balance of performance and cost
            "coding": "gpt-4o",                 # Best for code generation
            "codex": "code-davinci-002",        # Specialized code model
            "reasoning": "o1-preview",          # Advanced reasoning
            "fast": "gpt-3.5-turbo",           # Fastest response
            "cheap": "gpt-4o-mini",            # Most cost-effective
            "advanced": "gpt-4o",              # Most capable
            "legacy_completion": "text-davinci-003"  # Legacy text completion
        }
        
        return recommendations.get(task_type, "gpt-4o-mini")


def test_connection():
    """Test API connections"""
    client = AIClient()
    
    print("Testing AI API connections...")
    
    if client.claude_key:
        print("\n🤖 Testing Claude...")
        result = client.chat_completion("Hello, respond with 'Claude working!'", "claude")
        if result["success"]:
            print(f"✅ Claude: {result['content'][:50]}...")
        else:
            print(f"❌ Claude: {result['error']}")
    
    if client.openai_key:
        print("\n🤖 Testing OpenAI...")
        result = client.chat_completion("Hello, respond with 'OpenAI working!'", "openai")
        if result["success"]:
            print(f"✅ OpenAI: {result['content'][:50]}...")
        else:
            print(f"❌ OpenAI: {result['error']}")
        
        # Test different model types
        print(f"\n📋 Available OpenAI Models:")
        
        # Test code models
        code_models = client.list_openai_models("code")
        print(f"🔧 Code Models: {len(code_models['models'])} available")
        for model in list(code_models['models'].keys())[:3]:
            print(f"  - {model}")
        
        # Test chat models  
        chat_models = client.list_openai_models("chat")
        print(f"💬 Chat Models: {len(chat_models['models'])} available")
        for model in list(chat_models['models'].keys())[:3]:
            print(f"  - {model}")
        
        # Test reasoning models
        reasoning_models = client.list_openai_models("reasoning")
        print(f"🧠 Reasoning Models: {len(reasoning_models['models'])} available")
        for model in reasoning_models['models'].keys():
            print(f"  - {model}")
        
        # Show recommendations
        print(f"\n💡 Model Recommendations:")
        print(f"  General: {client.get_recommended_model('general')}")
        print(f"  Coding: {client.get_recommended_model('coding')}")
        print(f"  Codex: {client.get_recommended_model('codex')}")
        print(f"  Reasoning: {client.get_recommended_model('reasoning')}")
        print(f"  Fast: {client.get_recommended_model('fast')}")
        print(f"  Cheap: {client.get_recommended_model('cheap')}")
        
        # Test Codex model if available
        print(f"\n🔧 Testing Codex Model...")
        codex_result = client.chat_completion(
            "Write a Python function to calculate fibonacci numbers", 
            "openai", 
            "code-davinci-002"
        )
        if codex_result["success"]:
            print(f"✅ Codex: Generated {len(codex_result['content'])} characters of code")
        else:
            print(f"❌ Codex: {codex_result['error']}")
    
    if not client.claude_key and not client.openai_key:
        print("❌ No API keys found. Set ANTHROPIC_API_KEY and/or OPENAI_API_KEY")


if __name__ == "__main__":
    test_connection()