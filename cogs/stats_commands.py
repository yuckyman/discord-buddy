"""
Stats Commands Cog for Discord Habit Bot.

Handles statistics, leaderboards, and progress tracking commands.
"""

import logging
from datetime import date, timedelta
from typing import Optional
import discord
from discord.ext import commands

logger = logging.getLogger(__name__)


class StatsCommands(commands.Cog):
    """Commands for viewing statistics and leaderboards."""
    
    def __init__(self, bot):
        self.bot = bot
    
    @property
    def user_service(self):
        return self.bot.services.get("user")
    
    @property
    def habit_service(self):
        return self.bot.services.get("habit")
    
    @property
    def streak_service(self):
        return self.bot.services.get("streak")
    
    @property
    def reward_service(self):
        return self.bot.services.get("reward")
    
    @commands.command(name="stats", aliases=["profile", "me"])
    async def user_stats(self, ctx, user: Optional[discord.Member] = None):
        """Show user statistics and progress."""
        target_user = user or ctx.author
        
        try:
            # Get user from database
            db_user = await self.user_service.get_or_create_user(
                str(target_user.id), target_user.display_name
            )
            
            # Get streak information
            streaks = await self.streak_service.get_user_all_streaks(db_user.id)
            
            # Calculate stats
            active_streaks = sum(1 for s in streaks if s['is_active'])
            total_streaks = len(streaks)
            longest_streak = max((s['longest_streak'] for s in streaks), default=0)
            current_best = max((s['current_streak'] for s in streaks if s['is_active']), default=0)
            
            # Create embed
            embed = discord.Embed(
                title=f"📊 {target_user.display_name}'s Stats",
                color=discord.Color.blue()
            )
            
            # User info
            embed.add_field(
                name="👤 Profile",
                value=f"Level: **{db_user.level}**\nTotal XP: **{db_user.total_xp:,}**\nGold: **{db_user.gold:,}** 💰",
                inline=True
            )
            
            # Streak info
            embed.add_field(
                name="🔥 Streaks",
                value=f"Active: **{active_streaks}/{total_streaks}**\nLongest: **{longest_streak}** days\nBest Current: **{current_best}** days",
                inline=True
            )
            
            # Recent activity
            today_progress = await self.habit_service.get_user_daily_progress(db_user.id)
            completed_today = sum(1 for p in today_progress if p['completed'])
            total_today = len(today_progress)
            
            embed.add_field(
                name="📅 Today",
                value=f"Completed: **{completed_today}/{total_today}**\nProgress: {self._progress_bar(completed_today, total_today)}",
                inline=False
            )
            
            # Top streaks
            if streaks:
                top_streaks = sorted(streaks, key=lambda x: x['current_streak'], reverse=True)[:3]
                streak_text = []
                for i, streak in enumerate(top_streaks):
                    status = "🔥" if streak['is_active'] else "💔"
                    streak_text.append(f"{i+1}. {status} **{streak['habit'].name}** - {streak['current_streak']} days")
                
                embed.add_field(
                    name="🏆 Top Habits",
                    value="\n".join(streak_text) or "No habits tracked yet",
                    inline=False
                )
            
            embed.set_thumbnail(url=target_user.avatar.url if target_user.avatar else discord.Embed.Empty)
            embed.timestamp = discord.utils.utcnow()
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error showing stats: {e}")
            await ctx.send("❌ Error retrieving stats. Please try again.")
    
    @commands.command(name="leaderboard", aliases=["lb", "top"])
    async def leaderboard(self, ctx, category: str = "xp"):
        """Show leaderboards for XP, levels, or streaks."""
        try:
            if category.lower() in ["xp", "experience"]:
                users = await self.user_service.get_leaderboard(limit=10, sort_by="xp")
                title = "🏆 XP Leaderboard"
                format_func = lambda u, i: f"{i+1}. **{u.username}** - {u.total_xp:,} XP"
            elif category.lower() in ["level", "levels"]:
                users = await self.user_service.get_leaderboard(limit=10, sort_by="level")
                title = "🏆 Level Leaderboard"
                format_func = lambda u, i: f"{i+1}. **{u.username}** - Level {u.level} ({u.total_xp:,} XP)"
            elif category.lower() in ["gold", "coins"]:
                users = await self.user_service.get_leaderboard(limit=10, sort_by="gold")
                title = "🏆 Gold Leaderboard"
                format_func = lambda u, i: f"{i+1}. **{u.username}** - {u.gold:,} 💰"
            elif category.lower() in ["streak", "streaks"]:
                streaks = await self.streak_service.get_leaderboard_streaks(limit=10)
                title = "🏆 Streak Leaderboard"
                
                embed = discord.Embed(title=title, color=discord.Color.gold())
                
                if streaks:
                    streak_text = []
                    for i, streak in enumerate(streaks):
                        streak_text.append(
                            f"{i+1}. **{streak['user'].username}** - "
                            f"{streak['current_streak']} days ({streak['habit'].name})"
                        )
                    embed.description = "\n".join(streak_text)
                else:
                    embed.description = "No active streaks found."
                
                await ctx.send(embed=embed)
                return
            else:
                await ctx.send("❌ Invalid category. Use: `xp`, `level`, `gold`, or `streak`")
                return
            
            embed = discord.Embed(title=title, color=discord.Color.gold())
            
            if users:
                leaderboard_text = []
                for i, user in enumerate(users):
                    leaderboard_text.append(format_func(user, i))
                embed.description = "\n".join(leaderboard_text)
            else:
                embed.description = "No users found."
            
            embed.set_footer(text=f"Category: {category.title()}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error showing leaderboard: {e}")
            await ctx.send("❌ Error retrieving leaderboard. Please try again.")
    
    @commands.command(name="inventory", aliases=["inv", "items"])
    async def inventory(self, ctx):
        """Show user's inventory and items."""
        try:
            # Get user
            user = await self.user_service.get_or_create_user(
                str(ctx.author.id), ctx.author.display_name
            )
            
            # Get inventory
            inventory = await self.reward_service.get_user_inventory(user.id)
            
            embed = discord.Embed(
                title=f"🎒 {ctx.author.display_name}'s Inventory",
                color=discord.Color.purple()
            )
            
            if not inventory:
                embed.description = "Your inventory is empty. Complete habits to earn rewards!"
                await ctx.send(embed=embed)
                return
            
            # Group by item type
            categories = {}
            for item in inventory:
                item_type = item.item_type.title()
                if item_type not in categories:
                    categories[item_type] = []
                categories[item_type].append(item)
            
            # Add fields for each category
            for category, items in categories.items():
                item_text = []
                for item in items:
                    quantity_text = f" x{item.quantity}" if item.quantity > 1 else ""
                    item_text.append(f"• **{item.item_name}**{quantity_text}")
                
                embed.add_field(
                    name=f"{category} ({len(items)})",
                    value="\n".join(item_text),
                    inline=True
                )
            
            # Add gold info
            embed.add_field(
                name="💰 Gold",
                value=f"**{user.gold:,}** coins",
                inline=True
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error showing inventory: {e}")
            await ctx.send("❌ Error retrieving inventory. Please try again.")
    
    @commands.command(name="rewards", aliases=["recent"])
    async def recent_rewards(self, ctx, limit: int = 10):
        """Show recent rewards earned."""
        if limit > 20:
            limit = 20
        
        try:
            # Get user
            user = await self.user_service.get_or_create_user(
                str(ctx.author.id), ctx.author.display_name
            )
            
            # Get recent rewards
            rewards = await self.reward_service.get_user_rewards(user.id, limit)
            
            embed = discord.Embed(
                title=f"🎁 Recent Rewards ({len(rewards)})",
                color=discord.Color.green()
            )
            
            if not rewards:
                embed.description = "No rewards earned yet. Complete habits to earn rewards!"
                await ctx.send(embed=embed)
                return
            
            reward_text = []
            for reward in rewards:
                time_str = discord.utils.format_dt(reward.awarded_at, style='R')
                reward_text.append(f"• {reward.description} {time_str}")
            
            embed.description = "\n".join(reward_text)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error showing rewards: {e}")
            await ctx.send("❌ Error retrieving rewards. Please try again.")
    
    def _progress_bar(self, current: int, total: int, length: int = 10) -> str:
        """Generate a text progress bar."""
        if total == 0:
            return "▱" * length
        
        filled = int((current / total) * length)
        return "▰" * filled + "▱" * (length - filled)
    
    @commands.command(name="pushups", aliases=["push", "pushup_stats"])
    async def pushup_stats(self, ctx, user: Optional[discord.Member] = None):
        """Show detailed push-up statistics."""
        target_user = user or ctx.author
        
        try:
            # Get user from database
            db_user = await self.user_service.get_or_create_user(
                str(target_user.id), target_user.display_name
            )
            
            # Get push-up statistics
            stats = await self.habit_service.get_habit_count_stats(db_user.id, "Push-ups")
            
            if "error" in stats:
                await ctx.send(f"❌ {stats['error']}")
                return
            
            # Create embed
            embed = discord.Embed(
                title=f"💪 {target_user.display_name}'s Push-up Stats",
                description="your push-up journey so far!",
                color=0x00ff88
            )
            
            # Main stats
            embed.add_field(
                name="📊 overall stats",
                value=f"""
**total push-ups:** {stats['total_count']:,}
**sessions logged:** {stats['total_sessions']}
**average per session:** {stats['average']}
**personal best:** {stats['best']}
**lowest session:** {stats['worst']}
                """,
                inline=False
            )
            
            # Recent sessions
            if stats['recent_logs']:
                recent = []
                for log in stats['recent_logs'][:5]:  # Show last 5
                    recent.append(f"**{log['date']}:** {log['count']} push-ups")
                
                embed.add_field(
                    name="📈 recent sessions",
                    value="\n".join(recent),
                    inline=False
                )
            
            # Tips
            embed.add_field(
                name="💡 tip",
                value="log with: `!log push-ups - 32 feeling strong!`",
                inline=False
            )
            
            embed.set_footer(text="💪 keep pushing! every rep counts")
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Pushup stats error: {e}")
            await ctx.send("❌ error retrieving push-up stats. please try again.")


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(StatsCommands(bot))