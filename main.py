import asyncio
import logging
import os
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

from bot.database import Database
from bot.utils.logger import setup_logger


class BonkBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        intents.guild_messages = True
        intents.moderation = True
        
        super().__init__(
            command_prefix=commands.when_mentioned_or(os.getenv("COMMAND_PREFIX", "!")),
            intents=intents,
            help_command=None,
            case_insensitive=True,
        )
        
        self.database = Database()
        self.logger = logging.getLogger(__name__)
        
        # Bot configuration
        self.config = {
            "max_warnings": int(os.getenv("MAX_WARNINGS", 3)),
            "default_timeout_duration": int(os.getenv("DEFAULT_TIMEOUT_DURATION", 600)),
            "guild_id": int(os.getenv("GUILD_ID")) if os.getenv("GUILD_ID") else None,
        }

    async def setup_hook(self):
        """Called when the bot is starting up"""
        await self.database.initialize()
        await self.load_extensions()
          # Sync commands if guild_id is specified (for development)
        if self.config["guild_id"]:
            guild = discord.Object(id=self.config["guild_id"])
            # Clear any existing guild commands first to prevent duplicates
            self.tree.clear_commands(guild=guild)
            # Copy global commands to guild for faster testing
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            self.logger.info(f"Commands synced to guild {self.config['guild_id']}")
        else:
            await self.tree.sync()
            self.logger.info("Commands synced globally")

    async def load_extensions(self):
        """Load all bot extensions"""
        extensions = [
            "bot.cogs.moderation",
            "bot.cogs.utility",
            "bot.cogs.automod",
            "bot.cogs.logging",
            "bot.cogs.config",
            "bot.cogs.lockdown",
            "bot.cogs.suggestions",
            "bot.cogs.nsfw_management",
        ]
        
        for extension in extensions:
            try:
                await self.load_extension(extension)
                self.logger.info(f"Loaded extension: {extension}")
            except Exception as e:
                self.logger.error(f"Failed to load extension {extension}: {e}")

    async def on_ready(self):
        """Called when the bot is ready"""
        self.logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        self.logger.info(f"Bot is ready! Serving {len(self.guilds)} guilds")
        
        # Initialize guild configs for all existing guilds
        await self.initialize_existing_guilds()
        
        # Set bot status
        await self.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name="for rule violations")
        )
        
        # Start background tasks
        self.loop.create_task(self.cleanup_expired_punishments())
        self.loop.create_task(self.cleanup_old_activity_data())

    async def initialize_existing_guilds(self):
        """Initialize guild configs for all guilds the bot is already in"""
        self.logger.info("Initializing guild configurations for existing guilds...")
        
        for guild in self.guilds:
            try:
                await self.database.create_guild_config(guild.id)
                self.logger.debug(f"Initialized guild config for {guild.name} (ID: {guild.id})")
            except Exception as e:
                self.logger.error(f"Failed to initialize guild config for {guild.name} (ID: {guild.id}): {e}")
        
        self.logger.info(f"Guild configuration initialization complete for {len(self.guilds)} guilds")

    async def cleanup_expired_punishments(self):
        """Background task to clean up expired punishments"""
        await self.wait_until_ready()
        
        while not self.is_closed():
            try:
                expired_punishments = await self.database.get_expired_punishments()
                
                for punishment in expired_punishments:
                    guild = self.get_guild(punishment["guild_id"])
                    if not guild:
                        continue
                    
                    try:
                        if punishment["punishment_type"] == "timeout":
                            member = guild.get_member(punishment["user_id"])
                            if member and member.is_timed_out():
                                await member.timeout(None, reason="Automatic timeout removal")
                                self.logger.info(f"Removed timeout for {member} in {guild.name}")
                        
                        elif punishment["punishment_type"] == "ban":
                            await guild.unban(
                                discord.Object(id=punishment["user_id"]), 
                                reason="Automatic temporary ban removal"
                            )
                            self.logger.info(f"Removed temporary ban for user {punishment['user_id']} in {guild.name}")
                        
                        await self.database.remove_temp_punishment(punishment["id"])
                        
                    except Exception as e:
                        self.logger.error(f"Failed to remove expired punishment {punishment['id']}: {e}")
                
            except Exception as e:
                self.logger.error(f"Error in cleanup_expired_punishments: {e}")
            
            await asyncio.sleep(60)  # Check every minute    async def cleanup_old_activity_data(self):
        """Background task to clean up old activity data"""
        await self.wait_until_ready()
        
        while not self.is_closed():
            try:
                # Clean up activity data older than 90 days
                deleted_count = await self.database.cleanup_old_activity(days=90)
                if deleted_count > 0:
                    self.logger.info(f"Cleaned up {deleted_count} old activity records")
                
            except Exception as e:
                self.logger.error(f"Error in cleanup_old_activity_data: {e}")
            
            # Run cleanup once per day (24 hours)
            await asyncio.sleep(24 * 60 * 60)

    async def on_guild_join(self, guild):
        """Called when the bot joins a new guild"""
        self.logger.info(f"Joined guild: {guild.name} (ID: {guild.id}) with {guild.member_count} members")
        
        # Initialize guild in database
        await self.database.create_guild_config(guild.id)
        
        # Send welcome message
        if guild.system_channel:
            embed = discord.Embed(
                title="🎉 Thanks for adding Project Bonk!",
                description=(
                    "Hello! I'm **Project Bonk**, your new moderation bot.\n\n"
                    "**Getting Started:**\n"
                    "• Use `/help` to see all available commands\n"
                    "• Set up a log channel with `/config logchannel`\n"
                    "• Configure auto-moderation with `/automod`\n\n"
                    "**Key Features:**\n"
                    "• Modern slash commands\n"
                    "• Advanced moderation tools\n"
                    "• Automatic punishment tracking\n"
                    "• Comprehensive logging\n"
                    "• Auto-moderation capabilities\n\n"
                    "For support or questions, check out our documentation."
                ),
                color=discord.Color.green(),
            )
            embed.set_footer(text="Project Bonk | Moderation Bot")
            
            try:
                await guild.system_channel.send(embed=embed)
            except Exception as e:
                self.logger.warning(f"Could not send welcome message to {guild.name}: {e}")

    async def on_guild_remove(self, guild):
        """Called when the bot leaves a guild"""
        self.logger.info(f"Left guild: {guild.name} (ID: {guild.id})")

    async def close(self):
        """Called when the bot is shutting down"""
        await self.database.close()
        await super().close()


async def main():
    """Main function to run the bot"""
    # Load environment variables
    load_dotenv()
    
    # Setup logging
    setup_logger()
    
    # Create data directory
    Path("data").mkdir(exist_ok=True)
    
    # Check for required environment variables
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        logging.error("DISCORD_TOKEN is not set in environment variables")
        return
    
    # Create and run the bot
    bot = BonkBot()
    
    try:
        await bot.start(token)
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Bot encountered an error: {e}")
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
