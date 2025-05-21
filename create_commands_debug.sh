#!/bin/bash

# This is a debug script that will show what's happening with the create_claude_commands function

# Print the current script source
echo "Script source: $0"

# Create commands function
create_claude_commands() {
  echo "Creating custom Claude commands..."
  
  # Print project path for debugging
  echo "PROJECT_PATH: $PROJECT_PATH"
  
  # Create commands directory
  mkdir -p "$PROJECT_PATH/.autonomous-claude/commands"
  echo "Created directory: $PROJECT_PATH/.autonomous-claude/commands"
  
  # Create command files
  cat > "$PROJECT_PATH/.autonomous-claude/commands/document-project.md" << EOF
This command will scan through the codebase and generate comprehensive documentation for the project.

Follow these steps:
1. Analyze the structure of the project
2. Generate appropriate documentation based on the project type
3. Create or update documentation files in the docs directory

ARGUMENTS: none
EOF
  
  echo "Created document-project.md"
  
  cat > "$PROJECT_PATH/.autonomous-claude/commands/analyze-github-issue.md" << EOF
This command will analyze a GitHub issue and prepare a detailed plan for implementation.

ARGUMENTS: {issue_number}
EOF
  
  echo "Created analyze-github-issue.md"
}

# Set project path
PROJECT_PATH="$PWD"
echo "Current directory: $PROJECT_PATH"

# Call the function
create_claude_commands

echo "Commands created successfully in $PROJECT_PATH/.autonomous-claude/commands/"
ls -la "$PROJECT_PATH/.autonomous-claude/commands/"
