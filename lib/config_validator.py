#!/usr/bin/env python3
"""
Configuration validation and schema for Computer project
"""

import re
from typing import Dict, Any, List, Optional, Union
from pathlib import Path


class ConfigValidationError(Exception):
    """Exception raised for configuration validation errors"""
    pass


class ConfigValidator:
    """Validates configuration settings and provides schema validation"""
    
    def __init__(self):
        self.schema = self._define_schema()
    
    def _define_schema(self) -> Dict[str, Dict[str, Any]]:
        """Define the configuration schema"""
        return {
            # Exemplar directive settings
            'exemplar_threshold_seconds': {
                'type': int,
                'min': 1,
                'max': 3600,
                'default': 30,
                'description': 'Threshold in seconds for marking directives as exemplars'
            },
            'exemplar_enabled': {
                'type': bool,
                'default': True,
                'description': 'Enable/disable exemplar directive detection'
            },
            
            # Default CLI options
            'default_platform': {
                'type': str,
                'choices': ['claude', 'openai', 'auto'],
                'default': 'claude',
                'description': 'Default AI platform to use'
            },
            'default_model': {
                'type': str,
                'default': 'claude-3-sonnet',
                'description': 'Default AI model to use'
            },
            'default_parallel_threads': {
                'type': int,
                'min': 1,
                'max': 16,
                'default': 2,
                'description': 'Default number of parallel processing threads'
            },
            'default_single_mode': {
                'type': bool,
                'default': False,
                'description': 'Default to single directive processing mode'
            },
            
            # Processing settings
            'max_processing_time_seconds': {
                'type': int,
                'min': 10,
                'max': 3600,
                'default': 300,
                'description': 'Maximum processing time per directive in seconds'
            },
            'retry_attempts': {
                'type': int,
                'min': 1,
                'max': 10,
                'default': 3,
                'description': 'Number of retry attempts for failed operations'
            },
            'timeout_seconds': {
                'type': int,
                'min': 10,
                'max': 600,
                'default': 120,
                'description': 'Timeout for individual operations in seconds'
            },
            
            # Output settings
            'verbose_logging': {
                'type': bool,
                'default': False,
                'description': 'Enable verbose logging output'
            },
            'include_performance_metrics': {
                'type': bool,
                'default': True,
                'description': 'Include performance metrics in output files'
            },
            
            # Logging settings
            'log_level': {
                'type': str,
                'choices': ['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                'default': 'INFO',
                'description': 'Logging level'
            },
            'log_file': {
                'type': str,
                'optional': True,
                'description': 'Log file path (optional)'
            },
            
            # Security settings
            'max_prompt_length': {
                'type': int,
                'min': 100,
                'max': 100000,
                'default': 10000,
                'description': 'Maximum allowed prompt length in characters'
            },
            'sanitize_inputs': {
                'type': bool,
                'default': True,
                'description': 'Enable input sanitization'
            },
            
            # API settings
            'api_timeout': {
                'type': int,
                'min': 10,
                'max': 300,
                'default': 60,
                'description': 'API request timeout in seconds'
            },
            'api_retry_delay': {
                'type': float,
                'min': 0.1,
                'max': 10.0,
                'default': 1.0,
                'description': 'Initial delay between API retry attempts'
            },
            'rate_limit_delay': {
                'type': float,
                'min': 0.1,
                'max': 5.0,
                'default': 0.5,
                'description': 'Delay between API calls to avoid rate limiting'
            }
        }
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate configuration against schema, return list of errors"""
        errors = []
        
        for key, value in config.items():
            if key not in self.schema:
                errors.append(f"Unknown configuration key: {key}")
                continue
            
            field_errors = self._validate_field(key, value)
            errors.extend(field_errors)
        
        return errors
    
    def _validate_field(self, key: str, value: Any) -> List[str]:
        """Validate a single field against its schema"""
        errors = []
        schema = self.schema[key]
        
        # Type validation
        expected_type = schema['type']
        if not isinstance(value, expected_type):
            errors.append(f"{key}: Expected {expected_type.__name__}, got {type(value).__name__}")
            return errors  # Stop validation if type is wrong
        
        # Choice validation
        if 'choices' in schema and value not in schema['choices']:
            errors.append(f"{key}: Must be one of {schema['choices']}, got '{value}'")
        
        # Numeric range validation
        if expected_type in (int, float):
            if 'min' in schema and value < schema['min']:
                errors.append(f"{key}: Must be >= {schema['min']}, got {value}")
            if 'max' in schema and value > schema['max']:
                errors.append(f"{key}: Must be <= {schema['max']}, got {value}")
        
        # String validation
        if expected_type == str:
            if 'pattern' in schema:
                pattern = schema['pattern']
                if not re.match(pattern, value):
                    errors.append(f"{key}: Must match pattern {pattern}, got '{value}'")
            
            if key == 'log_file' and value:
                # Validate log file path
                try:
                    log_path = Path(value)
                    if not log_path.parent.exists():
                        errors.append(f"{key}: Parent directory does not exist: {log_path.parent}")
                except Exception as e:
                    errors.append(f"{key}: Invalid file path: {e}")
        
        return errors
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration values"""
        config = {}
        for key, schema in self.schema.items():
            if 'default' in schema:
                config[key] = schema['default']
        return config
    
    def validate_and_fill_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate config and fill in missing defaults"""
        errors = self.validate_config(config)
        if errors:
            raise ConfigValidationError(f"Configuration validation failed:\n" + "\n".join(errors))
        
        # Fill in defaults for missing keys
        result = self.get_default_config()
        result.update(config)
        
        return result
    
    def get_schema_documentation(self) -> str:
        """Generate documentation for the configuration schema"""
        doc = "# Computer Configuration Schema\n\n"
        doc += "The following configuration options are available:\n\n"
        
        categories = {
            'Exemplar Settings': ['exemplar_threshold_seconds', 'exemplar_enabled'],
            'CLI Defaults': ['default_platform', 'default_model', 'default_parallel_threads', 'default_single_mode'],
            'Processing': ['max_processing_time_seconds', 'retry_attempts', 'timeout_seconds'],
            'Output': ['verbose_logging', 'include_performance_metrics'],
            'Logging': ['log_level', 'log_file'],
            'Security': ['max_prompt_length', 'sanitize_inputs'],
            'API': ['api_timeout', 'api_retry_delay', 'rate_limit_delay']
        }
        
        for category, keys in categories.items():
            doc += f"## {category}\n\n"
            for key in keys:
                if key in self.schema:
                    schema = self.schema[key]
                    doc += f"### `{key}`\n"
                    doc += f"- **Type**: {schema['type'].__name__}\n"
                    if 'default' in schema:
                        doc += f"- **Default**: {schema['default']}\n"
                    if 'choices' in schema:
                        doc += f"- **Choices**: {', '.join(str(c) for c in schema['choices'])}\n"
                    if 'min' in schema or 'max' in schema:
                        range_info = []
                        if 'min' in schema:
                            range_info.append(f"min: {schema['min']}")
                        if 'max' in schema:
                            range_info.append(f"max: {schema['max']}")
                        doc += f"- **Range**: {', '.join(range_info)}\n"
                    doc += f"- **Description**: {schema['description']}\n\n"
        
        return doc
    
    def validate_model_name(self, platform: str, model: str) -> bool:
        """Validate model name for given platform"""
        valid_models = {
            'claude': [
                'claude-3-opus-20240229',
                'claude-3-sonnet-20240229', 
                'claude-3-haiku-20240307',
                'claude-3-opus',
                'claude-3-sonnet',
                'claude-3-haiku'
            ],
            'openai': [
                'gpt-4',
                'gpt-4-turbo',
                'gpt-4-turbo-preview',
                'gpt-3.5-turbo',
                'gpt-3.5-turbo-1106',
                'gpt-4-1106-preview'
            ]
        }
        
        platform_models = valid_models.get(platform.lower(), [])
        return model in platform_models or any(model.startswith(m) for m in platform_models)
    
    def suggest_fixes(self, errors: List[str]) -> List[str]:
        """Suggest fixes for validation errors"""
        suggestions = []
        
        for error in errors:
            if "Unknown configuration key" in error:
                key = error.split(": ")[1]
                # Find similar keys
                similar = [k for k in self.schema.keys() if k.lower().find(key.lower()) != -1]
                if similar:
                    suggestions.append(f"Did you mean one of: {', '.join(similar)}?")
            
            elif "Must be one of" in error:
                suggestions.append("Check the valid choices listed in the error message")
            
            elif "Must be >=" in error or "Must be <=" in error:
                suggestions.append("Adjust the value to be within the allowed range")
            
            elif "Expected" in error and "got" in error:
                suggestions.append("Check the data type - ensure booleans are true/false, numbers don't have quotes")
        
        return suggestions


if __name__ == "__main__":
    # Test configuration validation
    validator = ConfigValidator()
    
    # Test valid config
    valid_config = {
        'exemplar_threshold_seconds': 45,
        'default_platform': 'claude',
        'verbose_logging': True
    }
    
    print("Testing valid config...")
    errors = validator.validate_config(valid_config)
    if errors:
        print(f"Unexpected errors: {errors}")
    else:
        print("✅ Valid config passed")
    
    # Test invalid config
    invalid_config = {
        'exemplar_threshold_seconds': 'not_a_number',
        'default_platform': 'invalid_platform',
        'unknown_key': 'some_value'
    }
    
    print("\nTesting invalid config...")
    errors = validator.validate_config(invalid_config)
    if errors:
        print("❌ Found expected errors:")
        for error in errors:
            print(f"  - {error}")
        
        suggestions = validator.suggest_fixes(errors)
        if suggestions:
            print("\n💡 Suggestions:")
            for suggestion in suggestions:
                print(f"  - {suggestion}")
    
    # Generate documentation
    print("\n" + "="*50)
    print("CONFIGURATION DOCUMENTATION")
    print("="*50)
    print(validator.get_schema_documentation())