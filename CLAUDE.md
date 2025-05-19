# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Setup and Installation

```bash
# Install development dependencies
npm install -g @anthropic-ai/claude-code  # Claude Code CLI
pip install redis rq rq-dashboard         # Python packages for Redis queue

# Project setup
./autonomous-claude.sh init               # Initialize project structure
```

### Running the Service

```bash
# Start autonomous coding service
./autonomous-claude.sh start              # Start all services
./autonomous-claude.sh stop               # Stop all services
./autonomous-claude.sh status             # Check service status
./autonomous-claude.sh dashboard          # Start RQ dashboard
./autonomous-claude.sh docs               # Generate documentation
```

### Custom MCP Server (optional)

```bash
# Create custom MCP server
python create_claude_mcp_server.py --output ./autonomous-mcp-server
cd ./autonomous-mcp-server && npm install
node autonomous-mcp-server.js
```

## Architecture

### Core Components

1. **Main Shell Script (`autonomous-claude.sh`)**: 
   - Orchestrates the whole system
   - Handles initialization, service start/stop
   - Manages GitHub issue polling

2. **Redis Queue System**:
   - Background worker process (`worker.py`)
   - Task management (`tasks.py`)
   - Handles async processing of GitHub issues

3. **Headless Claude Code**:
   - Runs in non-interactive mode via worker
   - Executes custom commands for analysis and implementation

4. **Custom Claude Commands**:
   - `/project:analyze-github-issue` - Analyzes issues and creates plans
   - `/project:implement-github-issue` - Implements solutions based on plans
   - `/project:document-project` - Generates documentation

5. **MCP Server Integration** (Optional):
   - Custom MCP server for GitHub and Redis integration
   - Provides tools for Claude to interact with external services

### Data Flow

1. Service polls GitHub for issues with specific label
2. Issues are added to Redis queue
3. Worker processes queue, runs Claude Code headless
4. Claude analyzes issue and creates plan
5. Claude implements solution and creates PR
6. Human reviews PR and merges if appropriate

### Directory Structure

- `.autonomous-claude/` - Configuration and runtime files
  - `tasks/` - Plans for issues
  - `logs/` - Log files
  - `venv/` - Python virtual environment
- `.claude/commands/` - Custom Claude commands
- `docs/` - Generated documentation

### Configuration

Project settings are stored in `.autonomous-claude/config.sh` with the following parameters:
- Project paths and repo details
- Polling interval
- Redis configuration
- MCP server settings