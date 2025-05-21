# System Architecture

This document provides a detailed overview of the Autonomous Claude system architecture, how different components interact, and the data flow through the system.

## Architectural Overview

Autonomous Claude is designed with a modular architecture that separates concerns and enables asynchronous processing. The system consists of the following main components:

![Autonomous Claude Architecture](architecture-diagram.png)

## Core Components

### 1. Main Shell Script (`autonomous-claude.sh`)

The `autonomous-claude.sh` shell script is the primary entry point and orchestrator for the entire system. It handles:

- Project initialization and configuration
- Service startup and shutdown
- GitHub issue polling
- Environment setup
- Task queueing
- Dependency checking

The script provides a command-line interface with several key commands:
- `init`: Initialize a project for autonomous coding
- `start`: Start the autonomous coding service
- `stop`: Stop all services
- `docs`: Generate project documentation
- `dashboard`: Start the RQ dashboard
- `status`: Show status of all services

### 2. Redis Queue System

Autonomous Claude uses Redis and RQ (Redis Queue) for asynchronous task processing:

- **Redis**: Provides the persistent storage for the queue
- **RQ**: A Python library for task queuing based on Redis
- **RQ Dashboard**: A web interface for monitoring tasks

The queue system handles:
- Task prioritization and scheduling
- Storing job state and results
- Managing retries and failures
- Distributing work across processes

### 3. Worker Process (`worker.py`)

The worker process consumes tasks from the Redis queue and executes them. Key responsibilities include:

- Running Claude Code in headless mode
- Processing GitHub issues (analysis and implementation)
- Updating project documentation
- Error handling and logging
- Reporting results back to the queue

The worker is designed to run continuously in the background, processing tasks as they arrive in the queue.

### 4. Task Management (`tasks.py`)

The task management module handles the addition of tasks to the Redis queue. It provides functions for:

- Enqueueing GitHub issue processing tasks
- Enqueueing documentation update tasks
- Setting timeout and TTL parameters
- Managing job priority

### 5. GitHub Issue Checker (`github_issue_checker.py`)

This component is responsible for checking GitHub for new issues with the specified label and adding them to the processing queue. It:

- Polls the GitHub API at regular intervals
- Filters issues based on labels
- Creates lock files to prevent duplicate processing
- Enqueues new issues for processing

### 6. Headless Claude Code

Claude Code runs in non-interactive mode through the worker process to:
- Analyze GitHub issues and create plans
- Implement solutions based on those plans
- Generate and update documentation
- Create pull requests

### 7. Custom Claude Commands

The system extends Claude Code with several custom commands:

- `/project:analyze-github-issue`: Analyzes an issue and creates a detailed plan
- `/project:implement-github-issue`: Implements a solution based on the plan
- `/project:document-project`: Generates comprehensive documentation

These commands are defined as Markdown files in the `.claude/commands/` directory.

### 8. MCP Server Integration (Optional)

The Model Context Protocol (MCP) server integration provides additional capabilities:

- **GitHub Integration**: Allows Claude to interact directly with GitHub APIs
- **Redis Integration**: Enables queue management and monitoring
- **Custom Tools**: Provides domain-specific tools for autonomous coding

## Data Flow

The data flow through the system follows these steps:

1. **Issue Detection**:
   - `autonomous-claude.sh` periodically calls `github_issue_checker.py`
   - The checker finds new issues with the specified label
   - Issues are added to the Redis queue via `tasks.py`

2. **Analysis Phase**:
   - The worker process consumes a task from the queue
   - The worker runs Claude Code with the `/project:analyze-github-issue` command
   - Claude analyzes the issue and creates a plan
   - The plan is saved to `.autonomous-claude/tasks/[issue-number]-plan.md`

3. **Implementation Phase**:
   - The worker runs Claude Code with the `/project:implement-github-issue` command
   - Claude reads the plan and implements the solution
   - Claude creates a new branch, makes changes, and adds tests
   - Claude creates a pull request for review

4. **Documentation Phase**:
   - The worker runs Claude Code with the `/project:document-project` command
   - Claude scans the codebase and generates documentation
   - Documentation is saved to the `docs/` directory

## Directory Structure

```
project-root/
├── autonomous-claude.sh         # Main script
├── CLAUDE.md                    # Instructions for Claude Code
├── README.md                    # Project README
├── .autonomous-claude/          # Configuration and runtime files
│   ├── config.sh                # Configuration file
│   ├── logs/                    # Log files
│   │   ├── YYYY-MM-DD.log       # Daily logs
│   │   └── worker.log           # Worker-specific logs
│   ├── tasks/                   # Task plans and lock files
│   │   ├── issue-123-plan.md    # Plan for issue #123
│   │   └── issue-123.lock       # Lock file for issue #123
│   ├── venv/                    # Python virtual environment
│   ├── worker.py                # Worker process
│   ├── worker.pid               # Worker process ID
│   ├── tasks.py                 # Task management
│   ├── dashboard.pid            # Dashboard process ID
│   └── github_issue_checker.py  # GitHub issue checker
├── .claude/                     # Claude Code configuration
│   └── commands/                # Custom Claude commands
│       ├── analyze-github-issue.md
│       ├── document-project.md
│       └── implement-github-issue.md
└── docs/                        # Generated documentation
```

## Configuration

The system configuration is stored in `.autonomous-claude/config.sh` and includes:

- Project paths and settings
- GitHub repository details
- Polling interval for GitHub issues
- Redis connection settings
- MCP server configuration

## Security Considerations

The Autonomous Claude system runs with significant permissions, including:

- GitHub repository access
- Execution of code via Claude Code
- File system access

Key security considerations include:

- **GitHub Authentication**: Limited to necessary scopes
- **Code Execution**: Restricted to the project directory
- **Plan Review**: Human review of plans before implementation
- **PR Review**: Human review of pull requests before merging

## Scalability

The system is designed to scale in several ways:

- **Parallel Processing**: Multiple workers can consume tasks from the queue
- **Task Prioritization**: Important tasks can be prioritized in the queue
- **Resource Limits**: Timeouts and memory limits prevent runaway processes

## Dependencies

Autonomous Claude depends on the following external tools and libraries:

- **Claude Code CLI**: For headless AI-powered coding
- **GitHub CLI**: For GitHub API interaction
- **Redis**: For the queue backend
- **RQ (Redis Queue)**: For Python-based task queuing
- **Python 3**: For the worker and task management
- **Bash**: For the main orchestration script