#!/usr/bin/env python3
# github_api_helper.py
#
# Helper functions for interacting with GitHub API via GitHub CLI
# Provides better error handling, rate limiting, and retry mechanisms

import os
import sys
import json
import time
import subprocess
import logging
import random
from datetime import datetime, timedelta

# Setup logging
log_dir = os.path.join(os.getcwd(), '.autonomous-claude', 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'github_api.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('github-api-helper')

# Tracks API request times for rate limiting
api_requests = []
RATE_LIMIT_WINDOW = 60  # 1 minute window
MAX_REQUESTS_PER_WINDOW = 30  # Max 30 requests per minute
RETRY_BACKOFF_BASE = 2  # Base for exponential backoff

def _rate_limit_wait():
    """Implement rate limiting for GitHub API calls"""
    global api_requests
    
    # Clean up old requests
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    api_requests = [t for t in api_requests if t > window_start]
    
    # Check if we're over the rate limit
    if len(api_requests) >= MAX_REQUESTS_PER_WINDOW:
        # Calculate wait time
        oldest_in_window = min(api_requests)
        wait_time = oldest_in_window + RATE_LIMIT_WINDOW - now
        
        # Add a small random jitter (0-1 seconds) to prevent all processes resuming at once
        wait_time += random.random()
        
        logger.info(f"Rate limit reached. Waiting {wait_time:.2f} seconds before next request")
        time.sleep(wait_time)
        
        # Recursive call to check again after waiting
        return _rate_limit_wait()
    
    # Record this request
    api_requests.append(now)
    return True

def _handle_error_response(gh_command, error, attempt, max_retries):
    """Handle error responses from GitHub API"""
    stderr = error.stderr if hasattr(error, 'stderr') else str(error)
    
    # Check for rate limiting errors
    if "API rate limit exceeded" in stderr:
        # Calculate reset time (typically 60 minutes for GitHub)
        wait_time = RATE_LIMIT_WINDOW * 2  # Wait for 2 minutes by default
        
        # Try to extract reset time if provided
        import re
        reset_match = re.search(r'Reset in (\d+) minutes', stderr)
        if reset_match:
            minutes = int(reset_match.group(1))
            wait_time = (minutes + 1) * 60  # Add a minute for safety
        
        logger.warning(f"GitHub API rate limit exceeded. Waiting {wait_time} seconds")
        time.sleep(wait_time)
        return True  # Retry after waiting
    
    # Check for authentication errors
    if "authentication required" in stderr or "401: Unauthorized" in stderr:
        logger.error("GitHub authentication error. Please check your credentials")
        return False  # Don't retry authentication errors
    
    # Check for resource not found
    if "404: Not Found" in stderr:
        logger.error(f"GitHub resource not found: {gh_command}")
        return False  # Don't retry 404 errors
    
    # For other errors, implement exponential backoff
    if attempt < max_retries:
        wait_time = RETRY_BACKOFF_BASE ** attempt + random.random()
        logger.warning(f"GitHub API error, retrying in {wait_time:.2f} seconds (attempt {attempt+1}/{max_retries}): {stderr}")
        time.sleep(wait_time)
        return True  # Retry after backoff
    
    # If we've exceeded retries, give up
    logger.error(f"GitHub API error, max retries exceeded: {stderr}")
    return False

def run_gh_command(gh_command, args=None, max_retries=3, parse_json=True):
    """Run a GitHub CLI command with retry logic and rate limiting"""
    if args is None:
        args = []
    
    # Build the complete command
    cmd = ['gh'] + gh_command.split() + args
    
    # Initialize attempt counter
    attempt = 0
    
    while attempt <= max_retries:
        # Apply rate limiting
        _rate_limit_wait()
        
        try:
            # Run the command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            # If we're expecting JSON, try to parse it
            if parse_json and result.stdout:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse JSON output from GitHub command: {gh_command}")
                    return result.stdout
            
            return result.stdout
            
        except subprocess.CalledProcessError as e:
            # Handle errors with potential retry
            attempt += 1
            if _handle_error_response(gh_command, e, attempt, max_retries):
                continue  # Try again
            else:
                # If no more retries or non-retryable error
                return None
        
        except Exception as e:
            logger.error(f"Unexpected error executing GitHub command: {str(e)}")
            attempt += 1
            if attempt <= max_retries:
                time.sleep(RETRY_BACKOFF_BASE ** attempt)
                continue
            return None

def get_pull_request(pr_number, fields=None):
    """Get details of a specific pull request"""
    if fields is None:
        fields = "title,number,url,body,author,baseRefName,headRefName,state,updatedAt,commits,additions,deletions,changedFiles"
    
    args = ["pr", "view", str(pr_number), "--json", fields]
    return run_gh_command("", args=args)

def get_open_pull_requests(fields=None, repo=None):
    """Get list of open pull requests"""
    if fields is None:
        fields = "title,number,url,author,updatedAt,commits,additions,deletions,changedFiles"
    
    args = ["pr", "list", "--state", "open", "--json", fields]
    if repo:
        args.extend(["--repo", repo])
        
    return run_gh_command("", args=args)

def get_pull_request_diff(pr_number):
    """Get the diff for a pull request"""
    args = ["pr", "diff", str(pr_number)]
    return run_gh_command("", args=args, parse_json=False)

def get_pull_request_files(pr_number):
    """Get the list of files changed in a pull request"""
    args = ["pr", "view", str(pr_number), "--json", "files"]
    result = run_gh_command("", args=args)
    if result and 'files' in result:
        return result['files']
    return []

def get_pull_request_commits(pr_number):
    """Get the list of commits in a pull request"""
    args = ["pr", "view", str(pr_number), "--json", "commits"]
    result = run_gh_command("", args=args)
    if result and 'commits' in result:
        return result['commits']
    return []

def get_issue(issue_number, fields=None):
    """Get details of a specific issue"""
    if fields is None:
        fields = "title,number,url,body,author,state,updatedAt,labels"
    
    args = ["issue", "view", str(issue_number), "--json", fields]
    return run_gh_command("", args=args)

def get_open_issues(label=None, fields=None, repo=None):
    """Get list of open issues"""
    if fields is None:
        fields = "title,number,url,author,updatedAt,labels"
    
    args = ["issue", "list", "--state", "open", "--json", fields]
    
    if label:
        args.extend(["--label", label])
    
    if repo:
        args.extend(["--repo", repo])
        
    return run_gh_command("", args=args)

def post_pr_comment(pr_number, comment):
    """Post a comment on a pull request"""
    args = ["pr", "comment", str(pr_number), "--body", comment]
    return run_gh_command("", args=args, parse_json=False)

def create_pr(title, body, base_branch, head_branch):
    """Create a pull request"""
    args = ["pr", "create", "--title", title, "--body", body, "--base", base_branch, "--head", head_branch]
    return run_gh_command("", args=args, parse_json=False)

def check_rate_limits():
    """Check current GitHub API rate limits"""
    args = ["api", "rate_limit"]
    return run_gh_command("", args=args)

def extract_issue_number_from_pr(pr_data):
    """Extract referenced issue number from PR description"""
    if not pr_data or 'body' not in pr_data:
        return None
    
    body = pr_data['body']
    
    # Look for common issue reference formats
    import re
    patterns = [
        r'(?:close|closes|closed|fix|fixes|fixed|resolve|resolves|resolved)[ :]* ?#(\d+)',
        r'(?:close|closes|closed|fix|fixes|fixed|resolve|resolves|resolved)[ :]* ?(?:(?:issues?)|(?:pull requests?)) ?#?(\d+)',
        r'(?:implemented|implements|addresses|addressed|related to)[ :]* ?#(\d+)',
        r'#(\d+)',  # Simple issue reference (last priority)
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, body, re.IGNORECASE)
        if matches:
            return matches[0]
    
    return None

if __name__ == "__main__":
    # Simple test when run directly
    try:
        if len(sys.argv) > 1:
            pr_number = sys.argv[1]
            pr_data = get_pull_request(pr_number)
            if pr_data:
                print(f"Retrieved PR #{pr_number}: {pr_data.get('title')}")
                issue_number = extract_issue_number_from_pr(pr_data)
                if issue_number:
                    print(f"Referenced issue: #{issue_number}")
                else:
                    print("No referenced issue found")
            else:
                print(f"Failed to retrieve PR #{pr_number}")
        else:
            print("Usage: python github_api_helper.py <pr_number>")
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)