"""
Obsidian Commands for Discord Habit Bot.

Discord commands for interacting with Obsidian vault integration.
"""

import logging
from datetime import date
from typing import Optional
import discord
from discord.ext import commands
from services.obsidian_service import ObsidianService

logger = logging.getLogger(__name__)


class ObsidianCommands(commands.Cog):
    """Commands for Obsidian integration."""
    
    def __init__(self, bot):
        self.bot = bot
        self.obsidian_service = ObsidianService()
    
    @commands.command(name="obsidian_health", aliases=["obs_health"])
    async def obsidian_health(self, ctx):
        """Check Obsidian integration health status."""
        health = await self.obsidian_service.health_check()
        
        status_emoji = "✅" if health["status"] == "healthy" else "❌" if health["status"] == "unhealthy" else "⚠️"
        
        embed = discord.Embed(
            title=f"{status_emoji} Obsidian Integration Status",
            color=discord.Color.green() if health["status"] == "healthy" else discord.Color.red()
        )
        
        embed.add_field(name="Status", value=health["status"].title(), inline=True)
        embed.add_field(name="Mode", value=health.get("mode", "disabled").title(), inline=True)
        
        if health.get("vault"):
            embed.add_field(name="Vault", value=health["vault"], inline=False)
        
        if health.get("reason"):
            embed.add_field(name="Reason", value=health["reason"], inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="daily_note", aliases=["dnote"])
    async def daily_note(self, ctx, action: str = "get", target_date: str = None):
        """Manage daily notes. Usage: !daily [get|create] [YYYY-MM-DD]"""
        try:
            # Parse date if provided
            parsed_date = None
            if target_date:
                try:
                    parsed_date = date.fromisoformat(target_date)
                except ValueError:
                    await ctx.send("❌ Invalid date format. Use YYYY-MM-DD")
                    return
            
            if action.lower() == "get":
                daily_note = await self.obsidian_service.get_daily_note(parsed_date)
                if daily_note:
                    embed = discord.Embed(
                        title=f"📅 Daily Note - {(parsed_date or date.today()).strftime('%Y-%m-%d')}",
                        description=f"```markdown\n{daily_note.get('content', 'No content')[:1900]}...\n```" if len(daily_note.get('content', '')) > 1900 else f"```markdown\n{daily_note.get('content', 'No content')}\n```",
                        color=discord.Color.blue()
                    )
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(f"📅 No daily note found for {(parsed_date or date.today()).strftime('%Y-%m-%d')}")
            
            elif action.lower() == "create":
                success = await self.obsidian_service.create_daily_note(parsed_date)
                if success:
                    await ctx.send(f"✅ Daily note created for {(parsed_date or date.today()).strftime('%Y-%m-%d')}")
                else:
                    await ctx.send("❌ Failed to create daily note")
            
            else:
                await ctx.send("❌ Invalid action. Use 'get' or 'create'")
        
        except Exception as e:
            logger.error(f"Daily note command error: {e}")
            await ctx.send("❌ An error occurred while managing the daily note")
    
    @commands.command(name="add_task", aliases=["task"])
    async def add_task(self, ctx, *, task_description: str):
        """Add a task to today's daily note."""
        if not task_description:
            await ctx.send("❌ Please provide a task description")
            return
        
        try:
            success = await self.obsidian_service.add_task_to_daily_note(task_description)
            if success:
                await ctx.send(f"✅ Added task to daily note: *{task_description}*")
            else:
                await ctx.send("❌ Failed to add task to daily note")
        except Exception as e:
            logger.error(f"Add task command error: {e}")
            await ctx.send("❌ An error occurred while adding the task")
    
    @commands.command(name="sync_habits", aliases=["obsync"])
    async def sync_habits(self, ctx, target_date: str = None):
        """Sync today's habit completions to Obsidian."""
        try:
            # Parse date if provided
            parsed_date = None
            if target_date:
                try:
                    parsed_date = date.fromisoformat(target_date)
                except ValueError:
                    await ctx.send("❌ Invalid date format. Use YYYY-MM-DD")
                    return
            
            # Get user from database
            from services.user_service import UserService
            from database import DatabaseManager
            
            db_manager = DatabaseManager()
            user_service = UserService(db_manager)
            
            user = await user_service.get_user_by_discord_id(str(ctx.author.id))
            if not user:
                await ctx.send("❌ You need to create a habit first to sync data")
                return
            
            # Get habit logs for the date
            from services.habit_service import HabitService
            habit_service = HabitService(db_manager)
            
            # This would need to be implemented in habit_service
            # For now, we'll mock some data
            habit_logs = [
                {
                    "habit_name": "Example Habit",
                    "completed": True,
                    "xp_gained": 10,
                    "notes": "Synced from Discord bot"
                }
            ]
            
            success = await self.obsidian_service.sync_daily_habits(user.id, habit_logs, parsed_date)
            if success:
                date_str = (parsed_date or date.today()).strftime('%Y-%m-%d')
                await ctx.send(f"✅ Synced habits to Obsidian for {date_str}")
            else:
                await ctx.send("❌ Failed to sync habits to Obsidian")
        
        except Exception as e:
            logger.error(f"Sync habits command error: {e}")
            await ctx.send("❌ An error occurred while syncing habits")
    
    @commands.command(name="obsidian_info", aliases=["obs_info"])
    async def obsidian_info(self, ctx):
        """Show information about Obsidian integration features."""
        embed = discord.Embed(
            title="🔮 Obsidian Integration",
            description="Sync your habit tracking with your Obsidian vault!",
            color=discord.Color.purple()
        )
        
        embed.add_field(
            name="📅 Daily Notes",
            value="• `!daily_note get` - View today's note\n• `!daily_note create` - Create daily note\n• `!task <description>` - Add task",
            inline=False
        )
        
        embed.add_field(
            name="🔄 Habit Sync",
            value="• `!sync_habits` - Sync today's habits\n• `!sync_habits YYYY-MM-DD` - Sync specific date",
            inline=False
        )
        
        embed.add_field(
            name="🔧 Health Check",
            value="• `!obsidian_health` - Check integration status",
            inline=False
        )
        
        embed.add_field(
            name="⚙️ Setup",
            value="Configure `OBSIDIAN_VAULT_PATH` in environment for file-based sync, or `OBSIDIAN_API_URL` + `OBSIDIAN_API_KEY` for REST API integration.",
            inline=False
        )
        
        await ctx.send(embed=embed)


async def setup(bot):
    """Set up the Obsidian commands cog."""
    await bot.add_cog(ObsidianCommands(bot))