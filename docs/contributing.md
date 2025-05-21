# Contributing Guide

This document provides guidelines for contributing to the Autonomous Claude project. We welcome contributions in many forms, including bug reports, feature requests, documentation improvements, and code changes.

## Getting Started

### Prerequisites

Before you begin, ensure you have:

1. A GitHub account
2. Git installed on your machine
3. Node.js and npm (for Claude Code)
4. Python 3.6+
5. Basic knowledge of Bash, Python, and JavaScript
6. Familiarity with the Autonomous Claude architecture (see [Architecture](architecture.md))

### Setting Up the Development Environment

1. **Fork the Repository**:
   Visit the Autonomous Claude GitHub repository and click the "Fork" button to create your own copy.

2. **Clone Your Fork**:
   ```bash
   git clone https://github.com/your-username/autonomous-claude.git
   cd autonomous-claude
   ```

3. **Initialize the Project**:
   ```bash
   ./autonomous-claude.sh init
   ```

4. **Set Up Development Dependencies**:
   ```bash
   # Install Python development dependencies
   pip install -r requirements-dev.txt  # If available
   
   # Install Node.js dependencies for MCP server
   cd autonomous-mcp-server
   npm install
   cd ..
   ```

## Contribution Workflow

### Identifying Areas to Contribute

You can contribute to Autonomous Claude in several ways:

1. **Fix Bugs**: Check the issue tracker for bugs you can fix.
2. **Add Features**: Implement new features that would be useful for the project.
3. **Improve Documentation**: Enhance the documentation for clarity and completeness.
4. **Enhance Tests**: Add or improve tests for better code coverage.
5. **Optimize Performance**: Identify and fix performance bottlenecks.

### Making Changes

1. **Create a New Branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```
   or
   ```bash
   git checkout -b fix/issue-number-bug-description
   ```

2. **Make Your Changes**:
   - Follow the coding style of the project
   - Write clear, maintainable code
   - Add appropriate comments and documentation
   - Update documentation if necessary

3. **Test Your Changes**:
   ```bash
   # Run tests if available
   ./run_tests.sh  # Replace with actual test command
   
   # Manual testing
   ./autonomous-claude.sh status
   ./autonomous-claude.sh start
   ```

4. **Commit Your Changes**:
   ```bash
   git add .
   git commit -m "Descriptive commit message"
   ```
   
   Follow these commit message guidelines:
   - Use the present tense ("Add feature" not "Added feature")
   - Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
   - Reference issues and pull requests where appropriate
   - First line should be 50 characters or less
   - Subsequent lines should be wrapped at 72 characters

5. **Push to Your Fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request**:
   - Go to the original Autonomous Claude repository
   - Click "New Pull Request"
   - Select "compare across forks"
   - Select your fork and branch
   - Fill out the pull request template
   - Submit the pull request

### Code Review Process

After submitting a pull request:

1. Maintainers will review your code
2. They may request changes or improvements
3. Address any feedback by making additional commits to your branch
4. Once approved, a maintainer will merge your pull request

## Development Guidelines

### Code Style

For Bash scripts:
- Follow [Google's Shell Style Guide](https://google.github.io/styleguide/shellguide.html)
- Use 2-space indentation
- Use lowercase for function and variable names
- Add comments for complex logic

For Python code:
- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Use 4-space indentation
- Use snake_case for function and variable names
- Use docstrings for functions and classes

For JavaScript code (MCP server):
- Follow [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript)
- Use 2-space indentation
- Use camelCase for variables and functions
- Use JSDoc comments for functions

### Testing

When adding new features or fixing bugs:

1. **Write Tests First**: Follow a test-driven development approach when possible
2. **Test Edge Cases**: Consider various inputs and error conditions
3. **Manual Testing**: Test your changes with real GitHub issues and Claude Code

### Documentation

When making changes that affect user-facing functionality:

1. Update the relevant documentation in `docs/`
2. Update the README.md if necessary
3. Add comments to code explaining "why" not just "what"
4. Update any usage examples

## Working with Issues

### Reporting Bugs

When reporting bugs:

1. Check if the bug is already reported
2. Use the bug report template if available
3. Include:
   - Steps to reproduce
   - Expected behavior
   - Actual behavior
   - System information
   - Screenshots if applicable
   - Logs if available

### Requesting Features

When requesting features:

1. Check if the feature is already requested
2. Use the feature request template if available
3. Explain:
   - What the feature should do
   - Why it would be useful
   - Any alternatives you've considered
   - Example use cases

### Working on Issues

When working on an issue:

1. Comment on the issue expressing your interest
2. Wait for assignment or confirmation from a maintainer
3. Reference the issue in your pull request

## Development Tools

### Useful Commands

```bash
# Run the worker in debug mode
DEBUG=true python .autonomous-claude/worker.py

# Test the MCP server
cd autonomous-mcp-server
node autonomous-mcp-server.js

# Monitor logs
tail -f .autonomous-claude/logs/worker.log

# Check status
./autonomous-claude.sh status
```

### Debugging Tips

1. **Logging**: Add detailed logging statements for debugging
   ```python
   logger.debug(f"Variable value: {variable}")
   ```

2. **Redis Inspection**: Inspect Redis data
   ```bash
   redis-cli
   > KEYS *
   > GET key_name
   ```

3. **Testing Claude Commands**: Test custom commands directly
   ```bash
   claude -p "/project:document-project"
   ```

## Release Process

Autonomous Claude follows semantic versioning. The release process involves:

1. **Prepare Release**:
   - Update version number
   - Update changelog
   - Ensure all tests pass

2. **Create Release Branch**:
   ```bash
   git checkout -b release/v1.0.0
   ```

3. **Create Pull Request**: Create a PR from the release branch to main

4. **Tag Release**: After merge, tag the release
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

5. **Create GitHub Release**: Document changes and provide installation instructions

## Community Guidelines

### Code of Conduct

We expect all contributors to:

- Be respectful and inclusive
- Be patient with other community members
- Accept constructive criticism
- Focus on what is best for the community
- Show empathy towards other community members

### Communication Channels

- **GitHub Issues**: For bug reports, feature requests, and specific discussion
- **Pull Requests**: For code contributions and reviews
- **Discussions**: For general questions and ideas

### Recognition

All contributors will be recognized in the project's README or CONTRIBUTORS file.

## License

By contributing to Autonomous Claude, you agree that your contributions will be licensed under the same license as the project (generally the MIT License).

## Thank You!

Your contributions help make Autonomous Claude better for everyone. We appreciate your time and effort!