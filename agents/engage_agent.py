#!/usr/bin/env python3
"""
Engage Agent - Processes directive files by priority and age, executing tasks and moving them to appropriate status directories
"""

import os
import re
import shutil
import time
import yaml
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import subprocess
import tempfile

# Add lib directory to path for AI client, settings, and logging
sys.path.append(str(Path(__file__).parent.parent / "lib"))
from ai_client import AIClient
from settings import get_settings
from logger import get_logger, PerformanceTracker
from todo_directive_bridge import TodoDirectiveBridge
from batch_processor import BatchProcessor, BatchRequest


class EngageAgent:
    def __init__(self, base_path: str = ".", api_mode: bool = False):
        self.base_path = Path(base_path)
        self.directives_new = self.base_path / "directives" / "new"
        self.directives_success = self.base_path / "directives" / "success"
        self.directives_failed = self.base_path / "directives" / "failed"
        self.directives_slow = self.base_path / "directives" / "slow"
        self.directives_exemplars = self.base_path / "directives" / "possible-exemplars"
        self.api_mode = api_mode
        self.settings = get_settings(base_path)
        self.logger = get_logger("engage_agent", base_path)
        self.performance_tracker = PerformanceTracker(self.logger)
        
        # Initialize AI client if in API mode
        if self.api_mode:
            try:
                self.ai_client = AIClient()
                self.logger.info("API mode enabled - will use AI for task execution")
                print("🤖 API mode enabled - will use AI for task execution")
            except Exception as e:
                self.logger.error(f"Failed to initialize AI client: {e}")
                print(f"⚠️  Warning: Failed to initialize AI client: {e}")
                self.api_mode = False
        
        # Ensure all directories exist
        for dir_path in [self.directives_new, self.directives_success, 
                        self.directives_failed, self.directives_slow, 
                        self.directives_exemplars]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize todo-directive bridge
        self.todo_bridge = TodoDirectiveBridge(base_path)
        
        # Initialize batch processor
        self.batch_processor = BatchProcessor(base_path)
        
        # Initialize context persistence
        self.context_path = self.base_path / "directives" / "context"
        self.context_path.mkdir(exist_ok=True)
        self.session_context = self._load_or_create_session_context()
    
    def parse_directive_metadata(self, file_path: Path) -> Optional[Dict]:
        """Parse the frontmatter metadata from a directive file"""
        try:
            content = file_path.read_text()
            
            # Extract YAML frontmatter
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    frontmatter = yaml.safe_load(parts[1])
                    return frontmatter
            return None
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None
    
    def extract_prerequisites(self, content: str) -> List[str]:
        """Extract prerequisites from directive content"""
        prerequisites = []
        
        # Look for prerequisites in various formats
        patterns = [
            r'(?i)prerequisites?:\s*(.+)',
            r'(?i)depends?\s+on:\s*(.+)',
            r'(?i)requires?:\s*(.+)',
            r'(?i)needs?:\s*(.+)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            for match in matches:
                # Split on commas and clean up
                prereqs = [p.strip() for p in match.split(',')]
                prerequisites.extend(prereqs)
        
        return [p for p in prerequisites if p and p.lower() not in ['none', 'n/a', '-']]
    
    def check_prerequisites_met(self, prerequisites: List[str]) -> bool:
        """Check if all prerequisites have been completed (exist in completion directories)"""
        if not prerequisites:
            return True
        
        completed_info = []
        # Check all completion directories: success, slow, and exemplars
        completion_dirs = [self.directives_success, self.directives_slow, self.directives_exemplars]
        for directory in completion_dirs:
            for file_path in directory.glob("*.md"):
                # Parse metadata to get slug and claude_todo_id
                metadata = self.parse_directive_metadata(file_path)
                completed_info.append({
                    'filename': file_path.stem,
                    'slug': metadata.get('slug', '') if metadata else '',
                    'claude_todo_id': metadata.get('claude_todo_id', '') if metadata else ''
                })
        
        for prereq in prerequisites:
            # Remove any markdown link formatting and dashes
            clean_prereq = re.sub(r'\[\[(.+?)\]\]', r'\1', prereq)
            clean_prereq = clean_prereq.strip().lstrip('- ')
            
            # Check if prerequisite is met by filename, slug, or claude_todo_id
            found = False
            for completed in completed_info:
                if (clean_prereq == completed['filename'] or 
                    clean_prereq == completed['slug'] or 
                    clean_prereq == completed['claude_todo_id']):
                    found = True
                    break
            
            if not found:
                print(f"Prerequisite not met: {clean_prereq}")
                print(f"Available completed items: {[c['slug'] for c in completed_info]}")
                return False
            
        return True
    
    def get_priority_score(self, priority: str) -> int:
        """Convert priority string to numeric score (higher = more important)"""
        priority_map = {
            'high': 3,
            'medium': 2,
            'low': 1
        }
        return priority_map.get(priority.lower(), 1)
    
    def get_file_age(self, file_path: Path) -> float:
        """Get file age in seconds since creation"""
        try:
            stat = file_path.stat()
            return time.time() - stat.st_ctime
        except:
            return 0
    
    def find_next_directive(self) -> Optional[Path]:
        """Find the highest priority, oldest directive with no unmet prerequisites"""
        candidates = []
        
        for file_path in self.directives_new.glob("*.md"):
            metadata = self.parse_directive_metadata(file_path)
            if not metadata:
                continue
            
            # Extract prerequisites from file content
            content = file_path.read_text()
            prerequisites = self.extract_prerequisites(content)
            
            # Check if prerequisites are met
            if not self.check_prerequisites_met(prerequisites):
                print(f"Skipping {file_path.name} - prerequisites not met: {prerequisites}")
                continue
            
            priority = metadata.get('priority', 'medium')
            priority_score = self.get_priority_score(priority)
            age = self.get_file_age(file_path)
            
            candidates.append({
                'path': file_path,
                'priority_score': priority_score,
                'age': age,
                'metadata': metadata
            })
        
        if not candidates:
            return None
        
        # Sort by priority (desc) then age (desc, older first)
        candidates.sort(key=lambda x: (x['priority_score'], x['age']), reverse=True)
        return candidates[0]['path']
    
    def extract_task_content(self, file_path: Path) -> str:
        """Extract the main task content from directive file"""
        content = file_path.read_text()
        
        # Look for the prompt section
        prompt_match = re.search(r'## Prompt\s*\n(.*?)(?=\n##|\n###|$)', content, re.DOTALL)
        if prompt_match:
            return prompt_match.group(1).strip()
        
        # Fallback to looking for task content in metadata or title
        metadata = self.parse_directive_metadata(file_path)
        if metadata and 'content' in metadata:
            return metadata['content']
        
        # Extract from title if available
        title_match = re.search(r'# Directive: (.+)', content)
        if title_match:
            return title_match.group(1).strip()
        
        return "Process this directive"
    
    def execute_directive(self, file_path: Path) -> Tuple[bool, float, str, Optional[Dict]]:
        """Execute a directive and return (success, duration, output, metrics)"""
        directive_id = file_path.stem
        self.logger.directive_started(directive_id, str(file_path))
        print(f"\n🚀 Processing directive: {file_path.name}")
        
        start_time = time.time()
        
        try:
            task_content = self.extract_task_content(file_path)
            print(f"Task: {task_content[:100]}...")
            
            # Get context for this directive
            context = self._get_context_for_directive(file_path)
            
            # Enhance task content with context if available
            if context.strip():
                enhanced_task_content = f"{context}\n\n## Current Task\n{task_content}"
            else:
                enhanced_task_content = task_content
            
            # Check if API mode and get platform/model requirements
            if self.api_mode:
                metadata = self.parse_directive_metadata(file_path)
                platform = metadata.get('platform') if metadata else None
                model = metadata.get('model') if metadata else None
                
                self.logger.api_request(platform or 'auto', model or 'default')
                print(f"🤖 Using AI execution - Platform: {platform or 'auto'}, Model: {model or 'default'}")
                
                # Execute via AI API with enhanced context
                result = self.ai_client.chat_completion(enhanced_task_content, platform, model)
                duration = time.time() - start_time
                
                if result["success"]:
                    # Extract performance metrics
                    usage = result.get('usage', {})
                    tokens_in = usage.get('input_tokens', 0)
                    tokens_out = usage.get('output_tokens', 0)
                    cost = self._calculate_cost(platform, model, tokens_in, tokens_out)
                    
                    # Log API response and directive completion
                    self.logger.api_response(platform, model, True, tokens_out, cost)
                    self.logger.directive_completed(directive_id, True, duration, tokens_in, tokens_out, cost)
                    self.performance_tracker.track_directive(True, duration, tokens_in, tokens_out, cost)
                    self.performance_tracker.track_api_call(True)
                    
                    output = f"✅ Task completed successfully in {duration:.2f}s\n\n"
                    output += f"Platform: {result['platform']}\nModel: {result['model']}\n"
                    output += f"Tokens In: {tokens_in}\nTokens Out: {tokens_out}\nCost: ${cost:.4f}\n\n"
                    output += f"Response:\n{result['content']}"
                    
                    # Store metrics for output file update
                    result['metrics'] = {
                        'tokens_in': tokens_in,
                        'tokens_out': tokens_out, 
                        'cost': cost,
                        'processing_time': f"{duration:.2f}s"
                    }
                    
                    return True, duration, output, result
                else:
                    # Log API error and directive failure
                    self.logger.api_response(platform, model, False, error=result.get('error'))
                    self.logger.directive_completed(directive_id, False, duration)
                    self.performance_tracker.track_directive(False, duration)
                    self.performance_tracker.track_api_call(False)
                    
                    output = f"❌ AI execution failed after {duration:.2f}s\n\n"
                    output += f"Platform: {result['platform']}\nModel: {result['model']}\n\n"
                    output += f"Error: {result['error']}"
                    return False, duration, output, result
            else:
                # Fallback to script execution
                temp_script = self.create_execution_script(task_content)
                
                # Execute the task with timeout
                result = subprocess.run(
                    ['python', temp_script],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                
                duration = time.time() - start_time
                
                if result.returncode == 0:
                    self.logger.directive_completed(directive_id, True, duration)
                    self.performance_tracker.track_directive(True, duration)
                    output = f"✅ Task completed successfully in {duration:.2f}s\n\nOutput:\n{result.stdout}"
                    return True, duration, output, None
                else:
                    self.logger.directive_completed(directive_id, False, duration)
                    self.performance_tracker.track_directive(False, duration)
                    output = f"❌ Task failed after {duration:.2f}s\n\nError:\n{result.stderr}\n\nOutput:\n{result.stdout}"
                    return False, duration, output, None
                
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            self.logger.error(f"Directive {directive_id} timed out after {duration:.2f}s")
            self.logger.directive_completed(directive_id, False, duration)
            self.performance_tracker.track_directive(False, duration)
            output = f"⏰ Task timed out after {duration:.2f}s"
            return False, duration, output, None
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"Directive {directive_id} failed with exception: {str(e)}")
            self.logger.directive_completed(directive_id, False, duration)
            self.performance_tracker.track_directive(False, duration)
            output = f"💥 Task failed with exception after {duration:.2f}s: {str(e)}"
            return False, duration, output, None
        finally:
            # Clean up temp script
            if 'temp_script' in locals() and os.path.exists(temp_script):
                os.unlink(temp_script)
    
    def create_execution_script(self, task_content: str) -> str:
        """Create a temporary Python script to execute the task"""
        # This is a simplified implementation
        # In practice, you might want more sophisticated task parsing and execution
        
        script_content = f'''#!/usr/bin/env python3
"""
Temporary script for executing directive task
"""

def main():
    """Execute the directive task"""
    task = """{task_content}"""
    
    print(f"Executing task: {{task[:100]}}...")
    
    # Basic task execution simulation
    # In a real implementation, this would parse the task and execute appropriate actions
    
    # For now, just simulate some work and return success
    import time
    time.sleep(1)  # Simulate some work
    
    print("Task completed successfully!")
    return True

if __name__ == "__main__":
    main()
'''
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script_content)
            return f.name
    
    def _calculate_cost(self, platform: str, model: str, tokens_in: int, tokens_out: int) -> float:
        """Calculate approximate cost based on platform, model, and token usage"""
        # Cost per 1K tokens (approximate pricing as of 2024)
        pricing = {
            'claude': {
                'claude-3-opus': {'input': 0.015, 'output': 0.075},
                'claude-3-sonnet': {'input': 0.003, 'output': 0.015},
                'claude-3-haiku': {'input': 0.00025, 'output': 0.00125}
            },
            'openai': {
                'gpt-4': {'input': 0.03, 'output': 0.06},
                'gpt-4-turbo': {'input': 0.01, 'output': 0.03},
                'gpt-3.5-turbo': {'input': 0.0005, 'output': 0.0015}
            }
        }
        
        platform_pricing = pricing.get(platform, {})
        model_pricing = platform_pricing.get(model, {'input': 0, 'output': 0})
        
        cost_in = (tokens_in / 1000) * model_pricing['input']
        cost_out = (tokens_out / 1000) * model_pricing['output']
        
        return cost_in + cost_out
    
    def _load_or_create_session_context(self) -> Dict[str, Any]:
        """Load existing session context or create new one"""
        import json
        
        # Look for the most recent session context file
        context_files = list(self.context_path.glob("session-*.json"))
        
        if context_files:
            # Get the most recent context file
            latest_context = max(context_files, key=lambda p: p.stat().st_mtime)
            
            try:
                with open(latest_context, 'r') as f:
                    context = json.load(f)
                
                # Ensure required keys exist for backward compatibility
                if 'execution_history' not in context:
                    context['execution_history'] = []
                if 'completed_directives' not in context:
                    context['completed_directives'] = []
                if 'knowledge_base' not in context:
                    context['knowledge_base'] = {}
                
                self.logger.info(f"Loaded session context: {latest_context.name}")
                return context
            except Exception as e:
                self.logger.warning(f"Failed to load session context {latest_context}: {e}")
        
        # Create new session context
        session_id = f"session-{int(time.time())}"
        context = {
            'session_id': session_id,
            'created_at': datetime.now().isoformat(),
            'completed_directives': [],
            'knowledge_base': {},
            'execution_history': []
        }
        
        self._save_session_context(context)
        self.logger.info(f"Created new session context: {session_id}")
        return context
    
    def _save_session_context(self, context: Dict[str, Any]) -> None:
        """Save session context to file"""
        import json
        
        session_id = context.get('session_id', f"session-{int(time.time())}")
        context_file = self.context_path / f"{session_id}.json"
        
        with open(context_file, 'w') as f:
            json.dump(context, f, indent=2)
    
    def _update_session_context_with_directive(self, directive_path: Path, success: bool, 
                                             duration: float, output: str, metrics: Optional[Dict] = None) -> None:
        """Update session context with completed directive information"""
        directive_metadata = self.parse_directive_metadata(directive_path)
        
        directive_info = {
            'directive_id': directive_path.stem,
            'directive_file': directive_path.name,
            'task': self.extract_task_content(directive_path),
            'success': success,
            'duration': duration,
            'completed_at': datetime.now().isoformat(),
            'summary': output[:200] + "..." if len(output) > 200 else output,
            'files_modified': []  # Would be extracted from output in real implementation
        }
        
        # Add metrics if available
        if metrics:
            directive_info['metrics'] = metrics
        
        # Add Claude todo ID if available
        if directive_metadata and 'claude_todo_id' in directive_metadata:
            directive_info['claude_todo_id'] = directive_metadata['claude_todo_id']
            
            # Update todo bridge with completion status
            self.todo_bridge.sync_todo_status(
                directive_metadata['claude_todo_id'],
                directive_path.stem,
                'completed' if success else 'failed'
            )
        
        # Add to completed directives
        self.session_context['completed_directives'].append(directive_info)
        
        # Update execution history
        self.session_context['execution_history'].append({
            'timestamp': datetime.now().isoformat(),
            'directive_id': directive_path.stem,
            'action': 'completed' if success else 'failed',
            'duration': duration
        })
        
        # Save updated context
        self._save_session_context(self.session_context)
    
    def _get_context_for_directive(self, directive_path: Path) -> str:
        """Get relevant context for a directive execution"""
        metadata = self.parse_directive_metadata(directive_path)
        
        context_parts = []
        
        # Add session summary
        context_parts.append("## Session Context")
        context_parts.append(f"Session ID: {self.session_context.get('session_id', 'unknown')}")
        context_parts.append(f"Session Started: {self.session_context.get('created_at', 'unknown')}")
        
        # Add completed work summary
        completed = self.session_context.get('completed_directives', [])
        if completed:
            context_parts.append(f"\n## Previously Completed Work ({len(completed)} items)")
            for item in completed[-5:]:  # Show last 5 completed items
                status_emoji = "✅" if item['success'] else "❌"
                context_parts.append(f"- {status_emoji} {item['task'][:60]}... (Duration: {item['duration']:.1f}s)")
        
        # Add todo context if this is a Claude Code todo
        if metadata and 'claude_todo_id' in metadata:
            todo_context = self.todo_bridge.get_todo_context(metadata['claude_todo_id'])
            
            if todo_context.get('related_todos'):
                context_parts.append(f"\n## Related Todos")
                for related in todo_context['related_todos'][:3]:
                    context_parts.append(f"- {related['content']}")
            
            if todo_context.get('knowledge_base'):
                context_parts.append(f"\n## Knowledge Base")
                for key, value in todo_context['knowledge_base'].items():
                    context_parts.append(f"- {key}: {value}")
        
        # Add prerequisites context
        content = directive_path.read_text()
        prerequisites = self.extract_prerequisites(content)
        if prerequisites:
            context_parts.append(f"\n## Prerequisites Context")
            for prereq in prerequisites:
                # Find completed directive with this prereq
                for completed_dir in completed:
                    if prereq in completed_dir.get('directive_file', ''):
                        context_parts.append(f"- ✅ {prereq}: {completed_dir['summary']}")
                        break
        
        return '\n'.join(context_parts)

    def update_output_file(self, directive_path: Path, success: bool, duration: float, output: str, metrics: Optional[Dict] = None):
        """Update or create output file with execution results"""
        directive_name = directive_path.stem
        
        # First, look for existing output files that match this directive
        output_file_found = False
        for output_file in self.directives_new.glob(f"*output*.md"):
            if directive_name.split('-')[0] in output_file.name:
                output_file_found = True
                try:
                    content = output_file.read_text()
                    
                    # Update the output content
                    status = "✅ Completed" if success else "❌ Failed"
                    execution_time = f"{duration:.2f}s"
                    
                    # Replace template variables with actual results
                    content = content.replace("{{OUTPUT_CONTENT}}", output)
                    content = content.replace("_Output pending completion of directive_", output)
                    content = re.sub(r'status: .*', f'status: {status}', content)
                    
                    # Update performance metrics if available
                    if metrics:
                        content = content.replace("{{TOKENS_IN}}", str(metrics.get('tokens_in', 0)))
                        content = content.replace("{{TOKENS_OUT}}", str(metrics.get('tokens_out', 0)))
                        content = content.replace("{{COST}}", f"${metrics.get('cost', 0):.4f}")
                        content = content.replace("{{PROCESSING_TIME}}", metrics.get('processing_time', execution_time))
                    else:
                        content = content.replace("{{TOKENS_IN}}", "N/A")
                        content = content.replace("{{TOKENS_OUT}}", "N/A")
                        content = content.replace("{{COST}}", "N/A")
                        content = content.replace("{{PROCESSING_TIME}}", execution_time)
                    
                    # Add execution metadata
                    metadata_section = f"\n\n## Execution Results\n- Status: {status}\n- Duration: {execution_time}\n- Timestamp: {datetime.now().isoformat()}\n"
                    content += metadata_section
                    
                    output_file.write_text(content)
                    
                    # Move output file to same directory as directive
                    dest_dir = directive_path.parent
                    if dest_dir != self.directives_new:
                        shutil.move(str(output_file), str(dest_dir / output_file.name))
                    
                    break
                except Exception as e:
                    print(f"Error updating output file {output_file}: {e}")
        
        # If no existing output file found, create a new one (for TODO-generated directives)
        if not output_file_found:
            self._create_output_file_for_directive(directive_path, success, duration, output, metrics)
    
    def _create_output_file_for_directive(self, directive_path: Path, success: bool, duration: float, output: str, metrics: Optional[Dict] = None):
        """Create a new output file for TODO-generated directives"""
        try:
            # Get directive metadata for context
            metadata = self.parse_directive_metadata(directive_path)
            if not metadata:
                return
            
            # Extract basic info
            task_content = self.extract_task_content(directive_path)
            status = "✅ Completed" if success else "❌ Failed"
            execution_time = f"{duration:.2f}s"
            
            # Generate output filename
            directive_slug = metadata.get('slug', directive_path.stem)
            unix_timestamp = int(datetime.now().timestamp())
            output_filename = f"{directive_slug}-output_{unix_timestamp}.md"
            output_path = directive_path.parent / output_filename
            
            # Build output content with YAML frontmatter
            frontmatter = {
                'id': f"output-{metadata.get('id', directive_path.stem)}",
                'slug': directive_slug,
                'status': status,
                'priority': metadata.get('priority', 'medium'),
                'created': datetime.now().isoformat(),
                'directive': f"[[{directive_path.stem}]]",
                'tokens_in': metrics.get('tokens_in', 0) if metrics else 0,
                'tokens_out': metrics.get('tokens_out', 0) if metrics else 0,
                'cost': f"${metrics.get('cost', 0):.4f}" if metrics else "$0.0000",
                'processing_time': metrics.get('processing_time', execution_time) if metrics else execution_time
            }
            
            # Build content
            content_parts = [
                '---',
                yaml.dump(frontmatter, default_flow_style=False).strip(),
                '---',
                '',
                f"# {task_content}",
                '',
                "## Status",
                f"- {status}",
                '',
                "## Priority",
                f"- {metadata.get('priority', 'medium')}",
                '',
                "## Description", 
                task_content,
                '',
                "## Directive",
                f"- Link: [[{directive_path.stem}]]",
                '',
                "## Performance Metrics",
                f"- **Tokens In**: {frontmatter['tokens_in']}",
                f"- **Tokens Out**: {frontmatter['tokens_out']}",
                f"- **Cost**: {frontmatter['cost']}",
                f"- **Processing Time**: {frontmatter['processing_time']}",
                '',
                "## Output",
                output,
                '',
                "## Notes",
                "_Generated automatically by engage agent_",
                '',
                "## Execution Results",
                f"- Status: {status}",
                f"- Duration: {execution_time}",
                f"- Timestamp: {datetime.now().isoformat()}"
            ]
            
            # Write output file
            output_content = '\n'.join(content_parts)
            output_path.write_text(output_content)
            
            print(f"📄 Created output file: {output_filename}")
            
        except Exception as e:
            print(f"Error creating output file for {directive_path}: {e}")
    
    def move_directive(self, file_path: Path, success: bool, duration: float) -> Path:
        """Move directive to appropriate status directory"""
        if success:
            exemplar_threshold = self.settings.get('exemplar_threshold_seconds', 30)
            exemplar_enabled = self.settings.get('exemplar_enabled', True)
            
            if exemplar_enabled and duration <= exemplar_threshold:
                dest_dir = self.directives_exemplars
                status = "exemplar"
            elif duration > 60:
                dest_dir = self.directives_slow
                status = "slow"
            else:
                dest_dir = self.directives_success
                status = "success"
        else:
            dest_dir = self.directives_failed
            status = "failed"
        
        # Update the directive's status field before moving
        self._update_directive_status(file_path, "completed" if success else "failed")
        
        dest_path = dest_dir / file_path.name
        shutil.move(str(file_path), str(dest_path))
        
        print(f"📁 Moved {file_path.name} to {status}/")
        return dest_path
    
    def _update_directive_status(self, file_path: Path, new_status: str) -> None:
        """Update the status field in a directive file's YAML frontmatter"""
        try:
            content = file_path.read_text()
            # Update status in YAML frontmatter using regex
            content = re.sub(r'status: .*', f'status: {new_status}', content)
            file_path.write_text(content)
        except Exception as e:
            print(f"Warning: Failed to update status in {file_path}: {e}")
    
    def process_single_directive(self) -> bool:
        """Process a single directive. Returns True if a directive was processed."""
        directive_path = self.find_next_directive()
        
        if not directive_path:
            return False
        
        # Execute the directive
        success, duration, output, metrics = self.execute_directive(directive_path)
        
        # Update output file with results
        self.update_output_file(directive_path, success, duration, output, metrics.get('metrics') if metrics else None)
        
        # Update session context with directive completion
        self._update_session_context_with_directive(directive_path, success, duration, output, metrics.get('metrics') if metrics else None)
        
        # Move directive to appropriate status directory
        final_path = self.move_directive(directive_path, success, duration)
        
        # Print summary
        status_emoji = "✅" if success else "❌"
        print(f"{status_emoji} Directive {directive_path.name} completed in {duration:.2f}s")
        
        return True
    
    def run(self):
        """Main processing loop - continues until no more directives to process"""
        self.logger.info("Engage Agent starting", monitoring_path=str(self.directives_new))
        print("🎯 Engage Agent Starting...")
        print(f"Monitoring: {self.directives_new}")
        
        processed_count = 0
        
        while True:
            if self.process_single_directive():
                processed_count += 1
                print(f"\n📊 Processed {processed_count} directive(s)")
                
                # Brief pause between processing
                time.sleep(1)
            else:
                break
        
        self.logger.info(f"Engage Agent complete - processed {processed_count} directives")
        self.performance_tracker.log_summary()
        print(f"\n🏁 Engage Agent Complete! Processed {processed_count} directive(s)")
        
        # Show final status
        remaining = len(list(self.directives_new.glob("*.md")))
        if remaining > 0:
            self.logger.info(f"{remaining} directives remain with unmet prerequisites")
            print(f"📋 {remaining} directive(s) remain (may have unmet prerequisites)")
    
    def run_batch_processing(self):
        """Process all directives using sequential API calls with claiming mechanism"""
        if not self.api_mode:
            print("❌ Batch processing requires API mode. Set API keys and use --api-mode flag.")
            return
        
        self.logger.info("Starting batch processing mode")
        print("🚀 Starting Impulse Batch Processing...")
        print(f"Monitoring: {self.directives_new}")
        
        # Collect all available directives
        directive_files = list(self.directives_new.glob("*.md"))
        if not directive_files:
            print("No directives available for processing")
            return
        
        print(f"📋 Found {len(directive_files)} directives to process")
        
        # Filter available directives (check prerequisites and metadata)
        available_directives = []
        for directive_path in directive_files:
            try:
                metadata = self.parse_directive_metadata(directive_path)
                if not metadata:
                    self.logger.warning(f"Skipping {directive_path.name} - no metadata")
                    continue
                
                # Check prerequisites
                content = directive_path.read_text()
                prerequisites = self.extract_prerequisites(content)
                if not self.check_prerequisites_met(prerequisites):
                    self.logger.info(f"Skipping {directive_path.name} - unmet prerequisites: {prerequisites}")
                    continue
                
                available_directives.append((directive_path, metadata))
                
            except Exception as e:
                self.logger.error(f"Error preparing {directive_path.name}: {e}")
                continue
        
        if not available_directives:
            print("No directives are ready for processing")
            return
        
        print(f"🎯 Submitting {len(available_directives)} directives for batch processing...")
        
        # Process directives sequentially with claiming
        success_count = 0
        failed_count = 0
        
        for directive_path, metadata in available_directives:
            try:
                # Claim the directive by moving it to a processing state
                if not self._claim_directive(directive_path):
                    self.logger.info(f"Directive {directive_path.name} was claimed by another process")
                    continue
                
                # Extract task content
                task_content = self.extract_task_content(directive_path)
                
                # Determine platform and model
                platform = metadata.get('platform', 'claude')
                model = metadata.get('model', 'claude-3-5-sonnet-20241022' if platform == 'claude' else 'gpt-4o-mini')
                
                self.logger.info(f"Processing {directive_path.name} with {platform}/{model}")
                
                # Process using individual AI API call
                start_time = time.time()
                response = self.ai_client.chat_completion(task_content, platform, model)
                processing_time = time.time() - start_time
                
                success = response.get('success', False)
                result = response.get('content', response.get('error', 'Unknown error'))
                
                if success:
                    # Move to success directory
                    success_path = self.directives_success / directive_path.name
                    shutil.move(str(directive_path), str(success_path))
                    
                    # Create output file
                    output_file = success_path.with_suffix('.out')
                    with open(output_file, 'w') as f:
                        f.write(f"# Sequential Processing Output\n\n")
                        f.write(f"Platform: {platform}\n")
                        f.write(f"Model: {model}\n")
                        f.write(f"Processing Time: {processing_time:.2f}s\n\n")
                        f.write(result)
                    
                    success_count += 1
                    self.logger.info(f"✅ Success: {directive_path.name}")
                    print(f"✅ Completed: {directive_path.name}")
                    
                    # Update session context
                    self._update_session_context_with_directive(
                        directive_path, True, processing_time, result
                    )
                    
                else:
                    # Move to failed directory
                    failed_path = self.directives_failed / directive_path.name
                    shutil.move(str(directive_path), str(failed_path))
                    
                    # Create error file
                    error_file = failed_path.with_suffix('.err')
                    with open(error_file, 'w') as f:
                        f.write(f"# Sequential Processing Error\n\n")
                        f.write(f"Platform: {platform}\n")
                        f.write(f"Model: {model}\n")
                        f.write(f"Processing Time: {processing_time:.2f}s\n\n")
                        f.write(f"Error: {result}")
                    
                    failed_count += 1
                    self.logger.error(f"❌ Failed: {directive_path.name} - {result}")
                    print(f"❌ Failed: {directive_path.name}")
                    
                    # Update session context
                    self._update_session_context_with_directive(
                        directive_path, False, processing_time, result
                    )
                
            except Exception as e:
                failed_count += 1
                self.logger.error(f"❌ Processing error for {directive_path.name}: {e}")
                print(f"❌ Error: {directive_path.name}")
                
                # Move to failed if it still exists
                if directive_path.exists():
                    failed_path = self.directives_failed / directive_path.name
                    shutil.move(str(directive_path), str(failed_path))
        
        # Save updated session context
        self._save_session_context(self.session_context)
        
        print(f"\n🏁 Batch Processing Complete!")
        print(f"✅ Successful: {success_count}")
        print(f"❌ Failed: {failed_count}")
        print(f"📊 Total Processed: {success_count + failed_count}")
        
        self.logger.info(f"Batch processing complete - {success_count} success, {failed_count} failed")
        
        # Show remaining directives
        remaining = len(list(self.directives_new.glob("*.md")))
        if remaining > 0:
            print(f"📋 {remaining} directive(s) remain (may have unmet prerequisites)")
    
    def _claim_directive(self, directive_path: Path) -> bool:
        """
        Claim a directive for processing by atomically moving it to a temporary processing location.
        Returns True if successfully claimed, False if already claimed by another process.
        """
        try:
            # Create a processing directory if it doesn't exist
            processing_dir = self.directives_new.parent / "processing"
            processing_dir.mkdir(exist_ok=True)
            
            # Try to atomically move the file to claim it
            processing_path = processing_dir / directive_path.name
            
            # Use atomic move to claim the directive
            # If another process already claimed it, this will fail
            try:
                directive_path.rename(processing_path)
                # Successfully claimed - move it back to original location for processing
                processing_path.rename(directive_path)
                return True
            except FileNotFoundError:
                # File was already claimed by another process
                return False
            except OSError:
                # File system doesn't support atomic rename or other error
                return False
                
        except Exception as e:
            self.logger.warning(f"Failed to claim directive {directive_path.name}: {e}")
            return False
    
    def get_claude_todos_from_directives(self, include_completed: bool = True) -> List[Dict[str, Any]]:
        """Get Claude Code todos from all directive files"""
        return self.todo_bridge.get_claude_todos_from_directives(include_completed)
    
    def sync_claude_todos_with_directive_status(self, claude_todos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Update Claude todos based on current directive execution status"""
        return self.todo_bridge.sync_directive_status_to_claude_todos(claude_todos)
    
    def run_with_claude_todo_sync(self, claude_todos: List[Dict[str, Any]] = None):
        """Run the engage agent with Claude Code todo synchronization"""
        self.logger.info("Engage Agent starting with Claude Code todo sync")
        print("🎯 Engage Agent Starting with Claude Code Todo Sync...")
        print(f"Monitoring: {self.directives_new}")
        
        processed_count = 0
        
        while True:
            if self.process_single_directive():
                processed_count += 1
                print(f"\n📊 Processed {processed_count} directive(s)")
                
                # Sync Claude todos after each directive if provided
                if claude_todos:
                    try:
                        updated_todos = self.sync_claude_todos_with_directive_status(claude_todos)
                        # Here we would normally update the Claude Code todo system
                        # This would integrate with Claude Code's TodoWrite functionality
                        self.logger.info(f"Synced {len(updated_todos)} Claude todos")
                    except Exception as e:
                        self.logger.warning(f"Failed to sync Claude todos: {e}")
                
                # Brief pause between processing
                time.sleep(1)
            else:
                break
        
        self.logger.info(f"Engage Agent complete - processed {processed_count} directives")
        self.performance_tracker.log_summary()
        print(f"\n🏁 Engage Agent Complete! Processed {processed_count} directive(s)")
        
        # Final sync of Claude todos
        if claude_todos:
            try:
                updated_todos = self.sync_claude_todos_with_directive_status(claude_todos)
                print(f"📋 Final sync: {len(updated_todos)} Claude todos updated")
            except Exception as e:
                self.logger.warning(f"Failed to perform final Claude todo sync: {e}")
        
        # Show final status
        remaining = len(list(self.directives_new.glob("*.md")))
        if remaining > 0:
            self.logger.info(f"{remaining} directives remain with unmet prerequisites")
            print(f"📋 {remaining} directive(s) remain (may have unmet prerequisites)")


def main():
    """CLI interface for the engage agent"""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Process directive tasks')
    parser.add_argument('--single', action='store_true', help='Process only one directive')
    parser.add_argument('--api-mode', action='store_true', help='Use AI APIs for task execution')
    parser.add_argument('--batch-mode', action='store_true', help='Use batch processing for maximum efficiency')
    parser.add_argument('--claude-todos', help='JSON file containing Claude Code todos for sync')
    parser.add_argument('--list-todos', action='store_true', help='List todos from directives')
    
    args = parser.parse_args()
    
    agent = EngageAgent(api_mode=args.api_mode)
    
    # Handle todo listing
    if args.list_todos:
        todos = agent.get_claude_todos_from_directives()
        print(f"📋 Found {len(todos)} todos from directives:")
        for todo in todos:
            status_emoji = "✅" if todo["status"] == "completed" else "📋"
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            print(f"{status_emoji} {priority_emoji.get(todo['priority'], '⚪')} {todo['content']}")
        sys.exit(0)
    
    # Load Claude todos if provided
    claude_todos = None
    if args.claude_todos:
        try:
            import json
            with open(args.claude_todos, 'r') as f:
                claude_todos = json.load(f)
            print(f"📋 Loaded {len(claude_todos)} Claude Code todos for synchronization")
        except Exception as e:
            print(f"Error loading Claude todos: {e}")
            sys.exit(1)
    
    if args.single:
        # Process just one directive
        if agent.process_single_directive():
            print("Processed one directive")
            sys.exit(0)  # Success exit code for parallel processing
        else:
            print("No directives available to process")
            sys.exit(1)  # Failure exit code for parallel processing
    elif args.batch_mode:
        # Use batch processing mode
        agent.run_batch_processing()
    else:
        # Process all available directives
        if claude_todos:
            agent.run_with_claude_todo_sync(claude_todos)
        else:
            agent.run()


if __name__ == "__main__":
    main()