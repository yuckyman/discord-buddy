"""
User Service for Discord Habit Bot.

Handles user registration, profile management, and Discord integration.
"""

import logging
from datetime import datetime
from typing import Optional, List
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from models import User
from database import DatabaseManager

logger = logging.getLogger(__name__)


class UserService:
    """Service for managing Discord users."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    async def get_or_create_user(self, discord_id: str, username: str) -> User:
        """Get existing user or create new one.
        
        Args:
            discord_id: Discord user ID as string
            username: Discord username
            
        Returns:
            User object
        """
        async with self.db_manager.get_session() as session:
            # Try to find existing user
            stmt = select(User).where(User.discord_id == discord_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                # Update username and last active if needed
                if user.username != username or \
                   (datetime.utcnow() - user.last_active).total_seconds() > 300:  # 5 minutes
                    user.username = username
                    user.last_active = datetime.utcnow()
                    await session.commit()
                    logger.debug(f"Updated user {discord_id} activity")
                
                return user
            
            # Create new user
            user = User(
                discord_id=discord_id,
                username=username,
                total_xp=0,
                gold=0,
                level=1
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            logger.info(f"Created new user: {username} ({discord_id})")
            return user
    
    async def get_user_by_discord_id(self, discord_id: str) -> Optional[User]:
        """Get user by Discord ID."""
        async with self.db_manager.get_session() as session:
            stmt = select(User).where(User.discord_id == discord_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
    
    async def update_user_stats(self, user_id: int, xp_delta: int = 0, gold_delta: int = 0) -> User:
        """Update user XP and gold, recalculating level.
        
        Args:
            user_id: Database user ID
            xp_delta: XP to add (can be negative)
            gold_delta: Gold to add (can be negative)
            
        Returns:
            Updated user object
        """
        async with self.db_manager.get_session() as session:
            # Get current user
            user = await session.get(User, user_id)
            if not user:
                raise ValueError(f"User with ID {user_id} not found")
            
            # Update stats
            old_level = user.level
            user.total_xp = max(0, user.total_xp + xp_delta)
            user.gold = max(0, user.gold + gold_delta)
            
            # Calculate new level (simple formula: level = sqrt(xp / 100))
            # This means: Level 1 = 0-99 XP, Level 2 = 100-399 XP, Level 3 = 400-899 XP, etc.
            user.level = max(1, int((user.total_xp / 100) ** 0.5) + 1)
            
            user.last_active = datetime.utcnow()
            
            await session.commit()
            await session.refresh(user)
            
            # Log level up
            if user.level > old_level:
                logger.info(f"User {user.username} leveled up from {old_level} to {user.level}!")
            
            return user
    
    async def get_leaderboard(self, limit: int = 10, sort_by: str = "xp") -> List[User]:
        """Get leaderboard of top users.
        
        Args:
            limit: Number of users to return
            sort_by: Sort criteria ("xp", "level", "gold")
            
        Returns:
            List of top users
        """
        async with self.db_manager.get_session() as session:
            if sort_by == "xp":
                stmt = select(User).where(User.is_active == True).order_by(User.total_xp.desc()).limit(limit)
            elif sort_by == "level":
                stmt = select(User).where(User.is_active == True).order_by(User.level.desc(), User.total_xp.desc()).limit(limit)
            elif sort_by == "gold":
                stmt = select(User).where(User.is_active == True).order_by(User.gold.desc()).limit(limit)
            else:
                raise ValueError(f"Invalid sort_by value: {sort_by}")
            
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    async def deactivate_user(self, discord_id: str) -> bool:
        """Mark user as inactive (soft delete).
        
        Args:
            discord_id: Discord user ID
            
        Returns:
            True if user was deactivated, False if not found
        """
        async with self.db_manager.get_session() as session:
            stmt = (
                update(User)
                .where(User.discord_id == discord_id)
                .values(is_active=False)
            )
            result = await session.execute(stmt)
            await session.commit()
            
            if result.rowcount > 0:
                logger.info(f"Deactivated user {discord_id}")
                return True
            return False
    
    async def get_user_count(self) -> int:
        """Get total count of active users."""
        async with self.db_manager.get_session() as session:
            stmt = select(User).where(User.is_active == True)
            result = await session.execute(stmt)
            return len(list(result.scalars().all()))