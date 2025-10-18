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
