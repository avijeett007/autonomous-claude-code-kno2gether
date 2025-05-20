# Usage Guide

This guide explains how to use Autonomous Claude for various workflows, from basic commands to advanced usage patterns.

## Basic Commands

Autonomous Claude provides a command-line interface through the `autonomous-claude.sh` script. Here are the core commands:

### Checking Status

```bash
autonomous-claude status
```

This command displays the status of all components, including:
- Worker process status
- Dashboard status
- Redis connection
- Queue information (jobs in queue, completed jobs, failed jobs)
- Recent logs

### Starting the Service

```bash
autonomous-claude start
```

This command:
- Checks all requirements
- Initializes the project if needed
- Sets up MCP servers
- Starts the Redis worker
- Starts the RQ dashboard
- Begins polling for GitHub issues

### Stopping the Service

```bash
autonomous-claude stop
```

This command stops all running services, including:
- Worker process
- Dashboard
- Polling for GitHub issues

### Generating Documentation

```bash
autonomous-claude docs
```

This command triggers Claude Code to scan through the codebase and generate comprehensive documentation in the `docs/` directory.

### Starting the Dashboard

```bash
autonomous-claude dashboard
```

This command starts the RQ dashboard, which provides a web interface for monitoring tasks. The dashboard is available at http://localhost:9181.

## GitHub Issue Processing Workflow

The main purpose of Autonomous Claude is to process GitHub issues automatically. Here's how to set it up and use it:

### Setting Up GitHub Issues for Autonomous Processing

1. Create issues in your GitHub repository
2. Add the designated label (default: `autonomous-coding`) to issues you want to process automatically
3. Start the autonomous system:
   ```bash
   autonomous-claude start
   ```

### The Autonomous Processing Pipeline

Once an issue is labeled, Autonomous Claude will:

1. **Detect the issue** through periodic polling
2. **Analyze the issue** and create a detailed implementation plan
   - The plan is saved to `.autonomous-claude/tasks/[issue-number]-plan.md`
3. **Implement the solution** based on the plan
   - Creates a new branch named `feature/issue-[issue-number]`
   - Makes necessary code changes
   - Adds or updates tests
   - Updates documentation
4. **Create a pull request** for review
   - Includes detailed description of changes
   - Links back to the original issue
5. **Review the pull request** (if auto-review is enabled)
   - Analyzes code quality, bugs, tests, etc.
   - Provides structured feedback
   - Posts review as a comment on the PR

### Monitoring the Progress

You can monitor the progress of issue processing through:

1. **RQ Dashboard**:
   ```bash
   autonomous-claude dashboard
   # Then open http://localhost:9181 in your browser
   ```

2. **Log files**:
   ```bash
   # View the main log file
   cat .autonomous-claude/logs/$(date +%Y-%m-%d).log
   
   # Follow the worker log
   tail -f .autonomous-claude/logs/worker.log
   ```

3. **Status command**:
   ```bash
   autonomous-claude status
   ```

### Human Review and Intervention

While Autonomous Claude can handle much of the process automatically, human review is still important:

1. **Review the implementation plan**: Check `.autonomous-claude/tasks/[issue-number]-plan.md`
2. **Review the pull request**: Examine the code changes, tests, and documentation updates
3. **Merge or request changes**: Approve and merge the PR if satisfactory, or request changes if needed

## Documentation Generation

Autonomous Claude can generate comprehensive documentation for your project:

### Generating Documentation

```bash
autonomous-claude docs
```

This command will:
1. Analyze your project structure
2. Identify key components and classes
3. Document the architecture and data flow
4. Create documentation in Markdown format in the `docs/` directory

### Customizing Documentation Generation

You can customize the documentation generation by editing the custom Claude command:

```bash
# Edit the document-project command
nano .claude/commands/document-project.md
```

## Advanced Usage

### Custom Claude Commands

Autonomous Claude uses custom Claude commands stored in `.claude/commands/`. You can modify these or add new ones:

```bash
# View existing commands
ls -la .claude/commands/

# Edit a command
nano .claude/commands/analyze-github-issue.md
```

### Running Custom Tasks

You can extend Autonomous Claude with your own custom tasks by modifying the `.autonomous-claude/tasks.py` file:

```python
# Example: Add a new task type
def enqueue_custom_task(task_name, **kwargs):
    """Add a custom task to the queue"""
    job = queue.enqueue(
        custom_task_function,
        task_name,
        kwargs,
        job_timeout='1h',
        result_ttl=86400,
        ttl=86400
    )
    return job.id
```

### Changing Polling Interval

To change how often Autonomous Claude checks for new issues:

```bash
# Edit the configuration file
nano .autonomous-claude/config.sh

# Change the POLLING_INTERVAL value (in seconds)
# Default is 300 (5 minutes)
POLLING_INTERVAL=600  # 10 minutes
```

### Working with Multiple Projects

You can use Autonomous Claude with multiple projects:

```bash
# In project 1
cd /path/to/project1
autonomous-claude init
autonomous-claude start

# In project 2
cd /path/to/project2
autonomous-claude init
autonomous-claude start
```

Each project will have its own autonomous system, including:
- Separate configuration
- Separate logs
- Separate task plans
- Separate worker process

## PR Review System

Autonomous Claude includes a powerful PR review functionality that can automatically review pull requests. For detailed documentation, see [PR Review Documentation](pr-review.md).

### Enhanced PR Review Features

- **Automatic Review**: PRs can be automatically reviewed after creation
- **Structured Reviews**: Uses a standardized template for consistent, comprehensive reviews
- **Issue-PR Relationship**: Tracks which PRs relate to which issues
- **Re-review Detection**: Smart detection of PR updates that require re-reviews
- **Review History**: Maintains a history of all reviews for each PR
- **Review Analytics**: Tracks statistics and metrics about PRs and reviews
- **Severity Ratings**: Categorizes issues by severity (Critical, High, Medium, Low)
- **Differential Re-Reviews**: Focuses on changes since the last review
- **Robust Error Handling**: Better handling of API errors and retries

### PR Review Configuration

You can configure the PR review system in `.autonomous-claude/config.sh`:

```bash
# PR review settings
PR_REVIEW_ENABLED=true          # Enable PR review functionality
PR_AUTO_REVIEW=true             # Automatically review PRs after creation
PR_AUTO_REVIEW_DELAY=30         # Delay in seconds before auto-review
PR_REVIEW_MAX_RETRIES=3         # Maximum number of retry attempts
PR_REVIEW_RETRY_DELAY=60        # Initial delay in seconds between retries
PR_UPDATE_DETECTION=true        # Monitor PRs for updates and trigger re-reviews
MIN_REREVIEW_HOURS=24           # Minimum hours between re-reviews
REVIEW_ONLY_OWN_PRS=true        # Only review PRs created by the system
```

### Manually Triggering PR Review

To manually review a specific PR:

```bash
cd /path/to/project
source .autonomous-claude/venv/bin/activate
python -c "import sys; sys.path.append('.autonomous-claude'); from tasks import enqueue_review_pull_request; print(enqueue_review_pull_request('PR_NUMBER'))"
```

Replace `PR_NUMBER` with the actual PR number.

## Example Workflows

### Basic Bug Fix Workflow

1. Create a GitHub issue describing the bug
2. Add the `autonomous-coding` label to the issue
3. Autonomous Claude will:
   - Analyze the bug and determine root cause
   - Create a fix in a new branch
   - Add or update tests
   - Create a pull request
   - Automatically review the PR (if PR_AUTO_REVIEW is enabled)

### Feature Implementation Workflow

1. Create a GitHub issue describing the feature
2. Add the `autonomous-coding` label to the issue
3. Autonomous Claude will:
   - Analyze the feature requirements
   - Create an implementation plan
   - Implement the feature in a new branch
   - Add tests and documentation
   - Create a pull request
   - Automatically review the PR (if PR_AUTO_REVIEW is enabled)

### Documentation Update Workflow

1. Run the documentation generation:
   ```bash
   autonomous-claude docs
   ```
2. Review the generated documentation
3. Commit the changes if satisfied:
   ```bash
   git add docs/
   git commit -m "Update documentation"
   git push
   ```

## Best Practices

- **Issue Description Quality**: Provide clear, detailed descriptions in your GitHub issues
- **Regular Monitoring**: Check the dashboard and logs regularly to ensure smooth operation
- **Human Review**: Always review plans and pull requests before merging
- **Custom Command Refinement**: Refine the custom Claude commands over time to improve results
- **Logging Level**: Adjust logging level based on your needs (default is INFO)
- **Error Handling**: Check and address failed jobs in the dashboard

For more advanced usage patterns, consult the [API Documentation](api-documentation.md) and [MCP Server Integration](mcp-server.md) sections.