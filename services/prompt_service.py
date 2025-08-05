"""
Prompt Service for Discord Habit Bot.

Handles scheduled prompts, reaction tracking, and automated reminders.
"""

import logging
import os
import asyncio
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, and_, update
from models import PromptSchedule, PromptReaction, User, Habit, HabitLog
from database import DatabaseManager

logger = logging.getLogger(__name__)


class PromptService:
    """Service for managing scheduled prompts and reactions."""
    
    def __init__(self, db_manager: DatabaseManager, bot):
        self.db_manager = db_manager
        self.bot = bot
        self.scheduler = None
        self.scheduled_jobs = {}  # Track active jobs
        
        # Timezone for scheduling (should match environment setting)
        self.timezone = os.getenv("TIMEZONE", "UTC")
    
    async def start_scheduler(self) -> None:
        """Start the APScheduler for handling prompts."""
        try:
            self.scheduler = AsyncIOScheduler(timezone=self.timezone)
            self.scheduler.start()
            
            # Load and schedule existing prompts
            await self._load_scheduled_prompts()
            
            logger.info(f"Prompt scheduler started with timezone: {self.timezone}")
            
        except Exception as e:
            logger.error(f"Failed to start prompt scheduler: {e}")
            raise
    
    async def stop_scheduler(self) -> None:
        """Stop the scheduler gracefully."""
        if self.scheduler:
            self.scheduler.shutdown()
            logger.info("Prompt scheduler stopped")
    
    async def _load_scheduled_prompts(self) -> None:
        """Load all active prompt schedules and add them to the scheduler."""
        try:
            async with self.db_manager.get_session() as session:
                stmt = select(PromptSchedule).where(PromptSchedule.is_active == True)
                result = await session.execute(stmt)
                schedules = list(result.scalars().all())
                
                for schedule in schedules:
                    await self._schedule_prompt(schedule)
                
                logger.info(f"Loaded {len(schedules)} scheduled prompts")
                
        except Exception as e:
            logger.error(f"Error loading scheduled prompts: {e}")
    
    async def _schedule_prompt(self, schedule: PromptSchedule) -> None:
        """Add a single prompt schedule to the scheduler."""
        try:
            # Create cron trigger from the expression
            trigger = CronTrigger.from_crontab(
                schedule.cron_expression, 
                timezone=schedule.timezone or self.timezone
            )
            
            # Add job to scheduler
            job_id = f"prompt_{schedule.id}"
            job = self.scheduler.add_job(
                self._send_scheduled_prompt,
                trigger=trigger,
                args=[schedule.id],
                id=job_id,
                name=f"Prompt: {schedule.name}",
                replace_existing=True
            )
            
            self.scheduled_jobs[schedule.id] = job
            
            logger.info(f"Scheduled prompt: {schedule.name} ({schedule.cron_expression})")
            
        except Exception as e:
            logger.error(f"Error scheduling prompt {schedule.id}: {e}")
    
    async def _send_scheduled_prompt(self, schedule_id: int) -> None:
        """Send a scheduled prompt to Discord."""
        try:
            async with self.db_manager.get_session() as session:
                schedule = await session.get(PromptSchedule, schedule_id)
                if not schedule or not schedule.is_active:
                    logger.warning(f"Prompt schedule {schedule_id} not found or inactive")
                    return
                
                # Determine target channel
                channel_id = schedule.channel_id
                if not channel_id:
                    # Use first available channel if no specific channel set
                    # In production, you'd want to configure a default channel
                    for guild in self.bot.guilds:
                        for ch in guild.text_channels:
                            if ch.permissions_for(guild.me).send_messages:
                                channel_id = str(ch.id)
                                break
                        if channel_id:
                            break
                
                if not channel_id:
                    logger.error("No suitable channel found for prompt")
                    return
                
                # Get Discord channel
                channel = self.bot.get_channel(int(channel_id))
                if not channel:
                    logger.error(f"Channel {channel_id} not found")
                    return
                
                # Create embed for the prompt
                embed = discord.Embed(
                    title="🌱 Habit Reminder",
                    description=schedule.prompt_text,
                    color=discord.Color.green(),
                    timestamp=datetime.utcnow()
                )
                
                embed.add_field(
                    name="How to respond",
                    value="React with ✅ when you complete this habit!",
                    inline=False
                )
                
                embed.set_footer(text=f"Scheduled: {schedule.name}")
                
                # Send the message
                message = await channel.send(embed=embed)
                
                # Add reaction for easy interaction
                await message.add_reaction("✅")
                
                logger.info(f"Sent scheduled prompt: {schedule.name} to {channel.name}")
                
        except Exception as e:
            logger.error(f"Error sending scheduled prompt {schedule_id}: {e}")
    
    async def handle_reaction(self, payload: discord.RawReactionActionEvent) -> None:
        """Handle reaction to a prompt message."""
        try:
            # Only handle checkmark reactions
            if str(payload.emoji) != "✅":
                return
            
            # Get the message to check if it's a prompt
            channel = self.bot.get_channel(payload.channel_id)
            if not channel:
                return
            
            try:
                message = await channel.fetch_message(payload.message_id)
            except discord.NotFound:
                return
            
            # Check if message is from the bot and has prompt embed
            if message.author.id != self.bot.user.id:
                return
            
            if not message.embeds or "Habit Reminder" not in message.embeds[0].title:
                return
            
            # Get user info
            user_discord_id = str(payload.user_id)
            user_obj = self.bot.get_user(payload.user_id)
            if not user_obj:
                return
            
            username = user_obj.display_name
            
            # Get or create user in database
            from services.user_service import UserService
            user_service = UserService(self.db_manager)
            user = await user_service.get_or_create_user(user_discord_id, username)
            
            # Record the reaction
            await self._record_prompt_reaction(
                user.id,
                str(payload.message_id),
                str(payload.channel_id),
                "✅"
            )
            
            # Try to auto-log habits based on prompt content
            await self._process_prompt_reaction(user, message.embeds[0])
            
            logger.info(f"Processed prompt reaction from {username}")
            
        except Exception as e:
            logger.error(f"Error handling reaction: {e}")
    
    async def _record_prompt_reaction(self, user_id: int, message_id: str, 
                                    channel_id: str, emoji: str) -> None:
        """Record a prompt reaction in the database."""
        async with self.db_manager.get_session() as session:
            # Check if reaction already recorded
            existing_stmt = select(PromptReaction).where(
                and_(
                    PromptReaction.user_id == user_id,
                    PromptReaction.message_id == message_id,
                    PromptReaction.reaction_emoji == emoji
                )
            )
            existing_result = await session.execute(existing_stmt)
            if existing_result.scalar_one_or_none():
                return  # Already recorded
            
            # Create new reaction record
            reaction = PromptReaction(
                user_id=user_id,
                prompt_schedule_id=1,  # TODO: Extract from message or default
                message_id=message_id,
                channel_id=channel_id,
                reaction_emoji=emoji,
                processed=False
            )
            
            session.add(reaction)
            await session.commit()
    
    async def _process_prompt_reaction(self, user: User, embed: discord.Embed) -> None:
        """Process a prompt reaction and attempt to log relevant habits."""
        try:
            # Extract habit keywords from the prompt text
            prompt_text = embed.description.lower()
            
            # Simple keyword matching to find relevant habits
            from services.habit_service import HabitService
            habit_service = HabitService(self.db_manager)
            
            # Get all habits
            all_habits = await habit_service.get_all_habits()
            
            # Find habits mentioned in the prompt
            matched_habits = []
            for habit in all_habits:
                if habit.name.lower() in prompt_text:
                    matched_habits.append(habit)
            
            # If we found matching habits, log them
            if matched_habits:
                for habit in matched_habits:
                    try:
                        habit_log, is_new = await habit_service.log_habit_completion(
                            user.id, habit.id, 
                            notes="Completed via prompt reaction",
                            source="reaction"
                        )
                        
                        if is_new:
                            # Update user stats
                            from services.user_service import UserService
                            user_service = UserService(self.db_manager)
                            await user_service.update_user_stats(
                                user.id, xp_delta=habit_log.xp_awarded
                            )
                            
                            # Update streaks
                            from services.streak_service import StreakService
                            streak_service = StreakService(self.db_manager)
                            await streak_service.update_streak(user.id, habit.id)
                            
                            logger.info(f"Auto-logged habit {habit.name} for user {user.username} via reaction")
                            
                    except Exception as e:
                        logger.error(f"Error auto-logging habit {habit.name}: {e}")
            else:
                # Generic habit completion - look for a default habit or create one
                logger.debug(f"No specific habits matched for prompt reaction from {user.username}")
        
        except Exception as e:
            logger.error(f"Error processing prompt reaction: {e}")
    
    async def create_schedule(self, name: str, prompt_text: str, cron_expression: str,
                            channel_id: Optional[str] = None, 
                            timezone: Optional[str] = None) -> PromptSchedule:
        """Create a new prompt schedule."""
        async with self.db_manager.get_session() as session:
            schedule = PromptSchedule(
                name=name,
                prompt_text=prompt_text,
                cron_expression=cron_expression,
                channel_id=channel_id,
                timezone=timezone or self.timezone
            )
            
            session.add(schedule)
            await session.commit()
            await session.refresh(schedule)
            
            # Add to scheduler if scheduler is running
            if self.scheduler and self.scheduler.running:
                await self._schedule_prompt(schedule)
            
            logger.info(f"Created prompt schedule: {name}")
            return schedule
    
    async def update_schedule(self, schedule_id: int, **updates) -> bool:
        """Update an existing prompt schedule."""
        async with self.db_manager.get_session() as session:
            schedule = await session.get(PromptSchedule, schedule_id)
            if not schedule:
                return False
            
            # Update fields
            for field, value in updates.items():
                if hasattr(schedule, field):
                    setattr(schedule, field, value)
            
            await session.commit()
            
            # Reschedule if scheduler is running
            if self.scheduler and self.scheduler.running:
                # Remove old job
                if schedule_id in self.scheduled_jobs:
                    try:
                        self.scheduler.remove_job(f"prompt_{schedule_id}")
                        del self.scheduled_jobs[schedule_id]
                    except:
                        pass
                
                # Add updated job if still active
                if schedule.is_active:
                    await self._schedule_prompt(schedule)
            
            logger.info(f"Updated prompt schedule {schedule_id}")
            return True
    
    async def delete_schedule(self, schedule_id: int) -> bool:
        """Delete a prompt schedule."""
        async with self.db_manager.get_session() as session:
            schedule = await session.get(PromptSchedule, schedule_id)
            if not schedule:
                return False
            
            # Remove from scheduler
            if self.scheduler and schedule_id in self.scheduled_jobs:
                try:
                    self.scheduler.remove_job(f"prompt_{schedule_id}")
                    del self.scheduled_jobs[schedule_id]
                except:
                    pass
            
            # Mark as inactive instead of deleting (soft delete)
            schedule.is_active = False
            await session.commit()
            
            logger.info(f"Deleted prompt schedule {schedule_id}")
            return True
    
    async def get_all_schedules(self, active_only: bool = True) -> List[PromptSchedule]:
        """Get all prompt schedules."""
        async with self.db_manager.get_session() as session:
            if active_only:
                stmt = select(PromptSchedule).where(PromptSchedule.is_active == True)
            else:
                stmt = select(PromptSchedule)
            
            stmt = stmt.order_by(PromptSchedule.name)
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    async def get_user_reactions(self, user_id: int, limit: int = 50) -> List[PromptReaction]:
        """Get recent prompt reactions for a user."""
        async with self.db_manager.get_session() as session:
            stmt = select(PromptReaction).where(
                PromptReaction.user_id == user_id
            ).order_by(PromptReaction.reacted_at.desc()).limit(limit)
            
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    async def get_prompt_statistics(self) -> Dict[str, Any]:
        """Get statistics about prompt usage."""
        async with self.db_manager.get_session() as session:
            # Total active schedules
            schedules_stmt = select(PromptSchedule).where(PromptSchedule.is_active == True)
            schedules_result = await session.execute(schedules_stmt)
            active_schedules = len(list(schedules_result.scalars().all()))
            
            # Total reactions
            from sqlalchemy import func
            reactions_stmt = select(func.count(PromptReaction.id))
            reactions_result = await session.execute(reactions_stmt)
            total_reactions = reactions_result.scalar()
            
            # Reactions by day (last 7 days)
            # This would require more complex date filtering
            
            return {
                "active_schedules": active_schedules,
                "total_reactions": total_reactions,
                "scheduler_running": self.scheduler.running if self.scheduler else False,
                "active_jobs": len(self.scheduled_jobs)
            }