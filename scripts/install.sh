#!/bin/bash
# =============================================================================
# STIX CLI Installer
# =============================================================================
# Installs STIX CLI tools and optionally sets up local development environment
# Usage: curl -fsSL https://stix.example.com/install.sh | bash
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
STIX_VERSION="${STIX_VERSION:-latest}"
STIX_HOME="${STIX_HOME:-$HOME/.stix}"
STIX_BIN="${STIX_BIN:-$HOME/.local/bin}"

# =============================================================================
# HELPERS
# =============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# =============================================================================
# BANNER
# =============================================================================

print_banner() {
    echo ""
    echo -e "${BLUE}"
    echo "  ███████╗████████╗██╗██╗  ██╗"
    echo "  ██╔════╝╚══██╔══╝██║╚██╗██╔╝"
    echo "  ███████╗   ██║   ██║ ╚███╔╝ "
    echo "  ╚════██║   ██║   ██║ ██╔██╗ "
    echo "  ███████║   ██║   ██║██╔╝ ██╗"
    echo "  ╚══════╝   ╚═╝   ╚═╝╚═╝  ╚═╝"
    echo -e "${NC}"
    echo "  Shield, Trust & Integrity eXecution"
    echo "  Enterprise Policy Enforcement for AI Agents"
    echo ""
}

# =============================================================================
# PREREQUISITES
# =============================================================================

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Node.js
    if ! command_exists node; then
        log_error "Node.js is required. Please install Node.js 18+ first."
    fi

    NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
    if [ "$NODE_VERSION" -lt 18 ]; then
        log_error "Node.js 18+ is required. Current version: $(node -v)"
    fi
    log_success "Node.js $(node -v) found"

    # Check npm or pnpm
    if command_exists pnpm; then
        PACKAGE_MANAGER="pnpm"
    elif command_exists npm; then
        PACKAGE_MANAGER="npm"
    else
        log_error "npm or pnpm is required"
    fi
    log_success "Package manager: $PACKAGE_MANAGER"

    # Check git (optional)
    if command_exists git; then
        log_success "Git found"
    else
        log_warn "Git not found. Some features may be limited."
    fi

    # Check Docker (optional)
    if command_exists docker; then
        log_success "Docker found"
        DOCKER_AVAILABLE=true
    else
        log_warn "Docker not found. Local development mode requires Docker."
        DOCKER_AVAILABLE=false
    fi
}

# =============================================================================
# INSTALLATION
# =============================================================================

create_directories() {
    log_info "Creating STIX directories..."

    mkdir -p "$STIX_HOME"
    mkdir -p "$STIX_HOME/policies"
    mkdir -p "$STIX_HOME/keys"
    mkdir -p "$STIX_HOME/evidence"
    mkdir -p "$STIX_BIN"

    log_success "Directories created at $STIX_HOME"
}

install_cli_tools() {
    log_info "Installing STIX CLI tools..."

    # Install from npm
    if [ "$PACKAGE_MANAGER" = "pnpm" ]; then
        pnpm install -g @stix/simulate @stix/replay @stix/verify
    else
        npm install -g @stix/simulate @stix/replay @stix/verify
    fi

    log_success "CLI tools installed"
}

install_from_source() {
    log_info "Installing STIX from source..."

    # Clone repository
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR"

    git clone --depth 1 https://github.com/stix/stix.git
    cd stix

    # Install dependencies
    if [ "$PACKAGE_MANAGER" = "pnpm" ]; then
        pnpm install
        pnpm build
        pnpm link --global
    else
        npm install
        npm run build
        npm link
    fi

    # Copy default policies
    cp -r policies/default "$STIX_HOME/policies/"
    cp -r policies/examples "$STIX_HOME/policies/"

    # Cleanup
    cd /
    rm -rf "$TEMP_DIR"

    log_success "STIX installed from source"
}

generate_keys() {
    log_info "Generating signing keys..."

    # Generate Ed25519 key pair
    if command_exists openssl; then
        openssl genpkey -algorithm ED25519 -out "$STIX_HOME/keys/stix-signing.pem"
        openssl pkey -in "$STIX_HOME/keys/stix-signing.pem" -pubout -out "$STIX_HOME/keys/stix-signing.pub"
        chmod 600 "$STIX_HOME/keys/stix-signing.pem"
        log_success "Signing keys generated"
    else
        log_warn "OpenSSL not found. Keys will be generated at runtime."
    fi
}

configure_environment() {
    log_info "Configuring environment..."

    # Create config file
    cat > "$STIX_HOME/config.yaml" << EOF
# STIX Configuration
version: 1.0

# Enforcer settings
enforcer:
  port: 3000
  host: localhost

# Policy settings
policy:
  directory: $STIX_HOME/policies
  auto_reload: true

# Security settings
security:
  signing_key: $STIX_HOME/keys/stix-signing.pem
  public_key: $STIX_HOME/keys/stix-signing.pub

# Evidence settings
evidence:
  directory: $STIX_HOME/evidence
  chain_enabled: true

# Logging
logging:
  level: info
  format: json
EOF

    log_success "Configuration created at $STIX_HOME/config.yaml"
}

update_shell_profile() {
    log_info "Updating shell profile..."

    # Detect shell
    SHELL_NAME=$(basename "$SHELL")
    case "$SHELL_NAME" in
        bash)
            PROFILE="$HOME/.bashrc"
            ;;
        zsh)
            PROFILE="$HOME/.zshrc"
            ;;
        fish)
            PROFILE="$HOME/.config/fish/config.fish"
            ;;
        *)
            PROFILE="$HOME/.profile"
            ;;
    esac

    # Add to PATH if not already there
    if ! grep -q "STIX_HOME" "$PROFILE" 2>/dev/null; then
        cat >> "$PROFILE" << EOF

# STIX Configuration
export STIX_HOME="$STIX_HOME"
export PATH="\$STIX_BIN:\$PATH"
EOF
        log_success "Added STIX to $PROFILE"
    else
        log_info "STIX already in $PROFILE"
    fi
}

# =============================================================================
# DOCKER SETUP
# =============================================================================

setup_docker_dev() {
    if [ "$DOCKER_AVAILABLE" = true ]; then
        log_info "Setting up Docker development environment..."

        # Create docker-compose override for local dev
        cat > "$STIX_HOME/docker-compose.override.yaml" << EOF
version: "3.9"
services:
  enforcer:
    volumes:
      - $STIX_HOME/policies:/policies:ro
      - $STIX_HOME/keys:/keys:ro
    environment:
      - STIX_SIGNING_KEY=/keys/stix-signing.pem
EOF

        log_success "Docker development environment configured"
    fi
}

# =============================================================================
# VERIFICATION
# =============================================================================

verify_installation() {
    log_info "Verifying installation..."

    # Check CLI tools
    if command_exists stix-simulate; then
        log_success "stix-simulate: $(stix-simulate --version 2>/dev/null || echo 'installed')"
    fi

    if command_exists stix-replay; then
        log_success "stix-replay: $(stix-replay --version 2>/dev/null || echo 'installed')"
    fi

    if command_exists stix-verify; then
        log_success "stix-verify: $(stix-verify --version 2>/dev/null || echo 'installed')"
    fi

    # Check configuration
    if [ -f "$STIX_HOME/config.yaml" ]; then
        log_success "Configuration: $STIX_HOME/config.yaml"
    fi

    # Check policies
    POLICY_COUNT=$(find "$STIX_HOME/policies" -name "*.yaml" 2>/dev/null | wc -l)
    log_success "Policy files: $POLICY_COUNT"
}

# =============================================================================
# POST-INSTALL
# =============================================================================

print_next_steps() {
    echo ""
    echo -e "${GREEN}Installation complete!${NC}"
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Reload your shell or run:"
    echo "   source ~/.bashrc  # or ~/.zshrc"
    echo ""
    echo "2. Start the development environment:"
    echo "   cd $STIX_HOME && docker compose up -d"
    echo ""
    echo "3. Test with a policy simulation:"
    echo "   stix-simulate --policies $STIX_HOME/policies/default"
    echo ""
    echo "4. Read the documentation:"
    echo "   https://stix.example.com/docs"
    echo ""
    echo "For help: stix-simulate --help"
    echo ""
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    print_banner

    # Parse arguments
    INSTALL_MODE="cli"
    while [[ $# -gt 0 ]]; do
        case $1 in
            --full)
                INSTALL_MODE="full"
                shift
                ;;
            --source)
                INSTALL_MODE="source"
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --full     Install CLI tools and set up Docker environment"
                echo "  --source   Install from source code"
                echo "  --help     Show this help"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                ;;
        esac
    done

    log_info "Installation mode: $INSTALL_MODE"

    check_prerequisites
    create_directories

    if [ "$INSTALL_MODE" = "source" ]; then
        install_from_source
    else
        install_cli_tools
    fi

    generate_keys
    configure_environment
    update_shell_profile

    if [ "$INSTALL_MODE" = "full" ]; then
        setup_docker_dev
    fi

    verify_installation
    print_next_steps
}

main "$@"
