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
- **Neon Cassette Futurism UI**: Retro-futuristic, hacker-style terminal interface inspired by cassette futurism aesthetics.
- **Matrix Theme**: Green-on-black color scheme with optional "falling code" animations for that "let's hack the planet" vibe.
- **Gothic Library UI**: Candlelit, ominous typewriter-style color scheme evoking Poe’s writing desk or Hunter S. Thompson’s study.
- **Startup Splash & Quotes**: Theme-specific ASCII art banners and random witty quotes on launch
- **Animated Intros**: Confetti for cassette, falling code for matrix, cryptic effects for gothic themes
- **Top HUD Panel**: Always-visible header with time, theme, and context information (current file or page directory)
- **Chat Persona**: Distinctive AI persona name and icon per theme for more personality

## Themes

- **cassette** — Neon‑magenta cassette‑futurism UI (default)
- **matrix** — Green‑on‑black code rain animation
- **gothic** — Candlelit, ominous library/typewriter palette

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
# Default (cassette theme):
./bin/logseq-browser

# Matrix theme (falling code animation):
./bin/logseq-browser --theme=matrix

# Gothic Library theme (candlelit, ominous look):
./bin/logseq-browser --theme=gothic

# Suppress portrait (chat-only mode):
./bin/logseq-browser --no-portrait

# Or via environment variable:
LOGSEQ_CLI_THEME=gothic LOGSEQ_CLI_NO_PORTRAIT=1 ./bin/logseq-browser /path/to/your/pages
```

### Key Bindings

**Page List View:**
- `j/k` - Navigate up/down through pages
- `o` or `Enter` - Open selected page
- `:q` - Quit application
- `T` - Open theme selection popup

**Page Content View:**
- `j/k` - Navigate up/down through content lines
- `o` or `Enter` - Follow link on current line (if any)
- `b` - Go back to previous page
- `e` - Edit current page in your default editor
- `:q` - Return to page list (or quit if already in list view)
- `T` - Open theme selection popup (change UI theme)


### Chat Commands

- `:chat` - open interactive chat popup (with portrait animation and conversation history)
- `:theme` - open theme selection popup to switch themes interactively
- Prefix your message with `/insert ` to have the AI response inserted at the current cursor location; otherwise the response is only displayed in the chat popup.

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
- /search functionality would be nice
- Maybe <TAB> between links
- More advanced logseq out of the box
- - /query
- - Related Items (linked/unlinked)
- Export a limited subgraph based on [[page]]s or #tags

## License

This project is released into the public domain. See [LICENSE](LICENSE) for details.
