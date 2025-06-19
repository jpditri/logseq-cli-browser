#!/usr/bin/env python3
"""
Directive Agent - Creates todo lists and logseq-style directive files from prompts
"""

import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import sys

# Add lib to path for logging, security, and templates
sys.path.append(str(Path(__file__).parent.parent / "lib"))
from logger import get_logger
from security import get_sanitizer, SecurityError
from settings import get_settings
from template_manager import get_template_engine, TemplateLibrary
from todo_directive_bridge import TodoDirectiveBridge


class DirectiveAgent:
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.directives_path = self.base_path / "directives" / "new"
        self.templates_path = self.base_path / "templates"
        self.directives_path.mkdir(parents=True, exist_ok=True)
        self.templates_path.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger("directive_agent", base_path)
        self.sanitizer = get_sanitizer()
        self.settings = get_settings(base_path)
        self.template_engine = get_template_engine(base_path)
        
        # Install built-in templates if needed
        TemplateLibrary.install_built_in_templates(self.template_engine)
        
        # Initialize todo-directive bridge
        self.todo_bridge = TodoDirectiveBridge(str(self.base_path / "directives"))
    
    def create_slug(self, content: str) -> str:
        """Create a URL-friendly slug from content"""
        # Use secure ID generation if available
        if hasattr(self, 'sanitizer'):
            return self.sanitizer.generate_safe_id(content, "directive")
        
        # Fallback to original method
        slug = re.sub(r'[^\w\s-]', '', content.lower())
        slug = re.sub(r'[-\s]+', '-', slug)
        return slug[:50].strip('-')
    
    def analyze_prompt(self, prompt: str, use_llm: bool = False, platform: str = None, model: str = None) -> List[Dict[str, Any]]:
        """Analyze prompt and break it down into todo items"""
        
        # Use LLM decomposition if requested and available
        if use_llm and (platform or model):
            try:
                return self._llm_decompose_prompt(prompt, platform, model)
            except Exception as e:
                self.logger.warning(f"LLM decomposition failed, falling back to heuristic: {e}")
        
        # Fallback to heuristic method
        return self._heuristic_analyze_prompt(prompt)
    
    def _llm_decompose_prompt(self, prompt: str, platform: str = None, model: str = None) -> List[Dict[str, Any]]:
        """Use LLM to decompose prompt into structured todos"""
        # This would integrate with AI client if available
        # For now, provide enhanced heuristic analysis that mimics LLM thinking
        
        decomposition_prompt = f"""
Analyze the following prompt and break it down into specific, actionable todo items.
Each todo should be:
1. A single, clear action
2. Assigned appropriate priority (high/medium/low)
3. Logically ordered with dependencies

Original prompt: {prompt}

Please structure your response as a JSON array of todo objects with fields:
- id: unique identifier
- content: clear task description
- priority: high/medium/low
- dependencies: array of prerequisite task IDs (if any)

Focus on breaking complex tasks into manageable steps while preserving the overall goal.
"""
        
        # Enhanced heuristic that considers logical task breakdown
        return self._enhanced_heuristic_analysis(prompt)
    
    def _enhanced_heuristic_analysis(self, prompt: str) -> List[Dict[str, Any]]:
        """Enhanced heuristic analysis that mimics LLM thinking"""
        todos = []
        prompt_lower = prompt.lower()
        
        # Detect if this is a multi-step project
        complexity_indicators = ['system', 'application', 'project', 'platform', 'api', 'database', 'frontend', 'backend']
        is_complex = any(indicator in prompt_lower for indicator in complexity_indicators)
        
        if is_complex:
            # Break down complex projects into phases
            phases = []
            
            # Analysis phase
            if any(word in prompt_lower for word in ['new', 'create', 'build', 'develop']):
                phases.append({
                    "content": f"Analyze requirements and plan architecture for: {prompt[:50]}...",
                    "priority": "high"
                })
            
            # Implementation phases based on content
            if 'database' in prompt_lower or 'data' in prompt_lower:
                phases.append({
                    "content": "Design and implement database schema and models",
                    "priority": "high"
                })
            
            if 'api' in prompt_lower or 'backend' in prompt_lower:
                phases.append({
                    "content": "Implement backend API endpoints and business logic",
                    "priority": "high"
                })
            
            if 'frontend' in prompt_lower or 'ui' in prompt_lower or 'interface' in prompt_lower:
                phases.append({
                    "content": "Create frontend user interface and components",
                    "priority": "medium"
                })
            
            if 'test' in prompt_lower or phases:  # Add testing if phases exist
                phases.append({
                    "content": "Write comprehensive tests for all components",
                    "priority": "medium"
                })
            
            if 'deploy' in prompt_lower or phases:  # Add deployment if phases exist
                phases.append({
                    "content": "Deploy and configure production environment",
                    "priority": "low"
                })
            
            # Convert phases to todos
            for i, phase in enumerate(phases):
                todo_id = f"task-{uuid.uuid4().hex[:8]}"
                todos.append({
                    "id": todo_id,
                    "content": phase["content"],
                    "status": "pending",
                    "priority": phase["priority"]
                })
        
        # If no complex breakdown or additional specific tasks
        if not todos:
            todos = self._heuristic_analyze_prompt(prompt)
        
        return todos
    
    def _heuristic_analyze_prompt(self, prompt: str) -> List[Dict[str, Any]]:
        """Original heuristic analysis method"""
        # Simple heuristic: split by sentences and look for action words
        sentences = re.split(r'[.!?]+', prompt)
        todos = []
        
        action_words = ['create', 'build', 'implement', 'write', 'develop', 'design', 'test', 'deploy', 'fix', 'update', 'add', 'remove']
        
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Determine priority based on keywords
            priority = "medium"
            if any(word in sentence.lower() for word in ['urgent', 'critical', 'important', 'asap']):
                priority = "high"
            elif any(word in sentence.lower() for word in ['later', 'eventually', 'optional', 'nice to have']):
                priority = "low"
            
            # Check if sentence contains action words
            has_action = any(word in sentence.lower() for word in action_words)
            
            if has_action or len(sentence) > 10:  # Include substantial sentences
                todo_id = f"task-{uuid.uuid4().hex[:8]}"
                todos.append({
                    "id": todo_id,
                    "content": sentence.strip(),
                    "status": "pending",
                    "priority": priority
                })
        
        # If no todos found, create one from the whole prompt
        if not todos:
            todo_id = f"task-{uuid.uuid4().hex[:8]}"
            todos.append({
                "id": todo_id,
                "content": prompt.strip(),
                "status": "pending", 
                "priority": "medium"
            })
            
        return todos
    
    def create_detailed_prompt(self, todo: Dict[str, Any]) -> str:
        """Expand a todo item into a detailed prompt with completion instructions"""
        content = todo['content']
        priority = todo['priority']
        
        # Try to use template system first
        try:
            template_name = self._select_template_for_task(content)
            if template_name:
                variables = {
                    'TASK_CONTENT': content,
                    'PRIORITY_LEVEL': priority.title()
                }
                
                # Add Claude Code todo specific variables if present
                if 'claude_todo_id' in todo:
                    variables.update({
                        'CLAUDE_TODO_ID': todo.get('claude_todo_id', 'unknown'),
                        'TASK_ID': todo.get('id', 'unknown'),
                        'COMPLETION_CRITERIA': todo.get('completion_criteria', '- Task completed successfully')
                    })
                
                # Add additional variables based on content analysis
                additional_vars = self._extract_template_variables(content)
                variables.update(additional_vars)
                
                return self.template_engine.render_template(template_name, variables)
        except Exception as e:
            self.logger.warning(f"Template rendering failed, using fallback: {e}")
        
        # Fallback to original method
        detailed_prompt = f"""# Task: {content}

## Objective
Complete the following task: {content}

## Priority Level
{priority.title()} priority

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
"""
        return detailed_prompt
    
    def create_directive_file(self, todo: Dict[str, Any], output_slug: str, prerequisites: List[str] = None, platform: str = None, model: str = None) -> str:
        """Create a logseq-style directive file for a todo item"""
        timestamp = datetime.now().isoformat()
        slug = self.create_slug(todo['content'])
        filename = f"{slug}-{todo['id']}.md"
        filepath = self.directives_path / filename
        
        detailed_prompt = self.create_detailed_prompt(todo)
        
        # Format prerequisites section
        prerequisites_section = ""
        if prerequisites:
            prerequisites_section = "\n## Prerequisites\n"
            for prereq in prerequisites:
                prerequisites_section += f"- [[{prereq}]]\n"
        else:
            prerequisites_section = "\n## Prerequisites\n- None\n"
        
        # Add platform/model requirements to frontmatter
        platform_section = ""
        if platform:
            platform_section += f"platform: {platform}\n"
        if model:
            platform_section += f"model: {model}\n"
        
        # Add Claude todo ID if present
        claude_todo_section = ""
        if 'claude_todo_id' in todo:
            claude_todo_section = f"claude_todo_id: {todo['claude_todo_id']}\n"
        
        # Add platform/model to task details
        ai_requirements = ""
        if platform or model:
            ai_requirements = "\n## AI Requirements\n"
            if platform:
                ai_requirements += f"- **Platform**: {platform}\n"
            if model:
                ai_requirements += f"- **Model**: {model}\n"
        
        directive_content = f"""---
id: {todo['id']}
status: {todo['status']}
priority: {todo['priority']}
created: {timestamp}
slug: {slug}
{platform_section}{claude_todo_section}---

# Directive: {todo['content']}

## Task Details
- **ID**: {todo['id']}
- **Status**: {todo['status']}
- **Priority**: {todo['priority']}
- **Created**: {timestamp}
{prerequisites_section}{ai_requirements}
## Prompt
{detailed_prompt}

### Outputs
- Link to output: [[{output_slug}]]

## Metadata
- Type: Directive
- Category: Task Management
"""
        
        # Secure file writing
        if self.settings.get('sanitize_inputs', True):
            try:
                safe_filename = self.sanitizer.sanitize_filename(filename)
                if safe_filename != filename:
                    self.logger.warning(f"Filename sanitized: {filename} -> {safe_filename}")
                    filename = safe_filename
                    filepath = self.directives_path / filename
            except SecurityError as e:
                self.logger.error(f"Filename security error: {e}")
                # Generate a safe fallback filename
                safe_id = self.sanitizer.generate_safe_id(todo['content'])
                filename = f"{safe_id}.md"
                filepath = self.directives_path / filename
        
        filepath.write_text(directive_content)
        return filename
    
    def create_output_file(self, todo: Dict[str, Any], directive_filename: str) -> str:
        """Create an output file based on the template"""
        slug = self.create_slug(todo['content'])
        unix_timestamp = int(datetime.now().timestamp())
        output_filename = f"{slug}-output_{unix_timestamp}.md"
        output_path = self.directives_path / output_filename
        
        # Try to use template engine first
        try:
            output_content = self.template_engine.render_template('directive-out', {
                'TASK_SLUG': slug,
                'STATUS': todo['status'],
                'PRIORITY': todo['priority'],
                'CREATED_DATE': datetime.now().isoformat(),
                'DIRECTIVE_FILE': directive_filename.replace('.md', ''),
                'TASK_TITLE': todo['content'],
                'TASK_DESCRIPTION': todo['content'],
                'OUTPUT_CONTENT': '_Output pending completion of directive_',
                'ADDITIONAL_NOTES': '_No additional notes yet_'
                # Note: TOKENS_IN, TOKENS_OUT, COST, PROCESSING_TIME left as placeholders
            })
        except Exception as e:
            self.logger.warning(f"Template engine failed, using fallback: {e}")
            # Fallback to file-based template with manual replacement
            template_path = self.templates_path / "directive-out.md"
            template_content = template_path.read_text()
            
            # Replace template variables manually
            output_content = template_content.replace("{{TASK_SLUG}}", slug)
            output_content = output_content.replace("{{STATUS}}", todo['status'])
            output_content = output_content.replace("{{PRIORITY}}", todo['priority'])
            output_content = output_content.replace("{{CREATED_DATE}}", datetime.now().isoformat())
            output_content = output_content.replace("{{DIRECTIVE_FILE}}", directive_filename.replace('.md', ''))
            output_content = output_content.replace("{{TASK_TITLE}}", todo['content'])
            output_content = output_content.replace("{{TASK_DESCRIPTION}}", todo['content'])
            output_content = output_content.replace("{{OUTPUT_CONTENT}}", "_Output pending completion of directive_")
            output_content = output_content.replace("{{ADDITIONAL_NOTES}}", "_No additional notes yet_")
        
        # Add required ID field to YAML frontmatter if not present
        if output_content.startswith('---'):
            frontmatter_end = output_content.find('---', 3)
            if frontmatter_end != -1:
                frontmatter = output_content[3:frontmatter_end]
                if 'id:' not in frontmatter:
                    # Insert the id field at the beginning of the frontmatter
                    new_frontmatter = f"id: output-{todo['id']}\n{frontmatter}"
                    output_content = f"---\n{new_frontmatter}---{output_content[frontmatter_end + 3:]}"
        
        # Secure file writing for output
        if self.settings.get('sanitize_inputs', True):
            try:
                safe_output_filename = self.sanitizer.sanitize_filename(output_filename)
                if safe_output_filename != output_filename:
                    self.logger.warning(f"Output filename sanitized: {output_filename} -> {safe_output_filename}")
                    output_filename = safe_output_filename
                    output_path = self.directives_path / output_filename
            except SecurityError as e:
                self.logger.error(f"Output filename security error: {e}")
                # Generate a safe fallback filename
                safe_id = self.sanitizer.generate_safe_id(todo['content'])
                output_filename = f"{safe_id}-output_{unix_timestamp}.md"
                output_path = self.directives_path / output_filename
        
        output_path.write_text(output_content)
        return output_filename
    
    def process_prompt(self, prompt: str, platform: str = None, model: str = None, use_llm: bool = False) -> Dict[str, Any]:
        """Main method to process a prompt and create all necessary files"""
        # Security validation
        if self.settings.get('sanitize_inputs', True):
            try:
                prompt = self.sanitizer.sanitize_prompt(prompt)
                
                if platform and not self.sanitizer.validate_platform(platform):
                    raise SecurityError(f"Invalid platform: {platform}")
                
                if model and platform and not self.sanitizer.validate_model(model, platform):
                    self.logger.warning(f"Potentially invalid model: {model} for platform: {platform}")
                
                # Check for security warnings
                warnings = self.sanitizer.check_content_safety(prompt)
                if warnings:
                    self.logger.warning(f"Content safety warnings: {warnings}")
                    
            except SecurityError as e:
                self.logger.error(f"Security validation failed: {e}")
                raise e
        
        self.logger.info(f"Processing prompt: {prompt[:100]}...", 
                        prompt_length=len(prompt), platform=platform, model=model)
        print(f"Processing prompt: {prompt[:100]}...")
        
        # Create todos from prompt with optional LLM decomposition
        todos = self.analyze_prompt(prompt, use_llm=use_llm, platform=platform, model=model)
        self.logger.info(f"Created {len(todos)} todo items", todo_count=len(todos))
        print(f"Created {len(todos)} todo items")
        
        # Create files for each todo
        results = {
            "todos": todos,
            "files_created": {
                "directives": [],
                "outputs": []
            }
        }
        
        created_slugs = []  # Track created directive slugs for prerequisites
        
        for i, todo in enumerate(todos):
            # Create output file first to get the correct filename
            output_file = self.create_output_file(todo, "")
            output_slug = output_file.replace('.md', '')
            
            # Determine prerequisites (all previous tasks in the list)
            prerequisites = []
            if i > 0:  # Not the first task
                prerequisites = created_slugs.copy()
            
            # Create directive file with correct output link and prerequisites
            directive_file = self.create_directive_file(todo, output_slug, prerequisites, platform, model)
            
            # Log directive creation
            self.logger.directive_created(todo['id'], todo['content'], platform, model)
            
            # Track the slug for this directive for future prerequisites
            slug = self.create_slug(todo['content'])
            directive_slug = f"{slug}-{todo['id']}"
            created_slugs.append(directive_slug)
            
            results["files_created"]["directives"].append(directive_file)
            results["files_created"]["outputs"].append(output_file)
            
            print(f"Created directive: {directive_file}")
            print(f"Created output: {output_file}")
            if prerequisites:
                print(f"  Prerequisites: {', '.join(prerequisites)}")
        
        return results
    
    def create_directives_from_text(self, text: str, platform: str = None, model: str = None) -> Dict[str, Any]:
        """Create directives from plain text input (command line or file)"""
        try:
            # Use the main process_prompt method to handle text input
            results = self.process_prompt(text, platform, model, use_llm=False)
            return results
        except Exception as e:
            print(f"Error creating directives from text: {e}")
            return {"success": False, "error": str(e)}
    
    def _select_template_for_task(self, content: str) -> Optional[str]:
        """Select appropriate template based on task content"""
        content_lower = content.lower()
        
        # Template selection based on keywords
        if any(word in content_lower for word in ['api', 'rest', 'endpoint', 'service']):
            return 'api-project'
        elif any(word in content_lower for word in ['review', 'code review', 'check code']):
            return 'code-review'
        else:
            return 'directive-prompt'  # Default template
    
    def _extract_template_variables(self, content: str) -> Dict[str, str]:
        """Extract additional template variables from task content"""
        variables = {}
        content_lower = content.lower()
        
        # Extract project name if mentioned
        project_match = re.search(r'(?:for|of|called)\s+([\w\s-]+?)(?:\s|$)', content, re.IGNORECASE)
        if project_match:
            variables['PROJECT_NAME'] = project_match.group(1).strip()
        
        # Extract framework if mentioned
        frameworks = ['django', 'flask', 'fastapi', 'express', 'spring', 'rails']
        for framework in frameworks:
            if framework in content_lower:
                variables['FRAMEWORK'] = framework.title()
                break
        
        # Extract database if mentioned
        databases = ['postgresql', 'mysql', 'sqlite', 'mongodb', 'redis']
        for db in databases:
            if db in content_lower:
                variables['DATABASE'] = db.title()
                break
        
        return variables
    
    def create_directives_from_claude_todos(self, claude_todos: List[Dict[str, Any]], 
                                          platform: str = None, model: str = None) -> Dict[str, Any]:
        """Create directives from Claude Code todos"""
        self.logger.info(f"Creating directives from {len(claude_todos)} Claude Code todos")
        print(f"📋 Creating directives from {len(claude_todos)} Claude Code todos...")
        
        # Use bridge to convert todos to directives
        directive_ids = self.todo_bridge.claude_todos_to_directives(claude_todos, platform or "claude", model or "claude-3-sonnet")
        
        return {
            "todos": claude_todos,
            "directive_ids": directive_ids,
            "files_created": {
                "directives": [f"directive-{id}.md" for id in directive_ids],
                "outputs": []
            }
        }
    
    def sync_claude_todos_with_directives(self, claude_todos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Update Claude todos based on directive execution status"""
        self.logger.info(f"Syncing {len(claude_todos)} Claude Code todos with directive status")
        print(f"🔄 Syncing {len(claude_todos)} Claude Code todos with directive status...")
        
        # For each todo, check if it has a directive and update status
        updated_todos = []
        for todo in claude_todos:
            # This would typically get directive status from the system
            # For now, return the todos as-is for compatibility
            updated_todos.append(todo.copy())
        
        return updated_todos
    
    def get_claude_todos_from_directives(self, include_completed: bool = True) -> List[Dict[str, Any]]:
        """Extract Claude todos from existing directive files"""
        self.logger.info("Extracting Claude Code todos from directive files")
        
        # Find all directive files and extract Claude todo information
        todos = []
        directive_folders = ['new', 'success', 'failed', 'slow']
        
        for folder in directive_folders:
            folder_path = self.base_path / "directives" / folder
            if not folder_path.exists():
                continue
                
            for directive_file in folder_path.glob("directive-*.md"):
                try:
                    content = directive_file.read_text()
                    # Extract frontmatter
                    if content.startswith('---'):
                        parts = content.split('---', 2)
                        if len(parts) >= 2:
                            import yaml
                            frontmatter = yaml.safe_load(parts[1])
                            
                            if frontmatter and 'claude_todo_id' in frontmatter:
                                todo = {
                                    'id': frontmatter.get('claude_todo_id'),
                                    'content': frontmatter.get('task', ''),
                                    'status': 'completed' if folder == 'success' else 'pending',
                                    'priority': frontmatter.get('priority', 'medium'),
                                    'directive_id': frontmatter.get('id'),
                                    'directive_file': directive_file.name
                                }
                                
                                if include_completed or todo['status'] != 'completed':
                                    todos.append(todo)
                                
                except Exception as e:
                    self.logger.warning(f"Error parsing directive file {directive_file}: {e}")
        
        return todos
    
    def process_claude_todos(self, claude_todos: List[Dict[str, Any]], 
                           platform: str = None, model: str = None) -> Dict[str, Any]:
        """Process Claude Code todos directly without prompt analysis"""
        # Security validation
        if self.settings.get('sanitize_inputs', True):
            try:
                for todo in claude_todos:
                    if 'content' in todo:
                        todo['content'] = self.sanitizer.sanitize_prompt(todo['content'])
                
                if platform and not self.sanitizer.validate_platform(platform):
                    raise SecurityError(f"Invalid platform: {platform}")
                
                if model and platform and not self.sanitizer.validate_model(model, platform):
                    self.logger.warning(f"Potentially invalid model: {model} for platform: {platform}")
                    
            except SecurityError as e:
                self.logger.error(f"Security validation failed: {e}")
                raise e
        
        self.logger.info(f"Processing {len(claude_todos)} Claude Code todos directly", 
                        todo_count=len(claude_todos), platform=platform, model=model)
        print(f"📋 Processing {len(claude_todos)} Claude Code todos directly...")
        
        # Use the bridge to create directives
        results = self.create_directives_from_claude_todos(claude_todos, platform, model)
        
        print(f"\n=== Claude Todo Processing Results ===")
        print(f"Created {len(results['todos'])} directive items:")
        for todo in results['todos']:
            print(f"- [{todo['priority']}] {todo['content']} (ID: {todo['id']})")
        
        if platform or model:
            print(f"\nAI Requirements:")
            if platform:
                print(f"- Platform: {platform}")
            if model:
                print(f"- Model: {model}")
        
        print(f"\nFiles created in directives/new/:")
        for file in results['files_created']['directives'] + results['files_created']['outputs']:
            print(f"- {file}")
        
        return results


def main():
    """CLI interface for the directive agent"""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Create directives from prompts')
    parser.add_argument('prompt', nargs='*', help='Prompt text to process')
    parser.add_argument('--platform', choices=['claude', 'openai'], help='Required AI platform')
    parser.add_argument('--model', help='Required AI model')
    parser.add_argument('--template', help='Template to use for directive creation')
    parser.add_argument('--list-templates', action='store_true', help='List available templates')
    parser.add_argument('--claude-todos', help='JSON file containing Claude Code todos')
    parser.add_argument('--text', help='Todo text from command line')
    parser.add_argument('--file', help='Plain text file containing todo prompt')
    parser.add_argument('--sync-todos', action='store_true', help='Sync Claude todos with directive status')
    parser.add_argument('--list-todos', action='store_true', help='List todos from directives')
    parser.add_argument('--use-llm', action='store_true', help='Use LLM for prompt decomposition')
    
    args = parser.parse_args()
    
    # Handle template listing
    if args.list_templates:
        agent = DirectiveAgent()
        templates = agent.template_engine.get_available_templates()
        
        print("Available Templates:")
        print("=" * 50)
        
        categories = {}
        for name, metadata in templates.items():
            category = metadata.category
            if category not in categories:
                categories[category] = []
            categories[category].append((name, metadata))
        
        for category, template_list in sorted(categories.items()):
            print(f"\n📂 {category.title()}:")
            for name, metadata in sorted(template_list):
                print(f"   {name:<20} - {metadata.description}")
                if metadata.variables:
                    print(f"   {'':<20}   Variables: {', '.join(metadata.variables)}")
        
        sys.exit(0)
    
    # Handle Claude Code todo operations
    if args.claude_todos:
        try:
            import json
            with open(args.claude_todos, 'r') as f:
                claude_todos = json.load(f)
            
            agent = DirectiveAgent()
            results = agent.process_claude_todos(claude_todos, args.platform, args.model)
            sys.exit(0)
        except Exception as e:
            print(f"Error processing Claude todos: {e}")
            sys.exit(1)
    
    # Handle plain text input from command line
    if args.text:
        try:
            agent = DirectiveAgent()
            results = agent.create_directives_from_text(args.text, args.platform, args.model)
            sys.exit(0)
        except Exception as e:
            print(f"Error processing text input: {e}")
            sys.exit(1)
    
    # Handle plain text file input
    if args.file:
        try:
            with open(args.file, 'r') as f:
                text_content = f.read().strip()
            
            agent = DirectiveAgent()
            results = agent.create_directives_from_text(text_content, args.platform, args.model)
            sys.exit(0)
        except Exception as e:
            print(f"Error processing file input: {e}")
            sys.exit(1)
    
    if args.sync_todos:
        # This would typically be called with actual todos from Claude Code
        agent = DirectiveAgent()
        print("📋 Todo sync functionality available")
        print("Use this with Claude Code's TodoRead/TodoWrite for full integration")
        sys.exit(0)
    
    if args.list_todos:
        agent = DirectiveAgent()
        todos = agent.get_claude_todos_from_directives()
        print(f"📋 Found {len(todos)} todos from directives:")
        for todo in todos:
            status_emoji = "✅" if todo["status"] == "completed" else "📋"
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            print(f"{status_emoji} {priority_emoji.get(todo['priority'], '⚪')} {todo['content']}")
        sys.exit(0)
    
    if not args.prompt:
        print("Usage: python directive_agent.py 'Your prompt here'")
        print("Options: --platform [claude|openai] --model [model-name] --template [template-name]")
        print("         --list-templates (show available templates)")
        print("         --claude-todos FILE (process Claude Code todos from JSON file)")
        print("         --sync-todos (sync Claude todos with directive status)")
        print("         --list-todos (list all todos from directives)")
        sys.exit(1)
    
    prompt = " ".join(args.prompt)
    agent = DirectiveAgent()
    
    # Override template selection if specified
    if args.template:
        # Temporarily modify the template selection method
        original_method = agent._select_template_for_task
        agent._select_template_for_task = lambda content: args.template
    
    results = agent.process_prompt(prompt, args.platform, args.model, args.use_llm)
    
    # Restore original method
    if args.template:
        agent._select_template_for_task = original_method
    
    print("\n=== Results ===")
    print(f"Created {len(results['todos'])} todo items:")
    for todo in results['todos']:
        print(f"- [{todo['priority']}] {todo['content']} (ID: {todo['id']})")
    
    if args.platform or args.model:
        print(f"\nAI Requirements:")
        if args.platform:
            print(f"- Platform: {args.platform}")
        if args.model:
            print(f"- Model: {args.model}")
    
    print(f"\nFiles created in directives/new/:")
    for file in results['files_created']['directives'] + results['files_created']['outputs']:
        print(f"- {file}")


if __name__ == "__main__":
    main()