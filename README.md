# PostgreSQL Advanced Backup & Restore Tool

A comprehensive tool for backing up and restoring PostgreSQL databases with visual feedback, progress tracking, and multiple format support.

## 🚀 Quick Start

### Shell Script (Bash)
```bash
curl -sSL https://raw.githubusercontent.com/Mitsuzuki-satou/postgres-backup-tool/main/postgres-backup-restore.sh | bash
```

### Python Version (Recommended)
```bash
# Download and run
curl -sSL https://raw.githubusercontent.com/Mitsuzuki-satou/postgres-backup-tool/main/postgres_backup_restore.py -o postgres_backup_restore.py
python3 postgres_backup_restore.py

# Or with environment variables
export POSTGRES_REMOTE_HOST=your-server.com
export POSTGRES_REMOTE_USER=your-user
export POSTGRES_REMOTE_PASSWORD=your-password
python3 postgres_backup_restore.py
```

## 📋 Features

- **🔄 Multiple Backup Formats**: SQL, compressed SQL, and directory format with parallel processing
- **📊 Real-time Progress**: Visual progress bars with file size and table count monitoring
- **🎨 Colored Interface**: Rich terminal output with colors and symbols
- **⚙️ Flexible Configuration**: Interactive setup, environment variables, and config files
- **🔍 Connection Testing**: Verify remote and local database connections before operations
- **📝 Comprehensive Logging**: Detailed operation logs with timestamps
- **🔒 Error Handling**: Robust error handling with cleanup on failure
- **🗂️ Backup Management**: List, verify, and manage backup files

## 🛠️ Installation

### Prerequisites
- PostgreSQL client tools (`psql`, `pg_dump`, `pg_restore`)
- Python 3.6+ (for Python version)
- Bash shell (for shell script version)

### Install PostgreSQL Client Tools

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql-client
```

**CentOS/RHEL:**
```bash
sudo yum install postgresql
# or
sudo dnf install postgresql
```

**macOS:**
```bash
brew install postgresql
```

## 📖 Usage

### Python Version (Recommended)

#### Interactive Mode
```bash
python3 postgres_backup_restore.py
```

#### Environment Variables
```bash
# Set configuration via environment variables
export POSTGRES_REMOTE_HOST=your-server.com
export POSTGRES_REMOTE_PORT=54321
export POSTGRES_REMOTE_DB=your_database
export POSTGRES_REMOTE_USER=your_user
export POSTGRES_REMOTE_PASSWORD=your_password
export POSTGRES_LOCAL_HOST=localhost
export POSTGRES_LOCAL_PORT=5432
export POSTGRES_LOCAL_USER=postgres
export POSTGRES_LOCAL_PASSWORD=postgres
export POSTGRES_NEW_DB_NAME=restored_db
export POSTGRES_BACKUP_DIR=/path/to/backups
export POSTGRES_COMPRESSION=true
export POSTGRES_PARALLEL_JOBS=4

# Run the script
python3 postgres_backup_restore.py
```

#### Command Line Options
```bash
# Show help
python3 postgres_backup_restore.py --help

# Show environment variable help
python3 postgres_backup_restore.py --env-help

# Show version
python3 postgres_backup_restore.py --version
```

### Shell Script Version

#### Interactive Mode
```bash
./postgres-backup-restore.sh
```

#### Command Line Mode
```bash
# Direct execution (non-interactive)
./postgres-backup-restore.sh
```

#### Download and Execute
```bash
curl -sSL https://raw.githubusercontent.com/Mitsuzuki-satou/postgres-backup-tool/main/postgres-backup-restore.sh | bash
```

## 🔧 Configuration

### Configuration Priority
1. **Environment Variables** (highest priority)
2. **Configuration File**
3. **Default Values** (lowest priority)

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_REMOTE_HOST` | Remote database host | `46.250.224.248` |
| `POSTGRES_REMOTE_PORT` | Remote database port | `54321` |
| `POSTGRES_REMOTE_DB` | Remote database name | `dccpadmin_backup1` |
| `POSTGRES_REMOTE_USER` | Remote database user | `philex` |
| `POSTGRES_REMOTE_PASSWORD` | Remote database password | `admin@123` |
| `POSTGRES_LOCAL_HOST` | Local database host | `localhost` |
| `POSTGRES_LOCAL_PORT` | Local database port | `5432` |
| `POSTGRES_LOCAL_USER` | Local database user | `postgres` |
| `POSTGRES_LOCAL_PASSWORD` | Local database password | `postgres` |
| `POSTGRES_NEW_DB_NAME` | Name for restored database | `dccpadmin_backup_restored` |
| `POSTGRES_BACKUP_DIR` | Backup directory path | `~/postgres_backups` |
| `POSTGRES_COMPRESSION` | Enable compression | `true` |
| `POSTGRES_PARALLEL_JOBS` | Number of parallel jobs | `4` |

### Configuration Files

**Python Version (JSON):**
```json
{
    "REMOTE_HOST": "your-server.com",
    "REMOTE_PORT": "54321",
    "REMOTE_DB": "your_database",
    "REMOTE_USER": "your_user",
    "REMOTE_PASSWORD": "your_password",
    "LOCAL_HOST": "localhost",
    "LOCAL_PORT": "5432",
    "LOCAL_USER": "postgres",
    "LOCAL_PASSWORD": "postgres",
    "NEW_DB_NAME": "restored_db",
    "BACKUP_DIR": "/path/to/backups",
    "COMPRESSION": true,
    "PARALLEL_JOBS": 4
}
```

Location: `~/.postgres_backup_config` (JSON) or `~/.postgres_backup_config` (shell script)

## 🎯 Operations

### 1. Full Backup & Restore
Complete backup from remote database and restore to local database.

### 2. Backup Only
Create backup from remote database without restoration.

### 3. Restore Only
Restore from an existing backup file.

### 4. Test Connections
Verify remote and local database connections.

### 5. Configuration
Modify configuration settings interactively.

### 6. View Logs
Display recent operation logs.

### 7. List Backups
Show available backup files with details.

## 📁 Backup Formats

### SQL Format (.sql)
- Plain SQL dump
- Compatible with any PostgreSQL version
- Larger file size
- No compression

### Compressed SQL (.sql.gz)
- Gzip-compressed SQL dump
- Good compression ratio
- Smaller file size
- Slower backup, faster transfer

### Directory Format (.tar.gz)
- Parallel backup processing
- Best performance for large databases
- Built-in compression
- Requires `pg_restore` for restoration

## 🔄 Docker Usage

```dockerfile
FROM python:3.9-slim

# Install PostgreSQL client
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

# Download the script
COPY postgres_backup_restore.py /app/
WORKDIR /app

# Set environment variables
ENV POSTGRES_REMOTE_HOST=your-server.com
ENV POSTGRES_REMOTE_USER=your-user
ENV POSTGRES_REMOTE_PASSWORD=your-password

# Run the script
CMD ["python3", "postgres_backup_restore.py"]
```

## 🐳 Docker Run Example

```bash
docker run --rm \
  -e POSTGRES_REMOTE_HOST=your-server.com \
  -e POSTGRES_REMOTE_USER=your-user \
  -e POSTGRES_REMOTE_PASSWORD=your-password \
  -v /path/to/backups:/backups \
  postgres-backup-tool:latest
```

## 🔄 CI/CD Integration

### GitHub Actions
```yaml
name: PostgreSQL Backup
on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  backup:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2

    - name: Setup Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'

    - name: Install PostgreSQL client
      run: sudo apt-get install -y postgresql-client

    - name: Download backup script
      run: curl -sSL https://raw.githubusercontent.com/Mitsuzuki-satou/postgres-backup-tool/main/postgres_backup_restore.py -o backup.py

    - name: Run backup
      env:
        POSTGRES_REMOTE_HOST: ${{ secrets.DB_HOST }}
        POSTGRES_REMOTE_USER: ${{ secrets.DB_USER }}
        POSTGRES_REMOTE_PASSWORD: ${{ secrets.DB_PASSWORD }}
        POSTGRES_BACKUP_DIR: ./backups
      run: python3 backup.py
```

## 📝 Logging

Both versions create detailed logs in `~/.postgres_backup_logs/` with timestamps:

- **Backup operations** with file sizes and duration
- **Restore operations** with table counts and verification
- **Error messages** with stack traces
- **Configuration changes** and connection tests

## 🔍 Troubleshooting

### Common Issues

1. **Connection failed**
   - Verify database credentials
   - Check network connectivity
   - Ensure PostgreSQL is running

2. **Permission denied**
   - Check user privileges
   - Verify backup directory permissions
   - Ensure PostgreSQL user has necessary rights

3. **Out of space**
   - Check disk space on backup directory
   - Monitor database size
   - Clean up old backups

4. **Slow performance**
   - Increase parallel jobs
   - Enable compression
   - Check network bandwidth

### Debug Mode

Enable verbose output for debugging:

```bash
# Python version
python3 postgres_backup_restore.py --verbose

# Shell script
export DEBUG=1
./postgres-backup-restore.sh
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/Mitsuzuki-satou/postgres-backup-tool/issues)
- **Documentation**: [Wiki](https://github.com/Mitsuzuki-satou/postgres-backup-tool/wiki)
- **Discussions**: [GitHub Discussions](https://github.com/Mitsuzuki-satou/postgres-backup-tool/discussions)

## 🔗 Links

- **Repository**: https://github.com/Mitsuzuki-satou/postgres-backup-tool
- **Shell Script**: [postgres-backup-restore.sh](https://raw.githubusercontent.com/Mitsuzuki-satou/postgres-backup-tool/main/postgres-backup-restore.sh)
- **Python Script**: [postgres_backup_restore.py](https://raw.githubusercontent.com/Mitsuzuki-satou/postgres-backup-tool/main/postgres_backup_restore.py)

---

⭐ **Star this repository if it helps you!**