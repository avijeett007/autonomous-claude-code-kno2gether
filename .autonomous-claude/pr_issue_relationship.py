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
import re
from datetime import datetime, timedelta
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
review_metrics_file = os.path.join(data_dir, 'pr_review_metrics.json')

class PRIssueRelationship:
    """Class to manage the relationship between GitHub issues and pull requests"""
    
    def __init__(self):
        self.relationships = self._load_relationships()
        self.review_history = self._load_review_history()
        self.review_metrics = self._load_review_metrics()
    
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
    
    def _load_review_metrics(self):
        """Load existing review metrics from file"""
        if os.path.exists(review_metrics_file):
            try:
                with open(review_metrics_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to load review metrics file: {e}")
                return {}
        # Initialize metrics structure if it doesn't exist
        return {
            "authors": {},
            "global": {
                "total_reviews": 0,
                "issues_by_severity": {
                    "critical": 0,
                    "high": 0,
                    "medium": 0,
                    "low": 0
                },
                "issues_by_category": {
                    "code_quality": 0,
                    "bugs": 0,
                    "security": 0,
                    "performance": 0,
                    "testing": 0,
                    "documentation": 0
                },
                "avg_review_time": 0,
                "total_review_time": 0
            }
        }
    
    def _save_review_metrics(self):
        """Save review metrics to file"""
        try:
            with open(review_metrics_file, 'w') as f:
                json.dump(self.review_metrics, f, indent=2)
            logger.info("Saved review metrics to file")
            return True
        except IOError as e:
            logger.error(f"Failed to save review metrics to file: {e}")
            return False
    
    def associate_pr_with_issue(self, issue_number, pr_number, pr_url=None, pr_title=None):
        """Associate a pull request with an issue"""
        issue_key = str(issue_number)
        pr_key = str(pr_number)
        
        # Fetch PR details if not provided
        if pr_url is None or pr_title is None:
            try:
                pr_json = subprocess.check_output(
                    ['gh', 'pr', 'view', pr_number, '--json', 'title,url,author'],
                    text=True
                )
                pr_data = json.loads(pr_json)
                pr_url = pr_data.get('url', '')
                pr_title = pr_data.get('title', '')
                pr_author = pr_data.get('author', {}).get('login', '')
            except Exception as e:
                logger.error(f"Failed to fetch PR details: {e}")
                # Use placeholder values if GH CLI fails
                pr_url = pr_url or f"unknown_url_for_pr_{pr_number}"
                pr_title = pr_title or f"Unknown PR #{pr_number}"
                pr_author = "unknown"
        else:
            # If we don't have author, try to get it
            try:
                pr_json = subprocess.check_output(
                    ['gh', 'pr', 'view', pr_number, '--json', 'author'],
                    text=True
                )
                pr_data = json.loads(pr_json)
                pr_author = pr_data.get('author', {}).get('login', 'unknown')
            except Exception as e:
                logger.error(f"Failed to fetch PR author: {e}")
                pr_author = "unknown"
        
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
            'pr_author': pr_author,
            'created_at': datetime.now().isoformat(),
            'review_status': 'pending',  # pending, in_progress, completed
            'latest_review_id': None,
            'review_count': 0
        }
        
        # Update timestamp
        self.relationships[issue_key]['last_updated'] = datetime.now().isoformat()
        
        # Save to file
        self._save_relationships()
        
        # Initialize author metrics if this is a new author
        if pr_author != "unknown" and pr_author not in self.review_metrics["authors"]:
            self.review_metrics["authors"][pr_author] = {
                "total_prs": 0,
                "total_reviews": 0,
                "issues_by_severity": {
                    "critical": 0,
                    "high": 0,
                    "medium": 0,
                    "low": 0
                },
                "issues_by_category": {
                    "code_quality": 0,
                    "bugs": 0,
                    "security": 0,
                    "performance": 0,
                    "testing": 0,
                    "documentation": 0
                },
                "avg_review_time": 0,
                "total_review_time": 0
            }
            self.review_metrics["authors"][pr_author]["total_prs"] = 1
            self._save_review_metrics()
        elif pr_author != "unknown":
            # Increment PR count for existing author
            self.review_metrics["authors"][pr_author]["total_prs"] += 1
            self._save_review_metrics()
        
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
                
                # Increment review count if completed
                if status == 'completed':
                    issue_data['prs'][pr_key]['review_count'] = issue_data['prs'][pr_key].get('review_count', 0) + 1
                
                # Update timestamp
                issue_data['last_updated'] = datetime.now().isoformat()
                
                # Save to file
                self._save_relationships()
                
                logger.info(f"Updated PR #{pr_number} review status to {status}")
                return True
        
        logger.warning(f"PR #{pr_number} not found in any issue relationship")
        return False
    
    def extract_metrics_from_review(self, review_content):
        """Extract metrics from review content"""
        metrics = {
            "issues_by_severity": {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0
            },
            "issues_by_category": {
                "code_quality": 0,
                "bugs": 0,
                "security": 0,
                "performance": 0,
                "testing": 0,
                "documentation": 0
            }
        }
        
        # Count severity levels
        critical_matches = re.findall(r'\*\*Critical\*\*', review_content, re.IGNORECASE)
        high_matches = re.findall(r'\*\*High\*\*', review_content, re.IGNORECASE)
        medium_matches = re.findall(r'\*\*Medium\*\*', review_content, re.IGNORECASE)
        low_matches = re.findall(r'\*\*Low\*\*', review_content, re.IGNORECASE)
        
        metrics["issues_by_severity"]["critical"] = len(critical_matches)
        metrics["issues_by_severity"]["high"] = len(high_matches)
        metrics["issues_by_severity"]["medium"] = len(medium_matches)
        metrics["issues_by_severity"]["low"] = len(low_matches)
        
        # Count issues by category
        # Simple heuristic: check if there are any issues in each section
        if re.search(r'## Code Quality Analysis.*?\*\*Issues Found\*\*:.*?[^\s]', review_content, re.DOTALL):
            # Count bullet points in the code quality section
            section = re.search(r'## Code Quality Analysis.*?(?=##|\Z)', review_content, re.DOTALL)
            if section:
                bullet_points = re.findall(r'- ', section.group(0))
                metrics["issues_by_category"]["code_quality"] = len(bullet_points)
        
        if re.search(r'## Potential Bugs/Issues.*?\*\*Issues Found\*\*:.*?[^\s]', review_content, re.DOTALL):
            section = re.search(r'## Potential Bugs/Issues.*?(?=##|\Z)', review_content, re.DOTALL)
            if section:
                bullet_points = re.findall(r'- ', section.group(0))
                metrics["issues_by_category"]["bugs"] = len(bullet_points)
        
        if re.search(r'## Security Considerations.*?\*\*Security Issues\*\*:.*?[^\s]', review_content, re.DOTALL):
            section = re.search(r'## Security Considerations.*?(?=##|\Z)', review_content, re.DOTALL)
            if section:
                bullet_points = re.findall(r'- ', section.group(0))
                metrics["issues_by_category"]["security"] = len(bullet_points)
        
        if re.search(r'## Performance Analysis.*?\*\*Performance Issues\*\*:.*?[^\s]', review_content, re.DOTALL):
            section = re.search(r'## Performance Analysis.*?(?=##|\Z)', review_content, re.DOTALL)
            if section:
                bullet_points = re.findall(r'- ', section.group(0))
                metrics["issues_by_category"]["performance"] = len(bullet_points)
        
        if re.search(r'## Testing Analysis.*?(?:\*\*Test Coverage\*\*|\*\*Test Quality\*\*):.*?[^\s]', review_content, re.DOTALL):
            section = re.search(r'## Testing Analysis.*?(?=##|\Z)', review_content, re.DOTALL)
            if section:
                bullet_points = re.findall(r'- ', section.group(0))
                metrics["issues_by_category"]["testing"] = len(bullet_points)
        
        if re.search(r'## Documentation Quality.*?\*\*Documentation Issues\*\*:.*?[^\s]', review_content, re.DOTALL):
            section = re.search(r'## Documentation Quality.*?(?=##|\Z)', review_content, re.DOTALL)
            if section:
                bullet_points = re.findall(r'- ', section.group(0))
                metrics["issues_by_category"]["documentation"] = len(bullet_points)
        
        return metrics
    
    def update_metrics_from_review(self, pr_number, review_data, review_content):
        """Update metrics based on a review"""
        # Get PR author
        pr_relation = self.get_pr_issue_relationship(pr_number)
        if not pr_relation:
            logger.warning(f"PR #{pr_number} not found in relationships, can't update metrics")
            return
        
        pr_author = pr_relation['pr_data'].get('pr_author', 'unknown')
        
        # Extract metrics from review content
        metrics = self.extract_metrics_from_review(review_content)
        
        # Update global metrics
        self.review_metrics["global"]["total_reviews"] += 1
        
        for severity, count in metrics["issues_by_severity"].items():
            self.review_metrics["global"]["issues_by_severity"][severity] += count
        
        for category, count in metrics["issues_by_category"].items():
            self.review_metrics["global"]["issues_by_category"][category] += count
        
        # Update author metrics
        if pr_author != "unknown":
            if pr_author not in self.review_metrics["authors"]:
                self.review_metrics["authors"][pr_author] = {
                    "total_prs": 1,
                    "total_reviews": 0,
                    "issues_by_severity": {
                        "critical": 0,
                        "high": 0,
                        "medium": 0,
                        "low": 0
                    },
                    "issues_by_category": {
                        "code_quality": 0,
                        "bugs": 0,
                        "security": 0,
                        "performance": 0,
                        "testing": 0,
                        "documentation": 0
                    },
                    "avg_review_time": 0,
                    "total_review_time": 0
                }
            
            self.review_metrics["authors"][pr_author]["total_reviews"] += 1
            
            for severity, count in metrics["issues_by_severity"].items():
                self.review_metrics["authors"][pr_author]["issues_by_severity"][severity] += count
            
            for category, count in metrics["issues_by_category"].items():
                self.review_metrics["authors"][pr_author]["issues_by_category"][category] += count
        
        # Save updated metrics
        self._save_review_metrics()
    
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
        
        # Determine if this is an initial review or re-review
        review_type = "initial"
        if len(self.review_history[pr_key]['reviews']) > 0:
            review_type = "re-review"
        
        # Add review type to data
        review_data['review_type'] = review_type
        
        # Add review record
        review_record = {
            'review_id': review_id,
            'timestamp': datetime.now().isoformat(),
            'data': review_data,
            'review_type': review_type
        }
        
        self.review_history[pr_key]['reviews'].append(review_record)
        self.review_history[pr_key]['last_updated'] = datetime.now().isoformat()
        
        # Save to file
        self._save_review_history()
        
        # Update the PR's latest review ID in the relationship
        self.update_pr_review_status(pr_number, 'completed', review_id)
        
        # Update metrics if content is available
        if 'content' in review_data:
            self.update_metrics_from_review(pr_number, review_data, review_data['content'])
        
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
    
    def get_previous_review(self, pr_number, current_review_id=None):
        """Get the previous review before the current one"""
        reviews = self.get_pr_review_history(pr_number)
        if not reviews:
            return None
        
        if current_review_id:
            # Find the index of the current review
            current_index = -1
            for i, review in enumerate(reviews):
                if review.get('review_id') == current_review_id:
                    current_index = i
                    break
            
            # If found and not the first, return the previous review
            if current_index > 0:
                return reviews[current_index - 1]
            elif current_index == 0:
                return None  # No previous review
        
        # If no current_review_id or not found, return the second latest if exists
        if len(reviews) > 1:
            return reviews[-2]
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
        
        # Check if the PR is currently being reviewed
        if review_status == 'in_progress':
            logger.info(f"PR #{pr_number} is currently being reviewed, should not be reviewed again")
            return False
        
        # Check PR update timestamp vs last review timestamp
        pr_latest_review_id = pr_relationship['pr_data'].get('latest_review_id')
        
        if review_status == 'completed' and pr_latest_review_id:
            # Get latest review timestamp
            latest_review = self.get_latest_review(pr_number)
            if not latest_review:
                logger.warning(f"PR #{pr_number} has no review history despite having review_id, should be reviewed")
                return True
            
            review_timestamp = datetime.fromisoformat(latest_review['timestamp'])
            
            try:
                # Check if the PR has been updated since last review
                # Get PR updated timestamp from GitHub
                pr_json = subprocess.check_output(
                    ['gh', 'pr', 'view', pr_number, '--json', 'updatedAt'],
                    text=True
                )
                pr_data = json.loads(pr_json)
                pr_updated_at = pr_data.get('updatedAt', '')
                
                if not pr_updated_at:
                    logger.warning(f"Failed to get updatedAt for PR #{pr_number}, defaulting to re-review")
                    return True
                
                # Parse GitHub timestamps
                # GitHub format: 2023-10-25T15:40:24Z
                pr_updated_at_dt = datetime.fromisoformat(pr_updated_at.replace('Z', '+00:00'))
                
                # Add a small delay (5 minutes) to account for clock differences and processing time
                review_timestamp_with_delay = review_timestamp + timedelta(minutes=5)
                
                # Compare timestamps
                if pr_updated_at_dt > review_timestamp_with_delay:
                    logger.info(f"PR #{pr_number} was updated after last review ({pr_updated_at} > {review_timestamp}), should be re-reviewed")
                    return True
                else:
                    # Check minimum re-review interval
                    min_rereview_interval = timedelta(hours=24)  # Don't re-review more than once per day
                    time_since_review = datetime.now() - review_timestamp
                    
                    if time_since_review < min_rereview_interval:
                        logger.info(f"PR #{pr_number} was reviewed recently ({time_since_review} ago), should wait for re-review")
                        return False
                    
                    # Check if commits have been added since last review
                    last_reviewed_commits = latest_review['data'].get('commit_count', 0)
                    
                    try:
                        # Get current commit count
                        pr_json = subprocess.check_output(
                            ['gh', 'pr', 'view', pr_number, '--json', 'commits'],
                            text=True
                        )
                        pr_data = json.loads(pr_json)
                        current_commits = len(pr_data.get('commits', []))
                        
                        if current_commits > last_reviewed_commits:
                            logger.info(f"PR #{pr_number} has new commits since last review ({current_commits} > {last_reviewed_commits}), should be re-reviewed")
                            return True
                    except Exception as e:
                        logger.error(f"Failed to check commit count: {e}")
            except Exception as e:
                logger.error(f"Failed to check PR update status: {e}")
                # If we can't determine, err on the side of reviewing
                return True
        
        # If status is pending, review it
        if review_status == 'pending':
            logger.info(f"PR #{pr_number} review status is pending, should be reviewed")
            return True
        
        # By default, don't review the PR again if it's already been reviewed and no new changes
        return False
    
    def is_pr_from_issue(self, pr_number, issue_number):
        """Check if a PR is associated with a specific issue"""
        pr_relationship = self.get_pr_issue_relationship(pr_number)
        if pr_relationship and str(pr_relationship['issue_number']) == str(issue_number):
            return True
        return False
    
    def get_pr_review_metrics(self, pr_number=None, author=None):
        """Get review metrics for a PR or author"""
        if pr_number:
            # Get metrics for specific PR
            pr_key = str(pr_number)
            if pr_key in self.review_history:
                pr_metrics = {
                    "review_count": len(self.review_history[pr_key]['reviews']),
                    "first_review": self.review_history[pr_key]['reviews'][0]['timestamp'] if self.review_history[pr_key]['reviews'] else None,
                    "latest_review": self.review_history[pr_key]['reviews'][-1]['timestamp'] if self.review_history[pr_key]['reviews'] else None,
                    "reviews": []
                }
                
                # Extract metrics for each review
                for review in self.review_history[pr_key]['reviews']:
                    review_content = review['data'].get('content', '')
                    metrics = self.extract_metrics_from_review(review_content)
                    review_metrics = {
                        "review_id": review['review_id'],
                        "timestamp": review['timestamp'],
                        "review_type": review.get('review_type', 'unknown'),
                        "metrics": metrics
                    }
                    pr_metrics["reviews"].append(review_metrics)
                
                return pr_metrics
            return None
        
        if author:
            # Get metrics for specific author
            if author in self.review_metrics["authors"]:
                return self.review_metrics["authors"][author]
            return None
        
        # Return global metrics if no specific filter
        return self.review_metrics["global"]
    
    def analyze_pr_trends(self, time_period=30):
        """Analyze PR review trends over a specified time period (in days)"""
        cutoff_date = datetime.now() - timedelta(days=time_period)
        
        trends = {
            "total_prs": 0,
            "total_reviews": 0,
            "issues_by_severity": {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0
            },
            "issues_by_category": {
                "code_quality": 0,
                "bugs": 0,
                "security": 0,
                "performance": 0,
                "testing": 0,
                "documentation": 0
            },
            "top_authors": [],
            "avg_time_to_review": 0,
            "review_frequency": 0  # reviews per day
        }
        
        # Track reviews per day
        days_with_reviews = set()
        review_counts = {}
        
        # Analyze review history for trend data
        for pr_key, pr_data in self.review_history.items():
            for review in pr_data['reviews']:
                review_timestamp = datetime.fromisoformat(review['timestamp'])
                
                # Skip reviews outside the time period
                if review_timestamp < cutoff_date:
                    continue
                
                # Count review
                trends["total_reviews"] += 1
                
                # Track day of review for frequency calculation
                day_str = review_timestamp.strftime("%Y-%m-%d")
                days_with_reviews.add(day_str)
                
                # Get review metrics
                if 'data' in review and 'content' in review['data']:
                    metrics = self.extract_metrics_from_review(review['data']['content'])
                    
                    # Accumulate severity counts
                    for severity, count in metrics["issues_by_severity"].items():
                        trends["issues_by_severity"][severity] += count
                    
                    # Accumulate category counts
                    for category, count in metrics["issues_by_category"].items():
                        trends["issues_by_category"][category] += count
                
                # Count PR
                if pr_key not in review_counts:
                    review_counts[pr_key] = 1
                    trends["total_prs"] += 1
                else:
                    review_counts[pr_key] += 1
        
        # Calculate review frequency
        days_in_period = time_period
        if days_with_reviews:
            trends["review_frequency"] = trends["total_reviews"] / len(days_with_reviews)
        
        # Calculate average time to review
        # This would require PR creation timestamps which we don't track
        # We'll leave it as 0 for now
        
        # Find top authors
        author_review_counts = {}
        for author, data in self.review_metrics["authors"].items():
            # This is an approximation since we don't have date filtering in the author metrics
            author_review_counts[author] = data["total_reviews"]
        
        # Sort authors by review count and take top 5
        trends["top_authors"] = sorted(
            author_review_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        return trends


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
    print(f"Review metrics file: {review_metrics_file}")