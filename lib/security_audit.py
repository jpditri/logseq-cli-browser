#!/usr/bin/env python3
"""
Security Audit CLI - Security monitoring and configuration for Computer system
"""

import sys
import argparse
import json
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any

# Add lib directory to path
sys.path.append(str(Path(__file__).parent))

from logger import get_logger


class SecurityAuditor:
    """Security audit and monitoring system"""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.logs_dir = self.base_path / "logs"
        self.logger = get_logger("security_auditor", base_path)
        
        # Security configuration paths
        self.quarantine_config = self.base_path / ".quarantine-config"
        self.mcp_server_config = self.base_path / ".mcp-server-config.json"
        self.mcp_client_config = self.base_path / ".mcp-client-config.json"
        self.trusted_servers = self.base_path / ".mcp-trusted-servers.json"
        self.auth_tokens = self.base_path / ".mcp-auth-tokens.json"
    
    def analyze_audit_logs(self, days: int = 7, filter_term: str = None) -> Dict[str, Any]:
        """Analyze security audit logs"""
        analysis = {
            "time_range": f"Last {days} days",
            "total_events": 0,
            "security_events": {},
            "failed_events": 0,
            "rate_limited_events": 0,
            "quarantine_events": 0,
            "mcp_events": 0,
            "suspicious_activity": [],
            "recommendations": []
        }
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Analyze different log files
        log_files = [
            ("quarantine_audit.log", "quarantine"),
            ("mcp_audit.log", "mcp_server"),
            ("mcp_client_audit.log", "mcp_client")
        ]
        
        for log_file, log_type in log_files:
            log_path = self.logs_dir / log_file
            if not log_path.exists():
                continue
            
            try:
                with open(log_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        
                        try:
                            event = json.loads(line)
                            event_time = datetime.fromisoformat(event.get("timestamp", "").replace('Z', '+00:00'))
                            
                            if event_time < cutoff_date:
                                continue
                            
                            # Apply filter if specified
                            if filter_term and filter_term.lower() not in json.dumps(event).lower():
                                continue
                            
                            analysis["total_events"] += 1
                            
                            # Categorize events
                            action = event.get("action", "unknown")
                            success = event.get("success", True)
                            
                            if log_type not in analysis["security_events"]:
                                analysis["security_events"][log_type] = {}
                            
                            if action not in analysis["security_events"][log_type]:
                                analysis["security_events"][log_type][action] = {"count": 0, "failures": 0}
                            
                            analysis["security_events"][log_type][action]["count"] += 1
                            
                            if not success:
                                analysis["failed_events"] += 1
                                analysis["security_events"][log_type][action]["failures"] += 1
                            
                            # Specific event analysis
                            if "RATE_LIMITED" in action:
                                analysis["rate_limited_events"] += 1
                            
                            if "QUARANTINE" in action:
                                analysis["quarantine_events"] += 1
                            
                            if log_type.startswith("mcp"):
                                analysis["mcp_events"] += 1
                            
                            # Detect suspicious activity
                            if self._is_suspicious_event(event, log_type):
                                analysis["suspicious_activity"].append({
                                    "timestamp": event.get("timestamp"),
                                    "log_type": log_type,
                                    "action": action,
                                    "details": event.get("details", {}),
                                    "reason": self._get_suspicion_reason(event, log_type)
                                })
                        
                        except json.JSONDecodeError:
                            continue
                            
            except Exception as e:
                self.logger.error(f"Error analyzing {log_file}: {e}")
        
        # Generate recommendations
        analysis["recommendations"] = self._generate_security_recommendations(analysis)
        
        return analysis
    
    def _is_suspicious_event(self, event: Dict[str, Any], log_type: str) -> bool:
        """Detect suspicious security events"""
        action = event.get("action", "")
        details = event.get("details", {})
        success = event.get("success", True)
        
        # Multiple failed attempts
        if not success and ("REJECTED" in action or "FAILED" in action):
            return True
        
        # Large content submissions
        if "content_length" in details and details["content_length"] > 500000:  # 500KB
            return True
        
        # Unusual sources
        source = details.get("source", "")
        if source and not any(pattern in source for pattern in ["localhost", "127.0.0.1", "::1"]):
            return True
        
        # Rate limiting triggered
        if "RATE_LIMITED" in action:
            return True
        
        return False
    
    def _get_suspicion_reason(self, event: Dict[str, Any], log_type: str) -> str:
        """Get reason for marking event as suspicious"""
        action = event.get("action", "")
        details = event.get("details", {})
        success = event.get("success", True)
        
        if not success:
            return "Failed operation"
        
        if "content_length" in details and details["content_length"] > 500000:
            return "Large content submission"
        
        source = details.get("source", "")
        if source and not any(pattern in source for pattern in ["localhost", "127.0.0.1", "::1"]):
            return "Non-localhost source"
        
        if "RATE_LIMITED" in action:
            return "Rate limiting triggered"
        
        return "Pattern analysis"
    
    def _generate_security_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate security recommendations based on analysis"""
        recommendations = []
        
        # High failure rate
        if analysis["total_events"] > 0:
            failure_rate = analysis["failed_events"] / analysis["total_events"]
            if failure_rate > 0.1:  # 10% failure rate
                recommendations.append(f"High failure rate ({failure_rate:.1%}) - investigate authentication or configuration issues")
        
        # Rate limiting
        if analysis["rate_limited_events"] > 10:
            recommendations.append("Frequent rate limiting - consider adjusting rate limits or investigating automated attacks")
        
        # Suspicious activity
        if len(analysis["suspicious_activity"]) > 5:
            recommendations.append("Multiple suspicious events detected - review security logs and access controls")
        
        # Quarantine review
        if analysis["quarantine_events"] > 0:
            recommendations.append("Quarantined prompts detected - ensure timely review of quarantined content")
        
        # MCP activity
        if analysis["mcp_events"] > 100:
            recommendations.append("High MCP activity - monitor peer connections and validate trusted server list")
        
        if not recommendations:
            recommendations.append("No immediate security concerns detected")
        
        return recommendations
    
    def security_scan(self) -> Dict[str, Any]:
        """Perform comprehensive security scan"""
        scan_results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "file_permissions": {},
            "configuration_security": {},
            "directory_structure": {},
            "authentication": {},
            "recommendations": []
        }
        
        # Check file permissions
        critical_files = [
            self.quarantine_config,
            self.mcp_server_config,
            self.mcp_client_config,
            self.trusted_servers,
            self.auth_tokens
        ]
        
        for file_path in critical_files:
            if file_path.exists():
                stat = file_path.stat()
                permissions = oct(stat.st_mode)[-3:]
                scan_results["file_permissions"][str(file_path)] = {
                    "permissions": permissions,
                    "secure": permissions in ["600", "700"]
                }
                
                if permissions not in ["600", "700"]:
                    scan_results["recommendations"].append(f"Secure file permissions for {file_path.name}: chmod 600 {file_path}")
        
        # Check configuration security
        config_checks = [
            (self.mcp_server_config, self._check_mcp_server_config),
            (self.mcp_client_config, self._check_mcp_client_config),
            (self.trusted_servers, self._check_trusted_servers_config)
        ]
        
        for config_file, check_function in config_checks:
            if config_file.exists():
                try:
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                    result = check_function(config)
                    scan_results["configuration_security"][config_file.name] = result
                except Exception as e:
                    scan_results["configuration_security"][config_file.name] = {"error": str(e)}
        
        # Check directory structure
        critical_dirs = [
            self.base_path / "pages" / "prompts" / "quarantine",
            self.logs_dir,
            self.base_path / "directives" / "batches"
        ]
        
        for dir_path in critical_dirs:
            if dir_path.exists():
                stat = dir_path.stat()
                permissions = oct(stat.st_mode)[-3:]
                scan_results["directory_structure"][str(dir_path)] = {
                    "exists": True,
                    "permissions": permissions,
                    "secure": permissions in ["700", "750"]
                }
            else:
                scan_results["directory_structure"][str(dir_path)] = {
                    "exists": False,
                    "recommendation": "Create directory with secure permissions"
                }
        
        # Check authentication
        if self.auth_tokens.exists():
            try:
                with open(self.auth_tokens, 'r') as f:
                    tokens = json.load(f)
                scan_results["authentication"] = {
                    "token_count": len(tokens),
                    "default_tokens": any("default" in name.lower() for name in tokens.keys()),
                    "secure": len(tokens) < 10 and all(len(token) >= 32 for token in tokens.keys())
                }
                
                if scan_results["authentication"]["default_tokens"]:
                    scan_results["recommendations"].append("Replace default authentication tokens with custom ones")
                    
            except Exception as e:
                scan_results["authentication"]["error"] = str(e)
        
        return scan_results
    
    def _check_mcp_server_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Check MCP server configuration security"""
        result = {"secure": True, "issues": []}
        
        if not config.get("require_authentication", True):
            result["secure"] = False
            result["issues"].append("Authentication not required")
        
        if config.get("expose_sensitive_data", False):
            result["secure"] = False
            result["issues"].append("Sensitive data exposure enabled")
        
        if not config.get("read_only_mode", True):
            result["secure"] = False
            result["issues"].append("Read-only mode disabled")
        
        rate_limit = config.get("rate_limit_requests_per_minute", 0)
        if rate_limit < 10 or rate_limit > 1000:
            result["issues"].append(f"Unusual rate limit: {rate_limit}")
        
        return result
    
    def _check_mcp_client_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Check MCP client configuration security"""
        result = {"secure": True, "issues": []}
        
        if not config.get("auto_quarantine_prompts", True):
            result["secure"] = False
            result["issues"].append("Auto-quarantine disabled")
        
        if not config.get("quarantine_all_content", True):
            result["secure"] = False
            result["issues"].append("Content quarantine disabled")
        
        if config.get("allow_server_discovery", False):
            result["secure"] = False
            result["issues"].append("Server discovery enabled (security risk)")
        
        return result
    
    def _check_trusted_servers_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Check trusted servers configuration"""
        result = {"secure": True, "issues": [], "server_count": len(config)}
        
        for name, server_config in config.items():
            url = server_config.get("url", "")
            
            # Check if URL is localhost only
            if not any(host in url for host in ["localhost", "127.0.0.1", "::1"]):
                result["secure"] = False
                result["issues"].append(f"Non-localhost server: {name}")
            
            # Check if auto-quarantine is enabled
            if not server_config.get("auto_quarantine", True):
                result["issues"].append(f"Auto-quarantine disabled for: {name}")
            
            # Check if server is enabled by default
            if server_config.get("enabled", False) and "example" in name.lower():
                result["issues"].append(f"Example server enabled: {name}")
        
        return result
    
    def show_security_config(self) -> Dict[str, Any]:
        """Show current security configuration"""
        config_summary = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "files": {},
            "security_status": "checking"
        }
        
        config_files = [
            self.quarantine_config,
            self.mcp_server_config,
            self.mcp_client_config,
            self.trusted_servers,
            self.auth_tokens
        ]
        
        for config_file in config_files:
            file_info = {
                "exists": config_file.exists(),
                "path": str(config_file)
            }
            
            if config_file.exists():
                try:
                    stat = config_file.stat()
                    file_info["size"] = stat.st_size
                    file_info["permissions"] = oct(stat.st_mode)[-3:]
                    file_info["modified"] = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
                    
                    # Try to load and summarize content (without exposing secrets)
                    if config_file.suffix == '.json':
                        with open(config_file, 'r') as f:
                            content = json.load(f)
                        
                        if "auth-tokens" in config_file.name:
                            file_info["summary"] = f"{len(content)} authentication tokens"
                        elif "trusted-servers" in config_file.name:
                            enabled_count = sum(1 for s in content.values() if s.get("enabled", False))
                            file_info["summary"] = f"{len(content)} servers ({enabled_count} enabled)"
                        else:
                            file_info["summary"] = f"{len(content)} configuration keys"
                    
                except Exception as e:
                    file_info["error"] = str(e)
            
            config_summary["files"][config_file.name] = file_info
        
        # Determine overall security status
        secure_count = 0
        total_count = len([f for f in config_summary["files"].values() if f["exists"]])
        
        for file_info in config_summary["files"].values():
            if file_info.get("exists") and file_info.get("permissions") in ["600", "700"]:
                secure_count += 1
        
        if total_count == 0:
            config_summary["security_status"] = "no_config"
        elif secure_count == total_count:
            config_summary["security_status"] = "secure"
        else:
            config_summary["security_status"] = "needs_attention"
        
        return config_summary


def show_audit_logs(auditor: SecurityAuditor, days: int = 7, filter_term: str = None):
    """Display security audit analysis"""
    print(f"🔐 SECURITY AUDIT ({days} days)")
    print("="*60)
    print()
    
    analysis = auditor.analyze_audit_logs(days, filter_term)
    
    # Summary
    print("📊 Summary:")
    print(f"   Total events: {analysis['total_events']:,}")
    print(f"   Failed events: {analysis['failed_events']:,}")
    print(f"   Rate limited: {analysis['rate_limited_events']:,}")
    print(f"   Quarantine events: {analysis['quarantine_events']:,}")
    print(f"   MCP events: {analysis['mcp_events']:,}")
    print()
    
    # Event breakdown
    if analysis["security_events"]:
        print("📋 Event Breakdown:")
        for log_type, actions in analysis["security_events"].items():
            print(f"\n   {log_type.upper()}:")
            for action, stats in actions.items():
                failure_indicator = f" ({stats['failures']} failed)" if stats['failures'] > 0 else ""
                print(f"     {action}: {stats['count']}{failure_indicator}")
        print()
    
    # Suspicious activity
    if analysis["suspicious_activity"]:
        print("⚠️  SUSPICIOUS ACTIVITY:")
        for event in analysis["suspicious_activity"][-10]:  # Show last 10
            print(f"   📅 {event['timestamp']}")
            print(f"   🔍 {event['action']} ({event['log_type']})")
            print(f"   ⚠️  {event['reason']}")
            print()
    
    # Recommendations
    print("💡 RECOMMENDATIONS:")
    for rec in analysis["recommendations"]:
        print(f"   • {rec}")
    print()


def run_security_scan(auditor: SecurityAuditor):
    """Run and display security scan results"""
    print("🔍 SECURITY SCAN")
    print("="*50)
    print()
    
    results = auditor.security_scan()
    
    # File permissions
    print("📁 File Permissions:")
    for file_path, info in results["file_permissions"].items():
        status = "✅" if info["secure"] else "⚠️"
        print(f"   {status} {Path(file_path).name}: {info['permissions']}")
    print()
    
    # Configuration security
    print("⚙️  Configuration Security:")
    for config_name, info in results["configuration_security"].items():
        if "error" in info:
            print(f"   ❌ {config_name}: {info['error']}")
        else:
            status = "✅" if info["secure"] else "⚠️"
            print(f"   {status} {config_name}")
            for issue in info.get("issues", []):
                print(f"      • {issue}")
    print()
    
    # Directory structure
    print("📂 Directory Structure:")
    for dir_path, info in results["directory_structure"].items():
        if info["exists"]:
            status = "✅" if info["secure"] else "⚠️"
            print(f"   {status} {Path(dir_path).name}: {info['permissions']}")
        else:
            print(f"   ❌ {Path(dir_path).name}: Missing")
    print()
    
    # Authentication
    if "authentication" in results:
        auth_info = results["authentication"]
        print("🔑 Authentication:")
        if "error" in auth_info:
            print(f"   ❌ Error: {auth_info['error']}")
        else:
            status = "✅" if auth_info["secure"] else "⚠️"
            print(f"   {status} {auth_info['token_count']} tokens configured")
            if auth_info["default_tokens"]:
                print("   ⚠️  Default tokens detected")
        print()
    
    # Recommendations
    if results["recommendations"]:
        print("💡 RECOMMENDATIONS:")
        for rec in results["recommendations"]:
            print(f"   • {rec}")
        print()


def show_security_config(auditor: SecurityAuditor):
    """Display security configuration"""
    print("⚙️  SECURITY CONFIGURATION")
    print("="*50)
    print()
    
    config = auditor.show_security_config()
    
    # Overall status
    status_emoji = {
        "secure": "✅",
        "needs_attention": "⚠️",
        "no_config": "❌",
        "checking": "🔍"
    }
    
    print(f"🛡️  Overall Status: {status_emoji.get(config['security_status'], '❓')} {config['security_status'].replace('_', ' ').title()}")
    print()
    
    # File details
    print("📄 Configuration Files:")
    for file_name, info in config["files"].items():
        if info["exists"]:
            permissions = info.get("permissions", "unknown")
            size = info.get("size", 0)
            modified = info.get("modified", "unknown")
            summary = info.get("summary", "")
            
            status = "✅" if permissions in ["600", "700"] else "⚠️"
            print(f"   {status} {file_name}")
            print(f"      Permissions: {permissions}")
            print(f"      Size: {size:,} bytes")
            print(f"      Modified: {modified}")
            if summary:
                print(f"      Content: {summary}")
        else:
            print(f"   ❌ {file_name}: Not found")
        print()
    
    print("📋 Security Guidelines:")
    print("   • Keep configuration files with 600 permissions")
    print("   • Use strong authentication tokens (32+ characters)")
    print("   • Enable auto-quarantine for all peer connections")
    print("   • Review quarantined content promptly")
    print("   • Monitor audit logs regularly")
    print("   • Only trust localhost MCP servers")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="Security audit and configuration CLI")
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Audit command
    audit_parser = subparsers.add_parser('audit', help='Show security audit logs')
    audit_parser.add_argument('--days', type=int, default=7, help='Days of logs to analyze')
    audit_parser.add_argument('--filter', help='Filter events by term')
    
    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Run security scan')
    
    # Config command
    config_parser = subparsers.add_parser('config', help='Show security configuration')
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Initialize auditor
    try:
        auditor = SecurityAuditor()
    except Exception as e:
        print(f"❌ Failed to initialize security auditor: {e}")
        sys.exit(1)
    
    # Execute command
    try:
        if args.command == 'audit':
            show_audit_logs(auditor, args.days, args.filter)
        elif args.command == 'scan':
            run_security_scan(auditor)
        elif args.command == 'config':
            show_security_config(auditor)
        else:
            print(f"❌ Unknown command: {args.command}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Command failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()