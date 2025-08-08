"""
Discord Habit Bot - Main Bot Class

This is the core bot implementation that handles Discord integration,
command processing, and service coordination.

Design decisions:
- Using discord.py 2.0+ with application commands (slash commands)
- Modular service architecture for maintainability
- Graceful shutdown handling for systemd compatibility
- Comprehensive error handling and logging
"""

import os
import sys
import asyncio
import logging
import signal
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

import discord
from discord.ext import commands
from dotenv import load_dotenv

from database import initialize_database, close_database, db_manager
from services.habit_service import HabitService
from services.reward_service import RewardService
from services.streak_service import StreakService
from services.prompt_service import PromptService
from services.quiz_service import QuizService
from services.obsidian_service import ObsidianService
from services.user_service import UserService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.getenv("LOG_FILE", "logs/habit_bot.log"))
    ]
)

logger = logging.getLogger(__name__)


class HabitBot(commands.Bot):
    """
    Discord Habit Bot main class.
    
    Manages habit tracking, rewards, streaks, and gamification features.
    """
    
    def __init__(self):
        # Configure bot intents
        intents = discord.Intents.default()
        intents.message_content = True  # Required for reading message content
        intents.reactions = True       # Required for reaction-based logging
        
        # Initialize bot with prefix and intents
        super().__init__(
            command_prefix=os.getenv("COMMAND_PREFIX", "!"),
            intents=intents,
            help_command=None,  # We'll implement custom help
            case_insensitive=True,
            strip_after_prefix=True,
        )
        
        # Service instances
        self.services: Dict[str, Any] = {}
        self.startup_time: Optional[datetime] = None
        self.shutdown_event = asyncio.Event()
        
        # Background ping task
        self._ping_task: Optional[asyncio.Task] = None
        
        # Setup signal handlers for graceful shutdown
        if sys.platform != "win32":  # Unix-like systems
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum: int, frame) -> None:
        """Handle shutdown signals for graceful termination."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        asyncio.create_task(self.shutdown())
    
    async def setup_hook(self) -> None:
        """Initialize bot services and database connections."""
        try:
            logger.info("Starting bot initialization...")
            
            # Initialize database
            await initialize_database()
            
            # Initialize services with dependency injection
            self.services = {
                "user": UserService(db_manager),
                "habit": HabitService(db_manager),
                "reward": RewardService(db_manager),
                "streak": StreakService(db_manager),
                "prompt": PromptService(db_manager, self),
                "quiz": QuizService(db_manager, self),
                "obsidian": ObsidianService(),
            }
            
            # Load command extensions
            await self.load_extension("cogs.habit_commands")
            await self.load_extension("cogs.stats_commands")
            await self.load_extension("cogs.admin_commands")
            await self.load_extension("cogs.quiz_commands")
            await self.load_extension("cogs.obsidian_commands")
            await self.load_extension("cogs.help_commands")
            
            # Sync application commands (slash commands)
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} application commands")
            
            # Start scheduled services
            await self.services["prompt"].start_scheduler()
            
            # Run startup sequence (create default habits and send notification)
            await self._run_startup_sequence()
            
            self.startup_time = datetime.utcnow()
            
            # Start background ping task if enabled
            await self._start_ping_task_if_enabled()
            
            logger.info("Bot initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            raise
    
    async def on_ready(self) -> None:
        """Called when the bot has logged in and is ready."""
        logger.info(f"Bot logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        
        # Set bot status
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="your habits grow! 🌱"
        )
        await self.change_presence(activity=activity)
        
        # Log guild information
        for guild in self.guilds:
            logger.info(f"Active in guild: {guild.name} (ID: {guild.id})")
    
    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Called when the bot joins a new guild."""
        logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")
        
        # Find a suitable channel to send welcome message
        channel = None
        for ch in guild.text_channels:
            if ch.permissions_for(guild.me).send_messages:
                channel = ch
                break
        
        if channel:
            embed = discord.Embed(
                title="🌱 Habit Bot Activated!",
                description=(
                    "Thanks for adding me to your server! I'm here to help you "
                    "track habits, earn rewards, and build streaks.\n\n"
                    f"Use `{self.command_prefix}help` to get started!"
                ),
                color=discord.Color.green()
            )
            embed.add_field(
                name="Quick Start",
                value=(
                    f"`{self.command_prefix}log` - Log a habit completion\n"
                    f"`{self.command_prefix}stats` - View your progress\n"
                    f"`{self.command_prefix}habits` - List available habits"
                ),
                inline=False
            )
            await channel.send(embed=embed)
    
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        """Handle reaction-based habit logging."""
        # Ignore bot reactions
        if payload.user_id == self.user.id:
            return
        
        # Process reaction through prompt service
        if "prompt" in self.services:
            await self.services["prompt"].handle_reaction(payload)
    
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        """Global error handler for commands."""
        if isinstance(error, commands.CommandNotFound):
            # Check if this command is meant for the other bot
            command_name = ctx.message.content.split()[0][1:].lower()  # Remove prefix and get command
            excluded_commands = ["add", "brief"]  # Commands for the other bot
            
            if command_name in excluded_commands:
                # Silently ignore commands meant for the other bot
                return
            
            # Don't respond to unknown commands to avoid spam
            return
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: `{error.param.name}`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Invalid argument: {error}")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏰ Command on cooldown. Try again in {error.retry_after:.1f} seconds.")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command.")
        else:
            logger.error(f"Unhandled command error: {error}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the bot and all services."""
        try:
            logger.info("Starting graceful shutdown...")
            
            # Stop ping task
            if self._ping_task and not self._ping_task.done():
                self._ping_task.cancel()
                try:
                    await self._ping_task
                except asyncio.CancelledError:
                    pass
            
            # Stop scheduled services
            if "prompt" in self.services:
                await self.services["prompt"].stop_scheduler()
            
            # Close database connections
            await close_database()
            
            # Close Discord connection
            await self.close()
            
            self.shutdown_event.set()
            logger.info("Graceful shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    async def _run_startup_sequence(self) -> None:
        """Run startup sequence including default habits and notifications."""
        try:
            from startup_habits import run_startup_sequence
            
            logger.info("Running startup sequence...")
            results = await run_startup_sequence(self, send_notification=True)
            
            if results.get("success"):
                habits_created = results.get("habits_created", 0)
                notification_sent = results.get("notification_sent", False)
                
                if habits_created > 0:
                    logger.info(f"Created {habits_created} default habits")
                
                if notification_sent:
                    logger.info("Startup notification sent to Discord")
                else:
                    logger.warning("Failed to send startup notification")
            else:
                logger.error(f"Startup sequence failed: {results.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Error running startup sequence: {e}")
    
    async def _start_ping_task_if_enabled(self) -> None:
        """Start the periodic ping task if enabled via environment variables."""
        enabled = os.getenv("PING_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
        if not enabled:
            return
        # Determine interval in seconds
        interval_seconds = None
        if os.getenv("PING_INTERVAL_SECONDS"):
            try:
                interval_seconds = max(1, int(os.getenv("PING_INTERVAL_SECONDS", "300")))
            except ValueError:
                interval_seconds = 300
        else:
            try:
                minutes = int(os.getenv("PING_INTERVAL_MINUTES", "5"))
                interval_seconds = max(60, minutes * 60)
            except ValueError:
                interval_seconds = 300
        
        if self._ping_task and not self._ping_task.done():
            # Already running
            return
        
        async def ping_loop() -> None:
            await self.wait_until_ready()
            channel_id_env = os.getenv("PING_CHANNEL_ID") or os.getenv("COMMANDS_CHANNEL_ID")
            emoji = os.getenv("PING_EMOJI", "💓")
            use_embed = os.getenv("PING_USE_EMBED", "true").strip().lower() not in {"0", "false", "no", "off"}
            message_template = os.getenv(
                "PING_MESSAGE",
                "{emoji} Heartbeat OK | Uptime: {uptime} | Guilds: {guild_count} | {timestamp} UTC"
            )
            color_hex = os.getenv("PING_EMBED_COLOR") or os.getenv("PROMPT_EMBED_COLOR") or "#00FF7F"
            
            while not self.is_closed():
                try:
                    # Compute dynamic values
                    now = datetime.utcnow()
                    uptime_td: timedelta = (now - self.startup_time) if self.startup_time else timedelta(0)
                    uptime_str = _format_timedelta(uptime_td)
                    guild_count = len(self.guilds)
                    timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")
                    content = message_template.format(
                        emoji=emoji,
                        uptime=uptime_str,
                        guild_count=guild_count,
                        timestamp=timestamp_str,
                    )
                    
                    # Resolve channel
                    channel = None
                    if channel_id_env:
                        try:
                            channel = self.get_channel(int(channel_id_env))
                        except Exception:
                            channel = None
                    
                    if channel is None:
                        # Fallback to first channel with permission
                        for guild in self.guilds:
                            for ch in guild.text_channels:
                                if ch.permissions_for(guild.me).send_messages:
                                    channel = ch
                                    break
                            if channel:
                                break
                    
                    if channel:
                        if use_embed:
                            embed = discord.Embed(
                                title=f"{emoji} Bot Heartbeat",
                                description=content,
                                color=_parse_hex_color(color_hex),
                                timestamp=now,
                            )
                            await channel.send(embed=embed)
                        else:
                            await channel.send(content)
                    else:
                        logger.warning("PING: No suitable channel found to send heartbeat")
                except Exception as e:
                    logger.error(f"PING: Error sending heartbeat: {e}")
                
                await asyncio.sleep(interval_seconds)
        
        self._ping_task = asyncio.create_task(ping_loop())
        logger.info(f"Started ping task with interval {interval_seconds}s")
    
    def run_bot(self) -> None:
        """Run the bot with proper error handling."""
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            logger.error("DISCORD_TOKEN environment variable is required")
            sys.exit(1)
        
        try:
            self.run(token, log_handler=None)  # We handle logging ourselves
        except discord.LoginFailure:
            logger.error("Invalid Discord token")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Bot crashed: {e}", exc_info=True)
            sys.exit(1)


async def main():
    """Main entry point for the bot."""
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)
    
    # Create and run bot
    bot = HabitBot()
    
    try:
        # Run bot in background task
        bot_task = asyncio.create_task(bot.start(os.getenv("DISCORD_TOKEN")))
        
        # Wait for shutdown signal
        await bot.shutdown_event.wait()
        
        # Cancel bot task if still running
        if not bot_task.done():
            bot_task.cancel()
            try:
                await bot_task
            except asyncio.CancelledError:
                pass
    
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        await bot.shutdown()
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        await bot.shutdown()


if __name__ == "__main__":
    # Check for required environment variables
    required_vars = ["DISCORD_TOKEN", "DATABASE_URL"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        sys.exit(1)
    
    # Run the bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}", exc_info=True)
        sys.exit(1)


def _parse_hex_color(hex_str: str) -> discord.Color:
    """Parse a hex color string like '#00FF7F' into a discord.Color."""
    try:
        s = hex_str.strip().lower()
        if s.startswith("0x"):
            s = s[2:]
        if s.startswith("#"):
            s = s[1:]
        value = int(s, 16)
        # Clamp to 24-bit
        value = value & 0xFFFFFF
        return discord.Color(value)
    except Exception:
        return discord.Color.green()


def _format_timedelta(delta: timedelta) -> str:
    """Format timedelta as 'Xd Xh Xm Xs'."""
    total_seconds = int(delta.total_seconds())
    days, rem = divmod(total_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if not parts:
        parts.append(f"{seconds}s")
    return " ".join(parts)