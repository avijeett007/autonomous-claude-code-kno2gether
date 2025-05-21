# MCP Server Integration

This document explains how Autonomous Claude integrates with Model Context Protocol (MCP) servers to enhance Claude's capabilities when working with GitHub, Redis, and other external systems.

## What is the Model Context Protocol (MCP)?

The Model Context Protocol (MCP) is a standard developed by Anthropic that allows Claude to interact with external tools and services. MCP servers provide specific capabilities to Claude, enabling it to access external APIs, databases, and services in a secure and controlled manner.

In the context of Autonomous Claude, MCP servers are used to provide enhanced capabilities for:
- GitHub issue and pull request management
- Redis queue integration
- Project information retrieval
- Task management

## Custom MCP Server

Autonomous Claude includes a custom MCP server for GitHub and Redis integration. This server is defined in the `create_claude_mcp_server.py` script and can be built and run separately.

### Creating the MCP Server

To create the custom MCP server:

```bash
python create_claude_mcp_server.py --output ./autonomous-mcp-server
cd ./autonomous-mcp-server
npm install
```

This creates a Node.js-based MCP server with the following components:
- `autonomous-mcp-server.js`: Main server script
- `package.json`: Node.js package definition
- `README.md`: Documentation

### Running the MCP Server

To run the MCP server:

```bash
cd ./autonomous-mcp-server
node autonomous-mcp-server.js
```

### Registering with Claude Code

To register the MCP server with Claude Code:

```bash
claude mcp add autonomous_coding node /path/to/autonomous-mcp-server.js
```

## MCP Server Capabilities

### Resources

The MCP server provides the following resources that Claude can access:

#### project_info

```javascript
"project_info": {
  description: "Information about the current project",
  get: async () => {
    // Implementation...
  }
}
```

This resource provides information about the current project, including:
- Project root directory
- GitHub repository details
- List of files in the project
- Documentation path

**Example Usage**:
```
Claude> What files are in this project?
[Claude uses the project_info resource to get file information]
```

#### task_status

```javascript
"task_status": {
  description: "Information about the current autonomous coding tasks",
  get: async () => {
    // Implementation...
  }
}
```

This resource provides information about tasks in the Redis queue, including:
- Queue length
- Failed job count
- Recent jobs and their status

**Example Usage**:
```
Claude> What tasks are currently in the queue?
[Claude uses the task_status resource to get queue information]
```

### Tools

The MCP server provides the following tools that Claude can use:

#### github_search_issues

```javascript
"github_search_issues": {
  description: "Search GitHub issues in the current repository",
  parameters: {
    type: "object",
    properties: {
      label: {
        type: "string",
        description: "Issue label to filter by"
      },
      state: {
        type: "string",
        description: "Issue state (open, closed, all)",
        default: "open"
      },
      limit: {
        type: "integer",
        description: "Maximum number of issues to return",
        default: 10
      }
    },
    required: []
  }
}
```

This tool allows Claude to search for GitHub issues in the current repository with optional filtering by label, state, and limit.

**Example Usage**:
```
Claude> Show me open issues with the "bug" label
[Claude uses the github_search_issues tool to find matching issues]
```

#### github_get_issue

```javascript
"github_get_issue": {
  description: "Get detailed information about a GitHub issue",
  parameters: {
    type: "object",
    properties: {
      number: {
        type: "integer",
        description: "Issue number"
      }
    },
    required: ["number"]
  }
}
```

This tool allows Claude to get detailed information about a specific GitHub issue, including its title, body, labels, assignees, and comments.

**Example Usage**:
```
Claude> Tell me about issue #123
[Claude uses the github_get_issue tool to get detailed information]
```

#### github_comment_on_issue

```javascript
"github_comment_on_issue": {
  description: "Add a comment to a GitHub issue",
  parameters: {
    type: "object",
    properties: {
      number: {
        type: "integer",
        description: "Issue number"
      },
      body: {
        type: "string",
        description: "Comment body in Markdown format"
      }
    },
    required: ["number", "body"]
  }
}
```

This tool allows Claude to add a comment to a GitHub issue.

**Example Usage**:
```
Claude> Comment on issue #123 with "I'm currently analyzing this issue"
[Claude uses the github_comment_on_issue tool to add a comment]
```

#### github_create_pr

```javascript
"github_create_pr": {
  description: "Create a GitHub pull request",
  parameters: {
    type: "object",
    properties: {
      title: {
        type: "string",
        description: "Pull request title"
      },
      body: {
        type: "string",
        description: "Pull request body in Markdown format"
      },
      head: {
        type: "string",
        description: "Head branch name"
      },
      base: {
        type: "string",
        description: "Base branch name (usually main or master)",
        default: "main"
      }
    },
    required: ["title", "body", "head"]
  }
}
```

This tool allows Claude to create a GitHub pull request.

**Example Usage**:
```
Claude> Create a pull request from branch "feature/123" to "main" with title "Fix bug #123"
[Claude uses the github_create_pr tool to create a PR]
```

#### queue_task

```javascript
"queue_task": {
  description: "Add a task to the Redis queue for asynchronous processing",
  parameters: {
    type: "object",
    properties: {
      task_type: {
        type: "string",
        description: "Type of task (document_project, process_issue, etc.)"
      },
      issue_number: {
        type: "integer",
        description: "GitHub issue number (if applicable)"
      },
      args: {
        type: "object",
        description: "Additional arguments for the task"
      }
    },
    required: ["task_type"]
  }
}
```

This tool allows Claude to add tasks to the Redis queue for asynchronous processing.

**Example Usage**:
```
Claude> Queue a task to process issue #123
[Claude uses the queue_task tool to add a task to the queue]
```

#### run_claude_command

```javascript
"run_claude_command": {
  description: "Run a Claude Code command in headless mode",
  parameters: {
    type: "object",
    properties: {
      command: {
        type: "string",
        description: "Command to run (e.g., /project:analyze-github-issue 123)"
      },
      allowed_tools: {
        type: "string",
        description: "Comma-separated list of allowed tools",
        default: "Bash Edit Run Test"
      }
    },
    required: ["command"]
  }
}
```

This tool allows Claude to run Claude Code commands in headless mode.

**Example Usage**:
```
Claude> Run the command to analyze issue #123
[Claude uses the run_claude_command tool to execute a Claude Code command]
```

## Configuring MCP Integration

The MCP server integration is configured in the `.autonomous-claude/config.sh` file:

```bash
# MCP servers
MCP_SERVERS_ENABLED=true
# Add any custom MCP servers here
# Example: MCP_SERVER_GITHUB="docker run -i --rm -e GITHUB_PERSONAL_ACCESS_TOKEN=$GITHUB_TOKEN ghcr.io/github/github-mcp-server"
```

To enable the MCP server, set `MCP_SERVERS_ENABLED` to `true`. You can also define specific MCP servers in this file.

## Setting Up the GitHub MCP Server

In addition to the custom MCP server, you can also use the official GitHub MCP server:

```bash
# In config.sh
MCP_SERVER_GITHUB="docker run -i --rm -e GITHUB_PERSONAL_ACCESS_TOKEN=$GITHUB_TOKEN ghcr.io/github/github-mcp-server"
```

The GitHub MCP server provides enhanced GitHub functionality beyond what's available in the custom MCP server.

## MCP Server Authentication

The MCP server uses authentication mechanisms for the external services it interacts with:

### GitHub Authentication

The MCP server uses the GitHub CLI's authentication for GitHub operations. Before using the MCP server, make sure you're authenticated with GitHub:

```bash
gh auth login
```

### Redis Authentication

The MCP server connects to Redis using the URL specified in the environment:

```javascript
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
```

If your Redis instance requires authentication, include the password in the Redis URL:

```
redis://username:password@localhost:6379
```

## Extending the MCP Server

You can extend the MCP server with additional capabilities by modifying the `autonomous-mcp-server.js` file.

### Adding a New Resource

To add a new resource:

```javascript
// In capabilities.resources
"my_custom_resource": {
  description: "Description of my custom resource",
  get: async () => {
    try {
      // Implementation...
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(result)
          }
        ]
      };
    } catch (error) {
      return {
        isError: true,
        content: [
          {
            type: "text",
            text: `Error: ${error.message}`
          }
        ]
      };
    }
  }
}
```

### Adding a New Tool

To add a new tool:

```javascript
// In capabilities.tools
"my_custom_tool": {
  description: "Description of my custom tool",
  parameters: {
    type: "object",
    properties: {
      param1: {
        type: "string",
        description: "Description of param1"
      },
      param2: {
        type: "integer",
        description: "Description of param2"
      }
    },
    required: ["param1"]
  }
}

// In setRequestHandler
if (params.name === "my_custom_tool") {
  const { param1, param2 } = params.arguments;
  
  // Tool implementation...
  
  return {
    content: [
      {
        type: "text",
        text: result
      }
    ]
  };
}
```

## Security Considerations

When using MCP servers, consider the following security issues:

1. **GitHub Token Security**: The GitHub MCP server requires a personal access token, which should be kept secure.

2. **Redis Security**: Ensure your Redis instance is properly secured, especially if it contains sensitive information.

3. **Command Execution**: The `run_claude_command` tool allows Claude to execute commands, which should be restricted to safe operations.

4. **File Access**: The MCP server has access to the file system, which should be restricted to the project directory.

## Troubleshooting MCP Integration

### Common Issues

#### MCP Server Not Running

If the MCP server is not running, you'll see an error when trying to access its tools:

```
Tool 'github_search_issues' is not available. Make sure the MCP server is running.
```

To fix this, start the MCP server:

```bash
cd ./autonomous-mcp-server
node autonomous-mcp-server.js
```

#### GitHub Authentication Failed

If GitHub authentication fails, you'll see an error like:

```
Error: Error running command: gh issue list
```

To fix this, authenticate with GitHub:

```bash
gh auth login
```

#### Redis Connection Failed

If Redis connection fails, you'll see an error like:

```
Error connecting to Redis: Error: getaddrinfo ENOTFOUND localhost
```

To fix this, ensure Redis is running:

```bash
redis-cli ping
```

If Redis is not running, start it:

```bash
brew services start redis
```