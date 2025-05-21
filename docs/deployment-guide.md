# Deployment and Configuration Guide

This guide provides detailed instructions for deploying and configuring Autonomous Claude in various environments, from development to production.

## Configuration Options

### Core Configuration File

The main configuration for Autonomous Claude is stored in `.autonomous-claude/config.sh`. This file is created during initialization and can be customized to suit your needs.

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
```

### Configuration Parameters

| Parameter | Description | Default | Example |
|-----------|-------------|---------|---------|
| `PROJECT_PATH` | Path to your project directory | Current working directory | `/Users/username/projects/myapp` |
| `DOCS_PATH` | Path to your documentation directory | `$PROJECT_PATH/docs` | `/Users/username/projects/myapp/docs` |
| `GITHUB_REPO` | GitHub repository in format username/repo | Auto-detected using GitHub CLI | `username/repo` |
| `GITHUB_ISSUE_LABEL` | Label to identify issues for autonomous processing | `autonomous-coding` | `bot-fix` |
| `POLLING_INTERVAL` | How often to check for new issues (in seconds) | `300` (5 minutes) | `600` (10 minutes) |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379` | `redis://username:password@redis.example.com:6379` |
| `REDIS_QUEUE` | Name of the Redis queue | `autonomous-coding` | `myapp-tasks` |
| `CLAUDE_CODE_PATH` | Path to Claude Code executable | Auto-detected | `/usr/local/bin/claude` |
| `MCP_SERVERS_ENABLED` | Whether MCP servers are enabled | `true` | `false` |
| `MCP_SERVER_GITHUB` | GitHub MCP server configuration | Not set | `docker run -i --rm -e GITHUB_TOKEN=$GITHUB_TOKEN ghcr.io/github/github-mcp-server` |

## Deployment Scenarios

### Development Environment

For local development, the basic setup is sufficient:

```bash
# Initialize the project
cd /path/to/project
autonomous-claude init

# Edit configuration if needed
nano .autonomous-claude/config.sh

# Start the services
autonomous-claude start
```

This will:
- Run Redis locally
- Use the local GitHub CLI authentication
- Poll for issues every 5 minutes
- Store logs and task plans in the `.autonomous-claude` directory

### Production Deployment

For production environments, additional considerations are necessary:

#### System Service Setup

To run Autonomous Claude as a system service on macOS, create a launchd plist:

```bash
cat > ~/Library/LaunchAgents/com.user.autonomous-claude.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.autonomous-claude</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/autonomous-claude.sh</string>
        <string>start</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>/path/to/your/project</string>
    <key>StandardOutPath</key>
    <string>/path/to/your/project/.autonomous-claude/logs/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/path/to/your/project/.autonomous-claude/logs/stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>GITHUB_TOKEN</key>
        <string>your_github_token_here</string>
    </dict>
</dict>
</plist>
EOF

# Load the service
launchctl load ~/Library/LaunchAgents/com.user.autonomous-claude.plist
```

#### Remote Redis Setup

For production, you may want to use a hosted Redis service:

1. Update the configuration to use the remote Redis:

```bash
# In .autonomous-claude/config.sh
REDIS_URL="redis://username:password@redis.example.com:6379"
```

2. If using Redis with TLS/SSL:

```bash
# In .autonomous-claude/config.sh
REDIS_URL="rediss://username:password@redis.example.com:6379"
```

#### Secure GitHub Token Management

For production, securely manage GitHub tokens:

1. Store the token in an environment variable:

```bash
# In .autonomous-claude/config.sh
# Do not hard-code the token here
# Instead, reference the environment variable
GITHUB_TOKEN_ENV="${GITHUB_TOKEN}"
```

2. Set up the environment variable in the launchd plist as shown above

#### Logging Configuration

For production, configure more robust logging:

1. Update the worker script to use a more comprehensive logging setup:

```python
# In .autonomous-claude/worker.py
import logging.config

logging.config.dictConfig({
    'version': 1,
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
    },
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/worker.log',
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 10,
            'formatter': 'standard',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        }
    },
    'loggers': {
        'autonomous-claude-worker': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True
        }
    }
})

logger = logging.getLogger('autonomous-claude-worker')
```

### Multi-Environment Setup

For running in multiple environments (dev, staging, production):

1. Create separate configuration files:

```bash
cp .autonomous-claude/config.sh .autonomous-claude/config.dev.sh
cp .autonomous-claude/config.sh .autonomous-claude/config.staging.sh
cp .autonomous-claude/config.sh .autonomous-claude/config.prod.sh
```

2. Edit each configuration file for its environment

3. Use the appropriate configuration with an environment variable:

```bash
# Modify autonomous-claude.sh to support env-specific configs
if [ -n "$AUTONOMOUS_CLAUDE_ENV" ] && [ -f "$PROJECT_PATH/.autonomous-claude/config.$AUTONOMOUS_CLAUDE_ENV.sh" ]; then
  source "$PROJECT_PATH/.autonomous-claude/config.$AUTONOMOUS_CLAUDE_ENV.sh"
else
  source "$CONFIG_FILE"
fi
```

4. Run with the environment specified:

```bash
AUTONOMOUS_CLAUDE_ENV=prod autonomous-claude start
```

## Advanced Configuration

### Queue Configuration

You can configure the Redis queue settings in `.autonomous-claude/tasks.py`:

```python
def enqueue_process_github_issue(issue_number):
    """Add a GitHub issue processing task to the queue"""
    job = queue.enqueue(
        process_github_issue,
        issue_number,
        job_timeout='2h',     # Adjust timeout as needed
        result_ttl=86400,     # Adjust result storage time
        ttl=86400,            # Adjust queue time
        priority=10           # Set priority (lower is higher priority)
    )
    return job.id
```

### Worker Concurrency

For handling multiple tasks concurrently, you can run multiple worker processes:

```bash
# Start multiple workers
for i in {1..3}; do
  python3 "$PROJECT_PATH/.autonomous-claude/worker.py" > "$PROJECT_PATH/.autonomous-claude/logs/worker_${i}_stdout.log" 2>&1 &
  echo $! > "$PROJECT_PATH/.autonomous-claude/worker_${i}.pid"
  echo "Worker $i started with PID: $!"
done
```

Modify the `start_redis_worker` function in `autonomous-claude.sh` to implement this.

### Custom Claude Commands

You can customize the Claude commands used by the system by editing the files in `.claude/commands/`:

```bash
# Edit the analyze-github-issue command
nano .claude/commands/analyze-github-issue.md

# Edit the implement-github-issue command
nano .claude/commands/implement-github-issue.md

# Edit the document-project command
nano .claude/commands/document-project.md
```

### MCP Server Configuration

For custom MCP server settings:

1. Create the MCP server:

```bash
python create_claude_mcp_server.py --output ./autonomous-mcp-server
```

2. Customize the server:

```bash
nano ./autonomous-mcp-server/autonomous-mcp-server.js
```

3. Configure Autonomous Claude to use it:

```bash
# In .autonomous-claude/config.sh
MCP_SERVERS_ENABLED=true
MCP_SERVER_CUSTOM="node /path/to/autonomous-mcp-server/autonomous-mcp-server.js"
```

## Performance Tuning

### Optimizing Redis Performance

To optimize Redis performance:

1. Configure Redis with appropriate memory settings:

```bash
# In redis.conf
maxmemory 512mb
maxmemory-policy allkeys-lru
```

2. Adjust timeout settings for long-running tasks:

```python
# In tasks.py
job_timeout='4h'  # Increase for complex tasks
```

### GitHub Polling Optimization

To optimize GitHub polling:

1. Adjust polling interval based on project activity:

```bash
# In config.sh
# Lower value for active projects, higher for less active
POLLING_INTERVAL=900  # 15 minutes
```

2. Use more specific issue labels to reduce processing overhead:

```bash
# In config.sh
GITHUB_ISSUE_LABEL="autonomous-coding,priority"
```

### Claude Code Execution Optimization

To optimize Claude Code execution:

1. Use more specific allowed tools:

```python
# In worker.py
result = run_claude_code_headless(
    analyze_prompt,
    "Bash(gh:issue) Edit"  # More specific tools
)
```

2. Set appropriate timeouts for Claude Code execution:

```python
# Modify run_claude_code_headless to include a timeout
subprocess.run(
    command,
    capture_output=True,
    text=True,
    check=True,
    timeout=7200  # 2 hours
)
```

## Monitoring and Maintenance

### Health Checks

Implement health checks for the autonomous system:

```bash
# Add to autonomous-claude.sh
health_check() {
  log "INFO" "Performing health check..."
  
  # Check Redis connection
  if ! redis-cli ping > /dev/null 2>&1; then
    log "ERROR" "Redis not responding"
    return 1
  fi
  
  # Check worker process
  if [ -f "$PROJECT_PATH/.autonomous-claude/worker.pid" ]; then
    worker_pid=$(cat "$PROJECT_PATH/.autonomous-claude/worker.pid")
    if ! ps -p $worker_pid > /dev/null; then
      log "ERROR" "Worker process not running"
      return 1
    fi
  else
    log "ERROR" "Worker PID file not found"
    return 1
  fi
  
  # Check GitHub access
  if ! gh auth status > /dev/null 2>&1; then
    log "ERROR" "GitHub authentication failed"
    return 1
  fi
  
  log "INFO" "Health check passed"
  return 0
}
```

### Backup and Recovery

Set up backup procedures for important data:

1. Back up task plans:

```bash
# Add to autonomous-claude.sh
backup_task_plans() {
  backup_dir="$PROJECT_PATH/.autonomous-claude/backups/$(date +%Y-%m-%d)"
  mkdir -p "$backup_dir"
  cp -r "$PROJECT_PATH/.autonomous-claude/tasks" "$backup_dir/"
  log "INFO" "Task plans backed up to $backup_dir"
}
```

2. Automate backups with a cron job:

```bash
# Add to crontab
0 0 * * * /path/to/autonomous-claude.sh backup
```

### Log Rotation

Implement log rotation to prevent logs from growing too large:

```bash
# Add to autonomous-claude.sh
rotate_logs() {
  log "INFO" "Rotating logs..."
  find "$PROJECT_PATH/.autonomous-claude/logs" -name "*.log" -mtime +7 -delete
  log "INFO" "Deleted logs older than 7 days"
}
```

## Security Considerations

### GitHub Token Security

Secure your GitHub token:

1. Use a token with minimal required permissions:
   - `repo` scope for private repositories
   - `public_repo` scope for public repositories

2. Store the token securely:
   - Use environment variables
   - Use a secrets manager

3. Rotate the token regularly

### Redis Security

Secure your Redis instance:

1. Set a strong password:

```bash
# In redis.conf
requirepass "strong_password_here"
```

2. Update the Redis URL in the configuration:

```bash
# In config.sh
REDIS_URL="redis://:strong_password_here@localhost:6379"
```

3. Bind Redis to localhost only:

```bash
# In redis.conf
bind 127.0.0.1
```

### File System Security

Limit file system access:

1. Run the worker with restricted permissions:

```bash
# Create a dedicated user
sudo useradd --system autonomous-claude
sudo -u autonomous-claude python3 worker.py
```

2. Restrict the worker to the project directory:

```python
# In worker.py
def run_claude_code_headless(prompt, allowed_tools=None):
    # ...
    os.chdir(os.environ.get('PROJECT_PATH', os.getcwd()))
    # ...
```

## Debugging and Troubleshooting

### Verbose Logging

Enable verbose logging for debugging:

```bash
# In config.sh
DEBUG=true
```

```python
# In worker.py
if os.environ.get('DEBUG', 'false').lower() == 'true':
    logger.setLevel(logging.DEBUG)
```

### Accessing Worker Output

Capture and analyze worker output:

```bash
# Directly access worker stdout
tail -f .autonomous-claude/logs/worker_stdout.log

# Analyze worker logs
grep "ERROR" .autonomous-claude/logs/worker.log
```

### Testing the MCP Server

Test the MCP server independently:

```bash
# Start the MCP server in debug mode
DEBUG=true node ./autonomous-mcp-server/autonomous-mcp-server.js

# Test with Claude Code
claude mcp test autonomous_coding
```

## Upgrade Guide

When upgrading to a new version of Autonomous Claude:

1. Backup your configuration:

```bash
cp -r .autonomous-claude/config.sh .autonomous-claude/config.sh.backup
```

2. Update the main script:

```bash
curl -o autonomous-claude.sh.new https://raw.githubusercontent.com/yourusername/autonomous-claude/main/autonomous-claude.sh
chmod +x autonomous-claude.sh.new
mv autonomous-claude.sh.new autonomous-claude.sh
```

3. Run initialization with the `--update` flag:

```bash
./autonomous-claude.sh init --update
```

4. Review and merge configuration changes:

```bash
diff .autonomous-claude/config.sh.backup .autonomous-claude/config.sh
```

5. Restart the services:

```bash
./autonomous-claude.sh stop
./autonomous-claude.sh start
```