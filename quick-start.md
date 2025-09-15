# 🚀 Discord Habit Bot - Quick Start Guide

## 🔄 Making the Bot Persistent

### Option 1: GitHub Actions (Recommended) 🆕

The bot now runs entirely on GitHub Actions - no server needed!

1. **Fork this repository**
2. **Set up GitHub Secrets**:
   - Go to Settings → Secrets and Variables → Actions
   - Add: `DISCORD_TOKEN`, `HABIT_CHANNEL_ID`, `MEALS_CHANNEL_ID`, `TIMEZONE`
3. **Get Channel IDs**:
   ```bash
   python get_channel_ids.py
   ```
4. **That's it!** The bot will run automatically on schedule

See [ACTIONS_SETUP.md](ACTIONS_SETUP.md) for detailed setup instructions.

### Option 2: Systemd Service (Local Server)

1. **Install as service:**
   ```bash
   ./manage-bot.sh install-service
   ```

2. **Start the service:**
   ```bash
   sudo systemctl start discord-habit-bot
   ```

3. **Enable auto-start on boot:**
   ```bash
   sudo systemctl enable discord-habit-bot
   ```

4. **Check status:**
   ```bash
   sudo systemctl status discord-habit-bot
   ```

5. **View logs:**
   ```bash
   journalctl -u discord-habit-bot -f
   ```

### Option 2: Background Process

1. **Start in background:**
   ```bash
   ./manage-bot.sh start
   ```

2. **Check status:**
   ```bash
   ./manage-bot.sh status
   ```

3. **View logs:**
   ```bash
   ./manage-bot.sh logs
   ```

4. **Stop bot:**
   ```bash
   ./manage-bot.sh stop
   ```

## 🎯 Time-Specific Habit System

The bot now organizes habits by time of day for focused notifications:

### Morning Habits (8:00-8:15 AM EST)
- **Daily Inventory Check** (20 XP) - Reflect on yesterday, plan today
- **Morning Movement** (15 XP) - 5-10 minutes of stretching or light exercise
- **Meditation** (10 XP) - 10 minutes of mindfulness
- **Reading** (12 XP) - Read for at least 15 minutes
- **Hydration** (5 XP) - Drink adequate water

### Evening Habits (6:00-8:00 PM EST)
- **Evening Workout** (25 XP) - 30+ minutes of exercise or physical activity
- **Strength Training** (30 XP) - Weight training or bodyweight exercises
- **Cardio Session** (25 XP) - Running, cycling, or other cardio
- **Sleep Schedule** (10 XP) - Go to bed on time

### Meal Suggestions 🍽️
- **Breakfast** (8:00-8:15 AM EST) - Local recipes + The Meal DB API
- **Dinner** (6:00-8:00 PM EST) - Local recipes + The Meal DB API

2. **Sends startup notification** when bot comes online:
   - Welcome message with quick start tips
   - Reminds users of available commands
   - Encourages habit tracking

3. **Configurable prompts** via `configs/prompts.yml`:
   - Scheduled reminders throughout the day
   - Custom messages and timing
   - Channel and user targeting

## 🔧 Management Commands

### Bot Control
```bash
./manage-bot.sh start          # Start bot
./manage-bot.sh stop           # Stop bot  
./manage-bot.sh restart        # Restart bot
./manage-bot.sh status         # Check status
./manage-bot.sh logs           # View logs
```

### Service Management
```bash
./manage-bot.sh install-service    # Install systemd service
./manage-bot.sh remove-service     # Remove systemd service
sudo systemctl start discord-habit-bot    # Start service
sudo systemctl stop discord-habit-bot     # Stop service
```

## 🎮 Discord Commands

### Habit Management
- `!create meditation 10 minutes daily` - Create habits with natural language
- `!log exercise - great workout!` - Log completions with notes
- `!today` - Check today's progress
- `!stats` - View your statistics and achievements

### Obsidian Integration
- `!dnote get` - View today's daily note
- `!dnote create` - Create daily note
- `!task Buy groceries` - Add task to daily note
- `!obsync` - Sync habits to Obsidian
- `!obsidian_health` - Check integration status

### Gamification
- `!leaderboard xp` - View XP leaderboard
- `!inventory` - Check your items and gold
- `!rewards` - See recent rewards

## 🔮 Configuration

### Environment Variables (.env)
```env
DISCORD_TOKEN=your_bot_token_here
DATABASE_URL=sqlite:///./habit_bot.db
OBSIDIAN_VAULT_PATH=/path/to/vault
TIMEZONE=America/New_York
```

### Startup Behavior
Edit `startup_habits.py` to customize:
- Default habits created for new users
- Startup notification message
- Habit scheduling and XP rewards

### Scheduled Prompts
Edit `configs/prompts.yml` to customize:
- Daily motivation messages
- Reminder timing and frequency
- Channel targeting

## 🚀 Quick Deploy

1. **Make sure everything is working:**
   ```bash
   conda activate habit-bot
   python -c "import bot; print('✅ Bot ready')"
   ```

2. **Install as persistent service:**
   ```bash
   ./manage-bot.sh install-service
   sudo systemctl start discord-habit-bot
   ```

3. **Verify it's running:**
   ```bash
   sudo systemctl status discord-habit-bot
   journalctl -u discord-habit-bot -f
   ```

4. **Test in Discord:**
   - Bot should send startup notification
   - Try `!create meditation 5 minutes daily`
   - Try `!today` to see progress

## 🛠️ Troubleshooting

### Bot won't start
```bash
# Check logs
journalctl -u discord-habit-bot -n 50

# Check permissions
ls -la /home/ian/scripts/discord-buddy/

# Test manually
conda activate habit-bot && python bot.py
```

### Missing default habits
```bash
# Recreate defaults
conda activate habit-bot
python -c "
import asyncio
from startup_habits import run_startup_sequence
from bot import HabitBot

async def create_defaults():
    bot = HabitBot()
    result = await run_startup_sequence(bot, send_notification=False)
    print(f'Created {result.get(\"habits_created\", 0)} habits')

asyncio.run(create_defaults())
"
```

### Obsidian not syncing
- Check `!obsidian_health`
- Verify `OBSIDIAN_VAULT_PATH` in .env
- Test with `!dnote create`

Your habit bot is now fully persistent and will automatically create engaging startup experiences! 🎉