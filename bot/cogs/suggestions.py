import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from collections import defaultdict
import logging

from bot.utils.utils import Utils, is_superuser


class BotSuggestions(commands.Cog):
    """Bot suggestions based on user activity and moderation history"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        # Track voice activity: guild_id -> {user_id: join_time}
        self.voice_sessions = defaultdict(dict)

    async def cog_load(self):
        """Initialize activity tracking for existing voice channel members"""
        for guild in self.bot.guilds:
            for voice_channel in guild.voice_channels:
                for member in voice_channel.members:
                    if not member.bot:
                        self.voice_sessions[guild.id][member.id] = datetime.now()

    @commands.Cog.listener()
    async def on_message(self, message):
        """Track message activity for all users"""
        if message.author.bot or not message.guild:
            return
        
        # Update activity in database
        await self.bot.database.update_user_activity(
            message.guild.id, 
            message.author.id, 
            message_count=1
        )

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Track voice channel activity"""
        if member.bot:
            return
            
        guild_id = member.guild.id
        user_id = member.id
        now = datetime.now()
        
        # User left voice channel
        if before.channel and not after.channel:
            if user_id in self.voice_sessions[guild_id]:
                join_time = self.voice_sessions[guild_id].pop(user_id)
                minutes_spent = (now - join_time).total_seconds() / 60
                # Update database with voice minutes
                await self.bot.database.update_user_activity(
                    guild_id, 
                    user_id, 
                    voice_minutes=int(minutes_spent)
                )
        
        # User joined voice channel
        elif not before.channel and after.channel:
            self.voice_sessions[guild_id][user_id] = now
        
        # User switched channels (end previous session, start new one)
        elif before.channel and after.channel and before.channel != after.channel:
            if user_id in self.voice_sessions[guild_id]:
                join_time = self.voice_sessions[guild_id][user_id]
                minutes_spent = (now - join_time).total_seconds() / 60
                # Update database with voice minutes
                await self.bot.database.update_user_activity(
                    guild_id, 
                    user_id, 
                    voice_minutes=int(minutes_spent)
                )
                self.voice_sessions[guild_id][user_id] = now

    async def calculate_activity_score(self, guild_id: int, user_id: int, days: int = 30) -> dict:
        """Calculate activity score for a user"""
        # Get activity data from database
        activity_data = await self.bot.database.get_user_activity(guild_id, user_id, days)
        
        message_count = activity_data["message_count"]
        voice_minutes = activity_data["voice_minutes"]
        
        # Calculate score (weighted combination)
        # Messages: 1 point per message (up to 1000)
        # Voice: 1 point per 10 minutes (up to 500)
        message_score = min(message_count, 1000)
        voice_score = min(voice_minutes / 10, 500)
        
        total_score = message_score + voice_score
        
        return {
            "total_score": total_score,
            "message_count": message_count,
            "voice_minutes": voice_minutes,
            "message_score": message_score,
            "voice_score": voice_score,
            "days_tracked": days
        }

    async def get_user_moderation_stats(self, guild_id: int, user_id: int) -> dict:
        """Get moderation statistics for a user"""
        # Get warnings count
        warning_count = await self.bot.database.get_warning_count(guild_id, user_id)
        
        # Get all moderation cases for this user
        cases = []
        all_cases = await self.bot.database.get_active_cases(guild_id)
        for case in all_cases:
            if case["user_id"] == user_id:
                cases.append(case)
        
        # Count different types of punishments
        bans = sum(1 for case in cases if case["case_type"] == "ban")
        kicks = sum(1 for case in cases if case["case_type"] == "kick")
        timeouts = sum(1 for case in cases if case["case_type"] == "timeout")
        
        return {
            "warning_count": warning_count,
            "total_cases": len(cases),
            "bans": bans,
            "kicks": kicks,
            "timeouts": timeouts
        }

    def has_moderation_permissions(self, member: discord.Member) -> bool:
        """Check if user already has moderation permissions"""
        return (
            member.guild_permissions.kick_members or
            member.guild_permissions.ban_members or
            member.guild_permissions.manage_messages or
            member.guild_permissions.moderate_members or
            member.guild_permissions.administrator
        )

    @app_commands.command(name="suggest_mods", description="Get suggestions for potential moderators")
    @app_commands.describe(
        min_activity="Minimum activity score (default: 100)",
        max_warnings="Maximum warnings allowed (default: 0)",
        limit="Number of suggestions to show (default: 10)"
    )
    async def suggest_mods(
        self, 
        interaction: discord.Interaction, 
        min_activity: int = 100,
        max_warnings: int = 0,
        limit: int = 10
    ):
        """Suggest potential moderators based on activity and clean record"""
        # Check permissions
        if not is_superuser(interaction.user):
            if not await Utils.check_permissions(interaction, ["manage_guild"]):
                return

        try:
            await interaction.response.defer()
            
            guild = interaction.guild
            suggestions = []
            
            for member in guild.members:
                # Skip bots
                if member.bot:
                    continue
                    
                # Skip users who already have moderation permissions
                if self.has_moderation_permissions(member):
                    continue
                
                # Calculate activity score
                activity_data = await self.calculate_activity_score(guild.id, member.id)
                
                # Skip if activity is too low
                if activity_data["total_score"] < min_activity:
                    continue
                
                # Get moderation stats
                mod_stats = await self.get_user_moderation_stats(guild.id, member.id)
                
                # Skip if too many warnings
                if mod_stats["warning_count"] > max_warnings:
                    continue
                
                # Skip if they have serious punishments
                if mod_stats["bans"] > 0 or mod_stats["kicks"] > 0:
                    continue
                
                suggestions.append({
                    "member": member,
                    "activity": activity_data,
                    "moderation": mod_stats
                })
            
            # Sort by activity score (descending)
            suggestions.sort(key=lambda x: x["activity"]["total_score"], reverse=True)
            
            # Limit results
            suggestions = suggestions[:limit]
            
            if not suggestions:
                embed = Utils.create_info_embed(
                    "No moderator suggestions found with the current criteria.\n\n"
                    f"**Criteria:**\n"
                    f"• Minimum activity score: {min_activity}\n"
                    f"• Maximum warnings: {max_warnings}\n"
                    f"• Must not have existing moderation permissions\n"
                    f"• Must not have bans or kicks",
                    "No Suggestions"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Create embed with suggestions
            embed = Utils.create_embed(
                title="🏆 Moderator Suggestions",
                description=f"Top {len(suggestions)} candidates based on activity and clean record",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="📊 Criteria Used",
                value=f"• Min activity score: {min_activity}\n"
                      f"• Max warnings: {max_warnings}\n"
                      f"• No existing mod permissions\n"
                      f"• No serious punishments",
                inline=False
            )
            
            for i, suggestion in enumerate(suggestions, 1):
                member = suggestion["member"]
                activity = suggestion["activity"]
                mod_stats = suggestion["moderation"]
                
                # Create activity breakdown
                activity_text = (
                    f"**Total Score:** {activity['total_score']:.0f}\n"
                    f"• Messages: {activity['message_count']} ({activity['message_score']:.0f} pts)\n"
                    f"• Voice: {activity['voice_minutes']:.0f}m ({activity['voice_score']:.0f} pts)"
                )
                
                # Add moderation info if any
                if mod_stats["warning_count"] > 0:
                    activity_text += f"\n• Warnings: {mod_stats['warning_count']}"
                
                embed.add_field(
                    name=f"#{i} {member.display_name}",
                    value=f"{member.mention}\n{activity_text}",
                    inline=True
                )
                
                # Add empty field for better formatting every 2 suggestions
                if i % 2 == 0:
                    embed.add_field(name="\u200b", value="\u200b", inline=True)
            
            embed.add_field(
                name="📝 Notes",
                value="• Activity tracked over last 30 days\n"
                      "• Scores: Messages (1pt each, max 1000) + Voice (1pt per 10min, max 500)\n"
                      "• Users with existing mod permissions are excluded",
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"Error in suggest_mods command: {e}")
            embed = Utils.create_error_embed(f"Failed to generate suggestions: {str(e)}")
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="user_activity", description="View detailed activity stats for a user")
    @app_commands.describe(
        user="The user to view activity for (can be member or user ID)",
        days="Number of days to look back (default: 30)"
    )
    async def user_activity(
        self, 
        interaction: discord.Interaction, 
        user: str,  # Changed from discord.Member to str to accept both mentions and IDs
        days: int = 30
    ):
        """View detailed activity statistics for a user"""
        # Check permissions
        if not is_superuser(interaction.user):
            if not await Utils.check_permissions(interaction, ["view_audit_log"]):
                return

        try:
            # Parse user input (could be mention, ID, or username)
            user_id = None
            user_obj = None
            
            # Try to extract user ID from mention format
            if user.startswith('<@') and user.endswith('>'):
                user_id_str = user[2:-1]
                if user_id_str.startswith('!'):
                    user_id_str = user_id_str[1:]
                try:
                    user_id = int(user_id_str)
                except ValueError:
                    pass
            else:
                # Try to parse as direct user ID
                try:
                    user_id = int(user)
                except ValueError:
                    # Try to find by username/display name
                    for member in interaction.guild.members:
                        if (member.name.lower() == user.lower() or 
                            member.display_name.lower() == user.lower() or
                            str(member) == user):
                            user_id = member.id
                            user_obj = member
                            break
            
            if user_id is None:
                await Utils.send_response(
                    interaction,
                    embed=Utils.create_error_embed("Could not find user. Please use @mention, user ID, or exact username."),
                    ephemeral=True
                )
                return
            
            # Try to get user object (may be None if user left/banned)
            if user_obj is None:
                user_obj = interaction.guild.get_member(user_id)
                if user_obj is None:
                    # Try to fetch user from Discord API
                    try:
                        user_obj = await self.bot.fetch_user(user_id)
                    except discord.NotFound:
                        await Utils.send_response(
                            interaction,
                            embed=Utils.create_error_embed("User not found."),
                            ephemeral=True
                        )
                        return

            # Calculate activity score
            activity_data = await self.calculate_activity_score(interaction.guild.id, user_id, days)
            
            # Get moderation stats
            mod_stats = await self.get_user_moderation_stats(interaction.guild.id, user_id)
            
            # Check if user has mod permissions (only if they're still in the server)
            has_mod_perms = False
            if isinstance(user_obj, discord.Member):
                has_mod_perms = self.has_moderation_permissions(user_obj)
            
            # Create embed
            display_name = getattr(user_obj, 'display_name', getattr(user_obj, 'name', f'User {user_id}'))
            embed = Utils.create_embed(
                title=f"📊 Activity Report - {display_name}",
                description=f"Activity statistics for {user_obj.mention if hasattr(user_obj, 'mention') else f'User ID: {user_id}'}",
                color=discord.Color.blue(),
                thumbnail=getattr(user_obj, 'display_avatar', getattr(user_obj, 'avatar', None))
            )
            
            # Add status indicator for banned/left users
            if not isinstance(user_obj, discord.Member):
                embed.add_field(
                    name="⚠️ Status",
                    value="This user is no longer in the server (banned/left)",
                    inline=False
                )
            
            # Activity section
            embed.add_field(
                name="📈 Activity (Last 30 Days)",
                value=f"**Total Score:** {activity_data['total_score']:.0f}\n"
                      f"• Messages: {activity_data['message_count']} ({activity_data['message_score']:.0f} pts)\n"
                      f"• Voice Time: {activity_data['voice_minutes']:.0f} minutes ({activity_data['voice_score']:.0f} pts)",
                inline=False
            )
            
            # Moderation history section
            mod_text = f"**Warnings:** {mod_stats['warning_count']}\n"
            mod_text += f"**Total Cases:** {mod_stats['total_cases']}\n"
            if mod_stats['total_cases'] > 0:
                mod_text += f"• Bans: {mod_stats['bans']}\n"
                mod_text += f"• Kicks: {mod_stats['kicks']}\n"
                mod_text += f"• Timeouts: {mod_stats['timeouts']}"
            
            embed.add_field(
                name="⚖️ Moderation History",
                value=mod_text,
                inline=True
            )
            
            # Permissions section (only if user is still in server)
            perms_text = "✅ Has moderation permissions" if has_mod_perms else "❌ No moderation permissions"
            if has_mod_perms and isinstance(user_obj, discord.Member):
                mod_perms = []
                if user_obj.guild_permissions.administrator:
                    mod_perms.append("Administrator")
                else:
                    if user_obj.guild_permissions.kick_members:
                        mod_perms.append("Kick Members")
                    if user_obj.guild_permissions.ban_members:
                        mod_perms.append("Ban Members")
                    if user_obj.guild_permissions.manage_messages:
                        mod_perms.append("Manage Messages")
                    if user_obj.guild_permissions.moderate_members:
                        mod_perms.append("Moderate Members")
                perms_text += f"\n• {', '.join(mod_perms)}"
            elif not isinstance(user_obj, discord.Member):
                perms_text = "N/A (User not in server)"
            
            embed.add_field(
                name="🔑 Permissions",
                value=perms_text,
                inline=True
            )
            
            # Suggestion verdict
            if has_mod_perms:
                verdict = "❌ Already has moderation permissions"
                verdict_color = discord.Color.red()
            elif mod_stats['warning_count'] > 0 or mod_stats['bans'] > 0 or mod_stats['kicks'] > 0:
                verdict = "❌ Has moderation history"
                verdict_color = discord.Color.red()
            elif not isinstance(user_obj, discord.Member):
                verdict = "❌ User not in server"
                verdict_color = discord.Color.red()
            elif activity_data['total_score'] < 100:
                verdict = "⚠️ Low activity score"
                verdict_color = discord.Color.orange()
            else:
                verdict = "✅ Good candidate for moderation role"
                verdict_color = discord.Color.green()
            
            embed.add_field(
                name="🏆 Mod Candidate Assessment",
                value=verdict,
                inline=False
            )
            
            embed.color = verdict_color
            
            await Utils.send_response(interaction, embed=embed, ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"Error in user_activity command: {e}")
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed(f"Failed to get user activity: {str(e)}"),
                ephemeral=True
            )

    @app_commands.command(name="activity_leaderboard", description="Show most active users in the server")
    @app_commands.describe(
        limit="Number of users to show (default: 15)",
        exclude_mods="Exclude users with moderation permissions (default: True)"
    )
    async def activity_leaderboard(
        self, 
        interaction: discord.Interaction, 
        limit: int = 15,
        exclude_mods: bool = True
    ):
        """Show activity leaderboard for the server"""
        # Check permissions
        if not is_superuser(interaction.user):
            if not await Utils.check_permissions(interaction, ["view_audit_log"]):
                return

        try:
            await interaction.response.defer()
            
            guild = interaction.guild
            leaderboard = []
            
            for member in guild.members:
                # Skip bots
                if member.bot:
                    continue
                    
                # Skip mods if requested
                if exclude_mods and self.has_moderation_permissions(member):
                    continue
                
                # Calculate activity score
                activity_data = await self.calculate_activity_score(guild.id, member.id)
                
                # Skip users with no activity
                if activity_data["total_score"] == 0:
                    continue
                
                leaderboard.append({
                    "member": member,
                    "activity": activity_data
                })
            
            # Sort by activity score (descending)
            leaderboard.sort(key=lambda x: x["activity"]["total_score"], reverse=True)
            
            # Limit results
            leaderboard = leaderboard[:limit]
            
            if not leaderboard:
                embed = Utils.create_info_embed(
                    "No active users found with the current criteria.",
                    "No Activity Data"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Create embed
            embed = Utils.create_embed(
                title="📊 Activity Leaderboard",
                description=f"Top {len(leaderboard)} most active users (last 30 days)",
                color=discord.Color.blue()
            )
            
            if exclude_mods:
                embed.description += "\n*Users with moderation permissions excluded*"
            
            leaderboard_text = ""
            for i, entry in enumerate(leaderboard, 1):
                member = entry["member"]
                activity = entry["activity"]
                
                # Add medal emojis for top 3
                medal = ""
                if i == 1:
                    medal = "🥇 "
                elif i == 2:
                    medal = "🥈 "
                elif i == 3:
                    medal = "🥉 "
                
                leaderboard_text += (
                    f"{medal}**#{i}** {member.mention} - "
                    f"{activity['total_score']:.0f} pts\n"
                    f"   └ {activity['message_count']} msgs, {activity['voice_minutes']:.0f}m voice\n"
                )
            
            embed.add_field(
                name="🏆 Rankings",
                value=leaderboard_text,
                inline=False
            )
            
            embed.add_field(
                name="📝 Scoring",
                value="• Messages: 1 point each (max 1000)\n"
                      "• Voice: 1 point per 10 minutes (max 500)\n"
                      "• Activity tracked over last 30 days",
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"Error in activity_leaderboard command: {e}")
            embed = Utils.create_error_embed(f"Failed to generate leaderboard: {str(e)}")
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(BotSuggestions(bot))
