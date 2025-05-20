#!/usr/bin/env python3
# test_pr_review.py
#
# Test script for PR review functionality
# This script tests various components of the PR review system

import os
import sys
import json
import time
import logging
from datetime import datetime

# Setup logging
log_dir = os.path.join(os.getcwd(), '.autonomous-claude', 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'test_pr_review.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('test-pr-review')

def test_github_api_helper():
    """Test the GitHub API Helper module"""
    print("\n=== Testing GitHub API Helper ===")
    
    try:
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from github_api_helper import run_gh_command, get_open_pull_requests, extract_issue_number_from_pr
        
        # Test basic command
        print("Testing basic GitHub command...")
        whoami = run_gh_command("auth status", parse_json=False)
        if whoami:
            print(f"GitHub authentication: OK")
        else:
            print(f"GitHub authentication: Failed")
        
        # Test rate limiting
        print("\nTesting rate limiting...")
        start_time = time.time()
        for i in range(5):
            result = run_gh_command("api rate_limit")
            if result:
                print(f"Rate limit request {i+1}: OK")
            else:
                print(f"Rate limit request {i+1}: Failed")
        
        elapsed = time.time() - start_time
        print(f"Time for 5 requests: {elapsed:.2f} seconds")
        
        # Test error handling by intentionally causing an error
        print("\nTesting error handling...")
        result = run_gh_command("nonexistent-command", max_retries=1)
        print(f"Error handling (expected failure): {'OK' if result is None else 'Failed'}")
        
        return True
    except ImportError:
        print("GitHub API Helper module not found")
        return False
    except Exception as e:
        print(f"Error testing GitHub API Helper: {e}")
        return False

def test_pr_issue_relationship():
    """Test the PR-Issue Relationship module"""
    print("\n=== Testing PR-Issue Relationship ===")
    
    try:
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from pr_issue_relationship import get_instance
        
        # Get instance
        relationship_manager = get_instance()
        print("PR-Issue Relationship Manager initialized")
        
        # Test relationship file paths
        data_dir = os.path.join(os.getcwd(), '.autonomous-claude', 'data')
        relationships_file = os.path.join(data_dir, 'issue_pr_relationships.json')
        review_history_file = os.path.join(data_dir, 'pr_review_history.json')
        review_metrics_file = os.path.join(data_dir, 'pr_review_metrics.json')
        
        print(f"Relationship files exist:")
        print(f"  - relationships: {os.path.exists(relationships_file)}")
        print(f"  - review history: {os.path.exists(review_history_file)}")
        print(f"  - review metrics: {os.path.exists(review_metrics_file)}")
        
        # Test metrics extraction
        print("\nTesting metrics extraction...")
        sample_review = """
# Pull Request Review - PR #123

## Overview Assessment

This PR has some good aspects but also several issues.

**Final Recommendation**: Approve with Changes

## Code Quality Analysis

**Issues Found**:

- **Medium**: The function on line 45 is too complex
- **Low**: Variable naming could be improved

## Potential Bugs/Issues

**Issues Found**: 

- **Critical**: Potential null pointer dereference on line 67
- **High**: Race condition in async operation

## Security Considerations

**Security Issues**:

- **High**: SQL injection vulnerability in query construction
"""
        metrics = relationship_manager.extract_metrics_from_review(sample_review)
        print("Extracted metrics:")
        print(json.dumps(metrics, indent=2))
        
        return True
    except ImportError:
        print("PR-Issue Relationship module not found")
        return False
    except Exception as e:
        print(f"Error testing PR-Issue Relationship: {e}")
        return False

def test_pr_update_detector():
    """Test the PR Update Detector logic"""
    print("\n=== Testing PR Update Detector ===")
    
    try:
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from github_pr_update_detector import should_trigger_rereview
        from pr_issue_relationship import get_instance
        
        # Create test PR details
        pr_details = {
            'number': 999,
            'title': 'Test PR',
            'updated_at': datetime.now().isoformat(),
            'commits': 3
        }
        
        # Get relationship manager
        relationship_manager = get_instance()
        
        # Test the should_trigger_rereview function (will return False for test PR)
        result = should_trigger_rereview(pr_details, relationship_manager)
        print(f"Update detection (expected False for non-existent PR): {'OK' if result is False else 'Failed'}")
        
        return True
    except ImportError:
        print("PR Update Detector module not found")
        return False
    except Exception as e:
        print(f"Error testing PR Update Detector: {e}")
        return False

def test_review_template():
    """Test the PR Review Template"""
    print("\n=== Testing PR Review Template ===")
    
    # Check if template exists
    template_path = os.path.join(os.getcwd(), '.autonomous-claude', 'templates', 'pr_review_template.md')
    if not os.path.exists(template_path):
        print(f"PR Review Template not found at {template_path}")
        return False
    
    # Read template and check for expected sections
    with open(template_path, 'r') as f:
        template = f.read()
    
    expected_sections = [
        "# Pull Request Review",
        "## Summary",
        "## Overview Assessment",
        "## Severity Ratings",
        "## Code Quality Analysis",
        "## Potential Bugs/Issues",
        "## Security Considerations",
        "## Performance Analysis",
        "## Testing Analysis",
        "## Implementation Completeness",
        "## Documentation Quality",
        "## File-by-File Analysis",
        "## Positive Aspects",
        "## Suggestions for Improvement",
        "## Questions for Author",
        "## Next Steps"
    ]
    
    missing_sections = []
    for section in expected_sections:
        if section not in template:
            missing_sections.append(section)
    
    if missing_sections:
        print(f"Missing sections in template: {', '.join(missing_sections)}")
        return False
    else:
        print("PR Review Template contains all expected sections")
        return True

def main():
    """Run all tests"""
    print("=== Testing PR Review System ===")
    print(f"Started at: {datetime.now().isoformat()}")
    
    tests = [
        test_github_api_helper,
        test_pr_issue_relationship,
        test_pr_update_detector,
        test_review_template
    ]
    
    results = {}
    for test_func in tests:
        test_name = test_func.__name__
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            logger.error(f"Error running test {test_name}: {e}")
            results[test_name] = False
    
    # Print summary
    print("\n=== Test Summary ===")
    all_passed = True
    for test_name, result in results.items():
        print(f"{test_name}: {'PASSED' if result else 'FAILED'}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\nAll tests PASSED!")
    else:
        print("\nSome tests FAILED. Check logs for details.")

if __name__ == "__main__":
    main()