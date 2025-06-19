#!/usr/bin/env python3
"""
Tests for AI client module
"""

import pytest
import sys
import json
from pathlib import Path
from unittest.mock import Mock, patch

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
from ai_client import AIClient


class TestAIClient:
    def test_init_without_keys(self):
        """Test initialization without API keys"""
        with patch.dict('os.environ', {}, clear=True):
            client = AIClient()
            assert client.claude_key is None
            assert client.openai_key is None
    
    def test_init_with_keys(self):
        """Test initialization with API keys"""
        with patch.dict('os.environ', {
            'ANTHROPIC_API_KEY': 'test-claude-key',
            'OPENAI_API_KEY': 'test-openai-key'
        }):
            client = AIClient()
            assert client.claude_key == 'test-claude-key'
            assert client.openai_key == 'test-openai-key'
    
    @patch('lib.ai_client.requests.post')
    def test_claude_success(self, mock_post):
        """Test successful Claude API call"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"text": "Hello from Claude!"}],
            "usage": {"input_tokens": 10, "output_tokens": 5}
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            client = AIClient()
            result = client.chat_completion("Hello", "claude")
            
            assert result["success"] is True
            assert result["platform"] == "claude"
            assert result["content"] == "Hello from Claude!"
            assert "usage" in result
    
    @patch('lib.ai_client.requests.post')
    def test_openai_success(self, mock_post):
        """Test successful OpenAI API call"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello from OpenAI!"}}],
            "usage": {"prompt_tokens": 8, "completion_tokens": 4}
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            client = AIClient()
            result = client.chat_completion("Hello", "openai")
            
            assert result["success"] is True
            assert result["platform"] == "openai"
            assert result["content"] == "Hello from OpenAI!"
            assert "usage" in result
    
    @patch('lib.ai_client.requests.post')
    def test_rate_limit_retry(self, mock_post):
        """Test retry logic on rate limit"""
        # First call returns 429, second succeeds
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {'retry-after': '1'}
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            "content": [{"text": "Success after retry"}],
            "usage": {"input_tokens": 10, "output_tokens": 5}
        }
        mock_response_success.raise_for_status.return_value = None
        
        # First call raises exception, second succeeds
        mock_post.side_effect = [
            Exception("Rate limit exceeded (429). Headers: {'retry-after': '1'}"),
            mock_response_success
        ]
        
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            with patch('time.sleep'):  # Speed up test by mocking sleep
                client = AIClient()
                result = client.chat_completion("Hello", "claude", retry_attempts=2)
                
                assert result["success"] is True
                assert result["content"] == "Success after retry"
                assert mock_post.call_count == 2
    
    @patch('lib.ai_client.requests.post')
    def test_api_failure_all_retries(self, mock_post):
        """Test failure after all retries exhausted"""
        mock_post.side_effect = Exception("Server error")
        
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            with patch('time.sleep'):  # Speed up test
                client = AIClient()
                result = client.chat_completion("Hello", "claude", retry_attempts=2)
                
                assert result["success"] is False
                assert "All 2 attempts failed" in result["error"]
                assert mock_post.call_count == 2
    
    def test_invalid_platform(self):
        """Test invalid platform handling"""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            client = AIClient()
            result = client.chat_completion("Hello", "invalid-platform")
            
            assert result["success"] is False
            assert "Unsupported platform" in result["error"]
    
    def test_auto_platform_detection(self):
        """Test automatic platform detection"""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'claude-key'}):
            client = AIClient()
            
            # Mock the actual API call
            with patch.object(client, '_claude_completion') as mock_claude:
                mock_claude.return_value = {"success": True, "platform": "claude"}
                
                result = client.chat_completion("Hello")
                mock_claude.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, '-v'])