"""
Main TUI application for PostgreSQL Backup & Restore Tool
"""

import asyncio
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Button, ListView, ListItem, Label
from textual.reactive import reactive
from textual.binding import Binding

from ..core.config import ConfigManager
from ..core.backup import BackupManager
from ..core.restore import RestoreManager
from ..core.scheduler import BackupScheduler
from ..utils.logger import setup_logging, get_logger

from .screens import (
    DashboardScreen, 
    BackupScreen, 
    RestoreScreen, 
    ScheduleScreen,
    ConfigScreen,
    LogsScreen
)


class PostgresBackupTUI(App):
    """Main TUI application with sidebar navigation"""
    
    CSS = """
    App {
        background: $surface;
        layout: horizontal;
    }
    
    Header {
        background: $primary;
        text-align: center;
        dock: top;
        height: 3;
    }
    
    Footer {
        background: $surface;
        dock: bottom;
        height: 3;
    }
    
    #sidebar {
        background: $panel;
        border-right: solid $primary;
        padding: 1;
        width: 25%;
        dock: left;
    }
    
    #main-content {
        padding: 1;
    }
    
    .sidebar-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin: 1 0;
        padding: 1;
        background: $surface;
    }
    
    .nav-button {
        width: 100%;
        margin: 1 0;
        padding: 1;
        border: solid $primary;
        background: $surface;
    }
    
    .nav-button:hover {
        background: $secondary;
    }
    
    .nav-button.active {
        background: $primary;
        color: $text;
    }
    
    .status-panel {
        background: $panel;
        border: solid $primary;
        padding: 1;
        margin: 1 0;
    }
    
    .column-container {
        layout: horizontal;
        height: 100%;
    }
    
    .column {
        padding: 1;
        background: $surface;
        border: solid $primary;
        width: 1fr;
    }
    
    .panel-title {
        text-style: bold;
        color: $primary;
        margin: 0 0 1 0;
        padding: 0 0 1 0;
        border-bottom: solid $accent;
    }
    
    .info-text {
        color: $text;
        margin: 1 0;
    }
    
    .success {
        color: $success;
    }
    
    .error {
        color: $error;
    }
    
    .warning {
        color: $warning;
    }
    
    .button-group {
        layout: horizontal;
        height: auto;
        margin: 1 0;
    }
    
    .button-group > Button {
        margin: 0 1;
    }
    
    .form-container {
        padding: 1;
        background: $panel;
        margin: 1 0;
    }
    
    .form-row {
        layout: horizontal;
        height: 3;
        margin: 1 0;
    }
    
    .form-row > Label {
        width: 20%;
        text-align: right;
        padding: 0 1 0 0;
    }
    
    .form-row > Input {
        width: 80%;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("1", "dashboard", "Dashboard"),
        Binding("2", "backup", "Backup"),
        Binding("3", "restore", "Restore"),
        Binding("4", "schedule", "Schedule"),
        Binding("5", "config", "Config"),
        Binding("6", "logs", "Logs"),
        Binding("ctrl+r", "refresh", "Refresh"),
        Binding("tab", "focus_next", "Next"),
        Binding("shift+tab", "focus_previous", "Previous"),
    ]
    
    TITLE = "PostgreSQL Backup & Restore Tool"
    
    current_screen_name: reactive[str] = reactive("dashboard")
    
    def __init__(self, config_file: Optional[Path] = None):
        super().__init__()
        
        # Initialize core components
        self.config_manager = ConfigManager(config_file)
        self.backup_manager = BackupManager(self.config_manager)
        self.restore_manager = RestoreManager(self.config_manager)
        self.scheduler = BackupScheduler(self.config_manager, self.backup_manager)
        
        # Setup logging
        log_file = self.config_manager.get_app_dir() / "tui.log"
        setup_logging(
            log_level=self.config_manager.get_config_value("app.log_level", "INFO"),
            log_file=log_file
        )
        
        self.logger = get_logger(__name__)
        
        # Initialize screens
        self.screens = {
            "dashboard": DashboardScreen(self),
            "backup": BackupScreen(self),
            "restore": RestoreScreen(self),
            "schedule": ScheduleScreen(self),
            "config": ConfigScreen(self),
            "logs": LogsScreen(self)
        }
    
    def compose(self) -> ComposeResult:
        """Compose the app with sidebar layout"""
        yield Header()
        
        with Container(id="sidebar"):
            yield Static("🐘 PostgreSQL Backup Tool", classes="sidebar-title")
            yield self._create_sidebar_navigation()
            yield self._create_status_panel()
        
        with Container(id="main-content"):
            yield Container(id="screen-container")
        
        yield Footer()
    
    def _create_sidebar_navigation(self):
        """Create sidebar navigation buttons"""
        nav_items = [
            ("📊 Dashboard", "1", "dashboard"),
            ("💾 Backup", "2", "backup"),
            ("📥 Restore", "3", "restore"),
            ("⏰ Schedule", "4", "schedule"),
            ("⚙️ Config", "5", "config"),
            ("📋 Logs", "6", "logs")
        ]
        
        buttons = []
        for label, key, screen_name in nav_items:
            button = Button(
                f"{label} [{key}]",
                name=f"nav-{screen_name}",
                classes="nav-button"
            )
            button.tooltip = f"Press {key} or click to open {label.replace(' [', '').split(' [')[0]}"
            buttons.append(button)
        
        return Container(*buttons)
    
    def _create_status_panel(self):
        """Create status panel in sidebar"""
        return Container(
            Static("📈 Status", classes="panel-title"),
            Static("🟢 System Ready", classes="info-text"),
            Static("Source: Configured", classes="info-text"),
            Static("Target: Configured", classes="info-text"),
            Static("Jobs: 0 Active", classes="info-text"),
            classes="status-panel"
        )
    
    def on_mount(self) -> None:
        """Called when app is mounted"""
        self.logger.info("TUI application started")
        
        # Show dashboard by default
        self.push_screen(self.screens["dashboard"])
        self.current_screen_name = "dashboard"
        
        # Highlight first navigation button
        self._update_navigation_highlight("dashboard")
        
        # Start scheduler in background
        asyncio.create_task(self._start_scheduler())
    
    async def _start_scheduler(self):
        """Start the backup scheduler"""
        try:
            self.scheduler.load_jobs_from_config()
            await self.scheduler.start()
            self.logger.info("Scheduler started")
            self._update_status_panel()
        except Exception as e:
            self.logger.error(f"Failed to start scheduler: {e}")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events"""
        button_name = event.button.name
        
        if button_name and button_name.startswith("nav-"):
            screen_name = button_name[4:]  # Remove "nav-" prefix
            self._navigate_to_screen(screen_name)
    
    def action_dashboard(self) -> None:
        """Navigate to dashboard"""
        self._navigate_to_screen("dashboard")
    
    def action_backup(self) -> None:
        """Navigate to backup screen"""
        self._navigate_to_screen("backup")
    
    def action_restore(self) -> None:
        """Navigate to restore screen"""
        self._navigate_to_screen("restore")
    
    def action_schedule(self) -> None:
        """Navigate to schedule screen"""
        self._navigate_to_screen("schedule")
    
    def action_config(self) -> None:
        """Navigate to config screen"""
        self._navigate_to_screen("config")
    
    def action_logs(self) -> None:
        """Navigate to logs screen"""
        self._navigate_to_screen("logs")
    
    def action_refresh(self) -> None:
        """Refresh current screen"""
        current_screen = self.screen
        if hasattr(current_screen, 'refresh'):
            current_screen.refresh()
        self._update_status_panel()
    
    def _navigate_to_screen(self, screen_name: str) -> None:
        """Navigate to a specific screen"""
        if screen_name in self.screens:
            # Clear current screen container
            screen_container = self.query_one("#screen-container")
            screen_container.remove_children()
            
            # Push new screen
            self.push_screen(self.screens[screen_name])
            self.current_screen_name = screen_name
            
            # Update navigation highlighting
            self._update_navigation_highlight(screen_name)
    
    def _update_navigation_highlight(self, active_screen: str) -> None:
        """Update navigation menu highlighting"""
        for button in self.query("Button.nav-button"):
            button_name = button.name
            if button_name and button_name == f"nav-{active_screen}":
                button.add_class("active")
            else:
                button.remove_class("active")
    
    def _update_status_panel(self):
        """Update the status panel with current information"""
        try:
            status_panel = self.query_one(".status-panel")
            # Update status information here
            # This would fetch real-time data from the backup manager
        except:
            pass
    
    def show_status_message(self, message: str, message_type: str = "info") -> None:
        """Show status message to user"""
        self.logger.info(f"Status [{message_type}]: {message}")
        # Could implement a toast notification here
    
    def show_error(self, message: str) -> None:
        """Show error message"""
        self.show_status_message(message, "error")
    
    def show_success(self, message: str) -> None:
        """Show success message"""
        self.show_status_message(message, "success")
    
    def show_warning(self, message: str) -> None:
        """Show warning message"""
        self.show_status_message(message, "warning")
    
    async def on_unmount(self) -> None:
        """Called when app is unmounting"""
        self.logger.info("TUI application stopping")
        
        # Stop scheduler
        await self.scheduler.stop()
        
        # Close database connections
        from ..core.database import db_pool
        await db_pool.close_all()


def run_tui(config_file: Optional[Path] = None):
    """Run the TUI application"""
    app = PostgresBackupTUI(config_file)
    app.run()


if __name__ == "__main__":
    run_tui()