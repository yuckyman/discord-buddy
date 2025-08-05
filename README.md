# Discord Habit Bot 🌱

A comprehensive Discord bot for habit tracking, gamification, and productivity enhancement. Built with natural language processing for easy habit management and featuring reward systems, streak tracking, and scheduled reminders.

## ✨ Features

### 🎯 Habit Management
- **Natural Language Creation**: Create habits using conversational commands
  - `!create add habit meditation 20 minutes daily at 7am for mindfulness`
  - `!create habit: exercise (15 xp) - daily workout routine`
- **Flexible Scheduling**: Set custom reminder times and frequencies
- **Dynamic Categories**: Automatic categorization based on habit keywords
- **Smart XP Calculation**: Intelligent XP assignment based on activity type and duration

### 🎮 Gamification System
- **Experience Points (XP)**: Earn XP for completing habits
- **Level Progression**: Level up based on total XP earned
- **RNG Rewards**: D100 loot system with rare items and bonus XP
- **Gold Economy**: Earn and spend gold on future features
- **Achievement System**: Unlock items and titles for milestones

### 🔥 Streak Tracking
- **Daily Streaks**: Track consecutive days of habit completion
- **Milestone Bonuses**: Extra XP for 3, 7, 14, 30+ day streaks
- **Streak Recovery**: Grace period and recovery mechanics
- **Leaderboards**: Compete with others on streak lengths

### 📊 Progress Tracking
- **Daily Progress**: Visual progress bars for today's habits
- **Statistics Dashboard**: Comprehensive stats including levels, streaks, and completion rates
- **Leaderboards**: XP, level, gold, and streak leaderboards
- **Historical Data**: Track long-term progress and trends

### ⏰ Automated Reminders
- **Scheduled Prompts**: Cron-based habit reminders
- **Reaction Logging**: React with ✅ to log habit completion
- **Smart Scheduling**: Natural language time parsing
- **Timezone Support**: Configurable timezone handling

### 🔗 Integrations
- **Obsidian Sync**: Export habit data to Obsidian vault (planned)
- **Anki Integration**: Spaced repetition for habit reflection (planned)
- **Custom Templates**: Jinja2 templates for data export

## 🚀 Quick Start

### Prerequisites
- Debian/Ubuntu Linux system
- Root access for installation
- Discord bot token ([Create one here](https://discord.com/developers/applications))

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd discord-habit-bot
   ```

2. **Run the setup script**:
   ```bash
   sudo ./setup.sh
   ```

3. **Configure the bot**:
   ```bash
   sudo nano /opt/discord-habit-bot/.env
   ```
   Add your Discord token and other settings.

4. **Start the bot**:
   ```bash
   sudo systemctl start habit-bot
   ```

### Manual Setup (Alternative)

If you prefer manual setup or need to customize the installation:

1. **Install Miniconda**:
   ```bash
   wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
   bash Miniconda3-latest-Linux-x86_64.sh
   ```

2. **Create conda environment**:
   ```bash
   conda env create -f environment.yml
   conda activate habit-bot
   ```

3. **Set up database**:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   alembic upgrade head
   ```

4. **Run the bot**:
   ```bash
   python bot.py
   ```

## 💬 Commands

### Habit Management
- `!create <description>` - Create new habit with natural language
- `!log <habit> [- notes]` - Log habit completion
- `!habits [category]` - List available habits
- `!schedule <habit> at <time> [frequency]` - Schedule reminders
- `!today` - Show today's progress

### Statistics & Progress
- `!stats [@user]` - Show user statistics
- `!leaderboard [xp|level|gold|streak]` - View leaderboards
- `!inventory` - Show items and gold
- `!rewards [limit]` - Show recent rewards

### Admin Commands
- `!admin_status` - Bot status (Admin only)
- `!sync` - Sync slash commands (Admin only)

## 🎯 Usage Examples

### Creating Habits
```
# Simple habit creation
!create habit: read for 30 minutes

# Detailed habit with scheduling
!create add habit meditation 20 minutes daily at 7am for mindfulness

# Habit with custom XP
!create new habit: exercise (15 xp) - daily workout routine

# Recurring reminder
!create habit drink water every 2 hours
```

### Logging Completions
```
# Basic logging
!log meditation

# With notes
!log exercise - had a great gym session today!

# Alternative commands
!done reading
!complete water
```

### Viewing Progress
```
# Today's progress
!today

# Personal stats
!stats

# View someone else's stats
!stats @username

# Leaderboards
!leaderboard xp
!leaderboard streak
```

## 🛠️ System Management

### Service Management
```bash
# Start/stop/restart
sudo systemctl start habit-bot
sudo systemctl stop habit-bot
sudo systemctl restart habit-bot

# View status
sudo systemctl status habit-bot

# View logs
sudo journalctl -u habit-bot -f

# Enable/disable auto-start
sudo systemctl enable habit-bot
sudo systemctl disable habit-bot
```

### Using Management Script
```bash
cd /opt/discord-habit-bot

# Service control
./manage.sh start
./manage.sh stop
./manage.sh restart
./manage.sh status

# View logs
./manage.sh logs

# Update bot
./manage.sh update
```

## 🏗️ Architecture

### Core Components
- **Bot Core** (`bot.py`): Main Discord.py bot with service coordination
- **Database Layer** (`database.py`, `models.py`): SQLAlchemy async ORM
- **Service Layer** (`services/`): Business logic and feature implementation
- **Command Layer** (`cogs/`): Discord command handlers
- **Scheduler** (`prompt_service.py`): APScheduler for automated tasks

### Key Services
- **HabitService**: Habit CRUD, natural language parsing, scheduling
- **UserService**: User management, XP/level calculations
- **RewardService**: RNG loot system, inventory management
- **StreakService**: Streak tracking, milestone bonuses
- **PromptService**: Scheduled reminders, reaction handling

### Database Design
- **Async SQLAlchemy**: Modern async/await patterns
- **Alembic Migrations**: Version-controlled schema changes
- **Soft Deletes**: Data preservation with deactivation flags
- **Comprehensive Relationships**: Foreign keys and proper joins

## 🔧 Configuration

### Environment Variables
```bash
# Required
DISCORD_TOKEN=your_bot_token
DATABASE_URL=sqlite:///./habit_bot.db

# Optional
COMMAND_PREFIX=!
TIMEZONE=UTC
DEBUG=false
OBSIDIAN_VAULT_PATH=/path/to/vault
QUIZ_CHANNEL_ID=channel_id
ANKI_DECK=Habits
LOG_LEVEL=INFO
```

### Scheduling Format
Uses standard cron expressions:
```
# Daily at 7 AM
0 7 * * *

# Every Monday at 9 AM
0 9 * * 1

# Every 2 hours
0 */2 * * *
```

## 🧪 Testing

Run the test suite:
```bash
conda activate habit-bot
pytest tests/ -v
```

## 📈 Monitoring

### Log Files
- Application logs: `/opt/discord-habit-bot/logs/habit_bot.log`
- System logs: `journalctl -u habit-bot`

### Health Checks
- Bot status: `!admin_status`
- Service status: `systemctl status habit-bot`
- Database health: Check log files for connection errors

## 🔐 Security

### Service Security
- Dedicated user account (`habitbot`)
- Restricted filesystem access
- No new privileges
- Private temporary files

### Data Security
- Environment variables for secrets
- SQL injection protection via ORM
- Input validation and sanitization
- Graceful error handling

## 🛣️ Roadmap

### Phase 1 ✅
- [x] Core habit tracking
- [x] Natural language parsing
- [x] Basic gamification (XP, levels)
- [x] Streak tracking
- [x] Scheduled prompts

### Phase 2 🚧
- [ ] Advanced Obsidian integration
- [ ] Anki spaced repetition system
- [ ] Quiz generation from habits
- [ ] Advanced analytics dashboard

### Phase 3 📋
- [ ] Web dashboard
- [ ] Mobile app companion
- [ ] Team challenges
- [ ] Social features
- [ ] Advanced AI insights

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

### Development Setup
```bash
# Clone your fork
git clone <your-fork-url>
cd discord-habit-bot

# Set up development environment
conda env create -f environment.yml
conda activate habit-bot

# Install development dependencies
pip install -e .

# Run tests
pytest
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Discord.py community for excellent documentation
- SQLAlchemy team for robust ORM functionality
- APScheduler for reliable task scheduling
- The habit tracking and productivity communities for inspiration

## 🆘 Support

### Common Issues

**Bot not responding**:
- Check `systemctl status habit-bot`
- Verify Discord token in `.env`
- Check logs with `journalctl -u habit-bot`

**Database errors**:
- Run `alembic upgrade head`
- Check file permissions
- Verify SQLite file exists

**Scheduling issues**:
- Verify timezone settings
- Check cron expression syntax
- Ensure proper channel permissions

### Getting Help
1. Check the logs first: `sudo journalctl -u habit-bot -f`
2. Verify configuration: `sudo nano /opt/discord-habit-bot/.env`
3. Restart the service: `sudo systemctl restart habit-bot`
4. Create an issue on GitHub with log output

---

Made with ❤️ for the habit-building community. Start small, stay consistent, level up! 🚀