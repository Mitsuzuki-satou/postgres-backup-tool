"""
Configuration management for PostgreSQL Backup & Restore Tool
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

from .models import DatabaseConfig, BackupConfig, BackupJob


class ConfigManager:
    """Configuration management with environment variable support"""
    
    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = config_file or Path.home() / ".postgres_backup_config.json"
        self.app_dir = Path.home() / ".postgres_backup_tool"
        self.app_dir.mkdir(exist_ok=True)
        
        # Load environment variables
        load_dotenv()
        
        # Default configuration
        self.config = self._get_default_config()
        
        # Load from file and environment
        self._load_from_file()
        self._load_from_environment()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "app": {
                "version": "3.0.0",
                "log_level": "INFO",
                "max_log_files": 10,
                "backup_dir": str(Path.home() / "postgres_backups"),
                "temp_dir": str(self.app_dir / "temp"),
                "data_dir": str(self.app_dir / "data")
            },
            "database": {
                "source": {
                    "host": "localhost",
                    "port": 5432,
                    "database": "postgres",
                    "username": "postgres",
                    "password": "",
                    "ssl_mode": "prefer",
                    "connection_timeout": 30
                },
                "target": {
                    "host": "localhost", 
                    "port": 5432,
                    "database": "postgres",
                    "username": "postgres",
                    "password": "",
                    "ssl_mode": "prefer",
                    "connection_timeout": 30
                }
            },
            "backup": {
                "default_type": "full",
                "compression": "gzip",
                "encryption": "none",
                "parallel_jobs": 4,
                "retention_days": 30,
                "verify_backups": True,
                "exclude_schemas": [],
                "include_schemas": [],
                "exclude_tables": [],
                "include_tables": [],
                "verbose": True,
                "clean_before_restore": True,
                "no_owner": True,
                "no_privileges": True
            },
            "scheduler": {
                "enabled": False,
                "max_concurrent_jobs": 2,
                "job_timeout": 3600,
                "retry_attempts": 3,
                "retry_delay": 300
            },
            "web": {
                "host": "127.0.0.1",
                "port": 8080,
                "debug": False,
                "secret_key": "change-me-in-production",
                "cors_origins": ["*"],
                "max_upload_size": 104857600  # 100MB
            },
            "security": {
                "encryption_key": None,
                "session_timeout": 3600,
                "max_login_attempts": 5,
                "lockout_duration": 900
            }
        }
    
    def _load_from_file(self):
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    file_config = json.load(f)
                    self._merge_config(self.config, file_config)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Error loading config file: {e}")
    
    def _load_from_environment(self):
        """Load configuration from environment variables"""
        env_mappings = {
            # App settings
            "POSTGRES_BACKUP_DIR": ("app", "backup_dir"),
            "POSTGRES_LOG_LEVEL": ("app", "log_level"),
            "POSTGRES_MAX_LOG_FILES": ("app", "max_log_files"),
            
            # Source database
            "POSTGRES_SOURCE_HOST": ("database", "source", "host"),
            "POSTGRES_SOURCE_PORT": ("database", "source", "port"),
            "POSTGRES_SOURCE_DB": ("database", "source", "database"),
            "POSTGRES_SOURCE_USER": ("database", "source", "username"),
            "POSTGRES_SOURCE_PASSWORD": ("database", "source", "password"),
            "POSTGRES_SOURCE_SSL": ("database", "source", "ssl_mode"),
            
            # Target database
            "POSTGRES_TARGET_HOST": ("database", "target", "host"),
            "POSTGRES_TARGET_PORT": ("database", "target", "port"),
            "POSTGRES_TARGET_DB": ("database", "target", "database"),
            "POSTGRES_TARGET_USER": ("database", "target", "username"),
            "POSTGRES_TARGET_PASSWORD": ("database", "target", "password"),
            "POSTGRES_TARGET_SSL": ("database", "target", "ssl_mode"),
            
            # Backup settings
            "POSTGRES_BACKUP_TYPE": ("backup", "default_type"),
            "POSTGRES_COMPRESSION": ("backup", "compression"),
            "POSTGRES_ENCRYPTION": ("backup", "encryption"),
            "POSTGRES_PARALLEL_JOBS": ("backup", "parallel_jobs"),
            "POSTGRES_RETENTION_DAYS": ("backup", "retention_days"),
            "POSTGRES_VERIFY_BACKUPS": ("backup", "verify_backups"),
            
            # Web settings
            "POSTGRES_WEB_HOST": ("web", "host"),
            "POSTGRES_WEB_PORT": ("web", "port"),
            "POSTGRES_WEB_DEBUG": ("web", "debug"),
            "POSTGRES_SECRET_KEY": ("web", "secret_key"),
            
            # Security
            "POSTGRES_ENCRYPTION_KEY": ("security", "encryption_key"),
        }
        
        for env_var, config_path in env_mappings.items():
            env_value = os.environ.get(env_var)
            if env_value is not None:
                self._set_nested_value(self.config, config_path, env_value)
    
    def _merge_config(self, base: Dict, override: Dict):
        """Recursively merge configuration dictionaries"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def _set_nested_value(self, config: Dict, path: tuple, value: str):
        """Set nested configuration value"""
        current = config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        final_key = path[-1]
        
        # Type conversion
        if final_key in ["port", "parallel_jobs", "retention_days", "max_log_files", 
                        "connection_timeout", "job_timeout", "retry_attempts", 
                        "retry_delay", "session_timeout", "max_login_attempts", 
                        "lockout_duration", "max_upload_size"]:
            try:
                current[final_key] = int(value)
            except ValueError:
                pass
        elif final_key in ["verify_backups", "verbose", "clean_before_restore", 
                          "no_owner", "no_privileges", "enabled", "debug"]:
            current[final_key] = value.lower() in ('true', 'yes', '1', 'on')
        else:
            current[final_key] = value
    
    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4, default=str)
            return True
        except IOError as e:
            print(f"Error saving configuration: {e}")
            return False
    
    def get_database_config(self, name: str = "source") -> DatabaseConfig:
        """Get database configuration"""
        db_config = self.config["database"].get(name, self.config["database"]["source"])
        return DatabaseConfig(**db_config)
    
    def get_backup_config(self) -> BackupConfig:
        """Get backup configuration"""
        return BackupConfig(**self.config["backup"])
    
    def get_backup_jobs(self) -> List[BackupJob]:
        """Get all backup jobs"""
        jobs_file = self.app_dir / "jobs.json"
        if not jobs_file.exists():
            return []
        
        try:
            with open(jobs_file, 'r') as f:
                jobs_data = json.load(f)
                return [BackupJob(**job) for job in jobs_data]
        except (json.JSONDecodeError, IOError):
            return []
    
    def save_backup_jobs(self, jobs: List[BackupJob]):
        """Save backup jobs"""
        jobs_file = self.app_dir / "jobs.json"
        try:
            with open(jobs_file, 'w') as f:
                json.dump([job.dict() for job in jobs], f, indent=4, default=str)
            return True
        except IOError:
            return False
    
    def add_backup_job(self, job: BackupJob):
        """Add a backup job"""
        jobs = self.get_backup_jobs()
        jobs.append(job)
        self.save_backup_jobs(jobs)
    
    def remove_backup_job(self, job_id: str):
        """Remove a backup job"""
        jobs = self.get_backup_jobs()
        jobs = [job for job in jobs if job.id != job_id]
        self.save_backup_jobs(jobs)
    
    def get_app_dir(self) -> Path:
        """Get application directory"""
        return self.app_dir
    
    def get_backup_dir(self) -> Path:
        """Get backup directory"""
        backup_dir = Path(self.config["app"]["backup_dir"])
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir
    
    def get_temp_dir(self) -> Path:
        """Get temporary directory"""
        temp_dir = Path(self.config["app"]["temp_dir"])
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir
    
    def get_data_dir(self) -> Path:
        """Get data directory"""
        data_dir = Path(self.config["app"]["data_dir"])
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir
    
    def get_web_config(self) -> Dict[str, Any]:
        """Get web configuration"""
        return self.config["web"]
    
    def get_scheduler_config(self) -> Dict[str, Any]:
        """Get scheduler configuration"""
        return self.config["scheduler"]
    
    def get_security_config(self) -> Dict[str, Any]:
        """Get security configuration"""
        return self.config["security"]
    
    def update_config(self, path: str, value: Any):
        """Update configuration value"""
        keys = path.split('.')
        current = self.config
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
        self.save_config()
    
    def get_config_value(self, path: str, default: Any = None) -> Any:
        """Get configuration value"""
        keys = path.split('.')
        current = self.config
        
        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default
    
    def get_full_config(self) -> Dict[str, Any]:
        """Get full configuration"""
        return self.config.copy()