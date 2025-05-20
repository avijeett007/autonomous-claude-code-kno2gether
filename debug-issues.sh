#\!/usr/bin/env bash
# debug-issues.sh
#
# Test script to debug the GitHub issue checker

set -e

PROJECT_PATH=$(pwd)
source "$PROJECT_PATH/.autonomous-claude/venv/bin/activate"
export PROJECT_PATH="$PROJECT_PATH"

# Create test directories if needed
mkdir -p "$PROJECT_PATH/.autonomous-claude/tasks"
mkdir -p "$PROJECT_PATH/.autonomous-claude/logs"

echo "Testing github_issue_checker.py with test data..."
cat "$PROJECT_PATH/.autonomous-claude/test_issue.json"  < /dev/null |  python "$PROJECT_PATH/.autonomous-claude/github_issue_checker.py"

echo "Done."
