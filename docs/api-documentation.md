# API Documentation

This document provides technical documentation for the Redis worker and task management components of the Autonomous Claude system.

## Redis Queue System

Autonomous Claude uses Redis and RQ (Redis Queue) for asynchronous task management.

### Redis Configuration

The system connects to Redis using the URL specified in the configuration file:

```python
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
queue_name = os.environ.get('REDIS_QUEUE', 'autonomous-coding')
redis_conn = Redis.from_url(redis_url)
queue = Queue(queue_name, connection=redis_conn)
```

The default configuration uses:
- Redis running on localhost, port 6379
- Queue name: "autonomous-coding"

### Worker Module API

#### Worker Class

The worker module doesn't explicitly define a custom worker class, but it uses RQ's `Worker` class to process tasks:

```python
worker = Worker([queue], connection=redis_conn)
worker.work()
```

This worker listens for tasks in the specified queue and executes them as they arrive.

#### run_claude_code_headless Function

```python
def run_claude_code_headless(prompt, allowed_tools=None):
    """Run Claude Code in headless mode with the given prompt"""
```

**Parameters**:
- `prompt` (str): The prompt to send to Claude Code, including custom commands
- `allowed_tools` (str, optional): Comma-separated list of tools Claude is allowed to use

**Returns**:
- `dict`: A dictionary containing:
  - `success` (bool): Whether the execution was successful
  - `stdout` (str): Standard output from Claude Code
  - `stderr` (str): Standard error output from Claude Code
  - `error` (str, optional): Error message if execution failed

**Example Usage**:
```python
result = run_claude_code_headless(
    "/project:analyze-github-issue 123",
    "Bash(gh:*) Edit Run"
)

if result['success']:
    print("Analysis successful!")
    print(result['stdout'])
else:
    print(f"Analysis failed: {result.get('error')}")
```

#### process_github_issue Function

```python
def process_github_issue(issue_number):
    """Process a GitHub issue through the autonomous workflow"""
```

**Parameters**:
- `issue_number` (int): The GitHub issue number to process

**Returns**:
- `dict`: A dictionary containing:
  - `success` (bool): Whether the processing was successful
  - `issue_number` (int): The processed issue number
  - `completed_at` (float): Timestamp of completion
  - `stage` (str, optional): Stage at which processing failed ("analyze" or "implement")
  - `error` (str, optional): Error message if processing failed

**Processing Steps**:
1. Analyze the issue using `/project:analyze-github-issue`
2. Implement the solution using `/project:implement-github-issue`

**Example Usage**:
```python
result = process_github_issue(123)
if result['success']:
    print(f"Issue #{result['issue_number']} processed successfully")
else:
    print(f"Processing failed at {result['stage']} stage: {result['error']}")
```

#### update_project_documentation Function

```python
def update_project_documentation():
    """Update project documentation using Claude Code"""
```

**Parameters**: None

**Returns**:
- `dict`: A dictionary containing:
  - `success` (bool): Whether the documentation update was successful
  - `completed_at` (float): Timestamp of completion
  - `stage` (str, optional): "documentation" if failed
  - `error` (str, optional): Error message if failed

**Example Usage**:
```python
result = update_project_documentation()
if result['success']:
    print("Documentation updated successfully")
else:
    print(f"Documentation update failed: {result['error']}")
```

### Task Management API

The task management module (`tasks.py`) provides functions to add tasks to the Redis queue.

#### enqueue_process_github_issue Function

```python
def enqueue_process_github_issue(issue_number):
    """Add a GitHub issue processing task to the queue"""
```

**Parameters**:
- `issue_number` (int): The GitHub issue number to process

**Returns**:
- `str`: The job ID of the enqueued task

**Example Usage**:
```python
job_id = enqueue_process_github_issue(123)
print(f"Enqueued issue #123 with job ID: {job_id}")
```

#### enqueue_update_documentation Function

```python
def enqueue_update_documentation():
    """Add a documentation update task to the queue"""
```

**Parameters**: None

**Returns**:
- `str`: The job ID of the enqueued task

**Example Usage**:
```python
job_id = enqueue_update_documentation()
print(f"Enqueued documentation update with job ID: {job_id}")
```

## Job Configuration

Tasks are configured with the following parameters:

```python
job = queue.enqueue(
    process_github_issue,
    issue_number,
    job_timeout='2h',  # Long timeout for complex issues
    result_ttl=86400,  # Keep results for 24 hours
    ttl=86400          # Job can wait in queue for up to 24 hours
)
```

- `job_timeout`: Maximum time the job can run before being terminated (2 hours for issues, 1 hour for documentation)
- `result_ttl`: Time to keep the job result in Redis (24 hours)
- `ttl`: Time the job can wait in the queue before being discarded (24 hours)

## GitHub Issue Checker API

The GitHub issue checker module processes issues from GitHub and adds them to the queue.

#### main Function

```python
def main():
    """Process GitHub issues from stdin"""
```

**Input**:
- JSON data via stdin containing GitHub issues

**Processing Steps**:
1. Parse JSON from stdin
2. For each issue:
   - Check if a plan already exists (`.autonomous-claude/tasks/{issue_number}-plan.md`)
   - Check if a lock file exists (`.autonomous-claude/tasks/{issue_number}.lock`)
   - If the lock is stale (older than 1 hour), re-enqueue the issue
   - Create a lock file to prevent re-enqueueing
   - Enqueue the issue for processing
   - Add the job ID to the lock file

**Example Usage**:
```bash
gh issue list --repo "username/repo" --label "autonomous-coding" --state open --json number,title,url | python github_issue_checker.py
```

## Extending the API

### Adding Custom Task Types

To add a new task type:

1. Define the task function in `worker.py`:

```python
def my_custom_task(param1, param2):
    """Custom task implementation"""
    logger.info(f"Running custom task with params: {param1}, {param2}")
    
    # Task implementation
    # ...
    
    return {
        'success': True,
        'task_type': 'custom',
        'completed_at': time.time(),
        'result': 'Task result'
    }
```

2. Add a function to enqueue the task in `tasks.py`:

```python
def enqueue_my_custom_task(param1, param2):
    """Add a custom task to the queue"""
    job = queue.enqueue(
        my_custom_task,
        param1,
        param2,
        job_timeout='30m',
        result_ttl=86400,
        ttl=86400
    )
    return job.id
```

### Working with Job Results

To retrieve and work with job results:

```python
from redis import Redis
from rq import Queue
from rq.job import Job

# Connect to Redis
redis_conn = Redis.from_url('redis://localhost:6379')

# Get job by ID
job = Job.fetch(job_id, connection=redis_conn)

# Check job status
status = job.get_status()  # 'queued', 'started', 'finished', 'failed'

# Get job result (if finished)
if job.is_finished:
    result = job.result
    print(f"Job result: {result}")
elif job.is_failed:
    print(f"Job failed: {job.exc_info}")
else:
    print(f"Job is {status}")
```

### Error Handling

The worker module includes error handling for various failure scenarios:

```python
try:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True
    )
    # Success handling
except subprocess.CalledProcessError as e:
    # Error handling
    return {
        'success': False,
        'error': str(e),
        'stdout': e.stdout,
        'stderr': e.stderr
    }
```

When a job fails, RQ moves it to the failed job registry. You can access failed jobs through the RQ Dashboard or programmatically:

```python
failed_registry = queue.failed_job_registry
failed_job_ids = failed_registry.get_job_ids()

for job_id in failed_job_ids:
    job = Job.fetch(job_id, connection=redis_conn)
    print(f"Failed job {job_id}: {job.exc_info}")
    
    # Optionally requeue the job
    # failed_registry.requeue(job_id)
```

## Logging System

The worker module uses Python's logging module with two handlers:

```python
# Setup logging
log_dir = os.path.join(os.getcwd(), '.autonomous-claude', 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'worker.log')

logger = logging.getLogger('autonomous-claude-worker')
logger.setLevel(logging.INFO)

# File handler with rotation
handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
```

Log messages are written to:
- `.autonomous-claude/logs/worker.log` (rotated when it reaches 10MB)
- Standard output

## Environment Variables

The worker and task modules use the following environment variables:

- `REDIS_URL`: Redis connection URL (default: `redis://localhost:6379`)
- `REDIS_QUEUE`: Name of the Redis queue (default: `autonomous-coding`)
- `CLAUDE_CODE_PATH`: Path to the Claude Code executable (default: `claude`)
- `PROJECT_PATH`: Path to the project directory (default: current working directory)

These can be set in the environment or in the configuration file.