#!/usr/bin/env python3
"""
Secure MCP Client - Safely connects to trusted local MCP servers and quarantines prompts
"""

import json
import asyncio
import hashlib
import time
import re
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timezone
from pathlib import Path
import sys
import ssl

# Add lib directory to path
sys.path.append(str(Path(__file__).parent))

# Optional import for websockets
try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    websockets = None

from secure_quarantine import SecureQuarantine, QuarantineValidator
from logger import get_logger


class MCPClientSecurityValidator:
    """Strict security validation for MCP client interactions"""
    
    # Security limits for MCP interactions
    MAX_RESPONSE_SIZE = 2 * 1024 * 1024  # 2MB max response
    MAX_SERVER_COUNT = 10                # Max trusted servers
    MAX_CONNECTIONS_PER_SERVER = 3       # Max concurrent connections
    CONNECTION_TIMEOUT = 30              # 30 second timeout
    
    # Allowed server patterns (localhost only)
    ALLOWED_SERVER_PATTERNS = [
        r'^ws://localhost:[0-9]{1,5}$',
        r'^ws://127\.0\.0\.1:[0-9]{1,5}$',
        r'^ws://\[::1\]:[0-9]{1,5}$',
        r'^wss://localhost:[0-9]{1,5}$',
        r'^wss://127\.0\.0\.1:[0-9]{1,5}$',
        r'^wss://\[::1\]:[0-9]{1,5}$'
    ]
    
    @classmethod
    def validate_server_url(cls, url: str) -> bool:
        """Validate server URL is local and safe"""
        if not isinstance(url, str) or len(url) > 256:
            return False
        
        for pattern in cls.ALLOWED_SERVER_PATTERNS:
            if re.match(pattern, url):
                return True
        return False
    
    @classmethod
    def validate_response_size(cls, data: bytes) -> bool:
        """Validate response size is within limits"""
        return len(data) <= cls.MAX_RESPONSE_SIZE
    
    @classmethod
    def sanitize_server_id(cls, url: str) -> str:
        """Create a safe server identifier"""
        return hashlib.md5(url.encode('utf-8')).hexdigest()[:16]


class SecureMCPClient:
    """Secure MCP client for trusted local servers"""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.logger = get_logger("secure_mcp_client", base_path)
        self.quarantine = SecureQuarantine(base_path)
        
        # Security configuration
        self.config = self._load_security_config()
        self.trusted_servers = self._load_trusted_servers()
        
        # Connection tracking
        self.active_connections: Dict[str, int] = {}  # server_id -> connection_count
        self.connection_history: Dict[str, List[float]] = {}  # server_id -> timestamp_list
        self.blocked_servers: Set[str] = set()
        
        # Rate limiting
        self.rate_limits: Dict[str, Dict[str, Any]] = {}
    
    def _load_security_config(self) -> Dict[str, Any]:
        """Load MCP client security configuration"""
        config_path = self.base_path / ".mcp-client-config.json"
        default_config = {
            "auto_quarantine_prompts": True,
            "max_trusted_servers": MCPClientSecurityValidator.MAX_SERVER_COUNT,
            "connection_timeout": MCPClientSecurityValidator.CONNECTION_TIMEOUT,
            "rate_limit_per_minute": 30,
            "require_server_authentication": False,  # For local trusted servers
            "log_all_interactions": True,
            "allow_server_discovery": False,  # Only connect to explicitly trusted servers
            "quarantine_all_content": True   # Quarantine ALL content from peers
        }
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                config = default_config.copy()
                config.update(user_config)
                return config
            except Exception as e:
                self.logger.error(f"Failed to load MCP client config: {e}")
        
        return default_config
    
    def _load_trusted_servers(self) -> Dict[str, Dict[str, Any]]:
        """Load trusted server configurations"""
        servers_path = self.base_path / ".mcp-trusted-servers.json"
        default_servers = {
            # Example trusted server configurations
            "example_peer_server": {
                "url": "ws://localhost:8766",
                "name": "Example Peer Server",
                "auto_quarantine": True,
                "allowed_operations": ["submit_prompt", "get_status"],
                "rate_limit_override": 60,
                "enabled": False  # Disabled by default
            }
        }
        
        if servers_path.exists():
            try:
                with open(servers_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to load trusted servers: {e}")
                return default_servers
        
        # Save default configuration
        try:
            with open(servers_path, 'w') as f:
                json.dump(default_servers, f, indent=2)
            self.logger.info("Created default trusted servers configuration")
        except Exception as e:
            self.logger.error(f"Failed to save default servers config: {e}")
        
        return default_servers
    
    def _audit_log(self, action: str, server_info: Dict[str, Any], details: Dict[str, Any], success: bool = True):
        """Audit log all MCP client interactions"""
        if not self.config["log_all_interactions"]:
            return
        
        audit_path = self.base_path / "logs" / "mcp_client_audit.log"
        audit_path.parent.mkdir(exist_ok=True)
        
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "server": server_info,
            "details": details,
            "success": success
        }
        
        try:
            with open(audit_path, 'a') as f:
                f.write(json.dumps(log_entry, separators=(',', ':')) + '\n')
        except Exception as e:
            self.logger.error(f"Failed to write MCP client audit log: {e}")
        
        # Also log to main logger
        level = self.logger.info if success else self.logger.error
        level(f"MCP_CLIENT {action}: {details}")
    
    def _check_server_rate_limit(self, server_id: str) -> bool:
        """Check rate limiting for specific server"""
        now = time.time()
        minute_ago = now - 60
        
        if server_id not in self.rate_limits:
            self.rate_limits[server_id] = {"requests": [], "blocked_until": 0}
        
        server_limits = self.rate_limits[server_id]
        
        # Check if currently blocked
        if now < server_limits["blocked_until"]:
            return False
        
        # Clean old requests
        server_limits["requests"] = [req_time for req_time in server_limits["requests"] if req_time > minute_ago]
        
        # Check limit
        limit = self.config["rate_limit_per_minute"]
        if len(server_limits["requests"]) >= limit:
            server_limits["blocked_until"] = now + 60  # Block for 1 minute
            return False
        
        # Record this request
        server_limits["requests"].append(now)
        return True
    
    def _validate_server_response(self, response_data: str, server_id: str) -> bool:
        """Validate server response for security"""
        try:
            # Check size
            if len(response_data.encode('utf-8')) > MCPClientSecurityValidator.MAX_RESPONSE_SIZE:
                self.logger.warning(f"Server {server_id} response too large")
                return False
            
            # Validate JSON structure
            data = json.loads(response_data)
            
            # Basic JSON-RPC validation
            if not isinstance(data, dict):
                return False
            
            # Check for required JSON-RPC fields
            if "jsonrpc" in data and data["jsonrpc"] != "2.0":
                return False
            
            return True
            
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            self.logger.warning(f"Invalid response from server {server_id}: {e}")
            return False
    
    async def _connect_to_server(self, server_config: Dict[str, Any]) -> Optional[Any]:
        """Establish secure connection to trusted server"""
        if not WEBSOCKETS_AVAILABLE:
            self.logger.error("websockets library not available. Install with: pip install websockets")
            return None
        
        url = server_config["url"]
        server_id = MCPClientSecurityValidator.sanitize_server_id(url)
        
        # Validate URL
        if not MCPClientSecurityValidator.validate_server_url(url):
            self._audit_log("CONNECTION_REJECTED", {"server_id": server_id}, 
                          {"reason": "Invalid URL", "url": url}, success=False)
            return None
        
        # Check connection limits
        current_connections = self.active_connections.get(server_id, 0)
        if current_connections >= MCPClientSecurityValidator.MAX_CONNECTIONS_PER_SERVER:
            self._audit_log("CONNECTION_REJECTED", {"server_id": server_id}, 
                          {"reason": "Connection limit exceeded"}, success=False)
            return None
        
        # Check if server is blocked
        if server_id in self.blocked_servers:
            self._audit_log("CONNECTION_REJECTED", {"server_id": server_id}, 
                          {"reason": "Server blocked"}, success=False)
            return None
        
        try:
            # Configure SSL context for secure connections
            ssl_context = None
            if url.startswith("wss://"):
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False  # For localhost
                ssl_context.verify_mode = ssl.CERT_NONE  # For localhost
            
            # Connect with timeout
            websocket = await asyncio.wait_for(
                websockets.connect(
                    url,
                    ssl=ssl_context,
                    timeout=self.config["connection_timeout"]
                ),
                timeout=self.config["connection_timeout"]
            )
            
            # Track connection
            self.active_connections[server_id] = current_connections + 1
            
            self._audit_log("CONNECTION_ESTABLISHED", {"server_id": server_id}, 
                          {"url": url, "ssl": url.startswith("wss://")})
            
            return websocket
            
        except Exception as e:
            self._audit_log("CONNECTION_FAILED", {"server_id": server_id}, 
                          {"url": url, "error": str(e)}, success=False)
            return None
    
    async def _disconnect_from_server(self, websocket: Any, server_id: str):
        """Safely disconnect from server"""
        try:
            await websocket.close()
            current_connections = self.active_connections.get(server_id, 1)
            self.active_connections[server_id] = max(0, current_connections - 1)
            
            self._audit_log("CONNECTION_CLOSED", {"server_id": server_id}, {})
            
        except Exception as e:
            self.logger.error(f"Error disconnecting from server {server_id}: {e}")
    
    async def accept_prompt_from_peer(self, server_name: str, timeout: int = 30) -> Optional[str]:
        """Accept a prompt from a trusted peer server and quarantine it immediately"""
        
        if server_name not in self.trusted_servers:
            self.logger.error(f"Server {server_name} is not in trusted servers list")
            return None
        
        server_config = self.trusted_servers[server_name]
        if not server_config.get("enabled", False):
            self.logger.error(f"Server {server_name} is disabled")
            return None
        
        server_id = MCPClientSecurityValidator.sanitize_server_id(server_config["url"])
        
        # Rate limiting
        if not self._check_server_rate_limit(server_id):
            self._audit_log("PROMPT_REQUEST_RATE_LIMITED", {"server_id": server_id}, 
                          {"server_name": server_name}, success=False)
            return None
        
        websocket = await self._connect_to_server(server_config)
        if not websocket:
            return None
        
        try:
            # Send request for prompt
            request = {
                "jsonrpc": "2.0",
                "id": int(time.time()),
                "method": "get_prompt",
                "params": {
                    "request_type": "peer_prompt",
                    "requester": "computer-directive-system"
                }
            }
            
            await websocket.send(json.dumps(request))
            
            # Wait for response with timeout
            response_data = await asyncio.wait_for(websocket.recv(), timeout=timeout)
            
            # Validate response
            if not self._validate_server_response(response_data, server_id):
                self._audit_log("INVALID_RESPONSE", {"server_id": server_id}, 
                              {"server_name": server_name}, success=False)
                return None
            
            response = json.loads(response_data)
            
            # Extract prompt content
            prompt_content = ""
            if "result" in response and isinstance(response["result"], dict):
                prompt_content = response["result"].get("prompt", "")
            elif "result" in response and isinstance(response["result"], str):
                prompt_content = response["result"]
            
            if not prompt_content:
                self._audit_log("EMPTY_PROMPT", {"server_id": server_id}, 
                              {"server_name": server_name})
                return None
            
            # CRITICAL SECURITY: Immediately quarantine the prompt - NEVER interpret it
            metadata = {
                "peer_server": server_name,
                "server_url": server_config["url"], 
                "received_timestamp": datetime.now(timezone.utc).isoformat(),
                "response_id": response.get("id"),
                "source_type": "mcp_peer"
            }
            
            # Quarantine the prompt
            quarantine_filename = self.quarantine.quarantine_prompt(
                prompt_content=prompt_content,
                source=f"mcp_peer:{server_name}",
                metadata=metadata
            )
            
            if quarantine_filename:
                self._audit_log("PROMPT_QUARANTINED", {"server_id": server_id}, {
                    "server_name": server_name,
                    "quarantine_file": quarantine_filename,
                    "prompt_length": len(prompt_content)
                })
                
                return quarantine_filename
            else:
                self._audit_log("QUARANTINE_FAILED", {"server_id": server_id}, 
                              {"server_name": server_name}, success=False)
                return None
                
        except asyncio.TimeoutError:
            self._audit_log("PROMPT_REQUEST_TIMEOUT", {"server_id": server_id}, 
                          {"server_name": server_name, "timeout": timeout}, success=False)
            return None
            
        except Exception as e:
            self._audit_log("PROMPT_REQUEST_ERROR", {"server_id": server_id}, 
                          {"server_name": server_name, "error": str(e)}, success=False)
            return None
            
        finally:
            await self._disconnect_from_server(websocket, server_id)
    
    async def get_peer_server_status(self, server_name: str) -> Optional[Dict[str, Any]]:
        """Get status from a trusted peer server (read-only)"""
        
        if server_name not in self.trusted_servers:
            return None
        
        server_config = self.trusted_servers[server_name]
        if not server_config.get("enabled", False):
            return None
        
        server_id = MCPClientSecurityValidator.sanitize_server_id(server_config["url"])
        
        # Rate limiting
        if not self._check_server_rate_limit(server_id):
            return None
        
        websocket = await self._connect_to_server(server_config)
        if not websocket:
            return None
        
        try:
            # Request status
            request = {
                "jsonrpc": "2.0",
                "id": int(time.time()),
                "method": "get_status",
                "params": {}
            }
            
            await websocket.send(json.dumps(request))
            response_data = await asyncio.wait_for(websocket.recv(), timeout=10)
            
            # Validate and parse response
            if self._validate_server_response(response_data, server_id):
                response = json.loads(response_data)
                
                self._audit_log("STATUS_REQUEST", {"server_id": server_id}, 
                              {"server_name": server_name})
                
                return response.get("result", {})
            
        except Exception as e:
            self._audit_log("STATUS_REQUEST_ERROR", {"server_id": server_id}, 
                          {"server_name": server_name, "error": str(e)}, success=False)
            
        finally:
            await self._disconnect_from_server(websocket, server_id)
        
        return None
    
    def list_trusted_servers(self) -> Dict[str, Dict[str, Any]]:
        """List all trusted servers and their status"""
        servers_status = {}
        
        for server_name, config in self.trusted_servers.items():
            server_id = MCPClientSecurityValidator.sanitize_server_id(config["url"])
            servers_status[server_name] = {
                "config": {k: v for k, v in config.items() if k != "auth_token"},  # Don't expose tokens
                "server_id": server_id,
                "active_connections": self.active_connections.get(server_id, 0),
                "blocked": server_id in self.blocked_servers,
                "rate_limited": not self._check_server_rate_limit(server_id)
            }
        
        return servers_status
    
    def add_trusted_server(self, name: str, url: str, enabled: bool = False) -> bool:
        """Add a new trusted server"""
        if not MCPClientSecurityValidator.validate_server_url(url):
            return False
        
        if len(self.trusted_servers) >= self.config["max_trusted_servers"]:
            return False
        
        self.trusted_servers[name] = {
            "url": url,
            "name": name,
            "auto_quarantine": True,
            "allowed_operations": ["submit_prompt", "get_status"],
            "rate_limit_override": 30,
            "enabled": enabled,
            "added_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Save updated configuration
        try:
            servers_path = self.base_path / ".mcp-trusted-servers.json"
            with open(servers_path, 'w') as f:
                json.dump(self.trusted_servers, f, indent=2)
            
            self._audit_log("TRUSTED_SERVER_ADDED", {}, {"name": name, "url": url})
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save trusted servers: {e}")
            return False