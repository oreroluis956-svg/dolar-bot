#!/usr/bin/env python3
"""
Main runner for the Venezuelan Dollar Bot
This script starts both the Telegram bot and web interface
"""

import os
import sys
import threading
import time
import logging
from main import start_bot, dollar_bot
from web_interface import start_web_interface, set_bot_instance

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point"""
    logger.info("Starting Venezuelan Dollar Bot Application")
    
    # Check environment variables
    token = os.getenv("TOKEN")
    chat_id_str = os.getenv("CHAT_ID")
    
    if not token or token == "your_bot_token_here":
        logger.error("TOKEN environment variable not set or invalid")
        print("\n❌ Error: TOKEN environment variable not set")
        print("Please set your Telegram bot token:")
        print("export TOKEN='your_bot_token_here'")
        sys.exit(1)
    
    if not chat_id_str:
        logger.error("CHAT_ID environment variable not set")
        print("\n❌ Error: CHAT_ID environment variable not set")
        print("Please set your Telegram chat ID:")
        print("export CHAT_ID='your_chat_id_here'")
        sys.exit(1)
    
    # Validate CHAT_ID format
    try:
        chat_id = int(chat_id_str)
    except ValueError:
        logger.error(f"Invalid CHAT_ID format: '{chat_id_str}'. CHAT_ID should be numeric.")
        print(f"\n❌ Error: Invalid CHAT_ID format")
        print(f"Current CHAT_ID value: '{chat_id_str}'")
        print("CHAT_ID should be a numeric value (like: 123456789)")
        print("TOKEN should be your bot token (like: 123456789:ABCdefGhIjKlMnOpQr)")
        print("\nPlease check that the environment variables are set correctly:")
        print("- TOKEN = your bot token from @BotFather")
        print("- CHAT_ID = your numeric chat ID from @userinfobot")
        sys.exit(1)
    
    logger.info(f"Configuration loaded - Chat ID: {chat_id}")
    
    # Set bot instance for web interface
    set_bot_instance(dollar_bot)
    
    # Start web interface in a separate thread
    web_thread = threading.Thread(target=start_web_interface, daemon=True)
    web_thread.start()
    logger.info("Web interface thread started")
    
    # Give web interface time to start
    time.sleep(2)
    
    # Print startup information
    print("\n🤖 Venezuelan Dollar Bot Started Successfully!")
    print("=" * 50)
    print(f"📱 Telegram Bot: Active")
    print(f"🌐 Web Dashboard: http://localhost:5000")
    print(f"💬 Chat ID: {chat_id}")
    print(f"📅 Daily Updates: Weekdays at 9:00 AM")
    print("=" * 50)
    print("\nPress Ctrl+C to stop the bot")
    print("\nCommands available in Telegram:")
    print("  /start - Start the bot")
    print("  /tasas - Get current exchange rates")
    print("  /help - Show help message")
    print("\n")
    
    try:
        # Start the Telegram bot (this will block)
        start_bot()
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
        print("\n\n👋 Bot shutting down...")
        dollar_bot.stop_scheduler()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
