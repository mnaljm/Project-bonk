#!/usr/bin/env python3
"""
Simple test script to verify the bot setup
"""

import os
import sys
from pathlib import Path

def test_imports():
    """Test if all required modules can be imported"""
    try:
        import discord
        print("✅ discord.py imported successfully")
        
        import aiosqlite
        print("✅ aiosqlite imported successfully")
        
        import colorlog
        print("✅ colorlog imported successfully")
        
        from dotenv import load_dotenv
        print("✅ python-dotenv imported successfully")
        
        print("\n✅ All imports successful!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_file_structure():
    """Test if the file structure is correct"""
    required_files = [
        "main.py",
        "requirements.txt",
        ".env.example",
        "bot/__init__.py",
        "bot/database.py",
        "bot/utils/__init__.py",
        "bot/utils/logger.py",
        "bot/utils/utils.py",
        "bot/cogs/__init__.py",
        "bot/cogs/moderation.py",
        "bot/cogs/utility.py",
        "bot/cogs/config.py",
        "bot/cogs/automod.py",
        "bot/cogs/logging.py",
    ]
    
    print("Checking file structure...")
    all_exist = True
    
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - Missing!")
            all_exist = False
    
    return all_exist

def test_env_file():
    """Test if .env file exists and is configured"""
    env_path = Path(".env")
    
    if not env_path.exists():
        print("⚠️  .env file not found. Please copy .env.example to .env and configure it.")
        return False
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            print("⚠️  DISCORD_TOKEN not set in .env file")
            return False
        
        if token == "your_bot_token_here":
            print("⚠️  DISCORD_TOKEN still has default value. Please set your actual bot token.")
            return False
        
        print("✅ .env file configured")
        return True
        
    except Exception as e:
        print(f"❌ Error reading .env file: {e}")
        return False

def main():
    """Main test function"""
    print("🤖 Project Bonk - Setup Test")
    print("=" * 40)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Module Imports", test_imports),
        ("Environment Configuration", test_env_file),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 20)
        
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} failed")
    
    print("\n" + "=" * 40)
    print(f"Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! The bot is ready to run.")
        print("Use 'python main.py' to start the bot.")
    else:
        print("⚠️  Some tests failed. Please fix the issues before running the bot.")
        
        if passed < total - 1:  # More than just env file issues
            print("Install missing dependencies with: pip install -r requirements.txt")

if __name__ == "__main__":
    main()
