"""
Database module for job tracking and history.

Provides SQLite-based storage for video processing jobs, enabling
job history, status tracking, retry capability, and progress monitoring.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)


class JobStatus(Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Job:
    """
    Job data model.
    
    Attributes:
        id: Unique job identifier
        job_type: Type of operation (cut, concat, extract_audio, etc.)
        status: Current job status
        input_files: List of input file paths
        output_files: List of output file paths (populated after completion)
        config: Job configuration (duration, profile, etc.)
        created_at: Job creation timestamp
        started_at: Job start timestamp
        completed_at: Job completion timestamp
        error_message: Error message if failed
        retry_count: Number of retry attempts
        progress: Job progress percentage (0-100)
    """
    id: Optional[int]
    job_type: str
    status: JobStatus
    input_files: List[str]
    output_files: Optional[List[str]]
    config: Dict[str, Any]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    retry_count: int
    progress: float


class Database:
    """
    SQLite database interface for job tracking.
    
    Manages job lifecycle: creation, status updates, queries, and cleanup.
    Thread-safe for basic concurrent operations.
    
    Example:
        ```python
        db = Database()
        job_id = db.create_job(
            job_type="cut",
            input_files=["movie.mp4"],
            config={"duration": 11, "copy_codec": True}
        )
        db.update_job_status(job_id, JobStatus.RUNNING)
        # ... perform operation ...
        db.update_job_status(
            job_id, 
            JobStatus.COMPLETED, 
            progress=100.0,
            output_files=["part_001.mp4", "part_002.mp4"]
        )
        ```
    """
    
    def __init__(self, db_path: str = "jobs.db"):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file (default: jobs.db)
        """
        self.db_path = db_path
        self.init_database()
        logger.info(f"Database initialized: {db_path}")
    
    def init_database(self):
        """
        Initialize database tables and indexes.
        
        Creates jobs and job_logs tables if they don't exist.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create jobs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_type TEXT NOT NULL,
                status TEXT NOT NULL,
                input_files TEXT NOT NULL,
                output_files TEXT,
                config TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                progress REAL DEFAULT 0.0
            )
        """)
        
        # Create job_logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                FOREIGN KEY (job_id) REFERENCES jobs(id)
            )
        """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_jobs_status 
            ON jobs(status)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_jobs_created_at 
            ON jobs(created_at)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_job_logs_job_id 
            ON job_logs(job_id)
        """)
        
        conn.commit()
        conn.close()
    
    def create_job(
        self,
        job_type: str,
        input_files: List[str],
        config: Dict[str, Any]
    ) -> int:
        """
        Create new job record.
        
        Args:
            job_type: Type of operation (cut, concat, extract_audio, etc.)
            input_files: List of input file paths
            config: Job configuration dictionary
            
        Returns:
            Job ID
            
        Example:
            ```python
            job_id = db.create_job(
                job_type="cut",
                input_files=["movie.mp4"],
                config={"duration": 11, "profile": "clip_720p"}
            )
            ```
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO jobs (job_type, status, input_files, config)
            VALUES (?, ?, ?, ?)
        """, (
            job_type,
            JobStatus.PENDING.value,
            json.dumps(input_files),
            json.dumps(config)
        ))
        
        job_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        self.add_job_log(job_id, "INFO", f"Job created: {job_type}")
        logger.info(f"Created job {job_id}: {job_type}")
        
        return job_id
    
    def update_job_status(
        self,
        job_id: int,
        status: JobStatus,
        progress: Optional[float] = None,
        output_files: Optional[List[str]] = None,
        error_message: Optional[str] = None
    ):
        """
        Update job status and metadata.
        
        Args:
            job_id: Job ID to update
            status: New job status
            progress: Progress percentage (0-100)
            output_files: List of output file paths
            error_message: Error message if failed
            
        Example:
            ```python
            db.update_job_status(
                job_id=1,
                status=JobStatus.COMPLETED,
                progress=100.0,
                output_files=["output1.mp4", "output2.mp4"]
            )
            ```
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build UPDATE query dynamically
        updates = ["status = ?"]
        params = [status.value]
        
        if progress is not None:
            updates.append("progress = ?")
            params.append(progress)
        
        if output_files is not None:
            updates.append("output_files = ?")
            params.append(json.dumps(output_files))
        
        if error_message is not None:
            updates.append("error_message = ?")
            params.append(error_message)
        
        # Set timestamps based on status
        if status == JobStatus.RUNNING:
            updates.append("started_at = ?")
            params.append(datetime.now().isoformat())
        elif status in (JobStatus.COMPLETED, JobStatus.FAILED):
            updates.append("completed_at = ?")
            params.append(datetime.now().isoformat())
        
        params.append(job_id)
        
        cursor.execute(f"""
            UPDATE jobs 
            SET {', '.join(updates)}
            WHERE id = ?
        """, params)
        
        conn.commit()
        conn.close()
        
        # Add log entry
        log_message = f"Status updated: {status.value}"
        if progress is not None:
            log_message += f" ({progress:.1f}%)"
        self.add_job_log(job_id, "INFO", log_message)
        
        if status == JobStatus.FAILED and error_message:
            self.add_job_log(job_id, "ERROR", error_message)
        
        logger.info(f"Updated job {job_id}: {status.value}")
    
    def get_job(self, job_id: int) -> Optional[Job]:
        """
        Retrieve job by ID.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job object or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, job_type, status, input_files, output_files, config,
                   created_at, started_at, completed_at, error_message,
                   retry_count, progress
            FROM jobs
            WHERE id = ?
        """, (job_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return self._row_to_job(row)
    
    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        limit: int = 100
    ) -> List[Job]:
        """
        List jobs with optional filtering.
        
        Args:
            status: Filter by job status (None for all)
            limit: Maximum number of jobs to return
            
        Returns:
            List of Job objects
            
        Example:
            ```python
            # Get all failed jobs
            failed_jobs = db.list_jobs(status=JobStatus.FAILED)
            
            # Get recent 50 jobs
            recent = db.list_jobs(limit=50)
            ```
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if status:
            cursor.execute("""
                SELECT id, job_type, status, input_files, output_files, config,
                       created_at, started_at, completed_at, error_message,
                       retry_count, progress
                FROM jobs
                WHERE status = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (status.value, limit))
        else:
            cursor.execute("""
                SELECT id, job_type, status, input_files, output_files, config,
                       created_at, started_at, completed_at, error_message,
                       retry_count, progress
                FROM jobs
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_job(row) for row in rows]
    
    def add_job_log(
        self,
        job_id: int,
        level: str,
        message: str
    ):
        """
        Add log entry for job.
        
        Args:
            job_id: Job ID
            level: Log level (INFO, WARNING, ERROR)
            message: Log message
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO job_logs (job_id, level, message)
            VALUES (?, ?, ?)
        """, (job_id, level, message))
        
        conn.commit()
        conn.close()
    
    def get_job_logs(self, job_id: int) -> List[Dict[str, Any]]:
        """
        Retrieve logs for a job.
        
        Args:
            job_id: Job ID
            
        Returns:
            List of log entries as dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT timestamp, level, message
            FROM job_logs
            WHERE job_id = ?
            ORDER BY timestamp ASC
        """, (job_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "timestamp": row[0],
                "level": row[1],
                "message": row[2]
            }
            for row in rows
        ]
    
    def cleanup_old_jobs(self, days: int = 30) -> int:
        """
        Remove old completed jobs.
        
        Args:
            days: Remove jobs older than this many days
            
        Returns:
            Number of jobs deleted
            
        Example:
            ```python
            # Remove jobs older than 90 days
            deleted = db.cleanup_old_jobs(days=90)
            print(f"Deleted {deleted} old jobs")
            ```
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Delete old completed jobs
        cursor.execute("""
            DELETE FROM jobs
            WHERE status = ?
            AND completed_at < ?
        """, (JobStatus.COMPLETED.value, cutoff_date.isoformat()))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        logger.info(f"Cleaned up {deleted_count} old jobs (older than {days} days)")
        return deleted_count
    
    def increment_retry_count(self, job_id: int):
        """
        Increment retry count for a job.
        
        Args:
            job_id: Job ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE jobs
            SET retry_count = retry_count + 1
            WHERE id = ?
        """, (job_id,))
        
        conn.commit()
        conn.close()
        
        self.add_job_log(job_id, "INFO", "Retry attempt incremented")
    
    def _row_to_job(self, row: tuple) -> Job:
        """
        Convert database row to Job object.
        
        Args:
            row: Database row tuple
            
        Returns:
            Job object
        """
        return Job(
            id=row[0],
            job_type=row[1],
            status=JobStatus(row[2]),
            input_files=json.loads(row[3]),
            output_files=json.loads(row[4]) if row[4] else None,
            config=json.loads(row[5]) if row[5] else {},
            created_at=datetime.fromisoformat(row[6]) if row[6] else datetime.now(),
            started_at=datetime.fromisoformat(row[7]) if row[7] else None,
            completed_at=datetime.fromisoformat(row[8]) if row[8] else None,
            error_message=row[9],
            retry_count=row[10],
            progress=row[11]
        )
