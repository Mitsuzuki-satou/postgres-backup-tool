# PostgreSQL Advanced Backup & Restore Tool

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Bash](https://img.shields.io/badge/bash-4.0%2B-brightgreen.svg)](https://www.gnu.org/software/bash/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-9.0%2B-blue.svg)](https://www.postgresql.org/)

A powerful, user-friendly command-line tool for PostgreSQL database backup and restore operations with beautiful progress bars, parallel processing, and comprehensive error handling.

## ✨ Features

- 🎨 **Beautiful UI** - Colorized output with Unicode symbols and progress bars
- 📊 **Real-time Progress** - File size monitoring, transfer speed, and table counting
- ⚡ **Parallel Processing** - Multi-job backups and restores for faster operations
- 🗜️ **Smart Compression** - Automatic compression with size estimation
- 🔧 **Interactive Configuration** - Save and reuse database connection settings
- 📝 **Comprehensive Logging** - Detailed operation logs with timestamps
- 🔄 **Multiple Formats** - Support for SQL, compressed SQL, and directory formats
- 🛡️ **Error Handling** - Robust error detection with cleanup procedures
- 🔍 **Connection Testing** - Verify database connectivity before operations
- 📋 **Backup Management** - List, select, and manage backup files

## 🚀 One-Line Installation & Execution

Run directly from GitHub without downloading:

```bash
curl -sSL https://raw.githubusercontent.com/YOUR_USERNAME/postgres-backup-tool/main/postgres-backup-restore.sh | bash
```

Or download and run:

```bash
wget -qO- https://raw.githubusercontent.com/YOUR_USERNAME/postgres-backup-tool/main/postgres-backup-restore.sh | bash
```

## 📋 Prerequisites

- **PostgreSQL Client Tools**: `psql`, `pg_dump`, `pg_restore`
- **Bash**: Version 4.0 or higher
- **System Tools**: `tar`, `gzip`, `find`, `grep`

### Installation on Different Systems:

**Ubuntu/Debian:**
```bash
sudo apt update && sudo apt install postgresql-client
```

**CentOS/RHEL/Fedora:**
```bash
sudo yum install postgresql postgresql-contrib  # CentOS/RHEL
sudo dnf install postgresql postgresql-contrib  # Fedora
```

**Arch Linux:**
```bash
sudo pacman -S postgresql
```

**macOS:**
```bash
brew install postgresql
```

## 📖 Usage

### Interactive Mode (Recommended)

Simply run the script to enter the interactive menu:

```bash
./postgres-backup-restore.sh
```

You'll see a beautiful menu with options:

```
================================================================================
                 PostgreSQL Advanced Backup & Restore Tool v2.0                 
================================================================================

🗄 Current Configuration:

  Remote Database     : your-host:5432/your-database
  Local Database      : localhost:5432/restored-database
  Backup Directory    : /home/user/postgres_backups
  Compression         : true

⚙ Available Operations:

  1) Full Backup & Restore     - Complete backup and restore process
  2) Backup Only              - Create backup from remote database
  3) Restore Only             - Restore from existing backup file
  4) Test Connections         - Test remote and local database connections
  5) Configuration            - Modify configuration settings
  6) View Logs                - Display recent operation logs
  7) List Backups             - Show available backup files
  8) Exit                     - Exit the application
```

### Command Line Mode

For automated scripts, you can run in non-interactive mode:

```bash
./postgres-backup-restore.sh --non-interactive
```

### Configuration

The tool saves your configuration in `~/.postgres_backup_config`. First time setup:

1. Choose option **5** (Configuration)
2. Enter your database connection details
3. Settings are automatically saved for future use

## 🛠️ Configuration Options

| Setting | Description | Example |
|---------|-------------|---------|
| Remote Host | Source database server | `db.example.com` |
| Remote Port | Source database port | `5432` |
| Remote Database | Database name to backup | `production_db` |
| Remote User | Database username | `backup_user` |
| Remote Password | Database password | `secure_password` |
| Local Host | Target database server | `localhost` |
| Local Port | Target database port | `5432` |
| Local User | Local database username | `postgres` |
| Local Password | Local database password | `local_password` |
| New Database Name | Name for restored database | `restored_db` |
| Backup Directory | Where to store backups | `~/postgres_backups` |
| Compression | Enable/disable compression | `true` |
| Parallel Jobs | Number of parallel jobs | `4` |

## 📊 Progress Indicators

The tool provides real-time feedback for all operations:

### Backup Progress
```
Creating compressed backup [████████████░░░░░] 75% [150MB @ 3MB/s]
```

### Restore Progress
```
Restoring database (parallel) [██████████████░░░] 85% [45 tables restored]
```

### Time-based Progress
```
Creating parallel backup [████████████████░░] 90% [2m30s elapsed]
```

## 📁 File Structure

```
postgres-backup-tool/
├── postgres-backup-restore.sh    # Main script
├── README.md                     # This file
├── LICENSE                       # MIT License
├── CONTRIBUTING.md              # Contribution guidelines
└── examples/                    # Example configurations
    └── sample-config.conf       # Sample configuration file
```

## 🔧 Advanced Usage

### Backup Types

1. **Parallel + Compressed** (Fastest, smallest)
   - Uses directory format with multiple jobs
   - Compresses to tar.gz format
   - Recommended for large databases

2. **SQL + Compressed** (Good balance)
   - Standard SQL format with gzip compression
   - Single-threaded but reliable
   - Good for medium databases

3. **Plain SQL** (Maximum compatibility)
   - Uncompressed SQL format
   - Compatible with all PostgreSQL tools
   - Best for small databases or debugging

### Environment Variables

You can override configuration using environment variables:

```bash
export PGHOST="remote-server.com"
export PGPORT="5432"
export PGUSER="backup_user"
export PGPASSWORD="your_password"
./postgres-backup-restore.sh
```

### Logging

All operations are logged to `~/.postgres_backup_logs/`:

```bash
# View latest log
tail -f ~/.postgres_backup_logs/backup_restore_$(date +%Y%m%d)*.log
```

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

### Quick Start for Contributors

1. **Fork the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/postgres-backup-tool.git
   cd postgres-backup-tool
   ```

2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**
   - Follow the existing code style
   - Add comments for complex logic
   - Test your changes thoroughly

4. **Test the script**
   ```bash
   ./postgres-backup-restore.sh
   ```

5. **Commit and push**
   ```bash
   git add .
   git commit -m "Add: your feature description"
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request**

### Areas for Contribution

- 🔧 **New Features**: Additional backup formats, cloud storage integration
- 🐛 **Bug Fixes**: Error handling improvements, edge cases
- 📖 **Documentation**: Better examples, video tutorials
- 🧪 **Testing**: Unit tests, integration tests
- 🎨 **UI/UX**: Better progress indicators, more interactive features
- 🌍 **Localization**: Multi-language support

## 📋 Troubleshooting

### Common Issues

**Connection Failed**
```bash
# Check if PostgreSQL client is installed
psql --version

# Test manual connection
psql -h hostname -p port -U username -d database
```

**Permission Denied**
```bash
# Make script executable
chmod +x postgres-backup-restore.sh

# Check file permissions
ls -la postgres-backup-restore.sh
```

**Backup Failed**
- Verify source database exists and is accessible
- Check disk space in backup directory
- Ensure user has necessary privileges

**Restore Failed**
- Verify target database doesn't exist (or use drop option)
- Check PostgreSQL server is running locally
- Ensure backup file is not corrupted

### Debug Mode

Enable verbose output for debugging:

```bash
bash -x postgres-backup-restore.sh
```

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- PostgreSQL community for excellent documentation
- Contributors who help improve this tool
- Users who provide feedback and bug reports

## 📞 Support

- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/YOUR_USERNAME/postgres-backup-tool/issues)
- 💡 **Feature Requests**: [GitHub Discussions](https://github.com/YOUR_USERNAME/postgres-backup-tool/discussions)
- 📖 **Documentation**: [Wiki](https://github.com/YOUR_USERNAME/postgres-backup-tool/wiki)

---

⭐ **If this tool helped you, please star the repository!** ⭐
