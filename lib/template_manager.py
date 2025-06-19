#!/usr/bin/env python3
"""
Template management system for Computer project
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from dataclasses import dataclass, asdict
import yaml


@dataclass
class TemplateMetadata:
    """Metadata for a template"""
    name: str
    description: str
    category: str
    version: str = "1.0"
    author: str = "Computer"
    created: str = ""
    variables: List[str] = None
    
    def __post_init__(self):
        if not self.created:
            self.created = datetime.now().isoformat()
        if self.variables is None:
            self.variables = []


class TemplateEngine:
    """Template processing engine with variable substitution"""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.templates_path = self.base_path / "templates"
        self.user_templates_path = self.base_path / "templates" / "user"
        
        # Ensure template directories exist
        self.templates_path.mkdir(parents=True, exist_ok=True)
        self.user_templates_path.mkdir(parents=True, exist_ok=True)
        
        # Template variable pattern: {{VARIABLE_NAME}}
        self.variable_pattern = re.compile(r'\{\{([A-Z_][A-Z0-9_]*)\}\}')
    
    def get_available_templates(self) -> Dict[str, TemplateMetadata]:
        """Get all available templates with metadata"""
        templates = {}
        
        # Scan system templates
        for template_file in self.templates_path.glob("*.md"):
            if template_file.name.startswith('.'):
                continue
            
            metadata = self._extract_template_metadata(template_file)
            if metadata:
                templates[template_file.stem] = metadata
        
        # Scan user templates
        for template_file in self.user_templates_path.glob("*.md"):
            if template_file.name.startswith('.'):
                continue
            
            metadata = self._extract_template_metadata(template_file)
            if metadata:
                templates[f"user:{template_file.stem}"] = metadata
        
        return templates
    
    def _extract_template_metadata(self, template_file: Path) -> Optional[TemplateMetadata]:
        """Extract metadata from template file"""
        try:
            content = template_file.read_text()
            
            # Look for YAML frontmatter
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    try:
                        frontmatter = yaml.safe_load(parts[1])
                        if isinstance(frontmatter, dict):
                            # Extract variables from template content
                            variables = list(set(self.variable_pattern.findall(parts[2])))
                            
                            return TemplateMetadata(
                                name=frontmatter.get('name', template_file.stem),
                                description=frontmatter.get('description', 'No description'),
                                category=frontmatter.get('category', 'general'),
                                version=frontmatter.get('version', '1.0'),
                                author=frontmatter.get('author', 'Unknown'),
                                created=frontmatter.get('created', ''),
                                variables=variables
                            )
                    except yaml.YAMLError:
                        pass
            
            # Fallback: extract variables from content
            variables = list(set(self.variable_pattern.findall(content)))
            
            return TemplateMetadata(
                name=template_file.stem.replace('-', ' ').title(),
                description=f"Template: {template_file.stem}",
                category="general",
                variables=variables
            )
            
        except Exception as e:
            print(f"Error reading template {template_file}: {e}")
            return None
    
    def render_template(self, template_name: str, variables: Dict[str, Any]) -> str:
        """Render template with provided variables"""
        template_content = self.load_template(template_name)
        if not template_content:
            raise ValueError(f"Template '{template_name}' not found")
        
        # Perform variable substitution
        rendered = template_content
        
        for var_name, value in variables.items():
            pattern = f"{{{{{var_name.upper()}}}}}"
            rendered = rendered.replace(pattern, str(value))
        
        # Check for remaining unsubstituted variables
        remaining_vars = self.variable_pattern.findall(rendered)
        if remaining_vars:
            print(f"Warning: Unsubstituted variables: {remaining_vars}")
        
        return rendered
    
    def load_template(self, template_name: str) -> Optional[str]:
        """Load template content"""
        # Handle user templates
        if template_name.startswith('user:'):
            template_file = self.user_templates_path / f"{template_name[5:]}.md"
        else:
            template_file = self.templates_path / f"{template_name}.md"
        
        if not template_file.exists():
            return None
        
        try:
            content = template_file.read_text()
            
            # Keep the full content including YAML frontmatter
            # The frontmatter contains template variables that need substitution
            return content
        except Exception as e:
            print(f"Error loading template {template_file}: {e}")
            return None
    
    def create_template(self, name: str, content: str, metadata: TemplateMetadata, 
                       user_template: bool = True) -> bool:
        """Create a new template"""
        try:
            # Determine template path
            if user_template:
                template_file = self.user_templates_path / f"{name}.md"
            else:
                template_file = self.templates_path / f"{name}.md"
            
            # Extract variables from content
            variables = list(set(self.variable_pattern.findall(content)))
            metadata.variables = variables
            
            # Create template with frontmatter
            frontmatter = yaml.dump(asdict(metadata), default_flow_style=False)
            template_content = f"---\n{frontmatter}---\n\n{content}"
            
            template_file.write_text(template_content)
            return True
            
        except Exception as e:
            print(f"Error creating template: {e}")
            return False
    
    def delete_template(self, template_name: str) -> bool:
        """Delete a template (user templates only)"""
        if not template_name.startswith('user:'):
            print("Can only delete user templates")
            return False
        
        template_file = self.user_templates_path / f"{template_name[5:]}.md"
        
        if not template_file.exists():
            print(f"Template {template_name} not found")
            return False
        
        try:
            template_file.unlink()
            return True
        except Exception as e:
            print(f"Error deleting template: {e}")
            return False
    
    def validate_template(self, content: str) -> List[str]:
        """Validate template content and return issues"""
        issues = []
        
        # Check for valid variable syntax
        variables = self.variable_pattern.findall(content)
        
        # Check for malformed variables
        malformed = re.findall(r'\{[^}]*\}|\{[^{]*\{\{', content)
        for match in malformed:
            if not self.variable_pattern.match(match):
                issues.append(f"Malformed variable syntax: {match}")
        
        # Check for reserved variables
        reserved_vars = {
            'SYSTEM', 'ROOT', 'HOME', 'PATH', 'USER', 'ADMIN',
            'PASSWORD', 'SECRET', 'KEY', 'TOKEN'
        }
        
        for var in variables:
            if var in reserved_vars:
                issues.append(f"Reserved variable name: {var}")
        
        # Check for potentially dangerous content
        dangerous_patterns = [
            r'<script[^>]*>',
            r'javascript:',
            r'eval\s*\(',
            r'exec\s*\(',
            r'__import__'
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                issues.append(f"Potentially dangerous content: {pattern}")
        
        return issues


class TemplateLibrary:
    """Library of built-in templates"""
    
    @staticmethod
    def get_built_in_templates() -> Dict[str, Dict[str, Any]]:
        """Get built-in template definitions"""
        return {
            'directive-out': {
                'metadata': TemplateMetadata(
                    name="Directive Output",
                    description="Standard directive output template with performance metrics",
                    category="system",
                    author="Computer System"
                ),
                'content': """---
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
            },
            
            'directive-prompt': {
                'metadata': TemplateMetadata(
                    name="Directive Prompt",
                    description="Standard directive prompt template",
                    category="system",
                    author="Computer System"
                ),
                'content': """# Task: {{TASK_CONTENT}}

## Objective
Complete the following task: {{TASK_CONTENT}}

## Priority Level
{{PRIORITY_LEVEL}} priority

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
- Document any trade-offs or decisions made"""
            },
            
            'api-project': {
                'metadata': TemplateMetadata(
                    name="API Project",
                    description="Template for API development projects",
                    category="development",
                    author="Computer System"
                ),
                'content': """# API Development: {{PROJECT_NAME}}

## Project Overview
Create a {{API_TYPE}} API for {{PROJECT_DESCRIPTION}}

## Requirements
- **Framework**: {{FRAMEWORK}}
- **Database**: {{DATABASE}}
- **Authentication**: {{AUTH_METHOD}}
- **Documentation**: {{DOC_FORMAT}}

## Implementation Tasks
1. Set up project structure
2. Configure database connections
3. Implement core endpoints:
   {{#ENDPOINTS}}
   - {{METHOD}} {{PATH}} - {{DESCRIPTION}}
   {{/ENDPOINTS}}
4. Add authentication and authorization
5. Write comprehensive tests
6. Generate API documentation
7. Deploy to {{DEPLOYMENT_TARGET}}

## Success Criteria
- All endpoints working correctly
- Test coverage > 80%
- API documentation complete
- Security best practices followed
- Performance requirements met

## Deliverables
- Source code repository
- API documentation
- Test suite
- Deployment instructions"""
            },
            
            'code-review': {
                'metadata': TemplateMetadata(
                    name="Code Review",
                    description="Template for code review tasks",
                    category="development",
                    author="Computer System"
                ),
                'content': """# Code Review: {{COMPONENT_NAME}}

## Review Scope
- **Component**: {{COMPONENT_NAME}}
- **Files**: {{FILE_LIST}}
- **Author**: {{AUTHOR}}
- **Purpose**: {{PURPOSE}}

## Review Checklist
### Code Quality
- [ ] Follows project coding standards
- [ ] Functions are well-named and documented
- [ ] Code is DRY (Don't Repeat Yourself)
- [ ] Complex logic is commented
- [ ] Error handling is appropriate

### Security
- [ ] Input validation implemented
- [ ] No hardcoded secrets or credentials
- [ ] SQL injection prevention
- [ ] XSS protection where applicable
- [ ] Authentication/authorization correct

### Performance
- [ ] No obvious performance bottlenecks
- [ ] Database queries optimized
- [ ] Caching used appropriately
- [ ] Memory usage reasonable

### Testing
- [ ] Unit tests cover new functionality
- [ ] Integration tests where needed
- [ ] Edge cases tested
- [ ] Mock objects used appropriately

## Findings
{{REVIEW_FINDINGS}}

## Recommendations
{{RECOMMENDATIONS}}

## Approval Status
- [ ] Approved
- [ ] Approved with minor changes
- [ ] Requires changes
- [ ] Rejected"""
            }
        }
    
    @staticmethod
    def install_built_in_templates(template_engine: TemplateEngine) -> int:
        """Install all built-in templates"""
        templates = TemplateLibrary.get_built_in_templates()
        installed = 0
        
        for name, template_def in templates.items():
            template_file = template_engine.templates_path / f"{name}.md"
            
            # Skip if already exists
            if template_file.exists():
                continue
            
            success = template_engine.create_template(
                name, 
                template_def['content'], 
                template_def['metadata'],
                user_template=False
            )
            
            if success:
                installed += 1
        
        return installed


# Global template engine instance
_template_engine: Optional[TemplateEngine] = None


def get_template_engine(base_path: str = ".") -> TemplateEngine:
    """Get global template engine instance"""
    global _template_engine
    if _template_engine is None:
        _template_engine = TemplateEngine(base_path)
    return _template_engine


if __name__ == "__main__":
    # Test template functionality
    engine = TemplateEngine(".")
    
    print("Testing template engine...")
    
    # Install built-in templates
    installed = TemplateLibrary.install_built_in_templates(engine)
    print(f"Installed {installed} built-in templates")
    
    # List available templates
    templates = engine.get_available_templates()
    print(f"\nAvailable templates ({len(templates)}):")
    for name, metadata in templates.items():
        print(f"  - {name}: {metadata.description}")
        print(f"    Variables: {metadata.variables}")
    
    # Test template rendering
    if 'directive-prompt' in templates:
        variables = {
            'TASK_CONTENT': 'Create a user authentication system',
            'PRIORITY_LEVEL': 'High'
        }
        
        rendered = engine.render_template('directive-prompt', variables)
        print(f"\nRendered template preview:")
        print(rendered[:200] + "...")
    
    # Test template validation
    test_content = "Hello {{USER_NAME}}, your {{INVALID{}} template has {{DANGEROUS_SCRIPT}}"
    issues = engine.validate_template(test_content)
    print(f"\nValidation issues: {issues}")
    
    print("\nTemplate engine test complete!")