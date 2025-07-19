import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime

from bot.utils.utils import Utils


class Utility(commands.Cog):
    """Utility commands for the bot"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="ping", description="Check the bot's latency")
    async def ping(self, interaction: discord.Interaction):
        """Check the bot's latency"""
        embed = Utils.create_info_embed(
            f"🏓 Pong! Latency: {round(self.bot.latency * 1000)}ms",
            "Bot Latency"
        )
        await Utils.send_response(interaction, embed=embed)
    
    @app_commands.command(name="userinfo", description="Get information about a user")
    @app_commands.describe(user="The user to get information about")
    async def userinfo(self, interaction: discord.Interaction, user: discord.Member = None):
        """Get information about a user"""
        if user is None:
            user = interaction.user
        
        # Get user data
        created_at = Utils.format_timestamp(user.created_at)
        joined_at = Utils.format_timestamp(user.joined_at) if user.joined_at else "Unknown"
        
        # Get roles (excluding @everyone)
        roles = [role.mention for role in user.roles[1:]]
        roles_text = ", ".join(roles) if roles else "None"
        
        # Get permissions
        key_permissions = []
        if user.guild_permissions.administrator:
            key_permissions.append("Administrator")
        else:
            perms = [
                ("Manage Server", user.guild_permissions.manage_guild),
                ("Manage Channels", user.guild_permissions.manage_channels),
                ("Manage Messages", user.guild_permissions.manage_messages),
                ("Kick Members", user.guild_permissions.kick_members),
                ("Ban Members", user.guild_permissions.ban_members),
                ("Moderate Members", user.guild_permissions.moderate_members),
            ]
            key_permissions = [name for name, has_perm in perms if has_perm]
        
        permissions_text = ", ".join(key_permissions) if key_permissions else "None"
        
        # Create embed
        embed = Utils.create_embed(
            title=f"User Info - {user.display_name}",
            color=user.color if user.color != discord.Color.default() else discord.Color.blue(),
            thumbnail=user.display_avatar.url,
            fields=[
                {"name": "Username", "value": str(user), "inline": True},
                {"name": "User ID", "value": str(user.id), "inline": True},
                {"name": "Nickname", "value": user.display_name, "inline": True},
                {"name": "Account Created", "value": created_at, "inline": True},
                {"name": "Joined Server", "value": joined_at, "inline": True},
                {"name": "Status", "value": str(user.status).title(), "inline": True},
                {"name": f"Roles ({len(roles)})", "value": Utils.truncate_text(roles_text, 1024), "inline": False},
                {"name": "Key Permissions", "value": permissions_text, "inline": False},
            ]
        )
        
        # Add bot badge if user is a bot
        if user.bot:
            embed.add_field(name="Bot", value="✅ Yes", inline=True)
        
        # Add timeout info if user is timed out
        if hasattr(user, 'is_timed_out') and user.is_timed_out():
            embed.add_field(
                name="Timed Out Until",
                value=Utils.format_timestamp(user.timed_out_until),
                inline=True
            )
        
        await Utils.send_response(interaction, embed=embed)
    
    @app_commands.command(name="serverinfo", description="Get information about the server")
    async def serverinfo(self, interaction: discord.Interaction):
        """Get information about the server"""
        guild = interaction.guild
        
        # Get server data
        created_at = Utils.format_timestamp(guild.created_at)
        owner = guild.owner
        
        # Get member counts
        total_members = guild.member_count
        online_members = sum(1 for member in guild.members if member.status != discord.Status.offline)
        bots = sum(1 for member in guild.members if member.bot)
        humans = total_members - bots
        
        # Get channel counts
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        
        # Get other counts
        roles = len(guild.roles)
        emojis = len(guild.emojis)
        
        # Get boost info
        boost_level = guild.premium_tier
        boost_count = guild.premium_subscription_count
        
        # Create embed
        embed = Utils.create_embed(
            title=f"Server Info - {guild.name}",
            color=discord.Color.blue(),
            thumbnail=guild.icon.url if guild.icon else None,
            fields=[
                {"name": "Server ID", "value": str(guild.id), "inline": True},
                {"name": "Owner", "value": owner.mention if owner else "Unknown", "inline": True},
                {"name": "Created", "value": created_at, "inline": True},
                {"name": "Members", "value": f"{total_members} total\n{online_members} online\n{humans} humans\n{bots} bots", "inline": True},
                {"name": "Channels", "value": f"{text_channels} text\n{voice_channels} voice\n{categories} categories", "inline": True},
                {"name": "Other", "value": f"{roles} roles\n{emojis} emojis", "inline": True},
                {"name": "Boost Status", "value": f"Level {boost_level}\n{boost_count} boosts", "inline": True},
                {"name": "Verification Level", "value": str(guild.verification_level).title(), "inline": True},
            ]
        )
        
        # Add features
        if guild.features:
            features = [feature.replace("_", " ").title() for feature in guild.features]
            embed.add_field(
                name="Features",
                value=Utils.truncate_text(", ".join(features), 1024),
                inline=False
            )
        
        # Add description if available
        if guild.description:
            embed.add_field(
                name="Description",
                value=guild.description,
                inline=False
            )
        
        await Utils.send_response(interaction, embed=embed)
    
    @app_commands.command(name="avatar", description="Get a user's avatar")
    @app_commands.describe(user="The user to get the avatar of")
    async def avatar(self, interaction: discord.Interaction, user: discord.Member = None):
        """Get a user's avatar"""
        if user is None:
            user = interaction.user
        
        embed = Utils.create_embed(
            title=f"{user.display_name}'s Avatar",
            color=user.color if user.color != discord.Color.default() else discord.Color.blue(),
            image=user.display_avatar.url
        )
        
        # Add download link
        embed.add_field(
            name="Download",
            value=f"[Click here]({user.display_avatar.url})",
            inline=False
        )
        
        await Utils.send_response(interaction, embed=embed)
    
    @app_commands.command(name="roleinfo", description="Get information about a role")
    @app_commands.describe(role="The role to get information about")
    async def roleinfo(self, interaction: discord.Interaction, role: discord.Role):
        """Get information about a role"""
        # Get role data
        created_at = Utils.format_timestamp(role.created_at)
        members_with_role = len(role.members)
        
        # Get permissions
        key_permissions = []
        if role.permissions.administrator:
            key_permissions.append("Administrator")
        else:
            perms = [
                ("Manage Server", role.permissions.manage_guild),
                ("Manage Channels", role.permissions.manage_channels),
                ("Manage Messages", role.permissions.manage_messages),
                ("Kick Members", role.permissions.kick_members),
                ("Ban Members", role.permissions.ban_members),
                ("Moderate Members", role.permissions.moderate_members),
                ("Mention Everyone", role.permissions.mention_everyone),
            ]
            key_permissions = [name for name, has_perm in perms if has_perm]
        
        permissions_text = ", ".join(key_permissions) if key_permissions else "None"
        
        # Create embed
        embed = Utils.create_embed(
            title=f"Role Info - {role.name}",
            color=role.color if role.color != discord.Color.default() else discord.Color.blue(),
            fields=[
                {"name": "Role ID", "value": str(role.id), "inline": True},
                {"name": "Position", "value": str(role.position), "inline": True},
                {"name": "Color", "value": str(role.color), "inline": True},
                {"name": "Created", "value": created_at, "inline": True},
                {"name": "Members", "value": str(members_with_role), "inline": True},
                {"name": "Mentionable", "value": "✅ Yes" if role.mentionable else "❌ No", "inline": True},
                {"name": "Hoisted", "value": "✅ Yes" if role.hoist else "❌ No", "inline": True},
                {"name": "Managed", "value": "✅ Yes" if role.managed else "❌ No", "inline": True},
                {"name": "Key Permissions", "value": permissions_text, "inline": False},
            ]
        )
        
        await Utils.send_response(interaction, embed=embed)
    
    @app_commands.command(name="channelinfo", description="Get information about a channel")
    @app_commands.describe(channel="The channel to get information about")
    async def channelinfo(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        """Get information about a channel"""
        if channel is None:
            channel = interaction.channel
        
        # Get channel data
        created_at = Utils.format_timestamp(channel.created_at)
        category = channel.category.name if channel.category else "None"
        
        # Create embed
        embed = Utils.create_embed(
            title=f"Channel Info - {channel.name}",
            color=discord.Color.blue(),
            fields=[
                {"name": "Channel ID", "value": str(channel.id), "inline": True},
                {"name": "Type", "value": str(channel.type).title(), "inline": True},
                {"name": "Position", "value": str(channel.position), "inline": True},
                {"name": "Created", "value": created_at, "inline": True},
                {"name": "Category", "value": category, "inline": True},
                {"name": "NSFW", "value": "✅ Yes" if channel.nsfw else "❌ No", "inline": True},
            ]
        )
        
        # Add topic if available
        if channel.topic:
            embed.add_field(
                name="Topic",
                value=Utils.truncate_text(channel.topic, 1024),
                inline=False
            )
        
        # Add slowmode info
        if channel.slowmode_delay > 0:
            embed.add_field(
                name="Slowmode",
                value=f"{channel.slowmode_delay} seconds",
                inline=True
            )
        
        await Utils.send_response(interaction, embed=embed)
    
    @app_commands.command(name="help", description="Show help information")
    async def help(self, interaction: discord.Interaction):
        """Show help information"""
        embed = Utils.create_embed(
            title="🤖 Project Bonk - Help",
            description="Here are all the available commands:",
            color=discord.Color.blue()
        )
        
        # Moderation commands
        moderation_commands = [
            "`/ban` - Ban a user from the server",
            "`/kick` - Kick a user from the server",
            "`/timeout` - Timeout a user",
            "`/untimeout` - Remove timeout from a user",
            "`/warn` - Warn a user",
            "`/warnings` - View warnings for a user",
            "`/removewarning` - Remove a specific warning by ID",
            "`/clearwarnings` - Clear all warnings for a user",
            "`/purge` - Delete multiple messages",
            "`/case` - Look up a specific moderation case",
            "`/history` - View moderation history for a user",
            "`/recent` - View recent moderation actions",
        ]
        
        embed.add_field(
            name="🔨 Moderation",
            value="\n".join(moderation_commands),
            inline=False
        )
        
        # Utility commands
        utility_commands = [
            "`/ping` - Check bot latency",
            "`/userinfo` - Get user information",
            "`/serverinfo` - Get server information",
            "`/avatar` - Get a user's avatar",
            "`/roleinfo` - Get role information",
            "`/channelinfo` - Get channel information",
            "`/help` - Show this help message",
        ]
        
        embed.add_field(
            name="🛠️ Utility",
            value="\n".join(utility_commands),
            inline=False
        )
        
        # Configuration commands
        config_commands = [
            "`/config` - Configure server settings",
            "`/automod` - Configure auto-moderation",
            "`/lockdown` - Manage lockdown mode",
            "`/lockdownconfig` - Configure lockdown settings",
        ]
        
        embed.add_field(
            name="⚙️ Configuration",
            value="\n".join(config_commands),
            inline=False
        )
        
        embed.add_field(
            name="📋 Notes",
            value="• Most commands require appropriate permissions\n"
                  "• Use `/command --help` for detailed command information\n"
                  "• Bot respects role hierarchy for moderation actions",
            inline=False
        )
        
        embed.set_footer(text="Project Bonk | Moderation Bot")
        
        await Utils.send_response(interaction, embed=embed)


async def setup(bot):
    await bot.add_cog(Utility(bot))
