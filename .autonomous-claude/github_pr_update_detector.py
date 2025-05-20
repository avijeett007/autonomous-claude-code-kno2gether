#!/usr/bin/env python3
# github_pr_update_detector.py
#
# Monitors GitHub pull requests for updates and triggers re-reviews when necessary
# Works alongside github_pr_checker.py but focuses on detecting changes to existing PRs

import os
import sys
import json
import time
import logging
import traceback
import importlib.util
from datetime import datetime, timedelta

# Try to import GitHub API helper
try:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from github_api_helper import run_gh_command, get_pull_request, get_pull_request_commits
    use_api_helper = True
except ImportError:
    use_api_helper = False

# Setup logging
log_dir = os.path.join(os.getcwd(), '.autonomous-claude', 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'github_pr_update_detector.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('github-pr-update-detector')

# Import PR relationship module
def import_relationship_module():
    """Import PR relationship module dynamically"""
    project_path = os.environ.get('PROJECT_PATH', os.getcwd())
    module_path = os.path.join(project_path, '.autonomous-claude', 'pr_issue_relationship.py')
    
    if not os.path.exists(module_path):
        logger.error(f"PR relationship module not found at {module_path}")
        return None
    
    try:
        sys.path.append(os.path.dirname(os.path.abspath(module_path)))
        from pr_issue_relationship import get_instance
        logger.info("Successfully imported PR relationship module")
        return get_instance()
    except ImportError as e:
        logger.error(f"Failed to import PR relationship module: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error importing PR relationship module: {str(e)}")
        return None

# Load tasks module dynamically
def import_tasks_module():
    """Import tasks module dynamically"""
    project_path = os.environ.get('PROJECT_PATH', os.getcwd())
    tasks_path = os.path.join(project_path, '.autonomous-claude', 'tasks.py')
    
    if not os.path.exists(tasks_path):
        logger.error(f"Tasks module not found at {tasks_path}")
        return None
    
    try:
        spec = importlib.util.spec_from_file_location("tasks", tasks_path)
        tasks_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tasks_module)
        logger.info("Successfully imported tasks module")
        return tasks_module
    except Exception as e:
        logger.error(f"Failed to import tasks module: {str(e)}")
        return None

def extract_pr_details(pr):
    """Extract relevant details from PR data"""
    details = {
        'number': pr.get('number'),
        'title': pr.get('title', ''),
        'url': pr.get('url', ''),
        'state': pr.get('state', ''),
        'author': pr.get('author', {}).get('login', 'unknown'),
        'updated_at': pr.get('updatedAt', ''),
        'commits': len(pr.get('commits', [])),
        'additions': pr.get('additions', 0),
        'deletions': pr.get('deletions', 0),
        'changed_files': pr.get('changedFiles', 0)
    }
    return details

def should_trigger_rereview(pr_details, relationship_manager):
    """Determine if PR changes warrant a re-review"""
    pr_number = pr_details['number']
    
    # Check if the PR exists in our tracking system
    pr_relationship = relationship_manager.get_pr_issue_relationship(pr_number)
    if not pr_relationship:
        logger.info(f"PR #{pr_number} not found in relationship tracking, skipping")
        return False
    
    # Get the latest review
    latest_review = relationship_manager.get_latest_review(pr_number)
    if not latest_review:
        logger.info(f"No previous review found for PR #{pr_number}, should trigger initial review")
        return True
    
    # Skip PRs that are currently being reviewed
    if pr_relationship['pr_data'].get('review_status') == 'in_progress':
        logger.info(f"PR #{pr_number} is currently being reviewed, skipping")
        return False
    
    # Get latest review timestamp and other metadata
    review_timestamp = datetime.fromisoformat(latest_review.get('timestamp', '2000-01-01T00:00:00'))
    commit_count = latest_review.get('data', {}).get('commit_count', 0)
    
    # Get more detailed PR data if using API helper
    if use_api_helper:
        try:
            # Get current commit data
            commits = get_pull_request_commits(pr_number)
            current_commit_count = len(commits) if commits else pr_details['commits']
            
            # Get most recent commit date
            if commits and len(commits) > 0:
                latest_commit = commits[-1]
                latest_commit_date = latest_commit.get('commit', {}).get('committer', {}).get('date', '')
                
                if latest_commit_date:
                    try:
                        commit_date = datetime.fromisoformat(latest_commit_date.replace('Z', '+00:00'))
                        if commit_date > review_timestamp:
                            logger.info(f"PR #{pr_number} has a new commit after the last review")
                            return True
                    except Exception as e:
                        logger.warning(f"Error parsing commit date: {e}")
            
            # Check for commit count changes (fallback if date parsing fails)
            if current_commit_count > commit_count:
                logger.info(f"PR #{pr_number} has new commits: {current_commit_count} > {commit_count}")
                return True
            
        except Exception as e:
            logger.warning(f"Error checking PR using API helper: {e}")
            # Fall back to basic checks if API helper fails
    
    # Check if PR updated since last review
    if pr_details['updated_at']:
        try:
            pr_updated_at = datetime.fromisoformat(pr_details['updated_at'].replace('Z', '+00:00'))
            
            # Add a small buffer to account for processing time and clock differences
            review_timestamp_with_buffer = review_timestamp + timedelta(minutes=5)
            
            if pr_updated_at > review_timestamp_with_buffer:
                logger.info(f"PR #{pr_number} was updated after last review ({pr_updated_at} > {review_timestamp})")
                
                # Check for specific types of changes
                if pr_details['commits'] > commit_count:
                    logger.info(f"PR #{pr_number} has new commits: {pr_details['commits']} > {commit_count}")
                    return True
                
                # Check for other significant changes by looking at timestamp
                # This might be comments or other metadata that doesn't change commit count
                time_since_update = datetime.now() - pr_updated_at
                if time_since_update < timedelta(hours=6):  # Only consider recent updates
                    logger.info(f"PR #{pr_number} has recent update ({time_since_update} ago)")
                    return True
        except Exception as e:
            logger.error(f"Error checking PR update timestamp: {e}")
            return False
    
    # Check minimum wait time between reviews (don't re-review too frequently)
    time_since_review = datetime.now() - review_timestamp
    min_rereview_interval = timedelta(hours=int(os.environ.get('MIN_REREVIEW_HOURS', '24')))
    
    if time_since_review < min_rereview_interval:
        logger.info(f"PR #{pr_number} was reviewed too recently ({time_since_review} ago), waiting")
        return False
    
    # If we get here, the PR doesn't need a re-review
    logger.info(f"PR #{pr_number} doesn't need re-review at this time")
    return False

def process_pull_requests(prs_json):
    """Process pull requests to detect those needing re-review"""
    try:
        # Parse PR data
        prs = json.loads(prs_json)
        logger.info(f"Checking {len(prs)} pull requests for updates")
        
        # Import modules
        relationship_manager = import_relationship_module()
        tasks = import_tasks_module()
        
        if not relationship_manager or not tasks:
            logger.error("Failed to import required modules, cannot process PRs")
            return False
        
        # Check each PR for updates
        for pr in prs:
            try:
                pr_details = extract_pr_details(pr)
                pr_number = pr_details['number']
                
                logger.info(f"Checking updates for PR #{pr_number}: {pr_details['title']}")
                
                # Skip PRs that don't match our criteria
                if pr_details['state'] != 'OPEN':
                    logger.info(f"Skipping PR #{pr_number} as it's not open")
                    continue
                
                # Check with relationship manager if this PR should be re-reviewed
                if should_trigger_rereview(pr_details, relationship_manager):
                    logger.info(f"Changes detected for PR #{pr_number}, triggering re-review")
                    
                    # Directly use relationship manager to find existing review locks
                    project_path = os.environ.get('PROJECT_PATH', os.getcwd())
                    reviews_dir = os.path.join(project_path, '.autonomous-claude', 'reviews')
                    lock_file = os.path.join(reviews_dir, f"pr-{pr_number}.lock")
                    
                    # Skip if there's an active lock
                    if os.path.exists(lock_file):
                        lock_time = os.path.getmtime(lock_file)
                        if time.time() - lock_time < 3600:  # 1 hour in seconds
                            logger.info(f"PR #{pr_number} is already being processed, skipping")
                            continue
                        else:
                            logger.info(f"Found stale lock for PR #{pr_number}, removing")
                            os.remove(lock_file)
                    
                    # Create lock file
                    os.makedirs(reviews_dir, exist_ok=True)
                    with open(lock_file, 'w') as f:
                        timestamp = datetime.now().isoformat()
                        f.write(f"Re-review scheduled: {timestamp}\n")
                    
                    # Enqueue the PR for re-review
                    try:
                        # First, update the review status
                        relationship_manager.update_pr_review_status(pr_number, 'pending')
                        
                        # Then enqueue the review job
                        job_id = tasks.enqueue_review_pull_request(pr_number)
                        logger.info(f"Enqueued PR #{pr_number} for re-review with job ID: {job_id}")
                        
                        # Add job ID to lock file
                        with open(lock_file, 'a') as f:
                            f.write(f"Job ID: {job_id}\n")
                    except Exception as e:
                        logger.error(f"Failed to enqueue PR #{pr_number}: {str(e)}")
                        traceback.print_exc()
                        
                        # Remove lock file on failure
                        if os.path.exists(lock_file):
                            os.remove(lock_file)
            except Exception as e:
                logger.error(f"Error processing PR #{pr.get('number', 'unknown')}: {str(e)}")
                traceback.print_exc()
        
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