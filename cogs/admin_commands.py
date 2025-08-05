"""
Admin Commands Cog for Discord Habit Bot.

Handles administrative commands for bot management.
"""

import logging
import discord
from discord.ext import commands

logger = logging.getLogger(__name__)


class AdminCommands(commands.Cog):
    """Administrative commands for bot management."""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="admin_status", hidden=True)
    @commands.has_permissions(administrator=True)
    async def admin_status(self, ctx):
        """Show bot status and statistics (Admin only)."""
        try:
            embed = discord.Embed(
                title="🤖 Bot Status",
                color=discord.Color.blue()
            )
            
            # Basic info
            embed.add_field(
                name="📊 General",
                value=f"Guilds: {len(self.bot.guilds)}\nUsers: {len(self.bot.users)}\nUptime: Since bot start",
                inline=True
            )
            
            # Service status
            services_status = []
            for name, service in self.bot.services.items():
                status = "✅" if service else "❌"
                services_status.append(f"{status} {name.title()}")
            
            embed.add_field(
                name="🔧 Services",
                value="\n".join(services_status),
                inline=True
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in admin status: {e}")
            await ctx.send("❌ Error retrieving status.")
    
    @commands.command(name="sync", hidden=True)
    @commands.has_permissions(administrator=True)
    async def sync_commands(self, ctx):
        """Sync slash commands (Admin only)."""
        try:
            synced = await self.bot.tree.sync()
            await ctx.send(f"✅ Synced {len(synced)} commands.")
        except Exception as e:
            await ctx.send(f"❌ Failed to sync commands: {e}")


class QuizCommands(commands.Cog):
    """Quiz and review commands."""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="quiz")
    async def quiz(self, ctx):
        """Start a quiz session."""
        await ctx.send("🧠 Quiz system coming soon!")


async def setup(bot):
    """Setup function for loading the cogs."""
    await bot.add_cog(AdminCommands(bot))