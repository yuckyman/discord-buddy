# 🏗️ Discord Habit Bot - Information Architecture

## 📋 Overview

The Discord Habit Bot is organized into multiple domains that communicate through well-defined interfaces. This document outlines the information architecture and communication patterns.

## 🎯 Domain Architecture

### 1. **User Interface Domain** (Discord Commands)
**Purpose**: User interaction and command processing  
**Location**: `cogs/`  
**Components**:
- `habit_commands.py` - Habit CRUD operations
- `stats_commands.py` - Analytics and leaderboards  
- `admin_commands.py` - System administration
- `obsidian_commands.py` - External integrations
- `help_commands.py` - Documentation and guidance

**Communication**: Receives user input → Calls service layer → Returns formatted responses

### 2. **Business Logic Domain** (Services)
**Purpose**: Core functionality and business rules  
**Location**: `services/`  
**Components**:
- `habit_service.py` - Habit management, logging, scheduling
- `user_service.py` - User lifecycle, XP/level calculations
- `streak_service.py` - Streak tracking and milestone rewards
- `reward_service.py` - Gamification and loot systems
- `prompt_service.py` - Automated scheduling and reminders
- `obsidian_service.py` - External vault synchronization

**Communication**: Stateless services → Database operations → Return structured data

### 3. **Data Persistence Domain** (Database)
**Purpose**: Data storage and retrieval  
**Location**: `models.py`, `database.py`, `alembic/`  
**Components**:
- **Core Models**: User, Habit, HabitLog, Streak
- **Gamification**: Reward, InventoryItem
- **Scheduling**: PromptSchedule, PromptReaction
- **Future**: Quiz, QuizResponse

**Communication**: SQLAlchemy ORM → Async database operations → Structured queries

### 4. **Configuration Domain** (Settings & Templates)
**Purpose**: System configuration and templates  
**Location**: `configs/`, `startup_habits.py`  
**Components**:
- `prompts.yml` - Scheduled message templates
- `startup_habits.py` - Default habits and multi-scale templates
- Environment variables - System configuration

**Communication**: YAML/Python configs → Service initialization → Runtime behavior

### 5. **External Integration Domain** (APIs & Files)
**Purpose**: Third-party integrations  
**Location**: `services/obsidian_service.py`, future API integrations  
**Components**:
- Obsidian vault file operations
- Future: Anki deck synchronization
- Future: Calendar integrations

**Communication**: Service layer → External APIs/Files → Data transformation

## 📊 Information Flow Patterns

### 1. **Command Processing Flow**
```
Discord User Input → Cog Command Handler → Service Method → Database Operation → Response Formatting → Discord Output
```

### 2. **Scheduled Reminder Flow**
```
Cron Schedule → PromptService → Discord Channel → User Reaction → HabitService → Database Update
```

### 3. **Data Analysis Flow**
```
Database Query → Service Aggregation → Statistics Calculation → Formatted Display → User Interface
```

### 4. **Cross-Domain Communication**
```
Templates (Config) → Default Habits (Business Logic) → Database Creation (Persistence) → User Commands (Interface)
```

## 🎛️ Data Standardization

### **Habit Lifecycle States**
- **Definition**: Template → Creation → Activation → Logging → Statistics
- **Multi-Scale**: Daily (15 XP) → Weekly (30 XP) → Monthly (50 XP) → Quarterly (80 XP) → Yearly (100 XP)

### **User Progress Tracking**
- **Completions**: Binary (done/not done) + Optional count extraction
- **Streaks**: Current streak, longest streak, milestone rewards
- **Gamification**: XP accumulation, level progression, loot drops

### **Communication Formats**
- **Discord Embeds**: Structured, color-coded responses
- **Database Models**: Typed, validated data structures
- **Service Interfaces**: Async methods with clear return types
- **Configuration**: YAML for templates, ENV for secrets

## 🔄 Cross-Domain Dependencies

### **Service Dependencies**
```
HabitService → UserService (user creation)
StreakService → HabitService (completion logs)
RewardService → UserService (XP/gold updates)
PromptService → HabitService (auto-logging)
```

### **Data Dependencies**
```
HabitLog → User + Habit (foreign keys)
Streak → User + Habit (tracking relationship)
PromptReaction → User + PromptSchedule (reaction tracking)
```

### **Configuration Dependencies**
```
startup_habits.py → HabitService (default creation)
prompts.yml → PromptService (scheduled messages)
.env → All Services (configuration)
```

## 📱 Multi-Scale Time Management

### **Time Scale Domains**
- **Daily**: Immediate habits, morning/evening routines
- **Weekly**: Recurring tasks, maintenance activities
- **Monthly**: Deep cleaning, administrative tasks
- **Quarterly**: Seasonal organization, goal reviews
- **Yearly**: Annual commitments, major updates

### **Scheduling Architecture**
- **Cron Expressions**: Standard Unix format for precise timing
- **Template System**: Reusable patterns for each time scale
- **Default Habits**: Pre-configured examples across all scales

## 🎯 API Design Patterns

### **Service Method Signatures**
```python
async def create_habit(name: str, description: str, base_xp: int, category: str) -> Habit
async def log_completion(user_id: int, habit_id: int, notes: str = None) -> Tuple[HabitLog, bool]
async def get_user_stats(user_id: int) -> Dict[str, Any]
```

### **Error Handling**
- **Service Level**: Try/catch with logging, return structured error data
- **Command Level**: User-friendly error messages with guidance
- **Database Level**: Transaction rollback, constraint validation

### **Response Formatting**
- **Success**: Green embeds with confirmation and next steps
- **Errors**: Red embeds with clear explanation and suggested fixes
- **Information**: Blue embeds with structured data and navigation

## 🔧 Extensibility Points

### **Adding New Time Scales**
1. Update `startup_habits.py` template system
2. Add cron pattern to template configuration
3. Create default habits for the new scale
4. Update documentation and examples

### **Adding New Habit Types**
1. Extend count extraction patterns in `HabitService`
2. Create specialized statistics methods
3. Add new command handlers in appropriate cog
4. Update help documentation

### **Adding New Integrations**
1. Create new service in `services/` directory
2. Define service interface and data models
3. Add initialization to `bot.py` service registry
4. Create command handlers for user interaction

## 📋 Quality Assurance

### **Information Consistency**
- **Naming Conventions**: snake_case for files, PascalCase for classes
- **Documentation**: Docstrings for all public methods
- **Type Hints**: Full typing for service interfaces
- **Error Messages**: Consistent format and tone

### **Cross-Domain Validation**
- **Database Constraints**: Foreign keys, unique constraints
- **Service Validation**: Input sanitization, business rule enforcement
- **Command Validation**: Parameter checking, permission verification
- **Configuration Validation**: Required fields, format checking

This architecture ensures clean separation of concerns while enabling flexible communication between all domains of the habit tracking system.