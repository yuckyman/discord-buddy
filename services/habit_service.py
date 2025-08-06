"""
Habit Service for Discord Habit Bot.

Handles habit definitions, logging completions, and tracking progress.
Enhanced with natural language processing for dynamic habit management.
"""

import logging
import os
import re
from datetime import datetime, date, time
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy import select, and_, func, desc
from sqlalchemy.exc import IntegrityError
from models import Habit, HabitLog, User, PromptSchedule
from database import DatabaseManager

logger = logging.getLogger(__name__)


class HabitService:
    """Service for managing habits and habit logging."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        
        # Natural language patterns for habit creation
        self.habit_patterns = [
            # "add habit meditation 20 minutes daily at 7am for mindfulness"
            r'add habit\s+(?P<name>[^,]+?)(?:\s+(?P<duration>\d+\s*(?:min|minutes|hour|hours|sec|seconds)))?(?:\s+(?P<frequency>daily|weekly|monthly))?(?:\s+at\s+(?P<time>\d{1,2}(?::\d{2})?\s*(?:am|pm)))?(?:\s+for\s+(?P<description>.+))?',
            
            # "create habit read for 30 minutes"
            r'create habit\s+(?P<name>[^,]+?)(?:\s+for\s+(?P<duration>\d+\s*(?:min|minutes|hour|hours)))?(?:\s+(?P<description>.+))?',
            
            # "new habit: exercise (15 xp) - workout routine"
            r'new habit:\s*(?P<name>[^(]+?)(?:\s*\((?P<xp>\d+)\s*xp\))?(?:\s*-\s*(?P<description>.+))?',
            
            # "habit: drink water every 2 hours"
            r'habit:\s*(?P<name>[^,]+?)(?:\s+every\s+(?P<interval>\d+\s*(?:hours?|minutes?)))?(?:\s*-\s*(?P<description>.+))?',
        ]
        
        # Time parsing patterns
        self.time_patterns = [
            r'(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*(?P<period>am|pm)',
            r'(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?',
        ]
        
        # XP calculation based on keywords
        self.xp_keywords = {
            'exercise': 15, 'workout': 15, 'gym': 15, 'run': 20, 'walk': 10,
            'meditation': 12, 'mindfulness': 12, 'breathe': 8,
            'read': 10, 'study': 15, 'learn': 12, 'practice': 10,
            'water': 5, 'hydrate': 5, 'drink': 5,
            'sleep': 10, 'rest': 8, 'nap': 5,
            'clean': 8, 'organize': 10, 'tidy': 6,
            'write': 12, 'journal': 10, 'blog': 15,
            'code': 20, 'program': 20, 'develop': 18,
            'cook': 12, 'meal': 10, 'nutrition': 8,
        }
    
    def _parse_time_string(self, time_str: str) -> Optional[time]:
        """Parse natural language time string into time object."""
        if not time_str:
            return None
        
        time_str = time_str.lower().strip()
        
        for pattern in self.time_patterns:
            match = re.search(pattern, time_str)
            if match:
                hour = int(match.group('hour'))
                minute = int(match.group('minute')) if match.group('minute') else 0
                period = match.group('period') if 'period' in match.groupdict() else None
                
                # Convert to 24-hour format
                if period == 'pm' and hour != 12:
                    hour += 12
                elif period == 'am' and hour == 12:
                    hour = 0
                
                try:
                    return time(hour, minute)
                except ValueError:
                    continue
        
        return None
    
    def _calculate_xp_from_name(self, name: str, duration_str: Optional[str] = None) -> int:
        """Calculate base XP based on habit name and duration."""
        base_xp = 10  # Default XP
        
        name_lower = name.lower()
        
        # Check for keywords in habit name
        for keyword, xp in self.xp_keywords.items():
            if keyword in name_lower:
                base_xp = max(base_xp, xp)
                break
        
        # Adjust for duration if provided
        if duration_str:
            duration_match = re.search(r'(\d+)\s*(min|minutes|hour|hours)', duration_str.lower())
            if duration_match:
                amount = int(duration_match.group(1))
                unit = duration_match.group(2)
                
                if 'hour' in unit:
                    # More XP for longer activities
                    base_xp += amount * 5
                elif 'min' in unit:
                    if amount >= 30:
                        base_xp += 5
                    elif amount >= 60:
                        base_xp += 10
        
        return min(base_xp, 50)  # Cap at 50 XP
    
    def _extract_category_from_name(self, name: str) -> Optional[str]:
        """Extract category from habit name based on keywords."""
        name_lower = name.lower()
        
        categories = {
            'fitness': ['exercise', 'workout', 'gym', 'run', 'walk', 'yoga', 'swim'],
            'wellness': ['meditation', 'mindfulness', 'breathe', 'sleep', 'rest', 'water', 'hydrate'],
            'learning': ['read', 'study', 'learn', 'practice', 'course', 'book'],
            'productivity': ['code', 'program', 'write', 'work', 'project', 'plan'],
            'lifestyle': ['clean', 'organize', 'cook', 'meal', 'hobby'],
            'social': ['call', 'meet', 'friend', 'family', 'connect'],
        }
        
        for category, keywords in categories.items():
            if any(keyword in name_lower for keyword in keywords):
                return category
        
        return 'general'
    
    async def parse_and_create_habit(self, text: str, user_id: int) -> Tuple[Optional[Habit], Optional[PromptSchedule], str]:
        """Parse natural language text and create habit with optional scheduling.
        
        Args:
            text: Natural language habit description
            user_id: User ID for ownership tracking
            
        Returns:
            Tuple of (Habit, PromptSchedule, status_message)
        """
        text = text.strip()
        
        for pattern in self.habit_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groupdict()
                
                # Extract habit details
                name = groups.get('name', '').strip()
                if not name:
                    continue
                
                description = groups.get('description', '').strip() or None
                duration = groups.get('duration', '').strip() or None
                frequency = groups.get('frequency', 'daily').strip()
                time_str = groups.get('time', '').strip() or None
                explicit_xp = groups.get('xp')
                
                # Calculate XP
                if explicit_xp:
                    base_xp = int(explicit_xp)
                else:
                    base_xp = self._calculate_xp_from_name(name, duration)
                
                # Determine category
                category = self._extract_category_from_name(name)
                
                # Create habit
                try:
                    habit = await self.create_habit(
                        name=name,
                        description=description,
                        base_xp=base_xp,
                        category=category
                    )
                    
                    prompt_schedule = None
                    status_parts = [f"✅ Created habit: **{name}** ({base_xp} XP)"]
                    
                    if category:
                        status_parts.append(f"Category: {category}")
                    
                    # Create prompt schedule if time is specified
                    if time_str:
                        parsed_time = self._parse_time_string(time_str)
                        if parsed_time:
                            # Convert frequency to cron expression
                            cron_expr = self._frequency_to_cron(frequency, parsed_time)
                            
                            prompt_text = f"🌱 Time for your **{name}** habit! React with ✅ when complete."
                            if duration:
                                prompt_text += f" (Target: {duration})"
                            
                            prompt_schedule = await self._create_prompt_schedule(
                                name=f"{name} reminder",
                                prompt_text=prompt_text,
                                cron_expression=cron_expr
                            )
                            
                            status_parts.append(f"Scheduled {frequency} at {time_str}")
                    
                    return habit, prompt_schedule, " | ".join(status_parts)
                    
                except Exception as e:
                    logger.error(f"Failed to create habit from text '{text}': {e}")
                    return None, None, f"❌ Failed to create habit: {str(e)}"
        
        # No pattern matched
        return None, None, "❌ Could not parse habit. Try formats like:\n" \
                          "• `add habit meditation 20 minutes daily at 7am for mindfulness`\n" \
                          "• `create habit exercise for 30 minutes`\n" \
                          "• `new habit: read (15 xp) - daily reading`\n" \
                          "• `habit: drink water every 2 hours`"
    
    def _frequency_to_cron(self, frequency: str, target_time: time) -> str:
        """Convert frequency and time to cron expression."""
        minute = target_time.minute
        hour = target_time.hour
        
        if frequency.lower() == 'daily':
            return f"{minute} {hour} * * *"
        elif frequency.lower() == 'weekly':
            return f"{minute} {hour} * * 1"  # Monday
        elif frequency.lower() == 'monthly':
            return f"{minute} {hour} 1 * *"  # 1st of month
        else:
            return f"{minute} {hour} * * *"  # Default to daily
    
    async def _create_prompt_schedule(self, name: str, prompt_text: str, cron_expression: str) -> PromptSchedule:
        """Create a prompt schedule."""
        async with self.db_manager.get_session() as session:
            prompt_schedule = PromptSchedule(
                name=name,
                prompt_text=prompt_text,
                cron_expression=cron_expression,
                timezone=os.getenv("TIMEZONE", "UTC")  # Use environment variable or default to UTC
            )
            session.add(prompt_schedule)
            await session.commit()
            await session.refresh(prompt_schedule)
            
            logger.info(f"Created prompt schedule: {name} ({cron_expression})")
            return prompt_schedule
    
    async def list_habits_with_schedules(self) -> List[Dict[str, Any]]:
        """Get all habits with their associated prompt schedules."""
        async with self.db_manager.get_session() as session:
            # Get all active habits
            habits_stmt = select(Habit).where(Habit.is_active == True).order_by(Habit.category, Habit.name)
            habits_result = await session.execute(habits_stmt)
            habits = list(habits_result.scalars().all())
            
            # Get all active prompt schedules
            schedules_stmt = select(PromptSchedule).where(PromptSchedule.is_active == True).order_by(PromptSchedule.name)
            schedules_result = await session.execute(schedules_stmt)
            schedules = list(schedules_result.scalars().all())
            
            # Group by category
            categorized = {}
            for habit in habits:
                category = habit.category or 'general'
                if category not in categorized:
                    categorized[category] = []
                
                # Find matching schedules (simple name matching)
                matching_schedules = [s for s in schedules if habit.name.lower() in s.name.lower()]
                
                categorized[category].append({
                    'habit': habit,
                    'schedules': matching_schedules
                })
            
            return categorized
    
    async def modify_habit_schedule(self, habit_name: str, new_time: str, frequency: str = "daily") -> str:
        """Modify or create schedule for existing habit."""
        # Find habit
        habit = await self.get_habit_by_name(habit_name)
        if not habit:
            return f"❌ Habit '{habit_name}' not found"
        
        # Parse new time
        parsed_time = self._parse_time_string(new_time)
        if not parsed_time:
            return f"❌ Could not parse time '{new_time}'. Try formats like '7am', '14:30', '9:15pm'"
        
        # Create or update schedule
        cron_expr = self._frequency_to_cron(frequency, parsed_time)
        schedule_name = f"{habit.name} reminder"
        
        async with self.db_manager.get_session() as session:
            # Check for existing schedule
            existing_stmt = select(PromptSchedule).where(PromptSchedule.name == schedule_name)
            existing_result = await session.execute(existing_stmt)
            existing_schedule = existing_result.scalar_one_or_none()
            
            if existing_schedule:
                # Update existing schedule
                existing_schedule.cron_expression = cron_expr
                existing_schedule.is_active = True
                await session.commit()
                return f"✅ Updated schedule for **{habit.name}**: {frequency} at {new_time}"
            else:
                # Create new schedule
                prompt_text = f"🌱 Time for your **{habit.name}** habit! React with ✅ when complete."
                await self._create_prompt_schedule(schedule_name, prompt_text, cron_expr)
                return f"✅ Created schedule for **{habit.name}**: {frequency} at {new_time}"

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
    
    def extract_count_from_notes(self, notes: str) -> Optional[int]:
        """Extract numeric count from habit notes.
        
        Examples:
        - "32 push-ups" -> 32
        - "did 45 today" -> 45  
        - "completed 100" -> 100
        - "great workout" -> None
        
        Args:
            notes: The notes string to parse
            
        Returns:
            Extracted count or None if no count found
        """
        if not notes:
            return None
            
        # Patterns to match numbers in notes
        patterns = [
            r'(\d+)\s*push[-\s]?ups?',  # "32 push-ups", "32 pushups"
            r'did\s+(\d+)',             # "did 45"
            r'completed\s+(\d+)',       # "completed 100" 
            r'^(\d+)',                  # "32 today"
            r'(\d+)\s*today',           # "45 today"
            r'(\d+)\s*total',           # "67 total"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, notes.lower())
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
                    
        return None
    
    async def get_habit_count_stats(self, user_id: int, habit_name: str) -> Dict[str, Any]:
        """Get count-based statistics for a habit.
        
        Args:
            user_id: Database user ID
            habit_name: Name of the habit to analyze
            
        Returns:
            Dict with total, average, best, recent counts
        """
        async with self.db_manager.get_session() as session:
            # Get habit
            habit = await self.get_habit_by_name(habit_name)
            if not habit:
                return {"error": f"Habit '{habit_name}' not found"}
            
            # Get all logs for this user and habit
            stmt = select(HabitLog).where(
                and_(
                    HabitLog.user_id == user_id,
                    HabitLog.habit_id == habit.id,
                    HabitLog.notes.isnot(None)
                )
            ).order_by(desc(HabitLog.completion_date))
            
            result = await session.execute(stmt)
            logs = list(result.scalars().all())
            
            if not logs:
                return {"error": f"No logs found for '{habit_name}'"}
            
            # Extract counts from all logs
            counts = []
            recent_logs = []
            
            for log in logs:
                count = self.extract_count_from_notes(log.notes)
                if count is not None:
                    counts.append(count)
                    recent_logs.append({
                        "date": log.completion_date.strftime('%Y-%m-%d'),
                        "count": count,
                        "notes": log.notes
                    })
            
            if not counts:
                return {"error": f"No count data found in logs for '{habit_name}'"}
            
            # Calculate statistics
            total = sum(counts)
            average = total / len(counts)
            best = max(counts)
            worst = min(counts)
            
            return {
                "habit_name": habit_name,
                "total_count": total,
                "average": round(average, 1),
                "best": best,
                "worst": worst,
                "total_sessions": len(counts),
                "recent_logs": recent_logs[:10]  # Last 10 sessions with counts
            }
    
    async def schedule_habit_reminder(self, habit_name: str, cron_expression: str, bot=None) -> PromptSchedule:
        """Schedule a habit reminder using the prompt service.
        
        Args:
            habit_name: Name of the habit to schedule reminders for
            cron_expression: Cron expression for the schedule
            bot: Discord bot instance (optional, will be set by calling service)
            
        Returns:
            The created PromptSchedule object
        """
        try:
            # Get the habit to ensure it exists
            habit = await self.get_habit_by_name(habit_name)
            if not habit:
                raise ValueError(f"Habit '{habit_name}' not found")
            
            # Create prompt text for the habit
            prompt_text = f"🌱 Time for your **{habit_name}** habit!\n\n"
            if habit.description:
                prompt_text += f"*{habit.description}*\n\n"
            prompt_text += f"React with ✅ when you complete this habit to earn {habit.base_xp} XP!"
            
            # Create the prompt schedule using the prompt service
            from services.prompt_service import PromptService
            prompt_service = PromptService(self.db_manager, bot)
            
            schedule = await prompt_service.create_schedule(
                name=f"{habit_name} Reminder",
                prompt_text=prompt_text,
                cron_expression=cron_expression,
                channel_id=None  # Use default channel
            )
            
            logger.info(f"Scheduled habit reminder for '{habit_name}' with cron: {cron_expression}")
            return schedule
            
        except Exception as e:
            logger.error(f"Failed to schedule habit reminder for '{habit_name}': {e}")
            raise