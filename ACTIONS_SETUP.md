# GitHub Actions Setup Guide

## Overview
Your Discord habit bot now runs entirely on GitHub Actions with CSV storage. No database needed!

## Required Secrets
Add these to your GitHub repo settings → Secrets and Variables → Actions:

- `DISCORD_TOKEN` - Your Discord bot token
- `HABIT_CHANNEL_ID` - Channel ID for habit tracking
- `MEALS_CHANNEL_ID` - Channel ID for recipe suggestions

### Getting Channel IDs
Run the helper script to get your channel IDs:
```bash
python get_channel_ids.py
```

This will show all available channels in your Discord server with their IDs.

## Schedule
The bot runs automatically at specific times:
- **8:00-8:15 AM EST**: Morning habits + breakfast suggestions
- **6:00-8:00 PM EST**: Evening exercise + dinner suggestions

### Timing Details
- **Morning (8:00-8:15 AM EST)**: Daily inventory check + morning movement habits + breakfast recipes
- **Evening (6:00-8:00 PM EST)**: Exercise habits + dinner recipes
- **Habit Focus**: 1-2 habits per notification to avoid overwhelm

## Manual Triggers
Go to Actions tab → "Discord Habit Bot" → "Run workflow" to manually:
- `check-habits` - Send habit check-in prompt
- `send-recipe` - Send meal suggestion
- `process-reactions` - Process recent habit reactions
- `daily-summary` - Send progress summary

## Data Structure
All data stored in CSV files under `/data/`:
- `users.csv` - User profiles and XP
- `habits.csv` - Available habits
- `habit_logs.csv` - Daily completions
- `recipes.csv` - Meal database

## Adding Recipes
Simply edit `data/recipes.csv` and commit. Format:
```csv
id,name,prep_time,cook_time,servings,difficulty,category,ingredients,instructions,tags
```

Categories: `breakfast`, `lunch`, `dinner`
Difficulty: `easy`, `medium`, `hard`

### API Integration
The bot now includes **The Meal DB API** integration as a fallback:
- **Free API**: No API key required
- **Automatic Fallback**: Uses local recipes first, then API if needed
- **Source Tracking**: Shows whether recipe came from local database or API
- **Variety**: Adds more recipe options without manual entry

### Recipe Sources
1. **Local Database**: Your curated recipes in `data/recipes.csv`
2. **The Meal DB API**: Free recipe database with thousands of meals
3. **Fallback**: Always ensures a recipe is provided

## Troubleshooting

### Common Issues

**"ValueError: HABIT_CHANNEL_ID environment variable is not set"**
- Make sure you've added the required secrets to your GitHub repository
- Go to Settings → Secrets and Variables → Actions
- Add `HABIT_CHANNEL_ID` and `MEALS_CHANNEL_ID` with the correct channel IDs

**"PyNaCl is not installed, voice will NOT be supported"**
- This is just a warning and won't affect the bot's functionality
- The workflow now includes PyNaCl to suppress this warning

**"Required CSV file not found"**
- Make sure the `data/` directory exists in your repository
- The workflow will create it automatically, but you can also create it manually

### Testing Locally
1. Create a `.env` file with your Discord token:
   ```
   DISCORD_TOKEN=your_bot_token_here
   HABIT_CHANNEL_ID=your_channel_id_here
   MEALS_CHANNEL_ID=your_meals_channel_id_here
   ```
2. Run: `python actions_bot.py`

## Benefits
- ✅ No database hosting costs
- ✅ Full data visibility in git
- ✅ Perfect for Obsidian export
- ✅ Completely serverless
- ✅ Easy recipe management

(Perfect for your workflow - all data committed to repo means easy pipeline to Obsidian markdown files later!)