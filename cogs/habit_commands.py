"""
Habit Commands Cog for Discord Habit Bot.

Handles habit logging, creation, and management commands with natural language support.
"""

import logging
from datetime import date
from typing import Optional
import discord
from discord.ext import commands
from discord import app_commands

logger = logging.getLogger(__name__)


class HabitCommands(commands.Cog):
    """Commands for habit management and logging."""
    
    def __init__(self, bot):
        self.bot = bot
    
    @property
    def habit_service(self):
        """Get habit service from bot."""
        return self.bot.services.get("habit")
    
    @property
    def user_service(self):
        """Get user service from bot."""
        return self.bot.services.get("user")
    
    @property
    def reward_service(self):
        """Get reward service from bot."""
        return self.bot.services.get("reward")
    
    @property
    def streak_service(self):
        """Get streak service from bot."""
        return self.bot.services.get("streak")
    
    # === HABIT LOGGING COMMANDS ===
    
    @commands.command(name="log", aliases=["l", "done", "complete"])
    async def log_habit(self, ctx, *, habit_name: str):
        """Log completion of a habit.
        
        Usage: !log meditation
               !log exercise - had a great workout today
        """
        try:
            # Parse habit name and optional notes
            parts = habit_name.split(" - ", 1)
            habit_name = parts[0].strip()
            notes = parts[1].strip() if len(parts) > 1 else None
            
            # Get or create user
            user = await self.user_service.get_or_create_user(
                str(ctx.author.id), ctx.author.display_name
            )
            
            # Find habit
            habit = await self.habit_service.get_habit_by_name(habit_name)
            if not habit:
                # Suggest similar habits
                all_habits = await self.habit_service.get_all_habits()
                suggestions = [h.name for h in all_habits if habit_name.lower() in h.name.lower()]
                
                embed = discord.Embed(
                    title="❌ Habit Not Found",
                    description=f"Could not find habit: **{habit_name}**",
                    color=discord.Color.red()
                )
                
                if suggestions:
                    embed.add_field(
                        name="Did you mean?",
                        value="\n".join(f"• {s}" for s in suggestions[:5]),
                        inline=False
                    )
                
                embed.add_field(
                    name="Available Commands",
                    value=(
                        f"`{ctx.prefix}habits` - List all habits\n"
                        f"`{ctx.prefix}create <habit description>` - Create new habit"
                    ),
                    inline=False
                )
                
                await ctx.send(embed=embed)
                return
            
            # Log habit completion
            habit_log, is_new = await self.habit_service.log_habit_completion(
                user.id, habit.id, notes, source="command"
            )
            
            if not is_new:
                embed = discord.Embed(
                    title="📝 Habit Updated",
                    description=f"Updated your **{habit.name}** log for today",
                    color=discord.Color.blue()
                )
                if notes:
                    embed.add_field(name="Notes", value=notes, inline=False)
                await ctx.send(embed=embed)
                return
            
            # Update user stats
            updated_user = await self.user_service.update_user_stats(
                user.id, xp_delta=habit_log.xp_awarded
            )
            
            # Update streaks
            await self.streak_service.update_streak(user.id, habit.id)
            
            # Roll for rewards
            reward = await self.reward_service.roll_for_reward(
                user.id, "habit_log", habit_log.id
            )
            
            # Create success embed
            embed = discord.Embed(
                title="🎉 Habit Completed!",
                description=f"Great job completing **{habit.name}**!",
                color=discord.Color.green()
            )
            
            # Add XP info
            embed.add_field(
                name="XP Earned",
                value=f"+{habit_log.xp_awarded} XP",
                inline=True
            )
            
            # Add level info
            embed.add_field(
                name="Progress",
                value=f"Level {updated_user.level} ({updated_user.total_xp} total XP)",
                inline=True
            )
            
            # Add notes if provided
            if notes:
                embed.add_field(name="Notes", value=notes, inline=False)
            
            # Add reward if received
            if reward:
                embed.add_field(
                    name="🎁 Bonus Reward!",
                    value=reward.description,
                    inline=False
                )
            
            # Add streak info
            streak_info = await self.streak_service.get_user_streak(user.id, habit.id)
            if streak_info and streak_info.current_streak > 1:
                embed.add_field(
                    name="🔥 Streak",
                    value=f"{streak_info.current_streak} days",
                    inline=True
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error logging habit: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Something went wrong while logging your habit. Please try again.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    # === HABIT MANAGEMENT COMMANDS ===
    
    @commands.command(name="habits", aliases=["list", "h"])
    async def list_habits(self, ctx, category: Optional[str] = None):
        """List available habits, optionally filtered by category.
        
        Usage: !habits
               !habits fitness
        """
        try:
            if category:
                habits = await self.habit_service.get_habits_by_category(category)
                title = f"📋 {category.title()} Habits"
            else:
                categorized = await self.habit_service.list_habits_with_schedules()
                
                embed = discord.Embed(
                    title="📋 Available Habits",
                    description="Here are all the habits you can track:",
                    color=discord.Color.blue()
                )
                
                for category_name, habit_list in categorized.items():
                    if not habit_list:
                        continue
                    
                    habit_text = []
                    for item in habit_list:
                        habit = item['habit']
                        schedules = item['schedules']
                        
                        line = f"• **{habit.name}** ({habit.base_xp} XP)"
                        if schedules:
                            # Show first schedule time
                            cron = schedules[0].cron_expression
                            line += f" - Scheduled"
                        
                        if habit.description:
                            line += f"\n  *{habit.description}*"
                        
                        habit_text.append(line)
                    
                    if habit_text:
                        embed.add_field(
                            name=f"{category_name.title()} ({len(habit_text)})",
                            value="\n".join(habit_text),
                            inline=False
                        )
                
                embed.add_field(
                    name="Commands",
                    value=(
                        f"`{ctx.prefix}log <habit>` - Log completion\n"
                        f"`{ctx.prefix}create <description>` - Create new habit\n"
                        f"`{ctx.prefix}schedule <habit> at <time>` - Schedule reminders"
                    ),
                    inline=False
                )
                
                await ctx.send(embed=embed)
                return
            
            # Handle category-specific listing
            if not habits:
                embed = discord.Embed(
                    title="❌ No Habits Found",
                    description=f"No habits found in category: **{category}**",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return
            
            embed = discord.Embed(
                title=title,
                color=discord.Color.blue()
            )
            
            habit_text = []
            for habit in habits:
                line = f"• **{habit.name}** ({habit.base_xp} XP)"
                if habit.description:
                    line += f" - {habit.description}"
                habit_text.append(line)
            
            embed.description = "\n".join(habit_text)
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error listing habits: {e}")
            await ctx.send("❌ Error retrieving habits. Please try again.")
    
    # === DYNAMIC HABIT CREATION ===
    
    @commands.command(name="create", aliases=["new"])
    async def create_habit(self, ctx, *, description: str):
        """Create a new habit using natural language.
        
        Examples:
        - !create add habit meditation 20 minutes daily at 7am for mindfulness
        - !create habit: exercise (15 xp) - daily workout routine  
        - !create new habit reading for 30 minutes
        - !create habit drink water every 2 hours
        """
        try:
            # Get or create user
            user = await self.user_service.get_or_create_user(
                str(ctx.author.id), ctx.author.display_name
            )
            
            # Parse and create habit
            habit, schedule, message = await self.habit_service.parse_and_create_habit(
                description, user.id
            )
            
            if habit:
                embed = discord.Embed(
                    title="🌱 Habit Created!",
                    description=message,
                    color=discord.Color.green()
                )
                
                embed.add_field(
                    name="Quick Start",
                    value=f"`{ctx.prefix}log {habit.name}` - Log completion",
                    inline=False
                )
                
                if schedule:
                    embed.add_field(
                        name="📅 Scheduled Reminders",
                        value="You'll receive automatic reminders based on your schedule!",
                        inline=False
                    )
            else:
                embed = discord.Embed(
                    title="❌ Habit Creation Failed",
                    description=message,
                    color=discord.Color.red()
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error creating habit: {e}")
            await ctx.send("❌ Error creating habit. Please try again.")
    
    @commands.command(name="schedule", aliases=["remind", "timer"])
    async def schedule_habit(self, ctx, habit_name: str, *, schedule_text: str):
        """Add or modify schedule for an existing habit.
        
        Usage: !schedule meditation at 7am daily
               !schedule exercise at 6pm weekly
        """
        try:
            # Parse schedule text
            if " at " not in schedule_text:
                await ctx.send("❌ Please specify a time using 'at'. Example: `at 7am daily`")
                return
            
            parts = schedule_text.split(" at ", 1)
            if len(parts) != 2:
                await ctx.send("❌ Invalid format. Use: `!schedule <habit> at <time> [frequency]`")
                return
            
            time_and_freq = parts[1].split()
            if not time_and_freq:
                await ctx.send("❌ Please specify a time. Example: `7am`, `14:30`, `9:15pm`")
                return
            
            time_str = time_and_freq[0]
            frequency = time_and_freq[1] if len(time_and_freq) > 1 else "daily"
            
            # Create or update schedule
            result = await self.habit_service.modify_habit_schedule(
                habit_name, time_str, frequency
            )
            
            if result.startswith("✅"):
                embed = discord.Embed(
                    title="📅 Schedule Updated",
                    description=result,
                    color=discord.Color.green()
                )
            else:
                embed = discord.Embed(
                    title="❌ Schedule Error",
                    description=result,
                    color=discord.Color.red()
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error scheduling habit: {e}")
            await ctx.send("❌ Error updating schedule. Please try again.")
    
    # === MULTI-SCALE HABIT CREATION ===
    
    @commands.command(name="add_habit", aliases=["template_habit", "scale_habit"])
    async def add_habit_from_template(self, ctx, template_type: str, name: str, *, description: str = ""):
        """Create a habit using predefined time scale templates.
        
        Usage: !add_habit weekly "Meal Prep" "Prepare meals for the week"
               !add_habit monthly "Car Maintenance" "Check oil and tire pressure"
               !add_habit quarterly "Goal Review" "Review and update quarterly goals"
        
        Templates: daily, weekly, monthly, quarterly, yearly
        """
        try:
            # Check if template type is valid
            valid_templates = ["daily", "weekly", "monthly", "quarterly", "yearly"]
            if template_type.lower() not in valid_templates:
                await ctx.send(f"❌ Invalid template type. Choose from: {', '.join(valid_templates)}")
                return
            
            # Get startup habits service for template access
            from startup_habits import StartupHabits
            startup = StartupHabits(self.bot)
            
            # Create habit from template
            try:
                habit_tuple = startup.create_habit_from_template(
                    name=name,
                    description=description or f"A {template_type} habit",
                    template_type=template_type.lower(),
                    category="wellness"  # Default category
                )
                
                # Create the habit
                habit = await self.habit_service.create_habit(
                    name=habit_tuple[0],
                    description=habit_tuple[1],
                    base_xp=habit_tuple[2],
                    category=habit_tuple[3]
                )
                
                # Create the schedule
                if habit_tuple[4]:  # cron expression
                    try:
                        await self.habit_service.schedule_habit_reminder(
                            habit_name=habit_tuple[0],
                            cron_expression=habit_tuple[4]
                        )
                        schedule_msg = f"Scheduled {template_type} reminders"
                    except Exception as e:
                        logger.warning(f"Failed to schedule {name}: {e}")
                        schedule_msg = "Habit created but scheduling failed"
                else:
                    schedule_msg = "No schedule created"
                
                # Success response
                embed = discord.Embed(
                    title="✅ Multi-Scale Habit Created!",
                    description=f"**{name}** is ready to help you build consistency!",
                    color=discord.Color.green()
                )
                
                embed.add_field(
                    name="📋 details",
                    value=f"""
**name:** {habit_tuple[0]}
**description:** {habit_tuple[1]}
**xp reward:** {habit_tuple[2]}
**category:** {habit_tuple[3]}
**schedule:** {template_type} reminders
                    """,
                    inline=False
                )
                
                # Show template examples
                template_info = startup.habit_templates[template_type.lower()]
                embed.add_field(
                    name="💡 template examples",
                    value=", ".join(template_info["examples"]),
                    inline=False
                )
                
                embed.add_field(
                    name="🚀 next steps",
                    value=f"use `!log {name.lower()}` to track completions!",
                    inline=False
                )
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                logger.error(f"Error creating habit from template: {e}")
                await ctx.send(f"❌ Error creating habit: {str(e)}")
                
        except Exception as e:
            logger.error(f"Template habit command error: {e}")
            await ctx.send("❌ Error processing template habit. Please try again.")
    
    @commands.command(name="templates", aliases=["habit_templates", "scales"])
    async def show_templates(self, ctx):
        """Show available habit templates and examples."""
        try:
            from startup_habits import StartupHabits
            startup = StartupHabits(self.bot)
            
            embed = discord.Embed(
                title="🎯 Habit Templates & Time Scales",
                description="create habits at different time scales for comprehensive life management!",
                color=0x00ff88
            )
            
            for template_name, template_info in startup.habit_templates.items():
                examples = ", ".join(template_info["examples"])
                embed.add_field(
                    name=f"📅 {template_name.title()}",
                    value=f"**xp:** {template_info['base_xp']} | **examples:** {examples}",
                    inline=False
                )
            
            embed.add_field(
                name="🚀 usage",
                value="`!add_habit weekly 'Meal Prep' 'Prepare healthy meals'`",
                inline=False
            )
            
            embed.add_field(
                name="💡 pro tip",
                value="different time scales help you manage everything from daily routines to seasonal tasks!",
                inline=False
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Templates command error: {e}")
            await ctx.send("❌ Error showing templates. Please try again.")
    
    @commands.command(name="sync_default_habits", aliases=["update_habits", "create_missing"])
    async def sync_default_habits(self, ctx):
        """Create any missing default habits from the latest updates."""
        try:
            from startup_habits import StartupHabits
            startup = StartupHabits(self.bot)
            
            # Get existing habits
            existing_habits = await self.habit_service.get_all_habits()
            existing_names = {habit.name.lower() for habit in existing_habits}
            
            # Check which default habits are missing
            missing_habits = []
            created_habits = []
            
            for name, description, xp, category, schedule in startup.default_habits:
                if name.lower() not in existing_names:
                    missing_habits.append((name, description, xp, category, schedule))
            
            if not missing_habits:
                embed = discord.Embed(
                    title="✅ All habits up to date!",
                    description="all default habits are already created in the system.",
                    color=discord.Color.green()
                )
                await ctx.send(embed=embed)
                return
            
            # Create missing habits
            for name, description, xp, category, schedule in missing_habits:
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
                        
                        # Schedule if provided
                        if schedule:
                            try:
                                await self.habit_service.schedule_habit_reminder(
                                    habit_name=name,
                                    cron_expression=schedule
                                )
                            except Exception as e:
                                logger.warning(f"Failed to schedule {name}: {e}")
                        
                except Exception as e:
                    logger.error(f"Failed to create habit {name}: {e}")
            
            # Send results
            embed = discord.Embed(
                title="🎯 Default Habits Synced!",
                description=f"created {len(created_habits)} new habits from latest updates!",
                color=discord.Color.green()
            )
            
            if created_habits:
                embed.add_field(
                    name="✅ newly created habits",
                    value="\n".join([f"• {name}" for name in created_habits]),
                    inline=False
                )
            
            embed.add_field(
                name="🚀 next steps",
                value="use `!habits` to see all available habits including the new ones!",
                inline=False
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Sync default habits error: {e}")
            await ctx.send("❌ Error syncing default habits. Please try again.")
    
    # === PROGRESS TRACKING ===
    
    @commands.command(name="today", aliases=["progress", "daily"])
    async def daily_progress(self, ctx):
        """Show today's habit completion progress."""
        try:
            # Get or create user
            user = await self.user_service.get_or_create_user(
                str(ctx.author.id), ctx.author.display_name
            )
            
            # Get today's progress
            progress = await self.habit_service.get_user_daily_progress(user.id)
            
            if not progress:
                embed = discord.Embed(
                    title="📋 No Habits Available",
                    description="No habits are currently set up. Create some habits to get started!",
                    color=discord.Color.blue()
                )
                embed.add_field(
                    name="Get Started",
                    value=f"`{ctx.prefix}create <habit description>` - Create a new habit",
                    inline=False
                )
                await ctx.send(embed=embed)
                return
            
            # Calculate stats
            completed = sum(1 for p in progress if p['completed'])
            total = len(progress)
            total_xp = sum(p['xp_earned'] for p in progress)
            
            embed = discord.Embed(
                title=f"📅 Today's Progress ({completed}/{total})",
                description=f"**{user.username}** • Level {user.level} • {total_xp} XP earned today",
                color=discord.Color.green() if completed == total else discord.Color.blue()
            )
            
            # Group by category
            categories = {}
            for p in progress:
                category = p['habit'].category or 'general'
                if category not in categories:
                    categories[category] = []
                categories[category].append(p)
            
            for category, habits in categories.items():
                habit_lines = []
                for p in habits:
                    status = "✅" if p['completed'] else "⭕"
                    line = f"{status} **{p['habit'].name}** ({p['habit'].base_xp} XP)"
                    if p['completed'] and p['log'] and p['log'].notes:
                        line += f"\n    *{p['log'].notes[:50]}{'...' if len(p['log'].notes) > 50 else ''}*"
                    habit_lines.append(line)
                
                embed.add_field(
                    name=f"{category.title()} ({sum(1 for p in habits if p['completed'])}/{len(habits)})",
                    value="\n".join(habit_lines),
                    inline=False
                )
            
            # Add motivational footer
            if completed == total:
                embed.set_footer(text="🎉 Perfect day! All habits completed!")
            elif completed > 0:
                embed.set_footer(text=f"💪 Keep going! {total - completed} habits remaining.")
            else:
                embed.set_footer(text="🌱 Start your day by completing a habit!")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error showing daily progress: {e}")
            await ctx.send("❌ Error retrieving progress. Please try again.")


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(HabitCommands(bot))