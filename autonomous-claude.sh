#!/usr/bin/env bash
# autonomous-claude.sh
# 
# A utility for running autonomous coding workflows with Claude Code in headless mode
# This will monitor GitHub issues and automate the entire development workflow
# with minimal human intervention

set -e

# ===== Configuration =====
# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default settings (can be overridden in a config file)
POLLING_INTERVAL=300  # Default: check every 5 minutes
PROJECT_PATH=$(pwd)
DOCS_PATH="$PROJECT_PATH/docs"
GITHUB_REPO=""
GITHUB_ISSUE_LABEL="autonomous-coding"
CLAUDE_CODE_PATH=$(which claude || echo "")
LOG_FILE="$PROJECT_PATH/.autonomous-claude/logs/$(date +%Y-%m-%d).log"
CONFIG_FILE="$PROJECT_PATH/.autonomous-claude/config.sh"
REDIS_URL="redis://localhost:6379"
REDIS_QUEUE="autonomous-coding"
PR_REVIEW_ENABLED=true
PR_AUTO_REVIEW=true  # Auto-review PR after creation
PR_AUTO_REVIEW_DELAY=30  # Delay in seconds before auto-review
PR_REVIEW_MAX_RETRIES=3  # Maximum number of retry attempts for PR reviews
PR_REVIEW_RETRY_DELAY=60  # Initial delay in seconds between retry attempts
PR_UPDATE_DETECTION=true  # Monitor PRs for updates and trigger re-reviews
MIN_REREVIEW_HOURS=24  # Minimum hours between re-reviews
REVIEW_ONLY_OWN_PRS=true  # Only review PRs created by this system
GITHUB_USERNAME=""

# ===== Helper Functions =====

log() {
  local level=$1
  local message=$2
  local color=$NC
  
  case $level in
    "INFO") color=$GREEN ;;
    "WARNING") color=$YELLOW ;;
    "ERROR") color=$RED ;;
    "DEBUG") color=$BLUE ;;
  esac
  
  # Format timestamp
  local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
  
  # Print to console
  echo -e "${color}[$timestamp] [$level] $message${NC}"
  
  # Ensure log directory exists
  mkdir -p "$(dirname "$LOG_FILE")"
  
  # Write to log file
  echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

check_requirements() {
  log "INFO" "Checking required dependencies..."
  
  # Check for Claude Code
  if [ -z "$CLAUDE_CODE_PATH" ]; then
    CLAUDE_CODE_PATH=$(which claude 2>/dev/null || echo "")
    if [ -z "$CLAUDE_CODE_PATH" ]; then
      log "ERROR" "Claude Code CLI not found. Please install it with 'npm install -g @anthropic-ai/claude-code'"
      exit 1
    fi
  fi
  log "INFO" "Using Claude Code at: $CLAUDE_CODE_PATH"
  
  # Check for Redis
  if ! which redis-cli > /dev/null; then
    log "WARNING" "Redis CLI not found. Attempting to install Redis..."
    if [ "$(uname)" == "Darwin" ]; then
      brew install redis || {
        log "ERROR" "Failed to install Redis. Please install manually with 'brew install redis'"
        exit 1
      }
      brew services start redis
    else
      log "ERROR" "Unsupported operating system. Please install Redis manually."
      exit 1
    fi
  fi
  
  # Check Redis connection
  if ! redis-cli ping > /dev/null 2>&1; then
    log "WARNING" "Redis server not running. Attempting to start..."
    if [ "$(uname)" == "Darwin" ]; then
      brew services start redis || {
        log "ERROR" "Failed to start Redis. Please start manually with 'brew services start redis'"
        exit 1
      }
    else
      log "ERROR" "Redis server not running. Please start manually."
      exit 1
    fi
  fi
  
  # Check for GitHub CLI
  if ! which gh > /dev/null; then
    log "WARNING" "GitHub CLI not found. Attempting to install..."
    if [ "$(uname)" == "Darwin" ]; then
      brew install gh || {
        log "ERROR" "Failed to install GitHub CLI. Please install manually with 'brew install gh'"
        exit 1
      }
    else
      log "ERROR" "Unsupported operating system. Please install GitHub CLI manually."
      exit 1
    fi
  fi
  
  # Check GitHub authentication
  if ! gh auth status > /dev/null 2>&1; then
    log "ERROR" "Not authenticated with GitHub. Please run 'gh auth login' first."
    exit 1
  fi
  
  # Check Python for Redis support
  if ! which python3 > /dev/null; then
    log "ERROR" "Python 3 not found. Please install Python 3."
    exit 1
  fi
  
  # Setup Python environment and dependencies
  if [ ! -d "$PROJECT_PATH/.autonomous-claude/venv" ]; then
    log "INFO" "Setting up Python virtual environment..."
    python3 -m venv "$PROJECT_PATH/.autonomous-claude/venv"
    source "$PROJECT_PATH/.autonomous-claude/venv/bin/activate"
    pip install redis rq rq-dashboard 
  else
    source "$PROJECT_PATH/.autonomous-claude/venv/bin/activate"
  fi
  
  log "INFO" "All dependencies are available."
}

init_project() {
  log "INFO" "Initializing project: $PROJECT_PATH"
  
  # Create necessary directories
  mkdir -p "$PROJECT_PATH/.autonomous-claude"
  mkdir -p "$PROJECT_PATH/.autonomous-claude/logs"
  mkdir -p "$PROJECT_PATH/.autonomous-claude/tasks"
  mkdir -p "$PROJECT_PATH/.autonomous-claude/reviews"
  mkdir -p "$PROJECT_PATH/.autonomous-claude/templates"
  mkdir -p "$PROJECT_PATH/.autonomous-claude/instructions"
  mkdir -p "$PROJECT_PATH/.autonomous-claude/data"
  mkdir -p "$DOCS_PATH"
  
  # Determine the original installation directory
  SCRIPT_PATH=$(realpath "$0")
  INSTALL_DIR=$(dirname "$SCRIPT_PATH")
  
  # Link code files from the original installation, but keep data directories separate
  log "INFO" "Creating symlinks to core code files..."
  
  # Create symlinks for code files in the source installation's .autonomous-claude directory
  SRC_DIR="$INSTALL_DIR/.autonomous-claude"
  if [ -d "$SRC_DIR" ]; then
    # Link Python modules (but only code files, not project-specific data)
    for pyfile in "$SRC_DIR"/*.py; do
      if [ -f "$pyfile" ]; then
        FILENAME=$(basename "$pyfile")
        # Skip any Python files that might contain project-specific data
        if [[ "$FILENAME" != *"_data.py" && "$FILENAME" != *"_cache.py" ]]; then
          TARGET="$PROJECT_PATH/.autonomous-claude/$FILENAME"
          if [ ! -e "$TARGET" ]; then
            ln -sf "$pyfile" "$TARGET"
            log "INFO" "Linked $FILENAME from source installation"
          fi
        fi
      fi
    done
    
    # Link template files (but not project-specific ones)
    if [ -d "$SRC_DIR/templates" ]; then
      for template in "$SRC_DIR/templates"/*; do
        if [ -f "$template" ]; then
          FILENAME=$(basename "$template")
          # Only link generic templates
          if [[ "$FILENAME" == "*_template.md" || "$FILENAME" == "*_format.md" ]]; then
            TARGET="$PROJECT_PATH/.autonomous-claude/templates/$FILENAME"
            if [ ! -e "$TARGET" ]; then
              ln -sf "$template" "$TARGET"
              log "INFO" "Linked template: $FILENAME from source installation"
            fi
          fi
        fi
      done
    fi
    
    # Important: Create a unique project identifier in each project to ensure task isolation
    PROJECT_ID_FILE="$PROJECT_PATH/.autonomous-claude/project_id"
    if [ ! -f "$PROJECT_ID_FILE" ]; then
      # Create a unique project ID based on the absolute path hash
      PROJECT_ID=$(echo "$PROJECT_PATH" | shasum -a 256 | cut -c1-16)
      echo "$PROJECT_ID" > "$PROJECT_ID_FILE"
      log "INFO" "Created unique project ID: $PROJECT_ID"
    fi
  else
    log "WARNING" "Source installation directory not found: $SRC_DIR"
    log "INFO" "Creating core files from embedded templates"
    # If we can't find the source installation directory, fall back to copying templates
    start_redis_worker
  fi
  
  # Check if CLAUDE.md exists, if not create it
  if [ ! -f "$PROJECT_PATH/CLAUDE.md" ]; then
    cat > "$PROJECT_PATH/CLAUDE.md" << EOF
# CLAUDE.md

This file contains instructions for Claude Code to follow when working on this project.

## Project Overview

[Provide a brief description of the project here]

## Project Structure

[Describe the organization of the codebase]

## Dependencies

[List the main dependencies and technologies used]

## Coding Conventions

[Describe any coding conventions to follow]

## Pull Request Guidelines

[Provide guidelines for creating and reviewing PRs]

## Testing Guidelines

[Describe how to test changes]

## Additional Resources

[Link to documentation or other resources]
EOF

    log "INFO" "Created CLAUDE.md file with project guidelines"
  fi

  # Create config file if it doesn't exist
  if [ ! -f "$CONFIG_FILE" ]; then
    log "INFO" "Creating default configuration file..."
    
    # Get GitHub repository from remote
    GITHUB_REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "")
    
    # Get GitHub username
    GITHUB_USERNAME=$(gh api user -q .login 2>/dev/null || echo "")
    
    cat > "$CONFIG_FILE" << EOF
#!/usr/bin/env bash
# Autonomous Claude configuration

# Project settings
PROJECT_PATH="$PROJECT_PATH"
DOCS_PATH="$PROJECT_PATH/docs"
GITHUB_REPO="$GITHUB_REPO"
GITHUB_ISSUE_LABEL="autonomous-coding"
GITHUB_USERNAME="$GITHUB_USERNAME"

# Operation settings
POLLING_INTERVAL=300
REDIS_URL="redis://localhost:6379"
REDIS_QUEUE="autonomous-coding"

# PR review settings
PR_REVIEW_ENABLED=true
PR_AUTO_REVIEW=true  # Automatically review PR after creation
PR_AUTO_REVIEW_DELAY=30  # Delay in seconds before auto-review
PR_REVIEW_MAX_RETRIES=3  # Maximum number of retry attempts for PR reviews
PR_REVIEW_RETRY_DELAY=60  # Initial delay in seconds between retry attempts
PR_UPDATE_DETECTION=true  # Monitor PRs for updates and trigger re-reviews
MIN_REREVIEW_HOURS=24  # Minimum hours between re-reviews
REVIEW_ONLY_OWN_PRS=true  # Only review PRs created by this system

# Paths
CLAUDE_CODE_PATH="$CLAUDE_CODE_PATH"

# MCP servers
MCP_SERVERS_ENABLED=true
# Add any custom MCP servers here
# Example: MCP_SERVER_GITHUB="docker run -i --rm -e GITHUB_PERSONAL_ACCESS_TOKEN=\$GITHUB_TOKEN ghcr.io/github/github-mcp-server"
EOF

    log "INFO" "Created config file at $CONFIG_FILE"
  fi
  
  # Create custom Claude commands
  create_claude_commands
  
  log "INFO" "Project initialization complete."
}

create_claude_commands() {
  log "INFO" "Creating custom Claude commands..."
  
  # Make sure commands directory exists
  mkdir -p "$PROJECT_PATH/.autonomous-claude/commands"
  
  # Command: Generate comprehensive project documentation
  cat > "$PROJECT_PATH/.autonomous-claude/commands/document-project.md" << EOF
This command will scan through the codebase and generate comprehensive documentation for the project.

Follow these steps:
1. Analyze the project structure and identify key components
2. Create a project overview document
3. Document each major component, class, and function
4. Generate a data flow diagram if possible
5. Create directory structure documentation
6. Create a summary of dependencies and their purposes
7. Document any known issues or limitations
8. Consolidate all documentation into a well-structured format in the docs directory

All documentation should be written in Markdown format and saved to the docs directory.
EOF

  # Command: Analyze GitHub issue
  cat > "$PROJECT_PATH/.autonomous-claude/commands/analyze-github-issue.md" << EOF
This command will analyze a GitHub issue and prepare a detailed plan for implementation.

The argument should be the GitHub issue number.

Follow these steps:
1. Use the GitHub CLI to fetch detailed information about the issue
2. Analyze the issue requirements
3. Review the existing codebase to understand what needs to be modified
4. Research any necessary information online using available MCP tools
5. Create a detailed implementation plan
6. Save the plan to .autonomous-claude/tasks/[issue-number]-plan.md

The plan should include:
- Issue summary
- Required changes
- Implementation steps
- Files to be modified
- Testing approach
- Estimated complexity
EOF

  # Command: Implement GitHub issue
  cat > "$PROJECT_PATH/.autonomous-claude/commands/implement-github-issue.md" << EOF
This command will implement a solution for a GitHub issue based on the previously generated plan.

The argument should be the GitHub issue number.

Follow these steps:
1. Read the implementation plan from .autonomous-claude/tasks/[issue-number]-plan.md
2. Create a new branch named feature/issue-[issue-number]
3. Implement the changes according to the plan
4. Write tests for the implementation
5. Update documentation
6. Run tests to ensure everything works
7. Create a detailed commit message
8. Push the changes to GitHub
9. Create a pull request

Be sure to:
- Follow the project's coding style and conventions
- Add appropriate comments and documentation
- Write clean, maintainable code
- Handle edge cases and errors appropriately
EOF

  # Command: Review PR
  cat > "$PROJECT_PATH/.autonomous-claude/commands/review-pull-request.md" << EOF
This command will review a GitHub pull request and provide detailed feedback.

The argument should be the GitHub PR number.

Follow these steps:
1. Use the GitHub CLI to fetch detailed information about the PR
2. Get the full diff of the PR changes
3. Analyze the code changes for:
   - Code quality issues
   - Potential bugs or logical errors
   - Security concerns
   - Performance considerations
   - Adherence to project coding standards
   - Completeness of implementation
4. Generate a comprehensive review that includes:
   - An overall assessment of the PR
   - Specific feedback on each file changed
   - Suggestions for improvements
   - Questions about implementation decisions
5. Post the review as a comment on the PR using the GitHub CLI

Your review should be constructive, detailed, and helpful. Focus on making the code better rather than just pointing out issues.

The review should be helpful both to the PR author and to future developers who might read the code.

ARGUMENTS: {pr_number}
EOF

  log "INFO" "Custom Claude commands created successfully."
}

start_redis_worker() {
  log "INFO" "Starting Redis worker..."
  
  # Check if worker script exists, if not create it
  if [ ! -f "$PROJECT_PATH/.autonomous-claude/worker.py" ]; then
    cat > "$PROJECT_PATH/.autonomous-claude/worker.py" << 'EOF'
import os
import sys
import json
import time
import subprocess
from datetime import datetime, timedelta
from redis import Redis
from rq import Worker, Queue
import logging
from logging.handlers import RotatingFileHandler

# Setup logging
log_dir = os.path.join(os.getcwd(), '.autonomous-claude', 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'worker.log')

logger = logging.getLogger('autonomous-claude-worker')
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Also log to stdout
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Redis connection
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
queue_name = os.environ.get('REDIS_QUEUE', 'autonomous-coding')
redis_conn = Redis.from_url(redis_url)
queue = Queue(queue_name, connection=redis_conn)

# Task processing functions
def create_instruction_file(command_type, issue_or_pr_number=None, prompt=None):
    """Create an instruction file for Claude Code to read"""
    instructions_dir = os.path.join(os.getcwd(), '.autonomous-claude', 'instructions')
    os.makedirs(instructions_dir, exist_ok=True)
    
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    file_path = os.path.join(instructions_dir, f"{command_type}-{timestamp}.md")
    
    # Base instructions
    instructions = ["# Instructions for Claude Code\n"]
    
    if command_type == 'analyze-github-issue':
        # Get issue details using GitHub CLI
        try:
            issue_json = subprocess.check_output(
                ['gh', 'issue', 'view', issue_or_pr_number, '--json', 'title,body,number,url'],
                text=True
            )
            issue_data = json.loads(issue_json)
            
            instructions.append(f"## Analyze GitHub Issue #{issue_data['number']}\n")
            instructions.append(f"**Title**: {issue_data['title']}\n")
            instructions.append(f"**URL**: {issue_data['url']}\n")
            instructions.append("**Description**:\n")
            instructions.append(f"{issue_data['body']}\n\n")
            
            instructions.append("## Your Task\n")
            instructions.append("1. Analyze the GitHub issue described above\n")
            instructions.append("2. Create a plan for implementing a solution\n")
            instructions.append("3. Save your analysis and plan to a file named `tasks/{issue_number}-plan.md` where {issue_number} is the GitHub issue number\n")
            instructions.append("4. The plan should include detailed steps for implementation\n")
            instructions.append("\nYou have full access to examine the codebase, run commands, and create files.\n")
            
        except Exception as e:
            logger.error(f"Failed to get issue details: {str(e)}")
            instructions.append(f"## Analyze GitHub Issue #{issue_or_pr_number}\n")
            instructions.append("Could not fetch issue details. Please use GitHub CLI to get the issue information.\n")
    
    elif command_type == 'implement-github-issue':
        instructions.append(f"## Implement Solution for GitHub Issue #{issue_or_pr_number}\n")
        instructions.append("1. Read the analysis and plan from the previous step\n")
        instructions.append(f"2. Check if the file `tasks/{issue_or_pr_number}-plan.md` exists and read it\n")
        instructions.append("3. Implement the solution according to the plan\n")
        instructions.append("4. Create or modify necessary files\n")
        instructions.append("5. Test your implementation\n")
        instructions.append("6. Create a PR with your changes\n")
        instructions.append("\nYou have full access to examine the codebase, run commands, create files, and make changes.\n")
    
    elif command_type == 'document-project':
        instructions.append("## Update Project Documentation\n")
        instructions.append("1. Examine the codebase to understand its structure and functionality\n")
        instructions.append("2. Update or create documentation files in the `docs/` directory\n")
        instructions.append("3. Make sure to document the following:\n")
        instructions.append("   - Project overview\n")
        instructions.append("   - Installation instructions\n")
        instructions.append("   - Usage examples\n")
        instructions.append("   - API reference (if applicable)\n")
        instructions.append("   - Component descriptions\n")
        instructions.append("\nYou have full access to examine the codebase, run commands, and create or modify documentation files.\n")
    
    elif command_type == 'review-pull-request':
        # Get PR details using GitHub CLI
        try:
            pr_json = subprocess.check_output(
                ['gh', 'pr', 'view', issue_or_pr_number, '--json', 'title,body,number,url,files'],
                text=True
            )
            pr_data = json.loads(pr_json)
            
            instructions.append(f"## Review Pull Request #{pr_data['number']}\n")
            instructions.append(f"**Title**: {pr_data['title']}\n")
            instructions.append(f"**URL**: {pr_data['url']}\n")
            instructions.append("**Description**:\n")
            instructions.append(f"{pr_data['body']}\n\n")
            
            instructions.append("**Files Changed**:\n")
            for file in pr_data.get('files', []):
                instructions.append(f"- {file.get('path')}\n")
            
            instructions.append("\n## Your Task\n")
            instructions.append("1. Review the PR described above\n")
            instructions.append("2. Examine the code changes\n")
            instructions.append("3. Provide feedback on code quality, potential issues, and suggestions for improvement\n")
            instructions.append("4. Post your review as a comment on the PR\n")
            
        except Exception as e:
            logger.error(f"Failed to get PR details: {str(e)}")
            instructions.append(f"## Review Pull Request #{issue_or_pr_number}\n")
            instructions.append("Could not fetch PR details. Please use GitHub CLI to get the PR information.\n")
    
    else:
        # Custom command fallback
        instructions.append(f"## Custom Command\n")
        instructions.append(f"Command: {prompt}\n\n")
        instructions.append("Please execute this command and take appropriate actions.\n")
    
    # Write instructions to file
    with open(file_path, 'w') as f:
        f.write('\n'.join(instructions))
    
    return file_path

def run_claude_code_headless(prompt, allowed_tools=None):
    """Run Claude Code in headless mode with the given prompt"""
    claude_path = os.environ.get('CLAUDE_CODE_PATH', 'claude')
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.getcwd(), '.autonomous-claude', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Check if the prompt starts with a slash command (custom command)
    # For custom commands like /project:analyze-github-issue, convert to file-based instructions
    if prompt.startswith('/'):
        # Extract command type and parameters
        if prompt.startswith('/project:analyze-github-issue'):
            command_type = 'analyze-github-issue'
            issue_number = prompt.split()[-1]
            instruction_file = create_instruction_file(command_type, issue_number)
        elif prompt.startswith('/project:implement-github-issue'):
            command_type = 'implement-github-issue'
            issue_number = prompt.split()[-1]
            instruction_file = create_instruction_file(command_type, issue_number)
        elif prompt.startswith('/project:document-project'):
            command_type = 'document-project'
            instruction_file = create_instruction_file(command_type)
        elif prompt.startswith('/project:review-pull-request'):
            command_type = 'review-pull-request'
            pr_number = prompt.split()[-1]
            instruction_file = create_instruction_file(command_type, pr_number)
        else:
            # Fallback for unknown custom commands
            command_type = 'custom-command'
            instruction_file = create_instruction_file(command_type, prompt=prompt)
        
        logger.info(f"Running Claude Code with file-based instructions for: {command_type}")
        logger.info(f"Instruction file: {instruction_file}")
        
        # Run Claude in print mode with the instruction file
        file_prompt = f"Read and execute the instructions in this file: {instruction_file}"
        command = [claude_path, '-p', file_prompt, '--dangerously-skip-permissions']
        
        if allowed_tools:
            command.extend(['--allowedTools', allowed_tools])
        
        try:
            logger.info(f"Running Claude Code with command: {' '.join(command)}")
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"Claude Code execution successful")
            return {
                'success': True,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
        except subprocess.CalledProcessError as e:
            logger.error(f"Claude Code execution failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'stdout': e.stdout,
                'stderr': e.stderr
            }
        except Exception as e:
            logger.error(f"Claude Code execution failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'stdout': "",
                'stderr': str(e)
            }
    else:
        # For regular prompts, use print mode (-p) with the requested tools
        command = [claude_path, '-p', prompt, '--dangerously-skip-permissions']
        
        if allowed_tools:
            command.extend(['--allowedTools', allowed_tools])
        
        logger.info(f"Running Claude Code with command: {' '.join(command)}")
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"Claude Code execution successful")
            return {
                'success': True,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
        except subprocess.CalledProcessError as e:
            logger.error(f"Claude Code execution failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'stdout': e.stdout,
                'stderr': e.stderr
            }

def process_github_issue(issue_number):
    """Process a GitHub issue through the autonomous workflow"""
    logger.info(f"Processing GitHub issue #{issue_number}")
    
    # Create/update lock file
    project_path = os.environ.get('PROJECT_PATH', os.getcwd())
    tasks_dir = os.path.join(project_path, '.autonomous-claude', 'tasks')
    os.makedirs(tasks_dir, exist_ok=True)
    
    # Get unique project ID to ensure lock files don't conflict between projects
    project_id_file = os.path.join(project_path, '.autonomous-claude', 'project_id')
    project_id = ''
    if os.path.exists(project_id_file):
        with open(project_id_file, 'r') as f:
            project_id = f.read().strip()
    
    # Use project ID in lock file name to ensure isolation between projects
    lock_file = os.path.join(tasks_dir, f"{project_id}-issue-{issue_number}.lock")
    
    # Update lock file with current timestamp
    with open(lock_file, 'w') as f:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"Processing started: {timestamp}\n")
    
    logger.info(f"Created/updated lock file for issue #{issue_number}")
    
    try:
        # Step 1: Analyze the issue and create a plan
        analyze_prompt = f"/project:analyze-github-issue {issue_number}"
        
        result = run_claude_code_headless(
            analyze_prompt,
            "Bash(gh:*) Edit Run"
        )
        
        if not result['success']:
            logger.error(f"Failed to analyze issue #{issue_number}")
            # Don't remove lock file here - keep it as a record of failure
            return {
                'success': False,
                'stage': 'analyze',
                'error': result['stderr']
            }
        
        logger.info(f"Successfully analyzed issue #{issue_number}")
        
        # Update lock file to indicate progress
        with open(lock_file, 'a') as f:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"Analysis completed: {timestamp}\n")
        
        # Check if plan file exists
        plan_file = os.path.join(tasks_dir, f"{issue_number}-plan.md")
        if not os.path.exists(plan_file):
            logger.warning(f"Plan file not found after analysis for issue #{issue_number}")
            # Still continue to implementation even if plan file not found
        
        # Step 2: Implement the solution
        implement_prompt = f"/project:implement-github-issue {issue_number}"
        
        result = run_claude_code_headless(
            implement_prompt,
            "Bash(gh:*,git:*) Edit Run Test"
        )
        
        if not result['success']:
            logger.error(f"Failed to implement solution for issue #{issue_number}")
            # Update lock file with failure information
            with open(lock_file, 'a') as f:
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"Implementation failed: {timestamp}\n")
            
            return {
                'success': False,
                'stage': 'implement',
                'error': result['stderr']
            }
        
        logger.info(f"Successfully implemented solution for issue #{issue_number}")
        
        # Update lock file to indicate progress
        with open(lock_file, 'a') as f:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"Implementation completed: {timestamp}\n")
        
        # Step 3: Extract PR number and track relationship
        # This attempts to find the PR number from the implementation output
        pr_number = None
        try:
            # Look for a PR link in the output
            import re
            pr_url_pattern = r'https://github\.com/[^/]+/[^/]+/pull/(\d+)'
            pr_number_pattern = r'Created PR #(\d+)'
            
            pr_url_match = re.search(pr_url_pattern, result['stdout'])
            pr_number_match = re.search(pr_number_pattern, result['stdout'])
            
            if pr_url_match:
                pr_number = pr_url_match.group(1)
                logger.info(f"Found PR number from URL: {pr_number}")
            elif pr_number_match:
                pr_number = pr_number_match.group(1)
                logger.info(f"Found PR number from text: {pr_number}")
            
            if pr_number:
                # Try to import PR relationship module if available
                try:
                    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
                    from pr_issue_relationship import get_instance
                    
                    # Associate PR with issue
                    relationship_manager = get_instance()
                    relationship_manager.associate_pr_with_issue(issue_number, pr_number)
                    
                    logger.info(f"Associated PR #{pr_number} with issue #{issue_number}")
                    
                    # Update lock file with PR information
                    with open(lock_file, 'a') as f:
                        f.write(f"PR created: #{pr_number}\n")
                    
                    # Step 4: Trigger PR review if auto-review is enabled
                    auto_review = os.environ.get('PR_AUTO_REVIEW', 'true').lower() == 'true'
                    if auto_review:
                        logger.info(f"Triggering auto-review for PR #{pr_number}")
                        
                        # Add a delay to allow GitHub to process the PR
                        auto_review_delay = int(os.environ.get('PR_AUTO_REVIEW_DELAY', '30'))
                        time.sleep(auto_review_delay)
                        
                        # Try to import tasks module
                        try:
                            from tasks import enqueue_review_pull_request
                            
                            # Enqueue PR review
                            job_id = enqueue_review_pull_request(pr_number)
                            logger.info(f"Enqueued PR review job with ID: {job_id}")
                            
                            # Update lock file with review information
                            with open(lock_file, 'a') as f:
                                f.write(f"Auto-review triggered: job ID {job_id}\n")
                        except Exception as e:
                            logger.error(f"Failed to enqueue PR review: {str(e)}")
                except ImportError as e:
                    logger.warning(f"PR relationship module not available: {str(e)}")
                except Exception as e:
                    logger.error(f"Failed to associate PR with issue: {str(e)}")
            else:
                logger.warning(f"No PR number found in implementation output for issue #{issue_number}")
        except Exception as e:
            logger.error(f"Error extracting PR number from output: {str(e)}")
        
        # Create a note to indicate successful completion
        completion_file = os.path.join(tasks_dir, f"{issue_number}-completed.txt")
        with open(completion_file, 'w') as f:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"Issue #{issue_number} fully processed at {timestamp}\n")
            if pr_number:
                f.write(f"PR created: #{pr_number}\n")
        
        return {
            'success': True,
            'issue_number': issue_number,
            'pr_number': pr_number,
            'completed_at': time.time()
        }
    except Exception as e:
        # Log any unexpected errors
        logger.error(f"Unexpected error processing issue #{issue_number}: {str(e)}")
        
        # Update lock file with error information
        with open(lock_file, 'a') as f:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"Error occurred: {timestamp} - {str(e)}\n")
        
        return {
            'success': False,
            'stage': 'unknown',
            'error': str(e)
        }

def update_project_documentation():
    """Update project documentation using Claude Code"""
    logger.info("Updating project documentation")
    
    result = run_claude_code_headless(
        "/project:document-project",
        "Bash Edit Run"
    )
    
    if not result['success']:
        logger.error("Failed to update project documentation")
        return {
            'success': False,
            'stage': 'documentation',
            'error': result['stderr']
        }
    
    logger.info("Successfully updated project documentation")
    
    return {
        'success': True,
        'completed_at': time.time()
    }

def review_pull_request(pr_number):
    """Review a GitHub pull request and provide feedback"""
    logger.info(f"Reviewing GitHub PR #{pr_number}")
    
    # Ensure reviews directory exists
    project_path = os.environ.get('PROJECT_PATH', os.getcwd())
    reviews_dir = os.path.join(project_path, '.autonomous-claude', 'reviews')
    os.makedirs(reviews_dir, exist_ok=True)
    
    # Get unique project ID to ensure lock files don't conflict between projects
    project_id_file = os.path.join(project_path, '.autonomous-claude', 'project_id')
    project_id = ''
    if os.path.exists(project_id_file):
        with open(project_id_file, 'r') as f:
            project_id = f.read().strip()
    
    # Create a lock file to indicate the PR is being processed
    # Include project ID to ensure isolation between projects
    lock_file = os.path.join(reviews_dir, f"{project_id}-pr-{pr_number}.lock")
    if not os.path.exists(lock_file):
        with open(lock_file, 'w') as f:
            timestamp = datetime.now().isoformat()
            f.write(f"Review started: {timestamp}\n")
    
    # Import PR relationship module if available
    try:
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from pr_issue_relationship import get_instance
        relationship_manager = get_instance()
        
        # Update review status to in_progress
        relationship_manager.update_pr_review_status(pr_number, 'in_progress')
        logger.info(f"Updated PR review status to in_progress for PR #{pr_number}")
    except ImportError as e:
        logger.warning(f"Failed to import PR relationship module: {str(e)}")
        relationship_manager = None
    except Exception as e:
        logger.warning(f"Failed to update PR review status: {str(e)}")
        relationship_manager = None
    
    # Check if a review already exists and if we should re-review
    review_file = os.path.join(reviews_dir, f"pr-{pr_number}-review.md")
    should_review = True
    
    # Check with relationship manager if PR should be reviewed
    if relationship_manager:
        try:
            should_review = relationship_manager.should_review_pr(pr_number)
            logger.info(f"Relationship manager: should review PR #{pr_number}? {should_review}")
        except Exception as e:
            logger.warning(f"Failed to check should_review_pr: {str(e)}")
            # Default to reviewing if we can't determine
            should_review = True
    elif os.path.exists(review_file):
        # Fall back to simple file check if relationship manager isn't available
        logger.info(f"Review already exists for PR #{pr_number}, using simple file check")
        should_review = False
    
    # Skip if we shouldn't review
    if not should_review:
        logger.info(f"Skipping review for PR #{pr_number} based on status check")
        # Remove lock file
        try:
            os.remove(lock_file)
        except:
            logger.warning(f"Failed to remove lock file for PR #{pr_number}")
        
        return {
            'success': True,
            'pr_number': pr_number,
            'completed_at': time.time(),
            'status': 'skipped'
        }
    
    # Proceed with review
    review_prompt = f"/project:review-pull-request {pr_number}"
    
    result = run_claude_code_headless(
        review_prompt,
        "Bash(gh:*,git:*) Edit Run"
    )
    
    # Process result
    if not result['success']:
        logger.error(f"Failed to review PR #{pr_number}")
        
        # Update review status to failed if relationship manager is available
        if relationship_manager:
            try:
                relationship_manager.update_pr_review_status(pr_number, 'failed')
                logger.info(f"Updated PR review status to failed for PR #{pr_number}")
            except Exception as e:
                logger.warning(f"Failed to update PR review status to failed: {str(e)}")
        
        # Remove lock file
        try:
            os.remove(lock_file)
        except:
            logger.warning(f"Failed to remove lock file for PR #{pr_number}")
        
        return {
            'success': False,
            'stage': 'review',
            'error': result['stderr']
        }
    
    logger.info(f"Successfully reviewed PR #{pr_number}")
    
    # Check if review file was created
    review_id = None
    if os.path.exists(review_file):
        logger.info(f"Review file created for PR #{pr_number}")
        
        # Add review record in relationship manager
        if relationship_manager:
            try:
                # Read review file content
                with open(review_file, 'r') as f:
                    review_content = f.read()
                
                # Save review to history
                review_data = {
                    'content': review_content,
                    'timestamp': datetime.now().isoformat(),
                    'file_path': review_file
                }
                
                # Add review record and get review ID
                review_id = relationship_manager.add_review_record(pr_number, review_data)
                logger.info(f"Added review record for PR #{pr_number} with ID {review_id}")
            except Exception as e:
                logger.warning(f"Failed to add review record: {str(e)}")
    else:
        logger.warning(f"Review file not created for PR #{pr_number}")
    
    # Update PR review status to completed if relationship manager is available
    if relationship_manager:
        try:
            relationship_manager.update_pr_review_status(pr_number, 'completed', review_id)
            logger.info(f"Updated PR review status to completed for PR #{pr_number}")
        except Exception as e:
            logger.warning(f"Failed to update PR review status to completed: {str(e)}")
    
    # Remove lock file
    try:
        os.remove(lock_file)
    except:
        logger.warning(f"Failed to remove lock file for PR #{pr_number}")
    
    return {
        'success': True,
        'pr_number': pr_number,
        'review_id': review_id,
        'completed_at': time.time()
    }

# Worker loop
if __name__ == '__main__':
    logger.info(f"Starting worker for queue: {queue_name}")
    
    # Initialize worker with explicit connection parameter for RQ v2.3.3 compatibility
    worker = Worker([queue], connection=redis_conn)
    worker.work()
EOF

    log "INFO" "Created worker script at $PROJECT_PATH/.autonomous-claude/worker.py"
  fi
  
  # Check if tasks registration script exists, if not create it
  if [ ! -f "$PROJECT_PATH/.autonomous-claude/tasks.py" ]; then
    cat > "$PROJECT_PATH/.autonomous-claude/tasks.py" << 'EOF'
import os
import sys
import time
from redis import Redis
from rq import Queue

# Add current directory to path so we can import worker
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from worker import process_github_issue, update_project_documentation, review_pull_request

# Redis connection
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
queue_name = os.environ.get('REDIS_QUEUE', 'autonomous-coding')
redis_conn = Redis.from_url(redis_url)
queue = Queue(queue_name, connection=redis_conn)

def enqueue_process_github_issue(issue_number):
    """Add a GitHub issue processing task to the queue"""
    job = queue.enqueue(
        process_github_issue,
        issue_number,
        job_timeout='2h',  # Long timeout for complex issues
        result_ttl=86400,  # Keep results for 24 hours
        ttl=86400          # Job can wait in queue for up to 24 hours
    )
    return job.id

def enqueue_update_documentation():
    """Add a documentation update task to the queue"""
    job = queue.enqueue(
        update_project_documentation,
        job_timeout='1h',
        result_ttl=86400,
        ttl=86400
    )
    return job.id

def enqueue_review_pull_request(pr_number):
    """Add a PR review task to the queue"""
    job = queue.enqueue(
        review_pull_request,
        pr_number,
        job_timeout='1h',
        result_ttl=86400,
        ttl=86400
    )
    return job.id
EOF

    log "INFO" "Created tasks script at $PROJECT_PATH/.autonomous-claude/tasks.py"
  fi
  
  # Create PR checker script if it doesn't exist
  if [ ! -f "$PROJECT_PATH/.autonomous-claude/github_pr_checker.py" ]; then
    cat > "$PROJECT_PATH/.autonomous-claude/github_pr_checker.py" << 'EOF'
#!/usr/bin/env python3
# github_pr_checker.py
#
# Processes GitHub pull requests for autonomous review workflow
# Reads PR data from stdin and enqueues them for processing

import os
import sys
import json
import time
from datetime import datetime
import logging
import traceback
import importlib.util

# Setup logging
log_dir = os.path.join(os.getcwd(), '.autonomous-claude', 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'github_pr_checker.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('github-pr-checker')

# Load tasks module dynamically
def import_tasks_module():
    project_path = os.environ.get('PROJECT_PATH', os.getcwd())
    tasks_path = os.path.join(project_path, '.autonomous-claude', 'tasks.py')
    
    if not os.path.exists(tasks_path):
        logger.error(f"Tasks module not found at {tasks_path}")
        sys.exit(1)
    
    spec = importlib.util.spec_from_file_location("tasks", tasks_path)
    tasks_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tasks_module)
    return tasks_module

def is_already_reviewed(pr_number):
    """Check if a PR has already been reviewed or is being processed"""
    project_path = os.environ.get('PROJECT_PATH', os.getcwd())
    reviews_dir = os.path.join(project_path, '.autonomous-claude', 'reviews')
    os.makedirs(reviews_dir, exist_ok=True)
    
    # Review file would indicate PR has been reviewed
    review_file = os.path.join(reviews_dir, f"pr-{pr_number}-review.md")
    if os.path.exists(review_file):
        logger.info(f"PR #{pr_number} already has a review file")
        return True
    
    # Lock file indicates PR is being processed
    lock_file = os.path.join(reviews_dir, f"pr-{pr_number}.lock")
    if os.path.exists(lock_file):
        # Check if lock is stale (older than 1 hour)
        lock_time = os.path.getmtime(lock_file)
        if time.time() - lock_time < 3600:  # 1 hour in seconds
            logger.info(f"PR #{pr_number} is currently being processed")
            return True
        else:
            logger.warning(f"Found stale lock for PR #{pr_number}, removing")
            os.remove(lock_file)
    
    return False

def create_lock_file(pr_number):
    """Create a lock file to indicate a PR is being processed"""
    project_path = os.environ.get('PROJECT_PATH', os.getcwd())
    reviews_dir = os.path.join(project_path, '.autonomous-claude', 'reviews')
    os.makedirs(reviews_dir, exist_ok=True)
    
    lock_file = os.path.join(reviews_dir, f"pr-{pr_number}.lock")
    with open(lock_file, 'w') as f:
        timestamp = datetime.now().isoformat()
        f.write(f"Review started: {timestamp}\n")
    
    logger.info(f"Created lock file for PR #{pr_number}")
    return True

def should_review_pr(pr):
    """Determine if a PR should be reviewed based on configuration"""
    # Check if we should only review PRs from our own system
    review_only_own = os.environ.get('REVIEW_ONLY_OWN_PRS', 'true').lower() == 'true'
    github_username = os.environ.get('GITHUB_USERNAME', '')
    
    if review_only_own and github_username:
        # Check if PR author matches our GitHub username
        pr_author = pr.get('author', {}).get('login', '')
        if pr_author != github_username:
            logger.info(f"Skipping PR #{pr['number']} as it's not authored by {github_username}")
            return False
    
    return True

def process_pull_requests(prs_json):
    """Process pull requests from JSON data"""
    try:
        prs = json.loads(prs_json)
        logger.info(f"Processing {len(prs)} pull requests")
        
        # Import tasks module for enqueuing
        tasks = import_tasks_module()
        
        for pr in prs:
            pr_number = pr['number']
            pr_title = pr['title']
            pr_url = pr.get('url', '')
            
            logger.info(f"Found PR #{pr_number}: {pr_title}")
            
            # Check if this PR should be reviewed
            if not should_review_pr(pr):
                continue
            
            # Skip if already reviewed or being processed
            if is_already_reviewed(pr_number):
                continue
            
            # Create lock file
            create_lock_file(pr_number)
            
            # Enqueue the PR for review
            try:
                job_id = tasks.enqueue_review_pull_request(pr_number)
                logger.info(f"Enqueued PR #{pr_number} for review with job ID: {job_id}")
                
                # Add job ID to lock file
                lock_file = os.path.join(os.environ.get('PROJECT_PATH', os.getcwd()),
                                        '.autonomous-claude', 'reviews', f"pr-{pr_number}.lock")
                try:
                    with open(lock_file, 'a') as f:
                        f.write(f"Job ID: {job_id}\n")
                except Exception as e:
                    logger.error(f"Error updating lock file: {str(e)}")
                
                print(f"Enqueued PR review job with ID: {job_id}")
            except Exception as e:
                logger.error(f"Failed to enqueue PR #{pr_number}: {str(e)}")
                traceback.print_exc()
                
                # Remove lock file on failure
                project_path = os.environ.get('PROJECT_PATH', os.getcwd())
                lock_file = os.path.join(project_path, '.autonomous-claude', 'reviews', f"pr-{pr_number}.lock")
                if os.path.exists(lock_file):
                    os.remove(lock_file)
        
        return True
    except json.JSONDecodeError:
        logger.error("Failed to parse pull requests JSON")
        traceback.print_exc()
        return False
    except Exception as e:
        logger.error(f"Error processing pull requests: {str(e)}")
        traceback.print_exc()
        return False

def main():
    # Read pull requests JSON from stdin
    prs_json = sys.stdin.read()
    
    if not prs_json:
        logger.warning("No input received from stdin")
        sys.exit(1)
    
    if process_pull_requests(prs_json):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF

    log "INFO" "Created PR checker script at $PROJECT_PATH/.autonomous-claude/github_pr_checker.py"
    chmod +x "$PROJECT_PATH/.autonomous-claude/github_pr_checker.py"
  fi
  
  # Start worker process in the background
  source "$PROJECT_PATH/.autonomous-claude/venv/bin/activate"
  export PYTHONPATH="$PROJECT_PATH/.autonomous-claude:$PYTHONPATH"
  export CLAUDE_CODE_PATH="$CLAUDE_CODE_PATH"
  export PROJECT_PATH="$PROJECT_PATH"
  export REDIS_URL="$REDIS_URL"
  export REDIS_QUEUE="$REDIS_QUEUE"
  export PR_AUTO_REVIEW="$PR_AUTO_REVIEW"
  export PR_AUTO_REVIEW_DELAY="$PR_AUTO_REVIEW_DELAY"
  export PR_REVIEW_MAX_RETRIES="$PR_REVIEW_MAX_RETRIES"
  export PR_REVIEW_RETRY_DELAY="$PR_REVIEW_RETRY_DELAY"
  export MIN_REREVIEW_HOURS="$MIN_REREVIEW_HOURS"
  
  log "INFO" "Starting worker in the background..."
  python3 "$PROJECT_PATH/.autonomous-claude/worker.py" > "$PROJECT_PATH/.autonomous-claude/logs/worker_stdout.log" 2>&1 &
  WORKER_PID=$!
  echo $WORKER_PID > "$PROJECT_PATH/.autonomous-claude/worker.pid"
  log "INFO" "Worker started with PID: $WORKER_PID"
}

check_github_issues() {
  log "INFO" "Checking GitHub issues..."
  
  # Create and test the tasks directory
  tasks_dir="$PROJECT_PATH/.autonomous-claude/tasks"
  mkdir -p "$tasks_dir"
  
  # Get or create project ID for isolation
  project_id_file="$PROJECT_PATH/.autonomous-claude/project_id"
  if [ -f "$project_id_file" ]; then
    project_id=$(cat "$project_id_file")
    log "INFO" "Using existing project ID: $project_id"
  else
    # Create a unique project ID based on the absolute path hash
    project_id=$(echo "$PROJECT_PATH" | shasum -a 256 | cut -c1-16)
    echo "$project_id" > "$project_id_file"
    log "INFO" "Created new project ID: $project_id"
  fi
  
  # Verify write access to the tasks directory
  test_file="$tasks_dir/test-access.txt"
  echo "Testing write access at $(date)" > "$test_file"
  if [ ! -f "$test_file" ]; then
    log "ERROR" "Cannot write to tasks directory: $tasks_dir"
    return 1
  fi
  rm -f "$test_file"
  
  # Get the list of open issues with the specified label
  issues=$(gh issue list --repo "$GITHUB_REPO" --label "$GITHUB_ISSUE_LABEL" --state open --json number,title,url)
  
  # Check if there are any issues
  if [ -z "$issues" ] || [ "$issues" == "[]" ]; then
    log "INFO" "No open issues with label '$GITHUB_ISSUE_LABEL' found."
    return 0
  fi
  
  # Log the issues found for debugging
  log "INFO" "Found issues: $issues"
  
  # Use a for loop instead of piping to while to avoid subshell issues
  issue_count=$(echo "$issues" | jq '. | length')
  log "INFO" "Found $issue_count issues to process"
  
  for i in $(seq 0 $((issue_count - 1))); do
    issue_number=$(echo "$issues" | jq -r ".[$i].number")
    issue_title=$(echo "$issues" | jq -r ".[$i].title")
    
    # Log the extracted issue info
    log "INFO" "Extracted issue #$issue_number: $issue_title"
    
    # Check if this issue already has a plan or lock file
    project_plan_file="$tasks_dir/${project_id}-issue-${issue_number}-plan.md"
    old_plan_file="$tasks_dir/${issue_number}-plan.md"
    project_lock_file="$tasks_dir/${project_id}-issue-${issue_number}.lock"
    old_lock_file="$tasks_dir/${issue_number}.lock"
    
    log "INFO" "Checking plan files for project: $project_id, issue: $issue_number"
    # Check both new and old format plan files
    if [ -f "$project_plan_file" ]; then
      log "INFO" "Issue #$issue_number already has a plan in project $project_id, skipping"
      continue
    elif [ -f "$old_plan_file" ]; then
      log "INFO" "Issue #$issue_number has an old-format plan file, skipping"
      continue
    fi
    
    log "INFO" "Checking lock files for project: $project_id, issue: $issue_number"
    # Check both new and old format lock files
    if [ -f "$project_lock_file" ]; then
      # Check if lock file is more than 1 hour old
      lock_time=$(stat -f "%m" "$project_lock_file")
      current_time=$(date +%s)
      age_seconds=$((current_time - lock_time))
      
      if [ $age_seconds -lt 3600 ]; then  # Less than 1 hour old
        log "INFO" "Issue #$issue_number is already being processed in project $project_id (lock created $(($age_seconds / 60)) minutes ago)"
        continue
      else
        log "INFO" "Found stale lock for issue #$issue_number in project $project_id, re-enqueueing"
        rm "$project_lock_file"
      fi
    elif [ -f "$old_lock_file" ]; then
      # Check old format lock file too
      lock_time=$(stat -f "%m" "$old_lock_file")
      current_time=$(date +%s)
      age_seconds=$((current_time - lock_time))
      
      if [ $age_seconds -lt 3600 ]; then
        log "INFO" "Issue #$issue_number is already being processed with old-format lock (created $(($age_seconds / 60)) minutes ago)"
        continue
      else
        log "INFO" "Found stale old-format lock for issue #$issue_number, re-enqueueing"
        rm "$old_lock_file"
      fi
    fi
    
    # Create a project-specific lock file
    timestamp=$(date)
    log "INFO" "Creating lock file for issue #$issue_number in project $project_id at $timestamp"
    echo "Enqueued at $timestamp" > "$project_lock_file"
    echo "Project ID: $project_id" >> "$project_lock_file"
    echo "Project Path: $PROJECT_PATH" >> "$project_lock_file"
    
    if [ ! -f "$project_lock_file" ]; then
      log "ERROR" "Failed to create lock file for issue #$issue_number in project $project_id"
      continue
    fi
    
    # Enqueue the issue using Python
    log "INFO" "Processing issue #$issue_number: $issue_title"
    source "$PROJECT_PATH/.autonomous-claude/venv/bin/activate"
    
    # Use a simpler approach to avoid subshell issues
    cd "$PROJECT_PATH"
    python3 -c "import sys; sys.path.append('$PROJECT_PATH/.autonomous-claude'); from tasks import enqueue_process_github_issue; print(f'Enqueued job with ID: {enqueue_process_github_issue($issue_number)}')" > "$PROJECT_PATH/.autonomous-claude/logs/enqueue_output.txt"
    
    # Get the job ID from the output file
    job_id=$(cat "$PROJECT_PATH/.autonomous-claude/logs/enqueue_output.txt" | grep -o "Enqueued job with ID: .*" | sed 's/Enqueued job with ID: //')
    
    # Add job ID to lock file
    echo "Job ID: $job_id" >> "$project_lock_file"
    log "INFO" "Enqueued issue #$issue_number with job ID: $job_id in project $project_id"
    
    # Verify lock file contents
    log "INFO" "Lock file contents for issue #$issue_number in project $project_id:"
    cat "$project_lock_file" | while read line; do
      log "INFO" "  $line"
    done
  done
}

check_github_prs() {
  log "INFO" "Checking GitHub PRs..."
  
  # Ensure required directories exist
  mkdir -p "$PROJECT_PATH/.autonomous-claude/tasks"
  mkdir -p "$PROJECT_PATH/.autonomous-claude/reviews"
  mkdir -p "$PROJECT_PATH/.autonomous-claude/data"
  mkdir -p "$PROJECT_PATH/.autonomous-claude/task_analysis"
  
  # Get or create project ID for isolation
  project_id_file="$PROJECT_PATH/.autonomous-claude/project_id"
  if [ -f "$project_id_file" ]; then
    project_id=$(cat "$project_id_file")
    log "INFO" "Using existing project ID for PR checks: $project_id"
  else
    # Create a unique project ID based on the absolute path hash
    project_id=$(echo "$PROJECT_PATH" | shasum -a 256 | cut -c1-16)
    echo "$project_id" > "$project_id_file"
    log "INFO" "Created new project ID for PR checks: $project_id"
  fi
  
  # Get the list of open PRs with detailed information
  prs=$(gh pr list --repo "$GITHUB_REPO" --state open --json number,title,url,author,updatedAt,commits,additions,deletions,changedFiles)
  
  # Check if there are any PRs
  if [ -z "$prs" ] || [ "$prs" == "[]" ]; then
    log "INFO" "No open PRs found."
    return 0
  fi
  
  # Set necessary environment variables for the Python scripts
  export PROJECT_PATH="$PROJECT_PATH"
  export GITHUB_USERNAME="$GITHUB_USERNAME"
  export REVIEW_ONLY_OWN_PRS="$REVIEW_ONLY_OWN_PRS"
  export PR_AUTO_REVIEW="$PR_AUTO_REVIEW"
  export PR_AUTO_REVIEW_DELAY="$PR_AUTO_REVIEW_DELAY"
  export PR_REVIEW_MAX_RETRIES="$PR_REVIEW_MAX_RETRIES"
  export PR_REVIEW_RETRY_DELAY="$PR_REVIEW_RETRY_DELAY"
  export MIN_REREVIEW_HOURS="$MIN_REREVIEW_HOURS"
  
  # Create PR checker script if it doesn't exist
  pr_checker_script="$PROJECT_PATH/.autonomous-claude/github_pr_checker.py"
  if [ ! -f "$pr_checker_script" ]; then
    log "ERROR" "PR checker script not found: $pr_checker_script"
    return 1
  fi
  
  # Make the script executable
  chmod +x "$pr_checker_script"
  
  # Process PRs using the Python script for new PRs
  log "INFO" "Running GitHub PR checker script for new PRs..."
  
  cd "$PROJECT_PATH"
  source "$PROJECT_PATH/.autonomous-claude/venv/bin/activate"
  echo "$prs" | python3 "$pr_checker_script"
  script_exit=$?
  
  if [ $script_exit -ne 0 ]; then
    log "ERROR" "GitHub PR checker script failed with exit code $script_exit"
    return 1
  fi
  
  # Process PRs using the update detector script if enabled
  if [ "$PR_UPDATE_DETECTION" = "true" ]; then
    pr_update_detector="$PROJECT_PATH/.autonomous-claude/github_pr_update_detector.py"
    
    if [ ! -f "$pr_update_detector" ]; then
      log "ERROR" "PR update detector script not found: $pr_update_detector"
      return 1
    fi
    
    # Make the script executable
    chmod +x "$pr_update_detector"
    
    log "INFO" "Running GitHub PR update detector for changed PRs..."
    echo "$prs" | python3 "$pr_update_detector"
    detector_exit=$?
    
    if [ $detector_exit -ne 0 ]; then
      log "ERROR" "GitHub PR update detector failed with exit code $detector_exit"
      # Continue anyway, as this is not critical
    fi
  fi
}

generate_documentation() {
  log "INFO" "Generating project documentation..."
  
  # Enqueue documentation generation task
  job_id=$(python3 -c "
import sys
sys.path.append('$PROJECT_PATH/.autonomous-claude')
from tasks import enqueue_update_documentation
print(enqueue_update_documentation())
")
  
  log "INFO" "Enqueued documentation generation job with ID: $job_id"
}

start_dashboard() {
  log "INFO" "Starting RQ dashboard..."
  
  # Check if dashboard is already running
  if [ -f "$PROJECT_PATH/.autonomous-claude/dashboard.pid" ]; then
    dashboard_pid=$(cat "$PROJECT_PATH/.autonomous-claude/dashboard.pid")
    if ps -p $dashboard_pid > /dev/null; then
      log "INFO" "Dashboard already running with PID: $dashboard_pid"
      log "INFO" "Access the dashboard at: http://localhost:9181"
      return 0
    fi
  fi
  
  # Start RQ dashboard
  source "$PROJECT_PATH/.autonomous-claude/venv/bin/activate"
  rq-dashboard -H $(echo $REDIS_URL | cut -d'/' -f3) > "$PROJECT_PATH/.autonomous-claude/logs/dashboard.log" 2>&1 &
  DASHBOARD_PID=$!
  echo $DASHBOARD_PID > "$PROJECT_PATH/.autonomous-claude/dashboard.pid"
  log "INFO" "Dashboard started with PID: $DASHBOARD_PID"
  log "INFO" "Access the dashboard at: http://localhost:9181"
}

stop_services() {
  log "INFO" "Stopping services..."
  
  # Stop worker
  if [ -f "$PROJECT_PATH/.autonomous-claude/worker.pid" ]; then
    worker_pid=$(cat "$PROJECT_PATH/.autonomous-claude/worker.pid")
    if ps -p $worker_pid > /dev/null; then
      kill $worker_pid
      log "INFO" "Worker stopped (PID: $worker_pid)"
    fi
    rm "$PROJECT_PATH/.autonomous-claude/worker.pid"
  fi
  
  # Stop dashboard
  if [ -f "$PROJECT_PATH/.autonomous-claude/dashboard.pid" ]; then
    dashboard_pid=$(cat "$PROJECT_PATH/.autonomous-claude/dashboard.pid")
    if ps -p $dashboard_pid > /dev/null; then
      kill $dashboard_pid
      log "INFO" "Dashboard stopped (PID: $dashboard_pid)"
    fi
    rm "$PROJECT_PATH/.autonomous-claude/dashboard.pid"
  fi
  
  log "INFO" "All services stopped."
}

setup_mcp_servers() {
  log "INFO" "Setting up MCP servers..."
  
  # Check if MCP servers are enabled
  if [ "$MCP_SERVERS_ENABLED" != "true" ]; then
    log "INFO" "MCP servers are disabled. Skipping setup."
    return 0
  fi
  
  # Check if the GitHub MCP server is defined in the config
  if [ -n "$MCP_SERVER_GITHUB" ]; then
    log "INFO" "Setting up GitHub MCP server..."
    # Get GitHub token
    GITHUB_TOKEN=$(gh auth token)
    
    # Configure MCP server
    $CLAUDE_CODE_PATH mcp add github_mcp "$MCP_SERVER_GITHUB" || {
      log "WARNING" "Failed to add GitHub MCP server. It might already be configured."
    }
  else
    log "INFO" "GitHub MCP server not defined in config. Skipping."
  fi
  
  # Add other MCP servers here as needed
  
  log "INFO" "MCP servers setup complete."
}

main_loop() {
  log "INFO" "Starting main loop with polling interval of $POLLING_INTERVAL seconds."
  
  while true; do
    # Check for GitHub issues
    check_github_issues
    
    # Check for GitHub PRs that need review
    if [ "$PR_REVIEW_ENABLED" = "true" ]; then
      check_github_prs
    fi
    
    # Sleep for the polling interval
    log "DEBUG" "Sleeping for $POLLING_INTERVAL seconds..."
    sleep $POLLING_INTERVAL
  done
}

show_help() {
  echo "Autonomous Claude - A utility for running autonomous coding workflows"
  echo ""
  echo "Usage: $0 [command]"
  echo ""
  echo "Commands:"
  echo "  start        Start the autonomous coding service"
  echo "  stop         Stop all services"
  echo "  init         Initialize project for autonomous coding"
  echo "  docs         Generate project documentation"
  echo "  dashboard    Start the RQ dashboard"
  echo "  status       Show status of all services"
  echo "  help         Show this help message"
  echo ""
  echo "For more information, see the documentation."
}

show_status() {
  echo "Autonomous Claude Status"
  echo "======================="
  echo ""
  echo "Project: $PROJECT_PATH"
  echo "GitHub Repository: $GITHUB_REPO"
  echo ""
  
  # Check worker status
  if [ -f "$PROJECT_PATH/.autonomous-claude/worker.pid" ]; then
    worker_pid=$(cat "$PROJECT_PATH/.autonomous-claude/worker.pid")
    if ps -p $worker_pid > /dev/null; then
      echo -e "${GREEN}Worker: Running (PID: $worker_pid)${NC}"
      echo "Running processes:"
      ps aux | grep -v grep | grep claude | head -n 5
    else
      echo -e "${RED}Worker: Not running (stale PID file)${NC}"
    fi
  else
    echo -e "${RED}Worker: Not running${NC}"
  fi
  
  # Check dashboard status
  if [ -f "$PROJECT_PATH/.autonomous-claude/dashboard.pid" ]; then
    dashboard_pid=$(cat "$PROJECT_PATH/.autonomous-claude/dashboard.pid")
    if ps -p $dashboard_pid > /dev/null; then
      echo -e "${GREEN}Dashboard: Running (PID: $dashboard_pid)${NC}"
      echo "Dashboard URL: http://localhost:9181"
    else
      echo -e "${RED}Dashboard: Not running (stale PID file)${NC}"
    fi
  else
    echo -e "${RED}Dashboard: Not running${NC}"
  fi
  
  # Check Redis status
  if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}Redis: Running${NC}"
  else
    echo -e "${RED}Redis: Not running${NC}"
  fi
  
  # Check queue status
  source "$PROJECT_PATH/.autonomous-claude/venv/bin/activate"
  queue_info=$(python3 -c "
from redis import Redis
from rq import Queue
redis_conn = Redis.from_url('$REDIS_URL')
queue = Queue('$REDIS_QUEUE', connection=redis_conn)
print(f'Jobs in queue: {len(queue)}')
print(f'Failed jobs: {len(queue.failed_job_registry)}')
print(f'Completed jobs: {len(queue.finished_job_registry)}')

print('\nActive jobs:')
for job in queue.get_jobs():
    print(f'- Job ID: {job.id} | Function: {job.func_name}')

print('\nFailed jobs:')
for job_id in queue.failed_job_registry.get_job_ids():
    job = queue.fetch_job(job_id)
    if job:
        print(f'- Job ID: {job.id} | Function: {job.func_name} | Error: {job.exc_info}')
    else:
        print(f'- Job ID: {job_id} (details not available)')
")
  echo ""
  echo "Queue Status:"
  echo "$queue_info"
  
  # Show active locks
  echo ""
  echo "Active Tasks:"
  if [ -d "$PROJECT_PATH/.autonomous-claude/tasks" ]; then
    find "$PROJECT_PATH/.autonomous-claude/tasks" -name "*.lock" | while read lock_file; do
      issue_number=$(basename "$lock_file" .lock)
      lock_time=$(stat -f "%m" "$lock_file")
      current_time=$(date +%s)
      age_minutes=$(( (current_time - lock_time) / 60 ))
      job_id=$(grep "Job ID:" "$lock_file" | cut -d ":" -f 2 | tr -d " ")
      
      echo "Issue #$issue_number - Started $age_minutes minutes ago - Job ID: $job_id"
      echo "Lock file contents:"
      cat "$lock_file" | sed 's/^/  /'
    done
  else
    echo "No active tasks found"
  fi
  
  # Show active PR reviews
  echo ""
  echo "Active PR Reviews:"
  if [ -d "$PROJECT_PATH/.autonomous-claude/reviews" ]; then
    find "$PROJECT_PATH/.autonomous-claude/reviews" -name "*.lock" | while read lock_file; do
      pr_number=$(basename "$lock_file" .lock)
      lock_time=$(stat -f "%m" "$lock_file")
      current_time=$(date +%s)
      age_minutes=$(( (current_time - lock_time) / 60 ))
      job_id=$(grep "Job ID:" "$lock_file" | cut -d ":" -f 2 | tr -d " " 2>/dev/null || echo "N/A")
      
      echo "PR #$pr_number - Started $age_minutes minutes ago - Job ID: $job_id"
      echo "Lock file contents:"
      cat "$lock_file" | sed 's/^/  /'
    done
  fi
  
  # Show recent PR reviews
  echo ""
  echo "Recent PR Reviews:"
  if [ -d "$PROJECT_PATH/.autonomous-claude/reviews" ]; then
    find "$PROJECT_PATH/.autonomous-claude/reviews" -name "pr-*-review.md" | sort -r | head -n 5 | while read review_file; do
      pr_number=$(basename "$review_file" | sed 's/pr-\(.*\)-review.md/\1/')
      review_time=$(stat -f "%m" "$review_file")
      review_date=$(date -r "$review_time" "+%Y-%m-%d %H:%M:%S")
      
      echo "PR #$pr_number - Reviewed on $review_date"
    done
  else
    echo "No PR reviews found"
  fi
  
  # Show recent worker logs
  echo ""
  echo "Recent Worker Logs:"
  if [ -f "$PROJECT_PATH/.autonomous-claude/logs/worker.log" ]; then
    tail -n 10 "$PROJECT_PATH/.autonomous-claude/logs/worker.log"
  else
    echo "No worker logs available"
  fi
  
  # Show recent main logs
  echo ""
  echo "Recent Main Logs:"
  tail -n 5 "$LOG_FILE" 2>/dev/null || echo "No logs available"
}

# ===== Main Script =====

# Create .autonomous-claude directory if it doesn't exist
mkdir -p "$PROJECT_PATH/.autonomous-claude"

# Load config if it exists
if [ -f "$CONFIG_FILE" ]; then
  source "$CONFIG_FILE"
fi

# Process command line arguments
COMMAND=${1:-"help"}

case $COMMAND in
  "start")
    check_requirements
    init_project
    setup_mcp_servers
    start_redis_worker
    start_dashboard
    main_loop
    ;;
  "stop")
    stop_services
    ;;
  "init")
    check_requirements
    init_project
    setup_mcp_servers
    ;;
  "docs")
    check_requirements
    generate_documentation
    ;;
  "dashboard")
    check_requirements
    start_dashboard
    ;;
  "status")
    show_status
    ;;
  "help")
    show_help
    ;;
  *)
    echo "Unknown command: $COMMAND"
    show_help
    exit 1
    ;;
esac

exit 0