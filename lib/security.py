#!/usr/bin/env python3
"""
Security and input validation for Computer project
"""

import re
import html
import os
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from urllib.parse import urlparse


class SecurityError(Exception):
    """Exception raised for security-related issues"""
    pass


class InputSanitizer:
    """Input sanitization and validation utilities"""
    
    def __init__(self):
        # Dangerous patterns to detect
        self.dangerous_patterns = [
            r'<script[^>]*>.*?</script>',  # Script tags
            r'javascript:',  # JavaScript URLs
            r'on\w+\s*=',  # Event handlers
            r'eval\s*\(',  # eval() calls
            r'exec\s*\(',  # exec() calls
            r'__import__',  # Python imports
            r'subprocess\.',  # Subprocess calls
            r'os\.',  # OS module calls
            r'file\s*\(',  # File operations
            r'open\s*\(',  # File opening
            r'\.\./|\.\.\\'  # Directory traversal
        ]
        
        # Compile patterns for efficiency
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE | re.DOTALL) 
                                for pattern in self.dangerous_patterns]
        
        # Maximum lengths for different input types
        self.max_lengths = {
            'prompt': 50000,
            'filename': 255,
            'platform': 20,
            'model': 100,
            'description': 5000,
            'notes': 10000
        }
    
    def sanitize_prompt(self, prompt: str) -> str:
        """Sanitize user prompt input"""
        if not isinstance(prompt, str):
            raise SecurityError("Prompt must be a string")
        
        # Check length
        max_len = self.max_lengths.get('prompt', 50000)
        if len(prompt) > max_len:
            raise SecurityError(f"Prompt too long: {len(prompt)} > {max_len} characters")
        
        # Check for dangerous patterns
        for pattern in self.compiled_patterns:
            if pattern.search(prompt):
                raise SecurityError(f"Potentially dangerous content detected: {pattern.pattern}")
        
        # Basic HTML escape
        sanitized = html.escape(prompt)
        
        # Remove null bytes and control characters (except newlines and tabs)
        sanitized = ''.join(char for char in sanitized 
                          if ord(char) >= 32 or char in '\n\t\r')
        
        # Normalize whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized.strip())
        
        return sanitized
    
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path traversal and invalid characters"""
        if not isinstance(filename, str):
            raise SecurityError("Filename must be a string")
        
        # Check length
        max_len = self.max_lengths.get('filename', 255)
        if len(filename) > max_len:
            raise SecurityError(f"Filename too long: {len(filename)} > {max_len} characters")
        
        # Remove dangerous characters
        sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', filename)
        
        # Prevent directory traversal
        sanitized = sanitized.replace('..', '')
        
        # Remove leading/trailing dots and spaces
        sanitized = sanitized.strip('. ')
        
        if not sanitized:
            raise SecurityError("Filename becomes empty after sanitization")
        
        # Prevent reserved names on Windows
        reserved_names = {
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }
        
        name_without_ext = sanitized.split('.')[0].upper()
        if name_without_ext in reserved_names:
            sanitized = f"safe_{sanitized}"
        
        return sanitized
    
    def validate_platform(self, platform: str) -> bool:
        """Validate AI platform name"""
        if not isinstance(platform, str):
            return False
        
        valid_platforms = {'claude', 'openai', 'auto'}
        return platform.lower() in valid_platforms
    
    def validate_model(self, model: str, platform: str = None) -> bool:
        """Validate AI model name"""
        if not isinstance(model, str):
            return False
        
        # Basic validation
        if len(model) > self.max_lengths.get('model', 100):
            return False
        
        # Check for dangerous characters
        if re.search(r'[<>:"/\\|?*\x00-\x1f]', model):
            return False
        
        # Platform-specific validation
        if platform:
            valid_models = {
                'claude': [
                    'claude-3-opus', 'claude-3-sonnet', 'claude-3-haiku',
                    'claude-3-opus-20240229', 'claude-3-sonnet-20240229', 'claude-3-haiku-20240307'
                ],
                'openai': [
                    'gpt-4', 'gpt-4-turbo', 'gpt-4-turbo-preview',
                    'gpt-3.5-turbo', 'gpt-3.5-turbo-1106', 'gpt-4-1106-preview'
                ]
            }
            
            platform_models = valid_models.get(platform.lower(), [])
            return any(model.startswith(valid_model) for valid_model in platform_models)
        
        return True
    
    def validate_file_path(self, file_path: Union[str, Path], base_path: Union[str, Path] = None) -> bool:
        """Validate file path for security"""
        try:
            path = Path(file_path).resolve()
            
            # Check if path exists and is a file
            if not path.exists() or not path.is_file():
                return False
            
            # If base path provided, ensure file is within it
            if base_path:
                base = Path(base_path).resolve()
                try:
                    path.relative_to(base)
                except ValueError:
                    return False  # Path is outside base directory
            
            return True
        except (OSError, ValueError):
            return False
    
    def sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize metadata dictionary"""
        if not isinstance(metadata, dict):
            raise SecurityError("Metadata must be a dictionary")
        
        sanitized = {}
        
        for key, value in metadata.items():
            # Sanitize key
            if not isinstance(key, str):
                continue
            
            safe_key = re.sub(r'[^\w\-_]', '', key)[:50]
            if not safe_key:
                continue
            
            # Sanitize value based on type
            if isinstance(value, str):
                if len(value) > 1000:  # Limit string values
                    value = value[:1000]
                safe_value = html.escape(value)
            elif isinstance(value, (int, float, bool)):
                safe_value = value
            elif isinstance(value, list):
                # Sanitize list elements (only allow simple types)
                safe_value = []
                for item in value[:100]:  # Limit list size
                    if isinstance(item, (str, int, float, bool)):
                        if isinstance(item, str):
                            safe_value.append(html.escape(item[:100]))
                        else:
                            safe_value.append(item)
            else:
                # Skip complex objects
                continue
            
            sanitized[safe_key] = safe_value
        
        return sanitized
    
    def check_content_safety(self, content: str) -> List[str]:
        """Check content for potential security issues, return list of warnings"""
        warnings = []
        
        # Check for suspicious patterns
        patterns = {
            'SQL injection': r'(union|select|insert|update|delete|drop|create|alter)\s+',
            'Command injection': r'[;&|`$(){}]',
            'Path traversal': r'\.\./|\.\.\/',
            'Script content': r'<script[^>]*>',
            'Eval/exec': r'(eval|exec|__import__)\s*\(',
            'File operations': r'(open|file|read|write)\s*\(',
            'Network requests': r'(requests|urllib|http|fetch)\.',
            'System commands': r'(subprocess|os\.system|popen)\.',
        }
        
        for threat_type, pattern in patterns.items():
            if re.search(pattern, content, re.IGNORECASE):
                warnings.append(f"Potential {threat_type} detected")
        
        return warnings
    
    def generate_safe_id(self, content: str, prefix: str = "task") -> str:
        """Generate a safe ID from content"""
        # Create hash of content for uniqueness
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        
        # Create safe prefix
        safe_prefix = re.sub(r'[^\w\-]', '', prefix)[:10]
        
        return f"{safe_prefix}-{content_hash}"
    
    def validate_api_key(self, api_key: str, platform: str) -> bool:
        """Validate API key format"""
        if not isinstance(api_key, str):
            return False
        
        patterns = {
            'claude': r'^sk-ant-api03-[A-Za-z0-9\-_]+$',
            'openai': r'^sk-[A-Za-z0-9]{48,}$'
        }
        
        pattern = patterns.get(platform.lower())
        if pattern:
            return bool(re.match(pattern, api_key))
        
        # Generic validation
        return len(api_key) > 10 and api_key.startswith('sk-')


class PermissionManager:
    """Manage file and directory permissions"""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path).resolve()
    
    def is_safe_path(self, file_path: Union[str, Path]) -> bool:
        """Check if path is safe (within base directory)"""
        try:
            path = Path(file_path).resolve()
            return path.is_relative_to(self.base_path)
        except (OSError, ValueError):
            return False
    
    def create_safe_directory(self, dir_path: Union[str, Path]) -> bool:
        """Create directory with safe permissions"""
        try:
            path = Path(dir_path)
            
            if not self.is_safe_path(path):
                raise SecurityError(f"Directory path outside safe zone: {path}")
            
            path.mkdir(parents=True, exist_ok=True, mode=0o755)
            return True
        except (OSError, SecurityError) as e:
            print(f"Failed to create directory: {e}")
            return False
    
    def write_safe_file(self, file_path: Union[str, Path], content: str) -> bool:
        """Write file with safe permissions"""
        try:
            path = Path(file_path)
            
            if not self.is_safe_path(path):
                raise SecurityError(f"File path outside safe zone: {path}")
            
            # Ensure parent directory exists
            self.create_safe_directory(path.parent)
            
            # Write file with restricted permissions
            path.write_text(content, encoding='utf-8')
            path.chmod(0o644)
            return True
        except (OSError, SecurityError) as e:
            print(f"Failed to write file: {e}")
            return False


# Global sanitizer instance
_sanitizer_instance: Optional[InputSanitizer] = None


def get_sanitizer() -> InputSanitizer:
    """Get global sanitizer instance"""
    global _sanitizer_instance
    if _sanitizer_instance is None:
        _sanitizer_instance = InputSanitizer()
    return _sanitizer_instance


if __name__ == "__main__":
    # Test security functionality
    sanitizer = InputSanitizer()
    
    print("Testing input sanitization...")
    
    # Test prompt sanitization
    test_prompts = [
        "Create a simple web application",
        "Build an API with <script>alert('xss')</script>",
        "Delete all files using rm -rf /",
        "Print 'hello world' * 10000",
        "../../../etc/passwd"
    ]
    
    for prompt in test_prompts:
        try:
            sanitized = sanitizer.sanitize_prompt(prompt)
            print(f"✅ Sanitized: '{prompt[:30]}...' -> '{sanitized[:30]}...'")
        except SecurityError as e:
            print(f"❌ Blocked: '{prompt[:30]}...' - {e}")
    
    # Test filename sanitization
    test_filenames = [
        "normal_file.txt",
        "../../../etc/passwd",
        "file<with>bad:chars.txt",
        "CON",
        "a" * 300
    ]
    
    for filename in test_filenames:
        try:
            sanitized = sanitizer.sanitize_filename(filename)
            print(f"✅ File: '{filename}' -> '{sanitized}'")
        except SecurityError as e:
            print(f"❌ File blocked: '{filename}' - {e}")
    
    # Test content safety check
    dangerous_content = "SELECT * FROM users; rm -rf /"
    warnings = sanitizer.check_content_safety(dangerous_content)
    print(f"\n⚠️  Content warnings: {warnings}")
    
    print("\nSecurity testing complete!")