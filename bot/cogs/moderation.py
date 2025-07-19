import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta

from bot.utils.utils import Utils
from bot.utils.logger import log_moderation_action


class Moderation(commands.Cog):
    """Moderation commands for the bot"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="ban", description="Ban a user from the server")
    @app_commands.describe(
        user="The user to ban",
        reason="The reason for the ban",
        duration="Duration of the ban (e.g., 1h, 2d, 1w)",
        delete_messages="How many days of messages to delete (0-7)"
    )
    async def ban(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str = None,
        duration: str = None,
        delete_messages: int = 0
    ):
        """Ban a user from the server"""
        # Check permissions
        if not await Utils.check_permissions(interaction, ["ban_members"]):
            return
        
        if not await Utils.check_bot_permissions(interaction, ["ban_members"]):
            return
        
        # Check hierarchy
        hierarchy_check, error_msg = Utils.check_hierarchy(interaction.user, user)
        if not hierarchy_check:
            await Utils.send_response(interaction, embed=Utils.create_error_embed(error_msg), ephemeral=True)
            return
        
        bot_hierarchy_check, bot_error_msg = Utils.check_bot_hierarchy(interaction.guild.me, user)
        if not bot_hierarchy_check:
            await Utils.send_response(interaction, embed=Utils.create_error_embed(bot_error_msg), ephemeral=True)
            return
        
        # Parse duration
        duration_seconds = None
        if duration:
            duration_seconds = Utils.parse_duration(duration)
            if duration_seconds is None:
                await Utils.send_response(
                    interaction,
                    embed=Utils.create_error_embed("Invalid duration format. Use format like: 1h, 2d, 1w"),
                    ephemeral=True
                )
                return
        
        # Validate delete_messages
        if delete_messages < 0 or delete_messages > 7:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed("Delete messages must be between 0 and 7 days"),
                ephemeral=True
            )
            return
        
        try:
            # Create moderation case
            case_id = await self.bot.database.create_moderation_case(
                interaction.guild.id,
                "ban",
                user.id,
                interaction.user.id,
                reason,
                duration_seconds
            )
            
            # Send DM to user before banning
            try:
                dm_embed = Utils.create_moderation_embed(
                    "banned",
                    user,
                    interaction.user,
                    reason,
                    duration_seconds
                )
                dm_embed.add_field(
                    name="Guild",
                    value=interaction.guild.name,
                    inline=False
                )
                if duration_seconds:
                    dm_embed.add_field(
                        name="Expires",
                        value=Utils.format_timestamp(datetime.now() + timedelta(seconds=duration_seconds)),
                        inline=False
                    )
                await user.send(embed=dm_embed)
            except discord.HTTPException:
                pass  # User has DMs disabled
            
            # Ban the user
            await user.ban(reason=reason, delete_message_days=delete_messages)
            
            # Add temporary punishment if duration is specified
            if duration_seconds:
                await self.bot.database.add_temp_punishment(
                    interaction.guild.id,
                    user.id,
                    "ban",
                    datetime.now() + timedelta(seconds=duration_seconds),
                    case_id
                )
            
            # Create response embed
            embed = Utils.create_moderation_embed(
                "banned",
                user,
                interaction.user,
                reason,
                duration_seconds
            )
            embed.add_field(name="Case ID", value=f"#{case_id}", inline=True)
            
            await Utils.send_response(interaction, embed=embed)
            
            # Log the action
            log_moderation_action("ban", interaction.user, user, reason, interaction.guild)
            
        except discord.HTTPException as e:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed(f"Failed to ban user: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="kick", description="Kick a user from the server")
    @app_commands.describe(
        user="The user to kick",
        reason="The reason for the kick"
    )
    async def kick(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str = None
    ):
        """Kick a user from the server"""
        # Check permissions
        if not await Utils.check_permissions(interaction, ["kick_members"]):
            return
        
        if not await Utils.check_bot_permissions(interaction, ["kick_members"]):
            return
        
        # Check hierarchy
        hierarchy_check, error_msg = Utils.check_hierarchy(interaction.user, user)
        if not hierarchy_check:
            await Utils.send_response(interaction, embed=Utils.create_error_embed(error_msg), ephemeral=True)
            return
        
        bot_hierarchy_check, bot_error_msg = Utils.check_bot_hierarchy(interaction.guild.me, user)
        if not bot_hierarchy_check:
            await Utils.send_response(interaction, embed=Utils.create_error_embed(bot_error_msg), ephemeral=True)
            return
        
        try:
            # Create moderation case
            case_id = await self.bot.database.create_moderation_case(
                interaction.guild.id,
                "kick",
                user.id,
                interaction.user.id,
                reason
            )
            
            # Send DM to user before kicking
            try:
                dm_embed = Utils.create_moderation_embed(
                    "kicked",
                    user,
                    interaction.user,
                    reason
                )
                dm_embed.add_field(
                    name="Guild",
                    value=interaction.guild.name,
                    inline=False
                )
                await user.send(embed=dm_embed)
            except discord.HTTPException:
                pass  # User has DMs disabled
            
            # Kick the user
            await user.kick(reason=reason)
            
            # Create response embed
            embed = Utils.create_moderation_embed(
                "kicked",
                user,
                interaction.user,
                reason
            )
            embed.add_field(name="Case ID", value=f"#{case_id}", inline=True)
            
            await Utils.send_response(interaction, embed=embed)
            
            # Log the action
            log_moderation_action("kick", interaction.user, user, reason, interaction.guild)
            
        except discord.HTTPException as e:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed(f"Failed to kick user: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="timeout", description="Timeout a user")
    @app_commands.describe(
        user="The user to timeout",
        duration="Duration of the timeout (e.g., 10m, 1h, 2d)",
        reason="The reason for the timeout"
    )
    async def timeout(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        duration: str,
        reason: str = None
    ):
        """Timeout a user"""
        # Check permissions
        if not await Utils.check_permissions(interaction, ["moderate_members"]):
            return
        
        if not await Utils.check_bot_permissions(interaction, ["moderate_members"]):
            return
        
        # Check hierarchy
        hierarchy_check, error_msg = Utils.check_hierarchy(interaction.user, user)
        if not hierarchy_check:
            await Utils.send_response(interaction, embed=Utils.create_error_embed(error_msg), ephemeral=True)
            return
        
        bot_hierarchy_check, bot_error_msg = Utils.check_bot_hierarchy(interaction.guild.me, user)
        if not bot_hierarchy_check:
            await Utils.send_response(interaction, embed=Utils.create_error_embed(bot_error_msg), ephemeral=True)
            return
        
        # Parse duration
        duration_seconds = Utils.parse_duration(duration)
        if duration_seconds is None:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed("Invalid duration format. Use format like: 10m, 1h, 2d"),
                ephemeral=True
            )
            return
        
        # Check duration limits (Discord limit is 28 days)
        if duration_seconds > 28 * 24 * 60 * 60:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed("Timeout duration cannot exceed 28 days"),
                ephemeral=True
            )
            return
        
        try:
            # Create moderation case
            case_id = await self.bot.database.create_moderation_case(
                interaction.guild.id,
                "timeout",
                user.id,
                interaction.user.id,
                reason,
                duration_seconds
            )
            
            # Timeout the user
            timeout_until = datetime.now() + timedelta(seconds=duration_seconds)
            await user.timeout(timeout_until, reason=reason)
            
            # Add temporary punishment
            await self.bot.database.add_temp_punishment(
                interaction.guild.id,
                user.id,
                "timeout",
                timeout_until,
                case_id
            )
            
            # Create response embed
            embed = Utils.create_moderation_embed(
                "timed out",
                user,
                interaction.user,
                reason,
                duration_seconds
            )
            embed.add_field(name="Case ID", value=f"#{case_id}", inline=True)
            embed.add_field(
                name="Expires",
                value=Utils.format_timestamp(timeout_until),
                inline=True
            )
            
            await Utils.send_response(interaction, embed=embed)
            
            # Log the action
            log_moderation_action("timeout", interaction.user, user, reason, interaction.guild)
            
        except discord.HTTPException as e:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed(f"Failed to timeout user: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="untimeout", description="Remove timeout from a user")
    @app_commands.describe(
        user="The user to remove timeout from",
        reason="The reason for removing the timeout"
    )
    async def untimeout(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str = None
    ):
        """Remove timeout from a user"""
        # Check permissions
        if not await Utils.check_permissions(interaction, ["moderate_members"]):
            return
        
        if not await Utils.check_bot_permissions(interaction, ["moderate_members"]):
            return
        
        # Check if user is timed out
        if not user.is_timed_out():
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed("This user is not timed out"),
                ephemeral=True
            )
            return
        
        try:
            # Remove timeout
            await user.timeout(None, reason=reason)
            
            # Create response embed
            embed = Utils.create_success_embed(
                f"Removed timeout from {user.mention}",
                "Timeout Removed"
            )
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            embed.add_field(name="Reason", value=reason or "No reason provided", inline=False)
            
            await Utils.send_response(interaction, embed=embed)
            
            # Log the action
            log_moderation_action("untimeout", interaction.user, user, reason, interaction.guild)
            
        except discord.HTTPException as e:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed(f"Failed to remove timeout: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="warn", description="Warn a user")
    @app_commands.describe(
        user="The user to warn",
        reason="The reason for the warning"
    )
    async def warn(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str
    ):
        """Warn a user"""
        # Check permissions
        if not await Utils.check_permissions(interaction, ["kick_members"]):
            return
        
        try:
            # Add warning to database
            warning_id = await self.bot.database.add_warning(
                interaction.guild.id,
                user.id,
                interaction.user.id,
                reason
            )
            
            # Get warning count
            warning_count = await self.bot.database.get_warning_count(interaction.guild.id, user.id)
            
            # Create moderation case
            case_id = await self.bot.database.create_moderation_case(
                interaction.guild.id,
                "warn",
                user.id,
                interaction.user.id,
                reason
            )
            
            # Send DM to user
            try:
                dm_embed = Utils.create_warning_embed(
                    f"You have been warned in **{interaction.guild.name}**\n\n"
                    f"**Reason:** {reason}\n"
                    f"**Warning #{warning_count}** (Total: {warning_count})",
                    "Warning Received"
                )
                await user.send(embed=dm_embed)
            except discord.HTTPException:
                pass  # User has DMs disabled
            
            # Create response embed
            embed = Utils.create_moderation_embed(
                "warned",
                user,
                interaction.user,
                reason
            )
            embed.add_field(name="Case ID", value=f"#{case_id}", inline=True)
            embed.add_field(name="Warning Count", value=str(warning_count), inline=True)
            
            # Check if user reached warning limit
            guild_config = await self.bot.database.get_guild_config(interaction.guild.id)
            max_warnings = guild_config.get("max_warnings", 3)
            
            if warning_count >= max_warnings:
                embed.add_field(
                    name="⚠️ Warning Limit Reached",
                    value=f"This user has reached the warning limit ({max_warnings}). Consider taking further action.",
                    inline=False
                )
                embed.color = discord.Color.red()
            
            await Utils.send_response(interaction, embed=embed)
            
            # Log the action
            log_moderation_action("warn", interaction.user, user, reason, interaction.guild)
            
        except Exception as e:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed(f"Failed to warn user: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="warnings", description="View warnings for a user")
    @app_commands.describe(user="The user to view warnings for")
    async def warnings(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ):
        """View warnings for a user"""
        # Check permissions
        if not await Utils.check_permissions(interaction, ["kick_members"]):
            return
        
        try:
            # Get warnings from database
            warnings = await self.bot.database.get_warnings(interaction.guild.id, user.id)
            
            if not warnings:
                embed = Utils.create_info_embed(
                    f"{user.mention} has no warnings",
                    "No Warnings Found"
                )
                await Utils.send_response(interaction, embed=embed, ephemeral=True)
                return
            
            # Create embed with warnings
            embed = Utils.create_embed(
                title=f"Warnings for {user.display_name}",
                description=f"Total warnings: {len(warnings)}",
                color=discord.Color.orange(),
                thumbnail=user.display_avatar.url
            )
            
            for i, warning in enumerate(warnings[:10], 1):  # Show max 10 warnings
                moderator = interaction.guild.get_member(warning["moderator_id"])
                moderator_name = moderator.display_name if moderator else "Unknown"
                
                embed.add_field(
                    name=f"Warning #{i} (ID: {warning['id']})",
                    value=f"**Reason:** {warning['reason']}\n"
                          f"**Moderator:** {moderator_name}\n"
                          f"**Date:** {Utils.format_timestamp(datetime.fromisoformat(warning['created_at']))}",
                    inline=False
                )
            
            if len(warnings) > 10:
                embed.add_field(
                    name="Note",
                    value=f"Showing 10 of {len(warnings)} warnings",
                    inline=False
                )
            
            embed.add_field(
                name="Management Commands",
                value="• `/removewarning <warning_id>` - Remove a specific warning\n"
                      "• `/clearwarnings <user>` - Clear all warnings for a user",
                inline=False
            )
            
            await Utils.send_response(interaction, embed=embed, ephemeral=True)
            
        except Exception as e:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed(f"Failed to retrieve warnings: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="purge", description="Delete multiple messages")
    @app_commands.describe(
        amount="Number of messages to delete (1-100)",
        user="Only delete messages from this user",
        reason="The reason for the purge"
    )
    async def purge(
        self,
        interaction: discord.Interaction,
        amount: int,
        user: discord.Member = None,
        reason: str = None
    ):
        """Delete multiple messages"""
        # Check permissions
        if not await Utils.check_permissions(interaction, ["manage_messages"]):
            return
        
        if not await Utils.check_bot_permissions(interaction, ["manage_messages"]):
            return
        
        # Validate amount
        if amount < 1 or amount > 100:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed("Amount must be between 1 and 100"),
                ephemeral=True
            )
            return
        
        try:
            # Defer the response as this might take a while
            await interaction.response.defer()
            
            # Define check function
            def check(message):
                if user:
                    return message.author == user
                return True
            
            # Delete messages
            deleted = await interaction.channel.purge(limit=amount, check=check)
            
            # Create response embed
            embed = Utils.create_success_embed(
                f"Deleted {len(deleted)} message{'s' if len(deleted) != 1 else ''}",
                "Messages Purged"
            )
            embed.add_field(name="Channel", value=interaction.channel.mention, inline=True)
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            if user:
                embed.add_field(name="Target User", value=user.mention, inline=True)
            if reason:
                embed.add_field(name="Reason", value=reason, inline=False)
            
            await interaction.followup.send(embed=embed)
            
            # Log the action
            log_moderation_action("purge", interaction.user, user or "all users", reason, interaction.guild)
            
        except discord.HTTPException as e:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed(f"Failed to purge messages: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="clearwarnings", description="Clear all warnings for a user")
    @app_commands.describe(
        user="The user to clear warnings for",
        reason="The reason for clearing warnings"
    )
    async def clear_warnings(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str = "No reason provided"
    ):
        """Clear all warnings for a user"""
        # Check permissions
        if not await Utils.check_permissions(interaction, ["kick_members"]):
            return
        
        try:
            # Get current warning count
            warning_count = await self.bot.database.get_warning_count(interaction.guild.id, user.id)
            
            if warning_count == 0:
                await Utils.send_response(
                    interaction,
                    embed=Utils.create_info_embed(f"{user.mention} has no active warnings to clear."),
                    ephemeral=True
                )
                return
            
            # Clear warnings
            cleared_count = await self.bot.database.clear_warnings(interaction.guild.id, user.id)
            
            # Create moderation case
            await self.bot.database.create_moderation_case(
                interaction.guild.id,
                "clear_warnings",
                user.id,
                interaction.user.id,
                reason
            )
            
            # Create success embed
            embed = Utils.create_success_embed(
                f"Cleared {cleared_count} warning(s) for {user.mention}",
                "Warnings Cleared"
            )
            
            embed.add_field(name="User", value=user.mention, inline=True)
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            embed.add_field(name="Warnings Cleared", value=str(cleared_count), inline=True)
            if reason:
                embed.add_field(name="Reason", value=reason, inline=False)
            
            await Utils.send_response(interaction, embed=embed)
            
            # Send DM to user
            try:
                dm_embed = Utils.create_info_embed(
                    f"Your warnings have been cleared in **{interaction.guild.name}**\n\n"
                    f"**Reason:** {reason}\n"
                    f"**Warnings Cleared:** {cleared_count}",
                    "Warnings Cleared"
                )
                await user.send(embed=dm_embed)
            except discord.HTTPException:
                pass  # User has DMs disabled
            
            # Log the action
            log_moderation_action("clear_warnings", interaction.user, user, reason, interaction.guild)
            
        except Exception as e:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed(f"Failed to clear warnings: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="removewarning", description="Remove a specific warning by ID")
    @app_commands.describe(
        warning_id="The ID of the warning to remove",
        reason="The reason for removing the warning"
    )
    async def remove_warning(
        self,
        interaction: discord.Interaction,
        warning_id: int,
        reason: str = "No reason provided"
    ):
        """Remove a specific warning by ID"""
        # Check permissions
        if not await Utils.check_permissions(interaction, ["kick_members"]):
            return
        
        try:
            # Get the warning to check if it exists and belongs to this guild
            warnings = await self.bot.database.get_all_warnings(interaction.guild.id)
            warning_to_remove = None
            
            for warning in warnings:
                if warning["id"] == warning_id:
                    warning_to_remove = warning
                    break
            
            if not warning_to_remove:
                await Utils.send_response(
                    interaction,
                    embed=Utils.create_error_embed(f"Warning with ID {warning_id} not found in this server."),
                    ephemeral=True
                )
                return
            
            # Remove the warning
            await self.bot.database.remove_warning(warning_id)
            
            # Get the user
            user = interaction.guild.get_member(warning_to_remove["user_id"])
            user_mention = user.mention if user else f"<@{warning_to_remove['user_id']}>"
            
            # Create success embed
            embed = Utils.create_success_embed(
                f"Removed warning #{warning_id} for {user_mention}",
                "Warning Removed"
            )
            
            embed.add_field(name="Warning ID", value=str(warning_id), inline=True)
            embed.add_field(name="User", value=user_mention, inline=True)
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            embed.add_field(name="Original Reason", value=warning_to_remove["reason"], inline=False)
            if reason:
                embed.add_field(name="Removal Reason", value=reason, inline=False)
            
            await Utils.send_response(interaction, embed=embed)
            
            # Send DM to user if they're still in the server
            if user:
                try:
                    dm_embed = Utils.create_info_embed(
                        f"One of your warnings has been removed in **{interaction.guild.name}**\n\n"
                        f"**Warning ID:** {warning_id}\n"
                        f"**Original Reason:** {warning_to_remove['reason']}\n"
                        f"**Removal Reason:** {reason}",
                        "Warning Removed"
                    )
                    await user.send(embed=dm_embed)
                except discord.HTTPException:
                    pass  # User has DMs disabled
            
            # Log the action
            log_moderation_action("remove_warning", interaction.user, user or f"User ID {warning_to_remove['user_id']}", reason, interaction.guild)
            
        except Exception as e:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed(f"Failed to remove warning: {str(e)}"),
                ephemeral=True
            )

    @app_commands.command(name="case", description="Look up a specific moderation case")
    @app_commands.describe(case_id="The case ID to look up")
    async def case_lookup(self, interaction: discord.Interaction, case_id: int):
        """Look up a specific moderation case"""
        # Check permissions
        if not await Utils.check_permissions(interaction, ["moderate_members"]):
            return
        
        try:
            case = await self.bot.database.get_moderation_case(case_id)
            
            if not case or case['guild_id'] != interaction.guild.id:
                await Utils.send_response(
                    interaction,
                    embed=Utils.create_error_embed("Case not found or belongs to another server"),
                    ephemeral=True
                )
                return
            
            # Get user and moderator objects
            user = self.bot.get_user(case['user_id']) or await self.bot.fetch_user(case['user_id'])
            moderator = self.bot.get_user(case['moderator_id']) or await self.bot.fetch_user(case['moderator_id'])
            
            # Format the case information
            embed = Utils.create_embed(
                title=f"📋 Case #{case['id']}",
                description=f"**Action:** {case['action_type'].title()}",
                color=discord.Color.blue(),
                fields=[
                    {"name": "User", "value": f"{user.mention if user else 'Unknown User'}\n{user.name if user else 'Unknown'}#{user.discriminator if user else '0000'}\nID: {case['user_id']}", "inline": True},
                    {"name": "Moderator", "value": f"{moderator.mention if moderator else 'Unknown Moderator'}\n{moderator.name if moderator else 'Unknown'}#{moderator.discriminator if moderator else '0000'}\nID: {case['moderator_id']}", "inline": True},
                    {"name": "Date", "value": Utils.format_timestamp(datetime.fromisoformat(case['created_at'])), "inline": True},
                    {"name": "Reason", "value": case['reason'] or "No reason provided", "inline": False}
                ]
            )
            
            # Add duration if applicable
            if case['duration']:
                embed.add_field(
                    name="Duration", 
                    value=Utils.format_duration(case['duration']), 
                    inline=True
                )
            
            # Add status
            status = "🟢 Active" if case['active'] else "🔴 Inactive"
            embed.add_field(name="Status", value=status, inline=True)
            
            if user:
                embed.set_thumbnail(url=user.display_avatar.url)
            
            await Utils.send_response(interaction, embed=embed)
            
        except Exception as e:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed(f"Failed to look up case: {str(e)}"),
                ephemeral=True
            )

    @app_commands.command(name="history", description="View moderation history for a user")
    @app_commands.describe(
        user="The user to check history for",
        limit="Number of cases to show (default: 10, max: 25)"
    )
    async def moderation_history(
        self, 
        interaction: discord.Interaction, 
        user: discord.Member,
        limit: int = 10
    ):
        """View moderation history for a user"""
        # Check permissions
        if not await Utils.check_permissions(interaction, ["moderate_members"]):
            return
        
        # Validate limit
        if limit < 1 or limit > 25:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed("Limit must be between 1 and 25"),
                ephemeral=True
            )
            return
        
        try:
            cases = await self.bot.database.get_user_cases(interaction.guild.id, user.id)
            
            if not cases:
                await Utils.send_response(
                    interaction,
                    embed=Utils.create_embed(
                        title=f"📋 Moderation History - {user.display_name}",
                        description="No moderation cases found for this user.",
                        color=discord.Color.green()
                    )
                )
                return
            
            # Limit the results
            cases = cases[:limit]
            
            embed = Utils.create_embed(
                title=f"📋 Moderation History - {user.display_name}",
                description=f"Showing {len(cases)} of {len(await self.bot.database.get_user_cases(interaction.guild.id, user.id))} total cases",
                color=discord.Color.blue(),
                thumbnail=user.display_avatar.url
            )
            
            # Add case information
            for case in cases:
                moderator = self.bot.get_user(case['moderator_id'])
                moderator_name = moderator.name if moderator else "Unknown"
                
                status = "🟢" if case['active'] else "🔴"
                case_info = f"{status} **{case['action_type'].title()}** by {moderator_name}"
                case_info += f"\n**Reason:** {case['reason'] or 'No reason provided'}"
                case_info += f"\n**Date:** {Utils.format_timestamp(datetime.fromisoformat(case['created_at']))}"
                
                if case['duration']:
                    case_info += f"\n**Duration:** {Utils.format_duration(case['duration'])}"
                
                embed.add_field(
                    name=f"Case #{case['id']}",
                    value=case_info,
                    inline=False
                )
            
            # Add summary at the bottom
            active_cases = [c for c in await self.bot.database.get_user_cases(interaction.guild.id, user.id) if c['active']]
            embed.add_field(
                name="Summary",
                value=f"**Total Cases:** {len(await self.bot.database.get_user_cases(interaction.guild.id, user.id))}\n**Active Cases:** {len(active_cases)}",
                inline=False
            )
            
            await Utils.send_response(interaction, embed=embed)
            
        except Exception as e:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed(f"Failed to get moderation history: {str(e)}"),
                ephemeral=True
            )

    @app_commands.command(name="recent", description="View recent moderation actions in this server")
    @app_commands.describe(limit="Number of recent cases to show (default: 10, max: 20)")
    async def recent_cases(self, interaction: discord.Interaction, limit: int = 10):
        """View recent moderation actions in the server"""
        # Check permissions
        if not await Utils.check_permissions(interaction, ["moderate_members"]):
            return
        
        # Validate limit
        if limit < 1 or limit > 20:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed("Limit must be between 1 and 20"),
                ephemeral=True
            )
            return
        
        try:
            # Get recent cases from database
            async with self.bot.database.connection.execute(
                """SELECT * FROM moderation_cases 
                   WHERE guild_id = ? 
                   ORDER BY created_at DESC 
                   LIMIT ?""",
                (interaction.guild.id, limit)
            ) as cursor:
                rows = await cursor.fetchall()
                cases = [dict(zip([col[0] for col in cursor.description], row)) for row in rows]
            
            if not cases:
                await Utils.send_response(
                    interaction,
                    embed=Utils.create_embed(
                        title="📋 Recent Moderation Actions",
                        description="No moderation cases found for this server.",
                        color=discord.Color.green()
                    )
                )
                return
            
            embed = Utils.create_embed(
                title="📋 Recent Moderation Actions",
                description=f"Showing {len(cases)} most recent moderation actions",
                color=discord.Color.blue()
            )
            
            # Add case information
            for case in cases:
                user = self.bot.get_user(case['user_id'])
                moderator = self.bot.get_user(case['moderator_id'])
                
                user_name = user.name if user else f"Unknown User ({case['user_id']})"
                moderator_name = moderator.name if moderator else f"Unknown Moderator ({case['moderator_id']})"
                
                status = "🟢" if case['active'] else "🔴"
                case_info = f"{status} **{case['action_type'].title()}** on {user_name}"
                case_info += f"\n**Moderator:** {moderator_name}"
                case_info += f"\n**Reason:** {case['reason'] or 'No reason provided'}"
                case_info += f"\n**Date:** {Utils.format_timestamp(datetime.fromisoformat(case['created_at']))}"
                
                if case['duration']:
                    case_info += f"\n**Duration:** {Utils.format_duration(case['duration'])}"
                
                embed.add_field(
                    name=f"Case #{case['id']}",
                    value=case_info,
                    inline=False
                )
            
            await Utils.send_response(interaction, embed=embed)
            
        except Exception as e:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed(f"Failed to get recent cases: {str(e)}"),
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(Moderation(bot))
