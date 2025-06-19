#!/usr/bin/env python3
"""
Secure Quarantine System - Safely handles untrusted prompts with zero interpretation
"""

import os
import uuid
import hashlib
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pathlib import Path
import re

from logger import get_logger


class QuarantineValidator:
    """Strict input validation for quarantine system"""
    
    # Security limits
    MAX_PROMPT_SIZE = 1024 * 1024  # 1MB max prompt size
    MAX_METADATA_SIZE = 8192       # 8KB max metadata
    MAX_FILENAME_LENGTH = 255
    MAX_QUARANTINE_FILES = 10000   # Prevent directory DoS
    
    # Allowed characters (very restrictive)
    SAFE_CHARS = re.compile(r'^[a-zA-Z0-9\s\.\-_,;:!?()\[\]{}@#$%&*+=<>/\'\"`~|\\\n\r\t]*$')
    
    @classmethod
    def validate_prompt_content(cls, content: str) -> bool:
        """Validate prompt content is safe to store (but never execute)"""
        if not isinstance(content, str):
            return False
        if len(content) > cls.MAX_PROMPT_SIZE:
            return False
        if len(content.encode('utf-8')) > cls.MAX_PROMPT_SIZE:
            return False
        # Allow most printable characters but be very careful
        return cls.SAFE_CHARS.match(content) is not None
    
    @classmethod
    def validate_metadata(cls, metadata: Dict[str, Any]) -> bool:
        """Validate metadata is safe"""
        if not isinstance(metadata, dict):
            return False
        
        # Convert to JSON to check size
        try:
            json_str = json.dumps(metadata, separators=(',', ':'))
            if len(json_str) > cls.MAX_METADATA_SIZE:
                return False
        except (TypeError, ValueError):
            return False
        
        # Validate each key and value
        for key, value in metadata.items():
            if not isinstance(key, str) or len(key) > 100:
                return False
            if not isinstance(value, (str, int, float, bool, type(None))):
                return False
            if isinstance(value, str) and len(value) > 1000:
                return False
        
        return True
    
    @classmethod
    def sanitize_filename(cls, name: str) -> str:
        """Generate a completely safe filename using only UUID"""
        # Never use user input in filenames - only UUID
        return f"Q-{uuid.uuid4()}.md"


class SecureQuarantine:
    """Secure quarantine system for uninterpreted prompts"""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.quarantine_root = self.base_path / "pages" / "prompts" / "quarantine"
        self.audit_log_path = self.base_path / "logs" / "quarantine_audit.log"
        self.config_path = self.base_path / ".quarantine-config"
        
        # Initialize logger with security focus
        self.logger = get_logger("secure_quarantine", base_path)
        
        # Ensure quarantine directories exist with proper permissions
        self._initialize_quarantine_structure()
        
        # Load security configuration
        self.config = self._load_security_config()
        
        # Security state tracking
        self.quarantine_count = 0
        self.last_cleanup = time.time()
        
    def _initialize_quarantine_structure(self):
        """Initialize quarantine directory structure with secure permissions"""
        directories = [
            self.quarantine_root,
            self.audit_log_path.parent,
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            # Set restrictive permissions (owner only)
            os.chmod(str(directory), 0o700)
        
        # Create README with security warnings
        readme_path = self.quarantine_root / "README.md"
        if not readme_path.exists():
            with open(readme_path, 'w') as f:
                f.write("""# QUARANTINE DIRECTORY - SECURITY WARNING

⚠️  **DANGER: UNTRUSTED CONTENT** ⚠️

This directory contains UNINTERPRETED prompts from external sources.
These prompts may contain:
- Prompt injection attempts
- Malicious instructions
- Social engineering attacks

**NEVER:**
- Execute or interpret these prompts directly
- Copy content without careful review
- Process through AI systems without sanitization

**ALWAYS:**
- Review content manually before any use
- Use the CLI quarantine review commands
- Maintain audit logs of all actions

Files are named with UTC timestamps and UUIDs for safety.
""")
            os.chmod(str(readme_path), 0o600)
    
    def _load_security_config(self) -> Dict[str, Any]:
        """Load security configuration with safe defaults"""
        default_config = {
            "max_quarantine_files": QuarantineValidator.MAX_QUARANTINE_FILES,
            "max_prompt_size": QuarantineValidator.MAX_PROMPT_SIZE,
            "auto_cleanup_days": 30,
            "require_source_verification": True,
            "allowed_source_patterns": [
                r"^localhost:",
                r"^127\.0\.0\.1:",
                r"^::1:",
            ],
            "rate_limit_per_hour": 100,
        }
        
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    user_config = json.load(f)
                # Merge but keep security defaults for critical settings
                config = default_config.copy()
                config.update(user_config)
                return config
            except Exception as e:
                self.logger.error(f"Failed to load quarantine config: {e}")
        
        return default_config
    
    def _audit_log(self, action: str, details: Dict[str, Any], success: bool = True):
        """Write security audit log entry"""
        timestamp = datetime.now(timezone.utc).isoformat()
        log_entry = {
            "timestamp": timestamp,
            "action": action,
            "success": success,
            "details": details,
            "quarantine_count": self.quarantine_count
        }
        
        try:
            with open(self.audit_log_path, 'a') as f:
                f.write(json.dumps(log_entry, separators=(',', ':')) + '\n')
        except Exception as e:
            self.logger.error(f"Failed to write audit log: {e}")
        
        # Also log to main logger
        level = self.logger.info if success else self.logger.error
        level(f"QUARANTINE {action}: {details}")
    
    def _check_rate_limits(self, source: str) -> bool:
        """Check if source is within rate limits"""
        # Simple hourly rate limiting
        current_hour = int(time.time() // 3600)
        rate_file = self.quarantine_root / f".rate_{current_hour}_{hashlib.md5(source.encode()).hexdigest()[:8]}"
        
        if rate_file.exists():
            try:
                count = int(rate_file.read_text().strip())
                if count >= self.config["rate_limit_per_hour"]:
                    return False
            except:
                pass
        
        return True
    
    def _update_rate_limits(self, source: str):
        """Update rate limit counters"""
        current_hour = int(time.time() // 3600)
        rate_file = self.quarantine_root / f".rate_{current_hour}_{hashlib.md5(source.encode()).hexdigest()[:8]}"
        
        try:
            count = 1
            if rate_file.exists():
                count = int(rate_file.read_text().strip()) + 1
            rate_file.write_text(str(count))
        except:
            pass
    
    def _verify_source(self, source: str) -> bool:
        """Verify source is allowed"""
        if not self.config["require_source_verification"]:
            return True
        
        for pattern in self.config["allowed_source_patterns"]:
            if re.match(pattern, source):
                return True
        
        return False
    
    def quarantine_prompt(self, prompt_content: str, source: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Safely quarantine an uninterpreted prompt"""
        
        # Security validation
        if not QuarantineValidator.validate_prompt_content(prompt_content):
            self._audit_log("QUARANTINE_REJECTED", {
                "reason": "Invalid prompt content",
                "source": source,
                "content_length": len(prompt_content)
            }, success=False)
            return None
        
        if metadata and not QuarantineValidator.validate_metadata(metadata):
            self._audit_log("QUARANTINE_REJECTED", {
                "reason": "Invalid metadata",
                "source": source
            }, success=False)
            return None
        
        # Source verification
        if not self._verify_source(source):
            self._audit_log("QUARANTINE_REJECTED", {
                "reason": "Untrusted source",
                "source": source
            }, success=False)
            return None
        
        # Rate limiting
        if not self._check_rate_limits(source):
            self._audit_log("QUARANTINE_REJECTED", {
                "reason": "Rate limit exceeded",
                "source": source
            }, success=False)
            return None
        
        # Check quarantine capacity
        existing_files = list(self.quarantine_root.glob("Q-*.md"))
        if len(existing_files) >= self.config["max_quarantine_files"]:
            self._audit_log("QUARANTINE_REJECTED", {
                "reason": "Quarantine capacity exceeded",
                "source": source,
                "file_count": len(existing_files)
            }, success=False)
            return None
        
        # Generate secure filename
        filename = QuarantineValidator.sanitize_filename("")
        file_path = self.quarantine_root / filename
        
        # Ensure no collision (highly unlikely with UUID)
        while file_path.exists():
            filename = QuarantineValidator.sanitize_filename("")
            file_path = self.quarantine_root / filename
        
        # Prepare quarantine metadata
        quarantine_metadata = {
            "quarantine_timestamp": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "content_hash": hashlib.sha256(prompt_content.encode('utf-8')).hexdigest(),
            "content_length": len(prompt_content),
            "quarantine_id": filename[:-3],  # Remove .md extension
            "status": "quarantined",
            "reviewed": False,
            "reviewer": None,
            "review_timestamp": None,
            "review_notes": None,
            "original_metadata": metadata or {}
        }
        
        # Create quarantine file with metadata header
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("---\n")
                json.dump(quarantine_metadata, f, indent=2, separators=(',', ': '))
                f.write("\n---\n\n")
                f.write("# QUARANTINED PROMPT - DO NOT INTERPRET\n\n")
                f.write("⚠️  **WARNING: This content is UNVERIFIED and potentially MALICIOUS** ⚠️\n\n")
                f.write("Source: " + source + "\n")
                f.write("Quarantined: " + quarantine_metadata["quarantine_timestamp"] + "\n\n")
                f.write("## Original Content\n\n")
                f.write("```\n")
                f.write(prompt_content)
                f.write("\n```\n")
            
            # Set restrictive permissions
            os.chmod(str(file_path), 0o600)
            
            # Update counters and rate limits
            self.quarantine_count += 1
            self._update_rate_limits(source)
            
            # Audit log
            self._audit_log("PROMPT_QUARANTINED", {
                "filename": filename,
                "source": source,
                "content_length": len(prompt_content),
                "content_hash": quarantine_metadata["content_hash"]
            })
            
            return filename
            
        except Exception as e:
            self._audit_log("QUARANTINE_FAILED", {
                "reason": str(e),
                "source": source,
                "filename": filename
            }, success=False)
            return None
    
    def list_quarantined_prompts(self, include_reviewed: bool = False) -> List[Dict[str, Any]]:
        """List quarantined prompts with metadata"""
        prompts = []
        
        for file_path in self.quarantine_root.glob("Q-*.md"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract metadata from frontmatter
                if content.startswith("---\n"):
                    parts = content.split("---\n", 2)
                    if len(parts) >= 3:
                        metadata_str = parts[1]
                        metadata = json.loads(metadata_str)
                        
                        # Filter based on review status
                        if not include_reviewed and metadata.get("reviewed", False):
                            continue
                        
                        prompts.append({
                            "filename": file_path.name,
                            "metadata": metadata,
                            "file_path": str(file_path)
                        })
            except Exception as e:
                self.logger.error(f"Error reading quarantine file {file_path}: {e}")
        
        # Sort by quarantine timestamp (newest first)
        prompts.sort(key=lambda x: x["metadata"].get("quarantine_timestamp", ""), reverse=True)
        return prompts
    
    def get_quarantine_stats(self) -> Dict[str, Any]:
        """Get quarantine system statistics"""
        files = list(self.quarantine_root.glob("Q-*.md"))
        total_files = len(files)
        reviewed_count = 0
        pending_count = 0
        total_size = 0
        
        for file_path in files:
            try:
                total_size += file_path.stat().st_size
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if content.startswith("---\n"):
                        parts = content.split("---\n", 2)
                        if len(parts) >= 3:
                            metadata = json.loads(parts[1])
                            if metadata.get("reviewed", False):
                                reviewed_count += 1
                            else:
                                pending_count += 1
            except:
                pass
        
        return {
            "total_files": total_files,
            "reviewed_count": reviewed_count,
            "pending_count": pending_count,
            "total_size_bytes": total_size,
            "quarantine_path": str(self.quarantine_root),
            "max_capacity": self.config["max_quarantine_files"],
            "capacity_used_percent": (total_files / self.config["max_quarantine_files"]) * 100
        }
    
    def mark_reviewed(self, filename: str, reviewer: str, notes: str = "") -> bool:
        """Mark a quarantined prompt as reviewed"""
        file_path = self.quarantine_root / filename
        
        if not file_path.exists() or not filename.startswith("Q-") or not filename.endswith(".md"):
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if content.startswith("---\n"):
                parts = content.split("---\n", 2)
                if len(parts) >= 3:
                    metadata = json.loads(parts[1])
                    metadata["reviewed"] = True
                    metadata["reviewer"] = reviewer
                    metadata["review_timestamp"] = datetime.now(timezone.utc).isoformat()
                    metadata["review_notes"] = notes
                    
                    # Rewrite file with updated metadata
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write("---\n")
                        json.dump(metadata, f, indent=2, separators=(',', ': '))
                        f.write("\n---\n")
                        f.write(parts[2])
                    
                    self._audit_log("PROMPT_REVIEWED", {
                        "filename": filename,
                        "reviewer": reviewer,
                        "notes": notes[:100] + "..." if len(notes) > 100 else notes
                    })
                    
                    return True
        except Exception as e:
            self._audit_log("REVIEW_FAILED", {
                "filename": filename,
                "reviewer": reviewer,
                "error": str(e)
            }, success=False)
        
        return False