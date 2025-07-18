import re
import asyncio
from collections import defaultdict
from datetime import datetime, timedelta

import discord
from discord.ext import commands

from bot.utils.utils import Utils
from bot.utils.logger import log_moderation_action


class AutoMod(commands.Cog):
    """Auto-moderation functionality"""
    
    def __init__(self, bot):
        self.bot = bot
        self.spam_tracker = defaultdict(list)  # Track messages for spam detection
        self.profanity_words = [
            # Basic profanity list - you can expand this
            "shit", "fuck", "damn", "bitch", "ass", "bastard", "crap"
        ]
        self.invite_pattern = re.compile(
            r"(?:https?://)?(?:www\.)?(?:discord\.(?:gg|io|me|li)|discordapp\.com/invite)/[a-zA-Z0-9]+",
            re.IGNORECASE
        )
        self.link_pattern = re.compile(
            r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
            re.IGNORECASE
        )
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Process messages for auto-moderation"""
        # Ignore bots and DMs
        if message.author.bot or not message.guild:
            return
        
        # Check if auto-moderation is enabled
        guild_config = await self.bot.database.get_guild_config(message.guild.id)
        if not guild_config.get("auto_mod_enabled"):
            return
        
        # Get auto-moderation settings
        automod_settings = await self.bot.database.get_automod_settings(message.guild.id)
        
        # Check if lockdown mode is active
        is_lockdown = await self.bot.database.is_lockdown_active(message.guild.id)
        
        # Check if user has manage_messages permission (bypass auto-mod, but not lockdown)
        if message.author.guild_permissions.manage_messages and not is_lockdown:
            return
        
        # Check various auto-moderation features
        await self.check_spam(message, automod_settings, is_lockdown)
        await self.check_profanity(message, automod_settings, is_lockdown)
        await self.check_caps(message, automod_settings, is_lockdown)
        await self.check_links(message, automod_settings, is_lockdown)
        await self.check_invites(message, automod_settings, is_lockdown)
    
    async def check_spam(self, message, settings, is_lockdown=False):
        """Check for spam messages"""
        if not settings.get("spam_detection"):
            return
        
        user_id = message.author.id
        now = datetime.now()
        
        # Use lockdown threshold if in lockdown mode
        threshold = settings.get("lockdown_spam_threshold", 3) if is_lockdown else settings.get("spam_threshold", 5)
        
        # Add message to tracker
        self.spam_tracker[user_id].append(now)
        
        # Remove messages older than 10 seconds
        self.spam_tracker[user_id] = [
            timestamp for timestamp in self.spam_tracker[user_id]
            if now - timestamp < timedelta(seconds=10)
        ]
        
        # Check if spam threshold is exceeded
        if len(self.spam_tracker[user_id]) >= threshold:
            action_type = "spam_lockdown" if is_lockdown else "spam"
            reason = f"Sending {len(self.spam_tracker[user_id])} messages in 10 seconds"
            if is_lockdown:
                reason += " (Lockdown mode)"
            
            await self.take_action(message, action_type, reason, is_lockdown)
            # Clear tracker for this user
            self.spam_tracker[user_id] = []
    
    async def check_profanity(self, message, settings, is_lockdown=False):
        """Check for profanity in message"""
        if not settings.get("profanity_filter"):
            return
        
        content_lower = message.content.lower()
        found_words = []
        
        for word in self.profanity_words:
            if word in content_lower:
                found_words.append(word)
        
        if found_words:
            action_type = "profanity_lockdown" if is_lockdown else "profanity"
            reason = f"Message contains profanity: {', '.join(found_words)}"
            if is_lockdown:
                reason += " (Lockdown mode)"
            
            await self.take_action(message, action_type, reason, is_lockdown)
    
    async def check_caps(self, message, settings, is_lockdown=False):
        """Check for excessive caps"""
        if not settings.get("caps_filter"):
            return
        
        content = message.content
        if len(content) < 10:  # Ignore short messages
            return
        
        caps_count = sum(1 for c in content if c.isupper())
        caps_percentage = (caps_count / len(content)) * 100
        
        # Use lockdown threshold if in lockdown mode
        threshold = settings.get("lockdown_caps_threshold", 50) if is_lockdown else settings.get("caps_threshold", 70)
        
        if caps_percentage >= threshold:
            action_type = "excessive_caps_lockdown" if is_lockdown else "excessive_caps"
            reason = f"Message is {caps_percentage:.1f}% caps (limit: {threshold}%)"
            if is_lockdown:
                reason += " (Lockdown mode)"
            
            await self.take_action(message, action_type, reason, is_lockdown)
    
    async def check_links(self, message, settings, is_lockdown=False):
        """Check for links in message"""
        if not settings.get("link_filter"):
            return
        
        if self.link_pattern.search(message.content):
            action_type = "unauthorized_link_lockdown" if is_lockdown else "unauthorized_link"
            reason = "Message contains unauthorized links"
            if is_lockdown:
                reason += " (Lockdown mode)"
            
            await self.take_action(message, action_type, reason, is_lockdown)
    
    async def check_invites(self, message, settings, is_lockdown=False):
        """Check for Discord invites"""
        if not settings.get("invite_filter"):
            return
        
        if self.invite_pattern.search(message.content):
            action_type = "discord_invite_lockdown" if is_lockdown else "discord_invite"
            reason = "Message contains Discord invite links"
            if is_lockdown:
                reason += " (Lockdown mode)"
            
            await self.take_action(message, action_type, reason, is_lockdown)
    
    async def take_action(self, message, violation_type, reason, is_lockdown=False):
        """Take action against a message that violates auto-moderation rules"""
        try:
            # Delete the message
            await message.delete()
            
            # In lockdown mode, apply timeout/mute
            if is_lockdown:
                automod_settings = await self.bot.database.get_automod_settings(message.guild.id)
                timeout_duration = automod_settings.get("lockdown_timeout_duration", 300)  # 5 minutes default
                
                try:
                    # Apply timeout
                    timeout_until = datetime.now() + timedelta(seconds=timeout_duration)
                    await message.author.timeout(timeout_until, reason=f"Auto-moderation lockdown: {reason}")
                    
                    # Create moderation case
                    await self.bot.database.create_moderation_case(
                        message.guild.id,
                        "auto_timeout",
                        message.author.id,
                        self.bot.user.id,
                        f"Auto-moderation lockdown: {reason}",
                        timeout_duration
                    )
                    
                except discord.HTTPException:
                    pass  # Failed to timeout (permissions, etc.)
            
            # Send warning to user
            embed_title = f"Auto-Moderation - {violation_type.replace('_', ' ').title()}"
            if is_lockdown:
                embed_title += " (Lockdown Mode)"
            
            embed = Utils.create_warning_embed(
                f"Your message was deleted for: {reason}",
                embed_title
            )
            
            if is_lockdown:
                embed.add_field(
                    name="⚠️ Lockdown Mode Active",
                    value="Stricter rules are currently in effect. You have been temporarily timed out.",
                    inline=False
                )
            
            try:
                await message.author.send(embed=embed)
            except discord.HTTPException:
                pass  # User has DMs disabled
            
            # Log the action
            log_channel_id = (await self.bot.database.get_guild_config(message.guild.id)).get("log_channel_id")
            if log_channel_id:
                log_channel = message.guild.get_channel(log_channel_id)
                if log_channel:
                    log_embed_title = "🤖 Auto-Moderation Action"
                    if is_lockdown:
                        log_embed_title = "🔒 Lockdown Auto-Moderation Action"
                    
                    log_embed = Utils.create_embed(
                        title=log_embed_title,
                        description=f"Message deleted in {message.channel.mention}",
                        color=discord.Color.red() if is_lockdown else discord.Color.orange(),
                        fields=[
                            {"name": "User", "value": f"{message.author.mention} ({message.author.id})", "inline": True},
                            {"name": "Channel", "value": message.channel.mention, "inline": True},
                            {"name": "Violation", "value": violation_type.replace("_", " ").title(), "inline": True},
                            {"name": "Reason", "value": reason, "inline": False},
                            {"name": "Original Message", "value": Utils.truncate_text(message.content, 1000), "inline": False},
                        ]
                    )
                    
                    if is_lockdown:
                        log_embed.add_field(
                            name="Action Taken",
                            value="User has been timed out due to lockdown mode",
                            inline=False
                        )
                    
                    await log_channel.send(embed=log_embed)
            
            # Log to console
            log_moderation_action(
                f"auto_mod_{violation_type}",
                self.bot.user,
                message.author,
                reason,
                message.guild
            )
            
            # Check if user should be warned/timed out for repeated violations
            await self.check_repeated_violations(message.author, message.guild)
            
        except discord.HTTPException as e:
            # If we can't delete the message, log the error
            self.bot.logger.error(f"Failed to delete message in auto-moderation: {e}")
    
    async def check_repeated_violations(self, user, guild):
        """Check if user has repeated violations and take escalating action"""
        # Get recent cases for this user
        recent_cases = await self.bot.database.get_user_cases(guild.id, user.id)
        
        # Count auto-moderation violations in the last hour
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_automod_violations = [
            case for case in recent_cases
            if case["case_type"].startswith("auto_mod_") and
            datetime.fromisoformat(case["created_at"]) > one_hour_ago
        ]
        
        violation_count = len(recent_automod_violations)
        
        if violation_count >= 3:  # 3 violations in an hour
            # Timeout user for 10 minutes
            try:
                timeout_duration = 600  # 10 minutes
                timeout_until = datetime.now() + timedelta(seconds=timeout_duration)
                
                await user.timeout(
                    timeout_until,
                    reason=f"Auto-moderation: {violation_count} violations in 1 hour"
                )
                
                # Create moderation case
                case_id = await self.bot.database.create_moderation_case(
                    guild.id,
                    "auto_timeout",
                    user.id,
                    self.bot.user.id,
                    f"Automatic timeout for {violation_count} auto-moderation violations",
                    timeout_duration
                )
                
                # Add temporary punishment
                await self.bot.database.add_temp_punishment(
                    guild.id,
                    user.id,
                    "timeout",
                    timeout_until,
                    case_id
                )
                
                # Send notification to log channel
                log_channel_id = (await self.bot.database.get_guild_config(guild.id)).get("log_channel_id")
                if log_channel_id:
                    log_channel = guild.get_channel(log_channel_id)
                    if log_channel:
                        embed = Utils.create_embed(
                            title="🔒 Auto-Moderation Escalation",
                            description=f"{user.mention} has been automatically timed out",
                            color=discord.Color.red(),
                            fields=[
                                {"name": "User", "value": f"{user.mention} ({user.id})", "inline": True},
                                {"name": "Reason", "value": f"{violation_count} violations in 1 hour", "inline": True},
                                {"name": "Duration", "value": "10 minutes", "inline": True},
                                {"name": "Case ID", "value": f"#{case_id}", "inline": True},
                            ]
                        )
                        
                        await log_channel.send(embed=embed)
                
                # Log the action
                log_moderation_action(
                    "auto_timeout",
                    self.bot.user,
                    user,
                    f"{violation_count} auto-moderation violations",
                    guild
                )
                
            except discord.HTTPException as e:
                self.bot.logger.error(f"Failed to timeout user for repeated violations: {e}")
    
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        """Handle message edits for auto-moderation"""
        # Treat edited messages as new messages
        await self.on_message(after)


async def setup(bot):
    await bot.add_cog(AutoMod(bot))
