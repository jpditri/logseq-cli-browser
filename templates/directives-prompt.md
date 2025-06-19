# Directive Agent Creation Prompt

Create a Python agent that takes a prompt, generates a todo list, and creates interconnected logseq-style markdown files. The agent should:

1. **Directory Structure**: Create these directories if they don't exist:
   - `/directives/new/` - for directive files
   - `/pages/templates/` - for template files

2. **Template File**: Create `/pages/templates/directive-out.md` with this content:
   ```markdown
   ---
   slug: {{TASK_SLUG}}
   status: {{STATUS}}
   priority: {{PRIORITY}}
   created: {{CREATED_DATE}}
   directive: [[{{DIRECTIVE_FILE}}]]
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

   ## Output
   {{OUTPUT_CONTENT}}

   ## Notes
   {{ADDITIONAL_NOTES}}
   ```

3. **Main Agent**: Create `directive_agent.py` that:
   - Analyzes input prompts and breaks them into actionable todo items
   - Creates URL-friendly slugs from task content
   - Determines priority (high/medium/low) based on keywords like "urgent", "critical", "later", "optional"
   - Generates detailed completion instructions for each task
   - Creates two interconnected files for each todo:

   **Directive File** (`{slug}-{task-id}.md`):
   - Logseq-style frontmatter with id, status, priority, created timestamp, slug
   - Task details section
   - Prerequisites section with logseq-style links to previous tasks (each task depends on all previous tasks in the todo list)
   - Expanded prompt with detailed completion instructions
   - Links to corresponding output file under "### Outputs"

   **Output File** (`{slug}-output_{unix_timestamp}.md`):
   - Uses the template with variable substitution
   - Links back to the directive file
   - Includes unix timestamp in filename for uniqueness

4. **Features**:
   - CLI interface: `python directive_agent.py "Your prompt here"`
   - Cross-linking between directive and output files
   - Automatic todo list generation with IDs, status (pending), and priorities
   - Sequential dependency tracking (each task depends on completion of all previous tasks)
   - Detailed prompt expansion with analysis, implementation, and documentation phases
   - Results summary showing created todos and files

5. **File Naming**:
   - Directive files: `{slug}-{task-id}.md`
   - Output files: `{slug}-output_{unix_timestamp}.md`
   - All files created in `/directives/new/`

The agent should handle edge cases like empty prompts, create meaningful slugs, and ensure proper cross-referencing between all generated files.