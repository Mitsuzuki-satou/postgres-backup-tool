"""
Backup scheduler for PostgreSQL Backup & Restore Tool
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Callable
from croniter import croniter

from .models import BackupJob, BackupResult, BackupStatus
from .backup import BackupManager
from .config import ConfigManager
from ..utils.logger import get_logger

logger = get_logger(__name__)


class BackupScheduler:
    """Backup job scheduler"""
    
    def __init__(self, config_manager: ConfigManager, backup_manager: BackupManager):
        self.config_manager = config_manager
        self.backup_manager = backup_manager
        self.running = False
        self.scheduled_jobs: Dict[str, BackupJob] = {}
        self.job_history: List[BackupResult] = []
        self.scheduler_task: Optional[asyncio.Task] = None
        self.max_history = 1000
        
    def add_job(self, job: BackupJob):
        """Add a backup job to the schedule"""
        if job.schedule and job.enabled:
            self.scheduled_jobs[job.id] = job
            logger.info(f"Added scheduled job: {job.name} ({job.schedule})")
        else:
            logger.warning(f"Job {job.name} not scheduled: no schedule or disabled")
    
    def remove_job(self, job_id: str):
        """Remove a backup job from the schedule"""
        if job_id in self.scheduled_jobs:
            del self.scheduled_jobs[job_id]
            logger.info(f"Removed scheduled job: {job_id}")
    
    def update_job(self, job: BackupJob):
        """Update a backup job in the schedule"""
        if job.schedule and job.enabled:
            self.scheduled_jobs[job.id] = job
            logger.info(f"Updated scheduled job: {job.name}")
        else:
            self.remove_job(job.id)
    
    def get_scheduled_jobs(self) -> List[BackupJob]:
        """Get all scheduled jobs"""
        return list(self.scheduled_jobs.values())
    
    def get_job_history(self, limit: int = 100) -> List[BackupResult]:
        """Get job execution history"""
        return self.job_history[-limit:]
    
    async def start(self):
        """Start the scheduler"""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Backup scheduler started")
    
    async def stop(self):
        """Stop the scheduler"""
        if not self.running:
            return
        
        self.running = False
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Backup scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop"""
        logger.info("Scheduler loop started")
        
        while self.running:
            try:
                await self._check_and_run_jobs()
                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)
        
        logger.info("Scheduler loop ended")
    
    async def _check_and_run_jobs(self):
        """Check for jobs that need to run and execute them"""
        now = datetime.now()
        
        for job in list(self.scheduled_jobs.values()):
            if not job.enabled:
                continue
            
            try:
                # Check if job should run now
                if self._should_run_job(job, now):
                    logger.info(f"Running scheduled job: {job.name}")
                    
                    # Run job in background
                    asyncio.create_task(self._run_job(job))
                    
            except Exception as e:
                logger.error(f"Error checking job {job.name}: {e}")
    
    def _should_run_job(self, job: BackupJob, now: datetime) -> bool:
        """Check if a job should run at the current time"""
        if not job.schedule:
            return False
        
        try:
            cron = croniter(job.schedule, now)
            next_run = cron.get_next(datetime)
            
            # Check if the next run time is within the next minute
            time_diff = next_run - now
            return 0 <= time_diff.total_seconds() <= 60
            
        except Exception as e:
            logger.error(f"Error parsing cron schedule for job {job.name}: {e}")
            return False
    
    async def _run_job(self, job: BackupJob):
        """Execute a backup job"""
        try:
            # Create progress callback
            def progress_callback(progress: int, message: str):
                logger.debug(f"Job {job.name} progress: {progress}% - {message}")
            
            # Run backup
            result = await self.backup_manager.create_backup(
                job, 
                progress_callback=progress_callback
            )
            
            # Add to history
            self._add_to_history(result)
            
            # Log result
            if result.status == BackupStatus.COMPLETED:
                logger.info(f"Job {job.name} completed successfully")
            else:
                logger.error(f"Job {job.name} failed: {result.error_message}")
            
            # Handle retention
            await self._handle_retention(job)
            
        except Exception as e:
            logger.error(f"Error running job {job.name}: {e}")
            
            # Create failed result
            result = BackupResult(
                job_id=job.id,
                status=BackupStatus.FAILED,
                start_time=datetime.now(),
                end_time=datetime.now(),
                error_message=str(e)
            )
            self._add_to_history(result)
    
    def _add_to_history(self, result: BackupResult):
        """Add result to job history"""
        self.job_history.append(result)
        
        # Limit history size
        if len(self.job_history) > self.max_history:
            self.job_history = self.job_history[-self.max_history:]
    
    async def _handle_retention(self, job: BackupJob):
        """Handle backup retention for a job"""
        try:
            backup_dir = job.backup_dir
            
            if not backup_dir.exists():
                return
            
            # Get all backup files for this job
            cutoff_date = datetime.now() - timedelta(days=job.retention_days)
            
            for backup_file in backup_dir.glob(f"{job.name}_*"):
                try:
                    # Extract timestamp from filename
                    timestamp_str = backup_file.stem.split('_')[-1]
                    file_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    
                    # Delete old files
                    if file_date < cutoff_date:
                        backup_file.unlink()
                        logger.info(f"Deleted old backup: {backup_file}")
                        
                except (ValueError, IndexError):
                    # Skip files that don't match the expected pattern
                    continue
            
        except Exception as e:
            logger.error(f"Error handling retention for job {job.name}: {e}")
    
    def get_next_run_time(self, job: BackupJob) -> Optional[datetime]:
        """Get next run time for a job"""
        if not job.schedule or not job.enabled:
            return None
        
        try:
            cron = croniter(job.schedule, datetime.now())
            return cron.get_next(datetime)
        except Exception as e:
            logger.error(f"Error getting next run time for job {job.name}: {e}")
            return None
    
    def get_job_stats(self) -> Dict[str, any]:
        """Get scheduler statistics"""
        total_jobs = len(self.scheduled_jobs)
        enabled_jobs = sum(1 for job in self.scheduled_jobs.values() if job.enabled)
        
        # Recent history stats
        recent_history = self.job_history[-100:]  # Last 100 runs
        successful_runs = sum(1 for result in recent_history if result.status == BackupStatus.COMPLETED)
        failed_runs = sum(1 for result in recent_history if result.status == BackupStatus.FAILED)
        
        return {
            "total_jobs": total_jobs,
            "enabled_jobs": enabled_jobs,
            "disabled_jobs": total_jobs - enabled_jobs,
            "recent_runs": len(recent_history),
            "successful_runs": successful_runs,
            "failed_runs": failed_runs,
            "success_rate": (successful_runs / len(recent_history) * 100) if recent_history else 0,
            "last_run": recent_history[-1].start_time.isoformat() if recent_history else None
        }
    
    def load_jobs_from_config(self):
        """Load jobs from configuration"""
        jobs = self.config_manager.get_backup_jobs()
        
        for job in jobs:
            if job.schedule and job.enabled:
                self.add_job(job)
        
        logger.info(f"Loaded {len(self.scheduled_jobs)} scheduled jobs")
    
    async def run_job_now(self, job_id: str) -> Optional[BackupResult]:
        """Run a job immediately"""
        if job_id not in self.scheduled_jobs:
            logger.error(f"Job {job_id} not found")
            return None
        
        job = self.scheduled_jobs[job_id]
        logger.info(f"Running job {job.name} immediately")
        
        await self._run_job(job)
        
        # Return the last result for this job
        for result in reversed(self.job_history):
            if result.job_id == job_id:
                return result
        
        return None
    
    def enable_job(self, job_id: str):
        """Enable a job"""
        if job_id in self.scheduled_jobs:
            self.scheduled_jobs[job_id].enabled = True
            logger.info(f"Enabled job: {job_id}")
    
    def disable_job(self, job_id: str):
        """Disable a job"""
        if job_id in self.scheduled_jobs:
            self.scheduled_jobs[job_id].enabled = False
            logger.info(f"Disabled job: {job_id}")
    
    def get_upcoming_runs(self, hours: int = 24) -> List[Dict[str, any]]:
        """Get upcoming job runs"""
        upcoming = []
        now = datetime.now()
        end_time = now + timedelta(hours=hours)
        
        for job in self.scheduled_jobs.values():
            if not job.enabled or not job.schedule:
                continue
            
            try:
                cron = croniter(job.schedule, now)
                next_run = cron.get_next(datetime)
                
                if next_run <= end_time:
                    upcoming.append({
                        "job_id": job.id,
                        "job_name": job.name,
                        "next_run": next_run.isoformat(),
                        "schedule": job.schedule
                    })
            except Exception:
                continue
        
        return sorted(upcoming, key=lambda x: x["next_run"])