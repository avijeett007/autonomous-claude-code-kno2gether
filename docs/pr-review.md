# PR Review Functionality

The Autonomous Claude system includes an integrated PR review system that automatically reviews pull requests and provides structured feedback. This document explains how the PR review system works and how to configure it.

## Overview

The PR review system consists of the following components:

1. **PR Checker**: Polls GitHub for open PRs and enqueues them for review
2. **PR-Issue Relationship Manager**: Tracks the relationships between issues and PRs
3. **Review Template**: Standardizes the format of PR reviews
4. **Claude Code Integration**: Uses Claude Code to perform the actual PR review
5. **Redis Queue**: Manages the async processing of PR reviews

## Features

- **Automated PR Review**: Automatically detect and review PRs
- **PR-Issue Relationship Tracking**: Associate PRs with the issues they address
- **Structured Review Format**: Consistent, comprehensive review format
- **Re-Review Detection**: Detect updates to PRs and trigger re-reviews
- **Review History**: Maintain a history of all reviews for each PR
- **Configurable Settings**: Control which PRs are reviewed and when

## Configuration

PR review settings can be configured in the `.autonomous-claude/config.sh` file:

```bash
# PR review settings
PR_REVIEW_ENABLED=true  # Enable/disable PR review functionality
PR_AUTO_REVIEW=true     # Automatically review PRs after creation
REVIEW_ONLY_OWN_PRS=true  # Only review PRs created by the system
```

### Settings Explained

- **PR_REVIEW_ENABLED**: When set to true, the system will check for PRs during the polling cycle
- **PR_AUTO_REVIEW**: When set to true, PRs created during issue implementation will be automatically reviewed
- **REVIEW_ONLY_OWN_PRS**: When set to true, only PRs created by the authenticated GitHub user will be reviewed

## PR Review Process

1. **PR Detection**: The system checks for open PRs during each polling cycle
2. **Filtering**: PRs are filtered based on configuration settings
3. **Enqueueing**: Eligible PRs are added to the Redis queue for processing
4. **Review Generation**: Claude Code analyzes the PR changes and generates a review
5. **Review Storage**: The review is saved to `.autonomous-claude/reviews/pr-{pr_number}-review.md`
6. **GitHub Posting**: The review is posted as a comment on the GitHub PR
7. **Relationship Update**: The PR-Issue relationship is updated with the review information

## PR-Issue Relationship

The system maintains a relationship between issues and PRs, which enables:

1. Tracking which PRs address which issues
2. Determining when a PR needs to be re-reviewed (after updates)
3. Maintaining a history of reviews for each PR

The relationship data is stored in:
- `.autonomous-claude/data/issue_pr_relationships.json`
- `.autonomous-claude/data/pr_review_history.json`

## Review Structure

PR reviews follow a structured format that includes:

- Basic information (PR number, title, URL, etc.)
- Overview assessment
- Detailed analysis by category:
  - Code quality
  - Potential bugs/issues
  - Testing
  - Implementation completeness
  - Performance considerations
  - Security considerations
- File-by-file analysis
- Suggestions for improvement
- Questions for the author
- Final recommendation

## Manual Review Trigger

To manually trigger a review for a specific PR, you can use:

```bash
cd /path/to/project
source .autonomous-claude/venv/bin/activate
python -c "from .autonomous-claude.tasks import enqueue_review_pull_request; enqueue_review_pull_request('PR_NUMBER')"
```

Replace `PR_NUMBER` with the actual PR number.

## Review Templates

The PR review template is located at `.autonomous-claude/templates/pr_review_template.md`. You can customize this template to change the structure or content of reviews.

## Logs and Debugging

Review logs can be found in:
- `.autonomous-claude/logs/worker.log`: General worker logs
- `.autonomous-claude/logs/github_pr_checker.log`: PR checker specific logs

## Status Monitoring

To check the status of the PR review system:

```bash
./autonomous-claude.sh status
```

This will show:
- Active PR reviews
- Recently completed reviews
- Queue status