#!/usr/bin/env python3
"""
PostgreSQL Backup & Restore Tool - Main Entry Point
Version 3.0
A comprehensive backup and restore solution with multiple interfaces
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.config import ConfigManager
from src.utils.logger import setup_logging, get_logger


def run_cli_mode(config_file: Optional[Path] = None):
    """Run command-line interface mode"""
    print("🚀 PostgreSQL Backup & Restore Tool - CLI Mode")
    print("=" * 50)
    
    # Import here to avoid circular imports
    from src.core.backup import BackupManager
    from src.core.restore import RestoreManager
    from src.core.database import DatabaseManager
    
    config_manager = ConfigManager(config_file)
    backup_manager = BackupManager(config_manager)
    restore_manager = RestoreManager(config_manager)
    
    # Get database configurations
    remote_config = config_manager.get_database_config("default_remote")
    local_config = config_manager.get_database_config("default_local")
    
    async def run_backup_restore():
        """Run backup and restore process"""
        try:
            # Test connections
            print("🔍 Testing database connections...")
            
            db_manager = DatabaseManager(remote_config)
            success, message = await db_manager.test_connection()
            if success:
                print(f"✅ Remote connection: {message[:50]}...")
            else:
                print(f"❌ Remote connection failed: {message}")
                return
            
            # Create backup job
            from src.core.models import BackupJob, BackupConfig, BackupType, CompressionType
            
            backup_job = BackupJob(
                id="cli_backup",
                name="CLI Backup",
                source_config=remote_config,
                backup_config=BackupConfig(
                    backup_type=BackupType.FULL,
                    compression=CompressionType.GZIP,
                    parallel_jobs=4
                ),
                backup_dir=config_manager.get_backup_dir()
            )
            
            print("📦 Starting backup...")
            result = await backup_manager.create_backup(backup_job)
            
            if result.status.value == "completed":
                print(f"✅ Backup completed: {result.backup_file}")
                print(f"   Size: {result.size_bytes / (1024*1024):.1f} MB")
                print(f"   Duration: {result.duration:.1f} seconds")
            else:
                print(f"❌ Backup failed: {result.error_message}")
                return
            
            # Restore (optional)
            choice = input("\n📥 Restore this backup? (y/N): ").lower().strip()
            if choice == 'y':
                print("Starting restore...")
                restore_result = await restore_manager.restore_backup(
                    result.backup_file, 
                    local_config
                )
                
                if restore_result.status.value == "completed":
                    print(f"✅ Restore completed successfully")
                    print(f"   Tables restored: {restore_result.tables_restored}")
                    print(f"   Duration: {restore_result.duration:.1f} seconds")
                else:
                    print(f"❌ Restore failed: {restore_result.error_message}")
        
        except KeyboardInterrupt:
            print("\n⚠️ Operation cancelled by user")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Run the async function
    asyncio.run(run_backup_restore())


def run_tui_mode(config_file: Optional[Path] = None):
    """Run terminal user interface mode"""
    try:
        from src.tui.app import PostgresBackupTUI
        app = PostgresBackupTUI(config_file)
        app.run()
    except ImportError as e:
        print(f"❌ TUI dependencies not installed: {e}")
        print("Install with: pip install rich textual")
        sys.exit(1)





def run_web_mode(config_file: Optional[Path] = None, host: str = "127.0.0.1", port: int = 8080):
    """Run web interface mode"""
    try:
        import uvicorn
        from src.web.app import create_app
        
        config_manager = ConfigManager(config_file)
        app = create_app(config_manager)
        
        print(f"🌐 Starting web interface on http://{host}:{port}")
        uvicorn.run(app, host=host, port=port)
    except ImportError as e:
        print(f"❌ Web dependencies not installed: {e}")
        print("Install with: pip install fastapi uvicorn")
        sys.exit(1)


def run_scheduler_mode(config_file: Optional[Path] = None):
    """Run scheduler daemon mode"""
    print("⏰ Starting PostgreSQL Backup Scheduler...")
    
    async def run_scheduler():
        config_manager = ConfigManager(config_file)
        backup_manager = BackupManager(config_manager)
        scheduler = BackupScheduler(config_manager, backup_manager)
        
        # Load jobs and start scheduler
        scheduler.load_jobs_from_config()
        await scheduler.start()
        
        print("✅ Scheduler started. Press Ctrl+C to stop.")
        
        try:
            # Keep running
            while True:
                await asyncio.sleep(60)
        except KeyboardInterrupt:
            print("\n⏹️ Stopping scheduler...")
            await scheduler.stop()
            print("✅ Scheduler stopped.")
    
    # Import here to avoid circular imports
    from src.core.backup import BackupManager
    from src.core.scheduler import BackupScheduler
    
    asyncio.run(run_scheduler())


def check_dependencies():
    """Check if required dependencies are available"""
    missing = []
    
    # Check PostgreSQL client tools
    import shutil
    for tool in ["pg_dump", "pg_restore", "psql"]:
        if not shutil.which(tool):
            missing.append(tool)
    
    if missing:
        print(f"❌ Missing required PostgreSQL tools: {', '.join(missing)}")
        print("Please install PostgreSQL client tools:")
        print("  Ubuntu/Debian: sudo apt-get install postgresql-client")
        print("  CentOS/RHEL: sudo yum install postgresql")
        print("  macOS: brew install postgresql")
        return False
    
    return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="PostgreSQL Backup & Restore Tool v3.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Run in CLI mode
  %(prog)s --tui                    # Run terminal UI
  %(prog)s --web                    # Run web interface
  %(prog)s --scheduler              # Run scheduler daemon
  %(prog)s --config myconfig.json   # Use custom config
        """
    )
    
    parser.add_argument("--version", action="version", version="3.0.0")
    parser.add_argument("--config", type=Path, help="Configuration file path")
    
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--cli", action="store_true", help="Command-line interface (default)")
    mode_group.add_argument("--tui", action="store_true", help="Terminal user interface")
    
    mode_group.add_argument("--web", action="store_true", help="Web interface")
    mode_group.add_argument("--scheduler", action="store_true", help="Scheduler daemon mode")
    
    # Web-specific options
    parser.add_argument("--host", default="127.0.0.1", help="Web interface host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Web interface port (default: 8080)")
    
    # Logging options
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], 
                       default="INFO", help="Log level (default: INFO)")
    parser.add_argument("--log-file", type=Path, help="Log file path")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(
        log_level=args.log_level,
        log_file=args.log_file
    )
    
    logger = get_logger(__name__)
    logger.info("PostgreSQL Backup & Restore Tool v3.0 started")
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    try:
        # Run appropriate mode
        if args.tui:
            run_tui_mode(args.config)
        
        elif args.web:
            run_web_mode(args.config, args.host, args.port)
        elif args.scheduler:
            run_scheduler_mode(args.config)
        else:
            run_cli_mode(args.config)
    
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()