
def run_claude_code_headless(prompt, allowed_tools=None, max_retries=3, retry_delay=30):
    """Run Claude Code in headless mode with the given prompt
    
    Args:
        prompt: The prompt to execute with Claude Code
        allowed_tools: Tools to allow Claude to use
        max_retries: Maximum number of retry attempts (default: 3)
        retry_delay: Initial delay between retries in seconds (default: 30)
    """
    # Initialize variables
    claude_path = os.environ.get('CLAUDE_CODE_PATH', 'claude')
    command_type = None
    instruction_file = None
    command = None
    issue_or_pr_number = None
    
    # Parse the command/prompt and prepare execution
    try:
        # Check if the prompt starts with a custom command
        if prompt.startswith('/project:'):
            parts = prompt.split(' ')
            if len(parts) >= 1:
                command_with_prefix = parts[0]
                command_type = command_with_prefix.replace('/project:', '')
                
                if len(parts) >= 2:
                    issue_or_pr_number = parts[1]
            
            # Create instruction file for different commands
            if command_type in ['analyze-github-issue', 'implement-github-issue', 'document-project', 'review-pull-request']:
                instruction_file = create_instruction_file(command_type, issue_or_pr_number)
            else:
                # Fallback for unknown custom commands
                command_type = 'custom-command'
                instruction_file = create_instruction_file(command_type, prompt=prompt)
        
            logger.info(f"Running Claude Code with file-based instructions for: {command_type}")
            logger.info(f"Instruction file: {instruction_file}")
            
            # Run Claude in print mode with the instruction file
            file_prompt = f"Read and execute the instructions in this file: {instruction_file}"
            command = [claude_path, '-p', file_prompt]
            
            # Either use allowed_tools (more secure) or dangerously-skip-permissions (less secure)
            if allowed_tools:
                command.extend(['--allowed-tools', allowed_tools])
            else:
                command.append('--dangerously-skip-permissions')
        else:
            # Direct execution of prompt
            command = [claude_path, '-p', prompt]
            command_type = 'direct-prompt'
            
            # Either use allowed_tools (more secure) or dangerously-skip-permissions (less secure)
            if allowed_tools:
                command.extend(['--allowed-tools', allowed_tools])
            else:
                command.append('--dangerously-skip-permissions')
            
            logger.info(f"Running Claude Code with direct prompt")
    except Exception as e:
        logger.error(f"Error preparing Claude Code command: {str(e)}")
        return {
            'success': False,
            'stdout': '',
            'stderr': str(e),
            'command_type': command_type or 'unknown',
            'instruction_file': instruction_file,
            'retries': 0
        }
        
    # Execute command with retries
    retries = 0
    current_delay = retry_delay
    
    while retries <= max_retries:
        try:
            logger.info(f"Running Claude Code with command: {' '.join(command)}")
            if retries > 0:
                logger.info(f"Retry attempt {retries} of {max_retries}")
                
            # Run the command and capture output
            process = subprocess.run(command, capture_output=True, text=True, check=True)
            
            stdout = process.stdout
            stderr = process.stderr
            
            # Success! Return the result
            return {
                'success': True,
                'stdout': stdout,
                'stderr': stderr,
                'command_type': command_type,
                'instruction_file': instruction_file,
                'retries': retries
            }
                
        except subprocess.CalledProcessError as e:
            stderr_output = e.stderr if hasattr(e, 'stderr') else str(e)
            stdout_output = e.stdout if hasattr(e, 'stdout') else ''
            
            # If we have retries left, wait and try again
            if retries < max_retries:
                retries += 1
                logger.warning(f"Claude Code execution failed (attempt {retries}): {e}")
                logger.warning(f"Waiting {current_delay} seconds before retrying...")
                time.sleep(current_delay)
                # Exponential backoff for next retry
                current_delay = min(current_delay * 2, 300)  # Cap at 5 minutes
            else:
                # No more retries, report final failure
                logger.error(f"Claude Code execution failed after {max_retries} retries: {e}")
                return {
                    'success': False,
                    'stdout': stdout_output,
                    'stderr': stderr_output,
                    'command_type': command_type,
                    'instruction_file': instruction_file,
                    'retries': retries
                }
        except Exception as e:
            # For other exceptions, also implement retry
            if retries < max_retries:
                retries += 1
                logger.warning(f"Error running Claude Code (attempt {retries}): {str(e)}")
                logger.warning(f"Waiting {current_delay} seconds before retrying...")
                time.sleep(current_delay)
                # Exponential backoff for next retry
                current_delay = min(current_delay * 2, 300)  # Cap at 5 minutes
            else:
                logger.error(f"Error running Claude Code after {max_retries} retries: {str(e)}")
                return {
                    'success': False,
                    'stdout': '',
                    'stderr': str(e),
                    'command_type': command_type,
                    'instruction_file': instruction_file,
                    'retries': retries
                }
            process = subprocess.run(command, capture_output=True, text=True, check=True)
            
            stdout = process.stdout
            stderr = process.stderr
            
            # Success! Return the result
            return {
