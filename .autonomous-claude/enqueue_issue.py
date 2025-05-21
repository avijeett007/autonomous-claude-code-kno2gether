#!/usr/bin/env python3
# enqueue_issue.py
#
# Manually enqueue a GitHub issue for processing

import os
import sys
import logging
import importlib.util

# Setup logging
log_dir = os.path.join(os.getcwd(), '.autonomous-claude', 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'manual_enqueue.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('manual-enqueue')

# Load tasks module dynamically
def import_tasks_module():
    project_path = os.environ.get('PROJECT_PATH', os.getcwd())
    tasks_path = os.path.join(project_path, '.autonomous-claude', 'tasks.py')
    
    if not os.path.exists(tasks_path):
        logger.error(f"Tasks module not found at {tasks_path}")
        sys.exit(1)
    
    spec = importlib.util.spec_from_file_location("tasks", tasks_path)
    tasks_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tasks_module)
    return tasks_module

def enqueue_issue(issue_number):
    """Manually enqueue a specific GitHub issue"""
    try:
        # Import tasks module
        tasks = import_tasks_module()
        
        # Ensure tasks directory exists
        project_path = os.environ.get('PROJECT_PATH', os.getcwd())
        tasks_dir = os.path.join(project_path, '.autonomous-claude', 'tasks')
        os.makedirs(tasks_dir, exist_ok=True)
        
        # Clean up any existing plan or lock files for this issue
        plan_file = os.path.join(tasks_dir, f"{issue_number}-plan.md")
        lock_file = os.path.join(tasks_dir, f"{issue_number}.lock")
        completed_file = os.path.join(tasks_dir, f"{issue_number}-completed.txt")
        
        if os.path.exists(plan_file):
            logger.info(f"Removing existing plan file for issue #{issue_number}")
            os.remove(plan_file)
        
        if os.path.exists(lock_file):
            logger.info(f"Removing existing lock file for issue #{issue_number}")
            os.remove(lock_file)
            
        if os.path.exists(completed_file):
            logger.info(f"Removing existing completion file for issue #{issue_number}")
            os.remove(completed_file)
        
        # Enqueue the issue
        job_id = tasks.enqueue_process_github_issue(issue_number)
        logger.info(f"Successfully enqueued issue #{issue_number} with job ID: {job_id}")
        print(f"Enqueued issue #{issue_number} with job ID: {job_id}")
        return True
    except Exception as e:
        logger.error(f"Error enqueueing issue #{issue_number}: {str(e)}")
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python enqueue_issue.py <issue_number>")
        sys.exit(1)
    
    try:
        issue_number = sys.argv[1]
        if enqueue_issue(issue_number):
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        print(f"Unexpected error: {str(e)}")
        sys.exit(1)
