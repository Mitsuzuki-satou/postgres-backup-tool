"""
Progress tracking utilities for PostgreSQL Backup & Restore Tool
"""

import time
from typing import Callable, Optional, Any
from pathlib import Path


class ProgressCallback:
    """Progress callback function type"""
    
    def __init__(self, callback: Callable[[int, str], None]):
        self.callback = callback
    
    def __call__(self, progress: int, message: str):
        """Call the progress callback"""
        self.callback(progress, message)


class ProgressTracker:
    """Progress tracking utility"""
    
    def __init__(self, total: int = 100, description: str = "Processing"):
        self.total = total
        self.current = 0
        self.description = description
        self.start_time = time.time()
        self.last_update = 0
        self.callback: Optional[ProgressCallback] = None
    
    def set_callback(self, callback: Callable[[int, str], None]):
        """Set progress callback function"""
        self.callback = ProgressCallback(callback)
    
    def update(self, current: Optional[int] = None, message: Optional[str] = None):
        """Update progress"""
        if current is not None:
            self.current = current
        else:
            self.current += 1
        
        if message:
            self.description = message
        
        # Throttle updates to avoid too frequent calls
        current_time = time.time()
        if current_time - self.last_update < 0.1:  # 100ms throttle
            return
        
        self.last_update = current_time
        
        if self.callback:
            progress = min(100, (self.current * 100) // self.total) if self.total > 0 else 0
            elapsed = int(current_time - self.start_time)
            status_message = f"{self.description} ({elapsed}s)"
            self.callback(progress, status_message)
    
    def set_total(self, total: int):
        """Set total progress"""
        self.total = total
    
    def finish(self, message: str = "Completed"):
        """Mark progress as finished"""
        self.current = self.total
        if self.callback:
            elapsed = int(time.time() - self.start_time)
            status_message = f"{message} ({elapsed}s)"
            self.callback(100, status_message)


class FileProgressTracker(ProgressTracker):
    """File operation progress tracker"""
    
    def __init__(self, file_path: Path, description: str = "File operation"):
        super().__init__(description=description)
        self.file_path = file_path
        self.file_size = file_path.stat().st_size if file_path.exists() else 0
        self.processed_bytes = 0
    
    def update_bytes(self, processed_bytes: int, message: Optional[str] = None):
        """Update progress based on bytes processed"""
        self.processed_bytes = processed_bytes
        
        if self.file_size > 0:
            progress = int((processed_bytes * 100) / self.file_size)
            self.current = progress
        
        if message:
            self.description = message
        
        if self.callback:
            elapsed = int(time.time() - self.start_time)
            mb_processed = processed_bytes / (1024 * 1024)
            mb_total = self.file_size / (1024 * 1024)
            speed = mb_processed / elapsed if elapsed > 0 else 0
            
            status_message = (
                f"{self.description}: {mb_processed:.1f}/{mb_total:.1f}MB "
                f"({speed:.1f}MB/s, {elapsed}s)"
            )
            self.callback(min(100, self.current), status_message)


class DatabaseProgressTracker(ProgressTracker):
    """Database operation progress tracker"""
    
    def __init__(self, description: str = "Database operation"):
        super().__init__(description=description)
        self.tables_processed = 0
        self.total_tables = 0
    
    def update_tables(self, tables_processed: int, total_tables: int, message: Optional[str] = None):
        """Update progress based on tables processed"""
        self.tables_processed = tables_processed
        self.total_tables = total_tables
        
        if total_tables > 0:
            progress = int((tables_processed * 100) / total_tables)
            self.current = progress
        
        if message:
            self.description = message
        
        if self.callback:
            elapsed = int(time.time() - self.start_time)
            status_message = (
                f"{self.description}: {tables_processed}/{total_tables} tables "
                f"({elapsed}s)"
            )
            self.callback(min(100, self.current), status_message)


class MultiProgressTracker:
    """Multi-operation progress tracker"""
    
    def __init__(self, description: str = "Multi-operation"):
        self.description = description
        self.trackers: list[ProgressTracker] = []
        self.weights: list[float] = []
        self.start_time = time.time()
        self.callback: Optional[ProgressCallback] = None
    
    def add_tracker(self, tracker: ProgressTracker, weight: float = 1.0):
        """Add a progress tracker with weight"""
        self.trackers.append(tracker)
        self.weights.append(weight)
        
        # Set callback to update overall progress
        def update_callback(progress: int, message: str):
            self.update_overall()
        
        tracker.set_callback(update_callback)
    
    def set_callback(self, callback: Callable[[int, str], None]):
        """Set overall progress callback"""
        self.callback = ProgressCallback(callback)
    
    def update_overall(self):
        """Update overall progress based on all trackers"""
        if not self.trackers:
            return
        
        total_weight = sum(self.weights)
        weighted_progress = 0
        
        for tracker, weight in zip(self.trackers, self.weights):
            progress = (tracker.current * 100) // tracker.total if tracker.total > 0 else 0
            weighted_progress += (progress * weight) / total_weight
        
        if self.callback:
            elapsed = int(time.time() - self.start_time)
            status_message = f"{self.description} ({elapsed}s)"
            self.callback(int(weighted_progress), status_message)
    
    def finish(self, message: str = "All operations completed"):
        """Mark all operations as finished"""
        for tracker in self.trackers:
            tracker.finish()
        
        if self.callback:
            elapsed = int(time.time() - self.start_time)
            status_message = f"{message} ({elapsed}s)"
            self.callback(100, status_message)


def create_console_progress_tracker() -> ProgressTracker:
    """Create a console progress tracker"""
    def console_callback(progress: int, message: str):
        # Simple console progress bar
        bar_length = 50
        filled_length = int(bar_length * progress // 100)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        print(f'\r{message} [{bar}] {progress}%', end='', flush=True)
        
        if progress == 100:
            print()  # New line when complete
    
    tracker = ProgressTracker()
    tracker.set_callback(console_callback)
    return tracker


def create_file_progress_tracker(file_path: Path) -> FileProgressTracker:
    """Create a file progress tracker with console output"""
    def console_callback(progress: int, message: str):
        bar_length = 50
        filled_length = int(bar_length * progress // 100)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        print(f'\r{message} [{bar}] {progress}%', end='', flush=True)
        
        if progress == 100:
            print()  # New line when complete
    
    tracker = FileProgressTracker(file_path)
    tracker.set_callback(console_callback)
    return tracker