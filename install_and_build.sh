#!/bin/bash
# Install and Build Script for PostgreSQL Backup & Restore Tool
# This script works with both bash and fish shells

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Detect shell
detect_shell() {
    if [[ "$SHELL" == *"fish"* ]]; then
        echo "fish"
    else
        echo "bash"
    fi
}

# Check if we're in the right directory
check_project_root() {
    if [[ ! -f "main.py" ]]; then
        print_error "main.py not found. Please run this script from the project root."
        exit 1
    fi
}

# Clean previous build artifacts
clean_build() {
    print_status "Cleaning previous build artifacts..."
    
    dirs_to_clean=("build" "dist" "__pycache__" "release")
    for dir in "${dirs_to_clean[@]}"; do
        if [[ -d "$dir" ]]; then
            print_status "Removing $dir directory..."
            rm -rf "$dir"
        fi
    done
    
    # Clean Python cache files
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    
    print_success "Build artifacts cleaned"
}

# Set up virtual environment
setup_venv() {
    print_status "Setting up Python virtual environment..."
    
    # Remove existing venv if present
    if [[ -d "venv" ]]; then
        print_status "Removing existing virtual environment..."
        rm -rf venv
    fi
    
    # Create new virtual environment
    python3 -m venv venv
    print_success "Virtual environment created"
    
    # Activate virtual environment and install dependencies
    print_status "Installing dependencies..."
    
    # Use bash for activation to avoid fish compatibility issues
    bash -c "source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt"
    
    print_success "Dependencies installed"
}

# Run tests (optional)
run_tests() {
    print_status "Running tests..."
    
    bash -c "source venv/bin/activate && python -m pytest tests/ -v" || {
        print_warning "Some tests may have been skipped or failed"
    }
}

# Build binary
build_binary() {
    print_status "Building binary with PyInstaller..."
    
    # Install PyInstaller
    bash -c "source venv/bin/activate && pip install pyinstaller"
    
    # Build the binary
    bash -c "source venv/bin/activate && python -m PyInstaller \
        --clean \
        --onefile \
        --name=postgres-backup-tool \
        --add-data=templates:templates \
        --add-data=static:static \
        --add-data=examples:examples \
        --hidden-import=asyncpg \
        --hidden-import=psycopg2 \
        --hidden-import=textual \
        --hidden-import=rich \
        --hidden-import=fastapi \
        --hidden-import=uvicorn \
        --hidden-import=jinja2 \
        --hidden-import=cryptography \
        --hidden-import=schedule \
        --hidden-import=click \
        --hidden-import=pydantic \
        --hidden-import=aiofiles \
        --hidden-import=websockets \
        --hidden-import=starlette \
        --hidden-import=multipart \
        --exclude-module=tkinter \
        --exclude-module=matplotlib \
        --exclude-module=numpy \
        --exclude-module=pandas \
        --exclude-module=scipy \
        --exclude-module=PIL \
        main.py"
    
    print_success "Binary built successfully"
}

# Test binary
test_binary() {
    print_status "Testing binary..."
    
    if [[ ! -f "dist/postgres-backup-tool" ]]; then
        print_error "Binary not found in dist/ directory"
        return 1
    fi
    
    # Test help command
    if ./dist/postgres-backup-tool --help > /dev/null 2>&1; then
        print_success "Binary test passed"
        return 0
    else
        print_error "Binary test failed"
        return 1
    fi
}

# Create release package
create_release() {
    print_status "Creating release package..."
    
    # Create release directory
    mkdir -p release
    
    # Copy binary
    cp dist/postgres-backup-tool release/
    
    # Copy documentation and config files
    files_to_copy=("README.md" "LICENSE" "examples/sample-config.conf")
    for file in "${files_to_copy[@]}"; do
        if [[ -f "$file" ]]; then
            cp "$file" release/
        fi
    done
    
    # Create usage instructions
    cat > release/BINARY_USAGE.md << 'EOF'
# PostgreSQL Backup & Restore Tool - Binary Version

## Quick Start

### Linux/macOS
```bash
./postgres-backup-tool --help
./postgres-backup-tool --cli      # Command-line interface
./postgres-backup-tool --tui      # Terminal user interface  
./postgres-backup-tool --web      # Web interface at http://127.0.0.1:8080
./postgres-backup-tool --scheduler # Background scheduler daemon
```

### Windows
```cmd
postgres-backup-tool.exe --help
postgres-backup-tool.exe --cli      # Command-line interface
postgres-backup-tool.exe --tui      # Terminal user interface  
postgres-backup-tool.exe --web      # Web interface at http://127.0.0.1:8080
postgres-backup-tool.exe --scheduler # Background scheduler daemon
```

## Prerequisites

You need PostgreSQL client tools installed:
- Ubuntu/Debian: `sudo apt install postgresql-client`
- CentOS/RHEL: `sudo yum install postgresql` or `sudo dnf install postgresql`
- macOS: `brew install postgresql`
- Windows: Download from PostgreSQL website

## Configuration

The binary will look for configuration in:
1. Environment variables
2. `~/.postgres_backup_config` file
3. Command-line arguments

See README.md for detailed configuration options.

## Features

- **CLI Mode**: Command-line interface for scripting
- **TUI Mode**: Rich terminal interface with dashboard
- **Web Mode**: Modern web interface with dark mode
- **Scheduler Mode**: Background daemon for automated backups

## Support

For issues and documentation, visit the project repository.
EOF
    
    # Create archive
    system=$(uname -s | tr '[:upper:]' '[:lower:]')
    archive_name="postgres-backup-tool-v3.0-${system}.tar.gz"
    
    tar -czf "$archive_name" -C release .
    
    print_success "Release package created: $archive_name"
    echo "$archive_name"
}

# Install binary to PATH
install_binary() {
    print_status "Installing binary to PATH..."
    
    # Determine installation directory
    if [[ $EUID -eq 0 ]]; then
        INSTALL_DIR="/usr/local/bin"
        CONFIG_DIR="/etc/postgres-backup-tool"
        print_status "Running as root - installing to system directory"
    else
        INSTALL_DIR="$HOME/.local/bin"
        CONFIG_DIR="$HOME/.config/postgres-backup-tool"
        print_status "Running as user - installing to home directory"
        print_warning "Make sure $INSTALL_DIR is in your PATH"
    fi
    
    # Create directories
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$CONFIG_DIR"
    
    # Install binary
    print_status "Installing binary to $INSTALL_DIR"
    cp dist/postgres-backup-tool "$INSTALL_DIR/postgres-backup-tool"
    chmod +x "$INSTALL_DIR/postgres-backup-tool"
    
    # Install configuration files
    print_status "Installing configuration files to $CONFIG_DIR"
    if [[ -f "examples/sample-config.conf" ]]; then
        cp examples/sample-config.conf "$CONFIG_DIR/"
    fi
    
    if [[ -f "README.md" ]]; then
        cp README.md "$CONFIG_DIR/"
    fi
    
    if [[ -f "LICENSE" ]]; then
        cp LICENSE "$CONFIG_DIR/"
    fi
    
    # Create desktop entry for GUI (if not root)
    if [[ $EUID -ne 0 ]]; then
        DESKTOP_DIR="$HOME/.local/share/applications"
        mkdir -p "$DESKTOP_DIR"
        
        cat > "$DESKTOP_DIR/postgres-backup-tool.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=PostgreSQL Backup Tool
Comment=PostgreSQL Backup & Restore Tool
Exec=$INSTALL_DIR/postgres-backup-tool --web
Icon=applications-system
Terminal=false
Categories=System;Database;
StartupNotify=true
EOF
        print_status "Created desktop entry"
    fi
    
    # Create systemd service (if root)
    if [[ $EUID -eq 0 ]]; then
        cat > /etc/systemd/system/postgres-backup-tool.service << EOF
[Unit]
Description=PostgreSQL Backup & Restore Tool
After=network.target

[Service]
Type=simple
User=root
ExecStart=$INSTALL_DIR/postgres-backup-tool --scheduler
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
        
        print_status "Created systemd service"
        print_status "To enable the service: systemctl enable postgres-backup-tool"
        print_status "To start the service: systemctl start postgres-backup-tool"
    fi
    
    print_success "Binary installed successfully!"
    echo "Installation directory: $INSTALL_DIR"
    echo "Configuration directory: $CONFIG_DIR"
}

# Print success message
print_success_message() {
    local archive_name="$1"
    
    echo ""
    echo "============================================================"
    echo "🎉 PostgreSQL Backup & Restore Tool build completed!"
    echo "============================================================"
    echo "✅ Binary location: dist/postgres-backup-tool"
    echo "✅ Release package: $archive_name"
    echo "✅ Release directory: release/"
    echo ""
    
    # Install binary to PATH
    install_binary
    
    echo ""
    echo "📋 Usage Examples:"
    echo "  postgres-backup-tool --help"
    echo "  postgres-backup-tool --cli"
    echo "  postgres-backup-tool --tui"
    echo "  postgres-backup-tool --web"
    echo "  postgres-backup-tool --scheduler"
    echo ""
    echo "🔧 To activate virtual environment manually:"
    shell=$(detect_shell)
    if [[ "$shell" == "fish" ]]; then
        echo "  source venv/bin/activate.fish"
    else
        echo "  source venv/bin/activate"
    fi
    echo ""
    echo "📦 To install as package (optional):"
    echo "  pip install -e ."
    echo ""
    
    if [[ $EUID -ne 0 ]]; then
        echo "🔧 To add to PATH (add to ~/.bashrc, ~/.zshrc, or ~/.config/fish/config.fish):"
        echo "  bash/zsh: export PATH=\"\$PATH:$HOME/.local/bin\""
        echo "  fish: set -gx PATH \$PATH $HOME/.local/bin"
        echo ""
        echo "Then reload your shell:"
        echo "  bash/zsh: source ~/.bashrc  # or ~/.zshrc"
        echo "  fish: source ~/.config/fish/config.fish"
        echo ""
    fi
    
    print_success "Enjoy using PostgreSQL Backup & Restore Tool!"
}

# Main function
main() {
    echo "🚀 PostgreSQL Backup & Restore Tool - Install & Build Script"
    echo "============================================================"
    
    # Check project root
    check_project_root
    
    # Execute build steps
    clean_build
    setup_venv
    run_tests
    build_binary
    
    if test_binary; then
        archive_name=$(create_release)
        print_success_message "$archive_name"
    else
        print_error "Build failed! Binary test did not pass."
        exit 1
    fi
}

# Handle script interruption
trap 'print_error "Build interrupted by user."; exit 1' INT

# Run main function
main "$@"