import os
import sys
import json
import time
import subprocess
from redis import Redis
from rq import Worker, Queue
import logging
from logging.handlers import RotatingFileHandler

# Setup logging
log_dir = os.path.join(os.getcwd(), '.autonomous-claude', 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'worker.log')

logger = logging.getLogger('autonomous-claude-worker')
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Also log to stdout
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Redis connection
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
queue_name = os.environ.get('REDIS_QUEUE', 'autonomous-coding')
redis_conn = Redis.from_url(redis_url)
queue = Queue(queue_name, connection=redis_conn)

# Task processing functions
def run_claude_code_headless(prompt, allowed_tools=None):
    """Run Claude Code in headless mode with the given prompt"""
    claude_path = os.environ.get('CLAUDE_CODE_PATH', 'claude')
    command = [claude_path, '-p', prompt]
    
    if allowed_tools:
        command.extend(['--allowedTools', allowed_tools])
    
    logger.info(f"Running Claude Code with command: {' '.join(command)}")
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(f"Claude Code execution successful")
        return {
            'success': True,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"Claude Code execution failed: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'stdout': e.stdout,
            'stderr': e.stderr
        }

def process_github_issue(issue_number):
    """Process a GitHub issue through the autonomous workflow"""
    logger.info(f"Processing GitHub issue #{issue_number}")
    
    # Step 1: Analyze the issue and create a plan
    project_path = os.environ.get('PROJECT_PATH', os.getcwd())
    analyze_prompt = f"/project:analyze-github-issue {issue_number}"
    
    result = run_claude_code_headless(
        analyze_prompt,
        "Bash(gh:*) Edit Run"
    )
    
    if not result['success']:
        logger.error(f"Failed to analyze issue #{issue_number}")
        return {
            'success': False,
            'stage': 'analyze',
            'error': result['stderr']
        }
    
    logger.info(f"Successfully analyzed issue #{issue_number}")
    
    # Step 2: Implement the solution
    implement_prompt = f"/project:implement-github-issue {issue_number}"
    
    result = run_claude_code_headless(
        implement_prompt,
        "Bash(gh:*,git:*) Edit Run Test"
    )
    
    if not result['success']:
        logger.error(f"Failed to implement solution for issue #{issue_number}")
        return {
            'success': False,
            'stage': 'implement',
            'error': result['stderr']
        }
    
    logger.info(f"Successfully implemented solution for issue #{issue_number}")
    
    return {
        'success': True,
        'issue_number': issue_number,
        'completed_at': time.time()
    }

def update_project_documentation():
    """Update project documentation using Claude Code"""
    logger.info("Updating project documentation")
    
    result = run_claude_code_headless(
        "/project:document-project",
        "Bash Edit Run"
    )
    
    if not result['success']:
        logger.error("Failed to update project documentation")
        return {
            'success': False,
            'stage': 'documentation',
            'error': result['stderr']
        }
    
    logger.info("Successfully updated project documentation")
    
    return {
        'success': True,
        'completed_at': time.time()
    }

# Worker loop
if __name__ == '__main__':
    logger.info(f"Starting worker for queue: {queue_name}")
    
    # Create and start the worker directly with the queue that already has the connection
    worker = Worker([queue], connection=redis_conn)
    worker.work()
