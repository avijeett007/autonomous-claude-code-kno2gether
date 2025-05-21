# Autonomous Claude Documentation

Welcome to the official documentation for the Autonomous Claude project. This documentation provides comprehensive information about the Autonomous Claude tool, its architecture, installation, usage, and more.

## What's in this Documentation

- [Project Overview](project-overview.md) - Introduction to Autonomous Claude and its key features
- [Architecture](architecture.md) - Detailed explanation of the system architecture and components
- [Installation](installation.md) - Step-by-step guide to installing and setting up Autonomous Claude
- [Usage Guide](usage-guide.md) - How to use Autonomous Claude for various workflows
- [Component Reference](component-reference.md) - Detailed documentation of key files and components
- [API Documentation](api-documentation.md) - Technical documentation for the Redis worker and tasks
- [MCP Server Integration](mcp-server.md) - How to integrate with Claude's MCP servers
- [Deployment Guide](deployment-guide.md) - How to deploy and configure Autonomous Claude
- [Troubleshooting & FAQs](troubleshooting.md) - Solutions to common issues and frequently asked questions

## Quick Start

For a quick start with Autonomous Claude, follow these steps:

1. Install the necessary dependencies:
   ```bash
   npm install -g @anthropic-ai/claude-code
   pip install redis rq rq-dashboard
   ```

2. Initialize your project:
   ```bash
   ./autonomous-claude.sh init
   ```

3. Start the Autonomous Claude service:
   ```bash
   ./autonomous-claude.sh start
   ```

4. Check the status of your services:
   ```bash
   ./autonomous-claude.sh status
   ```

For detailed information about each step, refer to the [Installation](installation.md) and [Usage Guide](usage-guide.md) sections.

## Contributing

If you'd like to contribute to Autonomous Claude, please refer to the [Contributing Guide](contributing.md) for guidelines and best practices.

## License

Autonomous Claude is released under the [MIT License](../LICENSE).