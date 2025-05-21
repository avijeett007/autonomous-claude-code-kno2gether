# Installation Guide

This guide provides step-by-step instructions for installing and setting up Autonomous Claude.

## Prerequisites

Autonomous Claude currently requires:

- **Operating System**: macOS (with Homebrew)
- **Dependencies**:
  - Node.js and npm (for Claude Code CLI)
  - Python 3.6+
  - Git and GitHub CLI
  - Redis

### Checking Requirements

Before installation, make sure your system meets the requirements:

```bash
# Check for required tools
python3 --version  # Should be 3.6 or higher
npm --version      # Should be installed
gh --version       # GitHub CLI
redis-cli --version # Redis client
```

## Installation Methods

There are two ways to install Autonomous Claude:

1. **Using the Installer Script** (Recommended)
2. **Manual Installation**

## Option 1: Using the Installer Script

The installer script automates the entire setup process, including installing dependencies and configuring the environment.

### Running the Installer

```bash
# Download the installer script
curl -o autonomous_claude_installer.py https://raw.githubusercontent.com/yourusername/autonomous-claude/main/autonomous_claude_installer.py

# Make it executable
chmod +x autonomous_claude_installer.py

# Run the installer
./autonomous_claude_installer.py
```

The installer will:
- Check system requirements
- Install missing dependencies (GitHub CLI, Redis, Claude Code)
- Set up GitHub authentication
- Configure Claude Code
- Install the Autonomous Claude utility
- Create a symlink for easy access

Follow the prompts to complete the installation.

## Option 2: Manual Installation

If you prefer to install manually or if the installer doesn't work for your environment, follow these steps:

### Step 1: Install Dependencies

```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install GitHub CLI
brew install gh

# Install Redis
brew install redis
brew services start redis

# Install Claude Code CLI
npm install -g @anthropic-ai/claude-code

# Install Python dependencies
pip install redis rq rq-dashboard
```

### Step 2: Get the Autonomous Claude Scripts

```bash
# Clone the repository
git clone https://github.com/yourusername/autonomous-claude.git

# Make the main script executable
chmod +x autonomous-claude/autonomous-claude.sh

# Create a symlink (optional)
ln -s "$(pwd)/autonomous-claude/autonomous-claude.sh" /usr/local/bin/autonomous-claude
```

### Step 3: Authenticate with GitHub

```bash
# Log in to GitHub
gh auth login
```

Follow the prompts to authenticate with GitHub.

## Project Setup

After installing Autonomous Claude, you need to set up each project to use it:

### Initialize a Project

Navigate to your project directory and initialize it:

```bash
cd /path/to/your/project
autonomous-claude init
```

This will:
- Create necessary directories (.autonomous-claude, .claude/commands)
- Set up a Python virtual environment
- Create configuration files
- Configure custom Claude commands

### Configure the Project

Edit the configuration file to match your project's needs:

```bash
# Edit the configuration file
nano .autonomous-claude/config.sh
```

Key configuration options:

- `PROJECT_PATH`: Path to your project directory
- `GITHUB_REPO`: Your GitHub repository (username/repo)
- `GITHUB_ISSUE_LABEL`: Label to identify issues for autonomous processing
- `POLLING_INTERVAL`: How often to check for new issues (in seconds)
- `REDIS_URL`: Redis connection URL
- `REDIS_QUEUE`: Name of the Redis queue

### Test the Setup

Verify that everything is working:

```bash
# Check the status
autonomous-claude status

# Generate project documentation
autonomous-claude docs
```

## Installing MCP Servers (Optional)

For enhanced capabilities, you can install the custom MCP server:

```bash
# Create the MCP server
python create_claude_mcp_server.py --output ./autonomous-mcp-server

# Install dependencies
cd ./autonomous-mcp-server && npm install

# Start the server
node autonomous-mcp-server.js
```

To add the MCP server to Claude Code:

```bash
claude mcp add autonomous_coding node /path/to/autonomous-mcp-server.js
```

## Installation Verification

To verify that your installation is working correctly:

1. Check the services status:
   ```bash
   autonomous-claude status
   ```

2. Start the services:
   ```bash
   autonomous-claude start
   ```

3. Open the dashboard:
   ```bash
   # The dashboard should be available at http://localhost:9181
   open http://localhost:9181
   ```

4. Try generating documentation:
   ```bash
   autonomous-claude docs
   ```

## Troubleshooting Installation

If you encounter issues during installation:

### Redis Connection Problems

```bash
# Check if Redis is running
redis-cli ping

# Start Redis if it's not running
brew services start redis
```

### GitHub Authentication Issues

```bash
# Check GitHub authentication status
gh auth status

# Re-authenticate if needed
gh auth login
```

### Claude Code Installation Issues

```bash
# Check Claude Code installation
claude --version

# Reinstall if needed
npm install -g @anthropic-ai/claude-code
```

### Path Issues

If the `autonomous-claude` command is not found:

```bash
# Add symlink manually
sudo ln -s /path/to/autonomous-claude.sh /usr/local/bin/autonomous-claude

# Or use the full path
/path/to/autonomous-claude.sh status
```

For more detailed troubleshooting, see the [Troubleshooting](troubleshooting.md) section.