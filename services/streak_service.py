"""
Streak Service for Discord Habit Bot.

Handles streak tracking, milestone bonuses, and streak-related rewards.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import select, and_, or_, func
from models import Streak, HabitLog, User, Habit
from database import DatabaseManager

logger = logging.getLogger(__name__)


class StreakService:
    """Service for managing habit streaks and milestones."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        
        # Streak milestone thresholds for bonus rewards
        self.streak_milestones = [3, 7, 14, 30, 60, 100, 365]
        
        # Bonus XP multipliers for streak milestones
        self.streak_bonuses = {
            3: 1.2,    # 20% bonus for 3-day streak
            7: 1.5,    # 50% bonus for 7-day streak
            14: 2.0,   # 100% bonus for 2-week streak
            30: 2.5,   # 150% bonus for monthly streak
            60: 3.0,   # 200% bonus for 2-month streak
            100: 4.0,  # 300% bonus for 100-day streak
            365: 5.0,  # 400% bonus for yearly streak
        }
    
    async def update_streak(self, user_id: int, habit_id: int) -> Optional[Dict[str, Any]]:
        """Update streak for a user's habit completion.
        
        Args:
            user_id: Database user ID
            habit_id: Habit ID
            
        Returns:
            Dict with streak info and any milestone rewards, or None if error
        """
        try:
            async with self.db_manager.get_session() as session:
                # Get or create streak record
                streak_stmt = select(Streak).where(
                    and_(
                        Streak.user_id == user_id,
                        Streak.habit_id == habit_id
                    )
                )
                streak_result = await session.execute(streak_stmt)
                streak = streak_result.scalar_one_or_none()
                
                today = date.today()
                yesterday = today - timedelta(days=1)
                
                if not streak:
                    # Create new streak
                    streak = Streak(
                        user_id=user_id,
                        habit_id=habit_id,
                        current_streak=1,
                        longest_streak=1,
                        last_completion_date=today,
                        last_milestone_reward=0
                    )
                    session.add(streak)
                    await session.commit()
                    await session.refresh(streak)
                    
                    logger.info(f"Started new streak for user {user_id}, habit {habit_id}")
                    return {
                        "current_streak": 1,
                        "longest_streak": 1,
                        "is_new_streak": True,
                        "milestone_reached": False,
                        "milestone_bonus": None
                    }
                
                # Check if this is a continuation of the streak
                if streak.last_completion_date == today:
                    # Already completed today, no streak update needed
                    return {
                        "current_streak": streak.current_streak,
                        "longest_streak": streak.longest_streak,
                        "is_new_streak": False,
                        "milestone_reached": False,
                        "milestone_bonus": None
                    }
                elif streak.last_completion_date == yesterday:
                    # Continuing streak
                    old_streak = streak.current_streak
                    streak.current_streak += 1
                    streak.last_completion_date = today
                    
                    # Update longest streak if needed
                    if streak.current_streak > streak.longest_streak:
                        streak.longest_streak = streak.current_streak
                    
                    # Check for milestone
                    milestone_info = await self._check_milestone_reward(
                        session, streak, user_id, habit_id, old_streak
                    )
                    
                    await session.commit()
                    
                    logger.info(f"Extended streak for user {user_id}, habit {habit_id}: {streak.current_streak} days")
                    
                    return {
                        "current_streak": streak.current_streak,
                        "longest_streak": streak.longest_streak,
                        "is_new_streak": False,
                        "milestone_reached": milestone_info["milestone_reached"],
                        "milestone_bonus": milestone_info["milestone_bonus"]
                    }
                else:
                    # Streak broken, reset
                    old_longest = streak.longest_streak
                    streak.current_streak = 1
                    streak.last_completion_date = today
                    streak.last_milestone_reward = 0  # Reset milestone tracking
                    
                    await session.commit()
                    
                    logger.info(f"Reset broken streak for user {user_id}, habit {habit_id}. Previous: {old_longest} days")
                    
                    return {
                        "current_streak": 1,
                        "longest_streak": old_longest,
                        "is_new_streak": True,
                        "milestone_reached": False,
                        "milestone_bonus": None,
                        "streak_broken": True,
                        "previous_streak": old_longest
                    }
                    
        except Exception as e:
            logger.error(f"Error updating streak: {e}")
            return None
    
    async def _check_milestone_reward(self, session, streak: Streak, user_id: int, 
                                    habit_id: int, old_streak: int) -> Dict[str, Any]:
        """Check if streak reached a milestone and award bonus if applicable."""
        current_streak = streak.current_streak
        
        # Find the highest milestone reached
        milestone_reached = None
        for milestone in self.streak_milestones:
            if current_streak >= milestone and old_streak < milestone:
                # New milestone reached
                milestone_reached = milestone
                break
        
        if not milestone_reached:
            return {
                "milestone_reached": False,
                "milestone_bonus": None
            }
        
        # Award milestone bonus
        if milestone_reached > streak.last_milestone_reward:
            # Get habit for base XP calculation
            habit = await session.get(Habit, habit_id)
            if habit:
                bonus_multiplier = self.streak_bonuses.get(milestone_reached, 1.0)
                bonus_xp = int(habit.base_xp * bonus_multiplier)
                
                # Update user XP
                user = await session.get(User, user_id)
                if user:
                    old_level = user.level
                    user.total_xp += bonus_xp
                    user.level = max(1, int((user.total_xp / 100) ** 0.5) + 1)
                    
                    # Update streak milestone tracking
                    streak.last_milestone_reward = milestone_reached
                    
                    logger.info(f"Milestone bonus awarded: {bonus_xp} XP for {milestone_reached}-day streak")
                    
                    return {
                        "milestone_reached": True,
                        "milestone_bonus": {
                            "days": milestone_reached,
                            "bonus_xp": bonus_xp,
                            "multiplier": bonus_multiplier,
                            "leveled_up": user.level > old_level,
                            "new_level": user.level if user.level > old_level else None
                        }
                    }
        
        return {
            "milestone_reached": False,
            "milestone_bonus": None
        }
    
    async def get_user_streak(self, user_id: int, habit_id: int) -> Optional[Streak]:
        """Get streak info for a specific user and habit."""
        async with self.db_manager.get_session() as session:
            stmt = select(Streak).where(
                and_(
                    Streak.user_id == user_id,
                    Streak.habit_id == habit_id
                )
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
    
    async def get_user_all_streaks(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all streak information for a user."""
        async with self.db_manager.get_session() as session:
            # Join streaks with habits to get habit names
            stmt = select(Streak, Habit).join(
                Habit, Streak.habit_id == Habit.id
            ).where(
                and_(
                    Streak.user_id == user_id,
                    Habit.is_active == True
                )
            ).order_by(Streak.current_streak.desc())
            
            result = await session.execute(stmt)
            streaks_data = []
            
            for streak, habit in result.all():
                # Check if streak is still active (completed recently)
                today = date.today()
                is_active = (
                    streak.last_completion_date == today or 
                    streak.last_completion_date == today - timedelta(days=1)
                )
                
                # Calculate days since last completion
                days_since = (today - streak.last_completion_date).days if streak.last_completion_date else None
                
                # Determine next milestone
                next_milestone = None
                for milestone in self.streak_milestones:
                    if milestone > streak.current_streak:
                        next_milestone = milestone
                        break
                
                streaks_data.append({
                    "habit": habit,
                    "current_streak": streak.current_streak,
                    "longest_streak": streak.longest_streak,
                    "last_completion_date": streak.last_completion_date,
                    "is_active": is_active,
                    "days_since_last": days_since,
                    "next_milestone": next_milestone,
                    "last_milestone_reward": streak.last_milestone_reward
                })
            
            return streaks_data
    
    async def get_leaderboard_streaks(self, habit_id: Optional[int] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get leaderboard of current streaks.
        
        Args:
            habit_id: Optional specific habit ID, or None for all habits
            limit: Number of results to return
            
        Returns:
            List of top streak performers
        """
        async with self.db_manager.get_session() as session:
            # Base query joining streaks with users and habits
            stmt = select(Streak, User, Habit).join(
                User, Streak.user_id == User.id
            ).join(
                Habit, Streak.habit_id == Habit.id
            ).where(
                and_(
                    User.is_active == True,
                    Habit.is_active == True,
                    Streak.current_streak > 0
                )
            )
            
            # Filter by specific habit if provided
            if habit_id:
                stmt = stmt.where(Streak.habit_id == habit_id)
            
            # Order by current streak and limit results
            stmt = stmt.order_by(Streak.current_streak.desc()).limit(limit)
            
            result = await session.execute(stmt)
            leaderboard = []
            
            for streak, user, habit in result.all():
                # Check if streak is still active
                today = date.today()
                is_active = (
                    streak.last_completion_date == today or 
                    streak.last_completion_date == today - timedelta(days=1)
                )
                
                # Only include active streaks in leaderboard
                if is_active:
                    leaderboard.append({
                        "user": user,
                        "habit": habit,
                        "current_streak": streak.current_streak,
                        "longest_streak": streak.longest_streak,
                        "last_completion_date": streak.last_completion_date
                    })
            
            return leaderboard
    
    async def get_streak_statistics(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get streak statistics, optionally for a specific user."""
        async with self.db_manager.get_session() as session:
            base_filter = []
            if user_id:
                base_filter.append(Streak.user_id == user_id)
            
            # Total active streaks
            active_stmt = select(func.count(Streak.id)).where(
                and_(
                    Streak.current_streak > 0,
                    *base_filter
                )
            )
            active_result = await session.execute(active_stmt)
            active_streaks = active_result.scalar()
            
            # Average current streak
            avg_stmt = select(func.avg(Streak.current_streak)).where(
                and_(
                    Streak.current_streak > 0,
                    *base_filter
                )
            )
            avg_result = await session.execute(avg_stmt)
            avg_streak = avg_result.scalar() or 0
            
            # Longest streak overall
            max_stmt = select(func.max(Streak.longest_streak)).where(
                and_(*base_filter) if base_filter else True
            )
            max_result = await session.execute(max_stmt)
            longest_streak = max_result.scalar() or 0
            
            # Count of users with different milestone levels
            milestone_counts = {}
            for milestone in self.streak_milestones:
                milestone_stmt = select(func.count(func.distinct(Streak.user_id))).where(
                    and_(
                        Streak.current_streak >= milestone,
                        *base_filter
                    )
                )
                milestone_result = await session.execute(milestone_stmt)
                milestone_counts[f"{milestone}_day_club"] = milestone_result.scalar()
            
            return {
                "active_streaks": active_streaks,
                "average_streak": round(avg_streak, 1),
                "longest_streak": longest_streak,
                "milestone_counts": milestone_counts
            }
    
    async def find_broken_streaks(self, days_threshold: int = 2) -> List[Dict[str, Any]]:
        """Find streaks that should be marked as broken.
        
        Args:
            days_threshold: Number of days since last completion to consider broken
            
        Returns:
            List of broken streak info
        """
        async with self.db_manager.get_session() as session:
            cutoff_date = date.today() - timedelta(days=days_threshold)
            
            stmt = select(Streak, User, Habit).join(
                User, Streak.user_id == User.id
            ).join(
                Habit, Streak.habit_id == Habit.id
            ).where(
                and_(
                    Streak.current_streak > 0,
                    Streak.last_completion_date < cutoff_date,
                    User.is_active == True,
                    Habit.is_active == True
                )
            )
            
            result = await session.execute(stmt)
            broken_streaks = []
            
            for streak, user, habit in result.all():
                days_since = (date.today() - streak.last_completion_date).days
                
                broken_streaks.append({
                    "streak": streak,
                    "user": user,
                    "habit": habit,
                    "days_since_last": days_since,
                    "lost_streak": streak.current_streak
                })
            
            return broken_streaks
    
    async def reset_broken_streaks(self, days_threshold: int = 2) -> int:
        """Reset streaks that have been broken for too long.
        
        Args:
            days_threshold: Days since last completion to consider broken
            
        Returns:
            Number of streaks reset
        """
        broken_streaks = await self.find_broken_streaks(days_threshold)
        
        if not broken_streaks:
            return 0
        
        async with self.db_manager.get_session() as session:
            reset_count = 0
            
            for broken in broken_streaks:
                streak = broken["streak"]
                user = broken["user"]
                habit = broken["habit"]
                
                # Reset the streak
                streak.current_streak = 0
                streak.last_milestone_reward = 0
                
                logger.info(f"Reset broken streak: {user.username} - {habit.name} ({broken['lost_streak']} days lost)")
                reset_count += 1
            
            await session.commit()
            
        logger.info(f"Reset {reset_count} broken streaks")
        return reset_count