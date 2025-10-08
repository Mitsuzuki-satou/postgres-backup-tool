#!/usr/bin/env python3

"""
PostgreSQL Advanced Backup and Restore Tool
Version: 2.0
Author: Enhanced by AI Assistant (Python Implementation)
Description: User-friendly PostgreSQL backup and restore with visual feedback
"""

import os
import sys
import time
import json
import shutil
import subprocess
import threading
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple, Any
import tempfile
import tarfile
import gzip

# Terminal color codes
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[0;33m'
    BLUE = '\033[0;34m'
    MAGENTA = '\033[0;35m'
    CYAN = '\033[0;36m'
    WHITE = '\033[1;37m'
    BOLD = '\033[1m'
    NC = '\033[0m'  # No Color

# Unicode symbols
class Symbols:
    CHECK = "✓"
    CROSS = "✗"
    ARROW = "→"
    GEAR = "⚙"
    DATABASE = "🗄"
    BACKUP = "💾"
    RESTORE = "📥"
    CLOCK = "⏱"


class Logger:
    """Logging utility with file output"""

    def __init__(self):
        self.log_dir = Path.home() / ".postgres_backup_logs"
        self.log_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"backup_restore_{timestamp}.log"

    def log(self, message: str):
        """Log message to file and console"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        with open(self.log_file, "a") as f:
            f.write(log_message + "\n")

    def info(self, message: str):
        self.log(f"INFO: {message}")

    def error(self, message: str):
        self.log(f"ERROR: {message}")

    def warning(self, message: str):
        self.log(f"WARNING: {message}")


class ColorPrinter:
    """Colored output utility"""

    @staticmethod
    def print_color(color: str, message: str):
        print(f"{color}{message}{Colors.NC}")

    @staticmethod
    def print_header(title: str, width: int = 80):
        padding = (width - len(title) - 2) // 2
        print()
        ColorPrinter.print_color(Colors.CYAN, "=" * width)
        ColorPrinter.print_color(Colors.WHITE, f"{' ' * padding} {title} {' ' * padding}")
        ColorPrinter.print_color(Colors.CYAN, "=" * width)
        print()

    @staticmethod
    def print_step(step_num: int, step_desc: str):
        print()
        ColorPrinter.print_color(Colors.BLUE, f"{Colors.BOLD}STEP {step_num}: {step_desc}{Colors.NC}")
        ColorPrinter.print_color(Colors.BLUE, "─" * 50)


class ProgressTracker:
    """Progress tracking utilities"""

    @staticmethod
    def show_progress(current: int, total: int, message: str, width: int = 50):
        """Display progress bar"""
        percentage = (current * 100) // total
        completed = (current * width) // total
        remaining = width - completed

        bar = f"{Colors.GREEN}{'█' * completed}{Colors.WHITE}{'░' * remaining}"
        print(f"\r{Colors.CYAN}{message} [{bar}{Colors.CYAN}] {percentage}% {Colors.NC}", end="", flush=True)

    @staticmethod
    def track_process(process: subprocess.Popen, message: str, estimated_time: int = 60):
        """Track progress of a running process"""
        start_time = time.time()
        elapsed = 0

        while process.poll() is None:
            elapsed = int(time.time() - start_time)

            if elapsed < estimated_time:
                progress = (elapsed * 100) // estimated_time
            else:
                progress = 95  # Keep at 95% if taking longer than expected

            if progress > 99:
                progress = 99

            ProgressTracker.show_progress(progress, 100, message)

            mins, secs = divmod(elapsed, 60)
            print(f"{Colors.YELLOW} [{mins}m{secs}s elapsed]{Colors.NC}", end="", flush=True)

            time.sleep(1)

        # Show completion
        ProgressTracker.show_progress(100, 100, message)
        mins, secs = divmod(elapsed, 60)
        print(f"{Colors.GREEN} [Completed in {mins}m{secs}s]{Colors.NC}")
        print()

    @staticmethod
    def monitor_backup_progress(backup_file: Path, process: subprocess.Popen,
                               message: str, target_size_mb: int = 100):
        """Monitor backup file growth"""
        start_time = time.time()
        last_size = 0

        while process.poll() is None:
            if backup_file.exists():
                current_size = backup_file.stat().st_size // (1024 * 1024)  # MB

                progress = (current_size * 100) // target_size_mb
                if progress > 99:
                    progress = 99

                elapsed = int(time.time() - start_time)
                speed = current_size // elapsed if elapsed > 0 else 0

                ProgressTracker.show_progress(progress, 100, message)
                print(f"{Colors.YELLOW} [{current_size}MB @ {speed}MB/s]{Colors.NC}", end="", flush=True)

                last_size = current_size
            else:
                print(f"\r{Colors.CYAN}{message} {Colors.YELLOW}[Initializing...]{Colors.NC}", end="", flush=True)

            time.sleep(1)

        # Final size
        if backup_file.exists():
            final_size = backup_file.stat().st_size // (1024 * 1024)
        else:
            final_size = 0

        ProgressTracker.show_progress(100, 100, message)
        print(f"{Colors.GREEN} [{final_size}MB completed]{Colors.NC}")
        print()

    @staticmethod
    def monitor_restore_progress(database: str, process: subprocess.Popen,
                                message: str, estimated_tables: int = 50):
        """Monitor database restore progress"""
        start_time = time.time()

        while process.poll() is None:
            try:
                # Count current tables in database
                count_query = "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"
                result = subprocess.run(
                    ["psql", "-h", "localhost", "-p", "5432", "-U", "postgres",
                     "-d", database, "-tAc", count_query],
                    capture_output=True, text=True, env={**os.environ, "PGPASSWORD": "postgres"}
                )

                if result.returncode == 0:
                    current_tables = int(result.stdout.strip() or 0)

                    if estimated_tables > 0 and current_tables > 0:
                        progress = (current_tables * 100) // estimated_tables
                        if progress > 99:
                            progress = 99
                    else:
                        elapsed = int(time.time() - start_time)
                        progress = (elapsed * 100) // 120  # Assume 2 minutes max
                        if progress > 99:
                            progress = 99

                    ProgressTracker.show_progress(progress, 100, message)
                    print(f"{Colors.YELLOW} [{current_tables} tables restored]{Colors.NC}", end="", flush=True)

            except (subprocess.SubprocessError, ValueError):
                elapsed = int(time.time() - start_time)
                progress = (elapsed * 100) // 120
                if progress > 99:
                    progress = 99
                ProgressTracker.show_progress(progress, 100, message)

            time.sleep(2)

        # Final count
        try:
            result = subprocess.run(
                ["psql", "-h", "localhost", "-p", "5432", "-U", "postgres",
                 "-d", database, "-tAc", count_query],
                capture_output=True, text=True, env={**os.environ, "PGPASSWORD": "postgres"}
            )

            if result.returncode == 0:
                final_tables = int(result.stdout.strip() or 0)
            else:
                final_tables = 0
        except:
            final_tables = 0

        ProgressTracker.show_progress(100, 100, message)
        print(f"{Colors.GREEN} [{final_tables} tables completed]{Colors.NC}")
        print()


class ConfigManager:
    """Configuration management"""

    def __init__(self):
        self.config_file = Path.home() / ".postgres_backup_config"
        self.config = {
            "REMOTE_HOST": "46.250.224.248",
            "REMOTE_PORT": "54321",
            "REMOTE_DB": "dccpadmin_backup1",
            "REMOTE_USER": "philex",
            "REMOTE_PASSWORD": "admin@123",
            "LOCAL_HOST": "localhost",
            "LOCAL_PORT": "5432",
            "LOCAL_USER": "postgres",
            "LOCAL_PASSWORD": "postgres",
            "NEW_DB_NAME": "dccpadmin_backup_restored",
            "BACKUP_DIR": str(Path.home() / "postgres_backups"),
            "COMPRESSION": True,
            "PARALLEL_JOBS": 4
        }
        self.load_environment_variables()
        self.load_config()

    def load_environment_variables(self):
        """Load configuration from environment variables"""
        env_mappings = {
            "POSTGRES_REMOTE_HOST": "REMOTE_HOST",
            "POSTGRES_REMOTE_PORT": "REMOTE_PORT",
            "POSTGRES_REMOTE_DB": "REMOTE_DB",
            "POSTGRES_REMOTE_USER": "REMOTE_USER",
            "POSTGRES_REMOTE_PASSWORD": "REMOTE_PASSWORD",
            "POSTGRES_LOCAL_HOST": "LOCAL_HOST",
            "POSTGRES_LOCAL_PORT": "LOCAL_PORT",
            "POSTGRES_LOCAL_USER": "LOCAL_USER",
            "POSTGRES_LOCAL_PASSWORD": "LOCAL_PASSWORD",
            "POSTGRES_NEW_DB_NAME": "NEW_DB_NAME",
            "POSTGRES_BACKUP_DIR": "BACKUP_DIR",
            "POSTGRES_COMPRESSION": "COMPRESSION",
            "POSTGRES_PARALLEL_JOBS": "PARALLEL_JOBS"
        }

        env_loaded = False
        for env_var, config_key in env_mappings.items():
            env_value = os.environ.get(env_var)
            if env_value is not None:
                # Convert string values to appropriate types
                if config_key == "COMPRESSION":
                    self.config[config_key] = env_value.lower() in ('true', 'yes', '1', 'on')
                elif config_key == "PARALLEL_JOBS":
                    try:
                        self.config[config_key] = int(env_value)
                    except ValueError:
                        print(f"Warning: Invalid value for {env_var}, using default")
                else:
                    self.config[config_key] = env_value
                env_loaded = True

        if env_loaded:
            ColorPrinter.print_color(Colors.GREEN, f"{Symbols.CHECK} Configuration loaded from environment variables")

    def load_config(self):
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    file_config = json.load(f)
                    self.config.update(file_config)
                ColorPrinter.print_color(Colors.GREEN, f"{Symbols.CHECK} Loading configuration from {self.config_file}")
            except (json.JSONDecodeError, IOError) as e:
                ColorPrinter.print_color(Colors.YELLOW, f"{Symbols.GEAR} Error loading config file, using defaults: {e}")
        else:
            ColorPrinter.print_color(Colors.YELLOW, f"{Symbols.GEAR} No configuration file found, using defaults")

    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
            ColorPrinter.print_color(Colors.GREEN, f"{Symbols.CHECK} Configuration saved successfully!")
        except IOError as e:
            ColorPrinter.print_color(Colors.RED, f"{Symbols.CROSS} Error saving configuration: {e}")

    def configure_interactive(self):
        """Interactive configuration setup"""
        ColorPrinter.print_header("INTERACTIVE CONFIGURATION")

        print("Current configuration:")
        print()
        for key, value in self.config.items():
            if "PASSWORD" in key:
                masked_value = "*" * len(str(value))
                print(f"  {key:<20}: {masked_value}")
            else:
                print(f"  {key:<20}: {value}")
        print()

        choice = input("Do you want to modify the configuration? (y/N): ").lower().strip()

        if choice == 'y':
            for key in self.config.keys():
                current_value = self.config[key]
                if "PASSWORD" in key:
                    new_value = input(f"{key} [****]: ").strip()
                    if new_value:
                        self.config[key] = new_value
                else:
                    new_value = input(f"{key} [{current_value}]: ").strip()
                    if new_value:
                        # Convert string values to appropriate types
                        if key == "COMPRESSION":
                            self.config[key] = new_value.lower() in ('true', 'yes', '1')
                        elif key == "PARALLEL_JOBS":
                            try:
                                self.config[key] = int(new_value)
                            except ValueError:
                                print(f"Invalid value for {key}, keeping current value")
                        else:
                            self.config[key] = new_value

            self.save_config()


class DatabaseOperations:
    """Database operations class"""

    def __init__(self, config: Dict, logger: Logger):
        self.config = config
        self.logger = logger

    def test_connection(self, host: str, port: str, user: str, password: str,
                       database: str = "postgres", description: str = "Database") -> bool:
        """Test database connection"""
        ColorPrinter.print_color(Colors.YELLOW, f"{Symbols.GEAR} Testing {description} connection...")

        env = {**os.environ, "PGPASSWORD": password}
        try:
            result = subprocess.run(
                ["psql", "-h", host, "-p", port, "-U", user, "-d", database, "-c", "SELECT version();"],
                capture_output=True, text=True, env=env, timeout=30
            )

            if result.returncode == 0:
                ColorPrinter.print_color(Colors.GREEN, f"{Symbols.CHECK} {description} connection successful")
                self.logger.info(f"{description} connection successful")
                return True
            else:
                ColorPrinter.print_color(Colors.RED, f"{Symbols.CROSS} {description} connection failed")
                self.logger.error(f"{description} connection failed: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            ColorPrinter.print_color(Colors.RED, f"{Symbols.CROSS} {description} connection timeout")
            self.logger.error(f"{description} connection timeout")
            return False
        except Exception as e:
            ColorPrinter.print_color(Colors.RED, f"{Symbols.CROSS} {description} connection error: {e}")
            self.logger.error(f"{description} connection error: {e}")
            return False

    def get_db_size(self, host: str, port: str, user: str, password: str, database: str) -> str:
        """Get database size in human readable format"""
        env = {**os.environ, "PGPASSWORD": password}
        try:
            result = subprocess.run(
                ["psql", "-h", host, "-p", port, "-U", user, "-d", database,
                 "-tAc", f"SELECT pg_size_pretty(pg_database_size('{database}'));"],
                capture_output=True, text=True, env=env
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            self.logger.error(f"Error getting database size: {e}")
        return "Unknown"

    def get_table_count(self, host: str, port: str, user: str, password: str, database: str) -> int:
        """Get table count in database"""
        env = {**os.environ, "PGPASSWORD": password}
        try:
            result = subprocess.run(
                ["psql", "-h", host, "-p", port, "-U", user, "-d", database,
                 "-tAc", "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"],
                capture_output=True, text=True, env=env
            )
            if result.returncode == 0:
                return int(result.stdout.strip() or 0)
        except Exception as e:
            self.logger.error(f"Error getting table count: {e}")
        return 0

    def create_backup(self) -> Optional[Path]:
        """Create database backup"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{self.config['REMOTE_DB']}_{timestamp}"

        # Create backup directory
        backup_dir = Path(self.config["BACKUP_DIR"])
        backup_dir.mkdir(parents=True, exist_ok=True)

        env = {**os.environ, "PGPASSWORD": self.config["REMOTE_PASSWORD"]}

        ColorPrinter.print_color(Colors.BLUE, f"{Symbols.BACKUP} Starting backup process...")
        ColorPrinter.print_color(Colors.CYAN,
                                f"Source: {self.config['REMOTE_HOST']}:{self.config['REMOTE_PORT']}/{self.config['REMOTE_DB']}")

        # Get source database size
        source_size_pretty = self.get_db_size(
            self.config["REMOTE_HOST"], self.config["REMOTE_PORT"],
            self.config["REMOTE_USER"], self.config["REMOTE_PASSWORD"],
            self.config["REMOTE_DB"]
        )

        # Get size in MB for progress estimation
        try:
            result = subprocess.run(
                ["psql", "-h", self.config["REMOTE_HOST"], "-p", self.config["REMOTE_PORT"],
                 "-U", self.config["REMOTE_USER"], "-d", self.config["REMOTE_DB"],
                 "-tAc", f"SELECT ROUND(pg_database_size('{self.config['REMOTE_DB']}') / 1024.0 / 1024.0);"],
                capture_output=True, text=True, env=env
            )
            source_size_mb = int(float(result.stdout.strip() or "100"))
        except:
            source_size_mb = 100

        ColorPrinter.print_color(Colors.YELLOW, f"Database size: {source_size_pretty} (estimating {source_size_mb}MB backup)")
        print()

        backup_file = None

        if (self.config["PARALLEL_JOBS"] > 1 and self.config["COMPRESSION"]):
            # Directory format with parallel jobs and compression
            temp_backup_dir = backup_dir / f"{backup_name}_dir"
            backup_file = backup_dir / f"{backup_name}.tar.gz"

            ColorPrinter.print_color(Colors.CYAN, f"Target: {temp_backup_dir} (will be compressed to {backup_file.name})")
            print()

            # Create backup using directory format
            cmd = [
                "pg_dump", "-h", self.config["REMOTE_HOST"], "-p", self.config["REMOTE_PORT"],
                "-U", self.config["REMOTE_USER"], "-d", self.config["REMOTE_DB"],
                "--verbose", "--clean", "--no-owner", "--no-privileges",
                "--format=directory", f"--jobs={self.config['PARALLEL_JOBS']}",
                "--file", str(temp_backup_dir)
            ]

            process = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            ProgressTracker.track_process(process, "Creating parallel backup", 90)

            if process.returncode == 0:
                # Compress the directory
                ColorPrinter.print_color(Colors.YELLOW, f"{Symbols.GEAR} Compressing backup directory...")
                with tarfile.open(backup_file, "w:gz") as tar:
                    tar.add(temp_backup_dir, arcname=temp_backup_dir.name)

                # Remove temporary directory
                shutil.rmtree(temp_backup_dir)
            else:
                ColorPrinter.print_color(Colors.RED, f"{Symbols.CROSS} Backup failed!")
                self.logger.error("Backup failed during directory format creation")
                return None

        elif self.config["COMPRESSION"]:
            # Compressed SQL format
            backup_file = backup_dir / f"{backup_name}.sql.gz"
            ColorPrinter.print_color(Colors.CYAN, f"Target: {backup_file}")
            print()

            cmd = [
                "pg_dump", "-h", self.config["REMOTE_HOST"], "-p", self.config["REMOTE_PORT"],
                "-U", self.config["REMOTE_USER"], "-d", self.config["REMOTE_DB"],
                "--verbose", "--clean", "--no-owner", "--no-privileges"
            ]

            with gzip.open(backup_file, 'wt') as gz_file:
                process = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
                estimated_size = source_size_mb * 30 // 100  # Estimate 30% of original
                ProgressTracker.monitor_backup_progress(backup_file, process, "Creating compressed backup", estimated_size)

                if process.stdout:
                    for line in process.stdout:
                        gz_file.write(line)

        else:
            # Regular SQL format
            backup_file = backup_dir / f"{backup_name}.sql"
            ColorPrinter.print_color(Colors.CYAN, f"Target: {backup_file}")
            print()

            cmd = [
                "pg_dump", "-h", self.config["REMOTE_HOST"], "-p", self.config["REMOTE_PORT"],
                "-U", self.config["REMOTE_USER"], "-d", self.config["REMOTE_DB"],
                "--verbose", "--clean", "--no-owner", "--no-privileges"
            ]

            with open(backup_file, 'w') as sql_file:
                process = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
                estimated_size = source_size_mb * 80 // 100  # Estimate 80% of original
                ProgressTracker.monitor_backup_progress(backup_file, process, "Creating backup", estimated_size)

                if process.stdout:
                    for line in process.stdout:
                        sql_file.write(line)

        if backup_file and backup_file.exists():
            file_size = self._format_file_size(backup_file.stat().st_size)
            ColorPrinter.print_color(Colors.GREEN, f"{Symbols.CHECK} Backup created successfully!")
            ColorPrinter.print_color(Colors.GREEN, f"   File: {backup_file.name}")
            ColorPrinter.print_color(Colors.GREEN, f"   Size: {file_size}")
            ColorPrinter.print_color(Colors.GREEN, f"   Location: {backup_file}")
            self.logger.info(f"Backup created: {backup_file} ({file_size})")
            return backup_file
        else:
            ColorPrinter.print_color(Colors.RED, f"{Symbols.CROSS} Backup failed!")
            self.logger.error("Backup creation failed")
            return None

    def restore_backup(self, backup_file: Path) -> bool:
        """Restore database from backup file"""
        ColorPrinter.print_color(Colors.BLUE, f"{Symbols.RESTORE} Starting restore process...")

        env = {**os.environ, "PGPASSWORD": self.config["LOCAL_PASSWORD"]}

        # Check if database exists
        db_exists = self._database_exists()

        if db_exists:
            ColorPrinter.print_color(Colors.YELLOW, f"⚠ Database '{self.config['NEW_DB_NAME']}' already exists!")
            print()
            ColorPrinter.print_color(Colors.CYAN, "Options:")
            ColorPrinter.print_color(Colors.CYAN, "  1) Drop and recreate (DESTRUCTIVE)")
            ColorPrinter.print_color(Colors.CYAN, "  2) Use different name")
            ColorPrinter.print_color(Colors.CYAN, "  3) Cancel operation")
            print()

            while True:
                choice = input("Select option (1-3): ").strip()
                if choice == "1":
                    ColorPrinter.print_color(Colors.YELLOW, "Dropping existing database...")
                    subprocess.run(
                        ["psql", "-h", self.config["LOCAL_HOST"], "-p", self.config["LOCAL_PORT"],
                         "-U", self.config["LOCAL_USER"], "-d", "postgres",
                         "-c", f"DROP DATABASE \"{self.config['NEW_DB_NAME']}\";"],
                        capture_output=True, env=env
                    )
                    break
                elif choice == "2":
                    new_name = input("Enter new database name: ").strip()
                    if new_name:
                        self.config["NEW_DB_NAME"] = new_name
                    break
                elif choice == "3":
                    ColorPrinter.print_color(Colors.YELLOW, "Operation cancelled")
                    return False
                else:
                    ColorPrinter.print_color(Colors.RED, "Invalid option. Please select 1, 2, or 3.")

        # Create database
        ColorPrinter.print_color(Colors.BLUE, f"{Symbols.DATABASE} Creating database '{self.config['NEW_DB_NAME']}'...")
        result = subprocess.run(
            ["psql", "-h", self.config["LOCAL_HOST"], "-p", self.config["LOCAL_PORT"],
             "-U", self.config["LOCAL_USER"], "-d", "postgres",
             "-c", f"CREATE DATABASE \"{self.config['NEW_DB_NAME']}\";"],
            capture_output=True, env=env
        )

        if result.returncode != 0:
            ColorPrinter.print_color(Colors.RED, f"{Symbols.CROSS} Failed to create database!")
            self.logger.error(f"Database creation failed: {result.stderr}")
            return False

        # Restore from backup
        ColorPrinter.print_color(Colors.BLUE, f"{Symbols.RESTORE} Restoring data to '{self.config['NEW_DB_NAME']}'...")

        # Estimate table count for progress
        source_table_count = self._estimate_table_count(backup_file)
        ColorPrinter.print_color(Colors.YELLOW, f"Estimated tables to restore: {source_table_count}")
        print()

        try:
            if backup_file.suffix == ".gz" and backup_file.stem.endswith(".tar"):
                # Directory format backup (compressed tar)
                success = self._restore_from_directory_format(backup_file, source_table_count)
            elif backup_file.suffix == ".gz":
                # Compressed SQL backup
                success = self._restore_from_compressed_sql(backup_file, source_table_count)
            elif backup_file.suffix == ".sql":
                # Regular SQL backup
                success = self._restore_from_sql(backup_file, source_table_count)
            else:
                ColorPrinter.print_color(Colors.RED, f"{Symbols.CROSS} Unsupported backup format!")
                return False

            if success:
                ColorPrinter.print_color(Colors.GREEN, f"{Symbols.CHECK} Restore completed successfully!")
                self.logger.info(f"Database restored: {self.config['NEW_DB_NAME']}")
                return True
            else:
                ColorPrinter.print_color(Colors.RED, f"{Symbols.CROSS} Restore failed!")
                self.logger.error("Database restore failed")
                return False

        except Exception as e:
            ColorPrinter.print_color(Colors.RED, f"{Symbols.CROSS} Restore error: {e}")
            self.logger.error(f"Restore error: {e}")
            return False

    def verify_restoration(self):
        """Verify database restoration"""
        ColorPrinter.print_color(Colors.BLUE, f"{Symbols.GEAR} Verifying restoration...")

        table_count = self.get_table_count(
            self.config["LOCAL_HOST"], self.config["LOCAL_PORT"],
            self.config["LOCAL_USER"], self.config["LOCAL_PASSWORD"],
            self.config["NEW_DB_NAME"]
        )

        db_size = self.get_db_size(
            self.config["LOCAL_HOST"], self.config["LOCAL_PORT"],
            self.config["LOCAL_USER"], self.config["LOCAL_PASSWORD"],
            self.config["NEW_DB_NAME"]
        )

        ColorPrinter.print_color(Colors.GREEN, f"{Symbols.CHECK} Verification complete!")
        ColorPrinter.print_color(Colors.CYAN, f"   Database: {self.config['NEW_DB_NAME']}")
        ColorPrinter.print_color(Colors.CYAN, f"   Tables: {table_count}")
        ColorPrinter.print_color(Colors.CYAN, f"   Size: {db_size}")

        self.logger.info(f"Verification: {self.config['NEW_DB_NAME']} - Tables: {table_count}, Size: {db_size}")

    def _database_exists(self) -> bool:
        """Check if database exists"""
        env = {**os.environ, "PGPASSWORD": self.config["LOCAL_PASSWORD"]}
        try:
            result = subprocess.run(
                ["psql", "-h", self.config["LOCAL_HOST"], "-p", self.config["LOCAL_PORT"],
                 "-U", self.config["LOCAL_USER"], "-d", "postgres",
                 "-tAc", f"SELECT 1 FROM pg_database WHERE datname='{self.config['NEW_DB_NAME']}'"],
                capture_output=True, text=True, env=env
            )
            return result.stdout.strip() == "1"
        except:
            return False

    def _estimate_table_count(self, backup_file: Path) -> int:
        """Estimate table count from backup file"""
        try:
            if backup_file.suffix == ".gz" and backup_file.stem.endswith(".tar"):
                # Directory format - use default estimate
                return 50
            elif backup_file.suffix == ".gz":
                # Compressed SQL
                with gzip.open(backup_file, 'rt') as f:
                    content = f.read()
                    return content.count("CREATE TABLE")
            elif backup_file.suffix == ".sql":
                # Regular SQL
                with open(backup_file, 'r') as f:
                    content = f.read()
                    return content.count("CREATE TABLE")
        except Exception:
            pass
        return 50  # Default estimate

    def _restore_from_directory_format(self, backup_file: Path, table_count: int) -> bool:
        """Restore from directory format backup"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Extract backup archive
            ColorPrinter.print_color(Colors.YELLOW, f"{Symbols.GEAR} Extracting backup archive...")
            with tarfile.open(backup_file, 'r:gz') as tar:
                tar.extractall(temp_dir)

            # Find the extracted directory
            extracted_dirs = [d for d in Path(temp_dir).iterdir() if d.is_dir()]
            if not extracted_dirs:
                return False

            backup_dir = extracted_dirs[0]

            # Update table count from TOC if available
            toc_file = backup_dir / "toc.dat"
            if toc_file.exists():
                try:
                    with open(toc_file, 'rb') as f:
                        toc_content = f.read().decode('utf-8', errors='ignore')
                        table_count = toc_content.count("TABLE")
                except:
                    pass

            ColorPrinter.print_color(Colors.BLUE, f"Starting parallel restore with {self.config['PARALLEL_JOBS']} jobs...")

            # Restore using pg_restore
            cmd = [
                "pg_restore", "-h", self.config["LOCAL_HOST"], "-p", self.config["LOCAL_PORT"],
                "-U", self.config["LOCAL_USER"], "-d", self.config["NEW_DB_NAME"],
                "--verbose", "--clean", "--no-owner", "--no-privileges",
                f"--jobs={self.config['PARALLEL_JOBS']}", str(backup_dir)
            ]

            env = {**os.environ, "PGPASSWORD": self.config["LOCAL_PASSWORD"]}
            process = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            ProgressTracker.monitor_restore_progress(self.config["NEW_DB_NAME"], process,
                                                   "Restoring database (parallel)", table_count)

            return process.returncode == 0

    def _restore_from_compressed_sql(self, backup_file: Path, table_count: int) -> bool:
        """Restore from compressed SQL backup"""
        ColorPrinter.print_color(Colors.BLUE, "Starting SQL restore from compressed backup...")

        cmd = [
            "psql", "-h", self.config["LOCAL_HOST"], "-p", self.config["LOCAL_PORT"],
            "-U", self.config["LOCAL_USER"], "-d", self.config["NEW_DB_NAME"]
        ]

        env = {**os.environ, "PGPASSWORD": self.config["LOCAL_PASSWORD"]}

        with gzip.open(backup_file, 'rt') as gz_file:
            process = subprocess.Popen(cmd, env=env, stdin=subprocess.PIPE,
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)

            # Start restore process in a separate thread to monitor progress
            def restore_thread():
                with gz_file as f:
                    for line in f:
                        if process.stdin:
                            process.stdin.write(line)
                            process.stdin.flush()
                if process.stdin:
                    process.stdin.close()

            restore_thread = threading.Thread(target=restore_thread)
            restore_thread.start()

            ProgressTracker.monitor_restore_progress(self.config["NEW_DB_NAME"], process,
                                                   "Restoring compressed SQL backup", table_count)
            restore_thread.join()

            return process.returncode == 0

    def _restore_from_sql(self, backup_file: Path, table_count: int) -> bool:
        """Restore from regular SQL backup"""
        ColorPrinter.print_color(Colors.BLUE, "Starting SQL restore from backup file...")

        cmd = [
            "psql", "-h", self.config["LOCAL_HOST"], "-p", self.config["LOCAL_PORT"],
            "-U", self.config["LOCAL_USER"], "-d", self.config["NEW_DB_NAME"]
        ]

        env = {**os.environ, "PGPASSWORD": self.config["LOCAL_PASSWORD"]}

        with open(backup_file, 'r') as sql_file:
            process = subprocess.Popen(cmd, env=env, stdin=subprocess.PIPE,
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)

            # Start restore process in a separate thread to monitor progress
            def restore_thread():
                with sql_file as f:
                    for line in f:
                        if process.stdin:
                            process.stdin.write(line)
                            process.stdin.flush()
                if process.stdin:
                    process.stdin.close()

            restore_thread = threading.Thread(target=restore_thread)
            restore_thread.start()

            ProgressTracker.monitor_restore_progress(self.config["NEW_DB_NAME"], process,
                                                   "Restoring SQL backup", table_count)
            restore_thread.join()

            return process.returncode == 0

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f}TB"


class PostgresBackupRestore:
    """Main application class"""

    def __init__(self):
        self.logger = Logger()
        self.config_manager = ConfigManager()
        self.db_ops = DatabaseOperations(self.config_manager.config, self.logger)
        self.backup_file = None

    def show_menu(self):
        """Display main menu"""
        os.system('clear')
        ColorPrinter.print_header("PostgreSQL Advanced Backup & Restore Tool v2.0 (Python)")

        ColorPrinter.print_color(Colors.YELLOW, f"{Symbols.DATABASE} Current Configuration:")
        print()
        print(f"  Remote Database: {self.config_manager.config['REMOTE_HOST']}:{self.config_manager.config['REMOTE_PORT']}/{self.config_manager.config['REMOTE_DB']}")
        print(f"  Local Database:  {self.config_manager.config['LOCAL_HOST']}:{self.config_manager.config['LOCAL_PORT']}/{self.config_manager.config['NEW_DB_NAME']}")
        print(f"  Backup Directory: {self.config_manager.config['BACKUP_DIR']}")
        print(f"  Compression: {self.config_manager.config['COMPRESSION']}")
        print()

        ColorPrinter.print_color(Colors.CYAN, f"{Symbols.GEAR} Available Operations:")
        print()
        ColorPrinter.print_color(Colors.WHITE, "  1) Full Backup & Restore     - Complete backup and restore process")
        ColorPrinter.print_color(Colors.WHITE, "  2) Backup Only              - Create backup from remote database")
        ColorPrinter.print_color(Colors.WHITE, "  3) Restore Only             - Restore from existing backup file")
        ColorPrinter.print_color(Colors.WHITE, "  4) Test Connections         - Test remote and local database connections")
        ColorPrinter.print_color(Colors.WHITE, "  5) Configuration            - Modify configuration settings")
        ColorPrinter.print_color(Colors.WHITE, "  6) View Logs                - Display recent operation logs")
        ColorPrinter.print_color(Colors.WHITE, "  7) List Backups             - Show available backup files")
        ColorPrinter.print_color(Colors.WHITE, "  8) Exit                     - Exit the application")
        print()

    def list_backups(self):
        """List available backup files"""
        ColorPrinter.print_header("AVAILABLE BACKUPS")

        backup_dir = Path(self.config_manager.config["BACKUP_DIR"])
        if not backup_dir.exists():
            ColorPrinter.print_color(Colors.YELLOW, "No backup directory found.")
            return

        backup_files = []
        for pattern in ["*.sql", "*.sql.gz", "*.tar.gz"]:
            backup_files.extend(backup_dir.glob(pattern))

        backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        if not backup_files:
            ColorPrinter.print_color(Colors.YELLOW, f"No backup files found in {backup_dir}")
            return

        ColorPrinter.print_color(Colors.CYAN, f"Found {len(backup_files)} backup file(s):")
        print()

        for i, backup_file in enumerate(backup_files):
            size = self.db_ops._format_file_size(backup_file.stat().st_size)
            date = datetime.fromtimestamp(backup_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            print(f"  {i+1:2d}) {backup_file.name:<40} {size:>8}  {date}")
        print()

        return backup_files

    def view_logs(self):
        """View recent logs"""
        ColorPrinter.print_header("RECENT OPERATION LOGS")

        log_files = list(self.logger.log_dir.glob("*.log"))
        if not log_files:
            ColorPrinter.print_color(Colors.YELLOW, "No log files found.")
            return

        log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        latest_log = log_files[0]

        ColorPrinter.print_color(Colors.CYAN, f"Latest log file: {latest_log.name}")
        print()

        try:
            with open(latest_log, 'r') as f:
                lines = f.readlines()
                for line in lines[-20:]:  # Show last 20 lines
                    ColorPrinter.print_color(Colors.WHITE, line.rstrip())
        except Exception as e:
            ColorPrinter.print_color(Colors.RED, f"Error reading log file: {e}")

    def run_interactive(self):
        """Run interactive mode"""
        self.logger.info("Script started in interactive mode")

        while True:
            self.show_menu()
            choice = input("Select an option (1-8): ").strip()
            print()

            if choice == "1":
                self._run_full_backup_restore()
            elif choice == "2":
                self._run_backup_only()
            elif choice == "3":
                self._run_restore_only()
            elif choice == "4":
                self._run_connection_tests()
            elif choice == "5":
                self.config_manager.configure_interactive()
            elif choice == "6":
                self.view_logs()
            elif choice == "7":
                self.list_backups()
            elif choice == "8":
                ColorPrinter.print_color(Colors.GREEN, "Thank you for using PostgreSQL Backup & Restore Tool!")
                self.logger.info("Script ended normally")
                sys.exit(0)
            else:
                ColorPrinter.print_color(Colors.RED, "Invalid option. Please select 1-8.")

            print()
            input("Press Enter to continue...")

    def _run_full_backup_restore(self):
        """Run full backup and restore process"""
        ColorPrinter.print_header("FULL BACKUP & RESTORE PROCESS")

        # Test connections
        if not self._test_connections_with_prompt():
            return

        # Perform backup and restore
        self.backup_file = self.db_ops.create_backup()
        if self.backup_file:
            if self.db_ops.restore_backup(self.backup_file):
                self.db_ops.verify_restoration()

                # Cleanup option
                print()
                choice = input("Delete backup file? (y/N): ").lower().strip()
                if choice == 'y':
                    self.backup_file.unlink()
                    ColorPrinter.print_color(Colors.GREEN, f"{Symbols.CHECK} Backup file deleted")
                else:
                    ColorPrinter.print_color(Colors.BLUE, f"Backup file kept: {self.backup_file}")

    def _run_backup_only(self):
        """Run backup only"""
        ColorPrinter.print_header("BACKUP ONLY")

        if not self._test_remote_connection_with_prompt():
            return

        self.backup_file = self.db_ops.create_backup()

    def _run_restore_only(self):
        """Run restore only"""
        ColorPrinter.print_header("RESTORE ONLY")

        backup_files = self.list_backups()
        if not backup_files:
            return

        input_str = input("Enter backup file path (or number from list): ").strip()

        try:
            if input_str.isdigit():
                index = int(input_str) - 1
                if 0 <= index < len(backup_files):
                    backup_file = backup_files[index]
                else:
                    ColorPrinter.print_color(Colors.RED, "Invalid selection")
                    return
            else:
                backup_file = Path(input_str)
                if not backup_file.exists():
                    ColorPrinter.print_color(Colors.RED, f"{Symbols.CROSS} Backup file not found: {backup_file}")
                    return
        except (ValueError, IndexError):
            ColorPrinter.print_color(Colors.RED, "Invalid selection")
            return

        if self.db_ops.restore_backup(backup_file):
            self.db_ops.verify_restoration()

    def _run_connection_tests(self):
        """Run connection tests"""
        ColorPrinter.print_header("CONNECTION TESTS")

        self.db_ops.test_connection(
            self.config_manager.config["REMOTE_HOST"],
            self.config_manager.config["REMOTE_PORT"],
            self.config_manager.config["REMOTE_USER"],
            self.config_manager.config["REMOTE_PASSWORD"],
            self.config_manager.config["REMOTE_DB"],
            "Remote"
        )

        self.db_ops.test_connection(
            self.config_manager.config["LOCAL_HOST"],
            self.config_manager.config["LOCAL_PORT"],
            self.config_manager.config["LOCAL_USER"],
            self.config_manager.config["LOCAL_PASSWORD"],
            "postgres",
            "Local"
        )

    def _test_connections_with_prompt(self) -> bool:
        """Test connections with continue prompt"""
        remote_ok = self.db_ops.test_connection(
            self.config_manager.config["REMOTE_HOST"],
            self.config_manager.config["REMOTE_PORT"],
            self.config_manager.config["REMOTE_USER"],
            self.config_manager.config["REMOTE_PASSWORD"],
            self.config_manager.config["REMOTE_DB"],
            "Remote"
        )

        if not remote_ok:
            choice = input("Continue anyway? (y/N): ").lower().strip()
            if choice != 'y':
                return False

        local_ok = self.db_ops.test_connection(
            self.config_manager.config["LOCAL_HOST"],
            self.config_manager.config["LOCAL_PORT"],
            self.config_manager.config["LOCAL_USER"],
            self.config_manager.config["LOCAL_PASSWORD"],
            "postgres",
            "Local"
        )

        if not local_ok:
            choice = input("Continue anyway? (y/N): ").lower().strip()
            if choice != 'y':
                return False

        return True

    def _test_remote_connection_with_prompt(self) -> bool:
        """Test remote connection with continue prompt"""
        remote_ok = self.db_ops.test_connection(
            self.config_manager.config["REMOTE_HOST"],
            self.config_manager.config["REMOTE_PORT"],
            self.config_manager.config["REMOTE_USER"],
            self.config_manager.config["REMOTE_PASSWORD"],
            self.config_manager.config["REMOTE_DB"],
            "Remote"
        )

        if not remote_ok:
            choice = input("Continue anyway? (y/N): ").lower().strip()
            if choice != 'y':
                return False

        return True

    def run_command_line(self):
        """Run command-line mode"""
        ColorPrinter.print_header("COMMAND-LINE MODE")
        self.logger.info("Script started in command-line mode")

        if not self._test_connections_with_prompt():
            return

        self.backup_file = self.db_ops.create_backup()
        if self.backup_file:
            if self.db_ops.restore_backup(self.backup_file):
                self.db_ops.verify_restoration()


def check_dependencies():
    """Check required dependencies"""
    required_commands = ["psql", "pg_dump", "pg_restore"]
    missing_commands = []

    for cmd in required_commands:
        try:
            subprocess.run([cmd, "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing_commands.append(cmd)

    if missing_commands:
        ColorPrinter.print_color(Colors.RED,
                                f"{Symbols.CROSS} Required commands not found: {', '.join(missing_commands)}")
        ColorPrinter.print_color(Colors.RED, "Please install PostgreSQL client tools.")
        sys.exit(1)


def print_environment_help():
    """Print environment variable configuration help"""
    print("PostgreSQL Backup & Restore Tool - Environment Variables")
    print("=" * 60)
    print()
    print("You can configure the tool using environment variables:")
    print()
    print("Remote Database:")
    print("  POSTGRES_REMOTE_HOST     - Remote database host")
    print("  POSTGRES_REMOTE_PORT     - Remote database port")
    print("  POSTGRES_REMOTE_DB       - Remote database name")
    print("  POSTGRES_REMOTE_USER     - Remote database user")
    print("  POSTGRES_REMOTE_PASSWORD - Remote database password")
    print()
    print("Local Database:")
    print("  POSTGRES_LOCAL_HOST      - Local database host")
    print("  POSTGRES_LOCAL_PORT      - Local database port")
    print("  POSTGRES_LOCAL_USER      - Local database user")
    print("  POSTGRES_LOCAL_PASSWORD  - Local database password")
    print("  POSTGRES_NEW_DB_NAME     - Name for restored database")
    print()
    print("Backup Configuration:")
    print("  POSTGRES_BACKUP_DIR      - Backup directory path")
    print("  POSTGRES_COMPRESSION     - Enable compression (true/false)")
    print("  POSTGRES_PARALLEL_JOBS   - Number of parallel jobs")
    print()
    print("Example usage:")
    print("  export POSTGRES_REMOTE_HOST=your-server.com")
    print("  export POSTGRES_REMOTE_USER=your-user")
    print("  export POSTGRES_REMOTE_PASSWORD=your-password")
    print("  python3 postgres_backup_restore.py")
    print()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="PostgreSQL Advanced Backup and Restore Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  You can configure the tool using environment variables:
  POSTGRES_REMOTE_HOST, POSTGRES_REMOTE_PORT, POSTGRES_REMOTE_DB, etc.
  Use --env-help for detailed environment variable information.
        """
    )
    parser.add_argument("--version", action="version", version="PostgreSQL Backup & Restore Tool v2.0")
    parser.add_argument("--env-help", action="store_true", help="Show environment variable help")

    args = parser.parse_args()

    if args.env_help:
        print_environment_help()
        sys.exit(0)

    # Check dependencies
    check_dependencies()

    # Create and run application
    app = PostgresBackupRestore()

    if len(sys.argv) == 1:
        # Interactive mode
        app.run_interactive()
    else:
        # Command-line mode
        app.run_command_line()


if __name__ == "__main__":
    main()