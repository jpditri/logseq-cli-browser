#!/usr/bin/env python3
"""
Settings loader and manager for Computer project
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from config_validator import ConfigValidator, ConfigValidationError


class Settings:
    """Settings manager with file-based configuration and environment variable overrides"""
    
    def __init__(self, base_path: str = ".", validate: bool = True):
        self.base_path = Path(base_path)
        self.settings_file = self.base_path / ".computer-settings"
        self.validator = ConfigValidator() if validate else None
        self._config = self._load_settings()
    
    def _load_settings(self) -> Dict[str, Any]:
        """Load settings from file with defaults"""
        defaults = {
            # Exemplar directive settings
            'exemplar_threshold_seconds': 30,
            'exemplar_enabled': True,
            
            # Default CLI options
            'default_platform': 'claude',
            'default_model': 'claude-3-sonnet',
            'default_parallel_threads': 2,
            'default_single_mode': False,
            
            # Processing settings
            'max_processing_time_seconds': 300,
            'retry_attempts': 3,
            'timeout_seconds': 120,
            
            # Output settings
            'verbose_logging': False,
            'include_performance_metrics': True,
            
            # Logging settings
            'log_level': 'INFO',
            'log_file': None,
            
            # Security settings
            'max_prompt_length': 10000,
            'sanitize_inputs': True,
            
            # API settings
            'api_timeout': 60,
            'api_retry_delay': 1.0,
            'rate_limit_delay': 0.5
        }
        
        if not self.settings_file.exists():
            return defaults
        
        try:
            with open(self.settings_file, 'r') as f:
                file_config = {}
                for line in f:
                    line = line.strip()
                    if line.startswith('#') or not line:
                        continue
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Type conversion
                        if value.lower() in ('true', 'false'):
                            value = value.lower() == 'true'
                        elif value.isdigit():
                            value = int(value)
                        elif '.' in value and value.replace('.', '').isdigit():
                            value = float(value)
                        
                        file_config[key] = value
                
                # Merge with defaults
                defaults.update(file_config)
                
                # Validate configuration if validator is available
                if self.validator:
                    try:
                        validated_config = self.validator.validate_and_fill_defaults(defaults)
                        return validated_config
                    except ConfigValidationError as e:
                        print(f"Configuration validation error: {e}")
                        print("Using defaults with warnings.")
                        return defaults
                
                return defaults
                
        except Exception as e:
            print(f"Warning: Error loading settings file: {e}")
            return defaults
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get setting value with environment variable override"""
        # Check environment variable first (uppercase with COMPUTER_ prefix)
        env_key = f"COMPUTER_{key.upper()}"
        env_value = os.getenv(env_key)
        
        if env_value is not None:
            # Type conversion for env vars
            if env_value.lower() in ('true', 'false'):
                return env_value.lower() == 'true'
            elif env_value.isdigit():
                return int(env_value)
            elif '.' in env_value and env_value.replace('.', '').isdigit():
                return float(env_value)
            return env_value
        
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set setting value in memory (not persisted)"""
        # Validate single field if validator is available
        if self.validator and key in self.validator.schema:
            errors = self.validator._validate_field(key, value)
            if errors:
                raise ConfigValidationError(f"Invalid value for {key}: {'; '.join(errors)}")
        
        self._config[key] = value
    
    def save(self) -> None:
        """Save current settings to file"""
        try:
            with open(self.settings_file, 'w') as f:
                f.write("# Computer Settings Configuration\n")
                f.write("# This file contains default settings for the Computer task management system\n\n")
                
                # Group settings by category
                categories = {
                    'Exemplar directive settings': [
                        'exemplar_threshold_seconds',
                        'exemplar_enabled'
                    ],
                    'Default CLI options': [
                        'default_platform',
                        'default_model', 
                        'default_parallel_threads',
                        'default_single_mode'
                    ],
                    'Processing settings': [
                        'max_processing_time_seconds',
                        'retry_attempts',
                        'timeout_seconds'
                    ],
                    'Output settings': [
                        'verbose_logging',
                        'include_performance_metrics'
                    ]
                }
                
                for category, keys in categories.items():
                    f.write(f"\n# {category}\n")
                    for key in keys:
                        if key in self._config:
                            f.write(f"{key}: {self._config[key]}\n")
                
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def update_from_dict(self, updates: Dict[str, Any]) -> None:
        """Update multiple settings from dictionary"""
        # Validate all updates if validator is available
        if self.validator:
            errors = self.validator.validate_config(updates)
            if errors:
                raise ConfigValidationError(f"Invalid configuration: {'; '.join(errors)}")
        
        self._config.update(updates)
    
    def to_dict(self) -> Dict[str, Any]:
        """Return all settings as dictionary"""
        return self._config.copy()
    
    def reset_to_defaults(self) -> None:
        """Reset all settings to default values"""
        if self.validator:
            self._config = self.validator.get_default_config()
        else:
            self._config = self._load_settings()
    
    def validate_current_config(self) -> List[str]:
        """Validate current configuration and return errors"""
        if not self.validator:
            return ["Validation not available (validator disabled)"]
        
        return self.validator.validate_config(self._config)
    
    def get_schema_documentation(self) -> str:
        """Get configuration schema documentation"""
        if not self.validator:
            return "Schema documentation not available (validator disabled)"
        
        return self.validator.get_schema_documentation()
    
    def validate_platform_model(self, platform: str, model: str) -> bool:
        """Validate platform and model combination"""
        if not self.validator:
            return True  # Skip validation if not available
        
        return self.validator.validate_model_name(platform, model)


# Global settings instance
_settings_instance: Optional[Settings] = None


def get_settings(base_path: str = ".") -> Settings:
    """Get global settings instance"""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings(base_path)
    return _settings_instance


def reload_settings(base_path: str = ".") -> Settings:
    """Reload settings from file"""
    global _settings_instance
    _settings_instance = Settings(base_path)
    return _settings_instance


if __name__ == "__main__":
    # Test settings functionality
    settings = Settings()
    print("Current settings:")
    for key, value in settings.to_dict().items():
        print(f"  {key}: {value}")
    
    print(f"\nExemplar threshold: {settings.get('exemplar_threshold_seconds')} seconds")
    print(f"Default platform: {settings.get('default_platform')}")
    print(f"Verbose logging: {settings.get('verbose_logging')}")