"""
Startup Habits Module for Discord Habit Bot.

Handles creating default habits and sending startup notifications.
"""

import logging
import asyncio
from typing import List, Tuple
from services.habit_service import HabitService
from services.user_service import UserService
from database import db_manager

logger = logging.getLogger(__name__)


class StartupHabits:
    """Manages startup habits and notifications."""
    
    def __init__(self, bot):
        self.bot = bot
        self.habit_service = HabitService(db_manager)
        self.user_service = UserService(db_manager)
        
        # Default habits to create on first run
        self.default_habits = [
            ("Morning Meditation", "Start your day with mindfulness", 15, "wellness", "0 7 * * *"),
            ("Daily Exercise", "Physical activity for health", 20, "fitness", "0 18 * * *"),
            ("Read for Learning", "Expand your knowledge", 12, "learning", "0 20 * * *"),
            ("Drink Water", "Stay hydrated throughout the day", 5, "wellness", "0 */2 * * *"),
            ("Sleep Early", "Good sleep hygiene", 10, "wellness", "0 22 * * *"),
            ("Gratitude Journal", "Write 3 things you're grateful for", 8, "wellness", "0 21 * * *"),
            ("Code Review", "Review and improve coding skills", 15, "learning", "0 9 * * 1,2,3,4,5"),
        ]
    
    async def send_startup_notification(self, channel_id: int = None) -> bool:
        """Send startup notification to Discord channel."""
        try:
            # Find the appropriate channel
            channel = None
            if channel_id:
                channel = self.bot.get_channel(channel_id)
            else:
                # Use first available text channel
                for guild in self.bot.guilds:
                    for ch in guild.text_channels:
                        if ch.permissions_for(guild.me).send_messages:
                            channel = ch
                            break
                    if channel:
                        break
            
            if not channel:
                logger.warning("No suitable channel found for startup notification")
                return False
            
            startup_message = """🚀 **Habit Bot Online & Ready!**

Welcome back, habit builders! I'm here to help you level up your life.

🎯 **Quick Start:**
• `!create meditation 10 minutes daily` - Create new habit
• `!today` - Check today's progress  
• `!stats` - View your achievements
• `!obsidian_health` - Check Obsidian sync

💡 **New Features:**
• Obsidian integration for daily notes
• Advanced gamification with XP & rewards
• Natural language habit creation

Let's make today legendary! What habit will you tackle first? 💪"""

            await channel.send(startup_message)
            logger.info(f"Startup notification sent to {channel.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send startup notification: {e}")
            return False
    
    async def create_default_habits(self, user_id: int = None) -> List[str]:
        """Create default habits for new users or system."""
        created_habits = []
        
        try:
            for name, description, xp, category, schedule in self.default_habits:
                try:
                    # Create the habit
                    habit = await self.habit_service.create_habit(
                        name=name,
                        description=description,
                        base_xp=xp,
                        category=category
                    )
                    
                    if habit:
                        created_habits.append(name)
                        logger.info(f"Created default habit: {name}")
                        
                        # Schedule if it's a system-wide habit
                        if not user_id and schedule:
                            try:
                                await self.habit_service.schedule_habit_reminder(
                                    habit_name=name,
                                    cron_expression=schedule
                                )
                                logger.info(f"Scheduled habit reminder: {name} ({schedule})")
                            except Exception as e:
                                logger.warning(f"Failed to schedule {name}: {e}")
                    
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        logger.warning(f"Failed to create habit {name}: {e}")
                    # Habit already exists, which is fine
                    
        except Exception as e:
            logger.error(f"Error creating default habits: {e}")
        
        return created_habits
    
    async def setup_new_user(self, discord_id: str, username: str) -> dict:
        """Set up a new user with default habits and welcome message."""
        try:
            # Create user if not exists
            user = await self.user_service.get_or_create_user(discord_id, username)
            
            # Create default habits for this user
            created_habits = await self.create_default_habits(user.id)
            
            result = {
                "user_id": user.id,
                "created_habits": created_habits,
                "total_habits": len(created_habits)
            }
            
            logger.info(f"Set up new user {username} with {len(created_habits)} default habits")
            return result
            
        except Exception as e:
            logger.error(f"Failed to setup new user {username}: {e}")
            return {"error": str(e)}
    
    async def check_and_create_system_habits(self) -> int:
        """Check if system needs default habits and create them."""
        try:
            # Check if we have any habits in the system
            existing_habits = await self.habit_service.get_all_habits()
            
            if len(existing_habits) == 0:
                logger.info("No habits found in system, creating defaults...")
                created_habits = await self.create_default_habits()
                logger.info(f"Created {len(created_habits)} default system habits")
                return len(created_habits)
            else:
                logger.info(f"System already has {len(existing_habits)} habits")
                return 0
                
        except Exception as e:
            logger.error(f"Error checking system habits: {e}")
            return 0


async def run_startup_sequence(bot, send_notification: bool = True) -> dict:
    """Run the complete startup sequence."""
    startup = StartupHabits(bot)
    results = {}
    
    try:
        # Create default habits if needed
        habits_created = await startup.check_and_create_system_habits()
        results["habits_created"] = habits_created
        
        # Send startup notification to #habits channel
        if send_notification:
            habits_channel_id = 954466311596027984  # #habits channel
            notification_sent = await startup.send_startup_notification(habits_channel_id)
            results["notification_sent"] = notification_sent
        
        results["success"] = True
        logger.info("Startup sequence completed successfully")
        
    except Exception as e:
        logger.error(f"Startup sequence failed: {e}")
        results["success"] = False
        results["error"] = str(e)
    
    return results