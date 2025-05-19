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
REVIEW_ONLY_OWN_PRS=true
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
  
  # Create required directories
  mkdir -p "$PROJECT_PATH/.autonomous-claude/logs"
  mkdir -p "$PROJECT_PATH/.autonomous-claude/tasks"
  mkdir -p "$PROJECT_PATH/.autonomous-claude/templates"
  mkdir -p "$DOCS_PATH"
  
  # Check if CLAUDE.md exists, if not create it
  if [ ! -f "$PROJECT_PATH/CLAUDE.md" ]; then
    log "INFO" "CLAUDE.md not found, initializing with Claude Code..."
    $CLAUDE_CODE_PATH /init
  fi
  
  # Check if .claude directory exists, if not create it
  if [ ! -d "$PROJECT_PATH/.claude" ]; then
    log "INFO" ".claude directory not found, creating..."
    mkdir -p "$PROJECT_PATH/.claude/commands"
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
REVIEW_ONLY_OWN_PRS=true

# Paths
CLAUDE_CODE_PATH="$CLAUDE_CODE_PATH"

# MCP servers
MCP_SERVERS_ENABLED=true
# Add any custom MCP servers here
# Example: MCP_SERVER_GITHUB="docker run -i --rm -e GITHUB_PERSONAL_ACCESS_TOKEN=\$GITHUB_TOKEN ghcr.io/github/github-mcp-server"
EOF
    log "INFO" "Created default configuration file at $CONFIG_FILE"
  fi
  
  # Create custom Claude commands
  create_claude_commands
  
  log "INFO" "Project initialization complete."
}

create_claude_commands() {
  log "INFO" "Creating custom Claude commands..."
  
  # Command: Generate comprehensive project documentation
  cat > "$PROJECT_PATH/.claude/commands/document-project.md" << EOF
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
  cat > "$PROJECT_PATH/.claude/commands/analyze-github-issue.md" << EOF
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
  cat > "$PROJECT_PATH/.claude/commands/implement-github-issue.md" << EOF
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
from redis import Redis
from rq import Worker, Queue, Connection
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
def run_claude_code_headless(prompt, allowed_tools=None):
    """Run Claude Code in headless mode with the given prompt"""
    claude_path = os.environ.get('CLAUDE_CODE_PATH', 'claude')
    command = [claude_path, '-p', prompt]
    
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
    
    # Step 1: Analyze the issue and create a plan
    project_path = os.environ.get('PROJECT_PATH', os.getcwd())
    analyze_prompt = f"/project:analyze-github-issue {issue_number}"
    
    result = run_claude_code_headless(
        analyze_prompt,
        "Bash(gh:*) Edit Run"
    )
    
    if not result['success']:
        logger.error(f"Failed to analyze issue #{issue_number}")
        return {
            'success': False,
            'stage': 'analyze',
            'error': result['stderr']
        }
    
    logger.info(f"Successfully analyzed issue #{issue_number}")
    
    # Step 2: Implement the solution
    implement_prompt = f"/project:implement-github-issue {issue_number}"
    
    result = run_claude_code_headless(
        implement_prompt,
        "Bash(gh:*,git:*) Edit Run Test"
    )
    
    if not result['success']:
        logger.error(f"Failed to implement solution for issue #{issue_number}")
        return {
            'success': False,
            'stage': 'implement',
            'error': result['stderr']
        }
    
    logger.info(f"Successfully implemented solution for issue #{issue_number}")
    
    return {
        'success': True,
        'issue_number': issue_number,
        'completed_at': time.time()
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

# Worker loop
if __name__ == '__main__':
    logger.info(f"Starting worker for queue: {queue_name}")
    
    with Connection(redis_conn):
        worker = Worker([queue])
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

# Add parent directory to path so we can import worker
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from worker import process_github_issue, update_project_documentation

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
EOF

    log "INFO" "Created tasks script at $PROJECT_PATH/.autonomous-claude/tasks.py"
  fi
  
  # Start worker process in the background
  source "$PROJECT_PATH/.autonomous-claude/venv/bin/activate"
  export PYTHONPATH="$PROJECT_PATH/.autonomous-claude:$PYTHONPATH"
  export CLAUDE_CODE_PATH="$CLAUDE_CODE_PATH"
  export PROJECT_PATH="$PROJECT_PATH"
  export REDIS_URL="$REDIS_URL"
  export REDIS_QUEUE="$REDIS_QUEUE"
  
  log "INFO" "Starting worker in the background..."
  python3 "$PROJECT_PATH/.autonomous-claude/worker.py" > "$PROJECT_PATH/.autonomous-claude/logs/worker_stdout.log" 2>&1 &
  WORKER_PID=$!
  echo $WORKER_PID > "$PROJECT_PATH/.autonomous-claude/worker.pid"
  log "INFO" "Worker started with PID: $WORKER_PID"
}

check_github_issues() {
  log "INFO" "Checking GitHub issues..."
  
  # Ensure tasks directory exists
  mkdir -p "$PROJECT_PATH/.autonomous-claude/tasks"
  
  # Get the list of open issues with the specified label
  issues=$(gh issue list --repo "$GITHUB_REPO" --label "$GITHUB_ISSUE_LABEL" --state open --json number,title,url)
  
  # Check if there are any issues
  if [ -z "$issues" ] || [ "$issues" == "[]" ]; then
    log "INFO" "No open issues with label '$GITHUB_ISSUE_LABEL' found."
    return 0
  fi
  
  # Set necessary environment variables for the Python script
  export PROJECT_PATH="$PROJECT_PATH"
  
  # Make the script executable
  chmod +x "$PROJECT_PATH/.autonomous-claude/github_issue_checker.py"
  
  # Process issues using the standalone Python script
  log "INFO" "Running GitHub issue checker script..."
  
  cd "$PROJECT_PATH"
  source "$PROJECT_PATH/.autonomous-claude/venv/bin/activate"
  echo "$issues" | python3 "$PROJECT_PATH/.autonomous-claude/github_issue_checker.py"
  script_exit=$?
  
  if [ $script_exit -ne 0 ]; then
    log "ERROR" "GitHub issue checker script failed with exit code $script_exit"
    return 1
  fi
}

check_github_prs() {
  log "INFO" "Checking GitHub PRs..."
  
  # Ensure tasks directory exists
  mkdir -p "$PROJECT_PATH/.autonomous-claude/tasks"
  
  # Get the list of open PRs
  prs=$(gh pr list --repo "$GITHUB_REPO" --state open --json number,title,url,author)
  
  # Check if there are any PRs
  if [ -z "$prs" ] || [ "$prs" == "[]" ]; then
    log "INFO" "No open PRs found."
    return 0
  fi
  
  # Set necessary environment variables for the Python script
  export PROJECT_PATH="$PROJECT_PATH"
  export GITHUB_USERNAME="$GITHUB_USERNAME"
  export REVIEW_ONLY_OWN_PRS="$REVIEW_ONLY_OWN_PRS"
  
  # Create PR checker script if it doesn't exist
  if [ ! -f "$PROJECT_PATH/.autonomous-claude/github_pr_checker.py" ]; then
    log "INFO" "PR checker script not found, skipping PR checks."
    return 0
  fi
  
  # Make the script executable
  chmod +x "$PROJECT_PATH/.autonomous-claude/github_pr_checker.py"
  
  # Process PRs using the standalone Python script
  log "INFO" "Running GitHub PR checker script..."
  
  cd "$PROJECT_PATH"
  source "$PROJECT_PATH/.autonomous-claude/venv/bin/activate"
  echo "$prs" | python3 "$PROJECT_PATH/.autonomous-claude/github_pr_checker.py"
  script_exit=$?
  
  if [ $script_exit -ne 0 ]; then
    log "ERROR" "GitHub PR checker script failed with exit code $script_exit"
    return 1
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
")
  echo ""
  echo "Queue Status:"
  echo "$queue_info"
  
  # Show recent logs
  echo ""
  echo "Recent Logs:"
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
