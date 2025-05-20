# PR Review Functionality

The Autonomous Claude system includes an integrated PR review system that automatically reviews pull requests and provides structured feedback. This document explains how the PR review system works and how to configure it.

## Overview

The PR review system consists of the following components:

1. **PR Checker**: Polls GitHub for open PRs and enqueues them for review
2. **PR Update Detector**: Detects changes to existing PRs and triggers re-reviews
3. **PR-Issue Relationship Manager**: Tracks the relationships between issues and PRs
4. **Review Template**: Standardizes the format of PR reviews
5. **GitHub API Helper**: Provides error handling, rate limiting, and retry logic
6. **Claude Code Integration**: Uses Claude Code to perform the actual PR review
7. **Redis Queue**: Manages the async processing of PR reviews

## Features

- **Automated PR Review**: Automatically detect and review PRs
- **PR Update Detection**: Detect changes to existing PRs and trigger re-reviews
- **PR-Issue Relationship Tracking**: Associate PRs with the issues they address
- **Structured Review Format**: Consistent, comprehensive review format
- **Re-Review Detection**: Smart detection of PR updates that require re-reviews
- **Review History**: Maintain a history of all reviews for each PR
- **Review Analytics**: Track statistics about PR reviews and quality metrics
- **Severity Ratings**: Categorize issues by severity (Critical, High, Medium, Low)
- **Configurable Settings**: Control which PRs are reviewed, when, and how

## Configuration

PR review settings can be configured in the `.autonomous-claude/config.sh` file:

```bash
# PR review settings
PR_REVIEW_ENABLED=true          # Enable/disable PR review functionality
PR_AUTO_REVIEW=true             # Automatically review PRs after creation
PR_AUTO_REVIEW_DELAY=30         # Delay in seconds before auto-review
PR_REVIEW_MAX_RETRIES=3         # Maximum number of retry attempts for PR reviews
PR_REVIEW_RETRY_DELAY=60        # Initial delay in seconds between retry attempts
PR_UPDATE_DETECTION=true        # Monitor PRs for updates and trigger re-reviews
MIN_REREVIEW_HOURS=24           # Minimum hours between re-reviews
REVIEW_ONLY_OWN_PRS=true        # Only review PRs created by the system
```

### Settings Explained

- **PR_REVIEW_ENABLED**: When set to true, the system will check for PRs during the polling cycle
- **PR_AUTO_REVIEW**: When set to true, PRs created during issue implementation will be automatically reviewed
- **PR_AUTO_REVIEW_DELAY**: Seconds to wait after PR creation before auto-review (allows GitHub to process the PR)
- **PR_REVIEW_MAX_RETRIES**: Maximum attempts to review a PR if initial attempts fail
- **PR_REVIEW_RETRY_DELAY**: Initial seconds to wait between retry attempts (doubles with each retry)
- **PR_UPDATE_DETECTION**: When set to true, the system will monitor PRs for updates and trigger re-reviews
- **MIN_REREVIEW_HOURS**: Minimum time to wait before re-reviewing a PR
- **REVIEW_ONLY_OWN_PRS**: When set to true, only PRs created by the authenticated GitHub user will be reviewed

## PR Review Process

1. **PR Detection**: The system checks for open PRs during each polling cycle
2. **Filtering**: PRs are filtered based on configuration settings
3. **Enqueueing**: Eligible PRs are added to the Redis queue for processing
4. **Review Generation**: Claude Code analyzes the PR changes and generates a review
5. **Review Storage**: The review is saved to `.autonomous-claude/reviews/pr-{pr_number}-review.md`
6. **GitHub Posting**: The review is posted as a comment on the GitHub PR
7. **Relationship Update**: The PR-Issue relationship is updated with the review information
8. **Analytics**: Review metrics are stored and used to track PR and author trends

## PR Update Detection

The system can monitor PRs for updates and trigger re-reviews when:

1. **New Commits**: The PR has new commits since the last review
2. **Significant Changes**: The PR has been updated in a meaningful way
3. **Time-Based**: A minimum time period has passed since the last review

The update detection respects the `MIN_REREVIEW_HOURS` setting to avoid too frequent re-reviews.

## Differential Re-Reviews

When a PR is re-reviewed, the system:

1. Provides the previous review information to Claude
2. Highlights previous issues that should be checked
3. Focuses on changes made since the last review
4. Determines if previous issues have been addressed
5. Notes any new issues introduced by the changes

## PR-Issue Relationship

The system maintains a relationship between issues and PRs, which enables:

1. Tracking which PRs address which issues
2. Determining when a PR needs to be re-reviewed (after updates)
3. Maintaining a history of reviews for each PR
4. Collecting metrics about PR quality, issues found, etc.

The relationship data is stored in:
- `.autonomous-claude/data/issue_pr_relationships.json`
- `.autonomous-claude/data/pr_review_history.json`
- `.autonomous-claude/data/pr_review_metrics.json`

## Review Structure

PR reviews follow a structured format that includes:

- Basic information (PR number, title, URL, etc.)
- Review type (initial or re-review)
- Overview assessment
- Severity ratings (Critical, High, Medium, Low)
- Detailed analysis by category:
  - Code quality
  - Potential bugs/issues
  - Security considerations
  - Performance analysis
  - Testing analysis
  - Implementation completeness
  - Documentation quality
- File-by-file analysis
- Positive aspects
- Suggestions for improvement
- Questions for the author
- Next steps for the author
- Final recommendation

## Review Analytics

The system tracks analytics about reviews, including:

1. **Issues by Severity**: Number of critical, high, medium, and low issues
2. **Issues by Category**: Breakdown of issues by category (code quality, bugs, etc.)
3. **Author Metrics**: Statistics grouped by PR author
4. **Review Trends**: Changes in issue counts and types over time

## GitHub API Integration

The system includes robust GitHub API integration with:

1. **Rate Limiting**: Smart handling of GitHub API rate limits
2. **Error Handling**: Proper handling of various API errors
3. **Retry Logic**: Automatic retry with exponential backoff
4. **Resource Management**: Efficient use of GitHub API resources

## Manual Review Trigger

To manually trigger a review for a specific PR, you can use:

```bash
cd /path/to/project
source .autonomous-claude/venv/bin/activate
python -c "import sys; sys.path.append('.autonomous-claude'); from tasks import enqueue_review_pull_request; print(enqueue_review_pull_request('PR_NUMBER'))"
```

Replace `PR_NUMBER` with the actual PR number.

## Review Templates

The PR review template is located at `.autonomous-claude/templates/pr_review_template.md`. You can customize this template to change the structure or content of reviews.

## Logs and Debugging

Review logs can be found in:
- `.autonomous-claude/logs/worker.log`: General worker logs
- `.autonomous-claude/logs/github_pr_checker.log`: PR checker specific logs
- `.autonomous-claude/logs/github_pr_update_detector.log`: PR update detector logs
- `.autonomous-claude/logs/github_api.log`: GitHub API interaction logs
- `.autonomous-claude/logs/pr_relationship.log`: PR-Issue relationship logs

## Status Monitoring

To check the status of the PR review system:

```bash
./autonomous-claude.sh status
```

This will show:
- Active PR reviews
- Recently completed reviews
- Queue status
- Review metrics and statistics