---
author: Computer System
category: system
created: '2025-06-18T20:25:36.821109'
description: Standard directive prompt template
name: Directive Prompt
variables:
- TASK_CONTENT
- PRIORITY_LEVEL
version: '1.0'
---

# Task: {{TASK_CONTENT}}

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
- Document any trade-offs or decisions made