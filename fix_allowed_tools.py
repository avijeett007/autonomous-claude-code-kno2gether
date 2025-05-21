#!/usr/bin/env python3
import re

# Path to the worker.py file
worker_path = '/Users/avijitsarkar/personal_projects/autonomous-claude/.autonomous-claude/worker.py'

# Read the current file content
with open(worker_path, 'r') as f:
    content = f.read()

# Add a function to format allowed_tools correctly
format_allowed_tools_func = '''
def format_allowed_tools(tools_str):
    """Format the allowed tools parameter for Claude CLI
    
    The Claude CLI expects --allowed-tools to be comma-separated, not space-separated
    """
    if not tools_str:
        return tools_str
        
    # If it contains spaces but no commas, convert spaces to commas
    if ' ' in tools_str and ',' not in tools_str:
        return tools_str.replace(' ', ',')
    return tools_str
'''

# Add the function after the imports section
# Find the last import statement
last_import_match = re.search(r'^import [^\n]+$', content, re.MULTILINE)
if last_import_match:
    insert_pos = last_import_match.end()
    content = content[:insert_pos] + "\n\n" + format_allowed_tools_func + content[insert_pos:]

# Replace all occurrences of extending command with allowed_tools
pattern = r"command\.extend\(\['--allowed-tools', allowed_tools\]\)"
replacement = "command.extend(['--allowed-tools', format_allowed_tools(allowed_tools)])"
content = re.sub(pattern, replacement, content)

# Save the modified content back to the file
with open(worker_path, 'w') as f:
    f.write(content)

print("Fixed allowed_tools formatting in worker.py")
