"""
Database models for the Discord Habit Bot.

This module defines the SQLAlchemy models for all data persistence.
Design decisions:
- Using SQLAlchemy 2.0+ async syntax for better performance
- Storing Discord IDs as strings to handle large integers safely
- Using UTC timestamps consistently throughout
- Soft deletes where appropriate to maintain data integrity
"""

from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import String, Integer, DateTime, Date, Boolean, Text, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class User(Base):
    """Discord user with habit tracking data."""
    __tablename__ = "users"
    
    # Primary key and Discord integration
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    discord_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Gamification stats
    total_xp: Mapped[int] = mapped_column(Integer, default=0)
    gold: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=1)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    last_active: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relationships
    habit_logs: Mapped[List["HabitLog"]] = relationship("HabitLog", back_populates="user")
    rewards: Mapped[List["Reward"]] = relationship("Reward", back_populates="user")
    reactions: Mapped[List["PromptReaction"]] = relationship("PromptReaction", back_populates="user")
    quiz_responses: Mapped[List["QuizResponse"]] = relationship("QuizResponse", back_populates="user")
    inventory_items: Mapped[List["InventoryItem"]] = relationship("InventoryItem", back_populates="user")


class Habit(Base):
    """Habit definitions that users can log."""
    __tablename__ = "habits"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # XP and reward configuration
    base_xp: Mapped[int] = mapped_column(Integer, default=10)
    category: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relationships
    habit_logs: Mapped[List["HabitLog"]] = relationship("HabitLog", back_populates="habit")


class HabitLog(Base):
    """Individual habit completions by users."""
    __tablename__ = "habit_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    habit_id: Mapped[int] = mapped_column(ForeignKey("habits.id"), nullable=False)
    
    # Completion details
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    completion_date: Mapped[date] = mapped_column(Date, default=func.current_date())  # For streak tracking
    
    # Rewards given
    xp_awarded: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Source tracking (command vs reaction)
    source: Mapped[str] = mapped_column(String(20), default="command")  # "command" or "reaction"
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="habit_logs")
    habit: Mapped["Habit"] = relationship("Habit", back_populates="habit_logs")
    
    # Ensure one log per user per habit per day
    __table_args__ = (UniqueConstraint('user_id', 'habit_id', 'completion_date'),)


class Streak(Base):
    """User streak tracking for habits."""
    __tablename__ = "streaks"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    habit_id: Mapped[int] = mapped_column(ForeignKey("habits.id"), nullable=False)
    
    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0)
    last_completion_date: Mapped[Optional[date]] = mapped_column(Date)
    
    # Milestone tracking
    last_milestone_reward: Mapped[int] = mapped_column(Integer, default=0)
    
    # Metadata
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Ensure one streak record per user per habit
    __table_args__ = (UniqueConstraint('user_id', 'habit_id'),)


class Reward(Base):
    """Rewards given to users (loot, bonus XP, etc.)."""
    __tablename__ = "rewards"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    
    # Reward details
    reward_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "xp", "gold", "item", "title"
    reward_value: Mapped[str] = mapped_column(String(200), nullable=False)  # JSON or simple value
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # Source context
    source_type: Mapped[str] = mapped_column(String(50))  # "habit_log", "streak_milestone", "random_roll"
    source_id: Mapped[Optional[int]] = mapped_column(Integer)  # ID of the triggering record
    
    # RNG details
    roll_value: Mapped[Optional[int]] = mapped_column(Integer)  # d100 roll result
    
    # Metadata
    awarded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="rewards")


class InventoryItem(Base):
    """User inventory items."""
    __tablename__ = "inventory_items"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    
    item_name: Mapped[str] = mapped_column(String(100), nullable=False)
    item_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "consumable", "equipment", "collectible"
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Metadata
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="inventory_items")
    
    # Ensure unique items per user
    __table_args__ = (UniqueConstraint('user_id', 'item_name'),)


class PromptSchedule(Base):
    """Scheduled prompts for habit reminders."""
    __tablename__ = "prompt_schedules"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Scheduling
    cron_expression: Mapped[str] = mapped_column(String(100), nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    
    # Target configuration
    channel_id: Mapped[Optional[str]] = mapped_column(String(20))  # If None, use default channel
    target_users: Mapped[Optional[str]] = mapped_column(Text)  # JSON list of user IDs, or None for all
    
    # Metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    reactions: Mapped[List["PromptReaction"]] = relationship("PromptReaction", back_populates="prompt_schedule")


class PromptReaction(Base):
    """User reactions to scheduled prompts."""
    __tablename__ = "prompt_reactions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    prompt_schedule_id: Mapped[int] = mapped_column(ForeignKey("prompt_schedules.id"), nullable=False)
    
    # Message context
    message_id: Mapped[str] = mapped_column(String(20), nullable=False)
    channel_id: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # Reaction details
    reaction_emoji: Mapped[str] = mapped_column(String(10), default="✅")
    reacted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    
    # Processing
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="reactions")
    prompt_schedule: Mapped["PromptSchedule"] = relationship("PromptSchedule", back_populates="reactions")


class Quiz(Base):
    """Quiz questions generated from habit completions."""
    __tablename__ = "quizzes"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    
    # Question content
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(50), default="reflection")  # "reflection", "knowledge", "goal"
    
    # Source context
    source_habit_id: Mapped[Optional[int]] = mapped_column(ForeignKey("habits.id"))
    source_log_id: Mapped[Optional[int]] = mapped_column(ForeignKey("habit_logs.id"))
    
    # Scheduling
    scheduled_for: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    priority: Mapped[int] = mapped_column(Integer, default=1)  # Higher = more important
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="pending")  # "pending", "sent", "answered", "skipped"
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    responses: Mapped[List["QuizResponse"]] = relationship("QuizResponse", back_populates="quiz")


class QuizResponse(Base):
    """User responses to quiz questions."""
    __tablename__ = "quiz_responses"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id"), nullable=False)
    
    # Response content
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_rating: Mapped[Optional[int]] = mapped_column(Integer)  # 1-5 scale
    
    # Timing
    responded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    time_to_respond: Mapped[Optional[int]] = mapped_column(Integer)  # Seconds
    
    # Anki integration
    anki_note_id: Mapped[Optional[str]] = mapped_column(String(50))  # Anki note ID if synced
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="quiz_responses")
    quiz: Mapped["Quiz"] = relationship("Quiz", back_populates="responses")