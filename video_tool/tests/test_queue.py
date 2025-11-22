"""Tests for queue system (queue.py)."""

import os
import time
import tempfile
from unittest.mock import Mock, patch, MagicMock
import pytest

from core.database import Database, JobStatus
from core.queue import JobQueue, Worker, WorkerPool


class TestJobQueue:
    """Test JobQueue class."""

    def test_init(self):
        """Test JobQueue initialization."""
        db = Database(":memory:")
        queue = JobQueue(db)
        assert queue.db is db
        assert queue.manager is not None
        assert queue.lock is not None

    def test_get_next_job_with_pending(self):
        """Test getting next pending job."""
        db = Database(":memory:")
        queue = JobQueue(db)

        # Create pending job
        job_id = db.create_job(
            job_type="cut", input_files=["test.mp4"], config={"duration": 60}
        )

        # Get next job
        next_job_id = queue.get_next_job()
        assert next_job_id == job_id

    def test_get_next_job_no_pending(self):
        """Test getting next job when none pending."""
        db = Database(":memory:")
        queue = JobQueue(db)

        # No jobs created
        next_job_id = queue.get_next_job()
        assert next_job_id is None

    def test_get_next_job_skips_running(self):
        """Test that running jobs are skipped."""
        db = Database(":memory:")
        queue = JobQueue(db)

        # Create job and mark as running
        job_id = db.create_job(
            job_type="cut", input_files=["test.mp4"], config={"duration": 60}
        )
        db.update_job_status(job_id, JobStatus.RUNNING)

        # Should return None
        next_job_id = queue.get_next_job()
        assert next_job_id is None

    def test_requeue_job(self):
        """Test requeuing failed job."""
        db = Database(":memory:")
        queue = JobQueue(db)

        # Create and fail a job
        job_id = db.create_job(
            job_type="cut", input_files=["test.mp4"], config={"duration": 60}
        )
        db.update_job_status(job_id, JobStatus.FAILED, error_message="Test error")

        # Requeue
        queue.requeue_job(job_id)

        # Check status
        job = db.get_job(job_id)
        assert job.status == JobStatus.PENDING


class TestWorker:
    """Test Worker class."""

    @patch("core.queue.cut_by_duration")
    def test_execute_cut_job(self, mock_cut):
        """Test executing cut job."""
        db = Database(":memory:")
        queue = JobQueue(db)

        # Create job
        job_id = db.create_job(
            job_type="cut",
            input_files=["test.mp4"],
            config={
                "output_dir": "./output",
                "segment_duration": 660,
                "copy_codec": True,
                "prefix": "part",
            },
        )

        # Mock cut function
        mock_cut.return_value = ["part_001.mp4", "part_002.mp4"]

        # Create worker and execute
        worker = Worker(worker_id=0, queue=queue)
        worker.execute_job(job_id)

        # Verify cut was called
        mock_cut.assert_called_once()
        args = mock_cut.call_args[1]
        assert args["input_path"] == "test.mp4"
        assert args["output_dir"] == "./output"
        assert args["segment_duration"] == 660

        # Verify job completed
        job = db.get_job(job_id)
        assert job.status == JobStatus.COMPLETED

    @patch("core.queue.concat_videos")
    def test_execute_concat_job(self, mock_concat):
        """Test executing concat job."""
        db = Database(":memory:")
        queue = JobQueue(db)

        # Create job
        job_id = db.create_job(
            job_type="concat",
            input_files=["part1.mp4", "part2.mp4"],
            config={
                "output_path": "final.mp4",
                "copy_codec": True,
                "validate_compatibility": True,
            },
        )

        # Create worker and execute
        worker = Worker(worker_id=0, queue=queue)
        worker.execute_job(job_id)

        # Verify concat was called
        mock_concat.assert_called_once()
        args = mock_concat.call_args[1]
        assert args["input_files"] == ["part1.mp4", "part2.mp4"]
        assert args["output_path"] == "final.mp4"

        # Verify job completed
        job = db.get_job(job_id)
        assert job.status == JobStatus.COMPLETED

    @patch("core.queue.extract_audio")
    def test_execute_extract_audio_job(self, mock_extract):
        """Test executing extract audio job."""
        db = Database(":memory:")
        queue = JobQueue(db)

        # Create job
        job_id = db.create_job(
            job_type="extract_audio",
            input_files=["video.mp4"],
            config={"output_path": "audio.m4a", "codec": "copy"},
        )

        # Create worker and execute
        worker = Worker(worker_id=0, queue=queue)
        worker.execute_job(job_id)

        # Verify extract was called
        mock_extract.assert_called_once()
        args = mock_extract.call_args[1]
        assert args["input_path"] == "video.mp4"
        assert args["output_path"] == "audio.m4a"

        # Verify job completed
        job = db.get_job(job_id)
        assert job.status == JobStatus.COMPLETED

    @patch("core.queue.replace_audio")
    def test_execute_replace_audio_job(self, mock_replace):
        """Test executing replace audio job."""
        db = Database(":memory:")
        queue = JobQueue(db)

        # Create job
        job_id = db.create_job(
            job_type="replace_audio",
            input_files=["video.mp4", "audio.m4a"],
            config={
                "video_path": "video.mp4",
                "audio_path": "audio.m4a",
                "output_path": "final.mp4",
            },
        )

        # Create worker and execute
        worker = Worker(worker_id=0, queue=queue)
        worker.execute_job(job_id)

        # Verify replace was called
        mock_replace.assert_called_once()
        args = mock_replace.call_args[1]
        assert args["video_path"] == "video.mp4"
        assert args["audio_path"] == "audio.m4a"

        # Verify job completed
        job = db.get_job(job_id)
        assert job.status == JobStatus.COMPLETED

    @patch("core.queue.cut_by_duration")
    def test_execute_job_handles_errors(self, mock_cut):
        """Test that worker handles job execution errors."""
        db = Database(":memory:")
        queue = JobQueue(db)

        # Create job
        job_id = db.create_job(
            job_type="cut",
            input_files=["test.mp4"],
            config={"output_dir": "./output", "segment_duration": 660},
        )

        # Mock cut to raise error
        mock_cut.side_effect = Exception("FFmpeg error")

        # Create worker and execute
        worker = Worker(worker_id=0, queue=queue)
        worker.execute_job(job_id)

        # Verify job failed
        job = db.get_job(job_id)
        assert job.status == JobStatus.FAILED
        assert "FFmpeg error" in job.error_message
        assert job.retry_count == 1

    def test_execute_job_unknown_type(self):
        """Test handling unknown job type."""
        db = Database(":memory:")
        queue = JobQueue(db)

        # Create job with unknown type
        job_id = db.create_job(
            job_type="unknown", input_files=["test.mp4"], config={}
        )

        # Create worker and execute
        worker = Worker(worker_id=0, queue=queue)
        worker.execute_job(job_id)

        # Verify job failed
        job = db.get_job(job_id)
        assert job.status == JobStatus.FAILED
        assert "Unknown job type" in job.error_message

    def test_stop(self):
        """Test worker stop."""
        db = Database(":memory:")
        queue = JobQueue(db)
        worker = Worker(worker_id=0, queue=queue)

        # Stop worker
        worker.stop()
        assert worker.running is False


class TestWorkerPool:
    """Test WorkerPool class."""

    def test_init(self):
        """Test WorkerPool initialization."""
        db = Database(":memory:")
        pool = WorkerPool(num_workers=2, db=db)

        assert pool.num_workers == 2
        assert pool.db is db
        assert len(pool.workers) == 0
        assert pool.running is False

    def test_start_creates_workers(self):
        """Test that start creates worker processes."""
        db = Database(":memory:")
        pool = WorkerPool(num_workers=2, db=db)

        try:
            pool.start()

            # Check workers created
            assert len(pool.workers) == 2
            assert pool.running is True

            # Check PID file created
            assert os.path.exists(".worker_pool.pid")

            # Check workers alive
            time.sleep(1)  # Give workers time to start
            for worker in pool.workers:
                assert worker.is_alive()

        finally:
            # Clean up
            pool.stop()

    def test_stop_terminates_workers(self):
        """Test that stop terminates all workers."""
        db = Database(":memory:")
        pool = WorkerPool(num_workers=2, db=db)

        try:
            pool.start()
            time.sleep(1)

            # Stop pool
            pool.stop()

            # Check workers stopped
            for worker in pool.workers:
                assert not worker.is_alive()

            # Check PID file removed
            assert not os.path.exists(".worker_pool.pid")

            assert pool.running is False

        finally:
            # Ensure cleanup
            if os.path.exists(".worker_pool.pid"):
                os.remove(".worker_pool.pid")

    def test_status(self):
        """Test worker pool status."""
        db = Database(":memory:")
        pool = WorkerPool(num_workers=2, db=db)

        # Status before start
        status = pool.status()
        assert status["running"] is False
        assert status["num_workers"] == 2
        assert len(status["workers"]) == 0

        try:
            pool.start()
            time.sleep(1)

            # Status after start
            status = pool.status()
            assert status["running"] is True
            assert len(status["workers"]) == 2

            for worker_status in status["workers"]:
                assert worker_status["alive"] is True
                assert worker_status["pid"] is not None

        finally:
            pool.stop()

    def test_is_running(self):
        """Test is_running check."""
        db = Database(":memory:")
        pool = WorkerPool(num_workers=1, db=db)

        assert pool.is_running() is False

        try:
            pool.start()
            time.sleep(1)
            assert pool.is_running() is True

            pool.stop()
            assert pool.is_running() is False

        finally:
            if pool.running:
                pool.stop()

    def test_from_pid_file_not_exists(self):
        """Test from_pid_file when file doesn't exist."""
        # Clean up any existing PID file
        if os.path.exists(".worker_pool.pid"):
            os.remove(".worker_pool.pid")

        result = WorkerPool.from_pid_file()
        assert result is None

    def test_from_pid_file_stale(self):
        """Test from_pid_file with stale PID."""
        # Create fake PID file with invalid PID
        with open(".worker_pool.pid", "w") as f:
            f.write("999999")

        try:
            result = WorkerPool.from_pid_file()
            assert result is None

            # Should have removed stale file
            assert not os.path.exists(".worker_pool.pid")

        finally:
            if os.path.exists(".worker_pool.pid"):
                os.remove(".worker_pool.pid")


class TestWorkerPoolIntegration:
    """Integration tests for worker pool with real jobs."""

    @patch("core.queue.cut_by_duration")
    def test_worker_processes_pending_job(self, mock_cut):
        """Test that workers process pending jobs from queue."""
        db = Database(":memory:")

        # Create pending job
        job_id = db.create_job(
            job_type="cut",
            input_files=["test.mp4"],
            config={
                "output_dir": "./output",
                "segment_duration": 60,
                "copy_codec": True,
                "prefix": "part",
            },
        )

        # Mock cut function
        mock_cut.return_value = ["part_001.mp4"]

        # Start worker pool
        pool = WorkerPool(num_workers=1, db=db, check_interval=1)

        try:
            pool.start()

            # Wait for job to be processed (max 10 seconds)
            for _ in range(10):
                time.sleep(1)
                job = db.get_job(job_id)
                if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                    break

            # Verify job completed
            job = db.get_job(job_id)
            assert job.status == JobStatus.COMPLETED
            mock_cut.assert_called_once()

        finally:
            pool.stop()

    @patch("core.queue.concat_videos")
    @patch("core.queue.cut_by_duration")
    def test_multiple_workers_process_concurrent_jobs(self, mock_cut, mock_concat):
        """Test multiple workers processing jobs concurrently."""
        db = Database(":memory:")

        # Create multiple jobs
        job1_id = db.create_job(
            job_type="cut",
            input_files=["test1.mp4"],
            config={"output_dir": "./output", "segment_duration": 60},
        )
        job2_id = db.create_job(
            job_type="concat",
            input_files=["part1.mp4", "part2.mp4"],
            config={"output_path": "final.mp4"},
        )

        # Mock functions
        mock_cut.return_value = ["part_001.mp4"]
        mock_concat.return_value = None

        # Start worker pool with 2 workers
        pool = WorkerPool(num_workers=2, db=db, check_interval=1)

        try:
            pool.start()

            # Wait for jobs to be processed (max 15 seconds)
            for _ in range(15):
                time.sleep(1)
                job1 = db.get_job(job1_id)
                job2 = db.get_job(job2_id)
                if job1.status in [JobStatus.COMPLETED, JobStatus.FAILED] and job2.status in [
                    JobStatus.COMPLETED,
                    JobStatus.FAILED,
                ]:
                    break

            # Verify both jobs completed
            job1 = db.get_job(job1_id)
            job2 = db.get_job(job2_id)
            assert job1.status == JobStatus.COMPLETED
            assert job2.status == JobStatus.COMPLETED

            mock_cut.assert_called_once()
            mock_concat.assert_called_once()

        finally:
            pool.stop()
