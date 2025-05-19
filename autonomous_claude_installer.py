#!/usr/bin/env python3
# autonomous_claude_installer.py
#
# Installation script for the Autonomous Claude utility
# This script will set up all necessary components for the autonomous coding workflow

import os
import sys
import subprocess
import platform
import json
import shutil
from pathlib import Path

# Colors for output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_color(color, message):
    """Print a colored message"""
    print(f"{color}{message}{Colors.ENDC}")

def run_command(command, check=True, capture_output=False):
    """Run a shell command and handle errors"""
    try:
        result = subprocess.run(
            command, 
            check=check, 
            shell=True, 
            text=True,
            capture_output=capture_output
        )
        return result
    except subprocess.CalledProcessError as e:
        print_color(Colors.RED, f"Error running command: {command}")
        print_color(Colors.RED, f"Error details: {str(e)}")
        if not check:
            return e
        sys.exit(1)

def check_system():
    """Check if the system is supported"""
    if platform.system() != "Darwin":
        print_color(Colors.RED, "This installer currently only supports macOS.")
        print_color(Colors.YELLOW, "For other platforms, please follow the manual installation instructions.")
        sys.exit(1)
    
    print_color(Colors.GREEN, "✓ System check passed")

def check_requirements():
    """Check if all requirements are met"""
    requirements_met = True
    
    # Check for brew
    if shutil.which("brew") is None:
        print_color(Colors.RED, "✗ Homebrew is not installed")
        print_color(Colors.YELLOW, "Please install Homebrew from https://brew.sh/")
        requirements_met = False
    else:
        print_color(Colors.GREEN, "✓ Homebrew is installed")
    
    # Check for Python 3
    if shutil.which("python3") is None:
        print_color(Colors.RED, "✗ Python 3 is not installed")
        print_color(Colors.YELLOW, "Please install Python 3 using: brew install python3")
        requirements_met = False
    else:
        print_color(Colors.GREEN, "✓ Python 3 is installed")
    
    # Check for npm
    if shutil.which("npm") is None:
        print_color(Colors.RED, "✗ npm is not installed")
        print_color(Colors.YELLOW, "Please install Node.js using: brew install node")
        requirements_met = False
    else:
        print_color(Colors.GREEN, "✓ npm is installed")
    
    # Check for Claude Code
    if shutil.which("claude") is None:
        print_color(Colors.YELLOW, "! Claude Code is not installed")
        print_color(Colors.YELLOW, "We will install it during setup.")
    else:
        print_color(Colors.GREEN, "✓ Claude Code is installed")
    
    # Check for GitHub CLI
    if shutil.which("gh") is None:
        print_color(Colors.YELLOW, "! GitHub CLI is not installed")
        print_color(Colors.YELLOW, "We will install it during setup.")
    else:
        print_color(Colors.GREEN, "✓ GitHub CLI is installed")
    
    # Check for Redis
    if shutil.which("redis-cli") is None:
        print_color(Colors.YELLOW, "! Redis is not installed")
        print_color(Colors.YELLOW, "We will install it during setup.")
    else:
        print_color(Colors.GREEN, "✓ Redis is installed")
    
    if not requirements_met:
        print_color(Colors.RED, "Please install the missing requirements and run the installer again.")
        sys.exit(1)

def install_dependencies():
    """Install all required dependencies"""
    # Install GitHub CLI if not present
    if shutil.which("gh") is None:
        print_color(Colors.BLUE, "Installing GitHub CLI...")
        run_command("brew install gh")
        print_color(Colors.GREEN, "✓ GitHub CLI installed")
    
    # Install Redis if not present
    if shutil.which("redis-cli") is None:
        print_color(Colors.BLUE, "Installing Redis...")
        run_command("brew install redis")
        run_command("brew services start redis")
        print_color(Colors.GREEN, "✓ Redis installed and started")
    
    # Install Claude Code if not present
    if shutil.which("claude") is None:
        print_color(Colors.BLUE, "Installing Claude Code...")
        run_command("npm install -g @anthropic-ai/claude-code")
        print_color(Colors.GREEN, "✓ Claude Code installed")
    
    print_color(Colors.GREEN, "✓ All dependencies installed")

def setup_github_authentication():
    """Ensure GitHub CLI is authenticated"""
    # Check if already authenticated
    result = run_command("gh auth status", check=False, capture_output=True)
    if result.returncode == 0:
        print_color(Colors.GREEN, "✓ Already authenticated with GitHub")
        return
    
    print_color(Colors.BLUE, "Setting up GitHub authentication...")
    print_color(Colors.YELLOW, "You will be prompted to authenticate with GitHub.")
    run_command("gh auth login")
    print_color(Colors.GREEN, "✓ GitHub authentication complete")

def setup_claude_code():
    """Set up Claude Code configuration"""
    print_color(Colors.BLUE, "Setting up Claude Code...")
    
    # Check if Claude Code is already set up
    home_dir = Path.home()
    claude_config = home_dir / ".claude-code"
    
    if not claude_config.exists():
        claude_config.mkdir(exist_ok=True)
    
    # Create basic config if not exists
    config_file = claude_config / "config.json"
    if not config_file.exists():
        default_config = {
            "autoUpdaterStatus": "enabled",
            "theme": "dark",
            "customApiKeyResponses": {
                "approved": [],
                "rejected": []
            },
            "hasCompletedOnboarding": True,
            "mcpServers": {}
        }
        
        with open(config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
    
    print_color(Colors.GREEN, "✓ Claude Code configuration set up")

def install_utility(destination):
    """Install the utility script and README"""
    print_color(Colors.BLUE, "Installing Autonomous Claude utility...")
    
    # Create destination directory if it doesn't exist
    os.makedirs(destination, exist_ok=True)
    
    # Get the directory of the current script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Copy the script and README
    script_source = os.path.join(current_dir, "autonomous-claude.sh")
    readme_source = os.path.join(current_dir, "README.md")
    
    script_dest = os.path.join(destination, "autonomous-claude.sh")
    readme_dest = os.path.join(destination, "README.md")
    
    shutil.copy2(script_source, script_dest)
    shutil.copy2(readme_source, readme_dest)
    
    # Make the script executable
    os.chmod(script_dest, 0o755)
    
    # Create symlink
    symlink_path = "/usr/local/bin/autonomous-claude"
    try:
        if os.path.exists(symlink_path):
            os.remove(symlink_path)
        os.symlink(script_dest, symlink_path)
        print_color(Colors.GREEN, f"✓ Created symlink at {symlink_path}")
    except Exception as e:
        print_color(Colors.YELLOW, f"Could not create symlink: {str(e)}")
        print_color(Colors.YELLOW, f"You may need to manually create a symlink or add {destination} to your PATH")
    
    print_color(Colors.GREEN, f"✓ Autonomous Claude installed to {destination}")
    print_color(Colors.GREEN, f"✓ README installed to {readme_dest}")

def main():
    """Main installation function"""
    print_color(Colors.HEADER, "Autonomous Claude Installer")
    print_color(Colors.HEADER, "==========================")
    print("This installer will set up the Autonomous Claude utility for automated coding workflows.")
    print("")
    
    # Check system compatibility
    check_system()
    
    # Check requirements
    check_requirements()
    
    # Ask for installation confirmation
    print("")
    confirm = input("Do you want to proceed with the installation? (y/n): ")
    if confirm.lower() != 'y':
        print_color(Colors.YELLOW, "Installation cancelled.")
        sys.exit(0)
    
    # Install dependencies
    install_dependencies()
    
    # Set up GitHub authentication
    setup_github_authentication()
    
    # Set up Claude Code
    setup_claude_code()
    
    # Ask for installation directory
    print("")
    default_dest = os.path.expanduser("~/autonomous-claude")
    destination = input(f"Enter installation directory (default: {default_dest}): ")
    destination = destination.strip() or default_dest
    destination = os.path.expanduser(destination)
    
    # Install the utility
    install_utility(destination)
    
    # Final instructions
    print("")
    print_color(Colors.HEADER, "Installation Complete!")
    print_color(Colors.HEADER, "======================")
    print("")
    print_color(Colors.BOLD, "Next Steps:")
    print("1. Navigate to your project directory")
    print("2. Run: autonomous-claude init")
    print("3. Edit .autonomous-claude/config.sh to configure your project")
    print("4. Run: autonomous-claude start")
    print("")
    print_color(Colors.BOLD, "For more information, see the README:")
    print(f"cat {os.path.join(destination, 'README.md')}")
    print("")
    print_color(Colors.GREEN, "Thank you for installing Autonomous Claude!")

if __name__ == "__main__":
    main()
