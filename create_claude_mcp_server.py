#!/usr/bin/env python3
# create_claude_mcp_server.py
#
# This script creates a custom MCP server that enables Claude to better interact with GitHub,
# Redis, and the filesystem for autonomous coding workflows.

import os
import sys
import argparse
import json
import shutil
from pathlib import Path

def create_mcp_server_script(output_dir):
    """Create the MCP server script for autonomous coding workflow"""
    
    server_file = os.path.join(output_dir, "autonomous-mcp-server.js")
    
    script_content = """
const { Server } = require("@modelcontextprotocol/sdk/server/index.js");
const { StdioServerTransport } = require("@modelcontextprotocol/sdk/server/stdio.js");
const { exec, spawn } = require("child_process");
const { promisify } = require("util");
const fs = require("fs").promises;
const path = require("path");
const Redis = require("ioredis");
const util = require("util");

// Redis connection
let redis = null;
try {
  redis = new Redis(process.env.REDIS_URL || "redis://localhost:6379");
} catch (error) {
  console.error(`Error connecting to Redis: ${error.message}`);
}

// Create MCP server
const server = new Server(
  { name: "autonomous-coding-tools", version: "1.0.0" },
  {
    capabilities: {
      resources: {
        "project_info": {
          description: "Information about the current project",
          get: async () => {
            try {
              // Get current git info
              const execPromise = promisify(exec);
              const { stdout: gitRoot } = await execPromise("git rev-parse --show-toplevel");
              const projectRoot = gitRoot.trim();
              
              // Get GitHub repo info
              const { stdout: repoInfo } = await execPromise("gh repo view --json nameWithOwner,url,description");
              const repo = JSON.parse(repoInfo);
              
              // Get files in project
              const { stdout: files } = await execPromise("git ls-files");
              const fileList = files.trim().split("\\n").filter(Boolean);
              
              return {
                content: [
                  {
                    type: "text",
                    text: JSON.stringify({
                      projectRoot,
                      repository: repo,
                      fileCount: fileList.length,
                      files: fileList.slice(0, 100), // Limit to first 100 files
                      docsPath: path.join(projectRoot, "docs")
                    })
                  }
                ]
              };
            } catch (error) {
              return {
                isError: true,
                content: [
                  {
                    type: "text",
                    text: `Error getting project info: ${error.message}`
                  }
                ]
              };
            }
          }
        },
        "task_status": {
          description: "Information about the current autonomous coding tasks",
          get: async () => {
            if (!redis) {
              return {
                isError: true,
                content: [
                  {
                    type: "text",
                    text: "Redis not connected. Cannot get task status."
                  }
                ]
              };
            }
            
            try {
              // Get queue info
              const queueName = process.env.REDIS_QUEUE || "autonomous-coding";
              const queueLen = await redis.llen(`rq:queue:${queueName}`);
              const failedCount = await redis.zcard(`rq:failed:${queueName}`);
              
              // Get recent jobs
              const jobKeys = await redis.keys("rq:job:*");
              const jobs = [];
              
              for (let i = 0; i < Math.min(jobKeys.length, 10); i++) {
                const jobKey = jobKeys[i];
                const jobData = await redis.hgetall(jobKey);
                if (jobData) {
                  jobs.push({
                    id: jobKey.replace("rq:job:", ""),
                    status: jobData.status,
                    function: jobData.description,
                    created: new Date(parseInt(jobData.created_at) * 1000).toISOString()
                  });
                }
              }
              
              return {
                content: [
                  {
                    type: "text",
                    text: JSON.stringify({
                      queueName,
                      queueLength: queueLen,
                      failedJobs: failedCount,
                      recentJobs: jobs
                    })
                  }
                ]
              };
            } catch (error) {
              return {
                isError: true,
                content: [
                  {
                    type: "text",
                    text: `Error getting task status: ${error.message}`
                  }
                ]
              };
            }
          }
        }
      },
      tools: {
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
        },
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
        },
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
        },
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
        },
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
        },
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
      }
    }
  }
);

// Add tool handlers
server.setRequestHandler("callTool", async (params) => {
  try {
    if (params.name === "github_search_issues") {
      const { label = "", state = "open", limit = 10 } = params.arguments || {};
      const cmd = `gh issue list --json number,title,url,labels,state,createdAt ${
        label ? `--label "${label}"` : ""
      } --state ${state} --limit ${limit}`;
      
      const { stdout, stderr } = await promisify(exec)(cmd);
      
      if (stderr) {
        return {
          isError: true,
          content: [
            {
              type: "text",
              text: `Error: ${stderr}`
            }
          ]
        };
      }
      
      return {
        content: [
          {
            type: "text",
            text: stdout
          }
        ]
      };
    }
    
    if (params.name === "github_get_issue") {
      const { number } = params.arguments;
      const cmd = `gh issue view ${number} --json number,title,body,labels,assignees,state,createdAt,comments,url`;
      
      const { stdout, stderr } = await promisify(exec)(cmd);
      
      if (stderr) {
        return {
          isError: true,
          content: [
            {
              type: "text",
              text: `Error: ${stderr}`
            }
          ]
        };
      }
      
      return {
        content: [
          {
            type: "text",
            text: stdout
          }
        ]
      };
    }
    
    if (params.name === "github_comment_on_issue") {
      const { number, body } = params.arguments;
      
      // Write body to a temporary file to avoid command line escaping issues
      const tempFile = path.join(os.tmpdir(), `gh-comment-${Date.now()}.md`);
      await fs.writeFile(tempFile, body);
      
      const cmd = `gh issue comment ${number} --body-file "${tempFile}"`;
      
      try {
        const { stdout, stderr } = await promisify(exec)(cmd);
        
        // Clean up temp file
        await fs.unlink(tempFile);
        
        if (stderr) {
          return {
            isError: true,
            content: [
              {
                type: "text",
                text: `Error: ${stderr}`
              }
            ]
          };
        }
        
        return {
          content: [
            {
              type: "text",
              text: `Comment added successfully to issue #${number}`
            }
          ]
        };
      } catch (error) {
        // Try to clean up temp file even if there was an error
        try {
          await fs.unlink(tempFile);
        } catch (e) {
          // Ignore cleanup errors
        }
        
        throw error;
      }
    }
    
    if (params.name === "github_create_pr") {
      const { title, body, head, base = "main" } = params.arguments;
      
      // Write body to a temporary file to avoid command line escaping issues
      const tempFile = path.join(os.tmpdir(), `gh-pr-${Date.now()}.md`);
      await fs.writeFile(tempFile, body);
      
      const cmd = `gh pr create --title "${title}" --body-file "${tempFile}" --head "${head}" --base "${base}"`;
      
      try {
        const { stdout, stderr } = await promisify(exec)(cmd);
        
        // Clean up temp file
        await fs.unlink(tempFile);
        
        if (stderr) {
          return {
            isError: true,
            content: [
              {
                type: "text",
                text: `Error: ${stderr}`
              }
            ]
          };
        }
        
        return {
          content: [
            {
              type: "text",
              text: stdout
            }
          ]
        };
      } catch (error) {
        // Try to clean up temp file even if there was an error
        try {
          await fs.unlink(tempFile);
        } catch (e) {
          // Ignore cleanup errors
        }
        
        throw error;
      }
    }
    
    if (params.name === "queue_task") {
      if (!redis) {
        return {
          isError: true,
          content: [
            {
              type: "text",
              text: "Redis not connected. Cannot queue task."
            }
          ]
        };
      }
      
      const { task_type, issue_number, args = {} } = params.arguments;
      
      try {
        // Add to Redis queue
        const queueName = process.env.REDIS_QUEUE || "autonomous-coding";
        const taskData = {
          task_type,
          issue_number,
          args,
          created_at: Date.now()
        };
        
        // Convert to RQ job format
        // This is a simplified version - in production, you'd use the RQ library properly
        const jobId = `job-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
        await redis.hset(
          `rq:job:${jobId}`,
          "status", "queued",
          "created_at", Math.floor(Date.now() / 1000),
          "description", task_type,
          "data", JSON.stringify(taskData)
        );
        
        await redis.lpush(`rq:queue:${queueName}`, jobId);
        
        return {
          content: [
            {
              type: "text",
              text: `Task queued successfully with job ID: ${jobId}`
            }
          ]
        };
      } catch (error) {
        return {
          isError: true,
          content: [
            {
              type: "text",
              text: `Error queueing task: ${error.message}`
            }
          ]
        };
      }
    }
    
    if (params.name === "run_claude_command") {
      const { command, allowed_tools = "Bash Edit Run Test" } = params.arguments;
      
      try {
        // Get Claude Code path
        const claudeCodePath = process.env.CLAUDE_CODE_PATH || "claude";
        
        // Run Claude Code in headless mode
        const claudeProcess = spawn(
          claudeCodePath, 
          ["-p", command, "--allowedTools", allowed_tools],
          { stdio: ["ignore", "pipe", "pipe"] }
        );
        
        let stdout = "";
        let stderr = "";
        
        claudeProcess.stdout.on("data", (data) => {
          stdout += data.toString();
        });
        
        claudeProcess.stderr.on("data", (data) => {
          stderr += data.toString();
        });
        
        return new Promise((resolve) => {
          claudeProcess.on("close", (code) => {
            if (code !== 0) {
              resolve({
                isError: true,
                content: [
                  {
                    type: "text",
                    text: `Claude Code exited with code ${code}\\n${stderr}`
                  }
                ]
              });
            } else {
              resolve({
                content: [
                  {
                    type: "text",
                    text: stdout
                  }
                ]
              });
            }
          });
        });
      } catch (error) {
        return {
          isError: true,
          content: [
            {
              type: "text",
              text: `Error running Claude Code: ${error.message}`
            }
          ]
        };
      }
    }
    
    return {
      isError: true,
      content: [
        {
          type: "text",
          text: `Unknown tool: ${params.name}`
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
});

// Start server
const transport = new StdioServerTransport();
server.listen(transport);

console.error("Autonomous Coding MCP Server started");
"""
    
    with open(server_file, 'w') as f:
        f.write(script_content.strip())
        
    os.chmod(server_file, 0o755)
    print(f"Created MCP server script at: {server_file}")
    
    return server_file

def create_package_json(output_dir):
    """Create package.json for the MCP server"""
    
    package_file = os.path.join(output_dir, "package.json")
    
    package_content = {
        "name": "autonomous-mcp-server",
        "version": "1.0.0",
        "description": "MCP server for autonomous coding workflows",
        "main": "autonomous-mcp-server.js",
        "type": "commonjs",
        "scripts": {
            "start": "node autonomous-mcp-server.js"
        },
        "dependencies": {
            "@modelcontextprotocol/sdk": "^0.0.5",
            "ioredis": "^5.3.2"
        }
    }
    
    with open(package_file, 'w') as f:
        json.dump(package_content, f, indent=2)
        
    print(f"Created package.json at: {package_file}")
    
    return package_file

def create_readme(output_dir):
    """Create README.md for the MCP server"""
    
    readme_file = os.path.join(output_dir, "README.md")
    
    readme_content = """# Autonomous Coding MCP Server

This MCP (Model Context Protocol) server enables Claude to interact with GitHub, Redis, and the file system for automated coding workflows.

## Features

- GitHub integration (issues, PRs, comments)
- Redis queue management for async tasks
- File system access
- Project analysis capabilities

## Installation

1. Install dependencies:

```bash
npm install
```

2. Start the server:

```bash
node autonomous-mcp-server.js
```

## Configuration

The server uses the following environment variables:

- `REDIS_URL`: Redis connection URL (default: `redis://localhost:6379`)
- `REDIS_QUEUE`: Name of the Redis queue (default: `autonomous-coding`)
- `CLAUDE_CODE_PATH`: Path to Claude Code executable (default: `claude`)

## Usage with Claude

To use this MCP server with Claude, add it to Claude's configuration:

```bash
claude mcp add autonomous_coding node /path/to/autonomous-mcp-server.js
```

Or with Claude Desktop, add it through the UI in Settings > Integrations.

## Available Tools

- `github_search_issues`: Search GitHub issues
- `github_get_issue`: Get detailed information about an issue
- `github_comment_on_issue`: Add a comment to an issue
- `github_create_pr`: Create a pull request
- `queue_task`: Add a task to the Redis queue
- `run_claude_command`: Run a Claude Code command

## Resources

- `project_info`: Information about the current project
- `task_status`: Information about tasks in the queue
"""
    
    with open(readme_file, 'w') as f:
        f.write(readme_content)
        
    print(f"Created README.md at: {readme_file}")
    
    return readme_file

def main():
    parser = argparse.ArgumentParser(description='Create an MCP server for autonomous coding workflows')
    parser.add_argument('--output', '-o', default='./autonomous-mcp-server',
                        help='Output directory for MCP server files')
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = os.path.abspath(args.output)
    os.makedirs(output_dir, exist_ok=True)
    
    # Create MCP server files
    server_file = create_mcp_server_script(output_dir)
    package_file = create_package_json(output_dir)
    readme_file = create_readme(output_dir)
    
    print("\nMCP server files created successfully!")
    print(f"Output directory: {output_dir}")
    print("\nTo install dependencies:")
    print(f"cd {output_dir} && npm install")
    print("\nTo start the server:")
    print(f"node {os.path.basename(server_file)}")
    print("\nTo add to Claude:")
    print(f"claude mcp add autonomous_coding node {server_file}")

if __name__ == "__main__":
    main()
