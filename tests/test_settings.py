#!/usr/bin/env python3
"""
Tests for settings module
"""

import pytest
import os
import tempfile
from pathlib import Path
import sys

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
from settings import Settings


class TestSettings:
    def test_default_settings(self):
        """Test default settings are loaded correctly"""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(temp_dir)
            
            assert settings.get('exemplar_threshold_seconds') == 30
            assert settings.get('default_platform') == 'claude'
            assert settings.get('verbose_logging') is False
    
    def test_file_loading(self):
        """Test loading settings from file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / '.computer-settings'
            settings_file.write_text("""
# Test settings
exemplar_threshold_seconds: 45
default_platform: openai
verbose_logging: true
            """)
            
            settings = Settings(temp_dir)
            
            assert settings.get('exemplar_threshold_seconds') == 45
            assert settings.get('default_platform') == 'openai'
            assert settings.get('verbose_logging') is True
    
    def test_environment_override(self):
        """Test environment variable overrides"""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ['COMPUTER_DEFAULT_PLATFORM'] = 'claude'
            os.environ['COMPUTER_EXEMPLAR_THRESHOLD_SECONDS'] = '60'
            
            try:
                settings = Settings(temp_dir)
                
                assert settings.get('default_platform') == 'claude'
                assert settings.get('exemplar_threshold_seconds') == 60
            finally:
                # Clean up environment
                os.environ.pop('COMPUTER_DEFAULT_PLATFORM', None)
                os.environ.pop('COMPUTER_EXEMPLAR_THRESHOLD_SECONDS', None)
    
    def test_type_conversion(self):
        """Test proper type conversion from file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / '.computer-settings'
            settings_file.write_text("""
int_value: 42
float_value: 3.14
bool_true: true
bool_false: false
string_value: hello
            """)
            
            settings = Settings(temp_dir)
            
            assert settings.get('int_value') == 42
            assert settings.get('float_value') == 3.14
            assert settings.get('bool_true') is True
            assert settings.get('bool_false') is False
            assert settings.get('string_value') == 'hello'
    
    def test_set_and_save(self):
        """Test setting values and saving to file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(temp_dir)
            
            settings.set('test_key', 'test_value')
            assert settings.get('test_key') == 'test_value'
            
            settings.save()
            
            # Load new instance to verify persistence
            new_settings = Settings(temp_dir)
            assert new_settings.get('test_key') == 'test_value'


if __name__ == "__main__":
    pytest.main([__file__, '-v'])