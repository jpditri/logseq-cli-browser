#!/usr/bin/env python3
"""
Pytest configuration and fixtures
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import os


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory with basic structure"""
    temp_dir = tempfile.mkdtemp()
    project_path = Path(temp_dir)
    
    # Create directory structure
    (project_path / 'directives' / 'new').mkdir(parents=True)
    (project_path / 'directives' / 'success').mkdir(parents=True)
    (project_path / 'directives' / 'failed').mkdir(parents=True)
    (project_path / 'directives' / 'slow').mkdir(parents=True)
    (project_path / 'directives' / 'possible-exemplars').mkdir(parents=True)
    (project_path / 'templates').mkdir(parents=True)
    (project_path / 'lib').mkdir(parents=True)
    (project_path / 'agents').mkdir(parents=True)
    
    # Create basic template
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

## Performance Metrics
- **Tokens In**: {{TOKENS_IN}}
- **Tokens Out**: {{TOKENS_OUT}}  
- **Cost**: {{COST}}
- **Processing Time**: {{PROCESSING_TIME}}

## Output
{{OUTPUT_CONTENT}}

## Notes
{{ADDITIONAL_NOTES}}"""
    
    (project_path / 'templates' / 'directive-out.md').write_text(template_content)
    
    # Create basic settings file
    settings_content = """exemplar_threshold_seconds: 30
exemplar_enabled: true
default_platform: claude
default_model: claude-3-sonnet
verbose_logging: false"""
    
    (project_path / '.computer-settings').write_text(settings_content)
    
    yield str(project_path)
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing"""
    original_env = os.environ.copy()
    
    # Set test environment variables
    os.environ['ANTHROPIC_API_KEY'] = 'test-claude-key'
    os.environ['OPENAI_API_KEY'] = 'test-openai-key'
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def sample_directive_content():
    """Sample directive file content for testing"""
    return """---
id: test-task-123
status: pending
priority: high
created: 2024-01-01T12:00:00
slug: test-task
platform: claude
model: claude-3-sonnet
---

# Directive: Test Task

## Task Details
- **ID**: test-task-123
- **Status**: pending
- **Priority**: high
- **Created**: 2024-01-01T12:00:00

## Prerequisites
- None

## AI Requirements
- **Platform**: claude
- **Model**: claude-3-sonnet

## Prompt
# Task: Test Task

## Objective
Complete the following task: Test Task

## Priority Level
High priority

## Instructions for Completion
1. **Analysis Phase**: 
   - Break down the task into smaller components
   - Identify required resources and dependencies
   - Assess potential challenges and risks

2. **Implementation Phase**:
   - Follow best practices for the relevant domain
   - Document your approach and reasoning
   - Test your solution thoroughly

3. **Documentation Phase**:
   - Create clear documentation of what was accomplished
   - Note any assumptions made
   - Include examples where applicable

## Expected Output Format
Your output should be structured markdown that includes:
- Clear summary of what was accomplished
- Detailed explanation of the approach taken
- Any code, configurations, or artifacts created
- Testing results and validation
- Recommendations for next steps

## Success Criteria
- Task is completed as specified
- Output is well-documented and reproducible
- Quality standards are met
- Any deliverables are properly formatted

## Notes
- Ensure all work follows established conventions
- Consider maintainability and extensibility
- Document any trade-offs or decisions made

### Outputs
- Link to output: [[test-task-output_1234567890]]

## Metadata
- Type: Directive
- Category: Task Management"""


@pytest.fixture
def sample_output_content():
    """Sample output file content for testing"""
    return """---
slug: test-task
status: pending
priority: high
created: 2024-01-01T12:00:00
directive: [[test-task-123]]
tokens_in: 0
tokens_out: 0
cost: 0
processing_time: 0
---

# Test Task

## Status
- pending

## Priority  
- high

## Description
Test Task

## Directive
- Link: [[test-task-123]]

## Performance Metrics
- **Tokens In**: 0
- **Tokens Out**: 0  
- **Cost**: 0
- **Processing Time**: 0

## Output
_Output pending completion of directive_

## Notes
_No additional notes yet_"""