#!/usr/bin/env python3
# github_pr_checker.py
#
# Processes GitHub pull requests for autonomous review workflow
# Reads PR data from stdin and enqueues them for processing

import os
import sys
import json
import time
from datetime import datetime
import logging
import traceback
import importlib.util

# Try to import GitHub API helper
try:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from github_api_helper import run_gh_command, get_pull_request, extract_issue_number_from_pr
    use_api_helper = True
except ImportError:
    use_api_helper = False

# Setup logging
log_dir = os.path.join(os.getcwd(), '.autonomous-claude', 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'github_pr_checker.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('github-pr-checker')

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

def is_already_reviewed(pr_number):
    """Check if a PR has already been reviewed or is being processed"""
    project_path = os.environ.get('PROJECT_PATH', os.getcwd())
    reviews_dir = os.path.join(project_path, '.autonomous-claude', 'reviews')
    os.makedirs(reviews_dir, exist_ok=True)
    
    # Review file would indicate PR has been reviewed
    review_file = os.path.join(reviews_dir, f"pr-{pr_number}-review.md")
    if os.path.exists(review_file):
        logger.info(f"PR #{pr_number} already has a review file")
        return True
    
    # Lock file indicates PR is being processed
    lock_file = os.path.join(reviews_dir, f"pr-{pr_number}.lock")
    if os.path.exists(lock_file):
        # Check if lock is stale (older than 1 hour)
        lock_time = os.path.getmtime(lock_file)
        if time.time() - lock_time < 3600:  # 1 hour in seconds
            logger.info(f"PR #{pr_number} is currently being processed")
            return True
        else:
            logger.warning(f"Found stale lock for PR #{pr_number}, removing")
            os.remove(lock_file)
    
    return False

def create_lock_file(pr_number):
    """Create a lock file to indicate a PR is being processed"""
    project_path = os.environ.get('PROJECT_PATH', os.getcwd())
    reviews_dir = os.path.join(project_path, '.autonomous-claude', 'reviews')
    os.makedirs(reviews_dir, exist_ok=True)
    
    lock_file = os.path.join(reviews_dir, f"pr-{pr_number}.lock")
    with open(lock_file, 'w') as f:
        timestamp = datetime.now().isoformat()
        f.write(f"Review started: {timestamp}\n")
    
    logger.info(f"Created lock file for PR #{pr_number}")
    return True

def should_review_pr(pr):
    """Determine if a PR should be reviewed based on configuration"""
    # Check if we should only review PRs from our own system
    review_only_own = os.environ.get('REVIEW_ONLY_OWN_PRS', 'true').lower() == 'true'
    github_username = os.environ.get('GITHUB_USERNAME', '')
    
    if review_only_own and github_username:
        # Check if PR author matches our GitHub username
        pr_author = pr.get('author', {}).get('login', '')
        if pr_author != github_username:
            logger.info(f"Skipping PR #{pr['number']} as it's not authored by {github_username}")
            return False
    
    # Check for PR-issue relationship if we're using the API helper
    if use_api_helper:
        try:
            pr_number = pr['number']
            
            # Try to extract issue number from PR description
            pr_detail = get_pull_request(pr_number)
            if pr_detail:
                issue_number = extract_issue_number_from_pr(pr_detail)
                if issue_number:
                    # Import PR relationship module if needed
                    try:
                        project_path = os.environ.get('PROJECT_PATH', os.getcwd())
                        module_path = os.path.join(project_path, '.autonomous-claude', 'pr_issue_relationship.py')
                        
                        if os.path.exists(module_path):
                            sys.path.append(os.path.dirname(os.path.abspath(module_path)))
                            from pr_issue_relationship import get_instance
                            relationship_manager = get_instance()
                            
                            # Record the relationship
                            relationship_manager.associate_pr_with_issue(issue_number, pr_number)
                            logger.info(f"Associated PR #{pr_number} with issue #{issue_number}")
                    except ImportError as e:
                        logger.warning(f"Failed to import PR relationship module: {str(e)}")
                    except Exception as e:
                        logger.warning(f"Failed to associate PR with issue: {str(e)}")
        except Exception as e:
            logger.warning(f"Error extracting issue from PR: {str(e)}")
    
    return True

def process_pull_requests(prs_json):
    """Process pull requests from JSON data"""
    try:
        prs = json.loads(prs_json)
        logger.info(f"Processing {len(prs)} pull requests")
        
        # Import tasks module for enqueuing
        tasks = import_tasks_module()
        
        for pr in prs:
            pr_number = pr['number']
            pr_title = pr['title']
            pr_url = pr.get('url', '')
            
            logger.info(f"Found PR #{pr_number}: {pr_title}")
            
            # Check if this PR should be reviewed
            if not should_review_pr(pr):
                continue
            
            # Skip if already reviewed or being processed
            if is_already_reviewed(pr_number):
                continue
            
            # Create lock file
            create_lock_file(pr_number)
            
            # Add retry mechanism for enqueueing
            max_retries = 3
            retry_delay = 10  # seconds
            success = False
            
            for attempt in range(1, max_retries + 1):
                try:
                    job_id = tasks.enqueue_review_pull_request(pr_number)
                    logger.info(f"Enqueued PR #{pr_number} for review with job ID: {job_id} (attempt {attempt})")
                    
                    # Add job ID to lock file
                    lock_file = os.path.join(os.environ.get('PROJECT_PATH', os.getcwd()),
                                            '.autonomous-claude', 'reviews', f"pr-{pr_number}.lock")
                    try:
                        with open(lock_file, 'a') as f:
                            f.write(f"Job ID: {job_id}\n")
                    except Exception as e:
                        logger.error(f"Error updating lock file: {str(e)}")
                    
                    print(f"Enqueued PR review job with ID: {job_id}")
                    success = True
                    break
                except Exception as e:
                    logger.error(f"Failed to enqueue PR #{pr_number} on attempt {attempt}: {str(e)}")
                    if attempt < max_retries:
                        logger.info(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        traceback.print_exc()
                        
                        # Remove lock file on final failure
                        project_path = os.environ.get('PROJECT_PATH', os.getcwd())
                        lock_file = os.path.join(project_path, '.autonomous-claude', 'reviews', f"pr-{pr_number}.lock")
                        if os.path.exists(lock_file):
                            os.remove(lock_file)
        
        return True
    except json.JSONDecodeError:
        logger.error("Failed to parse pull requests JSON")
        traceback.print_exc()
        return False
    except Exception as e:
        logger.error(f"Error processing pull requests: {str(e)}")
        traceback.print_exc()
        return False

def main():
    # Read pull requests JSON from stdin
    prs_json = sys.stdin.read()
    
    if not prs_json:
        logger.warning("No input received from stdin")
        sys.exit(1)
    
    if process_pull_requests(prs_json):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()