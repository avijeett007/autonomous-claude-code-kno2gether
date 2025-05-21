# Project Overview

Autonomous Claude is a powerful utility that creates an autonomous coding system using Claude Code in headless mode. It's designed to monitor GitHub issues and automate the entire development process with minimal human intervention.

## Introduction

Modern software development requires significant human effort to coordinate between issue tracking, coding, testing, and documentation. Autonomous Claude aims to reduce this burden by automating many of these tasks using Anthropic's Claude Code AI assistant in a non-interactive, automated workflow.

The system continuously monitors GitHub issues with a specified label, analyzes them, creates implementation plans, and even generates pull requests with solutions - all with minimal human intervention. It handles everything from understanding the requirements to implementing the solution and creating proper documentation.

## Key Features

### Automatic GitHub Issue Monitoring

Autonomous Claude continuously polls your GitHub repository for new issues with a specified label (default: `autonomous-coding`). When it finds a relevant issue, it adds it to a processing queue and begins the automated workflow.

### Headless Claude Code Operation

The system runs Claude Code non-interactively for each step of the workflow. Claude analyzes issues, creates detailed implementation plans, writes code, and generates documentation without requiring constant user interaction.

### Asynchronous Task Processing

Autonomous Claude uses Redis Queue (RQ) for managing tasks asynchronously. This allows the system to handle multiple issues in parallel and ensures that long-running tasks don't block the main process.

### MCP Server Integration

The system supports integration with the Model Context Protocol (MCP) servers, including a custom GitHub MCP server that allows Claude to interact directly with GitHub APIs. This enables more powerful interactions with external systems.

### Project Documentation Generation

Autonomous Claude can automatically generate and update project documentation based on the current state of the codebase. This ensures that documentation stays in sync with the code.

### Web Dashboard

The system includes a real-time monitoring dashboard powered by RQ Dashboard. This allows you to track the status of tasks, view logs, and monitor the performance of the autonomous system.

## Use Cases

Autonomous Claude is particularly useful for:

1. **Routine Bug Fixes**: Automating the analysis and resolution of common bugs
2. **Feature Implementations**: Developing straightforward features based on clear requirements
3. **Documentation Updates**: Keeping documentation in sync with code changes
4. **Refactoring Tasks**: Performing code cleanup and optimization
5. **Testing Improvements**: Adding or updating tests based on existing code

## System Requirements

Autonomous Claude currently supports:

- **Operating System**: macOS (with Homebrew)
- **Dependencies**:
  - Claude Code CLI
  - GitHub CLI
  - Python 3
  - Redis
  - RQ (Redis Queue)

## Getting Started

To get started with Autonomous Claude, follow these steps:

1. Install the necessary dependencies
2. Initialize your project with `autonomous-claude.sh init`
3. Configure your project settings in `.autonomous-claude/config.sh`
4. Start the autonomous system with `autonomous-claude.sh start`

For more detailed installation and usage instructions, see the [Installation](installation.md) and [Usage Guide](usage-guide.md) sections.

## Architecture Overview

Autonomous Claude is built on several key components:

1. **Main Shell Script**: Orchestrates the entire system
2. **Redis Queue System**: Handles asynchronous task processing
3. **Headless Claude Code**: Performs the actual analysis and implementation
4. **Custom Claude Commands**: Extends Claude's capabilities for this workflow
5. **MCP Server Integration**: Provides additional tools for external system interaction

For a more detailed explanation of the system architecture, see the [Architecture](architecture.md) section.