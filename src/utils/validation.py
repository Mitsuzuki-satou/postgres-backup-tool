"""
Validation utilities for PostgreSQL Backup & Restore Tool
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional

from ..core.models import DatabaseConfig, BackupConfig


def validate_database_config(config: DatabaseConfig) -> List[str]:
    """Validate database configuration"""
    errors = []
    
    # Host validation
    if not config.host or not config.host.strip():
        errors.append("Database host is required")
    elif len(config.host) > 253:
        errors.append("Database host is too long (max 253 characters)")
    
    # Port validation
    if not (1 <= config.port <= 65535):
        errors.append("Database port must be between 1 and 65535")
    
    # Database name validation
    if not config.database or not config.database.strip():
        errors.append("Database name is required")
    elif not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', config.database):
        errors.append("Database name contains invalid characters")
    elif len(config.database) > 63:
        errors.append("Database name is too long (max 63 characters)")
    
    # Username validation
    if not config.username or not config.username.strip():
        errors.append("Database username is required")
    elif len(config.username) > 63:
        errors.append("Username is too long (max 63 characters)")
    
    # Password validation
    if not config.password:
        errors.append("Database password is required")
    
    # SSL mode validation
    valid_ssl_modes = ['disable', 'allow', 'prefer', 'require', 'verify-ca', 'verify-full']
    if config.ssl_mode not in valid_ssl_modes:
        errors.append(f"SSL mode must be one of: {', '.join(valid_ssl_modes)}")
    
    # Connection timeout validation
    if not (1 <= config.connection_timeout <= 300):
        errors.append("Connection timeout must be between 1 and 300 seconds")
    
    return errors


def validate_backup_config(config: BackupConfig) -> List[str]:
    """Validate backup configuration"""
    errors = []
    
    # Parallel jobs validation
    if not (1 <= config.parallel_jobs <= 32):
        errors.append("Parallel jobs must be between 1 and 32")
    
    # Schema validation
    for schema in config.exclude_schemas:
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', schema):
            errors.append(f"Invalid schema name in exclude_schemas: {schema}")
    
    for schema in config.include_schemas:
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', schema):
            errors.append(f"Invalid schema name in include_schemas: {schema}")
    
    # Table validation
    for table in config.exclude_tables:
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)?$', table):
            errors.append(f"Invalid table name in exclude_tables: {table}")
    
    for table in config.include_tables:
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)?$', table):
            errors.append(f"Invalid table name in include_tables: {table}")
    
    # Check for conflicting schemas
    if config.exclude_schemas and config.include_schemas:
        conflicts = set(config.exclude_schemas) & set(config.include_schemas)
        if conflicts:
            errors.append(f"Schemas cannot be both included and excluded: {', '.join(conflicts)}")
    
    # Check for conflicting tables
    if config.exclude_tables and config.include_tables:
        conflicts = set(config.exclude_tables) & set(config.include_tables)
        if conflicts:
            errors.append(f"Tables cannot be both included and excluded: {', '.join(conflicts)}")
    
    return errors


def validate_backup_file(file_path: Path) -> List[str]:
    """Validate backup file"""
    errors = []
    
    # Check if file exists
    if not file_path.exists():
        errors.append(f"Backup file does not exist: {file_path}")
        return errors
    
    # Check if it's a file
    if not file_path.is_file():
        errors.append(f"Path is not a file: {file_path}")
        return errors
    
    # Check file extension
    valid_extensions = ['.sql', '.sql.gz', '.dump', '.dump.gz', '.dump.bz2', '.tar', '.tar.gz', '.tar.bz2']
    if file_path.suffix not in valid_extensions:
        errors.append(f"Invalid backup file extension. Must be one of: {', '.join(valid_extensions)}")
    
    # Check file size
    if file_path.stat().st_size == 0:
        errors.append("Backup file is empty")
    
    # Try to open/read the file
    try:
        if file_path.suffix == '.gz':
            import gzip
            with gzip.open(file_path, 'rb') as f:
                f.read(1024)  # Try to read first 1KB
        elif file_path.suffix in ['.bz2']:
            import bz2
            with bz2.open(file_path, 'rb') as f:
                f.read(1024)
        elif file_path.suffix in ['.tar', '.tar.gz', '.tar.bz2']:
            import tarfile
            with tarfile.open(file_path, 'r:*') as tar:
                tar.getmembers()
        else:
            with open(file_path, 'rb') as f:
                f.read(1024)
    except Exception as e:
        errors.append(f"Cannot read backup file: {e}")
    
    return errors


def validate_schedule_expression(schedule: str) -> List[str]:
    """Validate cron schedule expression"""
    errors = []
    
    if not schedule or not schedule.strip():
        errors.append("Schedule expression is required")
        return errors
    
    # Basic cron format validation (5 fields: minute hour day month weekday)
    cron_pattern = r'^(\*|([0-9]|[1-5][0-9])|(\*/[0-9]+)) (\*|([0-9]|1[0-9]|2[0-3])|(\*/[0-9]+)) (\*|([1-9]|[1-2][0-9]|3[0-1])|(\*/[0-9]+)) (\*|([1-9]|1[0-2])|(\*/[0-9]+)) (\*|([0-6])|(\*/[0-9]+))$'
    
    if not re.match(cron_pattern, schedule.strip()):
        errors.append("Invalid cron expression format. Expected format: '* * * * *' (minute hour day month weekday)")
        errors.append("Examples: '0 2 * * *' (daily at 2 AM), '0 2 * * 0' (weekly on Sunday at 2 AM)")
    
    return errors


def validate_email(email: str) -> bool:
    """Validate email address"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_retention_days(days: int) -> List[str]:
    """Validate retention days"""
    errors = []
    
    if not (1 <= days <= 3650):  # Max 10 years
        errors.append("Retention days must be between 1 and 3650")
    
    return errors


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    # Remove or replace invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip(' .')
    # Ensure it's not empty
    if not sanitized:
        sanitized = 'unnamed'
    # Limit length
    if len(sanitized) > 255:
        sanitized = sanitized[:255]
    return sanitized


def validate_connection_string(connection_string: str) -> List[str]:
    """Validate PostgreSQL connection string"""
    errors = []
    
    if not connection_string or not connection_string.strip():
        errors.append("Connection string is required")
        return errors
    
    # Basic pattern for postgresql:// connection string
    pattern = r'^postgresql://[^:]+:[^@]+@[^:]+:[0-9]+/[^/]+$'
    if not re.match(pattern, connection_string.strip()):
        errors.append("Invalid connection string format. Expected: postgresql://username:password@host:port/database")
    
    return errors


def validate_json_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    """Simple JSON schema validation"""
    errors = []
    
    def validate_field(field_name: str, field_schema: Any, field_value: Any, path: str = ""):
        current_path = f"{path}.{field_name}" if path else field_name
        
        if field_schema.get('required', False) and field_value is None:
            errors.append(f"Required field '{current_path}' is missing")
            return
        
        if field_value is None:
            return
        
        field_type = field_schema.get('type')
        if field_type == 'string' and not isinstance(field_value, str):
            errors.append(f"Field '{current_path}' must be a string")
        elif field_type == 'integer' and not isinstance(field_value, int):
            errors.append(f"Field '{current_path}' must be an integer")
        elif field_type == 'boolean' and not isinstance(field_value, bool):
            errors.append(f"Field '{current_path}' must be a boolean")
        elif field_type == 'array' and not isinstance(field_value, list):
            errors.append(f"Field '{current_path}' must be an array")
        elif field_type == 'object' and not isinstance(field_value, dict):
            errors.append(f"Field '{current_path}' must be an object")
        
        # Validate min/max for numbers
        if isinstance(field_value, (int, float)):
            if 'minimum' in field_schema and field_value < field_schema['minimum']:
                errors.append(f"Field '{current_path}' must be >= {field_schema['minimum']}")
            if 'maximum' in field_schema and field_value > field_schema['maximum']:
                errors.append(f"Field '{current_path}' must be <= {field_schema['maximum']}")
        
        # Validate min/max length for strings
        if isinstance(field_value, str):
            if 'minLength' in field_schema and len(field_value) < field_schema['minLength']:
                errors.append(f"Field '{current_path}' must be at least {field_schema['minLength']} characters")
            if 'maxLength' in field_schema and len(field_value) > field_schema['maxLength']:
                errors.append(f"Field '{current_path}' must be at most {field_schema['maxLength']} characters")
        
        # Validate array items
        if isinstance(field_value, list) and 'items' in field_schema:
            for i, item in enumerate(field_value):
                validate_field(str(i), field_schema['items'], item, current_path)
        
        # Validate nested objects
        if isinstance(field_value, dict) and 'properties' in field_schema:
            for prop_name, prop_schema in field_schema['properties'].items():
                validate_field(prop_name, prop_schema, field_value.get(prop_name), current_path)
    
    for field_name, field_schema in schema.items():
        validate_field(field_name, field_schema, data.get(field_name))
    
    return errors