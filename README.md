# Logseq CLI Browser

A Ruby-based command-line interface for browsing and navigating Logseq markdown pages with vim-like keybindings.

## Overview

This project provides a terminal-based browser for navigating through Logseq markdown files. It features vim-like navigation, automatic page creation, and support for both wiki-style `[[links]]` and markdown `[links](file.md)`.

## Features

- **Vim-like Navigation**: Use `j/k` to move up/down, `o` to open pages/follow links
- **Page Discovery**: Automatically discovers all `.md` files in the pages directory
- **Link Following**: Supports both `[[wiki-style]]` and `[markdown](links.md)` formats
- **Auto Page Creation**: Creates new pages when following links to non-existent pages  
- **History Navigation**: Use `b` to go back through visited pages
- **File Editing**: Press `e` to edit the current page in your preferred editor
- **Terminal Optimized**: Responsive interface that adapts to terminal size

## Installation

### Prerequisites

- Ruby (version 2.7 or higher)
- A text editor (vim, nano, etc.) for editing pages

### Setup

```bash
# Clone the repository
git clone https://github.com/your-username/logseq-cli-browser.git
cd logseq-cli-browser

# Install Ruby dependencies (if any)
bundle install

# Make the CLI executable
chmod +x bin/logseq-browser
```

## Usage

### Basic Navigation

```bash
# Navigate pages in the current 'pages' directory
./bin/logseq-browser

# Navigate pages in a specific directory
./bin/logseq-browser /path/to/your/pages
```

### Key Bindings

**Page List View:**
- `j/k` - Navigate up/down through pages
- `o` or `Enter` - Open selected page
- `:q` - Quit application

**Page Content View:**
- `j/k` - Navigate up/down through content lines
- `o` or `Enter` - Follow link on current line (if any)
- `b` - Go back to previous page
- `e` - Edit current page in your default editor
- `:q` - Return to page list (or quit if already in list view)

### Environment Variables

- `EDITOR` - Set your preferred text editor (defaults to vim)

```bash
export EDITOR=nano
./bin/logseq-browser
```

## Directory Structure

```
├── bin/
│   └── logseq-browser    # Main Ruby CLI application
├── pages/                # Default pages directory (created if needed)
├── templates/            # Template files
├── Gemfile              # Ruby gem dependencies
└── lib/                 # Ruby library code (future use)
```

## How It Works

1. **Page Discovery**: Scans the specified directory for `.md` files
2. **Content Parsing**: Extracts wiki-style `[[links]]` and markdown `[links](file.md)`
3. **Navigation**: Provides vim-like interface for browsing content
4. **Link Resolution**: Automatically resolves links to existing pages or creates new ones
5. **File Management**: Integrates with your system's text editor for content modification

## Page Format

The browser works with standard markdown files and recognizes:

- **Wiki-style links**: `[[Page Name]]` - Links to pages by name
- **Markdown links**: `[Link Text](filename.md)` - Links to specific files
- **Standard Markdown**: Headers, lists, code blocks, etc.

## Development

### Technologies

- **Ruby**: Primary development language for CLI and navigation
- **Markdown**: Page content format  
- **Terminal**: Uses Ruby's IO.console for terminal interaction

### Architecture

- Single Ruby file containing the complete CLI browser
- Object-oriented design with clear separation of concerns
- No external dependencies beyond Ruby standard library

## Contributing

This is a simple, focused tool for browsing Logseq pages from the terminal. Contributions are welcome for:

- Performance improvements
- Additional navigation features
- Better link resolution
- Enhanced markdown parsing
- Bug fixes and stability improvements

## License

This project is released into the public domain. See [LICENSE](LICENSE) for details.