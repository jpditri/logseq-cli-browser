# Engage Agent Creation Prompt

Create a Python "engage" agent that processes directive files by priority and age, executing tasks and managing their lifecycle. The agent should:

## 1. Directory Structure
Create these status directories if they don't exist:
- `/directives/new/` - pending directives to process
- `/directives/success/` - completed directives (under 60s)
- `/directives/slow/` - completed directives (over 60s) 
- `/directives/failed/` - failed directives

## 2. Core Processing Logic

**Priority System**: Process directives by:
1. **Highest priority first** (high > medium > low)
2. **Oldest first** within same priority (by file creation time)
3. **Prerequisites met** (all linked dependencies completed)

**Prerequisites Detection**: Parse directive content for various prerequisite patterns:
- `Prerequisites: task1, task2`
- `Depends on: other-task` 
- `Requires: setup-task`
- `Needs: foundation-work`
- Logseq-style links: `[[task-name]]`

**Prerequisites Validation**: Check that all prerequisite tasks exist in `/directives/success/` before processing.

## 3. File Processing

**Metadata Parsing**: Extract YAML frontmatter from directive files:
```yaml
---
id: task-12345678
status: pending
priority: high
created: 2023-12-01T10:30:00
slug: implement-user-auth
---
```

**Task Extraction**: Parse directive content to extract:
- Main task description from `## Prompt` section
- Fallback to metadata content or title
- Clean task content for execution

## 4. Execution Engine

**Task Execution**:
- Create temporary Python scripts for task execution
- Execute with 5-minute timeout
- Capture stdout, stderr, and execution time
- Handle exceptions and timeouts gracefully

**Execution Results**: Track three outcomes:
- **Success + Fast** (< 60s) → `/directives/success/`
- **Success + Slow** (≥ 60s) → `/directives/slow/`
- **Failed/Timeout** → `/directives/failed/`

## 5. Output File Management

**Update Output Files**: Find and update corresponding `*-output*.md` files with:
- Execution status (✅ Completed / ❌ Failed)
- Execution duration
- Complete output/error logs
- Execution timestamp
- Move output file to same directory as processed directive

**Template Variable Replacement**:
- Replace `{{OUTPUT_CONTENT}}` with execution results
- Update status fields with actual results
- Add execution metadata section

## 6. File Movement and Tracking

**Directive Lifecycle**:
1. Find next eligible directive in `/directives/new/`
2. Execute the task
3. Update corresponding output file
4. Move both directive and output files to appropriate status directory
5. Log results and continue to next directive

**Cross-Reference Maintenance**: Ensure logseq links remain valid after file moves.

## 7. CLI Interface

**Main Mode**: `python engage_agent.py`
- Process all available directives continuously
- Stop when no eligible directives remain
- Show progress and final summary

**Single Mode**: `python engage_agent.py --single`
- Process exactly one directive
- Useful for testing or manual control

## 8. Logging and Feedback

**Real-time Progress**:
- Show directive being processed
- Display task content preview (first 100 chars)
- Report execution time and status
- Track total processed count

**Final Summary**:
- Total directives processed
- Count remaining (may have unmet prerequisites)
- Status breakdown (success/slow/failed)

## 9. Error Handling

**Robust Processing**:
- Handle malformed directive files gracefully
- Continue processing if one directive fails to parse
- Clean up temporary files after execution
- Validate file operations before moving files

**Prerequisites Edge Cases**:
- Handle circular dependencies
- Skip directives with missing prerequisites
- Report prerequisite validation failures

## 10. Dependencies

**Required Imports**:
- `yaml` for frontmatter parsing
- `subprocess` for task execution
- `pathlib` for file operations
- `shutil` for file moving
- Standard libraries: `os`, `re`, `time`, `datetime`, `tempfile`

## Implementation Notes

- Use proper exception handling throughout
- Ensure atomic file operations (complete or rollback)
- Maintain clean separation between parsing, execution, and file management
- Design for extensibility (pluggable execution engines)
- Include comprehensive docstrings and type hints
- Handle edge cases like empty directories, permission errors, etc.

The agent should run continuously until all eligible directives are processed, providing clear feedback and maintaining data integrity throughout the process.