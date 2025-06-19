#!/usr/bin/env python3
"""
Tests for directive agent module
"""

import pytest
import tempfile
import sys
from pathlib import Path

# Add agents to path
sys.path.insert(0, str(Path(__file__).parent.parent / "agents"))
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from directive_agent import DirectiveAgent


class TestDirectiveAgent:
    def test_create_slug(self):
        """Test slug creation from content"""
        agent = DirectiveAgent()
        
        assert agent.create_slug("Create a new feature") == "create-a-new-feature"
        assert agent.create_slug("Test with special chars!@#") == "test-with-special-chars"
        assert agent.create_slug("Very long string that should be truncated" * 10)[:50]
    
    def test_analyze_prompt_single_task(self):
        """Test prompt analysis for single task"""
        agent = DirectiveAgent()
        
        prompt = "Create a new user authentication system"
        todos = agent.analyze_prompt(prompt)
        
        assert len(todos) == 1
        assert todos[0]['content'] == prompt
        assert todos[0]['status'] == 'pending'
        assert todos[0]['priority'] == 'medium'
    
    def test_analyze_prompt_multiple_tasks(self):
        """Test prompt analysis for multiple tasks"""
        agent = DirectiveAgent()
        
        prompt = "Create a user system. Build the API endpoints. Test everything thoroughly."
        todos = agent.analyze_prompt(prompt)
        
        assert len(todos) == 3
        assert any('Create a user system' in todo['content'] for todo in todos)
        assert any('Build the API endpoints' in todo['content'] for todo in todos)
        assert any('Test everything thoroughly' in todo['content'] for todo in todos)
    
    def test_analyze_prompt_with_priorities(self):
        """Test prompt analysis with priority keywords"""
        agent = DirectiveAgent()
        
        prompt = "This is urgent! Create the API. Later, add documentation."
        todos = agent.analyze_prompt(prompt)
        
        # Find the urgent task
        urgent_task = next((todo for todo in todos if 'urgent' in todo['content'].lower()), None)
        assert urgent_task is not None
        assert urgent_task['priority'] == 'high'
        
        # Find the later task
        later_task = next((todo for todo in todos if 'later' in todo['content'].lower()), None)
        assert later_task is not None
        assert later_task['priority'] == 'low'
    
    def test_create_detailed_prompt(self):
        """Test detailed prompt creation"""
        agent = DirectiveAgent()
        
        todo = {
            'id': 'test-123',
            'content': 'Create user authentication',
            'priority': 'high'
        }
        
        detailed = agent.create_detailed_prompt(todo)
        
        assert 'Create user authentication' in detailed
        assert 'High priority' in detailed
        assert 'Analysis Phase' in detailed
        assert 'Implementation Phase' in detailed
        assert 'Documentation Phase' in detailed
    
    def test_file_creation(self):
        """Test directive and output file creation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = DirectiveAgent(temp_dir)
            
            # Create template directory and file
            templates_dir = Path(temp_dir) / 'templates'
            templates_dir.mkdir(exist_ok=True)
            
            template_content = """---
slug: {{TASK_SLUG}}
status: {{STATUS}}
priority: {{PRIORITY}}
created: {{CREATED_DATE}}
directive: [[{{DIRECTIVE_FILE}}]]
tokens_in: {{TOKENS_IN}}
tokens_out: {{TOKENS_OUT}}
cost: {{COST}}
processing_time: {{PROCESSING_TIME}}
---

# {{TASK_TITLE}}

## Status
- {{STATUS}}

## Priority  
- {{PRIORITY}}

## Description
{{TASK_DESCRIPTION}}

## Directive
- Link: [[{{DIRECTIVE_FILE}}]]

## Performance Metrics
- **Tokens In**: {{TOKENS_IN}}
- **Tokens Out**: {{TOKENS_OUT}}  
- **Cost**: {{COST}}
- **Processing Time**: {{PROCESSING_TIME}}

## Output
{{OUTPUT_CONTENT}}

## Notes
{{ADDITIONAL_NOTES}}"""
            
            (templates_dir / 'directive-out.md').write_text(template_content)
            
            # Process a simple prompt
            result = agent.process_prompt("Create a test feature", platform="claude", model="claude-3-sonnet")
            
            assert len(result['todos']) >= 1
            assert len(result['files_created']['directives']) >= 1
            assert len(result['files_created']['outputs']) >= 1
            
            # Check that files were actually created
            directives_dir = Path(temp_dir) / 'directives' / 'new'
            assert directives_dir.exists()
            
            directive_files = list(directives_dir.glob('*.md'))
            assert len(directive_files) >= 2  # At least directive + output file
            
            # Check file content
            directive_file = next(f for f in directive_files if 'output' not in f.name)
            content = directive_file.read_text()
            
            assert 'Create a test feature' in content
            assert 'platform: claude' in content
            assert 'model: claude-3-sonnet' in content
    
    def test_prerequisites_handling(self):
        """Test prerequisite dependency handling"""
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = DirectiveAgent(temp_dir)
            
            # Create template
            templates_dir = Path(temp_dir) / 'templates'
            templates_dir.mkdir(exist_ok=True)
            (templates_dir / 'directive-out.md').write_text("Basic template: {{TASK_TITLE}}")
            
            # Process multiple task prompt
            prompt = "First create the database. Then build the API. Finally add the frontend."
            result = agent.process_prompt(prompt)
            
            assert len(result['todos']) == 3
            
            # Check that directive files exist
            directives_dir = Path(temp_dir) / 'directives' / 'new'
            directive_files = list(directives_dir.glob('*directive*.md'))
            
            # Should have prerequisites in later tasks
            if len(directive_files) >= 2:
                # Read second directive file (should have prerequisites)
                second_file = sorted(directive_files)[1]
                content = second_file.read_text()
                assert 'Prerequisites' in content


if __name__ == "__main__":
    pytest.main([__file__, '-v'])