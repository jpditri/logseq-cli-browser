# Computer Task Manager

An advanced task management and directive processing system that combines semantic analysis with automated workflow execution using AI APIs. Features a dual-agent system for intelligent task breakdown and automated execution.

## Overview

This project implements a dual-agent system for creating and processing task directives:

- **Directive Agent**: Analyzes prompts and creates structured task directives with dependencies and AI platform requirements
- **Engage Agent**: Processes directives in priority order using Claude or OpenAI APIs for task execution
- **Parallel Processing**: Execute multiple directives simultaneously across different AI sessions

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/your-username/computer.git
cd computer

# Install Python dependencies
pip install -r requirements.txt

# Install development dependencies (optional)
pip install -e ".[dev]"

# Install Ruby dependencies for CLI
bundle install
```

### Using pip

```bash
pip install computer-task-manager
```

## Directory Structure

```
computer/
├── bin/
│   └── computer           # Main Ruby command interface
├── agents/                # Python agent implementations
│   ├── directive_agent.py # Creates directives from prompts
│   └── engage_agent.py    # Processes and executes directives
├── lib/                   # Python library modules
│   ├── ai_client.py       # AI API client for Claude and OpenAI
│   ├── config_validator.py # Configuration validation
│   ├── database.py        # SQLite database management
│   ├── interactive.py     # Interactive mode handling
│   ├── logger.py          # Logging utilities
│   ├── security.py        # Security and API key management
│   ├── settings.py        # Application settings
│   └── template_manager.py # Template file management
├── templates/             # Template files for directives
│   ├── api-project.md     # API project template
│   ├── code-review.md     # Code review template
│   ├── directive-out.md   # Output template for completed directives
│   ├── directive-prompt.md # Directive creation template
│   ├── directives-prompt.md # Multi-directive template
│   ├── engage-agent-prompt.md # Engage agent template
│   └── user/             # User-specific templates
├── directives/            # Task directive storage
│   ├── new/              # Pending directives
│   ├── success/          # Successfully completed directives
│   ├── failed/           # Failed directives
│   ├── slow/             # Slow-running directives (>60s)
│   └── possible-exemplars/ # Example/reference directives
├── tests/                # Test suite
│   ├── test_ai_client.py
│   ├── test_directive_agent.py
│   └── test_settings.py
├── pyproject.toml        # Python package configuration
├── requirements.txt      # Python dependencies
├── Gemfile              # Ruby dependencies
└── computer.db          # SQLite database
```

## Quick Start

### Prerequisites

Set up your AI API keys:

```bash
export ANTHROPIC_API_KEY="your-claude-api-key"
export OPENAI_API_KEY="your-openai-api-key"
```

### Using the Ruby Command Interface

```bash
# Create directives with platform requirements
./bin/computer directive --text "Create a REST API" --platform claude --model claude-3-sonnet
./bin/computer directive --text "Write unit tests" --platform openai --model gpt-4

# Read prompt from file
./bin/computer directive --file prompt.txt

# Process directives with AI
./bin/computer engage                    # Process all directives
./bin/computer engage --single           # Process one directive  
./bin/computer engage --parallel 4       # Process with 4 parallel threads
```

### Direct Python Usage

```bash
# Create directives with platform/model requirements
python agents/directive_agent.py "Build REST API" --platform claude --model claude-3-sonnet
python agents/directive_agent.py "Write tests" --platform openai --model gpt-4

# Process directives with AI APIs
python agents/engage_agent.py --api-mode             # Process all with AI
python agents/engage_agent.py --api-mode --single    # Process one with AI

# Test AI connections
python lib/ai_client.py
```

## How It Works

### Directive Agent

1. **Prompt Analysis**: Breaks down complex prompts into actionable todo items
2. **Priority Assignment**: Automatically assigns priorities based on keywords
3. **Dependency Detection**: Creates prerequisite chains between related tasks
4. **Platform Requirements**: Embeds AI platform and model requirements
5. **File Generation**: Creates structured markdown files with YAML frontmatter

### Engage Agent

1. **Priority Processing**: Selects highest priority tasks first
2. **Dependency Resolution**: Ensures prerequisites are met before execution
3. **AI Execution**: Sends tasks to Claude or OpenAI APIs based on requirements
4. **Parallel Processing**: Supports multiple concurrent AI sessions
5. **Status Tracking**: Moves completed tasks to appropriate directories
6. **Output Management**: Updates output files with AI responses and execution results

## Directive File Format

Directives use YAML frontmatter with structured content:

```markdown
---
id: task-abc123
status: pending
priority: high
created: 2024-01-01T12:00:00
slug: create-user-auth
platform: claude
model: claude-3-sonnet
---

# Directive: Create user authentication system

## Prerequisites
- [[setup-database-task-xyz]]
- [[create-user-model-task-abc]]

## AI Requirements
- **Platform**: claude
- **Model**: claude-3-sonnet

## Prompt
[Detailed task description and instructions]

### Outputs
- Link to output: [[create-user-auth-output_1704110400]]
```

## Features

- **AI-Powered Execution**: Tasks processed using Claude or OpenAI APIs
- **Platform Selection**: Specify required AI platform (Claude/OpenAI) per directive
- **Model Requirements**: Choose specific models (claude-3-sonnet, gpt-4, etc.)
- **Parallel Processing**: Execute multiple directives simultaneously across AI sessions
- **Smart Priority Handling**: Keywords like "urgent", "critical" automatically increase priority
- **Dependency Management**: Tasks can specify prerequisites using wiki-style links
- **Timeout Protection**: Long-running tasks are moved to slow directory
- **Error Recovery**: Failed tasks are tracked and can be retried
- **Structured Output**: All results are captured in structured markdown files
- **Claude Code Integration**: Seamless integration with Claude Code's TodoRead/TodoWrite functionality
- **Todo Synchronization**: Bidirectional sync between Claude Code todos and directive execution

## API Configuration

### Development and Testing

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=agents --cov=lib

# Format code
black agents/ lib/ tests/

# Type checking
mypy agents/ lib/

# Linting
flake8 agents/ lib/ tests/
```

### Dependencies

**Python packages:**
- `requests>=2.31.0` - HTTP client for AI API calls
- `PyYAML>=6.0.1` - YAML parsing for directive frontmatter
- `pytest>=7.4.0` - Testing framework
- `black>=23.7.0` - Code formatting
- `mypy>=1.5.0` - Static type checking

**Ruby gems:**
- `concurrent-ruby` - Parallel processing support

### Environment Variables

```bash
export ANTHROPIC_API_KEY="your-claude-api-key"
export OPENAI_API_KEY="your-openai-api-key"
```

### Supported Models

**Claude (Anthropic):**
- `claude-3-opus-20240229` - Most capable
- `claude-3-sonnet-20240229` - Balanced performance
- `claude-3-haiku-20240307` - Fast and efficient

**OpenAI:**
- `gpt-4` - Most capable GPT-4
- `gpt-4-turbo` - Latest GPT-4 variant
- `gpt-3.5-turbo` - Fast and cost-effective

## CLI Reference

### Directive Agent Options

```bash
./bin/computer directive [options]
  -t, --text TEXT          Prompt text to process
  -f, --file FILE          File containing prompt text  
  -p, --platform PLATFORM Required platform (claude, openai)
  -m, --model MODEL        Required model name
```

### Engage Agent Options  

```bash
./bin/computer engage [options]
  -s, --single             Process only one directive
  -j, --parallel THREADS   Number of parallel processing threads
```

## Project Architecture

### Core Components

- **Agents**: Python modules that handle task analysis and execution
- **Templates**: Markdown templates for generating structured directives
- **Library**: Shared Python modules for AI clients, database, security, etc.
- **CLI**: Ruby command-line interface for user interaction
- **Database**: SQLite database for persistent storage
- **Directives**: Structured task files with YAML frontmatter

### Design Principles

- **Modularity**: Separate concerns between directive creation and execution
- **Flexibility**: Support multiple AI platforms and models
- **Scalability**: Parallel processing for handling multiple tasks
- **Traceability**: Full audit trail of task processing and outcomes
- **Extensibility**: Plugin-style architecture for new features

## Claude Code Integration

This system includes full integration with Claude Code's TodoRead/TodoWrite functionality. You can:

- Convert Claude Code todos into structured directives
- Process todos using AI agents with automatic status synchronization  
- Maintain bidirectional sync between todos and directive execution

For detailed integration instructions and examples, see **[CLAUDE_CODE_INTEGRATION.md](CLAUDE_CODE_INTEGRATION.md)**.

### Quick Todo Integration Example

```bash
# Create directives from Claude Code todos
./bin/computer todo create -f my_todos.json

# Process with automatic status sync
./bin/computer todo sync -f my_todos.json

# View todo status
./bin/computer todo status
```

## Contributing

This is an experimental AI-powered task management system inspired by the computer interfaces from Star Trek. Like the Enterprise's computer, it provides an intelligent interface for complex task management and execution.

### Development Setup

1. Fork and clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run tests: `pytest`
4. Follow code style: `black agents/ lib/ tests/`

### Areas for Contribution

- New AI platform integrations
- Enhanced directive templates
- Improved dependency resolution algorithms
- Additional output formats
- Performance optimizations
- Documentation improvements

Feel free to extend the agents, add new AI platforms, or modify the directive format to suit your workflow needs.