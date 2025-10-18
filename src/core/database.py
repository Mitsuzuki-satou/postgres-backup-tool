"""
Database operations for PostgreSQL Backup & Restore Tool
"""

import asyncio
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import asyncpg
import psycopg2
from psycopg2.extras import RealDictCursor

from .models import DatabaseConfig, BackupStatus
from ..utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """Database connection and operations manager"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._connection = None
        self._async_pool = None
    
    def get_connection_string(self) -> str:
        """Get PostgreSQL connection string"""
        return (
            f"postgresql://{self.config.username}:{self.config.password}@"
            f"{self.config.host}:{self.config.port}/{self.config.database}"
            f"?sslmode={self.config.ssl_mode}"
        )
    
    async def get_async_connection(self) -> asyncpg.Connection:
        """Get async database connection"""
        return await asyncpg.connect(
            host=self.config.host,
            port=self.config.port,
            database=self.config.database,
            user=self.config.username,
            password=self.config.password,
            ssl=self.config.ssl_mode,
            command_timeout=self.config.connection_timeout
        )
    
    async def get_connection_pool(self) -> asyncpg.Pool:
        """Get async connection pool"""
        if not self._async_pool:
            self._async_pool = await asyncpg.create_pool(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.username,
                password=self.config.password,
                ssl=self.config.ssl_mode,
                command_timeout=self.config.connection_timeout,
                min_size=2,
                max_size=10
            )
        return self._async_pool
    
    def get_sync_connection(self):
        """Get synchronous database connection"""
        return psycopg2.connect(
            host=self.config.host,
            port=self.config.port,
            database=self.config.database,
            user=self.config.username,
            password=self.config.password,
            sslmode=self.config.ssl_mode,
            connect_timeout=self.config.connection_timeout
        )
    
    async def test_connection(self) -> Tuple[bool, str]:
        """Test database connection"""
        try:
            conn = await self.get_async_connection()
            version = await conn.fetchval("SELECT version()")
            await conn.close()
            return True, version
        except Exception as e:
            return False, str(e)
    
    def test_connection_sync(self) -> Tuple[bool, str]:
        """Test database connection synchronously"""
        try:
            conn = self.get_sync_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT version()")
                version = cursor.fetchone()["version"]
            conn.close()
            return True, version
        except Exception as e:
            return False, str(e)
    
    async def get_database_size(self) -> int:
        """Get database size in bytes"""
        try:
            conn = await self.get_async_connection()
            size = await conn.fetchval(
                "SELECT pg_database_size($1)", self.config.database
            )
            await conn.close()
            return size
        except Exception as e:
            logger.error(f"Error getting database size: {e}")
            return 0
    
    async def get_table_count(self) -> int:
        """Get table count"""
        try:
            conn = await self.get_async_connection()
            count = await conn.fetchval(
                """SELECT COUNT(*) FROM information_schema.tables 
                   WHERE table_schema = 'public'"""
            )
            await conn.close()
            return count
        except Exception as e:
            logger.error(f"Error getting table count: {e}")
            return 0
    
    async def get_table_list(self) -> List[Dict[str, Any]]:
        """Get list of tables with sizes"""
        try:
            conn = await self.get_async_connection()
            tables = await conn.fetch(
                """SELECT 
                   schemaname,
                   tablename,
                   pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                   pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                   FROM pg_tables 
                   WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
                   ORDER BY size_bytes DESC"""
            )
            await conn.close()
            return [dict(table) for table in tables]
        except Exception as e:
            logger.error(f"Error getting table list: {e}")
            return []
    
    async def get_schema_list(self) -> List[str]:
        """Get list of schemas"""
        try:
            conn = await self.get_async_connection()
            schemas = await conn.fetch(
                """SELECT schema_name FROM information_schema.schemata
                   WHERE schema_name NOT IN ('information_schema', 'pg_catalog')
                   ORDER BY schema_name"""
            )
            await conn.close()
            return [schema["schema_name"] for schema in schemas]
        except Exception as e:
            logger.error(f"Error getting schema list: {e}")
            return []
    
    async def database_exists(self, database_name: str) -> bool:
        """Check if database exists"""
        try:
            conn = await self.get_async_connection()
            exists = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1", database_name
            )
            await conn.close()
            return bool(exists)
        except Exception as e:
            logger.error(f"Error checking if database exists: {e}")
            return False
    
    async def create_database(self, database_name: str) -> bool:
        """Create new database"""
        try:
            # Connect to postgres database to create new database
            temp_config = self.config.copy()
            temp_config.database = "postgres"
            temp_manager = DatabaseManager(temp_config)
            
            conn = await temp_manager.get_async_connection()
            await conn.execute(f'CREATE DATABASE "{database_name}"')
            await conn.close()
            
            logger.info(f"Database {database_name} created successfully")
            return True
        except Exception as e:
            logger.error(f"Error creating database: {e}")
            return False
    
    async def drop_database(self, database_name: str) -> bool:
        """Drop database"""
        try:
            # Connect to postgres database to drop database
            temp_config = self.config.copy()
            temp_config.database = "postgres"
            temp_manager = DatabaseManager(temp_config)
            
            conn = await temp_manager.get_async_connection()
            await conn.execute(f'DROP DATABASE IF EXISTS "{database_name}"')
            await conn.close()
            
            logger.info(f"Database {database_name} dropped successfully")
            return True
        except Exception as e:
            logger.error(f"Error dropping database: {e}")
            return False
    
    async def get_database_info(self) -> Dict[str, Any]:
        """Get comprehensive database information"""
        try:
            conn = await self.get_async_connection()
            
            # Basic info
            version = await conn.fetchval("SELECT version()")
            size = await conn.fetchval(
                "SELECT pg_database_size($1)", self.config.database
            )
            
            # Table count
            table_count = await conn.fetchval(
                """SELECT COUNT(*) FROM information_schema.tables 
                   WHERE table_schema = 'public'"""
            )
            
            # Schema count
            schema_count = await conn.fetchval(
                """SELECT COUNT(*) FROM information_schema.schemata
                   WHERE schema_name NOT IN ('information_schema', 'pg_catalog')"""
            )
            
            # Connection count
            connection_count = await conn.fetchval(
                "SELECT count(*) FROM pg_stat_activity WHERE datname = $1",
                self.config.database
            )
            
            await conn.close()
            
            return {
                "version": version,
                "size_bytes": size,
                "size_pretty": self._format_size(size),
                "table_count": table_count,
                "schema_count": schema_count,
                "connection_count": connection_count,
                "last_checked": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting database info: {e}")
            return {}
    
    def _format_size(self, size_bytes: int) -> str:
        """Format size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    async def close(self):
        """Close connections"""
        if self._async_pool:
            await self._async_pool.close()
            self._async_pool = None


class DatabasePool:
    """Database connection pool manager"""
    
    def __init__(self):
        self.pools: Dict[str, asyncpg.Pool] = {}
    
    async def get_pool(self, config: DatabaseConfig) -> asyncpg.Pool:
        """Get or create connection pool for database config"""
        pool_key = f"{config.host}:{config.port}:{config.database}"
        
        if pool_key not in self.pools:
            self.pools[pool_key] = await asyncpg.create_pool(
                host=config.host,
                port=config.port,
                database=config.database,
                user=config.username,
                password=config.password,
                ssl=config.ssl_mode,
                command_timeout=config.connection_timeout,
                min_size=2,
                max_size=10
            )
        
        return self.pools[pool_key]
    
    async def close_all(self):
        """Close all connection pools"""
        for pool in self.pools.values():
            await pool.close()
        self.pools.clear()


# Global database pool instance
db_pool = DatabasePool()