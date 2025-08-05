"""
Quiz Commands Cog for Discord Habit Bot.

Handles quiz generation, Anki integration, and spaced repetition commands.
"""

import logging
import discord
from discord.ext import commands

logger = logging.getLogger(__name__)


class QuizCommands(commands.Cog):
    """Commands for quiz and review functionality."""
    
    def __init__(self, bot):
        self.bot = bot
    
    @property
    def quiz_service(self):
        return self.bot.services.get("quiz")
    
    @commands.command(name="quiz")
    async def quiz(self, ctx):
        """Start a quiz session for habit reflection."""
        await ctx.send("🧠 Quiz system coming soon! This will integrate with Anki for spaced repetition.")
    
    @commands.command(name="review")
    async def review(self, ctx):
        """Review pending quiz questions."""
        await ctx.send("📚 Review system coming soon!")


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(QuizCommands(bot))