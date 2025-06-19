# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is the "Computer" project - an advanced task management and directive processing system that combines semantic analysis with automated workflow execution. It provides intelligent task breakdown and automated execution capabilities.

## Project Architecture

The project implements a dual-agent system:

- **Directive Agent** (`agents/directive_agent.py`): Analyzes prompts and creates structured task directives
- **Engage Agent** (`agents/engage_agent.py`): Processes directives in priority order with dependency resolution
- **Ruby CLI** (`bin/computer`): Command-line interface for both agents

## Directory Structure

```
├── bin/computer           # Main Ruby command interface
├── agents/                # Python agent implementations  
├── templates/             # Template files for directives
├── directives/            # Task directive storage (new/success/failed/slow/possible-exemplars)
└── lib/                   # Ruby library code (future use)
```

## Development Workflow

### Running the System

```bash
# Create directives with AI platform requirements
./bin/computer directive --text "Your task" --platform claude --model claude-3-sonnet
./bin/computer directive --file prompt.txt --platform openai --model gpt-4

# Process directives with AI APIs (requires API keys)
./bin/computer engage                    # Process all directives
./bin/computer engage --single           # Process one directive  
./bin/computer engage --parallel 4       # Process with 4 parallel threads
```

### Direct Python Usage

```bash
# Create directives with platform/model requirements
python agents/directive_agent.py "Your prompt" --platform claude --model claude-3-sonnet

# Process directives with AI APIs
python agents/engage_agent.py --api-mode [--single]

# Test AI connections
python lib/ai_client.py
```

### API Setup

```bash
# Required environment variables
export ANTHROPIC_API_KEY="your-claude-api-key"
export OPENAI_API_KEY="your-openai-api-key"

# Required Python packages
pip install requests pyyaml

# Required Ruby gems  
gem install concurrent-ruby
```

## Testing

Currently no formal testing framework. Manual testing via CLI commands.

## Technologies

- **Python 3**: Core agent logic with YAML frontmatter and markdown processing
- **Ruby**: CLI interface, command parsing, and parallel processing
- **Claude API**: Anthropic's Claude for AI task execution
- **OpenAI API**: GPT models for AI task execution  
- **Markdown**: Directive file format with YAML frontmatter
- **YAML**: Metadata and configuration format

## Project Context

This Computer system implements advanced task processing through:
- Semantic analysis of natural language prompts
- Automatic task breakdown and dependency detection  
- Priority-based processing with prerequisite resolution
- AI-powered task execution with platform selection
- Parallel processing across multiple AI sessions
- Structured knowledge representation in markdown format

It provides an intelligent interface for complex task management and execution.