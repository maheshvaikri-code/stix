#!/bin/bash
#
# ISON Memory MCP Installation Script for macOS/Linux
#
# Installs ISON Memory MCP server and configures it for:
# - Claude Desktop
# - Claude Code CLI
# - Claude Code VSCode Extension
#
# Usage:
#   ./install-unix.sh
#   ./install-unix.sh --memory-path ~/my-memory
#   ./install-unix.sh --no-desktop --no-cli

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Functions
log_step() { echo -e "${CYAN}[*]${NC} $1"; }
log_success() { echo -e "${GREEN}[+]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[-]${NC} $1"; }

# Parse arguments
MEMORY_PATH=""
NO_DESKTOP=false
NO_CLI=false
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --memory-path)
            MEMORY_PATH="$2"
            shift 2
            ;;
        --no-desktop)
            NO_DESKTOP=true
            shift
            ;;
        --no-cli)
            NO_CLI=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo ""
echo -e "${MAGENTA}=====================================${NC}"
echo -e "${MAGENTA}  ISON Memory MCP Server Installer   ${NC}"
echo -e "${MAGENTA}=====================================${NC}"
echo ""

# Detect OS
OS="$(uname -s)"
case "$OS" in
    Darwin)
        OS_NAME="macOS"
        DEFAULT_MEMORY_PATH="$HOME/Library/Application Support/ison-memory"
        CLAUDE_DESKTOP_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
        ;;
    Linux)
        OS_NAME="Linux"
        DEFAULT_MEMORY_PATH="$HOME/.local/share/ison-memory"
        CLAUDE_DESKTOP_CONFIG="$HOME/.config/Claude/claude_desktop_config.json"
        ;;
    *)
        log_error "Unsupported OS: $OS"
        exit 1
        ;;
esac

log_step "Detected: $OS_NAME"

# Check Python
log_step "Checking Python installation..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

    if [[ $PYTHON_MAJOR -lt 3 ]] || [[ $PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -lt 10 ]]; then
        log_error "Python 3.10+ required. Found: Python $PYTHON_VERSION"
        exit 1
    fi
    log_success "Found Python $PYTHON_VERSION"
else
    log_error "Python 3 not found. Please install Python 3.10+"
    echo "  macOS: brew install python3"
    echo "  Ubuntu: sudo apt install python3"
    exit 1
fi

# Set memory path
if [[ -z "$MEMORY_PATH" ]]; then
    MEMORY_PATH="$DEFAULT_MEMORY_PATH"
fi
log_step "Memory path: $MEMORY_PATH"

# Create directories
log_step "Creating directories..."
mkdir -p "$MEMORY_PATH"
mkdir -p "$MEMORY_PATH/backups"
mkdir -p "$MEMORY_PATH/logs"
log_success "Directories created"

# Install package
log_step "Installing ison-memory-mcp..."
python3 -m pip install --upgrade pip

# Install from local path if available
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_PATH="$(dirname "$SCRIPT_DIR")"

if [[ -f "$LOCAL_PATH/pyproject.toml" ]]; then
    log_step "Installing from local source..."
    python3 -m pip install -e "$LOCAL_PATH"
else
    python3 -m pip install ison-memory-mcp --upgrade
fi
log_success "Package installed"

# Verify installation
log_step "Verifying installation..."
VERSION=$(python3 -c "import ison_memory_mcp; print(ison_memory_mcp.__version__)")
log_success "Installed version: $VERSION"

# Initialize configuration
log_step "Initializing configuration..."
ison-memory-mcp init --force

# Configure Claude Desktop
if [[ "$NO_DESKTOP" != true ]]; then
    log_step "Configuring Claude Desktop..."

    CLAUDE_DESKTOP_DIR="$(dirname "$CLAUDE_DESKTOP_CONFIG")"
    mkdir -p "$CLAUDE_DESKTOP_DIR"

    # Create or merge config
    if [[ -f "$CLAUDE_DESKTOP_CONFIG" ]]; then
        # Backup existing
        cp "$CLAUDE_DESKTOP_CONFIG" "${CLAUDE_DESKTOP_CONFIG}.bak"
        log_warning "Backed up existing config"
    fi

    # Use Python to merge JSON properly
    python3 << EOF
import json
import os

config_path = "$CLAUDE_DESKTOP_CONFIG"
memory_path = "$MEMORY_PATH"

new_server = {
    "command": "ison-memory-mcp",
    "args": ["serve"],
    "env": {
        "ISON_MEMORY_STORAGE__PATH": os.path.join(memory_path, "memory.db")
    }
}

if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        config = json.load(f)
else:
    config = {}

if 'mcpServers' not in config:
    config['mcpServers'] = {}

config['mcpServers']['ison-memory'] = new_server

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

print(f"Configuration saved to {config_path}")
EOF

    log_success "Claude Desktop configured"
fi

# Configure Claude Code CLI
if [[ "$NO_CLI" != true ]]; then
    log_step "Configuring Claude Code CLI..."

    CLAUDE_CODE_DIR="$HOME/.claude"
    CLAUDE_CODE_FILE="$CLAUDE_CODE_DIR/settings.json"

    mkdir -p "$CLAUDE_CODE_DIR"

    python3 << EOF
import json
import os

config_path = "$CLAUDE_CODE_FILE"
memory_path = "$MEMORY_PATH"

new_server = {
    "command": "ison-memory-mcp",
    "args": ["serve"],
    "env": {
        "ISON_MEMORY_STORAGE__PATH": os.path.join(memory_path, "memory.db")
    }
}

if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        config = json.load(f)
else:
    config = {}

if 'mcpServers' not in config:
    config['mcpServers'] = {}

config['mcpServers']['ison-memory'] = new_server

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

print(f"Configuration saved to {config_path}")
EOF

    log_success "Claude Code CLI configured"
fi

# Create VSCode workspace template
log_step "Creating VSCode workspace template..."
cat > "$MEMORY_PATH/vscode-mcp-template.json" << EOF
{
  "servers": {
    "ison-memory": {
      "command": "ison-memory-mcp",
      "args": ["serve"],
      "env": {
        "ISON_MEMORY_STORAGE__PATH": "$MEMORY_PATH/memory.db"
      }
    }
  }
}
EOF
log_success "VSCode template created"

# Summary
echo ""
echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}  Installation Complete!             ${NC}"
echo -e "${GREEN}=====================================${NC}"
echo ""
echo -e "${CYAN}Memory storage:${NC} $MEMORY_PATH"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Restart Claude Desktop to load the memory server"
echo "  2. In Claude, try: 'What do you remember about me?'"
echo "  3. Run 'ison-memory-mcp stats' to check memory status"
echo ""
echo -e "${YELLOW}Commands:${NC}"
echo "  ison-memory-mcp serve    # Start server manually"
echo "  ison-memory-mcp stats    # Show statistics"
echo "  ison-memory-mcp compact  # Run memory compaction"
echo "  ison-memory-mcp backup   # Create backup"
echo "  ison-memory-mcp export   # Export to ISON file"
echo ""
