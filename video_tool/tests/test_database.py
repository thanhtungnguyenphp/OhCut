"""
Tests for database module (job tracking).

Tests cover:
- Database initialization
- Job creation and retrieval
- Job status updates
- Job queries and filtering
- Job logs
- Old job cleanup
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path

from src.core.database import Database, Job, JobStatus


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    db = Database(db_path)
    yield db
    
    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)


class TestDatabaseInitialization:
    """Test database initialization and schema creation."""
    
    def test_database_creation(self, temp_db):
        """Test that database is created successfully."""
        assert os.path.exists(temp_db.db_path)
    
    def test_tables_exist(self, temp_db):
        """Test that required tables are created."""
        import sqlite3
        conn = sqlite3.connect(temp_db.db_path)
        cursor = conn.cursor()
        
        # Check jobs table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'"
        )
        assert cursor.fetchone() is not None
        
        # Check job_logs table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='job_logs'"
        )
        assert cursor.fetchone() is not None
        
        conn.close()
    
    def test_indexes_exist(self, temp_db):
        """Test that indexes are created."""
        import sqlite3
        conn = sqlite3.connect(temp_db.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        )
        indexes = [row[0] for row in cursor.fetchall()]
        
        assert "idx_jobs_status" in indexes
        assert "idx_jobs_created_at" in indexes
        assert "idx_job_logs_job_id" in indexes
        
        conn.close()


class TestJobCreation:
    """Test job creation operations."""
    
    def test_create_job(self, temp_db):
        """Test creating a new job."""
        job_id = temp_db.create_job(
            job_type="cut",
            input_files=["movie.mp4"],
            config={"duration": 60, "copy_codec": True}
        )
        
        assert job_id is not None
        assert job_id > 0
    
    def test_create_job_with_multiple_inputs(self, temp_db):
        """Test creating job with multiple input files."""
        job_id = temp_db.create_job(
            job_type="concat",
            input_files=["part1.mp4", "part2.mp4", "part3.mp4"],
            config={"copy_codec": True}
        )
        
        assert job_id is not None
        
        job = temp_db.get_job(job_id)
        assert len(job.input_files) == 3
        assert job.input_files[0] == "part1.mp4"
    
    def test_create_job_with_profile(self, temp_db):
        """Test creating job with profile configuration."""
        job_id = temp_db.create_job(
            job_type="cut",
            input_files=["movie.mp4"],
            config={
                "duration": 11,
                "copy_codec": False,
                "profile_name": "clip_720p"
            }
        )
        
        job = temp_db.get_job(job_id)
        assert job.config["profile_name"] == "clip_720p"
        assert job.config["copy_codec"] is False
    
    def test_job_initial_status(self, temp_db):
        """Test that new job has PENDING status."""
        job_id = temp_db.create_job(
            job_type="cut",
            input_files=["test.mp4"],
            config={}
        )
        
        job = temp_db.get_job(job_id)
        assert job.status == JobStatus.PENDING
        assert job.progress == 0.0
    
    def test_job_log_created_on_creation(self, temp_db):
        """Test that log entry is created when job is created."""
        job_id = temp_db.create_job(
            job_type="cut",
            input_files=["test.mp4"],
            config={}
        )
        
        logs = temp_db.get_job_logs(job_id)
        assert len(logs) == 1
        assert logs[0]["level"] == "INFO"
        assert "Job created" in logs[0]["message"]


class TestJobRetrieval:
    """Test job retrieval operations."""
    
    def test_get_job_by_id(self, temp_db):
        """Test retrieving job by ID."""
        job_id = temp_db.create_job(
            job_type="cut",
            input_files=["movie.mp4"],
            config={"duration": 60}
        )
        
        job = temp_db.get_job(job_id)
        assert job is not None
        assert job.id == job_id
        assert job.job_type == "cut"
        assert job.input_files == ["movie.mp4"]
    
    def test_get_nonexistent_job(self, temp_db):
        """Test retrieving job that doesn't exist."""
        job = temp_db.get_job(99999)
        assert job is None
    
    def test_job_attributes(self, temp_db):
        """Test that job has all required attributes."""
        job_id = temp_db.create_job(
            job_type="concat",
            input_files=["a.mp4", "b.mp4"],
            config={"test": "value"}
        )
        
        job = temp_db.get_job(job_id)
        assert hasattr(job, "id")
        assert hasattr(job, "job_type")
        assert hasattr(job, "status")
        assert hasattr(job, "input_files")
        assert hasattr(job, "output_files")
        assert hasattr(job, "config")
        assert hasattr(job, "created_at")
        assert hasattr(job, "started_at")
        assert hasattr(job, "completed_at")
        assert hasattr(job, "error_message")
        assert hasattr(job, "retry_count")
        assert hasattr(job, "progress")


class TestJobStatusUpdates:
    """Test job status update operations."""
    
    def test_update_status_to_running(self, temp_db):
        """Test updating job status to RUNNING."""
        job_id = temp_db.create_job(
            job_type="cut",
            input_files=["test.mp4"],
            config={}
        )
        
        temp_db.update_job_status(job_id, JobStatus.RUNNING)
        
        job = temp_db.get_job(job_id)
        assert job.status == JobStatus.RUNNING
        assert job.started_at is not None
    
    def test_update_status_to_completed(self, temp_db):
        """Test updating job status to COMPLETED."""
        job_id = temp_db.create_job(
            job_type="cut",
            input_files=["test.mp4"],
            config={}
        )
        
        temp_db.update_job_status(job_id, JobStatus.RUNNING)
        temp_db.update_job_status(
            job_id,
            JobStatus.COMPLETED,
            progress=100.0,
            output_files=["out1.mp4", "out2.mp4"]
        )
        
        job = temp_db.get_job(job_id)
        assert job.status == JobStatus.COMPLETED
        assert job.progress == 100.0
        assert job.completed_at is not None
        assert len(job.output_files) == 2
    
    def test_update_status_to_failed(self, temp_db):
        """Test updating job status to FAILED with error message."""
        job_id = temp_db.create_job(
            job_type="cut",
            input_files=["test.mp4"],
            config={}
        )
        
        temp_db.update_job_status(job_id, JobStatus.RUNNING)
        temp_db.update_job_status(
            job_id,
            JobStatus.FAILED,
            error_message="FFmpeg command failed"
        )
        
        job = temp_db.get_job(job_id)
        assert job.status == JobStatus.FAILED
        assert job.error_message == "FFmpeg command failed"
        assert job.completed_at is not None
    
    def test_update_progress(self, temp_db):
        """Test updating job progress."""
        job_id = temp_db.create_job(
            job_type="cut",
            input_files=["test.mp4"],
            config={}
        )
        
        temp_db.update_job_status(job_id, JobStatus.RUNNING, progress=25.0)
        job = temp_db.get_job(job_id)
        assert job.progress == 25.0
        
        temp_db.update_job_status(job_id, JobStatus.RUNNING, progress=50.0)
        job = temp_db.get_job(job_id)
        assert job.progress == 50.0
    
    def test_status_update_creates_log(self, temp_db):
        """Test that status updates create log entries."""
        job_id = temp_db.create_job(
            job_type="cut",
            input_files=["test.mp4"],
            config={}
        )
        
        temp_db.update_job_status(job_id, JobStatus.RUNNING)
        temp_db.update_job_status(job_id, JobStatus.COMPLETED, progress=100.0)
        
        logs = temp_db.get_job_logs(job_id)
        assert len(logs) >= 3  # Created, running, completed


class TestJobQueries:
    """Test job querying and filtering."""
    
    def test_list_all_jobs(self, temp_db):
        """Test listing all jobs."""
        # Create multiple jobs
        for i in range(5):
            temp_db.create_job(
                job_type="cut",
                input_files=[f"video{i}.mp4"],
                config={}
            )
        
        jobs = temp_db.list_jobs()
        assert len(jobs) == 5
    
    def test_list_jobs_with_limit(self, temp_db):
        """Test listing jobs with limit."""
        # Create 10 jobs
        for i in range(10):
            temp_db.create_job(
                job_type="cut",
                input_files=[f"video{i}.mp4"],
                config={}
            )
        
        jobs = temp_db.list_jobs(limit=5)
        assert len(jobs) == 5
    
    def test_list_jobs_by_status(self, temp_db):
        """Test filtering jobs by status."""
        # Create jobs with different statuses
        job1 = temp_db.create_job(job_type="cut", input_files=["a.mp4"], config={})
        job2 = temp_db.create_job(job_type="cut", input_files=["b.mp4"], config={})
        job3 = temp_db.create_job(job_type="cut", input_files=["c.mp4"], config={})
        
        temp_db.update_job_status(job1, JobStatus.COMPLETED, progress=100.0)
        temp_db.update_job_status(job2, JobStatus.FAILED, error_message="Error")
        # job3 remains PENDING
        
        completed_jobs = temp_db.list_jobs(status=JobStatus.COMPLETED)
        assert len(completed_jobs) == 1
        assert completed_jobs[0].id == job1
        
        failed_jobs = temp_db.list_jobs(status=JobStatus.FAILED)
        assert len(failed_jobs) == 1
        assert failed_jobs[0].id == job2
        
        pending_jobs = temp_db.list_jobs(status=JobStatus.PENDING)
        assert len(pending_jobs) == 1
        assert pending_jobs[0].id == job3
    
    def test_list_jobs_ordered_by_created_at(self, temp_db):
        """Test that jobs are ordered by creation time (newest first)."""
        job1 = temp_db.create_job(job_type="cut", input_files=["a.mp4"], config={})
        job2 = temp_db.create_job(job_type="cut", input_files=["b.mp4"], config={})
        job3 = temp_db.create_job(job_type="cut", input_files=["c.mp4"], config={})
        
        jobs = temp_db.list_jobs()
        assert jobs[0].id == job3  # Newest first
        assert jobs[1].id == job2
        assert jobs[2].id == job1


class TestJobLogs:
    """Test job logging operations."""
    
    def test_add_job_log(self, temp_db):
        """Test adding log entry to job."""
        job_id = temp_db.create_job(
            job_type="cut",
            input_files=["test.mp4"],
            config={}
        )
        
        temp_db.add_job_log(job_id, "INFO", "Processing started")
        temp_db.add_job_log(job_id, "INFO", "Processing 50%")
        temp_db.add_job_log(job_id, "INFO", "Processing complete")
        
        logs = temp_db.get_job_logs(job_id)
        assert len(logs) >= 4  # 1 from creation + 3 added
    
    def test_add_error_log(self, temp_db):
        """Test adding error log entry."""
        job_id = temp_db.create_job(
            job_type="cut",
            input_files=["test.mp4"],
            config={}
        )
        
        temp_db.add_job_log(job_id, "ERROR", "FFmpeg failed")
        
        logs = temp_db.get_job_logs(job_id)
        error_logs = [log for log in logs if log["level"] == "ERROR"]
        assert len(error_logs) == 1
        assert error_logs[0]["message"] == "FFmpeg failed"
    
    def test_get_logs_for_nonexistent_job(self, temp_db):
        """Test getting logs for job that doesn't exist."""
        logs = temp_db.get_job_logs(99999)
        assert logs == []
    
    def test_log_timestamps(self, temp_db):
        """Test that log entries have timestamps."""
        job_id = temp_db.create_job(
            job_type="cut",
            input_files=["test.mp4"],
            config={}
        )
        
        logs = temp_db.get_job_logs(job_id)
        assert len(logs) > 0
        assert "timestamp" in logs[0]
        assert logs[0]["timestamp"] is not None


class TestJobCleanup:
    """Test old job cleanup operations."""
    
    def test_cleanup_old_completed_jobs(self, temp_db):
        """Test removing old completed jobs."""
        # Create completed job
        job_id = temp_db.create_job(
            job_type="cut",
            input_files=["test.mp4"],
            config={}
        )
        temp_db.update_job_status(job_id, JobStatus.COMPLETED, progress=100.0)
        
        # Manually set completed_at to old date
        import sqlite3
        conn = sqlite3.connect(temp_db.db_path)
        cursor = conn.cursor()
        old_date = (datetime.now() - timedelta(days=60)).isoformat()
        cursor.execute(
            "UPDATE jobs SET completed_at = ? WHERE id = ?",
            (old_date, job_id)
        )
        conn.commit()
        conn.close()
        
        # Cleanup jobs older than 30 days
        deleted_count = temp_db.cleanup_old_jobs(days=30)
        assert deleted_count == 1
        
        # Verify job is gone
        job = temp_db.get_job(job_id)
        assert job is None
    
    def test_cleanup_preserves_recent_jobs(self, temp_db):
        """Test that recent jobs are not deleted."""
        job_id = temp_db.create_job(
            job_type="cut",
            input_files=["test.mp4"],
            config={}
        )
        temp_db.update_job_status(job_id, JobStatus.COMPLETED, progress=100.0)
        
        # Cleanup jobs older than 30 days (this one is recent)
        deleted_count = temp_db.cleanup_old_jobs(days=30)
        assert deleted_count == 0
        
        # Verify job still exists
        job = temp_db.get_job(job_id)
        assert job is not None
    
    def test_cleanup_only_completed_jobs(self, temp_db):
        """Test that only completed jobs are cleaned up."""
        # Create jobs with different statuses
        job1 = temp_db.create_job(job_type="cut", input_files=["a.mp4"], config={})
        job2 = temp_db.create_job(job_type="cut", input_files=["b.mp4"], config={})
        
        temp_db.update_job_status(job1, JobStatus.COMPLETED, progress=100.0)
        temp_db.update_job_status(job2, JobStatus.FAILED, error_message="Error")
        
        # Set old dates for both
        import sqlite3
        conn = sqlite3.connect(temp_db.db_path)
        cursor = conn.cursor()
        old_date = (datetime.now() - timedelta(days=60)).isoformat()
        cursor.execute(
            "UPDATE jobs SET completed_at = ? WHERE id IN (?, ?)",
            (old_date, job1, job2)
        )
        conn.commit()
        conn.close()
        
        # Cleanup should only remove completed jobs
        deleted_count = temp_db.cleanup_old_jobs(days=30)
        assert deleted_count == 1
        
        # Verify completed job is gone but failed job remains
        assert temp_db.get_job(job1) is None
        assert temp_db.get_job(job2) is not None


class TestRetryCount:
    """Test retry count operations."""
    
    def test_increment_retry_count(self, temp_db):
        """Test incrementing retry count."""
        job_id = temp_db.create_job(
            job_type="cut",
            input_files=["test.mp4"],
            config={}
        )
        
        job = temp_db.get_job(job_id)
        assert job.retry_count == 0
        
        temp_db.increment_retry_count(job_id)
        job = temp_db.get_job(job_id)
        assert job.retry_count == 1
        
        temp_db.increment_retry_count(job_id)
        job = temp_db.get_job(job_id)
        assert job.retry_count == 2
    
    def test_retry_count_log_entry(self, temp_db):
        """Test that incrementing retry count creates log entry."""
        job_id = temp_db.create_job(
            job_type="cut",
            input_files=["test.mp4"],
            config={}
        )
        
        temp_db.increment_retry_count(job_id)
        
        logs = temp_db.get_job_logs(job_id)
        retry_logs = [log for log in logs if "Retry" in log["message"]]
        assert len(retry_logs) == 1


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_input_files(self, temp_db):
        """Test creating job with empty input files list."""
        job_id = temp_db.create_job(
            job_type="cut",
            input_files=[],
            config={}
        )
        
        job = temp_db.get_job(job_id)
        assert job.input_files == []
    
    def test_empty_config(self, temp_db):
        """Test creating job with empty config."""
        job_id = temp_db.create_job(
            job_type="cut",
            input_files=["test.mp4"],
            config={}
        )
        
        job = temp_db.get_job(job_id)
        assert job.config == {}
    
    def test_long_error_message(self, temp_db):
        """Test storing long error message."""
        job_id = temp_db.create_job(
            job_type="cut",
            input_files=["test.mp4"],
            config={}
        )
        
        long_error = "Error: " + "x" * 1000
        temp_db.update_job_status(
            job_id,
            JobStatus.FAILED,
            error_message=long_error
        )
        
        job = temp_db.get_job(job_id)
        assert job.error_message == long_error
