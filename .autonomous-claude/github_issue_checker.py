#!/usr/bin/env python3
# github_issue_checker.py
#
# Processes GitHub issues for autonomous coding workflow
# Reads issue data from stdin and enqueues them for processing

import os
import sys
import json
import time
from datetime import datetime, timedelta
import logging
import importlib.util

# Setup logging
log_dir = os.path.join(os.getcwd(), '.autonomous-claude', 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'github_checker.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('github-issue-checker')

# Load tasks module dynamically (since it might be in a different location)
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

def is_already_processed(issue_number):
    """Check if an issue has already been processed or is being processed"""
    project_path = os.environ.get('PROJECT_PATH', os.getcwd())
    tasks_dir = os.path.join(project_path, '.autonomous-claude', 'tasks')
    
    # Get project ID for isolation
    project_id_file = os.path.join(project_path, '.autonomous-claude', 'project_id')
    project_id = ''
    if os.path.exists(project_id_file):
        with open(project_id_file, 'r') as f:
            project_id = f.read().strip()
    else:
        # Create project ID if it doesn't exist
        import hashlib
        project_id = hashlib.sha256(project_path.encode()).hexdigest()[:16]
        os.makedirs(os.path.dirname(project_id_file), exist_ok=True)
        with open(project_id_file, 'w') as f:
            f.write(project_id)
        logger.info(f"Created new project ID: {project_id}")
    
    # Plan file would indicate issue has been analyzed
    plan_file = os.path.join(tasks_dir, f"{project_id}-issue-{issue_number}-plan.md")
    if os.path.exists(plan_file):
        logger.info(f"Issue #{issue_number} already has a plan file in project {project_id}")
        return True
    
    # Also check the old format for backward compatibility
    old_plan_file = os.path.join(tasks_dir, f"{issue_number}-plan.md")
    if os.path.exists(old_plan_file):
        logger.info(f"Issue #{issue_number} has an old-format plan file")
        return True
    
    # Lock file indicates issue is being processed
    lock_file = os.path.join(tasks_dir, f"{project_id}-issue-{issue_number}.lock")
    if os.path.exists(lock_file):
        # Check if lock is stale (older than 1 hour)
        lock_time = os.path.getmtime(lock_file)
        if time.time() - lock_time < 3600:  # 1 hour in seconds
            logger.info(f"Issue #{issue_number} is currently being processed in project {project_id}")
            return True
        else:
            logger.warning(f"Found stale lock for issue #{issue_number} in project {project_id}, removing")
            os.remove(lock_file)
    
    # Also check the old lock file format for backward compatibility
    old_lock_file = os.path.join(tasks_dir, f"{issue_number}.lock")
    if os.path.exists(old_lock_file):
        lock_time = os.path.getmtime(old_lock_file)
        if time.time() - lock_time < 3600:
            logger.info(f"Issue #{issue_number} is currently being processed (old format lock)")
            return True
        else:
            logger.warning(f"Found stale old-format lock for issue #{issue_number}, removing")
            os.remove(old_lock_file)
    
    return False

def create_lock_file(issue_number):
    """Create a lock file to indicate an issue is being processed"""
    project_path = os.environ.get('PROJECT_PATH', os.getcwd())
    tasks_dir = os.path.join(project_path, '.autonomous-claude', 'tasks')
    os.makedirs(tasks_dir, exist_ok=True)
    
    # Get project ID for isolation
    project_id_file = os.path.join(project_path, '.autonomous-claude', 'project_id')
    project_id = ''
    if os.path.exists(project_id_file):
        with open(project_id_file, 'r') as f:
            project_id = f.read().strip()
    else:
        # Create project ID if it doesn't exist
        import hashlib
        project_id = hashlib.sha256(project_path.encode()).hexdigest()[:16]
        os.makedirs(os.path.dirname(project_id_file), exist_ok=True)
        with open(project_id_file, 'w') as f:
            f.write(project_id)
        logger.info(f"Created new project ID: {project_id}")
    
    # Use project ID in lock file name to ensure isolation between projects
    lock_file = os.path.join(tasks_dir, f"{project_id}-issue-{issue_number}.lock")
    with open(lock_file, 'w') as f:
        timestamp = datetime.now().isoformat()
        f.write(f"Processing started: {timestamp}\n")
        f.write(f"Project ID: {project_id}\n")
        f.write(f"Project Path: {project_path}\n")
    
    logger.info(f"Created lock file for issue #{issue_number} in project {project_id}")
    return True

def process_issues(issues_json):
    """Process issues from JSON data"""
    try:
        issues = json.loads(issues_json)
        logger.info(f"Processing {len(issues)} issues")
        
        # Import tasks module for enqueuing
        tasks = import_tasks_module()
        
        for issue in issues:
            issue_number = issue['number']
            issue_title = issue['title']
            issue_url = issue['url']
            
            logger.info(f"Found issue #{issue_number}: {issue_title}")
            
            # Skip if already processed or being processed
            if is_already_processed(issue_number):
                continue
            
            # Create lock file
            create_lock_file(issue_number)
            
            # Enqueue the issue for processing
            try:
                job_id = tasks.enqueue_process_github_issue(issue_number)
                logger.info(f"Enqueued issue #{issue_number} with job ID: {job_id}")
            except Exception as e:
                logger.error(f"Failed to enqueue issue #{issue_number}: {str(e)}")
                
                # Remove lock file on failure
                project_path = os.environ.get('PROJECT_PATH', os.getcwd())
                
                # Get project ID for isolation
                project_id_file = os.path.join(project_path, '.autonomous-claude', 'project_id')
                project_id = ''
                if os.path.exists(project_id_file):
                    with open(project_id_file, 'r') as f:
                        project_id = f.read().strip()
                else:
                    # Fallback if no project ID exists
                    import hashlib
                    project_id = hashlib.sha256(project_path.encode()).hexdigest()[:16]
                
                # Look for both new and old format lock files
                lock_file = os.path.join(project_path, '.autonomous-claude', 'tasks', f"{project_id}-issue-{issue_number}.lock")
                old_lock_file = os.path.join(project_path, '.autonomous-claude', 'tasks', f"{issue_number}.lock")
                
                if os.path.exists(lock_file):
                    logger.info(f"Removing lock file for failed issue #{issue_number} in project {project_id}")
                    os.remove(lock_file)
                
                if os.path.exists(old_lock_file):
                    logger.info(f"Removing old-format lock file for failed issue #{issue_number}")
                    os.remove(old_lock_file)
        
        return True
    except json.JSONDecodeError:
        logger.error("Failed to parse issues JSON")
        return False
    except Exception as e:
        logger.error(f"Error processing issues: {str(e)}")
        return False

if __name__ == "__main__":
    # Read issues JSON from stdin
    issues_json = sys.stdin.read()
    
    if not issues_json:
        logger.warning("No input received from stdin")
        sys.exit(1)
    
    if process_issues(issues_json):
        sys.exit(0)
    else:
        sys.exit(1)