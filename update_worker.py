#!/usr/bin/env python3
import re

# Path to the worker.py file
worker_path = '/Users/avijitsarkar/personal_projects/autonomous-claude/.autonomous-claude/worker.py'

# Read the current file content
with open(worker_path, 'r') as f:
    content = f.read()

# Find all blocks like "# No more retries, report final failure"
pattern = r"""                # No more retries, report final failure
                logger\.error\(f"Claude Code execution failed after \{max_retries\} retries: \{e\}"\)
                return \{
                    'success': False,
                    'stdout': stdout_output,
                    'stderr': stderr_output,
                    'command_type': command_type,
                    'instruction_file': instruction_file,
                    'retries': retries
                \}"""

# Replacement with the fallback mechanism
replacement = """                # After max_retries with allowed_tools, try one more time with dangerously-skip-permissions
                if allowed_tools:
                    logger.warning(f"Claude Code execution failed with --allowed-tools. Trying with --dangerously-skip-permissions as last resort")
                    # Build a new command with dangerously-skip-permissions instead of allowed_tools
                    dangerous_command = command.copy()
                    # Remove the allowed_tools arguments
                    tools_index = -1
                    for i in range(len(dangerous_command) - 1):
                        if dangerous_command[i] == '--allowed-tools':
                            tools_index = i
                            break
                    
                    if tools_index >= 0:
                        dangerous_command.pop(tools_index + 1)  # Remove the tools list
                        dangerous_command.pop(tools_index)      # Remove --allowed-tools
                    
                    # Add the dangerous flag
                    dangerous_command.append('--dangerously-skip-permissions')
                    
                    logger.info(f"Running Claude Code with dangerous command: {' '.join(dangerous_command)}")
                    try:
                        process = subprocess.run(dangerous_command, capture_output=True, text=True, check=True)
                        return {
                            'success': True,
                            'stdout': process.stdout,
                            'stderr': process.stderr,
                            'command_type': command_type,
                            'instruction_file': instruction_file,
                            'retries': retries + 1,
                            'fallback_to_dangerous': True
                        }
                    except Exception as dangerous_e:
                        logger.error(f"Claude Code execution failed even with --dangerously-skip-permissions: {dangerous_e}")
                
                # No more retries, and dangerous mode also failed (or wasn't tried), report final failure
                logger.error(f"Claude Code execution failed after {max_retries} retries: {e}")
                return {
                    'success': False,
                    'stdout': stdout_output,
                    'stderr': stderr_output,
                    'command_type': command_type,
                    'instruction_file': instruction_file,
                    'retries': retries,
                    'fallback_to_dangerous': allowed_tools is not None
                }"""

# Replace all occurrences of the pattern with the fallback mechanism
modified_content = re.sub(pattern, replacement, content)

# Save the modified content back to the file
with open(worker_path, 'w') as f:
    f.write(modified_content)

# Same for the "Error running Claude Code" case
error_pattern = r"""                logger\.error\(f"Error running Claude Code after \{max_retries\} retries: \{str\(e\)\}"\)
                return \{
                    'success': False,
                    'stdout': '',
                    'stderr': str\(e\),
                    'command_type': command_type,
                    'instruction_file': instruction_file,
                    'retries': retries
                \}"""

error_replacement = """                # Try dangerous mode as a last resort if we were using allowed_tools
                if allowed_tools:
                    logger.warning(f"Claude Code execution failed with --allowed-tools. Trying with --dangerously-skip-permissions as last resort")
                    # Build a new command with dangerously-skip-permissions instead of allowed_tools
                    dangerous_command = command.copy()
                    # Remove the allowed_tools arguments if present
                    tools_index = -1
                    for i in range(len(dangerous_command) - 1):
                        if dangerous_command[i] == '--allowed-tools':
                            tools_index = i
                            break
                    
                    if tools_index >= 0:
                        dangerous_command.pop(tools_index + 1)  # Remove the tools list
                        dangerous_command.pop(tools_index)      # Remove --allowed-tools
                    
                    # Add the dangerous flag
                    dangerous_command.append('--dangerously-skip-permissions')
                    
                    logger.info(f"Running Claude Code with dangerous command: {' '.join(dangerous_command)}")
                    try:
                        process = subprocess.run(dangerous_command, capture_output=True, text=True, check=True)
                        return {
                            'success': True,
                            'stdout': process.stdout,
                            'stderr': process.stderr,
                            'command_type': command_type,
                            'instruction_file': instruction_file,
                            'retries': retries + 1,
                            'fallback_to_dangerous': True
                        }
                    except Exception as dangerous_e:
                        logger.error(f"Claude Code execution failed even with --dangerously-skip-permissions: {dangerous_e}")
                
                logger.error(f"Error running Claude Code after {max_retries} retries: {str(e)}")
                return {
                    'success': False,
                    'stdout': '',
                    'stderr': str(e),
                    'command_type': command_type,
                    'instruction_file': instruction_file,
                    'retries': retries,
                    'fallback_to_dangerous': allowed_tools is not None
                }"""

# Read the current file content again after first modification
with open(worker_path, 'r') as f:
    content = f.read()

# Apply the second modification
modified_content = re.sub(error_pattern, error_replacement, content)

# Save the modified content back to the file
with open(worker_path, 'w') as f:
    f.write(modified_content)

print("Worker.py updated with fallback mechanism successfully!")
