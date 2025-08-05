"""
Database connection and session management for Discord Habit Bot.

This module provides async database session management and CRUD operations.
Design decisions:
- Using async sessions for compatibility with Discord.py
- Connection pooling for better performance
- Context managers for proper session lifecycle
- Centralized database configuration
"""

import os
import logging
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession, AsyncEngine
from sqlalchemy.exc import SQLAlchemyError
from models import Base
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and sessions."""
    
    def __init__(self):
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker] = None
        self._initialized = False
    
    def initialize(self, database_url: Optional[str] = None) -> None:
        """Initialize the database engine and session factory.
        
        Args:
            database_url: Database URL. If None, reads from DATABASE_URL env var.
        """
        if self._initialized:
            logger.warning("Database manager already initialized")
            return
        
        if not database_url:
            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                raise ValueError("DATABASE_URL environment variable is required")
        
        # Convert sync URL to async if needed
        if database_url.startswith("sqlite:///"):
            # For SQLite, use aiosqlite
            database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
        elif database_url.startswith("postgresql://"):
            # For PostgreSQL, use asyncpg
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
        
        # Create async engine with connection pooling
        self.engine = create_async_engine(
            database_url,
            echo=os.getenv("DEBUG", "false").lower() == "true",  # Log SQL in debug mode
            pool_pre_ping=True,  # Validate connections before use
            pool_recycle=3600,   # Recycle connections after 1 hour
        )
        
        # Create session factory
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Keep objects usable after commit
        )
        
        self._initialized = True
        logger.info("Database manager initialized successfully")
    
    async def create_tables(self) -> None:
        """Create all database tables."""
        if not self.engine:
            raise RuntimeError("Database manager not initialized")
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database tables created successfully")
    
    async def close(self) -> None:
        """Close the database engine."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database engine closed")
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an async database session with automatic cleanup.
        
        Usage:
            async with db_manager.get_session() as session:
                # Use session here
                pass
        """
        if not self.session_factory:
            raise RuntimeError("Database manager not initialized")
        
        session = self.session_factory()
        try:
            yield session
            await session.commit()
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"Database error: {e}")
            raise
        except Exception as e:
            await session.rollback()
            logger.error(f"Unexpected error: {e}")
            raise
        finally:
            await session.close()


# Global database manager instance
db_manager = DatabaseManager()


# Convenience functions for dependency injection
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session for dependency injection."""
    async with db_manager.get_session() as session:
        yield session


def get_database_url() -> str:
    """Get the database URL from environment."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")
    return database_url


async def initialize_database() -> None:
    """Initialize database connection and create tables if needed.
    
    This function is idempotent and safe to call multiple times.
    """
    try:
        # Initialize database manager
        db_manager.initialize()
        
        # Create tables (idempotent operation)
        await db_manager.create_tables()
        
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def close_database() -> None:
    """Close database connections gracefully."""
    await db_manager.close()