#!/usr/bin/env python3
"""
Secure MCP Server - Exposes directive system status and handles quarantine requests
"""

import json
import asyncio
import hashlib
import time
from typing import Dict, List, Any, Optional, Sequence
from datetime import datetime, timezone
from pathlib import Path
import sys
import os

# Add lib directory to path
sys.path.append(str(Path(__file__).parent))

from secure_quarantine import SecureQuarantine, QuarantineValidator
from logger import get_logger

# MCP imports (assuming standard MCP library)
try:
    from mcp.server import Server, NotificationOptions
    from mcp.server.models import InitializationOptions
    from mcp.types import (
        Resource, Tool, TextContent, ImageContent, EmbeddedResource,
        JSONRPCMessage, CallToolRequest, ListResourcesRequest, ListToolsRequest,
        ReadResourceRequest, GetPromptRequest, ListPromptsRequest
    )
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    # Create mock classes for development
    class Server:
        def __init__(self, name: str, version: str): pass
        async def run(self): pass
    class Resource: pass
    class Tool: pass
    class TextContent: pass


class SecureMCPServer:
    """Secure MCP Server for Computer directive system"""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.logger = get_logger("mcp_server", base_path)
        self.quarantine = SecureQuarantine(base_path)
        
        # Security configuration
        self.config = self._load_security_config()
        self.auth_tokens = self._load_auth_tokens()
        self.rate_limits = {}  # IP -> {last_request, count}
        
        # Initialize MCP server
        self.server = Server(
            name="computer-directive-system",
            version="1.0.0"
        ) if MCP_AVAILABLE else None
        
        # Register handlers if MCP is available
        if MCP_AVAILABLE and self.server:
            self._register_mcp_handlers()
    
    def _load_security_config(self) -> Dict[str, Any]:
        """Load MCP server security configuration"""
        config_path = self.base_path / ".mcp-server-config.json"
        default_config = {
            "require_authentication": True,
            "allowed_origins": ["localhost", "127.0.0.1", "::1"],
            "rate_limit_requests_per_minute": 60,
            "max_quarantine_size": 1024 * 1024,  # 1MB
            "audit_all_requests": True,
            "expose_sensitive_data": False,
            "read_only_mode": True  # Only expose status, no modifications
        }
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                config = default_config.copy()
                config.update(user_config)
                return config
            except Exception as e:
                self.logger.error(f"Failed to load MCP config: {e}")
        
        return default_config
    
    def _load_auth_tokens(self) -> Dict[str, Dict[str, Any]]:
        """Load authentication tokens"""
        tokens_path = self.base_path / ".mcp-auth-tokens.json"
        if tokens_path.exists():
            try:
                with open(tokens_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to load auth tokens: {e}")
        
        # Generate default token for localhost
        default_token = hashlib.sha256(f"computer-{time.time()}".encode()).hexdigest()
        default_tokens = {
            default_token: {
                "name": "default-localhost",
                "origins": ["localhost", "127.0.0.1"],
                "permissions": ["read_status", "quarantine_prompt"],
                "created": datetime.now(timezone.utc).isoformat()
            }
        }
        
        # Save default tokens
        try:
            with open(tokens_path, 'w') as f:
                json.dump(default_tokens, f, indent=2)
            os.chmod(str(tokens_path), 0o600)
            self.logger.info(f"Generated default MCP auth token: {default_token}")
        except Exception as e:
            self.logger.error(f"Failed to save default tokens: {e}")
        
        return default_tokens
    
    def _audit_log(self, action: str, client_info: Dict[str, Any], details: Dict[str, Any], success: bool = True):
        """Audit log all MCP interactions"""
        if not self.config["audit_all_requests"]:
            return
        
        audit_path = self.base_path / "logs" / "mcp_audit.log"
        audit_path.parent.mkdir(exist_ok=True)
        
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "client": client_info,
            "details": details,
            "success": success
        }
        
        try:
            with open(audit_path, 'a') as f:
                f.write(json.dumps(log_entry, separators=(',', ':')) + '\n')
        except Exception as e:
            self.logger.error(f"Failed to write MCP audit log: {e}")
        
        # Also log to main logger
        level = self.logger.info if success else self.logger.error
        level(f"MCP {action}: {details}")
    
    def _authenticate_request(self, headers: Dict[str, str], origin: str) -> Optional[Dict[str, Any]]:
        """Authenticate MCP request"""
        if not self.config["require_authentication"]:
            return {"name": "anonymous", "permissions": ["read_status"]}
        
        auth_header = headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header[7:]  # Remove "Bearer "
        token_info = self.auth_tokens.get(token)
        
        if not token_info:
            return None
        
        # Check origin
        if origin not in token_info.get("origins", []):
            return None
        
        return token_info
    
    def _check_rate_limit(self, client_id: str) -> bool:
        """Check rate limiting"""
        now = time.time()
        minute_ago = now - 60
        
        if client_id not in self.rate_limits:
            self.rate_limits[client_id] = {"requests": [], "blocked_until": 0}
        
        client_limits = self.rate_limits[client_id]
        
        # Check if currently blocked
        if now < client_limits["blocked_until"]:
            return False
        
        # Clean old requests
        client_limits["requests"] = [req_time for req_time in client_limits["requests"] if req_time > minute_ago]
        
        # Check limit
        if len(client_limits["requests"]) >= self.config["rate_limit_requests_per_minute"]:
            client_limits["blocked_until"] = now + 60  # Block for 1 minute
            return False
        
        # Record this request
        client_limits["requests"].append(now)
        return True
    
    def _get_directive_status(self) -> Dict[str, Any]:
        """Get directive system status (read-only)"""
        try:
            # Count files in each directory
            directives_base = self.base_path / "directives"
            
            status = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "directives": {},
                "processing_modes": {
                    "impulse_available": True,
                    "warp_available": True,
                    "single_available": True
                },
                "quarantine": self.quarantine.get_quarantine_stats()
            }
            
            # Count directive files
            for category in ["new", "success", "failed", "slow", "possible-exemplars"]:
                category_path = directives_base / category
                if category_path.exists():
                    count = len(list(category_path.glob("*.md")))
                    status["directives"][category] = count
                else:
                    status["directives"][category] = 0
            
            # Check API availability (without exposing keys)
            api_status = {}
            if os.getenv('ANTHROPIC_API_KEY'):
                api_status["claude"] = "configured"
            else:
                api_status["claude"] = "missing"
            
            if os.getenv('OPENAI_API_KEY'):
                api_status["openai"] = "configured"
            else:
                api_status["openai"] = "missing"
            
            status["api_status"] = api_status
            
            # Batch processing status
            batch_dir = directives_base / "batches"
            if batch_dir.exists():
                batch_files = len(list(batch_dir.glob("*")))
                status["batch_processing"] = {
                    "active_batches": batch_files,
                    "batch_directory": str(batch_dir)
                }
            
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get directive status: {e}")
            return {"error": "Failed to retrieve status"}
    
    def _register_mcp_handlers(self):
        """Register MCP protocol handlers"""
        
        @self.server.list_resources()
        async def handle_list_resources() -> List[Resource]:
            """List available resources"""
            return [
                Resource(
                    uri="computer://directive-status",
                    name="Directive System Status",
                    description="Current status of the Computer directive processing system",
                    mimeType="application/json"
                ),
                Resource(
                    uri="computer://quarantine-stats",
                    name="Quarantine Statistics",
                    description="Statistics about quarantined prompts",
                    mimeType="application/json"
                )
            ]
        
        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """Read resource content"""
            client_info = {"origin": "unknown", "action": "read_resource"}
            
            if uri == "computer://directive-status":
                self._audit_log("READ_DIRECTIVE_STATUS", client_info, {"uri": uri})
                status = self._get_directive_status()
                return json.dumps(status, indent=2)
            
            elif uri == "computer://quarantine-stats":
                self._audit_log("READ_QUARANTINE_STATS", client_info, {"uri": uri})
                stats = self.quarantine.get_quarantine_stats()
                return json.dumps(stats, indent=2)
            
            else:
                self._audit_log("READ_RESOURCE_FAILED", client_info, {"uri": uri, "reason": "not_found"}, success=False)
                raise ValueError(f"Unknown resource: {uri}")
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available tools"""
            return [
                Tool(
                    name="quarantine_prompt",
                    description="Safely quarantine an untrusted prompt for review",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "The prompt content to quarantine (will NOT be executed)",
                                "maxLength": QuarantineValidator.MAX_PROMPT_SIZE
                            },
                            "source": {
                                "type": "string", 
                                "description": "Source identifier for the prompt",
                                "maxLength": 256
                            },
                            "metadata": {
                                "type": "object",
                                "description": "Optional metadata about the prompt",
                                "additionalProperties": True
                            }
                        },
                        "required": ["prompt", "source"]
                    }
                ),
                Tool(
                    name="get_directive_status",
                    description="Get current directive processing system status",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls"""
            client_info = {"origin": "unknown", "tool": name}
            
            try:
                # Rate limiting
                if not self._check_rate_limit("unknown"):
                    self._audit_log("TOOL_CALL_RATE_LIMITED", client_info, {"tool": name}, success=False)
                    return [TextContent(type="text", text="Rate limit exceeded. Please wait before trying again.")]
                
                if name == "quarantine_prompt":
                    prompt = arguments.get("prompt", "")
                    source = arguments.get("source", "unknown")
                    metadata = arguments.get("metadata")
                    
                    self._audit_log("QUARANTINE_REQUEST", client_info, {
                        "source": source,
                        "prompt_length": len(prompt),
                        "has_metadata": metadata is not None
                    })
                    
                    # Quarantine the prompt
                    result = self.quarantine.quarantine_prompt(prompt, source, metadata)
                    
                    if result:
                        response = f"Prompt safely quarantined as: {result}\n"
                        response += "⚠️  Content has been stored UNINTERPRETED for manual review.\n"
                        response += "Use CLI quarantine commands to review safely."
                        
                        self._audit_log("QUARANTINE_SUCCESS", client_info, {
                            "filename": result,
                            "source": source
                        })
                    else:
                        response = "Failed to quarantine prompt. Check validation requirements."
                        self._audit_log("QUARANTINE_FAILED", client_info, {"source": source}, success=False)
                    
                    return [TextContent(type="text", text=response)]
                
                elif name == "get_directive_status":
                    self._audit_log("STATUS_REQUEST", client_info, {})
                    status = self._get_directive_status()
                    return [TextContent(type="text", text=json.dumps(status, indent=2))]
                
                else:
                    self._audit_log("UNKNOWN_TOOL", client_info, {"tool": name}, success=False)
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
                    
            except Exception as e:
                self._audit_log("TOOL_ERROR", client_info, {"tool": name, "error": str(e)}, success=False)
                return [TextContent(type="text", text=f"Tool error: {str(e)}")]
    
    async def start_server(self, host: str = "localhost", port: int = 8765):
        """Start the secure MCP server"""
        if not MCP_AVAILABLE:
            self.logger.error("MCP library not available. Install with: pip install mcp")
            return
        
        self.logger.info(f"Starting secure MCP server on {host}:{port}")
        self._audit_log("SERVER_START", {"host": host, "port": port}, {})
        
        try:
            await self.server.run(host=host, port=port)
        except Exception as e:
            self.logger.error(f"MCP server error: {e}")
            self._audit_log("SERVER_ERROR", {"host": host, "port": port}, {"error": str(e)}, success=False)


# CLI interface for MCP server
async def main():
    """Main entry point for MCP server"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Secure MCP Server for Computer directive system")
    parser.add_argument("--host", default="localhost", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind to")
    parser.add_argument("--base-path", default=".", help="Base path for directive system")
    
    args = parser.parse_args()
    
    server = SecureMCPServer(args.base_path)
    await server.start_server(args.host, args.port)


if __name__ == "__main__":
    asyncio.run(main())