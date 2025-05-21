# Component Reference

This document provides detailed information about the key files and components of the Autonomous Claude system.

## Core Files

### autonomous-claude.sh

**Location**: `/autonomous-claude.sh`

The main shell script that orchestrates the entire system. This script provides the command-line interface and handles most of the high-level functionality.

**Key Functions**:
- `init_project()`: Initializes a project for autonomous coding
- `start_redis_worker()`: Starts the Redis worker process
- `check_github_issues()`: Polls GitHub for issues with the specified label
- `generate_documentation()`: Triggers documentation generation
- `start_dashboard()`: Starts the RQ dashboard
- `stop_services()`: Stops all running services
- `setup_mcp_servers()`: Sets up MCP servers for enhanced capabilities
- `main_loop()`: Main polling loop for continuous operation

**Usage Examples**:
```bash
./autonomous-claude.sh start
./autonomous-claude.sh status
./autonomous-claude.sh docs
```

### worker.py

**Location**: `/.autonomous-claude/worker.py`

The Python module that processes tasks from the Redis queue. It handles running Claude Code in headless mode for various tasks.

**Key Functions**:
- `run_claude_code_headless()`: Runs Claude Code with specified prompt and tools
- `process_github_issue()`: Processes a GitHub issue through the autonomous workflow
- `update_project_documentation()`: Updates project documentation using Claude Code

**Example Code**:
```python
def run_claude_code_headless(prompt, allowed_tools=None):
    """Run Claude Code in headless mode with the given prompt"""
    claude_path = os.environ.get('CLAUDE_CODE_PATH', 'claude')
    
    # Use dangerously-skip-permissions instead of allowedTools
    command = [claude_path, '-p', prompt, '--dangerously-skip-permissions']
    
    logger.info(f"Running Claude Code with command: {' '.join(command)}")
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(f"Claude Code execution successful")
        return {
            'success': True,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"Claude Code execution failed: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'stdout': e.stdout,
            'stderr': e.stderr
        }
```

### tasks.py

**Location**: `/.autonomous-claude/tasks.py`

Handles adding tasks to the Redis queue for asynchronous processing.

**Key Functions**:
- `enqueue_process_github_issue()`: Adds a GitHub issue processing task to the queue
- `enqueue_update_documentation()`: Adds a documentation update task to the queue

**Example Code**:
```python
def enqueue_process_github_issue(issue_number):
    """Add a GitHub issue processing task to the queue"""
    job = queue.enqueue(
        process_github_issue,
        issue_number,
        job_timeout='2h',  # Long timeout for complex issues
        result_ttl=86400,  # Keep results for 24 hours
        ttl=86400          # Job can wait in queue for up to 24 hours
    )
    return job.id
```

### github_issue_checker.py

**Location**: `/.autonomous-claude/github_issue_checker.py`

Handles checking GitHub for new issues with the specified label and adding them to the processing queue.

**Key Functions**:
- `main()`: Main function that processes GitHub issues from stdin

### CLAUDE.md

**Location**: `/CLAUDE.md`

Provides guidance to Claude Code when working with code in the repository. This file is read by Claude Code to understand the project structure and commands.

### Custom Claude Commands

**Location**: `/.claude/commands/`

Markdown files that define custom commands for Claude Code to use in the autonomous workflow.

#### analyze-github-issue.md

**Location**: `/.claude/commands/analyze-github-issue.md`

Defines the command for analyzing a GitHub issue and creating an implementation plan.

**Example Content**:
```markdown
This command will analyze a GitHub issue and prepare a detailed plan for implementation.

The argument should be the GitHub issue number.

Follow these steps:
1. Use the GitHub CLI to fetch detailed information about the issue
2. Analyze the issue requirements
3. Review the existing codebase to understand what needs to be modified
4. Research any necessary information online using available MCP tools
5. Create a detailed implementation plan
6. Save the plan to .autonomous-claude/tasks/[issue-number]-plan.md

The plan should include:
- Issue summary
- Required changes
- Implementation steps
- Files to be modified
- Testing approach
- Estimated complexity
```

#### implement-github-issue.md

**Location**: `/.claude/commands/implement-github-issue.md`

Defines the command for implementing a solution based on the analysis plan.

#### document-project.md

**Location**: `/.claude/commands/document-project.md`

Defines the command for generating comprehensive project documentation.

## Configuration Files

### config.sh

**Location**: `/.autonomous-claude/config.sh`

Contains configuration settings for the autonomous system.

**Key Settings**:
- `PROJECT_PATH`: Path to the project directory
- `DOCS_PATH`: Path to the documentation directory
- `GITHUB_REPO`: GitHub repository name (username/repo)
- `GITHUB_ISSUE_LABEL`: Label to identify issues for autonomous processing
- `POLLING_INTERVAL`: How often to check for new issues (in seconds)
- `REDIS_URL`: Redis connection URL
- `REDIS_QUEUE`: Name of the Redis queue
- `MCP_SERVERS_ENABLED`: Whether MCP servers are enabled
- `MCP_SERVER_GITHUB`: Definition of the GitHub MCP server (if applicable)

**Example**:
```bash
#!/usr/bin/env bash
# Autonomous Claude configuration

# Project settings
PROJECT_PATH="/path/to/project"
DOCS_PATH="/path/to/project/docs"
GITHUB_REPO="username/repo"
GITHUB_ISSUE_LABEL="autonomous-coding"

# Operation settings
POLLING_INTERVAL=300
REDIS_URL="redis://localhost:6379"
REDIS_QUEUE="autonomous-coding"

# Paths
CLAUDE_CODE_PATH="/path/to/claude"

# MCP servers
MCP_SERVERS_ENABLED=true
# Add any custom MCP servers here
# Example: MCP_SERVER_GITHUB="docker run -i --rm -e GITHUB_PERSONAL_ACCESS_TOKEN=$GITHUB_TOKEN ghcr.io/github/github-mcp-server"
```

## Runtime Files

### worker.pid

**Location**: `/.autonomous-claude/worker.pid`

Contains the process ID of the running worker process.

### dashboard.pid

**Location**: `/.autonomous-claude/dashboard.pid`

Contains the process ID of the running RQ dashboard process.

## Task Data

### Issue Plans

**Location**: `/.autonomous-claude/tasks/[issue-number]-plan.md`

Detailed implementation plans created by Claude for each GitHub issue.

**Example Content**:
```markdown
# Implementation Plan for Issue #123: Add Dark Mode Support

## Issue Summary
The issue requests adding dark mode support to the application, including a toggle in the settings page and proper theme switching.

## Required Changes
1. Add a theme context provider
2. Create dark mode color scheme
3. Add toggle component in settings
4. Update components to use theme-aware styles

## Implementation Steps
1. Create a new ThemeContext with provider component
2. Define dark and light color themes
3. Add local storage for theme persistence
4. Create toggle component for settings page
5. Update existing components to use theme variables
6. Add tests for theme switching

## Files to be Modified
- src/contexts/ThemeContext.js (new)
- src/styles/themes.js (new)
- src/components/Settings.js
- src/components/Header.js
- src/App.js
- src/styles/global.css

## Testing Approach
1. Unit tests for ThemeContext
2. Integration tests for theme persistence
3. Visual tests for both themes

## Estimated Complexity
Medium - Requires changes across multiple components but follows established patterns.
```

### Issue Locks

**Location**: `/.autonomous-claude/tasks/[issue-number].lock`

Lock files that prevent duplicate processing of the same issue.

## Log Files

### Daily Logs

**Location**: `/.autonomous-claude/logs/YYYY-MM-DD.log`

Daily log files containing all log messages from the autonomous system.

### Worker Logs

**Location**: `/.autonomous-claude/logs/worker.log`

Log file specific to the worker process, containing detailed information about task processing.

### Worker Stdout Logs

**Location**: `/.autonomous-claude/logs/worker_stdout.log`

Standard output from the worker process.

### Dashboard Logs

**Location**: `/.autonomous-claude/logs/dashboard.log`

Log file for the RQ dashboard.

## MCP Server Files

### create_claude_mcp_server.py

**Location**: `/create_claude_mcp_server.py`

Script for creating a custom MCP server for enhanced GitHub and Redis integration.

**Key Functions**:
- `create_mcp_server_script()`: Creates the MCP server script
- `create_package_json()`: Creates the package.json file for the MCP server
- `create_readme()`: Creates the README.md file for the MCP server

The MCP server provides tools like:
- `github_search_issues`: Search GitHub issues
- `github_get_issue`: Get detailed information about an issue
- `github_comment_on_issue`: Add a comment to an issue
- `github_create_pr`: Create a pull request
- `queue_task`: Add a task to the Redis queue
- `run_claude_command`: Run a Claude Code command

## Generated Documentation

**Location**: `/docs/`

Generated documentation for the project, created by the `document-project` command.

## Python Environment

**Location**: `/.autonomous-claude/venv/`

Python virtual environment containing all required packages for the autonomous system.

## Extending and Customizing Components

### Adding Custom Tasks

To add custom tasks to the Autonomous Claude system:

1. Add a new function to `worker.py`:
```python
def my_custom_task(param1, param2):
    """Custom task implementation"""
    logger.info(f"Running custom task with {param1}, {param2}")
    # Implementation...
    return {'success': True, 'result': 'Task completed'}
```

2. Add a function to enqueue the task in `tasks.py`:
```python
def enqueue_my_custom_task(param1, param2):
    """Add custom task to the queue"""
    job = queue.enqueue(
        my_custom_task,
        param1,
        param2,
        job_timeout='1h',
        result_ttl=86400
    )
    return job.id
```

3. Add a call to the task in the main script or create a new command.

### Adding Custom Claude Commands

To add a new custom command for Claude Code:

1. Create a new Markdown file in `.claude/commands/`:
```bash
nano .claude/commands/my-custom-command.md
```

2. Define the command in the Markdown file:
```markdown
This command will perform a custom operation.

The argument should be [describe the expected argument].

Follow these steps:
1. [Step 1]
2. [Step 2]
3. [Step 3]

Additional information:
- [Info 1]
- [Info 2]
```

3. Update the main script to use the new command if needed.