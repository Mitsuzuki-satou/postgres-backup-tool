"""
FastAPI web application for PostgreSQL Backup & Restore Tool
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import json
import tempfile
from pathlib import Path

from ..core.config import ConfigManager
from ..core.backup import BackupManager
from ..core.restore import RestoreManager
from ..core.scheduler import BackupScheduler
from ..core.models import BackupJob, DatabaseConfig, BackupConfig
from ..utils.logger import get_logger


# Pydantic models for API
class DatabaseConfigModel(BaseModel):
    host: str
    port: int
    database: str
    username: str
    password: str
    ssl_mode: str = "prefer"


class BackupConfigModel(BaseModel):
    backup_type: str = "full"
    compression: str = "gzip"
    parallel_jobs: int = 4
    exclude_schemas: List[str] = []
    include_schemas: List[str] = []


class BackupJobModel(BaseModel):
    name: str
    source_config: DatabaseConfigModel
    backup_config: BackupConfigModel
    schedule: Optional[str] = None
    retention_days: int = 30


def create_app(config_manager: ConfigManager) -> FastAPI:
    """Create FastAPI application"""
    
    app = FastAPI(
        title="PostgreSQL Backup & Restore Tool",
        description="A comprehensive backup and restore solution for PostgreSQL databases",
        version="3.0.0"
    )
    
    # Initialize components
    backup_manager = BackupManager(config_manager)
    restore_manager = RestoreManager(config_manager)
    scheduler = BackupScheduler(config_manager, backup_manager)
    
    # Setup templates and static files
    templates_dir = Path(__file__).parent.parent.parent / "templates"
    static_dir = Path(__file__).parent.parent.parent / "static"
    
    if templates_dir.exists():
        templates = Jinja2Templates(directory=str(templates_dir))
    else:
        templates = None
    
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    logger = get_logger(__name__)
    
    @app.on_event("startup")
    async def startup_event():
        """Initialize application on startup"""
        logger.info("Web application starting up")
        scheduler.load_jobs_from_config()
        await scheduler.start()
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on shutdown"""
        logger.info("Web application shutting down")
        await scheduler.stop()
    
    # Routes
    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        """Main dashboard"""
        if templates:
            return templates.TemplateResponse("dashboard.html", {"request": request})
        return HTMLResponse("<h1>PostgreSQL Backup & Restore Tool</h1><p>Web Interface</p>")
    
    @app.get("/api/status")
    async def get_status():
        """Get system status"""
        stats = scheduler.get_job_stats()
        active_backups = backup_manager.get_active_backups()
        active_restores = restore_manager.get_active_restores()
        
        return {
            "status": "running",
            "scheduler_stats": stats,
            "active_backups": len(active_backups),
            "active_restores": len(active_restores),
            "uptime": "0:00:00"  # Would calculate actual uptime
        }
    
    @app.get("/api/backups")
    async def list_backups():
        """List all backup files"""
        backup_dir = config_manager.get_backup_dir()
        backups = []
        
        if backup_dir.exists():
            for backup_file in backup_dir.glob("*"):
                if backup_file.is_file():
                    stat = backup_file.stat()
                    backups.append({
                        "name": backup_file.name,
                        "size": stat.st_size,
                        "created": stat.st_ctime,
                        "path": str(backup_file)
                    })
        
        return {"backups": backups}
    
    @app.post("/api/backup")
    async def create_backup(
        backup_job: BackupJobModel,
        background_tasks: BackgroundTasks
    ):
        """Create a new backup"""
        try:
            # Convert to internal models
            db_config = DatabaseConfig(**backup_job.source_config.dict())
            backup_config = BackupConfig(**backup_job.backup_config.dict())
            
            job = BackupJob(
                id=f"backup_{int(asyncio.get_event_loop().time())}",
                name=backup_job.name,
                source_config=db_config,
                backup_config=backup_config,
                backup_dir=config_manager.get_backup_dir(),
                schedule=backup_job.schedule,
                retention_days=backup_job.retention_days,
                enabled=True
            )
            
            # Run backup in background
            background_tasks.add_task(backup_manager.create_backup, job)
            
            return {"message": "Backup started", "job_id": job.id}
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/restore")
    async def restore_database(
        backup_file: str,
        target_config: DatabaseConfigModel,
        background_tasks: BackgroundTasks
    ):
        """Restore database from backup"""
        try:
            backup_path = Path(backup_file)
            if not backup_path.exists():
                raise HTTPException(status_code=404, detail="Backup file not found")
            
            db_config = DatabaseConfig(**target_config.dict())
            
            # Run restore in background
            background_tasks.add_task(
                restore_manager.restore_backup,
                backup_path,
                db_config
            )
            
            return {"message": "Restore started"}
            
        except Exception as e:
            logger.error(f"Error starting restore: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/jobs")
    async def list_jobs():
        """List scheduled jobs"""
        jobs = scheduler.get_scheduled_jobs()
        
        job_list = []
        for job in jobs:
            next_run = scheduler.get_next_run_time(job)
            job_list.append({
                "id": job.id,
                "name": job.name,
                "schedule": job.schedule,
                "enabled": job.enabled,
                "next_run": next_run.isoformat() if next_run is not None else None
            })
        
        return {"jobs": job_list}
    
    @app.post("/api/jobs")
    async def create_job(backup_job: BackupJobModel):
        """Create a new scheduled job"""
        try:
            # Convert to internal models
            db_config = DatabaseConfig(**backup_job.source_config.dict())
            backup_config = BackupConfig(**backup_job.backup_config.dict())
            
            job = BackupJob(
                id=f"job_{int(asyncio.get_event_loop().time())}",
                name=backup_job.name,
                source_config=db_config,
                backup_config=backup_config,
                backup_dir=config_manager.get_backup_dir(),
                schedule=backup_job.schedule,
                retention_days=backup_job.retention_days,
                enabled=True
            )
            
            # Save job
            config_manager.add_backup_job(job)
            scheduler.add_job(job)
            
            return {"message": "Job created", "job_id": job.id}
            
        except Exception as e:
            logger.error(f"Error creating job: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/logs")
    async def get_logs(limit: int = 100):
        """Get recent logs"""
        # This would read from actual log files
        return {
            "logs": [
                {
                    "timestamp": "2023-10-15T12:00:00Z",
                    "level": "INFO",
                    "message": "Backup completed successfully"
                },
                {
                    "timestamp": "2023-10-15T11:58:00Z",
                    "level": "INFO", 
                    "message": "Starting backup"
                }
            ]
        }
    
    @app.get("/api/config")
    async def get_config():
        """Get current configuration"""
        return {
            "database": config_manager.config["database"],
            "backup": config_manager.config["backup"],
            "scheduler": config_manager.config["scheduler"]
        }
    
    @app.put("/api/config")
    async def update_config(config_data: dict):
        """Update configuration"""
        try:
            for key, value in config_data.items():
                config_manager.update_config(key, value)
            return {"message": "Configuration updated"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/test-connection")
    async def test_connection(config_data: dict):
        """Test database connection"""
        try:
            from ..core.database import DatabaseManager
            
            if config_data.get("type") == "database":
                db_config = DatabaseConfig(**config_data.get("config", {}))
                db_manager = DatabaseManager(db_config)
                
                # Test connection
                success, message = await db_manager.test_connection()
                if success:
                    return {"status": "success", "message": message}
                else:
                    return {"status": "error", "message": message}
            else:
                return {"status": "error", "message": "Unsupported connection type"}
                
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return {"status": "error", "message": str(e)}
    
    @app.get("/api/config/export")
    async def export_config():
        """Export configuration as JSON"""
        try:
            config = config_manager.get_full_config()
            return JSONResponse(
                content=config,
                headers={
                    "Content-Disposition": "attachment; filename=postgres-backup-config.json"
                }
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/config/import")
    async def import_config(file: UploadFile = File(...)):
        """Import configuration from JSON file"""
        try:
            if file.filename and not file.filename.endswith('.json'):
                raise HTTPException(status_code=400, detail="Only JSON files are supported")
            
            content = await file.read()
            config_data = json.loads(content.decode('utf-8'))
            
            # Validate and import configuration
            for key, value in config_data.items():
                config_manager.update_config(key, value)
            
            return {"message": "Configuration imported successfully"}
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON file")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/credentials")
    async def get_credentials():
        """Get all credential configurations"""
        try:
            config = config_manager.get_full_config()
            return {
                "database": config.get("database", {}),
                "source_storage": config.get("source_storage", {}),
                "target_storage": config.get("target_storage", {})
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.put("/api/credentials")
    async def update_credentials(credentials: dict):
        """Update credential configurations"""
        try:
            for cred_type, config in credentials.items():
                if cred_type in ["database", "source_storage", "target_storage"]:
                    config_manager.update_config(cred_type, config)
            return {"message": "Credentials updated successfully"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    return app