# 🔌 Discord Habit Bot - API Reference

## 📋 Service Layer APIs

This document defines the standardized interfaces between different domains of the habit tracking system.

## 🎯 HabitService API

### Core Operations
```python
# Habit Management
async def create_habit(name: str, description: str = None, base_xp: int = 10, category: str = "wellness") -> Habit
async def get_habit_by_name(name: str) -> Optional[Habit]
async def get_all_habits(include_inactive: bool = False) -> List[Habit]
async def get_habits_by_category(category: str) -> List[Habit]

# Habit Logging
async def log_habit_completion(user_id: int, habit_id: int, notes: str = None, source: str = "command") -> Tuple[HabitLog, bool]

# Scheduling
async def schedule_habit_reminder(habit_name: str, cron_expression: str) -> PromptSchedule
async def modify_habit_schedule(habit_name: str, new_time: str, frequency: str = "daily") -> str

# Analytics
async def get_habit_count_stats(user_id: int, habit_name: str) -> Dict[str, Any]
def extract_count_from_notes(notes: str) -> Optional[int]
```

### Multi-Scale Templates
```python
# Template System
def create_habit_from_template(name: str, description: str, template_type: str, category: str = "wellness", **kwargs) -> tuple

# Available Templates: daily, weekly, monthly, quarterly, yearly
# Returns: (name, description, xp, category, cron_expression)
```

## 👤 UserService API

### User Management
```python
async def get_or_create_user(discord_id: str, username: str) -> User
async def get_user_by_discord_id(discord_id: str) -> Optional[User]
async def update_user_activity(user_id: int) -> None
async def add_xp(user_id: int, xp_amount: int) -> Tuple[int, bool]  # Returns (new_total, leveled_up)
```

### Statistics
```python
async def get_user_stats(user_id: int) -> Dict[str, Any]
async def get_leaderboard(metric: str = "xp", limit: int = 10) -> List[Dict[str, Any]]
# Metrics: xp, level, gold, streak
```

## 🔥 StreakService API

### Streak Management
```python
async def update_streak(user_id: int, habit_id: int) -> Tuple[int, List[str]]  # Returns (streak_length, rewards)
async def get_user_streak(user_id: int, habit_id: int) -> Optional[Streak]
async def get_user_all_streaks(user_id: int) -> List[Streak]

# Milestone calculation
def calculate_milestone_bonus(streak_length: int) -> int
```

## 🎁 RewardService API

### Reward System
```python
async def process_completion_rewards(user_id: int, habit: Habit) -> List[str]
async def roll_loot(user_id: int, base_xp: int) -> List[str]
async def get_user_inventory(user_id: int) -> List[InventoryItem]
async def get_recent_rewards(user_id: int, limit: int = 10) -> List[Reward]
```

## ⏰ PromptService API

### Scheduled Prompts
```python
async def start_scheduler() -> None
async def stop_scheduler() -> None
async def handle_reaction(user_id: int, prompt_schedule_id: int, emoji: str) -> bool
```

## 🔮 ObsidianService API

### Vault Integration
```python
async def create_daily_note(date: str = None) -> bool
async def sync_daily_habits(user_id: int, habit_logs: List[Dict], date: str = None) -> bool
async def add_task_to_note(task: str, date: str = None) -> bool
async def get_vault_health() -> Dict[str, Any]
```

## 📊 Data Transfer Objects

### Habit Statistics Response
```python
{
    "habit_name": str,
    "total_count": int,        # For count-based habits
    "average": float,          # Average per session
    "best": int,              # Best single session
    "worst": int,             # Lowest session
    "total_sessions": int,     # Number of completed sessions
    "recent_logs": List[Dict]  # Last 10 sessions with details
}
```

### User Statistics Response
```python
{
    "user": {
        "discord_id": str,
        "username": str,
        "level": int,
        "total_xp": int,
        "gold": int
    },
    "habits": {
        "total_habits": int,
        "completed_today": int,
        "completion_rate": float
    },
    "streaks": {
        "active_streaks": int,
        "longest_streak": int,
        "total_streak_days": int
    }
}
```

### Leaderboard Response
```python
[
    {
        "rank": int,
        "user": {
            "discord_id": str,
            "username": str
        },
        "value": int,           # XP, level, gold, or streak length
        "metric": str          # "xp", "level", "gold", "streak"
    }
]
```

## 🎮 Command Interface Standards

### Success Response Format
```python
embed = discord.Embed(
    title="✅ Success Title",
    description="clear description of what happened",
    color=discord.Color.green()
)
embed.add_field(name="📋 details", value="structured information", inline=False)
embed.add_field(name="🚀 next steps", value="guidance for user", inline=False)
```

### Error Response Format
```python
embed = discord.Embed(
    title="❌ Error Title", 
    description="clear explanation of the problem",
    color=discord.Color.red()
)
embed.add_field(name="💡 suggestion", value="how to fix or what to try", inline=False)
```

### Information Response Format
```python
embed = discord.Embed(
    title="📊 Information Title",
    description="contextual overview",
    color=0x00ff88  # Consistent brand color
)
# Multiple fields for organized data display
```

## 🔄 Event Flow Patterns

### Habit Completion Flow
1. User command: `!log exercise - great workout!`
2. `HabitCommands.log_habit()` parses input
3. `UserService.get_or_create_user()` ensures user exists
4. `HabitService.get_habit_by_name()` finds habit
5. `HabitService.log_habit_completion()` creates log entry
6. `StreakService.update_streak()` updates streak data
7. `RewardService.process_completion_rewards()` handles rewards
8. Return formatted success response with XP/streak/rewards

### Scheduled Reminder Flow
1. Cron trigger activates in `PromptService`
2. `PromptService._send_scheduled_prompt()` posts to Discord
3. User reacts with ✅ emoji
4. `PromptService.handle_reaction()` processes reaction
5. `HabitService.log_habit_completion()` auto-logs if configured
6. Standard completion flow continues

### Multi-Scale Habit Creation
1. User command: `!add_habit weekly "Meal Prep" "Prepare weekly meals"`
2. `HabitCommands.add_habit_from_template()` validates template type
3. `StartupHabits.create_habit_from_template()` generates habit data
4. `HabitService.create_habit()` persists to database
5. `HabitService.schedule_habit_reminder()` sets up automation
6. Return template information and usage guidance

## 🛡️ Error Handling Standards

### Service Layer Errors
- **ValidationError**: Invalid input parameters
- **NotFoundError**: Requested resource doesn't exist  
- **DuplicateError**: Resource already exists
- **DatabaseError**: Database operation failed
- **ExternalError**: Third-party service failure

### Error Response Patterns
```python
# Service returns error dict
{"error": "Habit 'invalid' not found", "code": "NOT_FOUND"}

# Command layer converts to user-friendly message
"❌ Habit 'invalid' not found. Use `!habits` to see available habits."
```

## 🔧 Configuration Standards

### Environment Variables
```bash
# Core Configuration
DISCORD_TOKEN=required
DATABASE_URL=sqlite:///./habit_bot.db
COMMAND_PREFIX=!
TIMEZONE=UTC

# Feature Toggles
DEBUG=false
LOG_LEVEL=INFO

# Integration Settings  
OBSIDIAN_VAULT_PATH=/path/to/vault
ANKI_DECK=Habits
```

### YAML Configuration
```yaml
# prompts.yml structure
prompts:
  - name: "Human Readable Name"
    cron: "0 7 * * *"
    timezone: "America/New_York"
    message: |
      emoji **bold text**
      
      description and context
      
      🎯 structured list:
      • item one
      • item two
      
      call to action!
    channel_id: 1234567890123456789
    target_users: null  # or ["user_id1", "user_id2"]
```

This API reference ensures consistent communication patterns across all domains of the habit tracking system.