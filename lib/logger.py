#!/usr/bin/env python3
"""
Structured logging for Computer project
"""

import logging
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from settings import get_settings


class ComputerLogger:
    """Structured logger for Computer project with JSON and console output"""
    
    def __init__(self, name: str = "computer", base_path: str = "."):
        self.name = name
        self.base_path = Path(base_path)
        self.settings = get_settings(base_path)
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """Setup structured logger with console and file handlers"""
        logger = logging.getLogger(self.name)
        
        # Prevent duplicate handlers
        if logger.handlers:
            return logger
        
        # Set log level from settings
        log_level = self.settings.get('log_level', 'INFO')
        logger.setLevel(getattr(logging, log_level))
        
        # Console handler with simple format
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # File handler with JSON format (if log file specified)
        log_file = self.settings.get('log_file')
        if log_file:
            log_path = self.base_path / log_file
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_path)
            file_formatter = JsonFormatter()
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        
        return logger
    
    def info(self, message: str, **kwargs):
        """Log info message with optional structured data"""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with optional structured data"""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with optional structured data"""
        self._log(logging.ERROR, message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with optional structured data"""
        self._log(logging.DEBUG, message, **kwargs)
    
    def directive_created(self, directive_id: str, content: str, platform: str = None, model: str = None):
        """Log directive creation"""
        self.info(
            f"Directive created: {directive_id}",
            directive_id=directive_id,
            content_preview=content[:100],
            platform=platform,
            model=model,
            event_type="directive_created"
        )
    
    def directive_started(self, directive_id: str, file_path: str):
        """Log directive processing start"""
        self.info(
            f"Processing directive: {directive_id}",
            directive_id=directive_id,
            file_path=str(file_path),
            event_type="directive_started"
        )
    
    def directive_completed(self, directive_id: str, success: bool, duration: float, 
                          tokens_in: int = None, tokens_out: int = None, cost: float = None):
        """Log directive completion"""
        status = "success" if success else "failed"
        self.info(
            f"Directive {status}: {directive_id} ({duration:.2f}s)",
            directive_id=directive_id,
            success=success,
            duration=duration,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost=cost,
            event_type="directive_completed"
        )
    
    def api_request(self, platform: str, model: str, tokens_in: int = None):
        """Log API request"""
        self.debug(
            f"API request to {platform}/{model}",
            platform=platform,
            model=model,
            tokens_in=tokens_in,
            event_type="api_request"
        )
    
    def api_response(self, platform: str, model: str, success: bool, tokens_out: int = None, 
                    cost: float = None, error: str = None):
        """Log API response"""
        if success:
            self.debug(
                f"API response from {platform}/{model}",
                platform=platform,
                model=model,
                tokens_out=tokens_out,
                cost=cost,
                event_type="api_response"
            )
        else:
            self.warning(
                f"API error from {platform}/{model}: {error}",
                platform=platform,
                model=model,
                error=error,
                event_type="api_error"
            )
    
    def system_status(self, **metrics):
        """Log system status metrics"""
        self.info(
            "System status",
            **metrics,
            event_type="system_status"
        )
    
    def _log(self, level: int, message: str, **kwargs):
        """Internal logging method with structured data"""
        # Add common fields
        extra_data = {
            'timestamp': datetime.now().isoformat(),
            'component': self.name,
            **kwargs
        }
        
        # Log with extra data for JSON formatter
        self.logger.log(level, message, extra=extra_data)


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra data if present
        if hasattr(record, 'extra'):
            log_data.update(record.extra)
        
        return json.dumps(log_data, default=str)


class PerformanceTracker:
    """Track and log performance metrics"""
    
    def __init__(self, logger: ComputerLogger):
        self.logger = logger
        self.metrics = {
            'directives_processed': 0,
            'directives_succeeded': 0,
            'directives_failed': 0,
            'total_tokens_in': 0,
            'total_tokens_out': 0,
            'total_cost': 0.0,
            'total_processing_time': 0.0,
            'api_calls': 0,
            'api_errors': 0
        }
    
    def track_directive(self, success: bool, duration: float, tokens_in: int = 0, 
                       tokens_out: int = 0, cost: float = 0.0):
        """Track directive completion metrics"""
        self.metrics['directives_processed'] += 1
        
        if success:
            self.metrics['directives_succeeded'] += 1
        else:
            self.metrics['directives_failed'] += 1
        
        self.metrics['total_tokens_in'] += tokens_in
        self.metrics['total_tokens_out'] += tokens_out
        self.metrics['total_cost'] += cost
        self.metrics['total_processing_time'] += duration
    
    def track_api_call(self, success: bool):
        """Track API call metrics"""
        self.metrics['api_calls'] += 1
        if not success:
            self.metrics['api_errors'] += 1
    
    def log_summary(self):
        """Log performance summary"""
        success_rate = (self.metrics['directives_succeeded'] / 
                       max(self.metrics['directives_processed'], 1)) * 100
        
        avg_duration = (self.metrics['total_processing_time'] / 
                       max(self.metrics['directives_processed'], 1))
        
        api_error_rate = (self.metrics['api_errors'] / 
                         max(self.metrics['api_calls'], 1)) * 100
        
        self.logger.system_status(
            **self.metrics,
            success_rate=f"{success_rate:.1f}%",
            avg_duration=f"{avg_duration:.2f}s",
            api_error_rate=f"{api_error_rate:.1f}%"
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        return self.metrics.copy()


# Global logger instance
_logger_instance: Optional[ComputerLogger] = None


def get_logger(name: str = "computer", base_path: str = ".") -> ComputerLogger:
    """Get global logger instance"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = ComputerLogger(name, base_path)
    return _logger_instance


def setup_logging(base_path: str = ".", log_file: str = None):
    """Setup logging configuration"""
    settings = get_settings(base_path)
    if log_file:
        settings.set('log_file', log_file)
    
    # Initialize logger
    return get_logger("computer", base_path)


if __name__ == "__main__":
    # Test logging functionality
    logger = setup_logging(log_file="logs/computer.log")
    tracker = PerformanceTracker(logger)
    
    logger.info("Computer system starting up")
    logger.directive_created("test-123", "Create a test feature", "claude", "claude-3-sonnet")
    logger.directive_started("test-123", "/path/to/directive.md")
    logger.api_request("claude", "claude-3-sonnet", 100)
    logger.api_response("claude", "claude-3-sonnet", True, 50, 0.05)
    logger.directive_completed("test-123", True, 5.2, 100, 50, 0.05)
    
    tracker.track_directive(True, 5.2, 100, 50, 0.05)
    tracker.track_api_call(True)
    tracker.log_summary()
    
    logger.info("Test logging complete")