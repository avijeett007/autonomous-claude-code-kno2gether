import os
import sys
import time
from redis import Redis
from rq import Queue

# Add parent directory to path so we can import worker
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from worker import process_github_issue, update_project_documentation

# Redis connection
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
queue_name = os.environ.get('REDIS_QUEUE', 'autonomous-coding')
redis_conn = Redis.from_url(redis_url)
queue = Queue(queue_name, connection=redis_conn)

def enqueue_process_github_issue(issue_number):
    """Add a GitHub issue processing task to the queue"""
    job = queue.enqueue(
        process_github_issue,
        issue_number,
        job_timeout='2h',  # Long timeout for complex issues
        result_ttl=86400,  # Keep results for 24 hours
        ttl=86400          # Job can wait in queue for up to 24 hours
    )
    return job.id

def enqueue_update_documentation():
    """Add a documentation update task to the queue"""
    job = queue.enqueue(
        update_project_documentation,
        job_timeout='1h',
        result_ttl=86400,
        ttl=86400
    )
    return job.id
