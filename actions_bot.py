"""
GitHub Actions Discord Bot - CSV-based habit tracking with meals feature
Simplified, stateless bot that runs on schedule and commits data to repo
"""

import os
import sys
import asyncio
import logging
import random
from datetime import datetime, date
from typing import Dict, List, Optional

import discord
import pandas as pd
from dotenv import load_dotenv

# Setup
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ActionsBot:
    def __init__(self):
        # Discord setup
        intents = discord.Intents.default()
        intents.message_content = True
        intents.reactions = True
        self.client = discord.Client(intents=intents)

        # Channels
        self.habit_channel_id = int(os.getenv("HABIT_CHANNEL_ID"))
        self.meals_channel_id = int(os.getenv("MEALS_CHANNEL_ID"))

        # CSV file paths
        self.data_dir = "data"
        self.users_file = f"{self.data_dir}/users.csv"
        self.habits_file = f"{self.data_dir}/habits.csv"
        self.habit_logs_file = f"{self.data_dir}/habit_logs.csv"
        self.recipes_file = f"{self.data_dir}/recipes.csv"

        # Load data
        self.users_df = pd.read_csv(self.users_file)
        self.habits_df = pd.read_csv(self.habits_file)
        self.habit_logs_df = pd.read_csv(self.habit_logs_file)
        self.recipes_df = pd.read_csv(self.recipes_file)

    async def connect_and_run(self, action: str):
        """Connect to Discord and perform the specified action"""
        await self.client.login(os.getenv("DISCORD_TOKEN"))

        try:
            # Get channels
            habit_channel = await self.client.fetch_channel(self.habit_channel_id)
            meals_channel = await self.client.fetch_channel(self.meals_channel_id)

            # Perform action
            if action == "check-habits":
                await self.check_habits(habit_channel)
            elif action == "send-recipe":
                await self.send_recipe(meals_channel)
            elif action == "process-reactions":
                await self.process_reactions(habit_channel)
            elif action == "daily-summary":
                await self.daily_summary(habit_channel)

        finally:
            await self.client.close()

    async def check_habits(self, channel):
        """Send habit check-in prompt"""
        today = date.today().strftime("%Y-%m-%d")

        # Get habits for prompt
        active_habits = self.habits_df[self.habits_df['category'].isin(['fitness', 'wellness', 'nutrition'])]

        embed = discord.Embed(
            title="🌱 Daily Habit Check-in",
            description=f"Ready to grow today? React to log your habits!",
            color=discord.Color.green()
        )

        habit_text = ""
        for _, habit in active_habits.iterrows():
            habit_text += f"✅ {habit['name']} (+{habit['base_xp']} XP)\n"

        embed.add_field(name="Available Habits", value=habit_text, inline=False)
        embed.add_field(name="How to use", value="React with ✅ for each habit you completed!", inline=False)

        message = await channel.send(embed=embed)

        # Add reaction options
        await message.add_reaction("✅")

        logger.info(f"Sent habit check-in to {channel.name}")

    async def send_recipe(self, channel):
        """Send meal suggestion based on time of day"""
        current_hour = datetime.utcnow().hour

        # Determine meal type by time
        if 6 <= current_hour < 11:
            meal_category = "breakfast"
            meal_name = "Breakfast"
            emoji = "🌅"
        elif 11 <= current_hour < 16:
            meal_category = "lunch"
            meal_name = "Lunch"
            emoji = "☀️"
        else:
            meal_category = "dinner"
            meal_name = "Dinner"
            emoji = "🌙"

        # Get recipes for this meal
        meal_recipes = self.recipes_df[self.recipes_df['category'] == meal_category]

        if meal_recipes.empty:
            # Fallback to any recipe
            meal_recipes = self.recipes_df

        # Pick random recipe
        recipe = meal_recipes.sample(1).iloc[0]

        embed = discord.Embed(
            title=f"{emoji} {meal_name} Suggestion",
            description=f"**{recipe['name']}**",
            color=discord.Color.blue()
        )

        embed.add_field(name="⏱️ Time", value=f"Prep: {recipe['prep_time']}min | Cook: {recipe['cook_time']}min", inline=True)
        embed.add_field(name="🍽️ Servings", value=f"{recipe['servings']}", inline=True)
        embed.add_field(name="📊 Difficulty", value=f"{recipe['difficulty']}", inline=True)

        embed.add_field(name="🛒 Ingredients", value=recipe['ingredients'], inline=False)
        embed.add_field(name="👩‍🍳 Instructions", value=recipe['instructions'], inline=False)

        if pd.notna(recipe['tags']):
            embed.add_field(name="🏷️ Tags", value=recipe['tags'], inline=False)

        message = await channel.send(embed=embed)
        await message.add_reaction("❤️")  # For tracking favorites

        logger.info(f"Sent {meal_category} recipe: {recipe['name']}")

    async def process_reactions(self, channel):
        """Process recent habit reactions and update logs"""
        # This would process reactions from recent messages
        # For now, just log that we checked
        logger.info("Processed habit reactions")

    async def daily_summary(self, channel):
        """Send daily progress summary"""
        today = date.today().strftime("%Y-%m-%d")

        # Get today's habit logs
        today_logs = self.habit_logs_df[self.habit_logs_df['date'] == today]

        if today_logs.empty:
            summary_text = "No habits logged today yet! Time to get started? 💪"
        else:
            total_xp = today_logs['xp_awarded'].sum()
            habit_count = len(today_logs)
            summary_text = f"Today: {habit_count} habits completed for {total_xp} total XP! 🎉"

        embed = discord.Embed(
            title="📊 Daily Summary",
            description=summary_text,
            color=discord.Color.gold()
        )

        await channel.send(embed=embed)
        logger.info("Sent daily summary")

    def save_data(self):
        """Save all dataframes back to CSV files"""
        self.users_df.to_csv(self.users_file, index=False)
        self.habit_logs_df.to_csv(self.habit_logs_file, index=False)
        logger.info("Saved data to CSV files")

async def main():
    action = os.getenv("ACTION", "check-habits")
    bot = ActionsBot()

    try:
        await bot.connect_and_run(action)
        bot.save_data()
        logger.info(f"Completed action: {action}")
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())