import os
import sys
import json
import time
import subprocess
from redis import Redis
from rq import Worker, Queue
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

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
                ['gh', 'pr', 'view', issue_or_pr_number, '--json', 'title,body,number,url,files,additions,deletions,changedFiles'],
                text=True
            )
            pr_data = json.loads(pr_json)
            
            instructions.append(f"## Review Pull Request #{pr_data['number']}\n")
            instructions.append(f"**Title**: {pr_data['title']}\n")
            instructions.append(f"**URL**: {pr_data['url']}\n")
            instructions.append("**Description**:\n")
            instructions.append(f"{pr_data['body']}\n\n")
            
            instructions.append(f"**Changes**: +{pr_data.get('additions', 0)} / -{pr_data.get('deletions', 0)} in {pr_data.get('changedFiles', 0)} files\n\n")
            
            instructions.append("**Files Changed**:\n")
            for file in pr_data.get('files', []):
                instructions.append(f"- {file.get('path')}\n")
            
            instructions.append("\n## Your Task\n")
            instructions.append("1. Review the PR described above\n")
            instructions.append("2. Examine the code changes using `gh pr diff`\n")
            instructions.append("3. Analyze the code changes for:\n")
            instructions.append("   - Code quality issues\n")
            instructions.append("   - Potential bugs or logical errors\n")
            instructions.append("   - Security concerns\n")
            instructions.append("   - Performance considerations\n")
            instructions.append("   - Adherence to project coding standards\n")
            instructions.append("   - Completeness of implementation\n")
            instructions.append("4. Create a detailed review and save it to `.autonomous-claude/reviews/pr-{pr_number}-review.md`\n")
            instructions.append("5. Post your review as a comment on the PR using the GitHub CLI\n")
            
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
        # For regular prompts, use print mode (-p) as before
        command = [claude_path, '-p', prompt, '--dangerously-skip-permissions']
        
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
    lock_file = os.path.join(tasks_dir, f"{issue_number}.lock")
    
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
        
        # Update lock file to indicate completion
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
                # Import PR relationship module
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
                        time.sleep(10)
                        
                        # Import tasks module
                        from tasks import enqueue_review_pull_request
                        
                        # Enqueue PR review
                        job_id = enqueue_review_pull_request(pr_number)
                        logger.info(f"Enqueued PR review job with ID: {job_id}")
                        
                        # Update lock file with review information
                        with open(lock_file, 'a') as f:
                            f.write(f"Auto-review triggered: job ID {job_id}\n")
                except ImportError as e:
                    logger.error(f"Failed to import PR relationship module: {str(e)}")
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
    
    # Create a lock file to indicate the PR is being processed
    lock_file = os.path.join(reviews_dir, f"pr-{pr_number}.lock")
    if not os.path.exists(lock_file):
        with open(lock_file, 'w') as f:
            timestamp = datetime.now().isoformat()
            f.write(f"Review started: {timestamp}\n")
    
    # Import PR relationship module
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
            pass
        return {
            'success': True,
            'pr_number': pr_number,
            'completed_at': time.time(),
            'status': 'skipped'
        }
    
    # Run Claude to review the PR
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
    
    # Create and start the worker directly with the queue that already has the connection
    worker = Worker([queue], connection=redis_conn)
    worker.work()