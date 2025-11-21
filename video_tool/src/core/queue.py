"""
Queue system for background job processing.

Provides worker pool management for async video operations.
Workers process jobs from database queue in background.
"""

import os
import time
import signal
import logging
from multiprocessing import Process, Manager
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from core.database import Database, JobStatus
from core.video_ops import cut_by_duration, concat_videos
from core.audio_ops import extract_audio, replace_audio

logger = logging.getLogger(__name__)


class JobQueue:
    """
    Manage job queue with priority support.

    Uses database as queue storage. Workers poll for pending jobs.
    """

    def __init__(self, db: Database):
        """
        Initialize job queue.

        Args:
            db: Database instance for job storage
        """
        self.db = db
        self.manager = Manager()
        self.lock = self.manager.Lock()

    def get_next_job(self) -> Optional[int]:
        """
        Get next pending job from queue.

        Returns:
            Job ID if available, None otherwise
        """
        with self.lock:
            # Get oldest pending job
            jobs = self.db.list_jobs(status=JobStatus.PENDING, limit=1)
            if jobs:
                return jobs[0].id
            return None

    def requeue_job(self, job_id: int):
        """
        Requeue failed job for retry.

        Args:
            job_id: Job to requeue
        """
        self.db.update_job_status(job_id, JobStatus.PENDING)


class Worker(Process):
    """
    Worker process that executes jobs from queue.

    Runs as separate process for isolation and CPU parallelism.
    """

    def __init__(
        self, worker_id: int, queue: JobQueue, check_interval: int = 5, timeout: int = 3600
    ):
        """
        Initialize worker process.

        Args:
            worker_id: Unique worker identifier
            queue: JobQueue instance
            check_interval: Seconds to wait between queue checks
            timeout: Max seconds for single job execution
        """
        super().__init__()
        self.worker_id = worker_id
        self.queue = queue
        self.check_interval = check_interval
        self.timeout = timeout
        self.running = False
        self.current_job_id = None

    def run(self):
        """Main worker loop - polls queue and executes jobs."""
        self.running = True
        logger.info(f"Worker {self.worker_id} started (PID: {os.getpid()})")

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        while self.running:
            try:
                job_id = self.queue.get_next_job()

                if job_id:
                    self.current_job_id = job_id
                    logger.info(f"Worker {self.worker_id} processing job {job_id}")
                    self.execute_job(job_id)
                    self.current_job_id = None
                else:
                    # No jobs available, sleep
                    time.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"Worker {self.worker_id} encountered error: {e}", exc_info=True)
                time.sleep(self.check_interval)

        logger.info(f"Worker {self.worker_id} stopped")

    def execute_job(self, job_id: int):
        """
        Execute a job.

        Args:
            job_id: Job to execute
        """
        db = Database()  # Each worker needs own DB connection
        job = db.get_job(job_id)

        if not job:
            logger.error(f"Job {job_id} not found")
            return

        try:
            # Update status to running
            db.update_job_status(job_id, JobStatus.RUNNING)
            db.add_job_log(job_id, "INFO", f"Started by worker {self.worker_id}")

            # Execute based on job type
            if job.job_type == "cut":
                self._execute_cut(job, db)
            elif job.job_type == "concat":
                self._execute_concat(job, db)
            elif job.job_type == "extract_audio":
                self._execute_extract_audio(job, db)
            elif job.job_type == "replace_audio":
                self._execute_replace_audio(job, db)
            else:
                raise ValueError(f"Unknown job type: {job.job_type}")

            # Mark as completed
            db.update_job_status(job_id, JobStatus.COMPLETED, progress=100.0)
            db.add_job_log(job_id, "INFO", "Job completed successfully")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Job {job_id} failed: {error_msg}", exc_info=True)

            # Increment retry count
            job = db.get_job(job_id)
            new_retry_count = job.retry_count + 1

            # Update to failed
            db.update_job_status(job_id, JobStatus.FAILED, error_message=error_msg)
            db.add_job_log(job_id, "ERROR", f"Job failed: {error_msg}")

            # Update retry count
            db.increment_retry_count(job_id)

    def _execute_cut(self, job, db):
        """Execute cut operation."""
        config = job.config
        output_files = cut_by_duration(
            input_path=job.input_files[0],
            output_dir=config["output_dir"],
            segment_duration=config["segment_duration"],
            copy_codec=config.get("copy_codec", True),
            prefix=config.get("prefix", "part"),
            profile_name=config.get("profile_name"),
            track_job=False,  # Already tracked
        )

        # Update with output files
        db.update_job_status(job.id, JobStatus.RUNNING, output_files=output_files)

    def _execute_concat(self, job, db):
        """Execute concat operation."""
        config = job.config
        concat_videos(
            input_files=job.input_files,
            output_path=config["output_path"],
            copy_codec=config.get("copy_codec", True),
            validate_compatibility=config.get("validate_compatibility", True),
            profile_name=config.get("profile_name"),
        )

        # Update with output file
        db.update_job_status(job.id, JobStatus.RUNNING, output_files=[config["output_path"]])

    def _execute_extract_audio(self, job, db):
        """Execute extract audio operation."""
        config = job.config
        extract_audio(
            input_path=job.input_files[0],
            output_path=config["output_path"],
            codec=config.get("codec", "copy"),
            bitrate=config.get("bitrate"),
        )

        db.update_job_status(job.id, JobStatus.RUNNING, output_files=[config["output_path"]])

    def _execute_replace_audio(self, job, db):
        """Execute replace audio operation."""
        config = job.config
        replace_audio(
            video_path=config["video_path"],
            audio_path=config["audio_path"],
            output_path=config["output_path"],
        )

        db.update_job_status(job.id, JobStatus.RUNNING, output_files=[config["output_path"]])

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Worker {self.worker_id} received signal {signum}")
        self.stop()

    def stop(self):
        """Stop worker gracefully."""
        logger.info(f"Worker {self.worker_id} stopping...")
        self.running = False


class WorkerPool:
    """
    Manage pool of worker processes.

    Provides start/stop/status management for workers.
    """

    def __init__(
        self,
        num_workers: int = 2,
        db: Optional[Database] = None,
        check_interval: int = 5,
        worker_timeout: int = 3600,
    ):
        """
        Initialize worker pool.

        Args:
            num_workers: Number of worker processes
            db: Database instance (creates new if None)
            check_interval: Seconds between queue checks
            worker_timeout: Max seconds per job
        """
        self.num_workers = num_workers
        self.db = db or Database()
        self.check_interval = check_interval
        self.worker_timeout = worker_timeout
        self.queue = JobQueue(self.db)
        self.workers: List[Worker] = []
        self.running = False
        self.pid_file = ".worker_pool.pid"

    def start(self):
        """Start all workers."""
        if self.running:
            logger.warning("Worker pool already running")
            return

        logger.info(f"Starting worker pool with {self.num_workers} workers")
        self.running = True

        # Write PID file
        with open(self.pid_file, "w") as f:
            f.write(str(os.getpid()))

        # Start workers
        for i in range(self.num_workers):
            worker = Worker(
                worker_id=i,
                queue=self.queue,
                check_interval=self.check_interval,
                timeout=self.worker_timeout,
            )
            worker.start()
            self.workers.append(worker)
            logger.info(f"Started worker {i} (PID: {worker.pid})")

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info("Worker pool started successfully")

    def stop(self, timeout: int = 30):
        """
        Stop all workers gracefully.

        Args:
            timeout: Max seconds to wait for workers to finish
        """
        if not self.running:
            logger.warning("Worker pool not running")
            return

        logger.info("Stopping worker pool...")
        self.running = False

        # Stop all workers
        for worker in self.workers:
            worker.stop()

        # Wait for workers to finish
        start_time = time.time()
        for worker in self.workers:
            remaining = timeout - (time.time() - start_time)
            if remaining > 0:
                worker.join(timeout=remaining)
                if worker.is_alive():
                    logger.warning(f"Worker {worker.worker_id} didn't stop, terminating")
                    worker.terminate()
                    worker.join(timeout=5)
            else:
                logger.warning(f"Timeout exceeded, terminating worker {worker.worker_id}")
                worker.terminate()
                worker.join(timeout=5)

        self.workers.clear()

        # Remove PID file
        if os.path.exists(self.pid_file):
            os.remove(self.pid_file)

        logger.info("Worker pool stopped")

    def status(self) -> Dict[str, Any]:
        """
        Get worker pool status.

        Returns:
            Dict with pool and worker status
        """
        return {
            "running": self.running,
            "num_workers": self.num_workers,
            "pid": os.getpid() if self.running else None,
            "workers": [
                {
                    "id": w.worker_id,
                    "pid": w.pid if w.is_alive() else None,
                    "alive": w.is_alive(),
                    "current_job": w.current_job_id,
                }
                for w in self.workers
            ],
        }

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Worker pool received signal {signum}")
        self.stop()

    def is_running(self) -> bool:
        """Check if pool is running."""
        return self.running and any(w.is_alive() for w in self.workers)

    @classmethod
    def from_pid_file(cls, pid_file: str = ".worker_pool.pid") -> Optional["WorkerPool"]:
        """
        Get running worker pool from PID file.

        Args:
            pid_file: Path to PID file

        Returns:
            WorkerPool instance if running, None otherwise
        """
        if not os.path.exists(pid_file):
            return None

        try:
            with open(pid_file, "r") as f:
                pid = int(f.read().strip())

            # Check if process exists
            os.kill(pid, 0)  # Doesn't actually kill, just checks

            # Process exists, but we can't easily get the pool object
            # This is more for checking if running
            logger.info(f"Worker pool is running (PID: {pid})")
            return None  # Can't return actual instance

        except (OSError, ValueError):
            # Process doesn't exist or invalid PID
            if os.path.exists(pid_file):
                os.remove(pid_file)
            return None
