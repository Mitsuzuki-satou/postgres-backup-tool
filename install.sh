#!/bin/bash
# PostgreSQL Backup & Restore Tool Installation Script

set -e

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

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root for security reasons"
   exit 1
fi

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    if command -v apt-get >/dev/null 2>&1; then
        DISTRO="debian"
    elif command -v yum >/dev/null 2>&1; then
        DISTRO="redhat"
    elif command -v dnf >/dev/null 2>&1; then
        DISTRO="fedora"
    else
        print_error "Unsupported Linux distribution"
        exit 1
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    DISTRO="macos"
else
    print_error "Unsupported operating system: $OSTYPE"
    exit 1
fi

print_status "Detected OS: $OS ($DISTRO)"

# Install system dependencies
print_status "Installing system dependencies..."

if [[ "$DISTRO" == "debian" ]]; then
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip python3-venv postgresql-client build-essential libpq-dev
elif [[ "$DISTRO" == "redhat" ]]; then
    sudo yum install -y python3 python3-pip postgresql gcc libpq-devel
elif [[ "$DISTRO" == "fedora" ]]; then
    sudo dnf install -y python3 python3-pip postgresql gcc libpq-devel
elif [[ "$DISTRO" == "macos" ]]; then
    if ! command -v brew >/dev/null 2>&1; then
        print_error "Homebrew not found. Please install Homebrew first: https://brew.sh/"
        exit 1
    fi
    brew install python3 postgresql
fi

# Check if PostgreSQL client tools are available
if ! command -v pg_dump >/dev/null 2>&1; then
    print_error "PostgreSQL client tools not found. Please install postgresql-client"
    exit 1
fi

print_success "System dependencies installed"

# Create installation directory
INSTALL_DIR="$HOME/.postgres-backup-tool"
print_status "Installing to $INSTALL_DIR"

mkdir -p "$INSTALL_DIR"
cd "$(dirname "$0")"

# Copy files to installation directory
cp -r src main.py requirements.txt setup.py README.md "$INSTALL_DIR/"
cd "$INSTALL_DIR"

# Create virtual environment
print_status "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python dependencies
print_status "Installing Python dependencies..."
pip install -r requirements.txt

# Install the package in development mode
pip install -e .

# Create configuration directory
CONFIG_DIR="$HOME/.postgres_backup_tool"
mkdir -p "$CONFIG_DIR"

# Create default configuration if it doesn't exist
if [[ ! -f "$CONFIG_DIR/config.json" ]]; then
    print_status "Creating default configuration..."
    cat > "$CONFIG_DIR/config.json" << EOF
{
    "app": {
        "version": "3.0.0",
        "log_level": "INFO",
        "backup_dir": "$HOME/postgres_backups"
    },
    "database": {
        "default_remote": {
            "host": "localhost",
            "port": 5432,
            "database": "postgres",
            "username": "postgres",
            "password": "",
            "ssl_mode": "prefer"
        },
        "default_local": {
            "host": "localhost",
            "port": 5432,
            "database": "postgres",
            "username": "postgres",
            "password": "",
            "ssl_mode": "prefer"
        }
    },
    "backup": {
        "default_type": "full",
        "compression": "gzip",
        "parallel_jobs": 4,
        "retention_days": 30
    }
}
EOF
fi

# Create wrapper script
WRAPPER_SCRIPT="/usr/local/bin/postgres-backup-tool"
print_status "Creating wrapper script..."

sudo tee "$WRAPPER_SCRIPT" > /dev/null << EOF
#!/bin/bash
# PostgreSQL Backup & Restore Tool wrapper script

INSTALL_DIR="$INSTALL_DIR"
source "\$INSTALL_DIR/venv/bin/activate"
cd "\$INSTALL_DIR"
python main.py "\$@"
EOF

sudo chmod +x "$WRAPPER_SCRIPT"

# Create desktop entry for GUI (Linux)
if [[ "$OS" == "linux" ]]; then
    DESKTOP_ENTRY="$HOME/.local/share/applications/postgres-backup-tool.desktop"
    print_status "Creating desktop entry..."
    
    mkdir -p "$(dirname "$DESKTOP_ENTRY")"
    cat > "$DESKTOP_ENTRY" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=PostgreSQL Backup Tool
Comment=PostgreSQL database backup and restore utility
Exec=$WRAPPER_SCRIPT --gui
Icon=database
Terminal=false
Categories=Development;Database;System;
EOF
fi

# Create systemd service for scheduler (Linux)
if [[ "$OS" == "linux" ]]; then
    SERVICE_FILE="$HOME/.config/systemd/user/postgres-backup-scheduler.service"
    print_status "Creating systemd service..."
    
    mkdir -p "$(dirname "$SERVICE_FILE")"
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=PostgreSQL Backup Scheduler
After=network.target

[Service]
Type=simple
ExecStart=$WRAPPER_SCRIPT --scheduler
Restart=always
RestartSec=10
Environment=PATH=$INSTALL_DIR/venv/bin

[Install]
WantedBy=default.target
EOF
    
    # Reload systemd and enable service
    systemctl --user daemon-reload
    print_status "To enable the scheduler service, run: systemctl --user enable postgres-backup-scheduler"
fi

# Create backup directory
BACKUP_DIR="$HOME/postgres_backups"
mkdir -p "$BACKUP_DIR"
print_status "Created backup directory: $BACKUP_DIR"

print_success "Installation completed successfully!"
echo
print_status "Usage examples:"
echo "  postgres-backup-tool                    # CLI mode"
echo "  postgres-backup-tool --tui              # Terminal UI"
echo "  postgres-backup-tool --gui              # Graphical UI"
echo "  postgres-backup-tool --web              # Web interface"
echo "  postgres-backup-tool --scheduler        # Start scheduler daemon"
echo
print_status "Configuration file: $CONFIG_DIR/config.json"
print_status "Log directory: $CONFIG_DIR/logs"
print_status "Backup directory: $BACKUP_DIR"
echo
print_warning "Remember to:"
echo "  1. Update your database configuration in $CONFIG_DIR/config.json"
echo "  2. Test your database connections before running backups"
echo "  3. Enable the scheduler service if you want automated backups: systemctl --user enable postgres-backup-scheduler"
echo
print_success "Thank you for installing PostgreSQL Backup & Restore Tool!"