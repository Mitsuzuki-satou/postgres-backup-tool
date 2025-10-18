"""
Data models for PostgreSQL Backup & Restore Tool
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator


class BackupType(str, Enum):
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"


class CompressionType(str, Enum):
    NONE = "none"
    GZIP = "gzip"
    BZIP2 = "bzip2"
    LZ4 = "lz4"


class EncryptionType(str, Enum):
    NONE = "none"
    AES256 = "aes256"


class BackupStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DatabaseConfig(BaseModel):
    """Database connection configuration"""
    host: str = Field(..., description="Database host")
    port: int = Field(5432, description="Database port")
    database: str = Field(..., description="Database name")
    username: str = Field(..., description="Database username")
    password: str = Field(..., description="Database password")
    ssl_mode: str = Field("prefer", description="SSL mode")
    connection_timeout: int = Field(30, description="Connection timeout in seconds")
    
    @validator('port')
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError('Port must be between 1 and 65535')
        return v


class BackupConfig(BaseModel):
    """Backup configuration"""
    backup_type: BackupType = Field(BackupType.FULL, description="Type of backup")
    compression: CompressionType = Field(CompressionType.GZIP, description="Compression type")
    encryption: EncryptionType = Field(EncryptionType.NONE, description="Encryption type")
    encryption_key: Optional[str] = Field(None, description="Encryption key")
    parallel_jobs: int = Field(4, description="Number of parallel jobs")
    exclude_schemas: List[str] = Field(default_factory=list, description="Schemas to exclude")
    include_schemas: List[str] = Field(default_factory=list, description="Schemas to include")
    exclude_tables: List[str] = Field(default_factory=list, description="Tables to exclude")
    include_tables: List[str] = Field(default_factory=list, description="Tables to include")
    verbose: bool = Field(True, description="Verbose output")
    clean_before_restore: bool = Field(True, description="Clean objects before restore")
    no_owner: bool = Field(True, description="Skip owner commands")
    no_privileges: bool = Field(True, description="Skip privilege commands")
    
    @validator('parallel_jobs')
    def validate_parallel_jobs(cls, v):
        if v < 1:
            raise ValueError('Parallel jobs must be at least 1')
        return v


class BackupJob(BaseModel):
    """Backup job definition"""
    id: str = Field(..., description="Unique job identifier")
    name: str = Field(..., description="Job name")
    source_config: DatabaseConfig = Field(..., description="Source database configuration")
    backup_config: BackupConfig = Field(..., description="Backup configuration")
    backup_dir: Path = Field(..., description="Backup directory")
    schedule: Optional[str] = Field(None, description="Cron schedule expression")
    retention_days: int = Field(30, description="Retention period in days")
    enabled: bool = Field(True, description="Job enabled status")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Path: lambda v: str(v)
        }


class BackupResult(BaseModel):
    """Backup operation result"""
    job_id: str = Field(..., description="Job identifier")
    status: BackupStatus = Field(..., description="Backup status")
    backup_file: Optional[Path] = Field(None, description="Backup file path")
    start_time: datetime = Field(..., description="Start time")
    end_time: Optional[datetime] = Field(None, description="End time")
    size_bytes: int = Field(0, description="Backup size in bytes")
    size_compressed: int = Field(0, description="Compressed size in bytes")
    tables_count: int = Field(0, description="Number of tables")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    checksum: Optional[str] = Field(None, description="Backup file checksum")
    metadata: Dict[str, Union[str, int, bool]] = Field(default_factory=dict, description="Additional metadata")
    
    @property
    def duration(self) -> Optional[float]:
        """Calculate backup duration in seconds"""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def compression_ratio(self) -> Optional[float]:
        """Calculate compression ratio"""
        if self.size_bytes > 0 and self.size_compressed > 0:
            return self.size_compressed / self.size_bytes
        return None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Path: lambda v: str(v)
        }


class RestoreResult(BaseModel):
    """Restore operation result"""
    backup_file: Path = Field(..., description="Backup file path")
    target_config: DatabaseConfig = Field(..., description="Target database configuration")
    status: BackupStatus = Field(..., description="Restore status")
    start_time: datetime = Field(..., description="Start time")
    end_time: Optional[datetime] = Field(None, description="End time")
    tables_restored: int = Field(0, description="Number of tables restored")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    verification_passed: bool = Field(False, description="Verification status")
    
    @property
    def duration(self) -> Optional[float]:
        """Calculate restore duration in seconds"""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Path: lambda v: str(v)
        }


class SystemStatus(BaseModel):
    """System status information"""
    total_backups: int = Field(0, description="Total number of backups")
    successful_backups: int = Field(0, description="Successful backups")
    failed_backups: int = Field(0, description="Failed backups")
    total_size: int = Field(0, description="Total backup size in bytes")
    last_backup: Optional[datetime] = Field(None, description="Last backup timestamp")
    active_jobs: int = Field(0, description="Number of active jobs")
    disk_usage: Dict[str, int] = Field(default_factory=dict, description="Disk usage by directory")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }