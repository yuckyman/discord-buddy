# 🎯 Discord Server Configuration Guide

## 📍 Your Server Setup

**Guild**: habit tracking (ID: 954466244092891146)

### 📱 Available Channels & Their Purpose

| Channel | ID | Purpose | Bot Usage |
|---------|----|---------|-----------| 
| **#habits** | `954466311596027984` | Main habit discussions | Startup messages, evening reflections |
| **#reminders** | `1392910044923953172` | Scheduled reminders | Morning/exercise/mindfulness prompts |
| **#progress** | `1392910058840653834` | Daily progress tracking | Progress check-ins, habit logs |
| **#reports** | `1392911676008960060` | Weekly/monthly reports | Weekly summaries, leaderboards |
| **#commands** | `1392911686737854625` | Bot testing & commands | Command testing, bot health checks |
| **#notes** | `954466276896559185` | General notes | Available for custom use |
| **#stream** | `954466244092891149` | General chat | Available for custom use |

## 🔮 Obsidian Configuration Updated

**Daily Notes Path**: `/home/ian/WINTERMUTE/1_life/13_journal/`

### File Structure:
```
/home/ian/WINTERMUTE/
├── 1_life/
│   └── 13_journal/          # Daily notes location
│       ├── 2025-08-05.md    # Today's note
│       ├── 2025-08-06.md    # Tomorrow's note
│       └── ...
└── Habits/                  # Individual habit tracking
    ├── morning-meditation.md
    ├── daily-exercise.md
    └── ...
```

## ⏰ Scheduled Prompt Configuration

### Current Schedule:
- **7:00 AM** - Morning Kickstart → #reminders
- **12:00 PM** - Mindfulness Moment → #reminders  
- **6:00 PM** - Exercise Time (weekdays) → #reminders
- **8:00 PM** - Daily Progress Check → #progress
- **9:00 PM** - Evening Reflection → #habits
- **Sunday 9:00 AM** - Weekly Report → #reports
- **Monday 10:00 AM** - Bot Health Check → #commands
- **Bot Startup** - Welcome Message → #habits

## 🛠️ Environment Variables to Add

Add these to your `.env` file:

```env
# Discord Channel Configuration
MAIN_CHANNEL_ID=954466311596027984          # #habits
REMINDERS_CHANNEL_ID=1392910044923953172    # #reminders
PROGRESS_CHANNEL_ID=1392910058840653834     # #progress
REPORTS_CHANNEL_ID=1392911676008960060      # #reports
COMMANDS_CHANNEL_ID=1392911686737854625     # #commands
NOTES_CHANNEL_ID=954466276896559185         # #notes
QUIZ_CHANNEL_ID=1392911686737854625         # #commands for quizzes
```

## 🎯 How Your Bot Will Work

### Daily Flow:
1. **7:00 AM** - Bot sends morning motivation to #reminders
2. **Throughout day** - Users log habits using `!log exercise`, etc.
3. **12:00 PM** - Mindfulness check-in reminder
4. **6:00 PM** - Exercise reminder (weekdays only)
5. **8:00 PM** - Progress check prompt in #progress
6. **9:00 PM** - Evening reflection in #habits

### Weekly Flow:
- **Sunday 9:00 AM** - Weekly report and leaderboards in #reports
- **Monday 10:00 AM** - Bot health check in #commands

### Obsidian Integration:
- Daily notes created/updated in `1_life/13_journal/`
- Habit completions synced to daily notes
- Individual habit tracking in `Habits/` folder
- Tasks added via `!task` command

## 🚀 Commands by Channel

### #habits (Main Discussion)
- `!create meditation 10 minutes daily` - Create new habits
- `!habits` - List all habits
- `!obsidian_info` - Obsidian features

### #progress (Tracking)
- `!log exercise - great workout!` - Log completions
- `!today` - Daily progress
- `!stats` - Personal statistics

### #reports (Analytics)
- `!leaderboard xp` - XP leaderboard
- `!leaderboard streak` - Streak competition
- `!rewards` - Recent achievements

### #commands (Testing)
- `!admin_status` - Bot health
- `!obsidian_health` - Obsidian sync status
- `!sync` - Sync slash commands

### #reminders (Automated)
- Receives scheduled motivation messages
- Users react with ✅ to acknowledge

## 💡 Customization Tips

### Adding New Prompts:
Edit `configs/prompts.yml` to add custom reminders:

```yaml
- name: "Custom Reminder"
  cron: "0 15 * * *"  # 3 PM daily
  timezone: "America/New_York"
  message: "Your custom message here!"
  channel_id: 1392910044923953172  # #reminders
  target_users: null
```

### Targeting Specific Users:
```yaml
target_users: ["user_discord_id_1", "user_discord_id_2"]
```

### Different Timezones:
All prompts currently use `America/New_York` timezone. Adjust as needed.

Your habit tracking server is now professionally configured! 🎉