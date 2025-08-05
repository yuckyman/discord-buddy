"""
Habit Service for Discord Habit Bot.

Handles habit definitions, logging completions, and tracking progress.
"""

import logging
from datetime import datetime, date
from typing import Optional, List, Tuple
from sqlalchemy import select, and_, func
from sqlalchemy.exc import IntegrityError
from models import Habit, HabitLog, User
from database import DatabaseManager

logger = logging.getLogger(__name__)


class HabitService:
    """Service for managing habits and habit logging."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    async def create_habit(self, name: str, description: Optional[str] = None, 
                          base_xp: int = 10, category: Optional[str] = None) -> Habit:
        """Create a new habit definition.
        
        Args:
            name: Habit name
            description: Optional description
            base_xp: Base XP awarded for completion
            category: Optional category for grouping
            
        Returns:
            Created habit object
        """
        async with self.db_manager.get_session() as session:
            habit = Habit(
                name=name,
                description=description,
                base_xp=base_xp,
                category=category
            )
            session.add(habit)
            await session.commit()
            await session.refresh(habit)
            
            logger.info(f"Created new habit: {name} (XP: {base_xp})")
            return habit
    
    async def get_habit_by_name(self, name: str) -> Optional[Habit]:
        """Get habit by name (case-insensitive)."""
        async with self.db_manager.get_session() as session:
            stmt = select(Habit).where(
                and_(
                    func.lower(Habit.name) == name.lower(),
                    Habit.is_active == True
                )
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
    
    async def get_all_habits(self, include_inactive: bool = False) -> List[Habit]:
        """Get all habit definitions.
        
        Args:
            include_inactive: Whether to include inactive habits
            
        Returns:
            List of habits
        """
        async with self.db_manager.get_session() as session:
            if include_inactive:
                stmt = select(Habit).order_by(Habit.name)
            else:
                stmt = select(Habit).where(Habit.is_active == True).order_by(Habit.name)
            
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    async def get_habits_by_category(self, category: str) -> List[Habit]:
        """Get habits by category."""
        async with self.db_manager.get_session() as session:
            stmt = select(Habit).where(
                and_(
                    Habit.category == category,
                    Habit.is_active == True
                )
            ).order_by(Habit.name)
            
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    async def log_habit_completion(self, user_id: int, habit_id: int, 
                                  notes: Optional[str] = None, 
                                  source: str = "command") -> Tuple[HabitLog, bool]:
        """Log a habit completion for a user.
        
        Args:
            user_id: Database user ID
            habit_id: Habit ID
            notes: Optional notes about the completion
            source: Source of the log ("command" or "reaction")
            
        Returns:
            Tuple of (HabitLog, is_new) where is_new indicates if this is a new log for today
        """
        async with self.db_manager.get_session() as session:
            # Check if already logged today
            today = date.today()
            existing_stmt = select(HabitLog).where(
                and_(
                    HabitLog.user_id == user_id,
                    HabitLog.habit_id == habit_id,
                    HabitLog.completion_date == today
                )
            )
            existing_result = await session.execute(existing_stmt)
            existing_log = existing_result.scalar_one_or_none()
            
            if existing_log:
                # Update existing log with new notes if provided
                if notes:
                    existing_log.notes = notes
                existing_log.source = source  # Update source
                existing_log.completed_at = datetime.utcnow()  # Update timestamp
                await session.commit()
                await session.refresh(existing_log)
                
                logger.debug(f"Updated existing habit log for user {user_id}, habit {habit_id}")
                return existing_log, False
            
            # Get habit info for XP calculation
            habit = await session.get(Habit, habit_id)
            if not habit:
                raise ValueError(f"Habit with ID {habit_id} not found")
            
            # Create new log
            habit_log = HabitLog(
                user_id=user_id,
                habit_id=habit_id,
                xp_awarded=habit.base_xp,
                notes=notes,
                source=source,
                completion_date=today
            )
            
            try:
                session.add(habit_log)
                await session.commit()
                await session.refresh(habit_log)
                
                logger.info(f"Logged habit completion: user {user_id}, habit {habit.name}, XP {habit.base_xp}")
                return habit_log, True
                
            except IntegrityError:
                # Handle race condition where another process created the log
                await session.rollback()
                existing_stmt = select(HabitLog).where(
                    and_(
                        HabitLog.user_id == user_id,
                        HabitLog.habit_id == habit_id,
                        HabitLog.completion_date == today
                    )
                )
                existing_result = await session.execute(existing_stmt)
                existing_log = existing_result.scalar_one_or_none()
                
                if existing_log:
                    return existing_log, False
                else:
                    raise  # Re-raise if it's a different integrity error
    
    async def get_user_habit_logs(self, user_id: int, habit_id: Optional[int] = None, 
                                 limit: int = 50) -> List[HabitLog]:
        """Get habit logs for a user.
        
        Args:
            user_id: Database user ID
            habit_id: Optional specific habit ID
            limit: Maximum number of logs to return
            
        Returns:
            List of habit logs, most recent first
        """
        async with self.db_manager.get_session() as session:
            if habit_id:
                stmt = select(HabitLog).where(
                    and_(
                        HabitLog.user_id == user_id,
                        HabitLog.habit_id == habit_id
                    )
                ).order_by(HabitLog.completed_at.desc()).limit(limit)
            else:
                stmt = select(HabitLog).where(
                    HabitLog.user_id == user_id
                ).order_by(HabitLog.completed_at.desc()).limit(limit)
            
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    async def get_user_daily_progress(self, user_id: int, target_date: date = None) -> List[dict]:
        """Get user's habit completion progress for a specific day.
        
        Args:
            user_id: Database user ID
            target_date: Date to check (defaults to today)
            
        Returns:
            List of dicts with habit info and completion status
        """
        if target_date is None:
            target_date = date.today()
        
        async with self.db_manager.get_session() as session:
            # Get all active habits
            habits_stmt = select(Habit).where(Habit.is_active == True).order_by(Habit.name)
            habits_result = await session.execute(habits_stmt)
            habits = list(habits_result.scalars().all())
            
            # Get completions for the target date
            logs_stmt = select(HabitLog).where(
                and_(
                    HabitLog.user_id == user_id,
                    HabitLog.completion_date == target_date
                )
            )
            logs_result = await session.execute(logs_stmt)
            logs = {log.habit_id: log for log in logs_result.scalars().all()}
            
            # Build progress list
            progress = []
            for habit in habits:
                log = logs.get(habit.id)
                progress.append({
                    "habit": habit,
                    "completed": log is not None,
                    "log": log,
                    "xp_earned": log.xp_awarded if log else 0
                })
            
            return progress
    
    async def get_habit_statistics(self, habit_id: int) -> dict:
        """Get statistics for a specific habit.
        
        Args:
            habit_id: Habit ID
            
        Returns:
            Dict with statistics
        """
        async with self.db_manager.get_session() as session:
            # Get habit info
            habit = await session.get(Habit, habit_id)
            if not habit:
                raise ValueError(f"Habit with ID {habit_id} not found")
            
            # Count total completions
            total_stmt = select(func.count(HabitLog.id)).where(HabitLog.habit_id == habit_id)
            total_result = await session.execute(total_stmt)
            total_completions = total_result.scalar()
            
            # Count unique users
            users_stmt = select(func.count(func.distinct(HabitLog.user_id))).where(HabitLog.habit_id == habit_id)
            users_result = await session.execute(users_stmt)
            unique_users = users_result.scalar()
            
            # Get recent activity (last 7 days)
            recent_stmt = select(func.count(HabitLog.id)).where(
                and_(
                    HabitLog.habit_id == habit_id,
                    HabitLog.completion_date >= date.today().replace(day=date.today().day - 7)
                )
            )
            recent_result = await session.execute(recent_stmt)
            recent_completions = recent_result.scalar()
            
            return {
                "habit": habit,
                "total_completions": total_completions,
                "unique_users": unique_users,
                "recent_completions": recent_completions,
                "average_per_user": total_completions / unique_users if unique_users > 0 else 0
            }
    
    async def deactivate_habit(self, habit_id: int) -> bool:
        """Deactivate a habit (soft delete).
        
        Args:
            habit_id: Habit ID
            
        Returns:
            True if habit was deactivated, False if not found
        """
        async with self.db_manager.get_session() as session:
            habit = await session.get(Habit, habit_id)
            if not habit:
                return False
            
            habit.is_active = False
            await session.commit()
            
            logger.info(f"Deactivated habit: {habit.name}")
            return True