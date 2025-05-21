#!/usr/bin/env python3
# pr_review_integration.py
#
# Integrates PR review functionality with the autonomous coding workflow
# Detects PRs created by the autonomous agent and triggers reviews

import os
import sys
import json
import time
import logging
import traceback
import importlib.util
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler

# Setup logging
log_dir = os.path.join(os.getcwd(), '.autonomous-claude', 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'pr_review_integration.log')

logger = logging.getLogger('pr-review-integration')
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

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

def get_config():
    """Get configuration settings related to PR review"""
    config = {
        'auto_review_enabled': os.environ.get('AUTO_PR_REVIEW', 'true').lower() == 'true',
        'review_delay_minutes': int(os.environ.get('PR_REVIEW_DELAY_MINUTES', '5')),
        'min_rereview_hours': int(os.environ.get('MIN_REREVIEW_HOURS', '24')),
    }
    return config

def run_gh_command(command, capture_json=True):
    """Run GitHub CLI command and return the result"""
    import subprocess
    
    try:
        if capture_json:
            result = subprocess.check_output(command, text=True)
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON from command: {' '.join(command)}")
                return result
        else:
            result = subprocess.check_output(command, text=True)
            return result
    except subprocess.CalledProcessError as e:
        logger.error(f"GitHub CLI command failed: {' '.join(command)}")
        logger.error(f"Error output: {e.output if hasattr(e, 'output') else 'No output'}")
        return None
    except Exception as e:
        logger.error(f"Error running GitHub CLI command: {str(e)}")
        return None

def get_recently_created_prs():
    """Get recently created PRs that might be candidates for review"""
    command = ['gh', 'pr', 'list', '--json', 'number,title,url,author,createdAt,updatedAt,state,additions,deletions,changedFiles,commits']
    return run_gh_command(command)

def get_autonomous_prs(prs, hours=24):
    """Filter PRs created by the autonomous agent within the specified time window"""
    # Define the autonomous agent GitHub username
    autonomous_user = os.environ.get('GITHUB_USERNAME', 'autonomous-claude')
    
    # Calculate the time threshold
    cutoff_time = datetime.now() - timedelta(hours=hours)
    
    # Filter PRs
    autonomous_prs = []
    for pr in prs:
        # Check if PR was created by the autonomous agent
        is_autonomous = pr.get('author', {}).get('login', '') == autonomous_user
        
        # Check if PR was created recently
        created_at = pr.get('createdAt', '')
        if created_at:
            try:
                created_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                is_recent = created_time > cutoff_time
            except Exception:
                is_recent = False
        else:
            is_recent = False
        
        # Add to list if both conditions met
        if is_autonomous and is_recent and pr.get('state') == 'OPEN':
            autonomous_prs.append(pr)
    
    return autonomous_prs

def needs_review(pr, relationship_manager):
    """Check if a PR needs to be reviewed based on our criteria"""
    pr_number = pr.get('number')
    
    # Skip if PR doesn't have a number
    if not pr_number:
        return False
    
    # Using the relationship manager to check if PR needs review
    return relationship_manager.should_review_pr(pr_number)

def enqueue_pr_for_review(pr_number, tasks_module):
    """Enqueue a PR for review using the tasks module"""
    try:
        # Check if the review function exists in the tasks module
        if hasattr(tasks_module, 'enqueue_review_pull_request'):
            # Enqueue the review
            job_id = tasks_module.enqueue_review_pull_request(pr_number)
            logger.info(f"Enqueued PR #{pr_number} for review with job ID: {job_id}")
            return job_id
        else:
            logger.error("Tasks module doesn't have the enqueue_review_pull_request function")
            return None
    except Exception as e:
        logger.error(f"Failed to enqueue PR #{pr_number} for review: {str(e)}")
        return None

def process_autonomous_prs():
    """Process PRs created by the autonomous agent for review"""
    # Get configuration
    config = get_config()
    if not config['auto_review_enabled']:
        logger.info("Automatic PR review is disabled, skipping")
        return False
    
    # Import required modules
    relationship_manager = import_relationship_module()
    tasks_module = import_tasks_module()
    
    if not relationship_manager or not tasks_module:
        logger.error("Required modules not available")
        return False
    
    try:
        # Get recently created PRs
        all_prs = get_recently_created_prs()
        if not all_prs:
            logger.info("No PRs found")
            return True
        
        # Filter for autonomous PRs
        autonomous_prs = get_autonomous_prs(all_prs)
        logger.info(f"Found {len(autonomous_prs)} PRs created by the autonomous agent")
        
        # Process each PR
        for pr in autonomous_prs:
            pr_number = pr.get('number')
            logger.info(f"Processing PR #{pr_number}: {pr.get('title', '')}")
            
            # Check if PR needs review
            if needs_review(pr, relationship_manager):
                logger.info(f"PR #{pr_number} needs review, enqueuing")
                
                # Create lock file to prevent duplicate reviews
                project_path = os.environ.get('PROJECT_PATH', os.getcwd())
                reviews_dir = os.path.join(project_path, '.autonomous-claude', 'reviews')
                os.makedirs(reviews_dir, exist_ok=True)
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
                with open(lock_file, 'w') as f:
                    timestamp = datetime.now().isoformat()
                    f.write(f"Review scheduled: {timestamp}\n")
                
                # Update the review status
                relationship_manager.update_pr_review_status(pr_number, 'pending')
                
                # Enqueue the review job
                job_id = enqueue_pr_for_review(pr_number, tasks_module)
                if job_id:
                    # Add job ID to lock file
                    with open(lock_file, 'a') as f:
                        f.write(f"Job ID: {job_id}\n")
                else:
                    # Remove lock file on failure
                    if os.path.exists(lock_file):
                        os.remove(lock_file)
            else:
                logger.info(f"PR #{pr_number} doesn't need review at this time")
        
        return True
    except Exception as e:
        logger.error(f"Error processing autonomous PRs: {str(e)}")
        traceback.print_exc()
        return False

def main():
    """Main function to run the PR review integration"""
    logger.info("Starting PR review integration")
    
    # Process PRs created by the autonomous agent
    success = process_autonomous_prs()
    
    if success:
        logger.info("PR review integration completed successfully")
        sys.exit(0)
    else:
        logger.error("PR review integration failed")
        sys.exit(1)

if __name__ == "__main__":
    main()