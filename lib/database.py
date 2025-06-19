#!/usr/bin/env python3
"""
SQLite database for Computer project metadata storage
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class DirectiveRecord:
    """Data class for directive records"""
    id: str
    content: str
    status: str
    priority: str
    platform: Optional[str]
    model: Optional[str]
    created_at: datetime
    updated_at: datetime
    file_path: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost: float = 0.0
    processing_time: float = 0.0
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ComputerDatabase:
    """SQLite database for storing directive metadata and metrics"""
    
    def __init__(self, db_path: str = "computer.db"):
        self.db_path = Path(db_path)
        self.connection = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database and create tables"""
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row  # Enable column access by name
        
        self._create_tables()
    
    def _create_tables(self):
        """Create database tables"""
        cursor = self.connection.cursor()
        
        # Directives table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS directives (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                status TEXT NOT NULL,
                priority TEXT NOT NULL,
                platform TEXT,
                model TEXT,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                file_path TEXT NOT NULL,
                tokens_in INTEGER DEFAULT 0,
                tokens_out INTEGER DEFAULT 0,
                cost REAL DEFAULT 0.0,
                processing_time REAL DEFAULT 0.0,
                error_message TEXT,
                metadata TEXT
            )
        """)
        
        # Performance metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                directive_id TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                platform TEXT,
                model TEXT,
                tokens_in INTEGER,
                tokens_out INTEGER,
                cost REAL,
                processing_time REAL,
                success BOOLEAN,
                FOREIGN KEY (directive_id) REFERENCES directives (id)
            )
        """)
        
        # System events table for logging
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP NOT NULL,
                event_type TEXT NOT NULL,
                component TEXT,
                message TEXT,
                data TEXT
            )
        """)
        
        # API usage tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP NOT NULL,
                platform TEXT NOT NULL,
                model TEXT NOT NULL,
                tokens_in INTEGER,
                tokens_out INTEGER,
                cost REAL,
                success BOOLEAN,
                response_time REAL,
                error_message TEXT
            )
        """)
        
        # Create indices for common queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_directives_status ON directives (status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_directives_created ON directives (created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_performance_timestamp ON performance_metrics (timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_system_events_timestamp ON system_events (timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_usage_timestamp ON api_usage (timestamp)")
        
        self.connection.commit()
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def insert_directive(self, directive: DirectiveRecord) -> bool:
        """Insert or update a directive record"""
        try:
            cursor = self.connection.cursor()
            
            metadata_json = json.dumps(directive.metadata) if directive.metadata else None
            
            cursor.execute("""
                INSERT OR REPLACE INTO directives 
                (id, content, status, priority, platform, model, created_at, updated_at,
                 file_path, tokens_in, tokens_out, cost, processing_time, error_message, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                directive.id, directive.content, directive.status, directive.priority,
                directive.platform, directive.model, directive.created_at, directive.updated_at,
                directive.file_path, directive.tokens_in, directive.tokens_out,
                directive.cost, directive.processing_time, directive.error_message, metadata_json
            ))
            
            self.connection.commit()
            return True
        except sqlite3.Error as e:
            print(f"Database error inserting directive: {e}")
            return False
    
    def get_directive(self, directive_id: str) -> Optional[DirectiveRecord]:
        """Get a directive by ID"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM directives WHERE id = ?", (directive_id,))
            row = cursor.fetchone()
            
            if row:
                metadata = json.loads(row['metadata']) if row['metadata'] else None
                return DirectiveRecord(
                    id=row['id'],
                    content=row['content'],
                    status=row['status'],
                    priority=row['priority'],
                    platform=row['platform'],
                    model=row['model'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at']),
                    file_path=row['file_path'],
                    tokens_in=row['tokens_in'],
                    tokens_out=row['tokens_out'],
                    cost=row['cost'],
                    processing_time=row['processing_time'],
                    error_message=row['error_message'],
                    metadata=metadata
                )
            return None
        except sqlite3.Error as e:
            print(f"Database error getting directive: {e}")
            return None
    
    def update_directive_status(self, directive_id: str, status: str, 
                              tokens_in: int = None, tokens_out: int = None,
                              cost: float = None, processing_time: float = None,
                              error_message: str = None) -> bool:
        """Update directive status and metrics"""
        try:
            cursor = self.connection.cursor()
            
            updates = ["status = ?", "updated_at = ?"]
            values = [status, datetime.now().isoformat()]
            
            if tokens_in is not None:
                updates.append("tokens_in = ?")
                values.append(tokens_in)
            if tokens_out is not None:
                updates.append("tokens_out = ?")
                values.append(tokens_out)
            if cost is not None:
                updates.append("cost = ?")
                values.append(cost)
            if processing_time is not None:
                updates.append("processing_time = ?")
                values.append(processing_time)
            if error_message is not None:
                updates.append("error_message = ?")
                values.append(error_message)
            
            values.append(directive_id)
            
            cursor.execute(f"""
                UPDATE directives 
                SET {', '.join(updates)}
                WHERE id = ?
            """, values)
            
            self.connection.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Database error updating directive: {e}")
            return False
    
    def get_directives_by_status(self, status: str, limit: int = None) -> List[DirectiveRecord]:
        """Get directives by status"""
        try:
            cursor = self.connection.cursor()
            
            query = "SELECT * FROM directives WHERE status = ? ORDER BY created_at DESC"
            if limit:
                query += f" LIMIT {limit}"
            
            cursor.execute(query, (status,))
            rows = cursor.fetchall()
            
            directives = []
            for row in rows:
                metadata = json.loads(row['metadata']) if row['metadata'] else None
                directives.append(DirectiveRecord(
                    id=row['id'],
                    content=row['content'],
                    status=row['status'],
                    priority=row['priority'],
                    platform=row['platform'],
                    model=row['model'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at']),
                    file_path=row['file_path'],
                    tokens_in=row['tokens_in'],
                    tokens_out=row['tokens_out'],
                    cost=row['cost'],
                    processing_time=row['processing_time'],
                    error_message=row['error_message'],
                    metadata=metadata
                ))
            
            return directives
        except sqlite3.Error as e:
            print(f"Database error getting directives by status: {e}")
            return []
    
    def log_performance_metric(self, directive_id: str, platform: str, model: str,
                             tokens_in: int, tokens_out: int, cost: float,
                             processing_time: float, success: bool) -> bool:
        """Log performance metrics"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO performance_metrics 
                (directive_id, timestamp, platform, model, tokens_in, tokens_out,
                 cost, processing_time, success)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                directive_id, datetime.now().isoformat(), platform, model,
                tokens_in, tokens_out, cost, processing_time, success
            ))
            
            self.connection.commit()
            return True
        except sqlite3.Error as e:
            print(f"Database error logging performance metric: {e}")
            return False
    
    def log_system_event(self, event_type: str, component: str, message: str, 
                        data: Dict[str, Any] = None) -> bool:
        """Log system event"""
        try:
            cursor = self.connection.cursor()
            
            data_json = json.dumps(data) if data else None
            
            cursor.execute("""
                INSERT INTO system_events (timestamp, event_type, component, message, data)
                VALUES (?, ?, ?, ?, ?)
            """, (datetime.now().isoformat(), event_type, component, message, data_json))
            
            self.connection.commit()
            return True
        except sqlite3.Error as e:
            print(f"Database error logging system event: {e}")
            return False
    
    def log_api_usage(self, platform: str, model: str, tokens_in: int, tokens_out: int,
                     cost: float, success: bool, response_time: float,
                     error_message: str = None) -> bool:
        """Log API usage"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO api_usage 
                (timestamp, platform, model, tokens_in, tokens_out, cost,
                 success, response_time, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(), platform, model, tokens_in, tokens_out,
                cost, success, response_time, error_message
            ))
            
            self.connection.commit()
            return True
        except sqlite3.Error as e:
            print(f"Database error logging API usage: {e}")
            return False
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics"""
        try:
            cursor = self.connection.cursor()
            
            # Directive counts by status
            cursor.execute("""
                SELECT status, COUNT(*) as count 
                FROM directives 
                GROUP BY status
            """)
            status_counts = dict(cursor.fetchall())
            
            # Total metrics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_directives,
                    SUM(tokens_in) as total_tokens_in,
                    SUM(tokens_out) as total_tokens_out,
                    SUM(cost) as total_cost,
                    AVG(processing_time) as avg_processing_time
                FROM directives
                WHERE status IN ('success', 'exemplar', 'slow')
            """)
            totals = cursor.fetchone()
            
            # API usage stats
            cursor.execute("""
                SELECT 
                    platform,
                    COUNT(*) as calls,
                    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_calls,
                    SUM(cost) as total_cost
                FROM api_usage 
                GROUP BY platform
            """)
            api_stats = {row['platform']: dict(row) for row in cursor.fetchall()}
            
            return {
                'directive_counts': status_counts,
                'totals': dict(totals) if totals else {},
                'api_usage': api_stats
            }
        except sqlite3.Error as e:
            print(f"Database error getting summary stats: {e}")
            return {}
    
    def cleanup_old_records(self, days: int = 30) -> int:
        """Clean up old records older than specified days"""
        try:
            cursor = self.connection.cursor()
            cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
            cutoff_iso = datetime.fromtimestamp(cutoff_date).isoformat()
            
            # Clean up old performance metrics
            cursor.execute("""
                DELETE FROM performance_metrics 
                WHERE timestamp < ?
            """, (cutoff_iso,))
            perf_deleted = cursor.rowcount
            
            # Clean up old system events
            cursor.execute("""
                DELETE FROM system_events 
                WHERE timestamp < ?
            """, (cutoff_iso,))
            events_deleted = cursor.rowcount
            
            # Clean up old API usage records
            cursor.execute("""
                DELETE FROM api_usage 
                WHERE timestamp < ?
            """, (cutoff_iso,))
            api_deleted = cursor.rowcount
            
            self.connection.commit()
            
            total_deleted = perf_deleted + events_deleted + api_deleted
            print(f"Cleaned up {total_deleted} old records (perf: {perf_deleted}, events: {events_deleted}, api: {api_deleted})")
            
            return total_deleted
        except sqlite3.Error as e:
            print(f"Database error during cleanup: {e}")
            return 0


# Global database instance
_db_instance: Optional[ComputerDatabase] = None


def get_database(db_path: str = "computer.db") -> ComputerDatabase:
    """Get global database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = ComputerDatabase(db_path)
    return _db_instance


if __name__ == "__main__":
    # Test database functionality
    db = ComputerDatabase("test_computer.db")
    
    # Create a test directive
    directive = DirectiveRecord(
        id="test-123",
        content="Test directive",
        status="pending",
        priority="medium",
        platform="claude",
        model="claude-3-sonnet",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        file_path="/test/path.md",
        metadata={"test": "data"}
    )
    
    # Test operations
    print("Testing database operations...")
    
    # Insert directive
    success = db.insert_directive(directive)
    print(f"Insert directive: {'✅' if success else '❌'}")
    
    # Get directive
    retrieved = db.get_directive("test-123")
    print(f"Get directive: {'✅' if retrieved else '❌'}")
    
    # Update status
    success = db.update_directive_status("test-123", "success", tokens_in=100, tokens_out=50, cost=0.05)
    print(f"Update status: {'✅' if success else '❌'}")
    
    # Log metrics
    success = db.log_performance_metric("test-123", "claude", "claude-3-sonnet", 100, 50, 0.05, 5.2, True)
    print(f"Log performance: {'✅' if success else '❌'}")
    
    # Log system event
    success = db.log_system_event("test", "database", "Test event", {"key": "value"})
    print(f"Log system event: {'✅' if success else '❌'}")
    
    # Get stats
    stats = db.get_summary_stats()
    print(f"Get stats: {'✅' if stats else '❌'}")
    print(f"Stats: {stats}")
    
    db.close()
    
    # Clean up test database
    import os
    if os.path.exists("test_computer.db"):
        os.remove("test_computer.db")
    
    print("Database test complete!")