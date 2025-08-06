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
from database import db_manager

logger = logging.getLogger(__name__)


class StartupHabits:
    """Manages startup habits and notifications."""
    
    def __init__(self, bot):
        self.bot = bot
        self.habit_service = HabitService(db_manager)
        self.user_service = UserService(db_manager)
        
        # Default habits to create on first run
        # Format: (name, description, base_xp, category, cron_expression)
        self.default_habits = [
            # Daily habits
            ("Morning Meditation", "Start your day with mindfulness", 15, "wellness", "0 7 * * *"),
            ("Daily Exercise", "Physical activity for health", 20, "fitness", "0 18 * * *"),
            ("Push-ups", "Track your daily push-up count", 15, "fitness", "0 19 * * *"),
            ("Read for Learning", "Expand your knowledge", 12, "learning", "0 20 * * *"),
            ("Drink Water", "Stay hydrated throughout the day", 5, "wellness", "0 */2 * * *"),
            ("Sleep Early", "Good sleep hygiene", 10, "wellness", "0 22 * * *"),
            ("Gratitude Journal", "Write 3 things you're grateful for", 8, "wellness", "0 21 * * *"),
            ("Code Review", "Review and improve coding skills", 15, "learning", "0 9 * * 1,2,3,4,5"),
            
            # Weekly habits
            ("Laundry", "Do weekly laundry", 25, "wellness", "0 10 * * 0"),  # Sunday 10am
            ("Exercise 3x Weekly", "Complete 3 exercise sessions this week", 60, "fitness", "0 8 * * 1"),  # Monday reminder
            ("Vacuum", "Vacuum living spaces", 20, "wellness", "0 14 * * 6"),  # Saturday 2pm
            ("Groceries", "Weekly grocery shopping", 30, "wellness", "0 11 * * 0"),  # Sunday 11am
            
            # Monthly habits  
            ("Change Sheets", "Change bed sheets and pillowcases", 40, "wellness", "0 9 1 * *"),  # 1st of month, 9am
            ("Clean Bathroom", "Deep clean bathroom", 50, "wellness", "0 10 15 * *"),  # 15th of month, 10am
            ("Clean Car", "Wash and clean car interior", 45, "wellness", "0 9 28 * *"),  # 28th of month, 9am
            
            # Seasonal habits (quarterly)
            ("Clean Wardrobe", "Organize and declutter wardrobe", 80, "wellness", "0 10 1 1,4,7,10 *"),  # Jan/Apr/Jul/Oct 1st
            ("Update Resume", "Review and update resume/CV", 75, "learning", "0 14 15 3,6,9,12 *"),  # Mar/Jun/Sep/Dec 15th
        ]
        
        # Habit templates for easy addition of new multi-scale habits
        self.habit_templates = {
            "daily": {
                "cron_pattern": "0 {hour} * * *",
                "default_hour": 9,
                "base_xp": 15,
                "examples": ["Morning routine", "Evening reflection", "Daily walk"]
            },
            "weekly": {
                "cron_pattern": "0 {hour} * * {day}",  # day: 0=Sunday, 1=Monday, etc.
                "default_hour": 10,
                "default_day": 0,  # Sunday
                "base_xp": 30,
                "examples": ["Meal prep", "Grocery shopping", "Cleaning"]
            },
            "monthly": {
                "cron_pattern": "0 {hour} {day} * *",  # day: 1-28 safe for all months
                "default_hour": 9,
                "default_day": 1,  # 1st of month
                "base_xp": 50,
                "examples": ["Bill payments", "Deep cleaning", "Monthly review"]
            },
            "quarterly": {
                "cron_pattern": "0 {hour} {day} {months} *",  # months: 1,4,7,10 for quarters
                "default_hour": 10,
                "default_day": 1,
                "default_months": "1,4,7,10",
                "base_xp": 80,
                "examples": ["Seasonal wardrobe change", "Goal review", "Equipment maintenance"]
            },
            "yearly": {
                "cron_pattern": "0 {hour} {day} {month} *",
                "default_hour": 9,
                "default_day": 1,
                "default_month": 1,  # January
                "base_xp": 100,
                "examples": ["Annual health checkup", "Tax preparation", "Year-end review"]
            }
        }
    
    def create_habit_from_template(self, name: str, description: str, 
                                 template_type: str, category: str = "wellness",
                                 **kwargs) -> tuple:
        """Create a habit using predefined templates.
        
        Args:
            name: Habit name
            description: Habit description  
            template_type: Type of template (daily, weekly, monthly, quarterly, yearly)
            category: Habit category
            **kwargs: Template-specific parameters (hour, day, month, etc.)
            
        Returns:
            Tuple of (name, description, xp, category, cron_expression)
        """
        if template_type not in self.habit_templates:
            raise ValueError(f"Unknown template type: {template_type}")
        
        template = self.habit_templates[template_type]
        
        # Use provided values or defaults
        hour = kwargs.get("hour", template["default_hour"])
        base_xp = kwargs.get("xp", template["base_xp"])
        
        # Build cron expression based on template type
        if template_type == "daily":
            cron = template["cron_pattern"].format(hour=hour)
            
        elif template_type == "weekly":
            day = kwargs.get("day", template["default_day"])
            cron = template["cron_pattern"].format(hour=hour, day=day)
            
        elif template_type == "monthly":
            day = kwargs.get("day", template["default_day"])
            cron = template["cron_pattern"].format(hour=hour, day=day)
            
        elif template_type == "quarterly":
            day = kwargs.get("day", template["default_day"])
            months = kwargs.get("months", template["default_months"])
            cron = template["cron_pattern"].format(hour=hour, day=day, months=months)
            
        elif template_type == "yearly":
            day = kwargs.get("day", template["default_day"])
            month = kwargs.get("month", template["default_month"])
            cron = template["cron_pattern"].format(hour=hour, day=day, month=month)
        
        return (name, description, base_xp, category, cron)
    
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
                                    cron_expression=schedule,
                                    bot=self.bot
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