#!/usr/bin/env python3
"""
Test script to check if the bot can start and identify issues.
"""

import os
import sys
import asyncio
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_environment():
    """Check if required environment variables are set."""
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = ["DISCORD_TOKEN", "DATABASE_URL"]
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value or value == f"your_{var.lower()}_here":
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing or placeholder environment variables: {missing_vars}")
        logger.info("Please update the .env file with actual values:")
        logger.info("DISCORD_TOKEN=your_actual_discord_bot_token")
        logger.info("DATABASE_URL=sqlite+aiosqlite:///habits.db")
        return False
    
    logger.info("✅ Environment variables are set")
    return True

def check_dependencies():
    """Check if required Python packages are installed."""
    try:
        import discord
        import sqlalchemy
        import apscheduler
        import aiosqlite
        logger.info("✅ All required packages are installed")
        return True
    except ImportError as e:
        logger.error(f"❌ Missing package: {e}")
        return False

def check_database():
    """Check if database can be initialized."""
    try:
        from database import initialize_database, close_database
        logger.info("✅ Database module can be imported")
        return True
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        return False

def check_services():
    """Check if service modules can be imported."""
    try:
        from services.habit_service import HabitService
        from services.prompt_service import PromptService
        from services.user_service import UserService
        from services.reward_service import RewardService
        from services.streak_service import StreakService
        logger.info("✅ All service modules can be imported")
        return True
    except Exception as e:
        logger.error(f"❌ Service import error: {e}")
        return False

async def test_bot_initialization():
    """Test if the bot can be initialized."""
    try:
        from bot import HabitBot
        from database import initialize_database, close_database
        
        # Initialize database
        await initialize_database()
        
        # Create bot instance
        bot = HabitBot()
        logger.info("✅ Bot instance created successfully")
        
        # Clean up
        await close_database()
        return True
    except Exception as e:
        logger.error(f"❌ Bot initialization error: {e}")
        return False

def main():
    """Run all tests."""
    logger.info("🔍 Testing Discord Habit Bot...")
    
    tests = [
        ("Environment Variables", check_environment),
        ("Dependencies", check_dependencies),
        ("Database", check_database),
        ("Services", check_services),
    ]
    
    all_passed = True
    for test_name, test_func in tests:
        logger.info(f"\n--- Testing {test_name} ---")
        if not test_func():
            all_passed = False
    
    logger.info(f"\n--- Testing Bot Initialization ---")
    if all_passed:
        try:
            asyncio.run(test_bot_initialization())
            logger.info("✅ Bot initialization test passed")
        except Exception as e:
            logger.error(f"❌ Bot initialization test failed: {e}")
            all_passed = False
    else:
        logger.warning("⚠️ Skipping bot initialization test due to previous failures")
    
    if all_passed:
        logger.info("\n🎉 All tests passed! The bot should be able to start.")
        logger.info("\nTo start the bot:")
        logger.info("1. Create a .env file with your Discord token and database URL")
        logger.info("2. Run: python bot.py")
    else:
        logger.error("\n❌ Some tests failed. Please fix the issues above before starting the bot.")

if __name__ == "__main__":
    main()