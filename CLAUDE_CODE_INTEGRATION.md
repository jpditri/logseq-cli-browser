# Claude Code Integration Guide

This document describes the integration between Claude Code's todo system and the Computer directive processing system.

## Overview

The Computer system now provides seamless integration with Claude Code's TodoRead/TodoWrite functionality, allowing users to:

- Convert Claude Code todos into Computer directives for AI-powered execution
- Maintain bidirectional synchronization between todo status and directive completion
- Preserve context and dependencies across related tasks
- Leverage AI platforms (Claude, OpenAI) for intelligent task processing

## Architecture

### Components

1. **TodoDirectiveBridge** (`lib/todo_directive_bridge.py`)
   - Converts between Claude Code todos and Computer directives
   - Manages priority mapping and status synchronization
   - Handles context persistence across sessions

2. **Enhanced Directive Agent** (`agents/directive_agent.py`)
   - Creates directives from Claude Code todos
   - Supports LLM-powered prompt decomposition
   - Integrates with Claude-specific templates

3. **Enhanced Engage Agent** (`agents/engage_agent.py`)
   - Processes directives with context awareness
   - Syncs completion status back to Claude Code todos
   - Maintains session context for related tasks

4. **Ruby CLI** (`bin/computer`)
   - Provides `todo` command with subcommands
   - Handles JSON import/export of todos
   - Integrates with existing directive workflow

## Usage Guide

### 1. Basic Todo-to-Directive Workflow

```bash
# Export todos from Claude Code (using TodoRead)
# Save as todos.json

# Create directives from todos
./bin/computer todo create -f todos.json

# Process directives with AI
./bin/computer engage

# Check status
./bin/computer todo status
```

### 2. Advanced Workflow with Platform Requirements

```bash
# Create directives with specific AI platform
./bin/computer directive --claude-todos todos.json --platform claude --model claude-3-sonnet

# Process with parallel execution
./bin/computer engage --parallel 4 --claude-todos todos.json

# Export results back to Claude Code format
./bin/computer todo export > completed_todos.json
```

### 3. Interactive Todo Management

```bash
# List todos from directives
./bin/computer todo list

# Show todo status overview
./bin/computer todo status

# Sync Claude todos with directive status
./bin/computer todo sync -f todos.json
```

## File Formats

### Claude Code Todo Format

```json
[
  {
    "id": "todo-123",
    "content": "Implement user authentication system",
    "status": "pending",
    "priority": "high"
  },
  {
    "id": "todo-124", 
    "content": "Write unit tests for auth module",
    "status": "pending",
    "priority": "medium"
  }
]
```

### Generated Directive Example

```markdown
---
id: directive-1703123456-a1b2c3d4
created_at: 2024-12-19T10:30:00
platform: claude
model: claude-3-sonnet
urgency: urgent
completion_criteria: comprehensive
claude_todo_id: todo-123
session_id: session-1703123456
todo_index: 0
total_todos: 2
---

# Directive: Implement user authentication system

## Claude Code Integration
- **Claude Todo ID**: todo-123
- **Task ID**: directive-1703123456-a1b2c3d4
- **Session**: session-1703123456
- **Position**: 1 of 2
- **Priority**: Urgent

## Task Overview
Implement user authentication system

## Success Criteria
- Feature works as specified
- Edge cases are handled
- Code is well-documented with comments
- Performance implications considered
- Security considerations addressed
- Integration with existing systems verified

...
```

### Session Context Format

```json
{
  "session_id": "session-1703123456",
  "created_at": "2024-12-19T10:30:00",
  "todos": [...],
  "directive_mappings": {
    "todo-123": "directive-1703123456-a1b2c3d4"
  },
  "completed_directives": [
    {
      "directive_id": "directive-1703123456-a1b2c3d4",
      "task": "Implement user authentication system",
      "success": true,
      "duration": 45.2,
      "claude_todo_id": "todo-123",
      "summary": "Successfully implemented JWT-based authentication...",
      "metrics": {
        "tokens_in": 1200,
        "tokens_out": 800,
        "cost": 0.0156
      }
    }
  ],
  "knowledge_base": {}
}
```

## Priority Mapping

| Claude Code Priority | Computer Urgency | Completion Criteria |
|---------------------|------------------|-------------------|
| `high`              | `urgent`         | comprehensive     |
| `medium`            | `normal`         | standard         |
| `low`               | `low`            | basic            |

## Context Persistence

The system maintains context across related todos through:

### Session Context Files
- Stored in `directives/context/session-{timestamp}.json`
- Contains completed work summaries
- Tracks dependencies and relationships
- Preserves knowledge base entries

### Context Injection
When processing directives, the system automatically includes:
- Previously completed work in the session
- Related todo information
- Prerequisites and dependencies
- Accumulated knowledge from prior executions

## AI Platform Integration

### Supported Platforms
- **Claude** (Anthropic): `claude-3-opus`, `claude-3-sonnet`, `claude-3-haiku`
- **OpenAI**: `gpt-4`, `gpt-4-turbo`, `gpt-3.5-turbo`

### Configuration
```bash
export ANTHROPIC_API_KEY="your-claude-api-key"
export OPENAI_API_KEY="your-openai-api-key"
```

### Cost Tracking
The system tracks:
- Input/output token usage
- Estimated costs per directive
- Platform and model utilization
- Performance metrics

## Command Reference

### Todo Management Commands

```bash
# List todos from directive system
./bin/computer todo list

# Show comprehensive todo status
./bin/computer todo status

# Create directives from Claude Code todos
./bin/computer todo create -f todos.json

# Sync todo status with directive completion
./bin/computer todo sync -f todos.json
```

### Directive Agent Commands

```bash
# Process Claude Code todos directly
python agents/directive_agent.py --claude-todos todos.json

# Use LLM decomposition for complex prompts
python agents/directive_agent.py "Create a web app" --use-llm --platform claude

# List available templates
python agents/directive_agent.py --list-templates

# Sync todos with directive status
python agents/directive_agent.py --sync-todos
```

### Engage Agent Commands

```bash
# Process directives with Claude todo sync
python agents/engage_agent.py --claude-todos todos.json

# List todos from directives
python agents/engage_agent.py --list-todos

# Process in API mode with AI execution
python agents/engage_agent.py --api-mode
```

## Template System

### Claude-Specific Template
The system includes a specialized template (`templates/claude-todo.md`) that:
- Maintains Claude Code todo metadata
- Provides structured implementation guidelines
- Includes priority-based success criteria
- Supports session context integration

### Template Variables
- `{{CLAUDE_TODO_ID}}` - Original Claude Code todo ID
- `{{TASK_CONTENT}}` - Todo content/description
- `{{PRIORITY_LEVEL}}` - Mapped priority level
- `{{SESSION_ID}}` - Session identifier
- `{{TODO_INDEX}}` - Position in todo sequence
- `{{COMPLETION_CRITERIA}}` - Generated success criteria

## Integration Workflows

### Workflow 1: Simple Todo Processing
1. Export todos from Claude Code using `TodoRead`
2. Save to JSON file
3. Create directives: `./bin/computer todo create -f todos.json`
4. Process: `./bin/computer engage`
5. Import results back to Claude Code using `TodoWrite`

### Workflow 2: Advanced AI Processing
1. Export todos with priority and dependency information
2. Create directives with platform requirements
3. Process with parallel execution and context preservation
4. Review results and sync status back to Claude Code
5. Continue with dependent todos based on completion status

### Workflow 3: Interactive Development
1. Use `./bin/computer todo status` to monitor progress
2. Process todos incrementally with `./bin/computer engage --single`
3. Review context and adjust approach based on previous results
4. Maintain continuous sync with Claude Code todo system

## Best Practices

### Todo Organization
- Use clear, actionable todo descriptions
- Set appropriate priorities for processing order
- Group related todos in logical sequences
- Include context information in todo content

### Session Management
- Process related todos in the same session for context sharing
- Review session context before starting complex task sequences
- Archive completed sessions for future reference
- Clean up old context files periodically

### AI Platform Selection
- Use Claude for complex reasoning and analysis tasks
- Use OpenAI for code generation and technical implementation
- Consider cost vs. capability trade-offs for different priorities
- Test with different models for optimal results

### Error Handling
- Monitor directive failures and adjust approach
- Review failed directives for common patterns
- Use context from previous attempts to improve retry success
- Maintain backup of todo state before bulk processing

## Troubleshooting

### Common Issues

**Todos not converting to directives**
- Check JSON format validity
- Verify required fields (id, content, status, priority)
- Ensure file permissions and path accessibility

**Directives not processing**
- Check API key configuration
- Verify platform/model availability
- Review prerequisite dependencies
- Check system resource availability

**Context not persisting**
- Verify `directives/context/` directory exists
- Check file permissions for context files
- Ensure session IDs are consistent
- Review context file format validity

**Status sync failing**
- Verify Claude todo IDs match directive metadata
- Check session context file integrity
- Ensure proper todo-directive mapping
- Review bridge configuration

### Debug Commands

```bash
# Check system status
./bin/computer status

# List available templates
./bin/computer template list

# Show directive metadata
python -c "from lib.todo_directive_bridge import TodoDirectiveBridge; print(TodoDirectiveBridge().get_claude_todos_from_directives())"

# Check session context
ls -la directives/context/
cat directives/context/session-latest.json
```

## API Reference

### TodoDirectiveBridge Class

```python
from lib.todo_directive_bridge import TodoDirectiveBridge

bridge = TodoDirectiveBridge(".")

# Convert todos to directives
directive_ids = bridge.claude_todos_to_directives(todos, "claude", "claude-3-sonnet")

# Sync todo status
bridge.sync_todo_status("todo-123", "directive-456", "completed")

# Get todo context
context = bridge.get_todo_context("todo-123")

# Convert directives back to todos
todos = bridge.directives_to_claude_todos(directive_ids)
```

### DirectiveAgent Integration

```python
from agents.directive_agent import DirectiveAgent

agent = DirectiveAgent()

# Process Claude Code todos
results = agent.process_claude_todos(todos, "claude", "claude-3-sonnet")

# Sync todo status
updated_todos = agent.sync_claude_todos_with_directives(todos)

# Get todos from directives
todos = agent.get_claude_todos_from_directives()
```

### EngageAgent Integration

```python
from agents.engage_agent import EngageAgent

agent = EngageAgent(api_mode=True)

# Run with todo sync
agent.run_with_claude_todo_sync(claude_todos)

# Get todos from directives
todos = agent.get_claude_todos_from_directives()
```

## Performance Considerations

### Token Usage Optimization
- Use appropriate models for task complexity
- Leverage context efficiently without over-inclusion
- Monitor cost accumulation for large todo sets
- Consider batch processing for related tasks

### Processing Efficiency
- Use parallel processing for independent todos
- Process dependent todos in sequence
- Cache context information to reduce redundant processing
- Archive completed sessions to maintain performance

### Resource Management
- Monitor disk usage for context and directive files
- Clean up old sessions and completed directives
- Use appropriate timeouts for long-running tasks
- Balance parallel processing with system resources

## Future Enhancements

### Planned Features
- Real-time bidirectional sync with Claude Code
- Advanced dependency analysis and resolution
- Machine learning-based priority optimization
- Integration with external project management tools

### Extension Points
- Custom template creation for specific todo types
- Plugin system for additional AI platforms
- Webhook integration for automatic processing
- Dashboard for monitoring todo processing status

---

This integration provides a powerful bridge between Claude Code's interactive todo management and the Computer system's AI-powered directive processing, enabling sophisticated task automation while maintaining full user control and visibility.