#!/bin/bash

# PostgreSQL Backup & Restore Tool - Binary Installation Script
# This script installs the binary to /usr/local/bin and sets up proper permissions

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root for system-wide installation
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

# Find the binary
BINARY_PATH=""
if [ -f "dist/postgres-backup-tool" ]; then
    BINARY_PATH="dist/postgres-backup-tool"
elif [ -f "postgres-backup-tool" ]; then
    BINARY_PATH="postgres-backup-tool"
else
    print_error "Binary not found. Please run build.py first."
    exit 1
fi

# Install binary
print_status "Installing binary to $INSTALL_DIR"
cp "$BINARY_PATH" "$INSTALL_DIR/postgres-backup-tool"
chmod +x "$INSTALL_DIR/postgres-backup-tool"

# Install configuration files
print_status "Installing configuration files to $CONFIG_DIR"
if [ -f "examples/sample-config.conf" ]; then
    cp examples/sample-config.conf "$CONFIG_DIR/"
fi

if [ -f "README.md" ]; then
    cp README.md "$CONFIG_DIR/"
fi

if [ -f "LICENSE" ]; then
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

# Print installation summary
echo ""
print_status "Installation completed successfully!"
echo ""
echo "Binary location: $INSTALL_DIR/postgres-backup-tool"
echo "Configuration directory: $CONFIG_DIR"
echo ""
echo "Usage examples:"
echo "  postgres-backup-tool --help"
echo "  postgres-backup-tool --cli"
echo "  postgres-backup-tool --tui"
echo "  postgres-backup-tool --web"
echo "  postgres-backup-tool --scheduler"
echo ""

if [[ $EUID -ne 0 ]]; then
    echo "To add to PATH (add to ~/.bashrc or ~/.zshrc):"
    echo "  export PATH=\"\$PATH:$INSTALL_DIR\""
    echo ""
    echo "Then reload your shell:"
    echo "  source ~/.bashrc  # or ~/.zshrc"
    echo ""
fi

print_status "Enjoy using PostgreSQL Backup & Restore Tool!"