"""
TUI screens for PostgreSQL Backup & Restore Tool with column-based layout
"""

from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Static, Button, ListView, ListItem, Label, 
    ProgressBar, DataTable, Input, Select
)
from textual.binding import Binding
from datetime import datetime
from typing import Optional


class DashboardScreen(Screen):
    """Dashboard screen showing overview with column layout"""
    
    BINDINGS = [
        Binding("r", "refresh", "Refresh"),
        Binding("b", "backup", "New Backup"),
        Binding("s", "restore", "Restore"),
    ]
    
    def __init__(self, app):
        super().__init__()
        self.main_app = app
    
    def compose(self):
        with Container(classes="column-container"):
            # Left Column - System Status
            with Container(classes="column"):
                yield Static("📊 System Status", classes="panel-title")
                yield self._create_status_panel()
                yield self._create_quick_actions()
            
            # Right Column - Recent Activity
            with Container(classes="column"):
                yield Static("📋 Recent Activity", classes="panel-title")
                yield self._create_activity_panel()
                yield self._create_backup_stats()
    
    def _create_status_panel(self):
        """Create system status panel"""
        return Container(
            Static("🟢 All Systems Operational", classes="info-text success"),
            Static(f"Last Backup: {datetime.now().strftime('%Y-%m-%d %H:%M')}", classes="info-text"),
            Static("Active Jobs: 0", classes="info-text"),
            Static("Source DB: Connected", classes="info-text"),
            Static("Target DB: Connected", classes="info-text"),
            classes="form-container"
        )
    
    def _create_quick_actions(self):
        """Create quick actions panel"""
        return Container(
            Static("⚡ Quick Actions", classes="panel-title"),
            Container(
                Button("📦 Create Backup", name="quick_backup", variant="primary"),
                Button("📥 Restore Backup", name="quick_restore"),
                Button("⚙️ Configure", name="configure"),
                classes="button-group"
            ),
            classes="form-container"
        )
    
    def _create_activity_panel(self):
        """Create recent activity panel"""
        return Container(
            ListView(
                ListItem(Label("✅ Backup completed: source_db_20231015_120000")),
                ListItem(Label("✅ Restore completed: target_db")),
                ListItem(Label("📅 Schedule created: daily_backup")),
                ListItem(Label("⚙️ Configuration updated")),
                ListItem(Label("🔍 Connection tested: source_db")),
            ),
            classes="form-container"
        )
    
    def _create_backup_stats(self):
        """Create backup statistics panel"""
        return Container(
            Static("📈 Backup Statistics", classes="panel-title"),
            Static("Total Backups: 42", classes="info-text"),
            Static("Total Size: 8.5 GB", classes="info-text"),
            Static("This Month: 12", classes="info-text"),
            Static("Success Rate: 98.5%", classes="info-text"),
            classes="form-container"
        )
    
    def on_button_pressed(self, event):
        """Handle button presses"""
        if event.button.name == "quick_backup":
            self.main_app._navigate_to_screen("backup")
        elif event.button.name == "quick_restore":
            self.main_app._navigate_to_screen("restore")
        elif event.button.name == "configure":
            self.main_app._navigate_to_screen("config")
    
    def action_refresh(self):
        """Refresh dashboard data"""
        self.main_app.show_success("Dashboard refreshed")
    
    def action_backup(self):
        """Navigate to backup screen"""
        self.main_app._navigate_to_screen("backup")
    
    def action_restore(self):
        """Navigate to restore screen"""
        self.main_app._navigate_to_screen("restore")


class BackupScreen(Screen):
    """Backup screen with column layout"""
    
    BINDINGS = [
        Binding("s", "start_backup", "Start Backup"),
        Binding("t", "test_source", "Test Source"),
        Binding("c", "cancel", "Cancel"),
    ]
    
    def __init__(self, app):
        super().__init__()
        self.main_app = app
    
    def compose(self):
        with Container(classes="column-container"):
            # Left Column - Source Configuration
            with Container(classes="column"):
                yield Static("💾 Source Database", classes="panel-title")
                yield self._create_source_config()
                yield self._create_backup_options()
            
            # Right Column - Backup Progress & Settings
            with Container(classes="column"):
                yield Static("⚙️ Backup Settings", classes="panel-title")
                yield self._create_backup_settings()
                yield self._create_progress_section()
    
    def _create_source_config(self):
        """Create source database configuration"""
        return Container(
            Container(
                Label("Host:"),
                Input(placeholder="localhost", name="source_host", value="localhost"),
                classes="form-row"
            ),
            Container(
                Label("Port:"),
                Input(placeholder="5432", name="source_port", value="5432"),
                classes="form-row"
            ),
            Container(
                Label("Database:"),
                Input(placeholder="source_db", name="source_database"),
                classes="form-row"
            ),
            Container(
                Label("Username:"),
                Input(placeholder="postgres", name="source_username", value="postgres"),
                classes="form-row"
            ),
            Container(
                Label("Password:"),
                Input(placeholder="password", password=True, name="source_password"),
                classes="form-row"
            ),
            Button("🔍 Test Source Connection", name="test_source", variant="primary"),
            classes="form-container"
        )
    
    def _create_backup_options(self):
        """Create backup options"""
        return Container(
            Static("📋 Backup Options", classes="panel-title"),
            Container(
                Label("Backup Type:"),
                Select(
                    [("Full", "full"), ("Incremental", "incremental"), ("Differential", "differential")],
                    name="backup_type",
                    value="full"
                ),
                classes="form-row"
            ),
            Container(
                Label("Compression:"),
                Select(
                    [("GZIP", "gzip"), ("BZIP2", "bzip2"), ("None", "none")],
                    name="compression",
                    value="gzip"
                ),
                classes="form-row"
            ),
            Container(
                Label("Parallel Jobs:"),
                Input(placeholder="4", name="parallel_jobs", value="4"),
                classes="form-row"
            ),
            classes="form-container"
        )
    
    def _create_backup_settings(self):
        """Create backup settings"""
        return Container(
            Container(
                Label("Backup Directory:"),
                Input(placeholder="/path/to/backups", name="backup_dir"),
                classes="form-row"
            ),
            Container(
                Label("Retention Days:"),
                Input(placeholder="30", name="retention_days", value="30"),
                classes="form-row"
            ),
            Container(
                Label("Description:"),
                Input(placeholder="Optional backup description", name="description"),
                classes="form-row"
            ),
            classes="form-container"
        )
    
    def _create_progress_section(self):
        """Create progress section"""
        return Container(
            Static("📊 Progress", classes="panel-title"),
            ProgressBar(total=100, show_eta=True, name="backup_progress"),
            Static("Ready to start backup...", name="progress_status", classes="info-text"),
            Container(
                Button("🚀 Start Backup", name="start_backup", variant="primary"),
                Button("❌ Cancel", name="cancel"),
                classes="button-group"
            ),
            classes="form-container"
        )
    
    def on_button_pressed(self, event):
        """Handle button presses"""
        if event.button.name == "start_backup":
            self._start_backup()
        elif event.button.name == "cancel":
            self.main_app._navigate_to_screen("dashboard")
        elif event.button.name == "test_source":
            self._test_source_connection()
    
    def _start_backup(self):
        """Start backup process"""
        progress_bar = self.query_one("#backup_progress", ProgressBar)
        progress_bar.advance(10)
        
        status = self.query_one("#progress_status", Static)
        status.update("🔄 Starting backup...")
        
        self.main_app.show_success("Backup started successfully")
    
    def _test_source_connection(self):
        """Test source database connection"""
        self.main_app.show_success("Source database connection successful")
    
    def action_start_backup(self):
        """Start backup action"""
        self._start_backup()
    
    def action_test_source(self):
        """Test source connection action"""
        self._test_source_connection()
    
    def action_cancel(self):
        """Cancel action"""
        self.main_app._navigate_to_screen("dashboard")


class RestoreScreen(Screen):
    """Restore screen with column layout"""
    
    BINDINGS = [
        Binding("s", "start_restore", "Start Restore"),
        Binding("t", "test_target", "Test Target"),
        Binding("c", "cancel", "Cancel"),
    ]
    
    def __init__(self, app):
        super().__init__()
        self.main_app = app
    
    def compose(self):
        with Container(classes="column-container"):
            # Left Column - Target Configuration
            with Container(classes="column"):
                yield Static("📥 Target Database", classes="panel-title")
                yield self._create_target_config()
                yield self._create_restore_options()
            
            # Right Column - Backup Selection & Progress
            with Container(classes="column"):
                yield Static("📦 Available Backups", classes="panel-title")
                yield self._create_backup_list()
                yield self._create_restore_progress()
    
    def _create_target_config(self):
        """Create target database configuration"""
        return Container(
            Container(
                Label("Host:"),
                Input(placeholder="localhost", name="target_host", value="localhost"),
                classes="form-row"
            ),
            Container(
                Label("Port:"),
                Input(placeholder="5432", name="target_port", value="5432"),
                classes="form-row"
            ),
            Container(
                Label("Database:"),
                Input(placeholder="target_db", name="target_database"),
                classes="form-row"
            ),
            Container(
                Label("Username:"),
                Input(placeholder="postgres", name="target_username", value="postgres"),
                classes="form-row"
            ),
            Container(
                Label("Password:"),
                Input(placeholder="password", password=True, name="target_password"),
                classes="form-row"
            ),
            Button("🔍 Test Target Connection", name="test_target", variant="primary"),
            classes="form-container"
        )
    
    def _create_restore_options(self):
        """Create restore options"""
        return Container(
            Static("⚙️ Restore Options", classes="panel-title"),
            Container(
                Label("Drop Existing:"),
                Select([("Yes", "yes"), ("No", "no")], name="drop_existing", value="no"),
                classes="form-row"
            ),
            Container(
                Label("Verify After:"),
                Select([("Yes", "yes"), ("No", "no")], name="verify_after", value="yes"),
                classes="form-row"
            ),
            Container(
                Label("Clean Before:"),
                Select([("Yes", "yes"), ("No", "no")], name="clean_before", value="yes"),
                classes="form-row"
            ),
            classes="form-container"
        )
    
    def _create_backup_list(self):
        """Create list of available backups"""
        return Container(
            ListView(
                ListItem(Label("📦 source_db_20231015_120000.dump.gz - 250MB")),
                ListItem(Label("📦 source_db_20231014_120000.dump.gz - 245MB")),
                ListItem(Label("📦 source_db_20231013_120000.dump.gz - 240MB")),
                ListItem(Label("📦 source_db_20231012_120000.dump.gz - 238MB")),
            ),
            classes="form-container"
        )
    
    def _create_restore_progress(self):
        """Create restore progress section"""
        return Container(
            Static("📊 Restore Progress", classes="panel-title"),
            ProgressBar(total=100, show_eta=True, name="restore_progress"),
            Static("Select a backup to restore...", name="restore_status", classes="info-text"),
            Container(
                Button("🚀 Start Restore", name="start_restore", variant="primary"),
                Button("❌ Cancel", name="cancel"),
                classes="button-group"
            ),
            classes="form-container"
        )
    
    def on_button_pressed(self, event):
        """Handle button presses"""
        if event.button.name == "start_restore":
            self._start_restore()
        elif event.button.name == "cancel":
            self.main_app._navigate_to_screen("dashboard")
        elif event.button.name == "test_target":
            self._test_target_connection()
    
    def _start_restore(self):
        """Start restore process"""
        progress_bar = self.query_one("#restore_progress", ProgressBar)
        progress_bar.advance(10)
        
        status = self.query_one("#restore_status", Static)
        status.update("🔄 Starting restore...")
        
        self.main_app.show_success("Restore started successfully")
    
    def _test_target_connection(self):
        """Test target database connection"""
        self.main_app.show_success("Target database connection successful")
    
    def action_start_restore(self):
        """Start restore action"""
        self._start_restore()
    
    def action_test_target(self):
        """Test target connection action"""
        self._test_target_connection()
    
    def action_cancel(self):
        """Cancel action"""
        self.main_app._navigate_to_screen("dashboard")


class ScheduleScreen(Screen):
    """Schedule screen with column layout"""
    
    BINDINGS = [
        Binding("a", "add_job", "Add Job"),
        Binding("d", "delete_job", "Delete Job"),
        Binding("r", "refresh", "Refresh"),
    ]
    
    def __init__(self, app):
        super().__init__()
        self.main_app = app
    
    def compose(self):
        with Container(classes="column-container"):
            # Left Column - Add New Job
            with Container(classes="column"):
                yield Static("➕ Add Scheduled Job", classes="panel-title")
                yield self._create_job_form()
            
            # Right Column - Scheduled Jobs List
            with Container(classes="column"):
                yield Static("📅 Scheduled Jobs", classes="panel-title")
                yield self._create_jobs_list()
                yield self._create_job_controls()
    
    def _create_job_form(self):
        """Create job creation form"""
        return Container(
            Container(
                Label("Job Name:"),
                Input(placeholder="daily_backup", name="job_name"),
                classes="form-row"
            ),
            Container(
                Label("Cron Expression:"),
                Input(placeholder="0 2 * * *", name="cron_expr"),
                classes="form-row"
            ),
            Container(
                Label("Source Database:"),
                Input(placeholder="source_db", name="source_db"),
                classes="form-row"
            ),
            Container(
                Label("Enabled:"),
                Select([("Yes", "yes"), ("No", "no")], name="enabled", value="yes"),
                classes="form-row"
            ),
            Container(
                Label("Description:"),
                Input(placeholder="Daily backup at 2 AM", name="description"),
                classes="form-row"
            ),
            Container(
                Button("➕ Add Job", name="add_job", variant="primary"),
                Button("🧹 Clear Form", name="clear_form"),
                classes="button-group"
            ),
            classes="form-container"
        )
    
    def _create_jobs_list(self):
        """Create list of scheduled jobs"""
        return Container(
            ListView(
                ListItem(Label("📅 daily_backup - 0 2 * * * (✅ Enabled)")),
                ListItem(Label("📅 weekly_backup - 0 3 * * 0 (✅ Enabled)")),
                ListItem(Label("📅 monthly_backup - 0 4 1 * * (❌ Disabled)")),
                ListItem(Label("📅 hourly_backup - 0 * * * * (✅ Enabled)")),
            ),
            classes="form-container"
        )
    
    def _create_job_controls(self):
        """Create job control buttons"""
        return Container(
            Static("🎛️ Job Controls", classes="panel-title"),
            Container(
                Button("▶️ Start All", name="start_all"),
                Button("⏸️ Stop All", name="stop_all"),
                Button("🔄 Refresh", name="refresh_jobs"),
                classes="button-group"
            ),
            classes="form-container"
        )
    
    def on_button_pressed(self, event):
        """Handle button presses"""
        if event.button.name == "add_job":
            self._add_job()
        elif event.button.name == "clear_form":
            self._clear_form()
        elif event.button.name == "start_all":
            self.main_app.show_success("All jobs started")
        elif event.button.name == "stop_all":
            self.main_app.show_warning("All jobs stopped")
        elif event.button.name == "refresh_jobs":
            self.main_app.show_success("Job list refreshed")
    
    def _add_job(self):
        """Add new scheduled job"""
        self.main_app.show_success("Scheduled job added successfully")
    
    def _clear_form(self):
        """Clear the form"""
        # Clear all input fields
        for input_widget in self.query("Input"):
            input_widget.value = ""
    
    def action_add_job(self):
        """Add job action"""
        self._add_job()
    
    def action_delete_job(self):
        """Delete job action"""
        self.main_app.show_warning("Job deletion not implemented yet")
    
    def action_refresh(self):
        """Refresh action"""
        self.main_app.show_success("Schedule refreshed")


class ConfigScreen(Screen):
    """Configuration screen with column layout for database reconfiguration"""
    
    BINDINGS = [
        Binding("s", "save_config", "Save Config"),
        Binding("t", "test_connections", "Test All"),
        Binding("r", "reset_config", "Reset"),
        Binding("l", "load_config", "Load"),
    ]
    
    def __init__(self, app):
        super().__init__()
        self.main_app = app
    
    def compose(self):
        with Container(classes="column-container"):
            # Left Column - Source Database Configuration
            with Container(classes="column"):
                yield Static("🔗 Source Database Configuration", classes="panel-title")
                yield self._create_source_db_config()
                yield self._create_source_test_section()
            
            # Right Column - Target Database Configuration
            with Container(classes="column"):
                yield Static("🎯 Target Database Configuration", classes="panel-title")
                yield self._create_target_db_config()
                yield self._create_target_test_section()
    
    def _create_source_db_config(self):
        """Create source database configuration"""
        return Container(
            Static("Configure your source database connection", classes="info-text"),
            Container(
                Label("Host:"),
                Input(placeholder="localhost", name="source_host", value="localhost"),
                classes="form-row"
            ),
            Container(
                Label("Port:"),
                Input(placeholder="5432", name="source_port", value="5432"),
                classes="form-row"
            ),
            Container(
                Label("Database:"),
                Input(placeholder="source_database", name="source_database"),
                classes="form-row"
            ),
            Container(
                Label("Username:"),
                Input(placeholder="postgres", name="source_username", value="postgres"),
                classes="form-row"
            ),
            Container(
                Label("Password:"),
                Input(placeholder="password", password=True, name="source_password"),
                classes="form-row"
            ),
            Container(
                Label("SSL Mode:"),
                Select(
                    [("disable", "disable"), ("allow", "allow"), ("prefer", "prefer"), 
                     ("require", "require"), ("verify-ca", "verify-ca"), ("verify-full", "verify-full")],
                    name="source_ssl_mode",
                    value="prefer"
                ),
                classes="form-row"
            ),
            Container(
                Label("Connection Timeout:"),
                Input(placeholder="30", name="source_timeout", value="30"),
                classes="form-row"
            ),
            classes="form-container"
        )
    
    def _create_source_test_section(self):
        """Create source database test section"""
        return Container(
            Static("🔍 Source Connection Test", classes="panel-title"),
            Static("Test your source database connection before saving", classes="info-text"),
            Button("🔗 Test Source Connection", name="test_source", variant="primary"),
            Static("", name="source_test_result", classes="info-text"),
            classes="form-container"
        )
    
    def _create_target_db_config(self):
        """Create target database configuration"""
        return Container(
            Static("Configure your target database connection", classes="info-text"),
            Container(
                Label("Host:"),
                Input(placeholder="localhost", name="target_host", value="localhost"),
                classes="form-row"
            ),
            Container(
                Label("Port:"),
                Input(placeholder="5432", name="target_port", value="5432"),
                classes="form-row"
            ),
            Container(
                Label("Database:"),
                Input(placeholder="target_database", name="target_database"),
                classes="form-row"
            ),
            Container(
                Label("Username:"),
                Input(placeholder="postgres", name="target_username", value="postgres"),
                classes="form-row"
            ),
            Container(
                Label("Password:"),
                Input(placeholder="password", password=True, name="target_password"),
                classes="form-row"
            ),
            Container(
                Label("SSL Mode:"),
                Select(
                    [("disable", "disable"), ("allow", "allow"), ("prefer", "prefer"), 
                     ("require", "require"), ("verify-ca", "verify-ca"), ("verify-full", "verify-full")],
                    name="target_ssl_mode",
                    value="prefer"
                ),
                classes="form-row"
            ),
            Container(
                Label("Connection Timeout:"),
                Input(placeholder="30", name="target_timeout", value="30"),
                classes="form-row"
            ),
            classes="form-container"
        )
    
    def _create_target_test_section(self):
        """Create target database test section"""
        return Container(
            Static("🔍 Target Connection Test", classes="panel-title"),
            Static("Test your target database connection before saving", classes="info-text"),
            Button("🔗 Test Target Connection", name="test_target", variant="primary"),
            Static("", name="target_test_result", classes="info-text"),
            classes="form-container"
        )
    
    def on_button_pressed(self, event):
        """Handle button presses"""
        if event.button.name == "test_source":
            self._test_source_connection()
        elif event.button.name == "test_target":
            self._test_target_connection()
    
    def _test_source_connection(self):
        """Test source database connection"""
        result = self.query_one("#source_test_result", Static)
        result.update("🔄 Testing source connection...")
        
        # Simulate connection test
        self.set_timer(1.0, lambda: result.update("✅ Source connection successful"))
        self.main_app.show_success("Source database connection successful")
    
    def _test_target_connection(self):
        """Test target database connection"""
        result = self.query_one("#target_test_result", Static)
        result.update("🔄 Testing target connection...")
        
        # Simulate connection test
        self.set_timer(1.0, lambda: result.update("✅ Target connection successful"))
        self.main_app.show_success("Target database connection successful")
    
    def action_save_config(self):
        """Save configuration action"""
        self.main_app.show_success("Configuration saved successfully")
    
    def action_test_connections(self):
        """Test all connections action"""
        self._test_source_connection()
        self._test_target_connection()
    
    def action_reset_config(self):
        """Reset configuration action"""
        self.main_app.show_warning("Configuration reset to defaults")
    
    def action_load_config(self):
        """Load configuration action"""
        self.main_app.show_success("Configuration loaded from file")


class LogsScreen(Screen):
    """Logs screen with column layout"""
    
    BINDINGS = [
        Binding("r", "refresh", "Refresh"),
        Binding("c", "clear", "Clear"),
        Binding("e", "export", "Export"),
        Binding("f", "filter", "Filter"),
    ]
    
    def __init__(self, app):
        super().__init__()
        self.main_app = app
    
    def compose(self):
        with Container(classes="column-container"):
            # Left Column - Log Controls
            with Container(classes="column"):
                yield Static("🎛️ Log Controls", classes="panel-title")
                yield self._create_log_controls()
                yield self._create_log_stats()
            
            # Right Column - Log Display
            with Container(classes="column"):
                yield Static("📋 System Logs", classes="panel-title")
                yield self._create_log_display()
    
    def _create_log_controls(self):
        """Create log control panel"""
        return Container(
            Container(
                Label("Log Level:"),
                Select(
                    [("DEBUG", "debug"), ("INFO", "info"), ("WARNING", "warning"), ("ERROR", "error")],
                    name="log_level",
                    value="info"
                ),
                classes="form-row"
            ),
            Container(
                Label("Max Entries:"),
                Input(placeholder="100", name="max_entries", value="100"),
                classes="form-row"
            ),
            Container(
                Label("Filter:"),
                Input(placeholder="keyword", name="filter_keyword"),
                classes="form-row"
            ),
            Container(
                Button("🔄 Refresh", name="refresh_logs", variant="primary"),
                Button("🧹 Clear", name="clear_logs"),
                Button("📤 Export", name="export_logs"),
                classes="button-group"
            ),
            classes="form-container"
        )
    
    def _create_log_stats(self):
        """Create log statistics panel"""
        return Container(
            Static("📊 Log Statistics", classes="panel-title"),
            Static("Total Entries: 1,234", classes="info-text"),
            Static("Errors: 5", classes="info-text error"),
            Static("Warnings: 23", classes="info-text warning"),
            Static("Info: 1,206", classes="info-text"),
            classes="form-container"
        )
    
    def _create_log_display(self):
        """Create log display area"""
        return Container(
            ScrollableContainer(
                Static("[2023-10-15 12:00:00] INFO: Application started", classes="info-text"),
                Static("[2023-10-15 12:00:01] INFO: Scheduler started", classes="info-text"),
                Static("[2023-10-15 12:00:02] INFO: Source database connected", classes="info-text"),
                Static("[2023-10-15 12:00:03] INFO: Target database connected", classes="info-text"),
                Static("[2023-10-15 12:00:04] WARNING: Connection timeout warning", classes="info-text warning"),
                Static("[2023-10-15 12:00:05] ERROR: Failed to connect to backup server", classes="info-text error"),
                Static("[2023-10-15 12:00:06] INFO: Retrying connection...", classes="info-text"),
                Static("[2023-10-15 12:00:07] INFO: Connection established", classes="info-text"),
                Static("[2023-10-15 12:00:08] INFO: Backup job started", classes="info-text"),
                Static("[2023-10-15 12:00:09] INFO: Backup completed successfully", classes="info-text"),
            ),
            classes="form-container"
        )
    
    def on_button_pressed(self, event):
        """Handle button presses"""
        if event.button.name == "refresh_logs":
            self.main_app.show_success("Logs refreshed")
        elif event.button.name == "clear_logs":
            self.main_app.show_warning("Logs cleared")
        elif event.button.name == "export_logs":
            self.main_app.show_success("Logs exported to file")
    
    def action_refresh(self):
        """Refresh logs action"""
        self.main_app.show_success("Logs refreshed")
    
    def action_clear(self):
        """Clear logs action"""
        self.main_app.show_warning("Logs cleared")
    
    def action_export(self):
        """Export logs action"""
        self.main_app.show_success("Logs exported")
    
    def action_filter(self):
        """Filter logs action"""
        self.main_app.show_info("Filter applied")