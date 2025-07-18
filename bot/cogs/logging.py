import discord
from discord.ext import commands

from bot.utils.utils import Utils
from bot.utils.logger import log_moderation_action


class Logging(commands.Cog):
    """Logging functionality for moderation actions"""
    
    def __init__(self, bot):
        self.bot = bot
    
    # Member join/leave logging disabled per user request
    # @commands.Cog.listener()
    # async def on_member_join(self, member):
    #     """Log when a member joins"""
    #     await self.log_event(
    #         member.guild,
    #         "Member Joined",
    #         f"{member.mention} joined the server",
    #         discord.Color.green(),
    #         fields=[
    #             {"name": "User", "value": f"{member} ({member.id})", "inline": True},
    #             {"name": "Account Created", "value": Utils.format_timestamp(member.created_at), "inline": True},
    #         ],
    #         thumbnail=member.display_avatar.url
    #     )
    
    # @commands.Cog.listener()
    # async def on_member_remove(self, member):
    #     """Log when a member leaves"""
    #     await self.log_event(
    #         member.guild,
    #         "Member Left",
    #         f"{member.mention} left the server",
    #         discord.Color.red(),
    #         fields=[
    #             {"name": "User", "value": f"{member} ({member.id})", "inline": True},
    #             {"name": "Joined", "value": Utils.format_timestamp(member.joined_at) if member.joined_at else "Unknown", "inline": True},
    #         ],
    #         thumbnail=member.display_avatar.url
    #     )
    
    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        """Log when a member is banned"""
        # Try to get ban reason from audit log
        reason = "Unknown"
        moderator = None
        
        try:
            async for entry in guild.audit_logs(action=discord.AuditLogAction.ban, limit=1):
                if entry.target.id == user.id:
                    reason = entry.reason or "No reason provided"
                    moderator = entry.user
                    break
        except discord.HTTPException:
            pass
        
        fields = [
            {"name": "User", "value": f"{user} ({user.id})", "inline": True},
            {"name": "Reason", "value": reason, "inline": False},
        ]
        
        if moderator:
            fields.insert(1, {"name": "Moderator", "value": f"{moderator} ({moderator.id})", "inline": True})
        
        await self.log_event(
            guild,
            "Member Banned",
            f"{user.mention} was banned from the server",
            discord.Color.red(),
            fields=fields,
            thumbnail=user.display_avatar.url
        )
    
    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        """Log when a member is unbanned"""
        # Try to get unban reason from audit log
        reason = "Unknown"
        moderator = None
        
        try:
            async for entry in guild.audit_logs(action=discord.AuditLogAction.unban, limit=1):
                if entry.target.id == user.id:
                    reason = entry.reason or "No reason provided"
                    moderator = entry.user
                    break
        except discord.HTTPException:
            pass
        
        fields = [
            {"name": "User", "value": f"{user} ({user.id})", "inline": True},
            {"name": "Reason", "value": reason, "inline": False},
        ]
        
        if moderator:
            fields.insert(1, {"name": "Moderator", "value": f"{moderator} ({moderator.id})", "inline": True})
        
        await self.log_event(
            guild,
            "Member Unbanned",
            f"{user.mention} was unbanned from the server",
            discord.Color.green(),
            fields=fields,
            thumbnail=user.display_avatar.url
        )
    
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Log member updates (roles, nickname, timeout)"""
        # Check for role changes
        if before.roles != after.roles:
            added_roles = [role for role in after.roles if role not in before.roles]
            removed_roles = [role for role in before.roles if role not in after.roles]
            
            changes = []
            if added_roles:
                changes.append(f"**Added:** {', '.join(role.mention for role in added_roles)}")
            if removed_roles:
                changes.append(f"**Removed:** {', '.join(role.mention for role in removed_roles)}")
            
            if changes:
                await self.log_event(
                    after.guild,
                    "Member Roles Updated",
                    f"{after.mention}'s roles were updated",
                    discord.Color.blue(),
                    fields=[
                        {"name": "User", "value": f"{after} ({after.id})", "inline": True},
                        {"name": "Role Changes", "value": "\n".join(changes), "inline": False},
                    ],
                    thumbnail=after.display_avatar.url
                )
        
        # Check for nickname changes
        if before.nick != after.nick:
            await self.log_event(
                after.guild,
                "Nickname Updated",
                f"{after.mention}'s nickname was updated",
                discord.Color.blue(),
                fields=[
                    {"name": "User", "value": f"{after} ({after.id})", "inline": True},
                    {"name": "Before", "value": before.nick or "None", "inline": True},
                    {"name": "After", "value": after.nick or "None", "inline": True},
                ],
                thumbnail=after.display_avatar.url
            )
        
        # Check for timeout changes
        if before.timed_out_until != after.timed_out_until:
            if after.is_timed_out():
                await self.log_event(
                    after.guild,
                    "Member Timed Out",
                    f"{after.mention} was timed out",
                    discord.Color.orange(),
                    fields=[
                        {"name": "User", "value": f"{after} ({after.id})", "inline": True},
                        {"name": "Until", "value": Utils.format_timestamp(after.timed_out_until), "inline": True},
                    ],
                    thumbnail=after.display_avatar.url
                )
            else:
                await self.log_event(
                    after.guild,
                    "Timeout Removed",
                    f"{after.mention}'s timeout was removed",
                    discord.Color.green(),
                    fields=[
                        {"name": "User", "value": f"{after} ({after.id})", "inline": True},
                    ],
                    thumbnail=after.display_avatar.url
                )
    
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """Log message deletions"""
        # Ignore bot messages and DMs
        if message.author.bot or not message.guild:
            return
        
        await self.log_event(
            message.guild,
            "Message Deleted",
            f"Message by {message.author.mention} was deleted",
            discord.Color.red(),
            fields=[
                {"name": "Author", "value": f"{message.author} ({message.author.id})", "inline": True},
                {"name": "Channel", "value": message.channel.mention, "inline": True},
                {"name": "Content", "value": Utils.truncate_text(message.content or "*No content*", 1000), "inline": False},
            ],
            thumbnail=message.author.display_avatar.url
        )
    
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        """Log message edits"""
        # Ignore bot messages, DMs, and embeds
        if before.author.bot or not before.guild or before.content == after.content:
            return
        
        await self.log_event(
            before.guild,
            "Message Edited",
            f"Message by {before.author.mention} was edited",
            discord.Color.blue(),
            fields=[
                {"name": "Author", "value": f"{before.author} ({before.author.id})", "inline": True},
                {"name": "Channel", "value": before.channel.mention, "inline": True},
                {"name": "Before", "value": Utils.truncate_text(before.content or "*No content*", 500), "inline": False},
                {"name": "After", "value": Utils.truncate_text(after.content or "*No content*", 500), "inline": False},
                {"name": "Message Link", "value": f"[Jump to message]({after.jump_url})", "inline": False},
            ],
            thumbnail=before.author.display_avatar.url
        )
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Log voice state changes"""
        # Member joined voice channel
        if before.channel is None and after.channel is not None:
            await self.log_event(
                member.guild,
                "Voice Channel Joined",
                f"{member.mention} joined a voice channel",
                discord.Color.green(),
                fields=[
                    {"name": "User", "value": f"{member} ({member.id})", "inline": True},
                    {"name": "Channel", "value": after.channel.mention, "inline": True},
                ],
                thumbnail=member.display_avatar.url
            )
        
        # Member left voice channel
        elif before.channel is not None and after.channel is None:
            await self.log_event(
                member.guild,
                "Voice Channel Left",
                f"{member.mention} left a voice channel",
                discord.Color.red(),
                fields=[
                    {"name": "User", "value": f"{member} ({member.id})", "inline": True},
                    {"name": "Channel", "value": before.channel.mention, "inline": True},
                ],
                thumbnail=member.display_avatar.url
            )
        
        # Member moved between voice channels
        elif before.channel != after.channel and before.channel is not None and after.channel is not None:
            await self.log_event(
                member.guild,
                "Voice Channel Moved",
                f"{member.mention} moved between voice channels",
                discord.Color.blue(),
                fields=[
                    {"name": "User", "value": f"{member} ({member.id})", "inline": True},
                    {"name": "From", "value": before.channel.mention, "inline": True},
                    {"name": "To", "value": after.channel.mention, "inline": True},
                ],
                thumbnail=member.display_avatar.url
            )
    
    async def log_event(self, guild, title, description, color, fields=None, thumbnail=None):
        """Log an event to the guild's log channel"""
        try:
            guild_config = await self.bot.database.get_guild_config(guild.id)
            log_channel_id = guild_config.get("log_channel_id")
            
            if not log_channel_id:
                return
            
            log_channel = guild.get_channel(log_channel_id)
            if not log_channel:
                return
            
            embed = Utils.create_embed(
                title=f"📋 {title}",
                description=description,
                color=color,
                fields=fields or [],
                thumbnail=thumbnail
            )
            
            await log_channel.send(embed=embed)
            
        except discord.HTTPException as e:
            self.bot.logger.error(f"Failed to send log message: {e}")
        except Exception as e:
            self.bot.logger.error(f"Error in logging event: {e}")


async def setup(bot):
    await bot.add_cog(Logging(bot))
