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
            model = "claude-3-sonnet-20240229"
        
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
        """Send completion request to OpenAI API"""
        if not self.openai_key:
            raise ValueError("OPENAI_API_KEY not set")
        
        if not model:
            model = "gpt-4"
        
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 4000,
            "temperature": 0.7
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
                "platform": "openai",
                "model": model,
                "content": result["choices"][0]["message"]["content"],
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
                "platform": "openai",
                "model": model, 
                "error": f"JSON parsing or unexpected error: {str(e)}",
                "content": "",
                "timestamp": datetime.now().isoformat()
            }


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
    
    if not client.claude_key and not client.openai_key:
        print("❌ No API keys found. Set ANTHROPIC_API_KEY and/or OPENAI_API_KEY")


if __name__ == "__main__":
    test_connection()