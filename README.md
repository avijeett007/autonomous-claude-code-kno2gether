# Autonomous Coding with Claude Code

This utility creates an autonomous coding system using Claude Code in headless mode. It monitors GitHub issues and automates the entire development process with minimal human intervention.

## Key Features

- **Automatic GitHub Issue Monitoring**: Continuously polls for new issues with a specified label
- **Headless Claude Code Operation**: Runs Claude Code non-interactively for each step of the workflow
- **Asynchronous Task Processing**: Uses Redis Queue for managing tasks
- **MCP Server Integration**: Support for GitHub MCP server and other custom MCP servers
- **Project Documentation Generation**: Automatically generates and updates documentation
- **Web Dashboard**: Real-time monitoring of task status via RQ Dashboard

## Requirements

- macOS (with Homebrew)
- Claude Code CLI (`npm install -g @anthropic-ai/claude-code`)
- GitHub CLI (`gh`)
- Python 3
- Redis

## Installation

1. Download the `autonomous-claude.sh` script to your system
2. Make it executable: `chmod +x autonomous-claude.sh`
3. Place it somewhere in your PATH or create a symlink: `ln -s /path/to/autonomous-claude.sh /usr/local/bin/autonomous-claude`

## Usage

### Initialize a Project

```bash
cd /path/to/your/project
autonomous-claude init
```

This will:
- Create necessary directories and configuration
- Set up Claude Code with `/init` command if needed
- Configure custom Claude commands for the workflow
- Set up MCP servers if specified in the config

### Start the Service

```bash
autonomous-claude start
```

This will:
- Check all requirements
- Start a Redis worker for processing tasks
- Start the RQ dashboard for monitoring
- Begin polling for GitHub issues with the designated label

### Generate Documentation

```bash
autonomous-claude docs
```

Triggers Claude Code to scan through the codebase and generate comprehensive documentation.

### Check Status

```bash
autonomous-claude status
```

Shows the status of all components, including worker processes, Redis, and task queue.

### Stop the Service

```bash
autonomous-claude stop
```

Stops all running services and processes.

## Workflow

1. **Preparation**:
   - The utility initializes the project with Claude Code
   - It sets up custom Claude commands for specific tasks
   - Redis worker starts to process tasks asynchronously

2. **Issue Monitoring**:
   - The system polls GitHub for issues with the label specified in config
   - When a new issue is found, it's added to the Redis queue

3. **Analysis Phase**:
   - Claude Code runs in headless mode to analyze the issue
   - It researches the code, checks online references via MCP
   - It creates a detailed implementation plan
   - The plan is saved to `.autonomous-claude/tasks/[issue-number]-plan.md`

4. **Implementation Phase**:
   - Claude Code runs in headless mode to implement the solution
   - It creates the appropriate branch, makes code changes
   - It updates documentation and writes tests
   - It commits changes and creates a pull request

5. **Human Review**:
   - The human checks the GitHub issue for Claude's comment
   - The human reviews the PR and merges it if appropriate

## Configuration

Configuration is stored in `.autonomous-claude/config.sh` and includes:

- Project paths and GitHub repository details
- Polling interval for checking GitHub issues
- Redis configuration
- MCP server settings

You can edit this file to customize the behavior of the autonomous system.

## MCP Server Integration

To enable the GitHub MCP server, add the following to your config.sh:

```bash
MCP_SERVERS_ENABLED=true
MCP_SERVER_GITHUB="docker run -i --rm -e GITHUB_PERSONAL_ACCESS_TOKEN=\$GITHUB_TOKEN ghcr.io/github/github-mcp-server"
```

You can add other MCP servers similarly. The utility will configure Claude Code to use these servers.

## Adding Custom Claude Commands

The utility creates several custom Claude commands during initialization:

1. `/project:document-project` - Generates comprehensive documentation
2. `/project:analyze-github-issue [issue-number]` - Analyzes an issue and creates a plan
3. `/project:implement-github-issue [issue-number]` - Implements a solution based on the plan

You can add more custom commands by placing Markdown files in `.claude/commands/` directory.

## Logging

Logs are stored in `.autonomous-claude/logs/` with daily rotation. You can view recent logs with:

```bash
tail -f .autonomous-claude/logs/$(date +%Y-%m-%d).log
```

The RQ Dashboard (http://localhost:9181) also provides a web interface for monitoring task status.

## Running as a System Service

To run as a macOS system service, create a launchd plist:

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
</dict>
</plist>
EOF

launchctl load ~/Library/LaunchAgents/com.user.autonomous-claude.plist
```

## Security Notes

- This utility runs commands on your machine through Claude Code
- Make sure to review the plans before implementation
- Consider running in a restricted environment for additional security
- Use specific GitHub scopes for the GitHub CLI authentication

## Troubleshooting

### Common Issues

- **Claude Code not found**: Ensure Claude Code is installed and in your PATH
- **Redis connection error**: Check if Redis is running with `redis-cli ping`
- **GitHub authentication error**: Run `gh auth login` to authenticate
- **Worker not processing tasks**: Check worker logs in `.autonomous-claude/logs/`

### Debugging

Enable more verbose logging by setting `DEBUG=true` in your config file.
