import asyncio
import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta

from bot.utils.utils import Utils, is_superuser
from bot.utils.logger import log_moderation_action


class Lockdown(commands.Cog):
    """Lockdown mode functionality"""
    
    def __init__(self, bot):
        self.bot = bot
        self.last_activity = {}  # Track last activity: {guild_id: {user_id: timestamp}}
        self.check_moderator_availability.start()
    
    def cog_unload(self):
        self.check_moderator_availability.cancel()
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Track message activity for moderator detection"""
        if message.author.bot or not message.guild:
            return
            
        # Check if user has moderation permissions
        if (message.author.guild_permissions.kick_members or 
            message.author.guild_permissions.ban_members or 
            message.author.guild_permissions.manage_messages or
            message.author.guild_permissions.administrator):
            
            # Track activity
            guild_id = message.guild.id
            user_id = message.author.id
            
            if guild_id not in self.last_activity:
                self.last_activity[guild_id] = {}
            
            self.last_activity[guild_id][user_id] = datetime.now()
            self.bot.logger.debug(f"Tracked activity for moderator {message.author.display_name} in {message.guild.name}")
    
    @commands.Cog.listener()
    async def on_interaction(self, interaction):
        """Track command/interaction activity for moderator detection"""
        if not interaction.guild or not interaction.user:
            return
            
        # Check if user has moderation permissions
        if (interaction.user.guild_permissions.kick_members or 
            interaction.user.guild_permissions.ban_members or 
            interaction.user.guild_permissions.manage_messages or
            interaction.user.guild_permissions.administrator):
            
            # Track activity
            guild_id = interaction.guild.id
            user_id = interaction.user.id
            
            if guild_id not in self.last_activity:
                self.last_activity[guild_id] = {}
            
            self.last_activity[guild_id][user_id] = datetime.now()
            self.bot.logger.debug(f"Tracked interaction activity for moderator {interaction.user.display_name} in {interaction.guild.name}")
    
    @tasks.loop(minutes=5)
    async def check_moderator_availability(self):
        """Check if moderators are available and auto-enable lockdown if needed"""
        for guild in self.bot.guilds:
            try:
                automod_settings = await self.bot.database.get_automod_settings(guild.id)
                
                # Skip if auto-lockdown is disabled
                if not automod_settings.get("lockdown_auto_enable", 1):
                    continue
                
                # Skip if there's a manual override in place
                if await self.bot.database.is_manual_lockdown_override(guild.id):
                    self.bot.logger.info(f"Skipping auto-lockdown for {guild.name} - manual override active")
                    continue
                
                # Check if already in lockdown
                is_lockdown = await self.bot.database.is_lockdown_active(guild.id)
                
                # Check for available moderators
                moderators_online = self.get_online_moderators(guild)
                
                # Debug logging
                self.bot.logger.info(f"Auto-check for {guild.name}: lockdown={is_lockdown}, moderators_online={len(moderators_online)}")
                
                if not moderators_online and not is_lockdown:
                    # No moderators online, enable lockdown (auto)
                    self.bot.logger.info(f"Auto-enabling lockdown for {guild.name}")
                    await self.bot.database.enable_lockdown(guild.id, manual=False)
                    await self.log_lockdown_change(guild, True, "Auto-enabled: No moderators online")
                    
                elif moderators_online and is_lockdown:
                    # Moderators are back online, auto-disable lockdown
                    self.bot.logger.info(f"Auto-disabling lockdown for {guild.name}")
                    await self.bot.database.disable_lockdown(guild.id, manual=False)
                    await self.log_lockdown_change(guild, False, "Auto-disabled: Moderators are online")
                    
            except Exception as e:
                self.bot.logger.error(f"Error checking moderator availability for guild {guild.id}: {e}")
    
    @check_moderator_availability.before_loop
    async def before_check_moderator_availability(self):
        await self.bot.wait_until_ready()
        # Add additional delay to ensure guild initialization is complete
        await asyncio.sleep(10)  # Wait 10 seconds after bot is ready
    
    def get_online_moderators(self, guild: discord.Guild) -> list:
        """Get list of online moderators/admins using multiple detection methods"""
        online_moderators = []
        
        self.bot.logger.info(f"Checking {len(guild.members)} members in {guild.name}")
        
        for member in guild.members:
            if member.bot:
                continue
            
            # Check if member has moderation permissions
            has_perms = (member.guild_permissions.kick_members or 
                        member.guild_permissions.ban_members or 
                        member.guild_permissions.manage_messages or
                        member.guild_permissions.administrator)
            
            if has_perms:
                self.bot.logger.info(f"Found moderator: {member.display_name} ({member.id}) - Status: {member.status}, Perms: kick={member.guild_permissions.kick_members}, ban={member.guild_permissions.ban_members}, manage={member.guild_permissions.manage_messages}, admin={member.guild_permissions.administrator}")
                
                # Multiple detection methods
                is_online = self.is_moderator_available(member)
                
                if is_online:
                    online_moderators.append(member)
                    self.bot.logger.info(f"✅ Available moderator: {member.display_name} ({member.id})")
                else:
                    self.bot.logger.info(f"❌ Unavailable moderator: {member.display_name} ({member.id})")
        
        self.bot.logger.info(f"Total available moderators found in {guild.name}: {len(online_moderators)}")
        return online_moderators
    
    def is_moderator_available(self, member: discord.Member) -> bool:
        """Check if a moderator is available using multiple methods"""
        # Method 1: Discord status (current method)
        status_online = member.status != discord.Status.offline
        
        # Method 2: Recent activity (check if they were active recently)
        recent_activity = self.check_recent_activity(member)
        
        # Method 3: Mobile/desktop presence
        mobile_online = member.mobile_status != discord.Status.offline
        desktop_online = member.desktop_status != discord.Status.offline
        web_online = member.web_status != discord.Status.offline
        
        # Method 4: Check if they have any active presence
        has_presence = any([mobile_online, desktop_online, web_online])
        
        # Consider available if any method indicates they're online
        is_available = status_online or recent_activity or has_presence
        
        self.bot.logger.info(f"Availability check for {member.display_name}: status={member.status}, mobile={member.mobile_status}, desktop={member.desktop_status}, web={member.web_status}, recent_activity={recent_activity}, final={is_available}")
        
        return is_available
    
    def check_recent_activity(self, member: discord.Member) -> bool:
        """Check if member was recently active"""
        guild_id = member.guild.id
        user_id = member.id
        
        # Check if we have activity data for this user
        if guild_id not in self.last_activity:
            return False
            
        if user_id not in self.last_activity[guild_id]:
            return False
            
        # Check if activity was within the last 30 minutes
        last_activity = self.last_activity[guild_id][user_id]
        time_diff = datetime.now() - last_activity
        
        # Consider active if they were active in the last 30 minutes
        is_recent = time_diff.total_seconds() < 1800  # 30 minutes
        
        if is_recent:
            self.bot.logger.info(f"Recent activity for {member.display_name}: {time_diff.total_seconds():.0f} seconds ago")
        
        return is_recent
    
    async def log_lockdown_change(self, guild: discord.Guild, enabled: bool, reason: str):
        """Log lockdown mode changes"""
        try:
            guild_config = await self.bot.database.get_guild_config(guild.id)
            log_channel_id = guild_config.get("log_channel_id")
            
            if not log_channel_id:
                return
            
            log_channel = guild.get_channel(log_channel_id)
            if not log_channel:
                return
            
            color = discord.Color.red() if enabled else discord.Color.green()
            title = "🔒 Lockdown Mode Enabled" if enabled else "🔓 Lockdown Mode Disabled"
            
            embed = Utils.create_embed(
                title=title,
                description=f"Lockdown mode has been {'enabled' if enabled else 'disabled'}",
                color=color,
                fields=[
                    {"name": "Reason", "value": reason, "inline": False},
                    {"name": "Status", "value": "🔒 ACTIVE" if enabled else "🔓 INACTIVE", "inline": True},
                    {"name": "Auto-Moderation", "value": "Stricter rules active" if enabled else "Normal rules active", "inline": True},
                ]
            )
            
            await log_channel.send(embed=embed)
            
        except Exception as e:
            self.bot.logger.error(f"Error logging lockdown change: {e}")
    
    @app_commands.command(name="lockdown", description="Manage lockdown mode")
    @app_commands.describe(
        action="Enable or disable lockdown mode",
        reason="Reason for the lockdown action"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Enable", value="enable"),
        app_commands.Choice(name="Disable", value="disable"),
        app_commands.Choice(name="Status", value="status"),
        app_commands.Choice(name="Clear Override", value="clear"),
    ])
    async def lockdown(
        self,
        interaction: discord.Interaction,
        reason: str = None
    ):
        """Manage lockdown mode"""
        if not is_superuser(interaction.user):
            if not await Utils.check_permissions(interaction, ["manage_channels"]):
                return
        
        # Check permissions
        if is_superuser(interaction.user):
            pass  # allow superuser bypass
        #     # existing permission checks
        elif not await Utils.check_permissions(interaction, ["administrator"]):
            return
        
        try:
            if action == "status":
                # Show lockdown status
                is_active = await self.bot.database.is_lockdown_active(interaction.guild.id)
                automod_settings = await self.bot.database.get_automod_settings(interaction.guild.id)
                is_override = await self.bot.database.is_manual_lockdown_override(interaction.guild.id)
                
                online_mods = self.get_online_moderators(interaction.guild)
                
                embed = Utils.create_embed(
                    title="🔒 Lockdown Mode Status",
                    description="Current lockdown mode information",
                    color=discord.Color.red() if is_active else discord.Color.green()
                )
                
                embed.add_field(
                    name="Status",
                    value="🔒 ACTIVE" if is_active else "🔓 INACTIVE",
                    inline=True
                )
                
                embed.add_field(
                    name="Auto-Enable",
                    value="✅ Enabled" if automod_settings.get("lockdown_auto_enable") else "❌ Disabled",
                    inline=True
                )
                
                embed.add_field(
                    name="Manual Override",
                    value="🔄 ACTIVE" if is_override else "❌ None",
                    inline=True
                )
                
                embed.add_field(
                    name="Online Moderators",
                    value=f"{len(online_mods)} online" if online_mods else "None online",
                    inline=True
                )
                
                # Add detailed moderator info for debugging
                if online_mods:
                    mod_list = []
                    for mod in online_mods[:5]:  # Show first 5 moderators
                        mod_list.append(f"• {mod.display_name} ({mod.status})")
                    
                    embed.add_field(
                        name="Detected Moderators",
                        value="\n".join(mod_list) + (f"\n... and {len(online_mods) - 5} more" if len(online_mods) > 5 else ""),
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="Debug Info",
                        value="No moderators detected. Check bot logs for details.",
                        inline=False
                    )
                
                if is_active:
                    embed.add_field(
                        name="Lockdown Settings",
                        value=f"• Caps Threshold: {automod_settings.get('lockdown_caps_threshold', 50)}%\n"
                              f"• Spam Threshold: {automod_settings.get('lockdown_spam_threshold', 3)} messages\n"
                              f"• Timeout Duration: {automod_settings.get('lockdown_timeout_duration', 300)} seconds",
                        inline=False
                    )
                
                await Utils.send_response(interaction, embed=embed)
                
            elif action == "enable":
                # Enable lockdown manually
                await self.bot.database.enable_lockdown(interaction.guild.id, manual=True)
                
                embed = Utils.create_success_embed(
                    "Lockdown mode enabled",
                    "🔒 Lockdown Mode Activated"
                )
                
                embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
                embed.add_field(name="Reason", value=reason, inline=False)
                embed.add_field(name="Note", value="Manual override active - auto-lockdown disabled until cleared", inline=False)
                
                await Utils.send_response(interaction, embed=embed)
                
                # Log the action
                await self.log_lockdown_change(interaction.guild, True, f"Manual enable by {interaction.user}: {reason}")
                log_moderation_action("lockdown_enable", interaction.user, interaction.guild, reason, interaction.guild)
                
            elif action == "disable":
                # Disable lockdown manually
                await self.bot.database.disable_lockdown(interaction.guild.id, manual=True)
                
                embed = Utils.create_success_embed(
                    "Lockdown mode disabled",
                    "🔓 Lockdown Mode Deactivated"
                )
                
                embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
                embed.add_field(name="Reason", value=reason, inline=False)
                embed.add_field(name="Note", value="Manual override active - auto-lockdown disabled until cleared", inline=False)
                
                await Utils.send_response(interaction, embed=embed)
                
                # Log the action
                await self.log_lockdown_change(interaction.guild, False, f"Manual disable by {interaction.user}: {reason}")
                log_moderation_action("lockdown_disable", interaction.user, interaction.guild, reason, interaction.guild)
                
            elif action == "clear":
                # Clear manual override
                await self.bot.database.clear_lockdown_override(interaction.guild.id)
                
                embed = Utils.create_success_embed(
                    "Manual override cleared",
                    "🔄 Lockdown Override Cleared"
                )
                
                embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
                embed.add_field(name="Effect", value="Auto-lockdown system will now resume normal operation", inline=False)
                
                await Utils.send_response(interaction, embed=embed)
                
                # Log the action
                self.bot.logger.info(f"Manual override cleared by {interaction.user} in {interaction.guild.name}")
                
        except Exception as e:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed(f"Failed to manage lockdown: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="lockdownconfig", description="Configure lockdown settings")
    @app_commands.describe(
        setting="The lockdown setting to configure",
        value="The value to set"
    )
    @app_commands.choices(setting=[
        app_commands.Choice(name="Auto-Enable", value="auto_enable"),
        app_commands.Choice(name="Caps Threshold", value="caps_threshold"),
        app_commands.Choice(name="Spam Threshold", value="spam_threshold"),
        app_commands.Choice(name="Timeout Duration", value="timeout_duration"),
    ])
    async def lockdown_config(
        self,
        interaction: discord.Interaction,
        setting: str = None,
        value: str = None
    ):
        """Configure lockdown settings"""
        if not is_superuser(interaction.user):
            if not await Utils.check_permissions(interaction, ["manage_channels"]):
                return
        
        # Check permissions
        if is_superuser(interaction.user):
            pass  # allow superuser bypass
        #     # existing permission checks
        elif not await Utils.check_permissions(interaction, ["administrator"]):
            return
        
        automod_settings = await self.bot.database.get_automod_settings(interaction.guild.id)
        
        if value is None:
            # Show current settings
            embed = Utils.create_embed(
                title="🔒 Lockdown Configuration",
                description="Current lockdown settings:",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="Auto-Enable",
                value="✅ Enabled" if automod_settings.get("lockdown_auto_enable") else "❌ Disabled",
                inline=True
            )
            
            embed.add_field(
                name="Caps Threshold",
                value=f"{automod_settings.get('lockdown_caps_threshold', 50)}%",
                inline=True
            )
            
            embed.add_field(
                name="Spam Threshold",
                value=f"{automod_settings.get('lockdown_spam_threshold', 3)} messages",
                inline=True
            )
            
            embed.add_field(
                name="Timeout Duration",
                value=f"{automod_settings.get('lockdown_timeout_duration', 300)} seconds",
                inline=True
            )
            
            embed.add_field(
                name="Usage",
                value="Use `/lockdownconfig <setting> <value>` to change settings",
                inline=False
            )
            
            await Utils.send_response(interaction, embed=embed)
            return
        
        try:
            # Update setting
            if setting == "auto_enable":
                bool_value = value.lower() in ["true", "1", "yes", "on", "enable"]
                await self.bot.database.update_automod_settings(
                    interaction.guild.id,
                    lockdown_auto_enable=bool_value
                )
                
                embed = Utils.create_success_embed(
                    f"Auto-enable lockdown {'enabled' if bool_value else 'disabled'}",
                    "Lockdown Configuration Updated"
                )
                
            elif setting == "caps_threshold":
                threshold = int(value)
                if not 1 <= threshold <= 100:
                    await Utils.send_response(
                        interaction,
                        embed=Utils.create_error_embed("Caps threshold must be between 1 and 100."),
                        ephemeral=True
                    )
                    return
                
                await self.bot.database.update_automod_settings(
                    interaction.guild.id,
                    lockdown_caps_threshold=threshold
                )
                
                embed = Utils.create_success_embed(
                    f"Lockdown caps threshold set to {threshold}%",
                    "Lockdown Configuration Updated"
                )
                
            elif setting == "spam_threshold":
                threshold = int(value)
                if not 1 <= threshold <= 10:
                    await Utils.send_response(
                        interaction,
                        embed=Utils.create_error_embed("Spam threshold must be between 1 and 10."),
                        ephemeral=True
                    )
                    return
                
                await self.bot.database.update_automod_settings(
                    interaction.guild.id,
                    lockdown_spam_threshold=threshold
                )
                
                embed = Utils.create_success_embed(
                    f"Lockdown spam threshold set to {threshold} messages",
                    "Lockdown Configuration Updated"
                )
                
            elif setting == "timeout_duration":
                duration = int(value)
                if not 60 <= duration <= 3600:
                    await Utils.send_response(
                        interaction,
                        embed=Utils.create_error_embed("Timeout duration must be between 60 and 3600 seconds."),
                        ephemeral=True
                    )
                    return
                
                await self.bot.database.update_automod_settings(
                    interaction.guild.id,
                    lockdown_timeout_duration=duration
                )
                
                embed = Utils.create_success_embed(
                    f"Lockdown timeout duration set to {duration} seconds",
                    "Lockdown Configuration Updated"
                )
            
            await Utils.send_response(interaction, embed=embed)
            
        except ValueError:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed("Invalid value. Please provide a valid number."),
                ephemeral=True
            )
        except Exception as e:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed(f"Failed to update configuration: {str(e)}"),
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(Lockdown(bot))
