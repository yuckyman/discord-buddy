"""
GitHub Actions Discord Bot - CSV-based habit tracking with meals feature
Simplified, stateless bot that runs on schedule and commits data to repo
"""

import os
import sys
import asyncio
import logging
import random
import requests
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
        habit_channel_id = os.getenv("HABIT_CHANNEL_ID")
        meals_channel_id = os.getenv("MEALS_CHANNEL_ID")
        
        if not habit_channel_id:
            raise ValueError("HABIT_CHANNEL_ID environment variable is not set")
        if not meals_channel_id:
            raise ValueError("MEALS_CHANNEL_ID environment variable is not set")
            
        self.habit_channel_id = int(habit_channel_id)
        self.meals_channel_id = int(meals_channel_id)

        # CSV file paths
        self.data_dir = "data"
        self.users_file = f"{self.data_dir}/users.csv"
        self.habits_file = f"{self.data_dir}/habits.csv"
        self.habit_logs_file = f"{self.data_dir}/habit_logs.csv"
        self.recipes_file = f"{self.data_dir}/recipes.csv"

        # Load data
        try:
            self.users_df = pd.read_csv(self.users_file)
            self.habits_df = pd.read_csv(self.habits_file)
            self.habit_logs_df = pd.read_csv(self.habit_logs_file)
            self.recipes_df = pd.read_csv(self.recipes_file)
        except FileNotFoundError as e:
            logger.error(f"Required CSV file not found: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading CSV files: {e}")
            raise

    async def connect_and_run(self, action: str):
        """Connect to Discord and perform the specified action"""
        discord_token = os.getenv("DISCORD_TOKEN")
        if not discord_token:
            raise ValueError("DISCORD_TOKEN environment variable is not set")
        await self.client.login(discord_token)

        try:
            # Get channels
            habit_channel = await self.client.fetch_channel(self.habit_channel_id)
            meals_channel = await self.client.fetch_channel(self.meals_channel_id)

            # Perform action
            if action == "check-habits":
                await self.check_habits(habit_channel)
            elif action == "send-recipe":
                await self.send_recipe_with_api(meals_channel)
            elif action == "process-reactions":
                await self.process_reactions(habit_channel)
            elif action == "daily-summary":
                await self.daily_summary(habit_channel)

        finally:
            await self.client.close()

    async def check_habits(self, channel):
        """Send habit check-in prompt based on time of day"""
        today = date.today().strftime("%Y-%m-%d")
        current_hour = datetime.utcnow().hour

        # Determine time of day and select appropriate habits
        if 13 <= current_hour <= 13:  # 8:00-8:15 AM EST (morning)
            time_period = "morning"
            habits = self.habits_df[self.habits_df['time_preference'] == 'morning']
            title = "🌅 Morning Habits"
            description = "Start your day right! Pick 1-2 habits to focus on:"
            color = discord.Color.orange()
        elif 23 <= current_hour or current_hour <= 1:  # 6:00-8:00 PM EST (evening)
            time_period = "evening"
            habits = self.habits_df[self.habits_df['time_preference'] == 'evening']
            title = "🌙 Evening Habits"
            description = "Wind down with some healthy habits! Pick 1-2 to focus on:"
            color = discord.Color.purple()
        else:
            # Fallback to anytime habits
            time_period = "anytime"
            habits = self.habits_df[self.habits_df['time_preference'] == 'anytime']
            title = "🌱 Daily Habits"
            description = "Ready to grow today? Pick 1-2 habits to focus on:"
            color = discord.Color.green()

        # Select 1-2 random habits from the appropriate category
        if len(habits) > 0:
            selected_habits = habits.sample(n=min(2, len(habits)))
        else:
            selected_habits = self.habits_df.sample(n=min(2, len(self.habits_df)))

        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )

        habit_text = ""
        for _, habit in selected_habits.iterrows():
            habit_text += f"✅ **{habit['name']}**\n{habit['description']} (+{habit['base_xp']} XP)\n\n"

        embed.add_field(name="Today's Focus", value=habit_text, inline=False)
        embed.add_field(name="How to use", value="React with ✅ for each habit you completed!", inline=False)

        message = await channel.send(embed=embed)

        logger.info(f"Sent {time_period} habit check-in to {channel.name}")

    async def send_recipe(self, channel):
        """Send meal suggestion based on time of day"""
        current_hour = datetime.utcnow().hour

        # Determine meal type by time (EST times converted to UTC)
        if 13 <= current_hour <= 13:  # 8:00-8:15 AM EST (morning)
            meal_category = "breakfast"
            meal_name = "Breakfast"
            emoji = "🌅"
            description = "Start your day with a nutritious breakfast!"
        elif 23 <= current_hour or current_hour <= 1:  # 6:00-8:00 PM EST (evening)
            meal_category = "dinner"
            meal_name = "Dinner"
            emoji = "🌙"
            description = "End your day with a satisfying dinner!"
        else:
            # Fallback to any meal
            meal_category = "breakfast"
            meal_name = "Meal"
            emoji = "🍽️"
            description = "Here's a meal suggestion for you!"

        # Get recipes for this meal
        meal_recipes = self.recipes_df[self.recipes_df['category'] == meal_category]

        if meal_recipes.empty:
            # Fallback to any recipe
            meal_recipes = self.recipes_df

        # Pick random recipe
        recipe = meal_recipes.sample(1).iloc[0]

        embed = discord.Embed(
            title=f"{emoji} {meal_name} Suggestion",
            description=description,
            color=discord.Color.blue()
        )

        embed.add_field(name="🍽️ Recipe", value=f"**{recipe['name']}**", inline=False)
        embed.add_field(name="⏱️ Time", value=f"Prep: {recipe['prep_time']}min | Cook: {recipe['cook_time']}min", inline=True)
        embed.add_field(name="👥 Servings", value=f"{recipe['servings']}", inline=True)
        embed.add_field(name="📊 Difficulty", value=f"{recipe['difficulty']}", inline=True)

        embed.add_field(name="🛒 Ingredients", value=recipe['ingredients'], inline=False)
        embed.add_field(name="👩‍🍳 Instructions", value=recipe['instructions'], inline=False)

        if pd.notna(recipe['tags']):
            embed.add_field(name="🏷️ Tags", value=recipe['tags'], inline=False)

        message = await channel.send(embed=embed)
        await message.add_reaction("❤️")  # For tracking favorites

        logger.info(f"Sent {meal_category} recipe: {recipe['name']}")

    def fetch_api_recipe(self, meal_category: str) -> Optional[Dict]:
        """Fetch a random recipe from The Meal DB API"""
        try:
            # The Meal DB API endpoints
            if meal_category == "breakfast":
                # Search for breakfast-related meals
                url = "https://www.themealdb.com/api/json/v1/1/filter.php?c=Breakfast"
            elif meal_category == "dinner":
                # Search for dinner-related meals
                url = "https://www.themealdb.com/api/json/v1/1/filter.php?c=Dessert"  # Fallback to dessert for variety
            else:
                # Get random meal
                url = "https://www.themealdb.com/api/json/v1/1/random.php"
            
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if data.get('meals') and len(data['meals']) > 0:
                # Get a random meal from the results
                meal = random.choice(data['meals'])
                
                # Get full details for the meal
                meal_id = meal['idMeal']
                detail_url = f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={meal_id}"
                detail_response = requests.get(detail_url, timeout=5)
                detail_response.raise_for_status()
                detail_data = detail_response.json()
                
                if detail_data.get('meals') and len(detail_data['meals']) > 0:
                    full_meal = detail_data['meals'][0]
                    
                    # Format ingredients and instructions
                    ingredients = []
                    for i in range(1, 21):  # The API has up to 20 ingredients
                        ingredient = full_meal.get(f'strIngredient{i}')
                        measure = full_meal.get(f'strMeasure{i}')
                        if ingredient and ingredient.strip():
                            ingredients.append(f"{measure} {ingredient}".strip())
                    
                    return {
                        'name': full_meal['strMeal'],
                        'category': meal_category,
                        'ingredients': ', '.join(ingredients),
                        'instructions': full_meal['strInstructions'],
                        'prep_time': '15',  # Default since API doesn't provide this
                        'cook_time': '30',  # Default since API doesn't provide this
                        'servings': '4',    # Default since API doesn't provide this
                        'difficulty': 'medium',  # Default since API doesn't provide this
                        'tags': f"api,{full_meal.get('strCategory', '').lower()},{full_meal.get('strArea', '').lower()}",
                        'source': 'The Meal DB API'
                    }
            
        except Exception as e:
            logger.warning(f"Failed to fetch API recipe: {e}")
        
        return None

    async def send_recipe_with_api(self, channel):
        """Send meal suggestion with API integration as fallback"""
        current_hour = datetime.utcnow().hour

        # Determine meal type by time (EST times converted to UTC)
        if 13 <= current_hour <= 13:  # 8:00-8:15 AM EST (morning)
            meal_category = "breakfast"
            meal_name = "Breakfast"
            emoji = "🌅"
            description = "Start your day with a nutritious breakfast!"
        elif 23 <= current_hour or current_hour <= 1:  # 6:00-8:00 PM EST (evening)
            meal_category = "dinner"
            meal_name = "Dinner"
            emoji = "🌙"
            description = "End your day with a satisfying dinner!"
        else:
            # Fallback to any meal
            meal_category = "breakfast"
            meal_name = "Meal"
            emoji = "🍽️"
            description = "Here's a meal suggestion for you!"

        # Try to get a recipe from local CSV first
        meal_recipes = self.recipes_df[self.recipes_df['category'] == meal_category]
        
        if not meal_recipes.empty:
            # Use local recipe
            recipe = meal_recipes.sample(1).iloc[0]
            source = "Local Recipe Database"
        else:
            # Try API as fallback
            api_recipe = self.fetch_api_recipe(meal_category)
            if api_recipe:
                recipe = api_recipe
                source = "The Meal DB API"
            else:
                # Final fallback to any local recipe
                recipe = self.recipes_df.sample(1).iloc[0]
                source = "Local Recipe Database (Fallback)"

        embed = discord.Embed(
            title=f"{emoji} {meal_name} Suggestion",
            description=description,
            color=discord.Color.blue()
        )

        embed.add_field(name="🍽️ Recipe", value=f"**{recipe['name']}**", inline=False)
        embed.add_field(name="⏱️ Time", value=f"Prep: {recipe['prep_time']}min | Cook: {recipe['cook_time']}min", inline=True)
        embed.add_field(name="👥 Servings", value=f"{recipe['servings']}", inline=True)
        embed.add_field(name="📊 Difficulty", value=f"{recipe['difficulty']}", inline=True)

        embed.add_field(name="🛒 Ingredients", value=recipe['ingredients'], inline=False)
        embed.add_field(name="👩‍🍳 Instructions", value=recipe['instructions'], inline=False)

        if pd.notna(recipe.get('tags')):
            embed.add_field(name="🏷️ Tags", value=recipe['tags'], inline=False)
        
        embed.add_field(name="📚 Source", value=source, inline=False)

        message = await channel.send(embed=embed)
        await message.add_reaction("❤️")  # For tracking favorites

        logger.info(f"Sent {meal_category} recipe from {source}: {recipe['name']}")

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