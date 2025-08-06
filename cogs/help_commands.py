"""
Help Commands for Discord Habit Bot.

Provides comprehensive help and quick reference information.
"""

import logging
import discord
from discord.ext import commands

logger = logging.getLogger(__name__)


class HelpCommands(commands.Cog):
    """Help and reference commands."""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="help_habits", aliases=["guide", "quickref"])
    async def help_habits(self, ctx):
        """Show comprehensive habit bot help."""
        embed = discord.Embed(
            title="🤖 Discord Habit Bot - Quick Reference",
            description="Your complete guide to building legendary habits!",
            color=0x00ff88
        )
        
        # Basic Commands
        embed.add_field(
            name="🎯 Basic Commands",
            value="""
`!create meditation 10 minutes daily` - Create habit
`!add_habit weekly "Meal Prep"` - Use templates
`!log exercise - great workout!` - Log completion
`!today` - Today's progress
`!stats` - Your statistics
`!habits` - List all habits
`!sync_default_habits` - Update to latest habits
            """,
            inline=True
        )
        
        # Gamification
        embed.add_field(
            name="🎮 Gamification",
            value="""
`!leaderboard xp` - XP rankings
`!leaderboard streak` - Streak champions
`!inventory` - Items & gold
`!rewards` - Recent achievements
            """,
            inline=True
        )
        
        # Obsidian
        embed.add_field(
            name="🔮 Obsidian",
            value="""
`!dnote get` - View daily note
`!dnote create` - Create note
`!task Buy groceries` - Add task
`!obsync` - Sync to journal
`!obsidian_health` - Check status
            """,
            inline=True
        )
        
        # Channel guide
        embed.add_field(
            name="📱 Channel Guide",
            value="""
**#habits** - Main discussions
**#reminders** - Automated prompts
**#progress** - Daily check-ins
**#reports** - Weekly summaries
**#commands** - Testing & help
            """,
            inline=False
        )
        
        embed.add_field(
            name="💡 Pro Tips",
            value="🌟 Use natural language • 📈 Check `!today` daily • 🔥 Build streaks • 📝 Add notes to logs",
            inline=False
        )
        
        embed.set_footer(text="💪 Start small, stay consistent, level up!")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="example", aliases=["demo", "workflow"])
    async def example_workflow(self, ctx):
        """Show example daily workflow."""
        embed = discord.Embed(
            title="🚀 Example Daily Workflow",
            description="How to use the habit bot effectively",
            color=0x3498db
        )
        
        workflow = """
**Morning:**
1. `!today` - Check your habits
2. React ✅ to reminders

**Throughout Day:**
3. `!log meditation - 10 min peace`
4. `!task Finish project proposal`

**Evening:**
5. `!stats` - Check progress
6. `!dnote create` - Reflect in Obsidian
7. `!obsync` - Sync to journal

**Weekly:**
8. `!leaderboard xp` - See rankings
9. `!rewards` - Check achievements

**Get Started:**
`!create reading 15 minutes daily` 📚
        """
        
        embed.add_field(name="Daily Flow", value=workflow, inline=False)
        await ctx.send(embed=embed)
    
    @commands.command(name="channels")
    async def channel_guide(self, ctx):
        """Show channel-specific usage guide."""
        embed = discord.Embed(
            title="📱 Channel Usage Guide",
            description="How to use each channel effectively",
            color=0xe74c3c
        )
        
        channels = {
            "#habits": "Create habits, discuss strategies, evening reflections",
            "#reminders": "Receive automated prompts (7am, 12pm, 6pm)",
            "#progress": "Log completions, daily check-ins (8pm)",
            "#reports": "Weekly summaries, leaderboards (Sunday 9am)",
            "#commands": "Test commands, get help, bot status"
        }
        
        for channel, desc in channels.items():
            embed.add_field(name=channel, value=desc, inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="bot_schedule", aliases=["schedule_info"])
    async def show_schedule(self, ctx):
        """Show the bot's automated schedule."""
        embed = discord.Embed(
            title="⏰ Bot Schedule",
            description="When the bot sends automated messages",
            color=0xf39c12
        )
        
        schedule = """
**Daily:**
• 7:00 AM - Morning motivation → #reminders
• 12:00 PM - Mindfulness check → #reminders
• 6:00 PM - Exercise reminder → #reminders (weekdays)
• 8:00 PM - Progress check → #progress
• 9:00 PM - Evening reflection → #habits

**Weekly:**
• Sunday 9:00 AM - Weekly report → #reports
• Monday 10:00 AM - Bot health check → #commands

**Special:**
• Bot startup - Welcome message → #habits
        """
        
        embed.add_field(name="Automated Messages", value=schedule, inline=False)
        embed.add_field(
            name="Timezone", 
            value="All times in America/New_York timezone", 
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="send_help_to_commands")
    @commands.has_permissions(administrator=True)
    async def send_help_to_commands(self, ctx):
        """Send comprehensive help to #commands channel (Admin only)."""
        commands_channel_id = 1392911686737854625
        commands_channel = self.bot.get_channel(commands_channel_id)
        
        if not commands_channel:
            await ctx.send("❌ Could not find #commands channel")
            return
        
        # Use the same embed from the script
        embed = discord.Embed(
            title="🤖 Discord Habit Bot - Quick Reference Guide",
            description="Your complete guide to building legendary habits!",
            color=0x00ff88
        )
        
        # Add all the fields (abbreviated for the command)
        embed.add_field(
            name="🎯 Basic Habit Commands",
            value="`!create`, `!log`, `!today`, `!stats`, `!habits`",
            inline=True
        )
        
        embed.add_field(
            name="🎮 Gamification",
            value="`!leaderboard`, `!inventory`, `!rewards`",
            inline=True
        )
        
        embed.add_field(
            name="🔮 Obsidian Integration",
            value="`!dnote`, `!task`, `!obsync`, `!obsidian_health`",
            inline=True
        )
        
        try:
            await commands_channel.send("📋 **Help Guide Updated!**", embed=embed)
            await ctx.send(f"✅ Help message sent to {commands_channel.mention}")
        except Exception as e:
            await ctx.send(f"❌ Error sending help: {e}")


async def setup(bot):
    """Set up the Help commands cog."""
    await bot.add_cog(HelpCommands(bot))