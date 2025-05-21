# Troubleshooting & FAQs

This document provides solutions to common issues and answers to frequently asked questions about Autonomous Claude.

## Common Issues

### Installation Issues

#### Claude Code Not Found

**Issue**: The system cannot find Claude Code.

**Error Message**:
```
ERROR: Claude Code CLI not found. Please install it with 'npm install -g @anthropic-ai/claude-code'
```

**Solution**:
1. Ensure Claude Code is installed:
   ```bash
   npm install -g @anthropic-ai/claude-code
   ```

2. Verify the installation:
   ```bash
   claude --version
   ```

3. If installed but not found, check your PATH:
   ```bash
   which claude
   ```

4. If the path is not in your PATH, add it:
   ```bash
   export PATH="$PATH:/path/to/claude/bin"
   ```

5. Specify the Claude Code path in the configuration:
   ```bash
   # In .autonomous-claude/config.sh
   CLAUDE_CODE_PATH="/absolute/path/to/claude"
   ```

#### Redis Installation or Connection Problems

**Issue**: Redis cannot be installed or connected to.

**Error Message**:
```
ERROR: Failed to install Redis. Please install manually with 'brew install redis'
```
or
```
ERROR: Redis server not running. Please start manually.
```

**Solution**:
1. Install Redis manually:
   ```bash
   brew install redis
   ```

2. Start Redis:
   ```bash
   brew services start redis
   ```

3. Check if Redis is running:
   ```bash
   redis-cli ping
   ```
   
   Should return: `PONG`

4. If Redis is running on a different port or host, update the configuration:
   ```bash
   # In .autonomous-claude/config.sh
   REDIS_URL="redis://host:port"
   ```

#### GitHub CLI Authentication Issues

**Issue**: GitHub CLI authentication fails.

**Error Message**:
```
ERROR: Not authenticated with GitHub. Please run 'gh auth login' first.
```

**Solution**:
1. Authenticate with GitHub:
   ```bash
   gh auth login
   ```

2. Follow the prompts to complete authentication.

3. Verify authentication:
   ```bash
   gh auth status
   ```

4. If you need to use a specific token, set it in the environment:
   ```bash
   export GITHUB_TOKEN="your_token_here"
   ```

### Runtime Issues

#### Worker Process Not Starting

**Issue**: The worker process fails to start.

**Error Message**:
```
ERROR: Failed to start worker process
```

**Solution**:
1. Check Python dependencies:
   ```bash
   source .autonomous-claude/venv/bin/activate
   pip install -r requirements.txt
   ```

2. Check worker log for specific errors:
   ```bash
   cat .autonomous-claude/logs/worker.log
   ```

3. Try running the worker manually:
   ```bash
   source .autonomous-claude/venv/bin/activate
   python .autonomous-claude/worker.py
   ```

4. Check Redis connection:
   ```bash
   redis-cli ping
   ```

#### Redis Queue Issues

**Issue**: Tasks are not being processed.

**Solution**:
1. Check if the worker is running:
   ```bash
   ps aux | grep worker.py
   ```

2. Check the queue status:
   ```bash
   source .autonomous-claude/venv/bin/activate
   python -c "
   from redis import Redis
   from rq import Queue
   redis_conn = Redis.from_url('redis://localhost:6379')
   queue = Queue('autonomous-coding', connection=redis_conn)
   print(f'Jobs in queue: {len(queue)}')
   print(f'Failed jobs: {len(queue.failed_job_registry)}')
   "
   ```

3. Check if there are any failed jobs:
   ```bash
   source .autonomous-claude/venv/bin/activate
   python -c "
   from redis import Redis
   from rq import Queue
   from rq.job import Job
   redis_conn = Redis.from_url('redis://localhost:6379')
   queue = Queue('autonomous-coding', connection=redis_conn)
   failed = queue.failed_job_registry
   for job_id in failed.get_job_ids():
       job = Job.fetch(job_id, connection=redis_conn)
       print(f'Failed job {job_id}: {job.exc_info}')
   "
   ```

4. Clear the queue if necessary:
   ```bash
   source .autonomous-claude/venv/bin/activate
   python -c "
   from redis import Redis
   from rq import Queue
   redis_conn = Redis.from_url('redis://localhost:6379')
   queue = Queue('autonomous-coding', connection=redis_conn)
   queue.empty()
   print('Queue emptied')
   "
   ```

#### GitHub Issues Not Being Processed

**Issue**: GitHub issues with the specified label are not being processed.

**Solution**:
1. Check if the issue has the correct label:
   ```bash
   gh issue view <issue-number> --json labels
   ```

2. Check the polling status:
   ```bash
   cat .autonomous-claude/logs/$(date +%Y-%m-%d).log | grep "Checking GitHub issues"
   ```

3. Try manually triggering the issue check:
   ```bash
   gh issue list --repo "<username>/<repo>" --label "<label>" --state open --json number,title,url | python .autonomous-claude/github_issue_checker.py
   ```

4. Check if there's a lock file for the issue:
   ```bash
   ls -la .autonomous-claude/tasks/<issue-number>.lock
   ```
   
   If it exists, delete it to re-process:
   ```bash
   rm .autonomous-claude/tasks/<issue-number>.lock
   ```

#### Claude Code Execution Problems

**Issue**: Claude Code fails to execute or produces errors.

**Solution**:
1. Try running Claude Code manually:
   ```bash
   claude -p "/project:document-project"
   ```

2. Check if the custom commands are defined correctly:
   ```bash
   ls -la .claude/commands/
   cat .claude/commands/document-project.md
   ```

3. Check the logs for specific Claude errors:
   ```bash
   grep "Claude Code execution failed" .autonomous-claude/logs/worker.log
   ```

4. Update Claude Code:
   ```bash
   npm update -g @anthropic-ai/claude-code
   ```

#### MCP Server Issues

**Issue**: MCP server is not working properly.

**Solution**:
1. Check if the MCP server is running:
   ```bash
   ps aux | grep autonomous-mcp-server
   ```

2. Restart the MCP server:
   ```bash
   cd ./autonomous-mcp-server
   node autonomous-mcp-server.js
   ```

3. Check if Claude Code recognizes the MCP server:
   ```bash
   claude mcp list
   ```

4. Re-add the MCP server:
   ```bash
   claude mcp add autonomous_coding node /path/to/autonomous-mcp-server.js
   ```

## Frequently Asked Questions

### General Questions

#### What is Autonomous Claude?

Autonomous Claude is a utility that creates an autonomous coding system using Claude Code in headless mode. It monitors GitHub issues and automates the entire development process with minimal human intervention.

#### What Can Autonomous Claude Do?

Autonomous Claude can:
- Automatically detect and analyze GitHub issues
- Create implementation plans for solving issues
- Implement solutions and create pull requests
- Generate and update project documentation
- Work asynchronously with Redis queue

#### What Are the System Requirements?

Autonomous Claude requires:
- macOS (currently only supported OS)
- Node.js and npm (for Claude Code)
- Python 3.6+
- Git and GitHub CLI
- Redis

#### Is Autonomous Claude Free to Use?

Yes, Autonomous Claude is an open-source project and free to use. However, it requires Claude Code, which is an Anthropic product that may have its own pricing model.

### Configuration Questions

#### How Do I Change Which GitHub Issues Are Processed?

To change which issues are processed, modify the `GITHUB_ISSUE_LABEL` in your configuration:

```bash
# In .autonomous-claude/config.sh
GITHUB_ISSUE_LABEL="your-custom-label"
```

#### Can I Use Autonomous Claude with Multiple GitHub Repositories?

Yes, you can run separate instances of Autonomous Claude for different repositories:

1. Clone each repository
2. Initialize Autonomous Claude in each:
   ```bash
   cd /path/to/repo1
   autonomous-claude init
   
   cd /path/to/repo2
   autonomous-claude init
   ```

3. Configure each instance with the appropriate repository settings
4. Start each instance

#### How Do I Change the Polling Interval?

To change how often Autonomous Claude checks for new issues:

```bash
# In .autonomous-claude/config.sh
POLLING_INTERVAL=600  # Check every 10 minutes (in seconds)
```

#### Can I Customize the Claude Commands?

Yes, you can customize the Claude commands by editing the files in `.claude/commands/`:

```bash
# Edit the document-project command
nano .claude/commands/document-project.md
```

### Usage Questions

#### How Do I Monitor the Status of Tasks?

You can monitor tasks through:

1. The RQ Dashboard:
   ```bash
   autonomous-claude dashboard
   # Then open http://localhost:9181 in your browser
   ```

2. The status command:
   ```bash
   autonomous-claude status
   ```

3. Log files:
   ```bash
   cat .autonomous-claude/logs/$(date +%Y-%m-%d).log
   ```

#### Can I Run Autonomous Claude in the Background?

Yes, Autonomous Claude is designed to run in the background. When you use:

```bash
autonomous-claude start
```

The worker process and polling are started in the background.

To run it as a system service, see the [Deployment Guide](deployment-guide.md) for setting up a launchd service on macOS.

#### How Can I Generate Documentation Manually?

To manually trigger documentation generation:

```bash
autonomous-claude docs
```

This will enqueue a documentation generation task, which will be processed by the worker.

#### How Do I Stop All Services?

To stop all Autonomous Claude services:

```bash
autonomous-claude stop
```

This will stop the worker process, the RQ dashboard, and any other running components.

### Troubleshooting Questions

#### Why Aren't My GitHub Issues Being Processed?

Issues might not be processed for several reasons:

1. The issue doesn't have the specified label (`GITHUB_ISSUE_LABEL` in config)
2. A lock file exists for the issue (`.autonomous-claude/tasks/<issue-number>.lock`)
3. The worker isn't running
4. GitHub authentication has failed
5. The polling loop isn't running

Check logs and the status command for more details.

#### How Do I Clear a Stuck Task?

To clear a stuck task:

1. Find the task ID:
   ```bash
   source .autonomous-claude/venv/bin/activate
   python -c "
   from redis import Redis
   from rq import Queue
   redis_conn = Redis.from_url('redis://localhost:6379')
   queue = Queue('autonomous-coding', connection=redis_conn)
   print('Active jobs:', queue.get_job_ids())
   "
   ```

2. Cancel the job:
   ```bash
   source .autonomous-claude/venv/bin/activate
   python -c "
   from redis import Redis
   from rq.job import Job
   redis_conn = Redis.from_url('redis://localhost:6379')
   job = Job.fetch('job_id_here', connection=redis_conn)
   job.cancel()
   print('Job cancelled')
   "
   ```

3. Remove any lock files:
   ```bash
   rm .autonomous-claude/tasks/<issue-number>.lock
   ```

#### How Do I Reset the Entire System?

To reset the entire Autonomous Claude system:

1. Stop all services:
   ```bash
   autonomous-claude stop
   ```

2. Clear the Redis queue:
   ```bash
   redis-cli -h localhost -p 6379 FLUSHDB
   ```

3. Remove lock files and plans:
   ```bash
   rm -rf .autonomous-claude/tasks/*
   ```

4. Restart the services:
   ```bash
   autonomous-claude start
   ```

#### What If Claude Code Produces Incorrect Solutions?

If Claude Code produces incorrect solutions:

1. Review the plans before implementation:
   ```bash
   cat .autonomous-claude/tasks/<issue-number>-plan.md
   ```

2. Adjust the custom commands to provide better instructions:
   ```bash
   nano .claude/commands/analyze-github-issue.md
   nano .claude/commands/implement-github-issue.md
   ```

3. Add more context to the issue description
4. Consider breaking down complex tasks into smaller, more manageable issues

#### Why Is the Worker Using High CPU or Memory?

High resource usage can occur for several reasons:

1. Complex issues requiring intensive processing
2. Too many concurrent tasks
3. Insufficient system resources

Solutions:
1. Limit the number of concurrent tasks
2. Increase the worker timeout for complex tasks
3. Use a machine with more resources
4. Split large issues into smaller ones

### Advanced Questions

#### Can I Extend Autonomous Claude with Custom Tasks?

Yes, you can extend Autonomous Claude with custom tasks:

1. Add a new function to `.autonomous-claude/worker.py`
2. Add a function to enqueue the task in `.autonomous-claude/tasks.py`
3. Create a custom command in `.claude/commands/`
4. Add a command to `autonomous-claude.sh` to trigger the task

See the [API Documentation](api-documentation.md) for examples.

#### How Can I Integrate with Continuous Integration?

To integrate with CI systems:

1. Add CI-specific labels for issues (e.g., `ci-ready`)
2. Modify the implementation command to run tests and CI checks
3. Use GitHub Actions to trigger Autonomous Claude when issues are labeled
4. Have Autonomous Claude update the issue with CI results

#### Can I Use My Own LLM Instead of Claude?

Autonomous Claude is specifically designed for Claude Code. However, you could modify the system to use a different LLM:

1. Replace the `run_claude_code_headless` function with one that calls your LLM
2. Adjust the custom commands for your LLM's format
3. Update any LLM-specific configurations

This would require significant changes to the codebase.

#### How Do I Add Support for Other Version Control Systems?

Autonomous Claude currently supports GitHub. To add support for other VCS:

1. Modify the issue checking logic to work with your VCS
2. Update the custom commands to use the appropriate VCS commands
3. Add authentication and API support for your VCS
4. Create or modify the MCP server to support your VCS

## Advanced Troubleshooting

### Debug Mode

For detailed troubleshooting, enable debug mode:

```bash
# Run with debug logging
DEBUG=true autonomous-claude start
```

This will:
- Enable verbose logging
- Show detailed error messages
- Log more information about each step of the process

### Recovering from Database Corruption

If the Redis database becomes corrupted:

1. Stop the services:
   ```bash
   autonomous-claude stop
   ```

2. Backup the Redis data:
   ```bash
   cp /usr/local/var/db/redis/dump.rdb /usr/local/var/db/redis/dump.rdb.backup
   ```

3. Reset Redis:
   ```bash
   brew services stop redis
   rm /usr/local/var/db/redis/dump.rdb
   brew services start redis
   ```

4. Restart the services:
   ```bash
   autonomous-claude start
   ```

### Debugging Worker Crashes

If the worker process crashes frequently:

1. Run the worker in the foreground:
   ```bash
   source .autonomous-claude/venv/bin/activate
   python .autonomous-claude/worker.py
   ```

2. Check for Python exceptions or errors

3. Consider running with a memory profiler:
   ```bash
   pip install memory_profiler
   python -m memory_profiler .autonomous-claude/worker.py
   ```

### Debugging MCP Server Issues

For MCP server issues:

1. Run the MCP server in debug mode:
   ```bash
   DEBUG=true node ./autonomous-mcp-server/autonomous-mcp-server.js
   ```

2. Enable verbose output for Claude Code MCP interactions:
   ```bash
   claude mcp list --verbose
   ```

3. Check the Node.js and MCP SDK versions:
   ```bash
   node --version
   npm list @modelcontextprotocol/sdk
   ```

4. Reinstall the MCP SDK:
   ```bash
   cd ./autonomous-mcp-server
   npm install @modelcontextprotocol/sdk@latest
   ```

## Getting Help

If you still have issues after trying the solutions above:

1. Check for recent changes in Claude Code that might affect Autonomous Claude
2. Look for updates to Autonomous Claude
3. Submit an issue to the Autonomous Claude GitHub repository
4. Reach out to the Anthropic community for Claude Code-specific issues