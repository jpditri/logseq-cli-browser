---
template_name: claude-todo
description: Template for Claude Code todo directives with enhanced context
category: todo-management
variables:
  - CLAUDE_TODO_ID
  - TASK_CONTENT
  - PRIORITY_LEVEL
  - TASK_ID
  - SESSION_ID
  - COMPLETION_CRITERIA
  - TODO_INDEX
  - TOTAL_TODOS
  - PLATFORM
  - MODEL
created: "{{CREATED_DATE}}"
---

# Directive: {{TASK_CONTENT}}

## Claude Code Integration
- **Claude Todo ID**: {{CLAUDE_TODO_ID}}
- **Task ID**: {{TASK_ID}}
- **Session**: {{SESSION_ID}}
- **Position**: {{TODO_INDEX}} of {{TOTAL_TODOS}}
- **Priority**: {{PRIORITY_LEVEL}}

## Task Overview
{{TASK_CONTENT}}

## Context
This directive was generated from a Claude Code todo item. It maintains full integration with Claude Code's todo management system for status synchronization and progress tracking.

{{#TODO_INDEX}}
{{#if (gt TODO_INDEX 0)}}
### Prerequisites
This task depends on the completion of previous tasks in the sequence. Check that all prerequisite todos have been completed successfully before proceeding.
{{/if}}
{{/TODO_INDEX}}

## Success Criteria
{{COMPLETION_CRITERIA}}

## Implementation Guidelines

### 1. Analysis Phase
- Break down the task into specific, actionable steps
- Identify any dependencies or prerequisites  
- Consider integration points with existing systems
- Document any assumptions or constraints

### 2. Implementation Phase
- Follow established coding standards and conventions
- Implement incrementally with regular testing
- Document code with clear comments and explanations
- Consider error handling and edge cases

### 3. Validation Phase
- Test thoroughly with various scenarios
- Verify all success criteria are met
- Check integration with related components
- Validate performance and security considerations

### 4. Documentation Phase  
- Document what was implemented and why
- Include examples and usage instructions
- Note any limitations or known issues
- Provide guidance for future maintenance

## AI Processing Requirements
- **Platform**: {{PLATFORM}}
- **Model**: {{MODEL}}

## Output Expectations
Your response should include:

1. **Implementation Summary**
   - Clear description of what was accomplished
   - Key decisions made and rationale
   - Any challenges encountered and solutions

2. **Code/Artifacts**
   - All code, configurations, or files created
   - Proper formatting and documentation
   - Test cases and validation results

3. **Integration Notes**
   - How this integrates with existing systems
   - Any setup or configuration required
   - Dependencies or prerequisites for others

4. **Next Steps**
   - Recommendations for follow-up work
   - Potential improvements or optimizations
   - Related tasks that should be considered

## Quality Standards
- All code must be production-ready and well-documented
- Follow security best practices and input validation
- Ensure compatibility with existing systems and conventions
- Include appropriate error handling and logging
- Provide clear examples and usage documentation

## Session Context
This task is part of a larger session with {{TOTAL_TODOS}} total tasks. Previous work in this session may provide important context for this implementation. Consider how this task builds upon or relates to prior completed work.

---

**Note**: This directive will be processed by the Computer system's AI agents and results will be synchronized back to Claude Code's todo system for seamless integration.