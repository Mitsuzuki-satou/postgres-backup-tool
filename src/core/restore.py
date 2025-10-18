"""
Restore operations for PostgreSQL Backup & Restore Tool
"""

import asyncio
import gzip
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
    RestoreResult, BackupStatus, DatabaseConfig, BackupConfig
)
from .database import DatabaseManager
from ..utils.logger import get_logger, OperationLogger
from ..utils.progress import ProgressTracker

logger = get_logger(__name__)


class RestoreManager:
    """Restore operations manager"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.active_restores: Dict[str, RestoreResult] = {}
        self.progress_callbacks: Dict[str, Callable] = {}
    
    async def restore_backup(
        self,
        backup_file: Path,
        target_config: DatabaseConfig,
        backup_config: Optional[BackupConfig] = None,
        progress_callback: Optional[Callable] = None
    ) -> RestoreResult:
        """Restore database from backup file"""
        
        result = RestoreResult(
            backup_file=backup_file,
            target_config=target_config,
            status=BackupStatus.RUNNING,
            start_time=datetime.now()
        )
        
        restore_id = f"restore_{int(time.time())}"
        self.active_restores[restore_id] = result
        if progress_callback:
            self.progress_callbacks[restore_id] = progress_callback
        
        try:
            with OperationLogger(logger, f"restore from {backup_file}"):
                
                # Verify backup file
                if not await self._verify_backup_file(backup_file):
                    raise RuntimeError(f"Backup file verification failed: {backup_file}")
                
                # Get backup info
                backup_info = await self._get_backup_info(backup_file)
                
                # Check if target database exists
                db_manager = DatabaseManager(target_config)
                
                if await db_manager.database_exists(target_config.database):
                    # Handle existing database
                    if not await self._handle_existing_database(db_manager, target_config):
                        raise RuntimeError("Restore cancelled by user")
                
                # Create target database
                if not await db_manager.create_database(target_config.database):
                    raise RuntimeError(f"Failed to create database: {target_config.database}")
                
                # Perform restore based on backup format
                if backup_info.get("format") == "custom":
                    await self._restore_custom_format(backup_file, target_config, restore_id, result)
                elif backup_info.get("format") == "directory":
                    await self._restore_directory_format(backup_file, target_config, restore_id, result)
                elif backup_info.get("format") == "sql":
                    await self._restore_sql_format(backup_file, target_config, restore_id, result)
                else:
                    raise RuntimeError(f"Unsupported backup format: {backup_info.get('format')}")
                
                # Verify restoration
                verification_passed = await self._verify_restoration(db_manager, backup_info)
                
                # Update result
                result.status = BackupStatus.COMPLETED
                result.end_time = datetime.now()
                result.verification_passed = verification_passed
                result.tables_restored = backup_info.get("tables_count", 0)
                
                logger.info(f"Restore completed: {target_config.database}")
                
        except Exception as e:
            result.status = BackupStatus.FAILED
            result.error_message = str(e)
            result.end_time = datetime.now()
            logger.error(f"Restore failed: {e}")
        
        finally:
            # Cleanup
            if restore_id in self.active_restores:
                del self.active_restores[restore_id]
            if restore_id in self.progress_callbacks:
                del self.progress_callbacks[restore_id]
        
        return result
    
    async def _verify_backup_file(self, backup_file: Path) -> bool:
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
    
    async def _get_backup_info(self, backup_file: Path) -> Dict[str, Any]:
        """Get backup file information"""
        try:
            stat = backup_file.stat()
            
            info = {
                "file_path": str(backup_file),
                "size_bytes": stat.st_size,
                "created_time": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat()
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
            return {"format": "unknown"}
    
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
                
                # Look for toc.dat file to get table count
                table_count = 0
                for member in members:
                    if member.name.endswith('toc.dat'):
                        try:
                            content = tar.extractfile(member).read().decode('utf-8', errors='ignore')
                            table_count = content.count("TABLE")
                            break
                        except:
                            pass
                
                return {
                    "format": "directory",
                    "files_count": len(members),
                    "tables_count": table_count,
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
    
    async def _handle_existing_database(
        self, 
        db_manager: DatabaseManager, 
        target_config: DatabaseConfig
    ) -> bool:
        """Handle existing target database"""
        
        # For now, we'll drop and recreate
        # In a real implementation, you might want to ask the user
        logger.warning(f"Database {target_config.database} already exists, dropping it")
        return await db_manager.drop_database(target_config.database)
    
    async def _restore_custom_format(
        self, 
        backup_file: Path, 
        target_config: DatabaseConfig, 
        restore_id: str,
        result: RestoreResult
    ):
        """Restore from custom format backup"""
        
        cmd = [
            "pg_restore",
            f"-h{target_config.host}",
            f"-p{target_config.port}",
            f"-U{target_config.username}",
            f"-d{target_config.database}",
            "--verbose",
            "--clean",
            "--no-owner",
            "--no-privileges",
            str(backup_file)
        ]
        
        env = {"PGPASSWORD": target_config.password}
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        await self._monitor_restore_process(process, restore_id, "Restoring custom format backup")
        
        if process.returncode != 0:
            stderr = await process.stderr.read()
            raise RuntimeError(f"pg_restore failed: {stderr.decode()}")
    
    async def _restore_directory_format(
        self, 
        backup_file: Path, 
        target_config: DatabaseConfig, 
        restore_id: str,
        result: RestoreResult
    ):
        """Restore from directory format backup"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Extract tar archive
            with tarfile.open(backup_file, 'r:*') as tar:
                tar.extractall(temp_dir)
            
            # Find the extracted directory
            extracted_dirs = [d for d in Path(temp_dir).iterdir() if d.is_dir()]
            if not extracted_dirs:
                raise RuntimeError("No backup directory found in archive")
            
            backup_dir = extracted_dirs[0]
            
            cmd = [
                "pg_restore",
                f"-h{target_config.host}",
                f"-p{target_config.port}",
                f"-U{target_config.username}",
                f"-d{target_config.database}",
                "--verbose",
                "--clean",
                "--no-owner",
                "--no-privileges",
                "--jobs=4",
                str(backup_dir)
            ]
            
            env = {"PGPASSWORD": target_config.password}
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await self._monitor_restore_process(process, restore_id, "Restoring directory format backup")
            
            if process.returncode != 0:
                stderr = await process.stderr.read()
                raise RuntimeError(f"pg_restore failed: {stderr.decode()}")
    
    async def _restore_sql_format(
        self, 
        backup_file: Path, 
        target_config: DatabaseConfig, 
        restore_id: str,
        result: RestoreResult
    ):
        """Restore from SQL format backup"""
        
        cmd = [
            "psql",
            f"-h{target_config.host}",
            f"-p{target_config.port}",
            f"-U{target_config.username}",
            f"-d{target_config.database}",
            "--verbose"
        ]
        
        env = {"PGPASSWORD": target_config.password}
        
        # Prepare input file
        if backup_file.suffix == '.sql.gz':
            # For compressed SQL, we need to decompress first
            process = await asyncio.create_subprocess_exec(
                "gunzip", "-c", str(backup_file),
                stdout=asyncio.subprocess.PIPE
            )
            gunzip_stdout, _ = await process.communicate()
            
            if process.returncode != 0:
                raise RuntimeError("Failed to decompress SQL file")
            
            # Pipe to psql
            psql_process = await asyncio.create_subprocess_exec(
                *cmd,
                env=env,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await psql_process.communicate(input=gunzip_stdout)
            
        else:
            # For regular SQL files
            with open(backup_file, 'rb') as f:
                psql_process = await asyncio.create_subprocess_exec(
                    *cmd,
                    env=env,
                    stdin=f,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await psql_process.communicate()
        
        await self._monitor_restore_process(psql_process, restore_id, "Restoring SQL backup")
        
        if psql_process.returncode != 0:
            raise RuntimeError(f"psql failed: {stderr.decode()}")
    
    async def _monitor_restore_process(
        self, 
        process: asyncio.subprocess.Process, 
        restore_id: str, 
        message: str
    ):
        """Monitor restore process progress"""
        
        start_time = time.time()
        
        while process.returncode is None:
            await asyncio.sleep(1)
            
            elapsed = int(time.time() - start_time)
            
            # Update progress callback if available
            if restore_id in self.progress_callbacks:
                try:
                    # Simple time-based progress estimation
                    progress = min(95, (elapsed * 100) // 600)  # Assume 10 minutes max
                    self.progress_callbacks[restore_id](progress, f"{message} ({elapsed}s)")
                except Exception:
                    pass
        
        # Final update
        if restore_id in self.progress_callbacks:
            try:
                self.progress_callbacks[restore_id](100, f"{message} completed")
            except Exception:
                pass
    
    async def _verify_restoration(
        self, 
        db_manager: DatabaseManager, 
        backup_info: Dict[str, Any]
    ) -> bool:
        """Verify database restoration"""
        try:
            # Get database info
            db_info = await db_manager.get_database_info()
            
            # Basic checks
            if not db_info:
                return False
            
            # Check table count if available
            backup_tables = backup_info.get("tables_count", 0)
            if backup_tables > 0:
                current_tables = db_info.get("table_count", 0)
                if current_tables < backup_tables * 0.9:  # Allow 10% tolerance
                    logger.warning(f"Table count mismatch: expected {backup_tables}, got {current_tables}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error verifying restoration: {e}")
            return False
    
    def get_active_restores(self) -> List[RestoreResult]:
        """Get list of active restores"""
        return list(self.active_restores.values())
    
    def cancel_restore(self, restore_id: str) -> bool:
        """Cancel active restore"""
        if restore_id in self.active_restores:
            result = self.active_restores[restore_id]
            result.status = BackupStatus.CANCELLED
            result.end_time = datetime.now()
            del self.active_restores[restore_id]
            if restore_id in self.progress_callbacks:
                del self.progress_callbacks[restore_id]
            return True
        return False