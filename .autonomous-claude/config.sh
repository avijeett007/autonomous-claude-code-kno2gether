#!/usr/bin/env bash
# Autonomous Claude configuration

# Project settings
PROJECT_PATH="/Users/avijitsarkar/personal_projects/autonomous-claude"
DOCS_PATH="/Users/avijitsarkar/personal_projects/autonomous-claude/docs"
GITHUB_REPO=""
GITHUB_ISSUE_LABEL="autonomous-coding"

# Operation settings
POLLING_INTERVAL=300
REDIS_URL="redis://localhost:6379"
REDIS_QUEUE="autonomous-coding"

# Paths
CLAUDE_CODE_PATH="/usr/local/bin/claude"

# MCP servers
MCP_SERVERS_ENABLED=true
# Add any custom MCP servers here
# Example: MCP_SERVER_GITHUB="docker run -i --rm -e GITHUB_PERSONAL_ACCESS_TOKEN=$GITHUB_TOKEN ghcr.io/github/github-mcp-server"
