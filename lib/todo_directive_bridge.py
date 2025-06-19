#!/usr/bin/env python3
"""
Todo-Directive Bridge Module

Provides bidirectional conversion between Claude Code todos and Computer directives.
Handles priority mapping, status synchronization, and context management.
"""

import json
import yaml
import os
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

class TodoDirectiveBridge:
    """Bridge between Claude Code todos and Computer directives"""
    
    def __init__(self, directives_path: str = "directives"):
        self.directives_path = Path(directives_path)
        self.context_path = self.directives_path / "context"
        
        # Ensure all necessary directories exist
        self.context_path.mkdir(parents=True, exist_ok=True)
        (self.directives_path / "new").mkdir(parents=True, exist_ok=True)
        (self.directives_path / "success").mkdir(parents=True, exist_ok=True)
        (self.directives_path / "failed").mkdir(parents=True, exist_ok=True)
        (self.directives_path / "slow").mkdir(parents=True, exist_ok=True)
        
        # Priority mappings
        self.priority_map = {
            "high": {"urgency": "urgent", "completion_criteria": "comprehensive"},
            "medium": {"urgency": "normal", "completion_criteria": "standard"},
            "low": {"urgency": "low", "completion_criteria": "basic"}
        }
        
        # Status mappings
        self.status_map = {
            "pending": "new",
            "in_progress": "new",  # Will be processed by engage agent
            "completed": "success"
        }
    
    def claude_todos_to_directives(self, todos: List[Dict[str, Any]], 
                                 platform: str = "claude", 
                                 model: str = "claude-3-sonnet") -> List[str]:
        """Convert Claude Code todos to directive files"""
        directive_ids = []
        
        # Create session context
        session_id = self._create_session_context(todos)
        
        for i, todo in enumerate(todos):
            directive_id = self._generate_directive_id()
            directive_path = self.directives_path / "new" / f"directive-{directive_id}.md"
            
            # Build directive content
            content = self._build_directive_from_todo(
                todo, directive_id, session_id, platform, model, i, len(todos)
            )
            
            # Write directive file
            with open(directive_path, 'w') as f:
                f.write(content)
            
            directive_ids.append(directive_id)
            
            # Update session context with directive mapping
            self._update_session_context(session_id, todo['id'], directive_id)
        
        return directive_ids
    
    def sync_todo_status(self, todo_id: str, directive_id: str, status: str) -> bool:
        """Sync todo status based on directive completion"""
        session_context = self._load_session_context()
        
        if not session_context:
            return False
        
        # Update todo status in session context
        for todo in session_context.get('todos', []):
            if todo['id'] == todo_id:
                todo['status'] = status
                todo['directive_id'] = directive_id
                todo['updated_at'] = datetime.now().isoformat()
                break
        
        # Save updated context
        self._save_session_context(session_context)
        return True
    
    def get_todo_context(self, todo_id: str) -> Dict[str, Any]:
        """Get context for a specific todo including related work"""
        session_context = self._load_session_context()
        
        if not session_context:
            return {}
        
        # Find the todo
        target_todo = None
        for todo in session_context.get('todos', []):
            if todo['id'] == todo_id:
                target_todo = todo
                break
        
        if not target_todo:
            return {}
        
        # Build context
        context = {
            'session_id': session_context.get('session_id'),
            'session_created': session_context.get('created_at'),
            'todo': target_todo,
            'related_todos': self._get_related_todos(target_todo, session_context),
            'completed_work': self._get_completed_work(session_context),
            'knowledge_base': session_context.get('knowledge_base', {})
        }
        
        return context
    
    def directives_to_claude_todos(self, directive_ids: List[str]) -> List[Dict[str, Any]]:
        """Convert completed directives back to Claude Code todo format"""
        todos = []
        
        for directive_id in directive_ids:
            # Look for directive in success/failed folders
            directive_path = self._find_directive(directive_id)
            if not directive_path:
                continue
            
            # Parse directive
            directive_content = self._parse_directive(directive_path)
            
            # Convert to todo format
            todo = {
                'id': directive_content.get('claude_todo_id', f'todo-{directive_id}'),
                'content': directive_content.get('task', ''),
                'status': 'completed' if 'success' in str(directive_path) else 'pending',
                'priority': self._map_directive_priority(directive_content.get('urgency', 'normal')),
                'directive_id': directive_id,
                'results': directive_content.get('results', ''),
                'files_modified': directive_content.get('files_modified', [])
            }
            
            todos.append(todo)
        
        return todos
    
    def _create_session_context(self, todos: List[Dict[str, Any]]) -> str:
        """Create a new session context file"""
        session_id = f"session-{int(datetime.now().timestamp())}"
        
        context = {
            'session_id': session_id,
            'created_at': datetime.now().isoformat(),
            'todos': [dict(todo) for todo in todos],  # Deep copy
            'directive_mappings': {},
            'knowledge_base': {},
            'completed_directives': []
        }
        
        # Analyze todos for dependencies
        context['dependencies'] = self._analyze_todo_dependencies(todos)
        
        # Save context
        context_file = self.context_path / f"{session_id}.json"
        with open(context_file, 'w') as f:
            json.dump(context, f, indent=2)
        
        return session_id
    
    def _build_directive_from_todo(self, todo: Dict[str, Any], directive_id: str, 
                                 session_id: str, platform: str, model: str,
                                 todo_index: int, total_todos: int) -> str:
        """Build directive content from todo"""
        
        # Get priority settings
        priority_info = self.priority_map.get(todo.get('priority', 'medium'))
        
        # Build frontmatter with fields expected by engage agent
        frontmatter = {
            'id': directive_id,
            'status': todo.get('status', 'pending'),  # Required by engage agent
            'priority': todo.get('priority', 'medium'),  # Required by engage agent 
            'created': datetime.now().isoformat(),  # Required by engage agent
            'slug': f"todo-{todo['id']}",  # For logseq-style linking
            'platform': platform,
            'model': model,
            'urgency': priority_info['urgency'],  # Keep for internal use
            'completion_criteria': priority_info['completion_criteria'],
            'claude_todo_id': todo['id'],
            'session_id': session_id,
            'todo_index': todo_index,
            'total_todos': total_todos
        }
        
        # Add dependencies if this isn't the first todo
        # For now, make each todo depend on the previous one by directive slug
        if todo_index > 0:
            prev_todo = todos[todo_index - 1]
            prev_slug = f"todo-{prev_todo['id']}"
            frontmatter['prerequisites'] = [prev_slug]
        
        # Try to use Claude-specific template first
        try:
            template_path = self.directives_path.parent / "templates" / "claude-todo.md"
            if template_path.exists():
                template_content = template_path.read_text()
                
                # Extract template body (after frontmatter)
                template_parts = template_content.split('---', 2)
                if len(template_parts) >= 3:
                    template_body = template_parts[2].strip()
                    
                    # Replace template variables
                    content_body = template_body.replace("{{CLAUDE_TODO_ID}}", todo['id'])
                    content_body = content_body.replace("{{TASK_CONTENT}}", todo['content'])
                    content_body = content_body.replace("{{PRIORITY_LEVEL}}", priority_info['urgency'].title())
                    content_body = content_body.replace("{{TASK_ID}}", directive_id)
                    content_body = content_body.replace("{{SESSION_ID}}", session_id)
                    content_body = content_body.replace("{{TODO_INDEX}}", str(todo_index))
                    content_body = content_body.replace("{{TOTAL_TODOS}}", str(total_todos))
                    content_body = content_body.replace("{{PLATFORM}}", platform)
                    content_body = content_body.replace("{{MODEL}}", model)
                    content_body = content_body.replace("{{COMPLETION_CRITERIA}}", 
                                                      self._generate_success_criteria(todo, priority_info['completion_criteria']))
                    
                    # Build full content with frontmatter
                    content_parts = [
                        '---',
                        yaml.dump(frontmatter, default_flow_style=False).strip(),
                        '---',
                        '',
                        content_body
                    ]
                    
                    return '\n'.join(content_parts)
        except Exception as e:
            # Fall back to basic template if template processing fails
            pass
        
        # Fallback to basic content structure
        content_parts = [
            '---',
            yaml.dump(frontmatter, default_flow_style=False).strip(),
            '---',
            '',
            f"# Task: {todo['content']}",
            '',
            "## Context",
            f"This is todo {todo_index + 1} of {total_todos} in the current session.",
            ''
        ]
        
        # Add session context if available
        context = self.get_todo_context(todo['id'])
        if context and context.get('completed_work'):
            content_parts.extend([
                "## Previous Work Completed",
                ""
            ])
            for work in context['completed_work']:
                content_parts.append(f"- {work['task']}: {work['summary']}")
            content_parts.append("")
        
        # Add detailed task description
        content_parts.extend([
            "## Task Details",
            todo['content'],
            "",
            "## Success Criteria",
            self._generate_success_criteria(todo, priority_info['completion_criteria']),
            ""
        ])
        
        return '\n'.join(content_parts)
    
    def _generate_success_criteria(self, todo: Dict[str, Any], criteria_level: str) -> str:
        """Generate success criteria based on todo content and priority"""
        content = todo['content'].lower()
        
        base_criteria = []
        
        # Content-specific criteria
        if 'test' in content:
            base_criteria.append("- Tests are written and passing")
            base_criteria.append("- Test coverage meets project standards")
        
        if 'bug' in content or 'fix' in content:
            base_criteria.append("- Bug is completely resolved")
            base_criteria.append("- No regressions introduced")
        
        if 'documentation' in content or 'docs' in content:
            base_criteria.append("- Documentation is clear and complete")
            base_criteria.append("- Examples are provided where appropriate")
        
        if 'feature' in content or 'implement' in content:
            base_criteria.append("- Feature works as specified")
            base_criteria.append("- Edge cases are handled")
        
        # Priority-based criteria
        if criteria_level == "comprehensive":
            base_criteria.extend([
                "- Code is well-documented with comments",
                "- Performance implications considered",
                "- Security considerations addressed",
                "- Integration with existing systems verified"
            ])
        elif criteria_level == "standard":
            base_criteria.extend([
                "- Code follows project conventions",
                "- Basic error handling implemented"
            ])
        
        # Default criteria if none match
        if not base_criteria:
            base_criteria = [
                "- Task requirements are fully met",
                "- Code is functional and tested"
            ]
        
        return '\n'.join(base_criteria)
    
    def _analyze_todo_dependencies(self, todos: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Analyze todos for potential dependencies"""
        dependencies = {}
        
        for i, todo in enumerate(todos):
            todo_deps = []
            content = todo['content'].lower()
            
            # Look for explicit references to previous todos
            for j in range(i):
                prev_todo = todos[j]
                prev_content = prev_todo['content'].lower()
                
                # Simple keyword matching for dependencies
                if any(word in content for word in prev_content.split()[:3]):
                    todo_deps.append(prev_todo['id'])
            
            if todo_deps:
                dependencies[todo['id']] = todo_deps
        
        return dependencies
    
    def _generate_directive_id(self) -> str:
        """Generate a unique directive ID"""
        return f"{int(datetime.now().timestamp())}-{os.urandom(4).hex()}"
    
    def _find_directive(self, directive_id: str) -> Optional[Path]:
        """Find directive file in any status folder"""
        for folder in ['new', 'success', 'failed', 'slow']:
            directive_path = self.directives_path / folder / f"directive-{directive_id}.md"
            if directive_path.exists():
                return directive_path
        return None
    
    def _parse_directive(self, directive_path: Path) -> Dict[str, Any]:
        """Parse directive file and extract metadata"""
        with open(directive_path, 'r') as f:
            content = f.read()
        
        # Split frontmatter and content
        parts = content.split('---', 2)
        if len(parts) >= 2:
            frontmatter_str = parts[1]
            try:
                frontmatter = yaml.safe_load(frontmatter_str)
                return frontmatter or {}
            except yaml.YAMLError:
                pass
        
        return {}
    
    def _map_directive_priority(self, urgency: str) -> str:
        """Map directive urgency back to todo priority"""
        mapping = {"urgent": "high", "normal": "medium", "low": "low"}
        return mapping.get(urgency, "medium")
    
    def _load_session_context(self) -> Optional[Dict[str, Any]]:
        """Load the most recent session context"""
        context_files = list(self.context_path.glob("session-*.json"))
        if not context_files:
            return None
        
        # Get the most recent context file
        latest_context = max(context_files, key=lambda p: p.stat().st_mtime)
        
        with open(latest_context, 'r') as f:
            return json.load(f)
    
    def _save_session_context(self, context: Dict[str, Any]) -> None:
        """Save session context to file"""
        session_id = context.get('session_id', f"session-{int(datetime.now().timestamp())}")
        context_file = self.context_path / f"{session_id}.json"
        
        with open(context_file, 'w') as f:
            json.dump(context, f, indent=2)
    
    def _update_session_context(self, session_id: str, todo_id: str, directive_id: str) -> None:
        """Update session context with directive mapping"""
        context_file = self.context_path / f"{session_id}.json"
        
        if context_file.exists():
            with open(context_file, 'r') as f:
                context = json.load(f)
            
            context['directive_mappings'][todo_id] = directive_id
            
            with open(context_file, 'w') as f:
                json.dump(context, f, indent=2)
    
    def _get_related_todos(self, target_todo: Dict[str, Any], 
                          session_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get todos related to the target todo"""
        related = []
        target_content = target_todo['content'].lower().split()
        
        for todo in session_context.get('todos', []):
            if todo['id'] == target_todo['id']:
                continue
            
            # Simple similarity matching
            todo_content = todo['content'].lower().split()
            common_words = set(target_content) & set(todo_content)
            
            if len(common_words) >= 2:  # At least 2 words in common
                related.append(todo)
        
        return related
    
    def _get_completed_work(self, session_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get completed work from session context"""
        completed = []
        
        for directive_info in session_context.get('completed_directives', []):
            completed.append({
                'directive_id': directive_info.get('directive_id'),
                'task': directive_info.get('task', ''),
                'summary': directive_info.get('summary', ''),
                'files_modified': directive_info.get('files_modified', [])
            })
        
        return completed

# CLI Functions for standalone usage
def main():
    """CLI interface for todo-directive bridge"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Todo-Directive Bridge")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Convert todos to directives
    convert_parser = subparsers.add_parser('convert', help='Convert todos to directives')
    convert_parser.add_argument('--todos-file', required=True, help='JSON file with todos')
    convert_parser.add_argument('--platform', default='claude', help='AI platform')
    convert_parser.add_argument('--model', default='claude-3-sonnet', help='AI model')
    
    # Sync todo status
    sync_parser = subparsers.add_parser('sync', help='Sync todo status')
    sync_parser.add_argument('--todo-id', required=True, help='Todo ID')
    sync_parser.add_argument('--directive-id', required=True, help='Directive ID')
    sync_parser.add_argument('--status', required=True, help='New status')
    
    # Export directives to todos
    export_parser = subparsers.add_parser('export', help='Export directives to todos')
    export_parser.add_argument('--directive-ids', nargs='+', required=True, help='Directive IDs')
    export_parser.add_argument('--output-file', help='Output JSON file')
    
    args = parser.parse_args()
    bridge = TodoDirectiveBridge()
    
    if args.command == 'convert':
        with open(args.todos_file, 'r') as f:
            todos = json.load(f)
        
        directive_ids = bridge.claude_todos_to_directives(todos, args.platform, args.model)
        print(f"Created {len(directive_ids)} directives: {', '.join(directive_ids)}")
    
    elif args.command == 'sync':
        success = bridge.sync_todo_status(args.todo_id, args.directive_id, args.status)
        print(f"Sync {'successful' if success else 'failed'}")
    
    elif args.command == 'export':
        todos = bridge.directives_to_claude_todos(args.directive_ids)
        
        if args.output_file:
            with open(args.output_file, 'w') as f:
                json.dump(todos, f, indent=2)
            print(f"Exported {len(todos)} todos to {args.output_file}")
        else:
            print(json.dumps(todos, indent=2))

if __name__ == '__main__':
    main()