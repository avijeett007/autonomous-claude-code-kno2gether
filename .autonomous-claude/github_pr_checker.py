#!/usr/bin/env python3
import json
import sys
import os
import time
import traceback
import logging
from tasks import enqueue_review_pull_request

# Setup logging
log_dir = os.path.join(os.getcwd(), '.autonomous-claude', 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'github_pr_checker.log')

logger = logging.getLogger('github-pr-checker')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(log_file)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Also log to stdout
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

def main():
    try:
        # Get project path from environment
        project_path = os.environ.get('PROJECT_PATH', os.getcwd())
        logger.debug(f"Project path: {project_path}")
        
        # Ensure tasks directory exists
        tasks_dir = os.path.join(project_path, '.autonomous-claude', 'tasks')
        logger.debug(f"Tasks directory: {tasks_dir}")
        os.makedirs(tasks_dir, exist_ok=True)
        
        # Read JSON from stdin
        logger.debug("Reading PRs from stdin")
        prs = json.load(sys.stdin)
        logger.debug(f"Found {len(prs)} PRs")
        
        for pr in prs:
            # Check if this PR is already being processed
            pr_number = pr['number']
            logger.debug(f"Processing PR #{pr_number}")
            
            # Skip PRs created by others if configured that way
            if pr['author']['login'] != os.environ.get('GITHUB_USERNAME', '') and \
               os.environ.get('REVIEW_ONLY_OWN_PRS', 'false').lower() == 'true':
                logger.info(f"PR #{pr_number} was not created by the system, skipping")
                continue
                
            review_lock_file = os.path.join(tasks_dir, f"pr-{pr_number}-review.lock")
            
            # Skip if lock file exists (PR already being reviewed)
            if os.path.exists(review_lock_file):
                # Check if lock is stale (older than 1 hour)
                lock_age = time.time() - os.path.getmtime(review_lock_file)
                if lock_age < 3600:  # 1 hour in seconds
                    logger.info(f"PR #{pr_number} is already being reviewed (lock created {int(lock_age/60)} minutes ago)")
                    continue
                else:
                    logger.info(f"Found stale lock for PR #{pr_number}, re-enqueueing")
            
            # Create a lock file to prevent re-enqueueing
            try:
                with open(review_lock_file, 'w') as f:
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"Enqueued at {timestamp}\n")
            except Exception as e:
                logger.error(f"Error creating lock file: {str(e)}")
                traceback.print_exc()
            
            logger.info(f"Processing PR #{pr_number}: {pr['title']}")
            job_id = enqueue_review_pull_request(pr_number)
            
            # Add job ID to lock file
            try:
                with open(review_lock_file, 'a') as f:
                    f.write(f"Job ID: {job_id}\n")
            except Exception as e:
                logger.error(f"Error updating lock file: {str(e)}")
                traceback.print_exc()
            
            print(f"Enqueued PR review job with ID: {job_id}")
            
    except Exception as e:
        logger.error(f"Exception in PR processing: {str(e)}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()