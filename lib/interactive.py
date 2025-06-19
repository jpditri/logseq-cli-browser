#!/usr/bin/env python3
"""
Interactive REPL mode for Computer project
"""

import cmd
import sys
import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add local modules to path
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent.parent / "agents"))

from settings import get_settings
from logger import get_logger
from database import get_database
from directive_agent import DirectiveAgent
from engage_agent import EngageAgent


class ComputerREPL(cmd.Cmd):
    """Interactive REPL for Computer task management system"""
    
    intro = """
╔══════════════════════════════════════════════════════════════╗
║                 🖥️  Computer Interactive Mode                ║
║                                                              ║
║   Advanced Task Management & Directive Processing System    ║
║                                                              ║
║   Type 'help' for available commands                        ║
║   Type 'quit' to exit                                       ║
╚══════════════════════════════════════════════════════════════╝
"""
    
    prompt = "computer> "
    
    def __init__(self, base_path: str = "."):
        super().__init__()
        self.base_path = Path(base_path)
        self.settings = get_settings(str(base_path))
        self.logger = get_logger("computer_repl", str(base_path))
        self.db = get_database(str(self.base_path / "computer.db"))
        
        # Initialize agents
        self.directive_agent = DirectiveAgent(str(base_path))
        self.engage_agent = EngageAgent(str(base_path), api_mode=True)
        
        # Track session state
        self.session_stats = {
            'directives_created': 0,
            'directives_processed': 0,
            'start_time': datetime.now()
        }
        
        self.logger.info("Interactive REPL session started")
    
    def do_create(self, line):
        """Create a new directive from text.
        Usage: create <prompt text>
        Example: create Build a REST API for user management
        """
        if not line.strip():
            print("❌ Please provide a prompt. Usage: create <prompt text>")
            return
        
        try:
            platform = self.settings.get('default_platform', 'claude')
            model = self.settings.get('default_model', 'claude-3-sonnet')
            
            print(f"📝 Creating directive with {platform}/{model}...")
            
            result = self.directive_agent.process_prompt(
                line.strip(), 
                platform=platform, 
                model=model
            )
            
            self.session_stats['directives_created'] += len(result['todos'])
            
            print(f"✅ Created {len(result['todos'])} directive(s):")
            for i, todo in enumerate(result['todos'], 1):
                print(f"   {i}. [{todo['priority']}] {todo['content'][:60]}...")
            
            print(f"\n📁 Files created in directives/new/:")
            for file in result['files_created']['directives']:
                print(f"   - {file}")
            
        except Exception as e:
            print(f"❌ Error creating directive: {e}")
            self.logger.error(f"REPL create error: {e}")
    
    def do_process(self, line):
        """Process pending directives.
        Usage: process [single|all]
        Example: process single
        """
        mode = line.strip().lower() or 'single'
        
        if mode not in ['single', 'all']:
            print("❌ Invalid mode. Use 'single' or 'all'")
            return
        
        try:
            if mode == 'single':
                print("🚀 Processing one directive...")
                success = self.engage_agent.process_single_directive()
                if success:
                    self.session_stats['directives_processed'] += 1
                    print("✅ Directive processed successfully")
                else:
                    print("ℹ️  No directives available to process")
            else:
                print("🚀 Processing all directives...")
                initial_count = self.session_stats['directives_processed']
                self.engage_agent.run()
                processed = self.session_stats['directives_processed'] - initial_count
                print(f"✅ Processed {processed} directives")
        
        except Exception as e:
            print(f"❌ Error processing directive: {e}")
            self.logger.error(f"REPL process error: {e}")
    
    def do_status(self, line):
        """Show system status and directive counts.
        Usage: status [detailed]
        """
        detailed = line.strip().lower() == 'detailed'
        
        print("📊 Computer System Status")
        print("=" * 50)
        
        # Count directives in each directory
        directories = {
            'new': 'pending',
            'success': 'completed',
            'failed': 'failed', 
            'slow': 'slow',
            'possible-exemplars': 'exemplars'
        }
        
        total_directives = 0
        for dir_name, status_name in directories.items():
            dir_path = self.base_path / 'directives' / dir_name
            if dir_path.exists():
                count = len(list(dir_path.glob('*.md')))
                total_directives += count
                
                status_emoji = {
                    'pending': '🆕', 'completed': '✅', 'failed': '❌',
                    'slow': '🐌', 'exemplars': '⭐'
                }.get(status_name, '📄')
                
                print(f"{status_emoji} {status_name.capitalize().ljust(12)}: {count}")
        
        print(f"\n📈 Total Directives: {total_directives}")
        
        # Session stats
        duration = datetime.now() - self.session_stats['start_time']
        print(f"\n🕐 Session Stats:")
        print(f"   Duration: {duration}")
        print(f"   Created: {self.session_stats['directives_created']}")
        print(f"   Processed: {self.session_stats['directives_processed']}")
        
        # API status
        claude_key = os.getenv('ANTHROPIC_API_KEY')
        openai_key = os.getenv('OPENAI_API_KEY')
        print(f"\n🔑 API Keys:")
        print(f"   Claude: {'✅ Configured' if claude_key else '❌ Missing'}")
        print(f"   OpenAI: {'✅ Configured' if openai_key else '❌ Missing'}")
        
        if detailed:
            # Database stats
            try:
                stats = self.db.get_summary_stats()
                if stats:
                    print(f"\n📊 Database Stats:")
                    if 'totals' in stats:
                        totals = stats['totals']
                        print(f"   Total Cost: ${totals.get('total_cost', 0):.2f}")
                        print(f"   Total Tokens: {totals.get('total_tokens_in', 0):,} in, {totals.get('total_tokens_out', 0):,} out")
                        print(f"   Avg Time: {totals.get('avg_processing_time', 0):.1f}s")
            except Exception as e:
                print(f"   Database stats unavailable: {e}")
    
    def do_list(self, line):
        """List directives by status.
        Usage: list [status] [limit]
        Example: list pending 5
        """
        parts = line.strip().split()
        status = parts[0] if parts else 'pending'
        limit = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 10
        
        # Map status names to directory names
        status_map = {
            'pending': 'new',
            'new': 'new',
            'success': 'success', 
            'completed': 'success',
            'failed': 'failed',
            'slow': 'slow',
            'exemplars': 'possible-exemplars'
        }
        
        dir_name = status_map.get(status, status)
        dir_path = self.base_path / 'directives' / dir_name
        
        if not dir_path.exists():
            print(f"❌ Invalid status: {status}")
            return
        
        files = list(dir_path.glob('*.md'))
        files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        print(f"📋 {status.capitalize()} Directives (showing {min(limit, len(files))} of {len(files)}):")
        print("-" * 60)
        
        for i, file in enumerate(files[:limit], 1):
            # Try to extract title from filename
            name = file.stem
            if 'output' not in name:
                # Get file modification time
                mtime = datetime.fromtimestamp(file.stat().st_mtime)
                print(f"{i:2d}. {name[:45]:<45} {mtime.strftime('%m/%d %H:%M')}")
    
    def do_settings(self, line):
        """Show or modify settings.
        Usage: settings [key] [value]
        Example: settings default_platform claude
        """
        parts = line.strip().split(maxsplit=2)
        
        if not parts:
            # Show all settings
            print("⚙️  Current Settings:")
            print("-" * 40)
            for key, value in sorted(self.settings.to_dict().items()):
                print(f"{key:<25}: {value}")
        
        elif len(parts) == 1:
            # Show specific setting
            key = parts[0]
            value = self.settings.get(key)
            if value is not None:
                print(f"{key}: {value}")
            else:
                print(f"❌ Setting '{key}' not found")
        
        elif len(parts) == 2:
            # Set setting value
            key, value = parts
            try:
                # Type conversion
                if value.lower() in ('true', 'false'):
                    value = value.lower() == 'true'
                elif value.isdigit():
                    value = int(value)
                elif '.' in value and value.replace('.', '').replace('-', '').isdigit():
                    value = float(value)
                
                self.settings.set(key, value)
                print(f"✅ Set {key} = {value}")
            except Exception as e:
                print(f"❌ Error setting {key}: {e}")
        else:
            print("❌ Usage: settings [key] [value]")
    
    def do_clean(self, line):
        """Clean old directive files.
        Usage: clean [days] [--confirm]
        Example: clean 30 --confirm
        """
        parts = line.strip().split()
        days = 30
        confirm = False
        
        for part in parts:
            if part.isdigit():
                days = int(part)
            elif part == '--confirm':
                confirm = True
        
        print(f"🧹 Cleaning files older than {days} days...")
        
        if not confirm:
            print("❓ Add --confirm to actually delete files")
            print("   This will show what would be deleted:")
        
        # Find old files
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        total_files = 0
        
        for status_dir in ['success', 'failed', 'slow']:
            dir_path = self.base_path / 'directives' / status_dir
            if not dir_path.exists():
                continue
            
            old_files = []
            for file in dir_path.glob('*.md'):
                if file.stat().st_mtime < cutoff:
                    old_files.append(file)
            
            if old_files:
                print(f"\n📁 {status_dir}/:")
                for file in old_files:
                    mtime = datetime.fromtimestamp(file.stat().st_mtime)
                    print(f"   - {file.name} ({mtime.strftime('%Y-%m-%d')})")
                    if confirm:
                        file.unlink()
                
                total_files += len(old_files)
        
        if total_files == 0:
            print("✨ No old files found")
        elif confirm:
            print(f"✅ Deleted {total_files} old files")
        else:
            print(f"📊 Would delete {total_files} files (use --confirm)")
    
    def do_export(self, line):
        """Export directive data.
        Usage: export [format] [filename]
        Example: export csv report.csv
        """
        parts = line.strip().split()
        format_type = parts[0] if parts else 'json'
        filename = parts[1] if len(parts) > 1 else f"computer_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format_type}"
        
        if format_type not in ['json', 'csv']:
            print("❌ Supported formats: json, csv")
            return
        
        try:
            # Collect directive data
            data = []
            for status_dir in ['new', 'success', 'failed', 'slow', 'possible-exemplars']:
                dir_path = self.base_path / 'directives' / status_dir
                if not dir_path.exists():
                    continue
                
                for file in dir_path.glob('*.md'):
                    if 'output' not in file.name:
                        mtime = datetime.fromtimestamp(file.stat().st_mtime)
                        data.append({
                            'name': file.name,
                            'status': status_dir,
                            'modified': mtime.isoformat(),
                            'path': str(file)
                        })
            
            # Write export file
            output_path = self.base_path / filename
            
            if format_type == 'json':
                with open(output_path, 'w') as f:
                    json.dump(data, f, indent=2)
            else:  # csv
                import csv
                with open(output_path, 'w', newline='') as f:
                    if data:
                        writer = csv.DictWriter(f, fieldnames=data[0].keys())
                        writer.writeheader()
                        writer.writerows(data)
            
            print(f"✅ Exported {len(data)} directives to {filename}")
            
        except Exception as e:
            print(f"❌ Export error: {e}")
            self.logger.error(f"REPL export error: {e}")
    
    def do_quit(self, line):
        """Exit the interactive mode."""
        duration = datetime.now() - self.session_stats['start_time']
        print(f"\n👋 Session complete!")
        print(f"   Duration: {duration}")
        print(f"   Created: {self.session_stats['directives_created']} directives")
        print(f"   Processed: {self.session_stats['directives_processed']} directives")
        self.logger.info("Interactive REPL session ended", **self.session_stats)
        return True
    
    def do_exit(self, line):
        """Exit the interactive mode."""
        return self.do_quit(line)
    
    def do_help(self, line):
        """Show help for commands."""
        if line:
            super().do_help(line)
        else:
            print("\n📚 Available Commands:")
            print("-" * 50)
            commands = [
                ("create <prompt>", "Create new directive from text"),
                ("process [single|all]", "Process pending directives"),
                ("status [detailed]", "Show system status"),
                ("list [status] [limit]", "List directives by status"),
                ("settings [key] [value]", "Show or modify settings"),
                ("clean [days] [--confirm]", "Clean old directive files"),
                ("export [format] [file]", "Export directive data"),
                ("help [command]", "Show command help"),
                ("quit/exit", "Exit interactive mode")
            ]
            
            for cmd, desc in commands:
                print(f"  {cmd:<20} - {desc}")
            
            print(f"\n💡 Tips:")
            print(f"  - Use Tab for command completion")
            print(f"  - Commands can be abbreviated (e.g., 'st' for 'status')")
            print(f"  - Use 'help <command>' for detailed help")
    
    def emptyline(self):
        """Handle empty line input."""
        pass
    
    def default(self, line):
        """Handle unknown commands."""
        print(f"❌ Unknown command: {line}")
        print("   Type 'help' for available commands")


def start_interactive_mode(base_path: str = "."):
    """Start the interactive REPL mode"""
    try:
        repl = ComputerREPL(base_path)
        repl.cmdloop()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Interactive mode error: {e}")


if __name__ == "__main__":
    start_interactive_mode()