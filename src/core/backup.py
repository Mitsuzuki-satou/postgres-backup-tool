"""
Backup operations for PostgreSQL Backup & Restore Tool
"""

import asyncio
import gzip
import hashlib
import shutil
import subprocess
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
import threading
import time

from .models import (
    BackupJob, BackupResult, BackupStatus, BackupType, 
    CompressionType, EncryptionType, DatabaseConfig, BackupConfig
)
from .database import DatabaseManager
from ..utils.logger import get_logger, OperationLogger
from ..utils.progress import ProgressTracker

logger = get_logger(__name__)


class BackupManager:
    """Backup operations manager"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.active_backups: Dict[str, BackupResult] = {}
        self.progress_callbacks: Dict[str, Callable] = {}
    
    async def create_backup(
        self, 
        job: BackupJob,
        progress_callback: Optional[Callable] = None
    ) -> BackupResult:
        """Create backup from job configuration"""
        
        result = BackupResult(
            job_id=job.id,
            status=BackupStatus.RUNNING,
            start_time=datetime.now()
        )
        
        self.active_backups[job.id] = result
        if progress_callback:
            self.progress_callbacks[job.id] = progress_callback
        
        try:
            with OperationLogger(logger, f"backup job {job.id}"):
                
                # Get database info
                db_manager = DatabaseManager(job.source_config)
                db_info = await db_manager.get_database_info()
                
                # Create backup file path
                backup_file = self._get_backup_file_path(job)
                backup_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Update result with initial info
                result.tables_count = db_info.get("table_count", 0)
                
                # Perform backup based on configuration
                if job.backup_config.backup_type == BackupType.FULL:
                    backup_file = await self._create_full_backup(job, backup_file, result)
                else:
                    raise ValueError(f"Backup type {job.backup_config.backup_type} not yet implemented")
                
                # Calculate checksum
                checksum = await self._calculate_checksum(backup_file)
                
                # Update result
                result.status = BackupStatus.COMPLETED
                result.backup_file = backup_file
                result.end_time = datetime.now()
                result.size_bytes = backup_file.stat().st_size
                result.checksum = checksum
                result.metadata = {
                    "database_info": db_info,
                    "backup_config": job.backup_config.dict(),
                    "compression": job.backup_config.compression.value,
                    "encryption": job.backup_config.encryption.value
                }
                
                logger.info(f"Backup completed: {backup_file} ({result.size_bytes} bytes)")
                
        except Exception as e:
            result.status = BackupStatus.FAILED
            result.error_message = str(e)
            result.end_time = datetime.now()
            logger.error(f"Backup failed: {e}")
        
        finally:
            # Cleanup
            if job.id in self.active_backups:
                del self.active_backups[job.id]
            if job.id in self.progress_callbacks:
                del self.progress_callbacks[job.id]
        
        return result
    
    async def _create_full_backup(
        self, 
        job: BackupJob, 
        backup_file: Path, 
        result: BackupResult
    ) -> Path:
        """Create full database backup"""
        
        config = job.backup_config
        db_config = job.source_config
        
        if config.parallel_jobs > 1 and config.compression != CompressionType.NONE:
            # Use directory format for parallel backup
            return await self._create_parallel_backup(job, backup_file, result)
        else:
            # Use custom format for single-threaded backup
            return await self._create_custom_backup(job, backup_file, result)
    
    async def _create_parallel_backup(
        self, 
        job: BackupJob, 
        backup_file: Path, 
        result: BackupResult
    ) -> Path:
        """Create parallel backup using directory format"""
        
        config = job.backup_config
        db_config = job.source_config
        
        # Create temporary directory for backup
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_backup_dir = Path(temp_dir) / f"{backup_file.stem}_dir"
            
            # Build pg_dump command
            cmd = [
                "pg_dump",
                f"-h{db_config.host}",
                f"-p{db_config.port}",
                f"-U{db_config.username}",
                f"-d{db_config.database}",
                "--verbose",
                "--format=directory",
                f"--jobs={config.parallel_jobs}",
                "--file", str(temp_backup_dir)
            ]
            
            if config.clean_before_restore:
                cmd.append("--clean")
            if config.no_owner:
                cmd.append("--no-owner")
            if config.no_privileges:
                cmd.append("--no-privileges")
            
            # Add schema filters
            for schema in config.exclude_schemas:
                cmd.extend(["--exclude-schema", schema])
            for schema in config.include_schemas:
                cmd.extend(["--schema", schema])
            
            # Add table filters
            for table in config.exclude_tables:
                cmd.extend(["--exclude-table", table])
            for table in config.include_tables:
                cmd.extend(["--table", table])
            
            # Set environment
            env = {"PGPASSWORD": db_config.password}
            
            # Run backup
            process = await asyncio.create_subprocess_exec(
                *cmd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Monitor progress
            await self._monitor_backup_process(process, job.id, "Creating parallel backup")
            
            if process.returncode != 0:
                stderr = await process.stderr.read()
                raise RuntimeError(f"pg_dump failed: {stderr.decode()}")
            
            # Compress directory
            if config.compression == CompressionType.GZIP:
                final_file = backup_file.with_suffix(".tar.gz")
                with tarfile.open(final_file, "w:gz") as tar:
                    tar.add(temp_backup_dir, arcname=temp_backup_dir.name)
            elif config.compression == CompressionType.BZIP2:
                final_file = backup_file.with_suffix(".tar.bz2")
                with tarfile.open(final_file, "w:bz2") as tar:
                    tar.add(temp_backup_dir, arcname=temp_backup_dir.name)
            else:
                # No compression - just copy directory
                final_file = backup_file.with_suffix(".tar")
                with tarfile.open(final_file, "w") as tar:
                    tar.add(temp_backup_dir, arcname=temp_backup_dir.name)
            
            return final_file
    
    async def _create_custom_backup(
        self, 
        job: BackupJob, 
        backup_file: Path, 
        result: BackupResult
    ) -> Path:
        """Create custom format backup"""
        
        config = job.backup_config
        db_config = job.source_config
        
        # Build pg_dump command
        cmd = [
            "pg_dump",
            f"-h{db_config.host}",
            f"-p{db_config.port}",
            f"-U{db_config.username}",
            f"-d{db_config.database}",
            "--verbose",
            "--format=custom"
        ]
        
        if config.clean_before_restore:
            cmd.append("--clean")
        if config.no_owner:
            cmd.append("--no-owner")
        if config.no_privileges:
            cmd.append("--no-privileges")
        
        # Add schema and table filters
        for schema in config.exclude_schemas:
            cmd.extend(["--exclude-schema", schema])
        for schema in config.include_schemas:
            cmd.extend(["--schema", schema])
        for table in config.exclude_tables:
            cmd.extend(["--exclude-table", table])
        for table in config.include_tables:
            cmd.extend(["--table", table])
        
        # Determine output file
        if config.compression == CompressionType.GZIP:
            final_file = backup_file.with_suffix(".dump.gz")
        elif config.compression == CompressionType.BZIP2:
            final_file = backup_file.with_suffix(".dump.bz2")
        else:
            final_file = backup_file.with_suffix(".dump")
        
        cmd.extend(["--file", str(final_file)])
        
        # Set environment
        env = {"PGPASSWORD": db_config.password}
        
        # Run backup
        process = await asyncio.create_subprocess_exec(
            *cmd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Monitor progress
        await self._monitor_backup_process(process, job.id, "Creating custom backup")
        
        if process.returncode != 0:
            stderr = await process.stderr.read()
            raise RuntimeError(f"pg_dump failed: {stderr.decode()}")
        
        return final_file
    
    async def _monitor_backup_process(
        self, 
        process: asyncio.subprocess.Process, 
        job_id: str, 
        message: str
    ):
        """Monitor backup process progress"""
        
        start_time = time.time()
        
        while process.returncode is None:
            await asyncio.sleep(1)
            
            elapsed = int(time.time() - start_time)
            
            # Update progress callback if available
            if job_id in self.progress_callbacks:
                try:
                    # Simple time-based progress estimation
                    progress = min(95, (elapsed * 100) // 300)  # Assume 5 minutes max
                    self.progress_callbacks[job_id](progress, f"{message} ({elapsed}s)")
                except Exception:
                    pass
        
        # Final update
        if job_id in self.progress_callbacks:
            try:
                self.progress_callbacks[job_id](100, f"{message} completed")
            except Exception:
                pass
    
    async def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        hash_sha256 = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        
        return hash_sha256.hexdigest()
    
    def _get_backup_file_path(self, job: BackupJob) -> Path:
        """Generate backup file path"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{job.name}_{timestamp}"
        return job.backup_dir / filename
    
    async def verify_backup(self, backup_file: Path) -> bool:
        """Verify backup file integrity"""
        try:
            # Check if file exists and is readable
            if not backup_file.exists():
                return False
            
            # For custom format backups, use pg_restore --list
            if backup_file.suffix in ['.dump', '.dump.gz', '.dump.bz2']:
                cmd = ["pg_restore", "--list", str(backup_file)]
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
                await process.wait()
                return process.returncode == 0
            
            # For tar archives, check if they can be opened
            elif backup_file.suffix in ['.tar', '.tar.gz', '.tar.bz2']:
                try:
                    with tarfile.open(backup_file, 'r:*') as tar:
                        tar.getmembers()
                    return True
                except:
                    return False
            
            # For SQL files, check if they're readable
            elif backup_file.suffix in ['.sql', '.sql.gz']:
                try:
                    if backup_file.suffix == '.sql.gz':
                        with gzip.open(backup_file, 'rt') as f:
                            f.read(1024)  # Read first 1KB
                    else:
                        with open(backup_file, 'r') as f:
                            f.read(1024)
                    return True
                except:
                    return False
            
            return False
            
        except Exception as e:
            logger.error(f"Error verifying backup {backup_file}: {e}")
            return False
    
    async def get_backup_info(self, backup_file: Path) -> Dict[str, Any]:
        """Get backup file information"""
        try:
            stat = backup_file.stat()
            
            info = {
                "file_path": str(backup_file),
                "size_bytes": stat.st_size,
                "size_pretty": self._format_size(stat.st_size),
                "created_time": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "checksum": await self._calculate_checksum(backup_file)
            }
            
            # Try to extract additional info based on file type
            if backup_file.suffix in ['.dump', '.dump.gz', '.dump.bz2']:
                info.update(await self._get_custom_backup_info(backup_file))
            elif backup_file.suffix in ['.tar', '.tar.gz', '.tar.bz2']:
                info.update(await self._get_tar_backup_info(backup_file))
            elif backup_file.suffix in ['.sql', '.sql.gz']:
                info.update(await self._get_sql_backup_info(backup_file))
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting backup info {backup_file}: {e}")
            return {}
    
    async def _get_custom_backup_info(self, backup_file: Path) -> Dict[str, Any]:
        """Get custom format backup info"""
        try:
            cmd = ["pg_restore", "--list", str(backup_file)]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL
            )
            stdout, _ = await process.communicate()
            
            if process.returncode == 0:
                content = stdout.decode()
                return {
                    "format": "custom",
                    "tables_count": content.count("TABLE"),
                    "functions_count": content.count("FUNCTION"),
                    "triggers_count": content.count("TRIGGER")
                }
        except:
            pass
        
        return {"format": "custom"}
    
    async def _get_tar_backup_info(self, backup_file: Path) -> Dict[str, Any]:
        """Get tar backup info"""
        try:
            with tarfile.open(backup_file, 'r:*') as tar:
                members = tar.getmembers()
                return {
                    "format": "directory",
                    "files_count": len(members),
                    "uncompressed_size": sum(m.size for m in members)
                }
        except:
            pass
        
        return {"format": "directory"}
    
    async def _get_sql_backup_info(self, backup_file: Path) -> Dict[str, Any]:
        """Get SQL backup info"""
        try:
            if backup_file.suffix == '.sql.gz':
                with gzip.open(backup_file, 'rt') as f:
                    content = f.read(10240)  # Read first 10KB
            else:
                with open(backup_file, 'r') as f:
                    content = f.read(10240)
            
            return {
                "format": "sql",
                "tables_count": content.count("CREATE TABLE"),
                "indexes_count": content.count("CREATE INDEX"),
                "triggers_count": content.count("CREATE TRIGGER")
            }
        except:
            pass
        
        return {"format": "sql"}
    
    def _format_size(self, size_bytes: int) -> str:
        """Format size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    def get_active_backups(self) -> List[BackupResult]:
        """Get list of active backups"""
        return list(self.active_backups.values())
    
    def cancel_backup(self, job_id: str) -> bool:
        """Cancel active backup"""
        if job_id in self.active_backups:
            result = self.active_backups[job_id]
            result.status = BackupStatus.CANCELLED
            result.end_time = datetime.now()
            del self.active_backups[job_id]
            if job_id in self.progress_callbacks:
                del self.progress_callbacks[job_id]
            return True
        return False