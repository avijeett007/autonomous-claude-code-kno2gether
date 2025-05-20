#!/usr/bin/env python3
# pr_issue_relationship.py
#
# Manages the relationship between GitHub issues and pull requests
# Tracks which PRs are associated with which issues, and maintains the status
# of PRs for review tracking and management

import os
import json
import logging
import time
import subprocess
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Setup logging
log_dir = os.path.join(os.getcwd(), '.autonomous-claude', 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'pr_relationship.log')

logger = logging.getLogger('pr-issue-relationship')
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Directory for storing relationship data
data_dir = os.path.join(os.getcwd(), '.autonomous-claude', 'data')
os.makedirs(data_dir, exist_ok=True)
relationships_file = os.path.join(data_dir, 'issue_pr_relationships.json')
review_history_file = os.path.join(data_dir, 'pr_review_history.json')

class PRIssueRelationship:
    """Class to manage the relationship between GitHub issues and pull requests"""
    
    def __init__(self):
        self.relationships = self._load_relationships()
        self.review_history = self._load_review_history()
    
    def _load_relationships(self):
        """Load existing relationships from file"""
        if os.path.exists(relationships_file):
            try:
                with open(relationships_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to load relationships file: {e}")
                return {}
        return {}
    
    def _save_relationships(self):
        """Save relationships to file"""
        try:
            with open(relationships_file, 'w') as f:
                json.dump(self.relationships, f, indent=2)
            logger.info("Saved relationships to file")
            return True
        except IOError as e:
            logger.error(f"Failed to save relationships to file: {e}")
            return False
    
    def _load_review_history(self):
        """Load existing review history from file"""
        if os.path.exists(review_history_file):
            try:
                with open(review_history_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to load review history file: {e}")
                return {}
        return {}
    
    def _save_review_history(self):
        """Save review history to file"""
        try:
            with open(review_history_file, 'w') as f:
                json.dump(self.review_history, f, indent=2)
            logger.info("Saved review history to file")
            return True
        except IOError as e:
            logger.error(f"Failed to save review history to file: {e}")
            return False
    
    def associate_pr_with_issue(self, issue_number, pr_number, pr_url=None, pr_title=None):
        """Associate a pull request with an issue"""
        issue_key = str(issue_number)
        pr_key = str(pr_number)
        
        # Fetch PR details if not provided
        if pr_url is None or pr_title is None:
            try:
                pr_json = subprocess.check_output(
                    ['gh', 'pr', 'view', pr_number, '--json', 'title,url'],
                    text=True
                )
                pr_data = json.loads(pr_json)
                pr_url = pr_data.get('url', '')
                pr_title = pr_data.get('title', '')
            except Exception as e:
                logger.error(f"Failed to fetch PR details: {e}")
                # Use placeholder values if GH CLI fails
                pr_url = pr_url or f"unknown_url_for_pr_{pr_number}"
                pr_title = pr_title or f"Unknown PR #{pr_number}"
        
        # Update or create relationship
        if issue_key not in self.relationships:
            self.relationships[issue_key] = {
                'prs': {},
                'last_updated': datetime.now().isoformat()
            }
        
        # Add or update PR information
        self.relationships[issue_key]['prs'][pr_key] = {
            'pr_number': pr_number,
            'pr_url': pr_url,
            'pr_title': pr_title,
            'created_at': datetime.now().isoformat(),
            'review_status': 'pending',  # pending, in_progress, completed
            'latest_review_id': None
        }
        
        # Update timestamp
        self.relationships[issue_key]['last_updated'] = datetime.now().isoformat()
        
        # Save to file
        self._save_relationships()
        
        logger.info(f"Associated PR #{pr_number} with issue #{issue_number}")
        return True
    
    def get_associated_prs(self, issue_number):
        """Get all PRs associated with an issue"""
        issue_key = str(issue_number)
        if issue_key in self.relationships:
            return self.relationships[issue_key]['prs']
        return {}
    
    def get_pr_issue_relationship(self, pr_number):
        """Get the issue associated with a PR"""
        pr_key = str(pr_number)
        for issue_key, issue_data in self.relationships.items():
            if pr_key in issue_data['prs']:
                return {
                    'issue_number': issue_key,
                    'pr_data': issue_data['prs'][pr_key]
                }
        return None
    
    def update_pr_review_status(self, pr_number, status, review_id=None):
        """Update the review status of a PR"""
        pr_key = str(pr_number)
        
        # Find the PR in the relationships
        for issue_key, issue_data in self.relationships.items():
            if pr_key in issue_data['prs']:
                # Update the review status
                issue_data['prs'][pr_key]['review_status'] = status
                
                # Update review ID if provided
                if review_id:
                    issue_data['prs'][pr_key]['latest_review_id'] = review_id
                
                # Update timestamp
                issue_data['last_updated'] = datetime.now().isoformat()
                
                # Save to file
                self._save_relationships()
                
                logger.info(f"Updated PR #{pr_number} review status to {status}")
                return True
        
        logger.warning(f"PR #{pr_number} not found in any issue relationship")
        return False
    
    def add_review_record(self, pr_number, review_data):
        """Add a new review record for a PR"""
        pr_key = str(pr_number)
        
        if pr_key not in self.review_history:
            self.review_history[pr_key] = {
                'reviews': [],
                'last_updated': datetime.now().isoformat()
            }
        
        # Generate review ID
        review_id = f"review_{int(time.time())}"
        
        # Add review record
        review_record = {
            'review_id': review_id,
            'timestamp': datetime.now().isoformat(),
            'data': review_data
        }
        
        self.review_history[pr_key]['reviews'].append(review_record)
        self.review_history[pr_key]['last_updated'] = datetime.now().isoformat()
        
        # Save to file
        self._save_review_history()
        
        # Update the PR's latest review ID in the relationship
        self.update_pr_review_status(pr_number, 'completed', review_id)
        
        logger.info(f"Added review record for PR #{pr_number} with ID {review_id}")
        return review_id
    
    def get_pr_review_history(self, pr_number):
        """Get the review history for a PR"""
        pr_key = str(pr_number)
        if pr_key in self.review_history:
            return self.review_history[pr_key]['reviews']
        return []
    
    def get_latest_review(self, pr_number):
        """Get the latest review for a PR"""
        reviews = self.get_pr_review_history(pr_number)
        if reviews:
            return reviews[-1]
        return None
    
    def should_review_pr(self, pr_number):
        """Determine if a PR should be reviewed based on its current status"""
        pr_relationship = self.get_pr_issue_relationship(pr_number)
        
        # If PR is not associated with any issue, review it anyway
        if not pr_relationship:
            logger.info(f"PR #{pr_number} not associated with any issue, should be reviewed")
            return True
        
        # Get the PR's review status
        review_status = pr_relationship['pr_data']['review_status']
        
        # Check PR update timestamp vs last review timestamp
        pr_latest_review_id = pr_relationship['pr_data'].get('latest_review_id')
        
        if review_status == 'completed' and pr_latest_review_id:
            # Check if PR has been updated since last review
            try:
                # Get PR updated timestamp from GitHub
                pr_json = subprocess.check_output(
                    ['gh', 'pr', 'view', pr_number, '--json', 'updatedAt'],
                    text=True
                )
                pr_data = json.loads(pr_json)
                pr_updated_at = pr_data.get('updatedAt', '')
                
                if pr_updated_at:
                    # Get latest review timestamp
                    latest_review = self.get_latest_review(pr_number)
                    if latest_review:
                        review_timestamp = latest_review['timestamp']
                        
                        # Compare timestamps (string comparison works for ISO format)
                        if pr_updated_at > review_timestamp:
                            logger.info(f"PR #{pr_number} was updated after last review, should be re-reviewed")
                            return True
            except Exception as e:
                logger.error(f"Failed to check PR update status: {e}")
                # If we can't determine, err on the side of reviewing
                return True
        
        # If status is pending or in_progress, don't review again
        if review_status in ['pending', 'in_progress']:
            logger.info(f"PR #{pr_number} review status is {review_status}, should not be reviewed again")
            return False
        
        # By default, review the PR
        return True
    
    def is_pr_from_issue(self, pr_number, issue_number):
        """Check if a PR is associated with a specific issue"""
        pr_relationship = self.get_pr_issue_relationship(pr_number)
        if pr_relationship and str(pr_relationship['issue_number']) == str(issue_number):
            return True
        return False


# Singleton instance for global access
_instance = None

def get_instance():
    """Get the singleton instance of PRIssueRelationship"""
    global _instance
    if _instance is None:
        _instance = PRIssueRelationship()
    return _instance

if __name__ == '__main__':
    # Simple test when run directly
    relationship_manager = get_instance()
    print("PR-Issue Relationship Manager initialized")
    print(f"Relationships file: {relationships_file}")
    print(f"Review history file: {review_history_file}")