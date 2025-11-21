# 📊 PHASE 2: PRODUCTION-READY - PHÂN TÍCH CHI TIẾT

**Status:** Planning & Analysis  
**Priority:** HIGH  
**Duration:** 4-6 tuần (35-45 ngày làm việc)  
**Date:** 2025-11-21

---

## 🎯 MỤC TIÊU PHASE 2

Transform từ MVP working tool → Production-ready enterprise solution với:
- ✅ Re-encoding support (profiles thực sự hoạt động)
- ✅ Complete test coverage (85%+)
- ✅ CI/CD automation
- ✅ Integration tests với real video files
- ✅ Performance benchmarks
- ✅ Enhanced documentation

---

## 📋 DANH SÁCH TASKS (13 TASKS)

### ✅ **COMPLETED TASKS (2/13)**

#### Task 2.2: Complete Test Coverage ✅ DONE
- **Status:** Completed
- **Coverage:** Audio_ops và logger tests đã hoàn thành
- **Achievement:** Test coverage từ 75% → 85%+

#### Task 2.3: CI/CD Pipeline ✅ DONE  
- **Status:** Completed
- **Workflows:** test.yml, lint.yml
- **Test Matrix:** Python 3.9, 3.10, 3.11 on macOS
- **Note:** Cần thêm real video file testing

---

### 🚧 **IN-PROGRESS / PLANNED TASKS (11/13)**

---

## 📦 TASK 2.1: RE-ENCODING SUPPORT

**Priority:** 🔴 CRITICAL  
**Status:** 50% Complete (Code có, chưa test đủ)  
**Estimated:** 3 ngày  
**Dependencies:** None

### Current Status

#### ✅ What's Done:
```
src/core/video_ops.py (lines 120-168)
- Profile application logic implemented
- FFmpeg argument building for re-encoding
- Support for CRF, bitrate, resolution, fps
- Hardware acceleration (VideoToolbox) ready
```

#### ❌ What's Missing:
1. **Integration tests với real videos**
   - Chưa test với actual video files
   - Chưa verify output quality
   - Chưa test hardware acceleration

2. **Performance benchmarks**
   - Codec copy vs re-encode speed
   - Quality metrics (VMAF, PSNR)
   - Memory usage tracking

3. **Profile application trong concat**
   - Concat chưa có re-encoding support
   - Cần implement tương tự như cut

4. **Error handling for profiles**
   - Profile not found
   - Hardware codec not available
   - Fallback strategies

### Implementation Plan

#### Subtask 2.1.1: Complete cut with profiles
```bash
# Test commands needed:
video-tool cut -i movie.mp4 -o ./output -d 11 --no-copy --profile clip_720p
video-tool cut -i movie.mp4 -o ./output -d 11 --no-copy --profile movie_1080p

# Expected: Re-encoded clips với profile settings
```

**Files to modify:**
- `src/core/video_ops.py::cut_by_duration()` - Already has code
- Need: Integration tests

**Tasks:**
1. Test với 2 video files có sẵn
2. Verify output codec/resolution/bitrate
3. Measure performance
4. Document results

---

#### Subtask 2.1.2: Implement concat with profiles
```bash
# Target command:
video-tool concat -i part1.mp4 -i part2.mp4 -o final.mp4 --no-copy --profile web_720p
```

**Files to modify:**
- `src/core/video_ops.py::concat_videos()`

**Implementation:**
```python
def concat_videos(
    input_files: List[str],
    output_path: str,
    copy_codec: bool = True,
    validate_compatibility: bool = True,
    profile_name: Optional[str] = None,  # Add this
):
    # ... existing validation ...
    
    if not copy_codec:
        if profile_name:
            profile = get_profile(profile_name)
            # Apply profile settings
            args.extend(["-c:v", profile.video_codec])
            # ... rest of profile application
        else:
            # Default re-encoding settings
            args.extend(["-c:v", "libx264", "-c:a", "aac"])
```

**Estimated:** 1 ngày

---

#### Subtask 2.1.3: Integration tests
```python
# tests/integration/test_reencode.py

def test_cut_with_profile_720p():
    """Test cutting with clip_720p profile."""
    result = cut_by_duration(
        input_path="test_video.mp4",
        output_dir="./output",
        segment_duration=60,
        copy_codec=False,
        profile_name="clip_720p"
    )
    
    # Verify output
    assert len(result) > 0
    for segment in result:
        info = get_video_info(segment)
        assert info['width'] == 1280
        assert info['height'] == 720
        assert info['codec'] == 'hevc'

def test_concat_with_profile():
    """Test concatenation with re-encoding."""
    # Test implementation
    pass
```

**Test cases needed:**
1. Cut with each profile (11 profiles)
2. Concat with re-encoding
3. Hardware acceleration test
4. Fallback when hw not available
5. Profile not found error
6. Invalid profile settings

**Estimated:** 1 ngày

---

#### Subtask 2.1.4: Performance benchmarks
```bash
# Benchmark script
time video-tool cut -i large_video.mp4 -o ./out1 -d 11  # Copy
time video-tool cut -i large_video.mp4 -o ./out2 -d 11 --no-copy --profile clip_720p  # Re-encode

# Measure:
# - Execution time
# - Output file size
# - CPU/Memory usage
# - Quality (VMAF if possible)
```

**Create:** `benchmarks/benchmark_reencode.py`

**Estimated:** 0.5 ngày

---

### Success Criteria

- [ ] Cut với profiles hoạt động với 11 profiles
- [ ] Concat với profiles hoạt động
- [ ] Integration tests pass với real videos
- [ ] Performance benchmarks documented
- [ ] Hardware acceleration verified on macOS
- [ ] Fallback strategy works
- [ ] Documentation updated

**Total Estimated:** 3 ngày

---

## 🗄️ TASK 2.4: DATABASE SCHEMA & JOB TRACKING

**Priority:** 🔴 HIGH  
**Status:** Not Started  
**Estimated:** 3 ngày  
**Dependencies:** None

### Overview
Implement SQLite database để track jobs, enable retry, monitor progress.

### Database Schema

#### Table: jobs
```sql
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_type TEXT NOT NULL,  -- 'cut', 'concat', 'extract_audio', etc.
    status TEXT NOT NULL,     -- 'pending', 'running', 'completed', 'failed'
    input_files TEXT NOT NULL, -- JSON array
    output_files TEXT,         -- JSON array
    config TEXT,               -- JSON (duration, profile, etc.)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    progress REAL DEFAULT 0.0  -- 0-100
);

CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_created_at ON jobs(created_at);
```

#### Table: job_logs
```sql
CREATE TABLE job_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    level TEXT NOT NULL,      -- 'INFO', 'WARNING', 'ERROR'
    message TEXT NOT NULL,
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);

CREATE INDEX idx_job_logs_job_id ON job_logs(job_id);
```

---

### Implementation

#### File: `src/core/database.py`

```python
import sqlite3
import json
from datetime import datetime
from typing import List, Optional, Dict
from dataclasses import dataclass
from enum import Enum

class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Job:
    id: Optional[int]
    job_type: str
    status: JobStatus
    input_files: List[str]
    output_files: Optional[List[str]]
    config: Dict
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    retry_count: int
    progress: float

class Database:
    def __init__(self, db_path: str = "jobs.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""CREATE TABLE IF NOT EXISTS jobs ...""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS job_logs ...""")
        
        conn.commit()
        conn.close()
    
    def create_job(
        self, 
        job_type: str,
        input_files: List[str],
        config: Dict
    ) -> int:
        """Create new job and return job_id."""
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
        
        return job_id
    
    def update_job_status(
        self,
        job_id: int,
        status: JobStatus,
        progress: Optional[float] = None,
        output_files: Optional[List[str]] = None,
        error_message: Optional[str] = None
    ):
        """Update job status and progress."""
        # Implementation
        pass
    
    def get_job(self, job_id: int) -> Optional[Job]:
        """Get job by ID."""
        # Implementation
        pass
    
    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        limit: int = 100
    ) -> List[Job]:
        """List jobs with optional status filter."""
        # Implementation
        pass
    
    def add_job_log(
        self,
        job_id: int,
        level: str,
        message: str
    ):
        """Add log entry for job."""
        # Implementation
        pass
```

---

### CLI Commands

#### File: `src/cli/main.py` - Add jobs subcommand

```python
jobs_app = typer.Typer(help="Job management")
app.add_typer(jobs_app, name="jobs")

@jobs_app.command("list")
def jobs_list(
    status: Optional[str] = typer.Option(None, help="Filter by status"),
    limit: int = typer.Option(20, help="Max number of jobs to show")
):
    """List jobs."""
    db = Database()
    jobs = db.list_jobs(status=status, limit=limit)
    
    # Display in table
    table = Table(title="Jobs")
    table.add_column("ID")
    table.add_column("Type")
    table.add_column("Status")
    table.add_column("Progress")
    table.add_column("Created")
    
    for job in jobs:
        table.add_row(
            str(job.id),
            job.job_type,
            job.status.value,
            f"{job.progress:.0f}%",
            job.created_at.strftime("%Y-%m-%d %H:%M")
        )
    
    console.print(table)

@jobs_app.command("show")
def jobs_show(job_id: int):
    """Show job details."""
    # Implementation
    pass

@jobs_app.command("retry")
def jobs_retry(job_id: int):
    """Retry failed job."""
    # Implementation
    pass

@jobs_app.command("clean")
def jobs_clean(
    older_than: int = typer.Option(7, help="Days")
):
    """Clean old completed jobs."""
    # Implementation
    pass
```

---

### Integration with Operations

```python
# Modify video_ops.py to use database

def cut_by_duration(
    input_path: str,
    output_dir: str,
    segment_duration: int,
    copy_codec: bool = True,
    prefix: str = "part",
    profile_name: Optional[str] = None,
    track_job: bool = False  # New parameter
) -> List[str]:
    
    job_id = None
    if track_job:
        db = Database()
        job_id = db.create_job(
            job_type="cut",
            input_files=[input_path],
            config={
                "output_dir": output_dir,
                "duration": segment_duration,
                "profile": profile_name
            }
        )
        db.update_job_status(job_id, JobStatus.RUNNING)
    
    try:
        # ... existing cut logic ...
        
        # Update progress
        if job_id:
            db.update_job_status(job_id, JobStatus.RUNNING, progress=50)
        
        # ... more operations ...
        
        if job_id:
            db.update_job_status(
                job_id, 
                JobStatus.COMPLETED,
                progress=100,
                output_files=output_files
            )
        
        return output_files
        
    except Exception as e:
        if job_id:
            db.update_job_status(
                job_id,
                JobStatus.FAILED,
                error_message=str(e)
            )
        raise
```

---

### Testing

```python
# tests/test_database.py

def test_create_job():
    db = Database(":memory:")
    job_id = db.create_job(
        job_type="cut",
        input_files=["movie.mp4"],
        config={"duration": 660}
    )
    assert job_id > 0

def test_update_job_status():
    db = Database(":memory:")
    job_id = db.create_job("cut", ["movie.mp4"], {})
    db.update_job_status(job_id, JobStatus.COMPLETED, progress=100)
    
    job = db.get_job(job_id)
    assert job.status == JobStatus.COMPLETED
    assert job.progress == 100

def test_list_jobs_with_filter():
    # Test implementation
    pass
```

**Success Criteria:**
- [ ] Database schema created
- [ ] All CRUD operations work
- [ ] CLI commands functional
- [ ] Integration with video_ops
- [ ] Tests pass (unit + integration)
- [ ] Documentation complete

**Total Estimated:** 3 ngày

---

## ⚙️ TASK 2.5: QUEUE SYSTEM

**Priority:** 🟡 MEDIUM  
**Status:** Not Started  
**Estimated:** 4 ngày  
**Dependencies:** Task 2.4 (Database)

### Overview
Implement background job processing với worker pool.

### Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   CLI/API   │────▶│  Job Queue   │────▶│   Workers   │
│  Submit Job │     │  (Database)  │     │  (Pool)     │
└─────────────┘     └──────────────┘     └─────────────┘
                            │                     │
                            ▼                     ▼
                    ┌──────────────┐     ┌─────────────┐
                    │  Job Status  │     │  FFmpeg     │
                    │   Tracking   │     │  Operations │
                    └──────────────┘     └─────────────┘
```

### Implementation

#### File: `src/core/queue.py`

```python
from multiprocessing import Process, Queue, Manager
from typing import Dict, List, Optional
import time
import signal

class JobQueue:
    """Manage job queue with priority support."""
    
    def __init__(self, db: Database):
        self.db = db
        self.manager = Manager()
        self.queue = self.manager.Queue()
    
    def add_job(self, job_id: int, priority: int = 0):
        """Add job to queue."""
        self.queue.put((priority, job_id))
    
    def get_next_job(self) -> Optional[int]:
        """Get next job from queue (blocks)."""
        if not self.queue.empty():
            priority, job_id = self.queue.get()
            return job_id
        return None

class Worker(Process):
    """Worker process that executes jobs."""
    
    def __init__(
        self, 
        worker_id: int,
        queue: JobQueue,
        db: Database
    ):
        super().__init__()
        self.worker_id = worker_id
        self.queue = queue
        self.db = db
        self.running = True
    
    def run(self):
        """Main worker loop."""
        logger.info(f"Worker {self.worker_id} started")
        
        while self.running:
            job_id = self.queue.get_next_job()
            if job_id:
                self.execute_job(job_id)
            else:
                time.sleep(1)  # Wait for jobs
    
    def execute_job(self, job_id: int):
        """Execute a job."""
        job = self.db.get_job(job_id)
        
        try:
            self.db.update_job_status(job_id, JobStatus.RUNNING)
            
            if job.job_type == "cut":
                self._execute_cut(job)
            elif job.job_type == "concat":
                self._execute_concat(job)
            # ... other job types
            
            self.db.update_job_status(
                job_id,
                JobStatus.COMPLETED,
                progress=100
            )
            
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            self.db.update_job_status(
                job_id,
                JobStatus.FAILED,
                error_message=str(e)
            )
    
    def _execute_cut(self, job: Job):
        """Execute cut job."""
        config = job.config
        cut_by_duration(
            input_path=job.input_files[0],
            output_dir=config['output_dir'],
            segment_duration=config['duration'],
            # ... other params
        )
    
    def stop(self):
        """Stop worker gracefully."""
        self.running = False

class WorkerPool:
    """Manage multiple workers."""
    
    def __init__(
        self,
        num_workers: int = 2,
        db: Database = None
    ):
        self.num_workers = num_workers
        self.db = db or Database()
        self.queue = JobQueue(self.db)
        self.workers: List[Worker] = []
        self.running = False
    
    def start(self):
        """Start all workers."""
        logger.info(f"Starting {self.num_workers} workers")
        self.running = True
        
        for i in range(self.num_workers):
            worker = Worker(i, self.queue, self.db)
            worker.start()
            self.workers.append(worker)
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def stop(self):
        """Stop all workers gracefully."""
        logger.info("Stopping workers...")
        self.running = False
        
        for worker in self.workers:
            worker.stop()
            worker.join(timeout=10)
        
        logger.info("All workers stopped")
    
    def _signal_handler(self, sig, frame):
        """Handle shutdown signals."""
        self.stop()
    
    def status(self) -> Dict:
        """Get worker pool status."""
        return {
            "num_workers": self.num_workers,
            "running": self.running,
            "workers": [
                {
                    "id": w.worker_id,
                    "alive": w.is_alive()
                }
                for w in self.workers
            ]
        }
```

---

### CLI Commands

```python
@app.command()
def worker(
    action: str = typer.Argument(..., help="start|stop|status"),
    workers: int = typer.Option(2, help="Number of workers")
):
    """Manage background workers."""
    
    if action == "start":
        console.print(f"Starting {workers} workers...")
        pool = WorkerPool(num_workers=workers)
        pool.start()
        
        # Keep running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pool.stop()
    
    elif action == "stop":
        # Implementation: Send signal to worker process
        pass
    
    elif action == "status":
        # Implementation: Check worker status
        pass
```

---

### Configuration

**File:** `configs/queue.yaml`

```yaml
queue:
  max_workers: 2
  check_interval: 5  # seconds
  retry_failed_jobs: true
  max_retries: 3
  retry_delay: 300  # 5 minutes

worker:
  timeout: 3600  # 1 hour
  log_level: INFO
  enable_progress_callback: true
```

---

### Usage Example

```bash
# Terminal 1: Start workers
video-tool worker start --workers 2

# Terminal 2: Submit jobs
video-tool cut -i movie.mp4 -o ./output -d 11 --async
# Returns: Job ID: 123

# Check status
video-tool jobs show 123

# List all jobs
video-tool jobs list

# Stop workers
video-tool worker stop
```

**Success Criteria:**
- [ ] Queue system working
- [ ] Workers can execute jobs
- [ ] Graceful shutdown
- [ ] Health monitoring
- [ ] Integration with database
- [ ] CLI commands work
- [ ] Configuration system
- [ ] Tests pass

**Total Estimated:** 4 ngày

---

## 🔧 REMAINING TASKS SUMMARY

### Task 2.6: Pipeline - Movie to Clips
**Estimated:** 4 ngày  
**Status:** Planning  
High-level workflow combining cut + re-encode + metadata

### Task 2.7: Error Handling Enhancement  
**Estimated:** 2 ngày  
**Status:** Planning  
Retry mechanism, fallback strategies, better error messages

### Task 2.8: File Validation & Safety
**Estimated:** 2 ngày  
**Status:** Planning  
Disk space check, corruption detection, atomic operations

### Task 2.9: FastAPI Backend
**Estimated:** 5 ngày  
**Status:** Planning  
REST API for remote job submission

### Task 2.10: Web UI - Frontend
**Estimated:** 7 ngày  
**Status:** Planning  
Basic HTML/JS interface for job management

### Task 2.11: Integration Tests
**Estimated:** 3 ngày  
**Status:** Planning  
Full workflow tests with real videos

### Task 2.12: CI/CD Enhancement
**Estimated:** 2 ngày  
**Status:** Partially Done  
Add real video testing, release automation

### Task 2.13: Documentation - Phase 2
**Estimated:** 3 ngày  
**Status:** Planning  
User guide, API docs, deployment guide

---

## 📊 PHASE 2 TIMELINE

### Critical Path (4 tuần minimum)

**Week 1:**
- Task 2.1: Re-encoding Support (3 ngày) ← START HERE
- Task 2.4: Database & Job Tracking (3 ngày)

**Week 2:**
- Task 2.5: Queue System (4 ngày)
- Task 2.7: Error Handling (2 ngày)

**Week 3:**
- Task 2.6: Movie Pipeline (4 ngày)
- Task 2.11: Integration Tests (3 ngày)

**Week 4:**
- Task 2.8: File Safety (2 ngày)
- Task 2.12: CI/CD Enhancement (2 ngày)
- Task 2.13: Documentation (3 ngày)

**Optional (Tuần 5-6):**
- Task 2.9: FastAPI Backend (5 ngày)
- Task 2.10: Web UI (7 ngày)

---

## 🎯 RECOMMENDED PRIORITY ORDER

### Must Have (Core Phase 2):
1. ✅ **Task 2.1** - Re-encoding (CRITICAL)
2. ✅ **Task 2.4** - Database (HIGH)
3. ✅ **Task 2.5** - Queue System (HIGH)
4. ✅ **Task 2.7** - Error Handling (HIGH)
5. ✅ **Task 2.11** - Integration Tests (HIGH)

### Should Have:
6. **Task 2.6** - Movie Pipeline
7. **Task 2.8** - File Safety
8. **Task 2.12** - CI/CD Enhancement
9. **Task 2.13** - Documentation

### Nice to Have (Phase 2.5):
10. **Task 2.9** - FastAPI Backend
11. **Task 2.10** - Web UI

---

## 🚀 NEXT IMMEDIATE STEPS

### To Start Phase 2 Development:

1. **Create Phase 2 branch:**
```bash
git checkout -b phase-2-dev
```

2. **Start with Task 2.1 (Re-encoding):**
```bash
# Create test videos
ffmpeg -f lavfi -i testsrc=duration=300:size=1920x1080:rate=30 \
       -pix_fmt yuv420p test_1080p.mp4

# Test cut with profiles
video-tool cut -i test_1080p.mp4 -o ./test_output \
  -d 2 --no-copy --profile clip_720p --verbose

# Verify output
video-tool info -i ./test_output/part_001.mp4
```

3. **Create integration test structure:**
```bash
mkdir -p tests/integration
mkdir -p tests/fixtures
mkdir -p benchmarks
```

4. **Update progress tracking:**
- Create PHASE_2_PROGRESS.md
- Track daily progress
- Document blockers

---

## 📈 SUCCESS METRICS

### Phase 2 Complete When:
- [ ] Re-encoding works with all 11 profiles
- [ ] Database tracks all operations
- [ ] Queue system processes jobs in background
- [ ] Integration tests pass with real videos
- [ ] Test coverage ≥ 85%
- [ ] Performance benchmarks documented
- [ ] All documentation updated
- [ ] CI/CD runs successfully

### Stretch Goals:
- [ ] API backend working
- [ ] Basic web UI functional
- [ ] Movie pipeline automated

---

**Document Created:** 2025-11-21  
**Status:** Ready for Phase 2 Development  
**Next Step:** Begin Task 2.1 - Re-encoding Support
