<#
.SYNOPSIS
    ISON Memory MCP Installation Script for Windows

.DESCRIPTION
    Installs ISON Memory MCP server and configures it for:
    - Claude Desktop
    - Claude Code CLI
    - Claude Code VSCode Extension

.PARAMETER MemoryPath
    Custom path for memory storage (default: %LOCALAPPDATA%\ison-memory)

.PARAMETER NoDesktop
    Skip Claude Desktop configuration

.PARAMETER NoCLI
    Skip Claude Code CLI configuration

.EXAMPLE
    .\install-windows.ps1
    .\install-windows.ps1 -MemoryPath "D:\MyMemory"
#>

param(
    [string]$MemoryPath = "",
    [switch]$NoDesktop,
    [switch]$NoCLI,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

# Colors
function Write-Step { param($msg) Write-Host "[*] $msg" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "[+] $msg" -ForegroundColor Green }
function Write-Warning { param($msg) Write-Host "[!] $msg" -ForegroundColor Yellow }
function Write-Error { param($msg) Write-Host "[-] $msg" -ForegroundColor Red }

Write-Host ""
Write-Host "=====================================" -ForegroundColor Magenta
Write-Host "  ISON Memory MCP Server Installer   " -ForegroundColor Magenta
Write-Host "=====================================" -ForegroundColor Magenta
Write-Host ""

# Check Python
Write-Step "Checking Python installation..."
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python 3\.(\d+)") {
        $minorVersion = [int]$Matches[1]
        if ($minorVersion -lt 10) {
            Write-Error "Python 3.10+ required. Found: $pythonVersion"
            exit 1
        }
        Write-Success "Found $pythonVersion"
    }
} catch {
    Write-Error "Python not found. Please install Python 3.10+"
    Write-Host "Download from: https://www.python.org/downloads/"
    exit 1
}

# Set memory path
if (-not $MemoryPath) {
    $MemoryPath = Join-Path $env:LOCALAPPDATA "ison-memory"
}
Write-Step "Memory path: $MemoryPath"

# Create directories
Write-Step "Creating directories..."
$dirs = @(
    $MemoryPath,
    (Join-Path $MemoryPath "backups"),
    (Join-Path $MemoryPath "logs")
)
foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Success "Created: $dir"
    }
}

# Install package
Write-Step "Installing ison-memory-mcp..."
try {
    pip install --upgrade pip

    # Install from local path if available, otherwise from PyPI
    $localPath = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
    if (Test-Path (Join-Path $localPath "pyproject.toml")) {
        Write-Host "Installing from local source..."
        pip install -e $localPath
    } else {
        pip install ison-memory-mcp --upgrade
    }
    Write-Success "Package installed"
} catch {
    Write-Error "Failed to install package: $_"
    exit 1
}

# Verify installation
Write-Step "Verifying installation..."
try {
    $version = python -c "import ison_memory_mcp; print(ison_memory_mcp.__version__)"
    Write-Success "Installed version: $version"
} catch {
    Write-Error "Installation verification failed"
    exit 1
}

# Initialize configuration
Write-Step "Initializing configuration..."
ison-memory-mcp init --force

# Configure Claude Desktop
if (-not $NoDesktop) {
    Write-Step "Configuring Claude Desktop..."

    $claudeConfigDir = Join-Path $env:APPDATA "Claude"
    $claudeConfigFile = Join-Path $claudeConfigDir "claude_desktop_config.json"

    if (-not (Test-Path $claudeConfigDir)) {
        New-Item -ItemType Directory -Path $claudeConfigDir -Force | Out-Null
    }

    $mcpConfig = @{
        mcpServers = @{
            "ison-memory" = @{
                command = "ison-memory-mcp"
                args = @("serve")
                env = @{
                    ISON_MEMORY_STORAGE__PATH = (Join-Path $MemoryPath "memory.db").Replace("\", "/")
                }
            }
        }
    }

    if (Test-Path $claudeConfigFile) {
        try {
            $existingConfig = Get-Content $claudeConfigFile -Raw | ConvertFrom-Json -AsHashtable
            if (-not $existingConfig.mcpServers) {
                $existingConfig.mcpServers = @{}
            }
            $existingConfig.mcpServers["ison-memory"] = $mcpConfig.mcpServers["ison-memory"]
            $existingConfig | ConvertTo-Json -Depth 10 | Set-Content $claudeConfigFile -Encoding UTF8
        } catch {
            Write-Warning "Could not merge with existing config, creating new"
            $mcpConfig | ConvertTo-Json -Depth 10 | Set-Content $claudeConfigFile -Encoding UTF8
        }
    } else {
        $mcpConfig | ConvertTo-Json -Depth 10 | Set-Content $claudeConfigFile -Encoding UTF8
    }

    Write-Success "Claude Desktop configured: $claudeConfigFile"
}

# Configure Claude Code CLI
if (-not $NoCLI) {
    Write-Step "Configuring Claude Code CLI..."

    $claudeCodeDir = Join-Path $env:USERPROFILE ".claude"
    $claudeCodeFile = Join-Path $claudeCodeDir "settings.json"

    if (-not (Test-Path $claudeCodeDir)) {
        New-Item -ItemType Directory -Path $claudeCodeDir -Force | Out-Null
    }

    $cliConfig = @{
        mcpServers = @{
            "ison-memory" = @{
                command = "ison-memory-mcp"
                args = @("serve")
                env = @{
                    ISON_MEMORY_STORAGE__PATH = (Join-Path $MemoryPath "memory.db").Replace("\", "/")
                }
            }
        }
    }

    if (Test-Path $claudeCodeFile) {
        try {
            $existingConfig = Get-Content $claudeCodeFile -Raw | ConvertFrom-Json -AsHashtable
            if (-not $existingConfig.mcpServers) {
                $existingConfig.mcpServers = @{}
            }
            $existingConfig.mcpServers["ison-memory"] = $cliConfig.mcpServers["ison-memory"]
            $existingConfig | ConvertTo-Json -Depth 10 | Set-Content $claudeCodeFile -Encoding UTF8
        } catch {
            Write-Warning "Could not merge with existing config, creating new"
            $cliConfig | ConvertTo-Json -Depth 10 | Set-Content $claudeCodeFile -Encoding UTF8
        }
    } else {
        $cliConfig | ConvertTo-Json -Depth 10 | Set-Content $claudeCodeFile -Encoding UTF8
    }

    Write-Success "Claude Code CLI configured: $claudeCodeFile"
}

# Create VSCode workspace config template
Write-Step "Creating VSCode workspace template..."
$vscodeTemplate = @"
{
  "servers": {
    "ison-memory": {
      "command": "ison-memory-mcp",
      "args": ["serve"],
      "env": {
        "ISON_MEMORY_STORAGE__PATH": "${MemoryPath.Replace('\', '/')}/memory.db"
      }
    }
  }
}
"@

$vscodeTemplatePath = Join-Path $MemoryPath "vscode-mcp-template.json"
$vscodeTemplate | Set-Content $vscodeTemplatePath -Encoding UTF8
Write-Success "VSCode template: $vscodeTemplatePath"

# Summary
Write-Host ""
Write-Host "=====================================" -ForegroundColor Green
Write-Host "  Installation Complete!             " -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""
Write-Host "Memory storage: $MemoryPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Restart Claude Desktop to load the memory server"
Write-Host "  2. In Claude, try: 'What do you remember about me?'"
Write-Host "  3. Run 'ison-memory-mcp stats' to check memory status"
Write-Host ""
Write-Host "Commands:" -ForegroundColor Yellow
Write-Host "  ison-memory-mcp serve    # Start server manually"
Write-Host "  ison-memory-mcp stats    # Show statistics"
Write-Host "  ison-memory-mcp compact  # Run memory compaction"
Write-Host "  ison-memory-mcp backup   # Create backup"
Write-Host "  ison-memory-mcp export   # Export to ISON file"
Write-Host ""
