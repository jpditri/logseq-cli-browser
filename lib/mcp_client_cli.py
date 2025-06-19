#!/usr/bin/env python3
"""
MCP Client CLI - Command line interface for MCP peer management
"""

import sys
import argparse
import asyncio
import json
from pathlib import Path

# Add lib directory to path
sys.path.append(str(Path(__file__).parent))

from secure_mcp_client import SecureMCPClient, MCPClientSecurityValidator


def list_trusted_servers(client: SecureMCPClient):
    """List all trusted MCP servers"""
    servers = client.list_trusted_servers()
    
    if not servers:
        print("📭 No trusted servers configured")
        print()
        print("Add a server with: computer mcp add -n <name> -u <url>")
        return
    
    print(f"🌐 Trusted MCP Servers ({len(servers)})")
    print("="*60)
    print()
    
    for name, info in servers.items():
        config = info["config"]
        
        # Status indicators
        enabled_emoji = "✅" if config.get("enabled", False) else "⏸️"
        blocked_emoji = "🚫" if info.get("blocked", False) else ""
        rate_limited_emoji = "🐌" if info.get("rate_limited", False) else ""
        
        print(f"{enabled_emoji} {name} {blocked_emoji}{rate_limited_emoji}")
        print(f"   🌐 URL: {config['url']}")
        print(f"   📅 Added: {config.get('added_timestamp', 'Unknown')}")
        print(f"   🔗 Active Connections: {info.get('active_connections', 0)}")
        print(f"   ⚙️  Operations: {', '.join(config.get('allowed_operations', []))}")
        
        if not config.get("enabled", False):
            print("   ⚠️  Disabled - enable in configuration file")
        
        print()
    
    print("Configuration files:")
    print("• Trusted servers: .mcp-trusted-servers.json")
    print("• Client config: .mcp-client-config.json")


async def connect_to_peer(client: SecureMCPClient, server_name: str, timeout: int = 30):
    """Connect to a peer server and request a prompt"""
    print(f"🔗 Connecting to peer server: {server_name}")
    print(f"⏱️  Timeout: {timeout} seconds")
    print("⚠️  Any received prompts will be QUARANTINED for review")
    print()
    
    try:
        quarantine_filename = await client.accept_prompt_from_peer(server_name, timeout)
        
        if quarantine_filename:
            print(f"✅ Prompt received and quarantined: {quarantine_filename}")
            print()
            print("🔍 Next steps:")
            print(f"   computer quarantine review -f {quarantine_filename}")
            print(f"   computer quarantine approve -f {quarantine_filename} -r YOUR_NAME")
            print()
            print("⚠️  Remember: NEVER execute quarantined content without review!")
        else:
            print("❌ Failed to receive prompt from peer")
            print("   Check server status and connection")
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")


async def get_peer_status(client: SecureMCPClient, server_name: str):
    """Get status from a peer server"""
    print(f"📊 Getting status from: {server_name}")
    print()
    
    try:
        status = await client.get_peer_server_status(server_name)
        
        if status:
            print("✅ Server Status:")
            print(json.dumps(status, indent=2))
        else:
            print("❌ Failed to get server status")
            print("   Server may be offline or unreachable")
            
    except Exception as e:
        print(f"❌ Status request failed: {e}")


def add_trusted_server(client: SecureMCPClient, name: str, url: str):
    """Add a new trusted server"""
    print(f"➕ Adding trusted server: {name}")
    print(f"🌐 URL: {url}")
    print()
    
    # Validate URL
    if not MCPClientSecurityValidator.validate_server_url(url):
        print("❌ Invalid server URL")
        print("   Only localhost URLs are allowed for security")
        print("   Examples: ws://localhost:8766, wss://127.0.0.1:8080")
        return
    
    if client.add_trusted_server(name, url, enabled=False):
        print("✅ Server added successfully")
        print()
        print("⚠️  Server is DISABLED by default for security")
        print("   To enable, edit .mcp-trusted-servers.json and set 'enabled': true")
        print()
        print("Next steps:")
        print(f"   1. Review server configuration: .mcp-trusted-servers.json")
        print(f"   2. Enable the server: set 'enabled': true")
        print(f"   3. Test connection: computer mcp connect -n {name}")
    else:
        print("❌ Failed to add server")
        print("   Check if name already exists or server limit exceeded")


def show_mcp_status(client: SecureMCPClient):
    """Show overall MCP system status"""
    print("📊 MCP SYSTEM STATUS")
    print("="*50)
    print()
    
    # Load configurations
    try:
        config_path = Path(".mcp-client-config.json")
        if config_path.exists():
            with open(config_path, 'r') as f:
                client_config = json.load(f)
        else:
            client_config = {"status": "default configuration"}
        
        print("⚙️  Client Configuration:")
        print(f"   Auto-quarantine: {client_config.get('auto_quarantine_prompts', True)}")
        print(f"   Rate limit: {client_config.get('rate_limit_per_minute', 30)}/min")
        print(f"   Connection timeout: {client_config.get('connection_timeout', 30)}s")
        print(f"   Require auth: {client_config.get('require_server_authentication', False)}")
        print()
        
    except Exception as e:
        print(f"⚠️  Error reading client config: {e}")
        print()
    
    # Server summary
    servers = client.list_trusted_servers()
    enabled_count = sum(1 for s in servers.values() if s["config"].get("enabled", False))
    blocked_count = sum(1 for s in servers.values() if s.get("blocked", False))
    
    print("🌐 Server Summary:")
    print(f"   Total servers: {len(servers)}")
    print(f"   Enabled: {enabled_count}")
    print(f"   Blocked: {blocked_count}")
    print(f"   Available: {enabled_count - blocked_count}")
    print()
    
    # Security status
    print("🔒 Security Status:")
    print("   ✅ Localhost-only connections enforced")
    print("   ✅ All prompts automatically quarantined")
    print("   ✅ Input validation enabled")
    print("   ✅ Rate limiting active")
    print("   ✅ Audit logging enabled")
    print()
    
    # Log files
    log_dir = Path("logs")
    if log_dir.exists():
        audit_log = log_dir / "mcp_client_audit.log"
        quarantine_log = log_dir / "quarantine_audit.log"
        
        print("📋 Log Files:")
        if audit_log.exists():
            size = audit_log.stat().st_size
            print(f"   MCP Client: {audit_log} ({size:,} bytes)")
        if quarantine_log.exists():
            size = quarantine_log.stat().st_size
            print(f"   Quarantine: {quarantine_log} ({size:,} bytes)")
        print()
    
    # Quarantine status
    try:
        from secure_quarantine import SecureQuarantine
        quarantine = SecureQuarantine()
        stats = quarantine.get_quarantine_stats()
        
        print("🔒 Quarantine Status:")
        print(f"   Total files: {stats['total_files']}")
        print(f"   Pending review: {stats['pending_count']}")
        print(f"   Reviewed: {stats['reviewed_count']}")
        print()
        
        if stats['pending_count'] > 0:
            print("⚠️  ACTION REQUIRED:")
            print(f"   {stats['pending_count']} quarantined prompts need review")
            print("   Use: computer quarantine list")
            print()
            
    except Exception as e:
        print(f"⚠️  Cannot access quarantine status: {e}")
        print()


async def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="MCP client management CLI")
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List trusted servers')
    
    # Connect command
    connect_parser = subparsers.add_parser('connect', help='Connect to peer and get prompt')
    connect_parser.add_argument('server_name', help='Name of trusted server')
    connect_parser.add_argument('--timeout', type=int, default=30, help='Connection timeout in seconds')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Add trusted server')
    add_parser.add_argument('server_name', help='Name for the server')
    add_parser.add_argument('server_url', help='Server WebSocket URL')
    
    # Status command (specific server)
    status_parser = subparsers.add_parser('peer-status', help='Get status from peer server')
    status_parser.add_argument('server_name', help='Name of trusted server')
    
    # System status command
    system_parser = subparsers.add_parser('status', help='Show MCP system status')
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Initialize MCP client
    try:
        client = SecureMCPClient()
    except Exception as e:
        print(f"❌ Failed to initialize MCP client: {e}")
        sys.exit(1)
    
    # Execute command
    try:
        if args.command == 'list':
            list_trusted_servers(client)
        elif args.command == 'connect':
            await connect_to_peer(client, args.server_name, args.timeout)
        elif args.command == 'add':
            add_trusted_server(client, args.server_name, args.server_url)
        elif args.command == 'peer-status':
            await get_peer_status(client, args.server_name)
        elif args.command == 'status':
            show_mcp_status(client)
        else:
            print(f"❌ Unknown command: {args.command}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n👋 Operation cancelled by user")
    except Exception as e:
        print(f"❌ Command failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())