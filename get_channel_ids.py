#!/usr/bin/env python3
"""
Simple script to get Discord channel IDs for GitHub Actions setup
Run this with your bot token to get the channel IDs you need
"""

import os
import asyncio
import discord
from dotenv import load_dotenv

load_dotenv()

async def get_channel_ids():
    """Get all channel IDs from the bot's guilds"""
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ DISCORD_TOKEN not found in .env file")
        return
    
    intents = discord.Intents.default()
    intents.guilds = True
    client = discord.Client(intents=intents)
    
    @client.event
    async def on_ready():
        print(f"🤖 Bot logged in as {client.user}")
        print("\n📋 Available channels:")
        print("=" * 50)
        
        for guild in client.guilds:
            print(f"\n🏰 Guild: {guild.name}")
            for channel in guild.channels:
                if isinstance(channel, discord.TextChannel):
                    print(f"  #{channel.name}: {channel.id}")
        
        print("\n" + "=" * 50)
        print("💡 Copy the channel IDs you want to use for:")
        print("   - HABIT_CHANNEL_ID: Channel for habit tracking")
        print("   - MEALS_CHANNEL_ID: Channel for recipe suggestions")
        print("\n🔧 Add these to your GitHub repo secrets!")
        
        await client.close()
    
    try:
        await client.start(token)
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(get_channel_ids())
