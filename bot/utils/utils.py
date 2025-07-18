import asyncio
import re
from datetime import datetime, timedelta
from typing import Optional, Union

import discord
from discord.ext import commands


class Utils:
    """Utility functions for the bot"""
    
    # Time formatting utilities
    @staticmethod
    def format_duration(seconds: int) -> str:
        """Format seconds into a human-readable duration"""
        if seconds < 60:
            return f"{seconds} second{'s' if seconds != 1 else ''}"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''}"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''}"
        else:
            days = seconds // 86400
            return f"{days} day{'s' if days != 1 else ''}"
    
    @staticmethod
    def parse_duration(duration_str: str) -> Optional[int]:
        """Parse a duration string into seconds"""
        if not duration_str:
            return None
        
        # Regular expressions for different time units
        time_regex = re.compile(r'(\d+)\s*([smhdw])', re.IGNORECASE)
        matches = time_regex.findall(duration_str.lower())
        
        if not matches:
            return None
        
        total_seconds = 0
        multipliers = {
            's': 1,
            'm': 60,
            'h': 3600,
            'd': 86400,
            'w': 604800
        }
        
        for amount, unit in matches:
            total_seconds += int(amount) * multipliers.get(unit, 0)
        
        return total_seconds if total_seconds > 0 else None
    
    @staticmethod
    def format_timestamp(dt: datetime, style: str = "F") -> str:
        """Format a datetime object as a Discord timestamp"""
        return f"<t:{int(dt.timestamp())}:{style}>"
    
    # Embed creation utilities
    @staticmethod
    def create_embed(
        title: str = None,
        description: str = None,
        color: Union[discord.Color, int] = None,
        timestamp: bool = True,
        **kwargs
    ) -> discord.Embed:
        """Create a standardized embed"""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color or discord.Color.blue(),
            timestamp=datetime.utcnow() if timestamp else None
        )
        
        if "author" in kwargs:
            embed.set_author(**kwargs["author"])
        if "footer" in kwargs:
            embed.set_footer(**kwargs["footer"])
        if "thumbnail" in kwargs:
            embed.set_thumbnail(url=kwargs["thumbnail"])
        if "image" in kwargs:
            embed.set_image(url=kwargs["image"])
        if "fields" in kwargs:
            for field in kwargs["fields"]:
                embed.add_field(**field)
        
        return embed
    
    @staticmethod
    def create_success_embed(description: str, title: str = "Success") -> discord.Embed:
        """Create a success embed"""
        return Utils.create_embed(
            title=f"✅ {title}",
            description=description,
            color=discord.Color.green()
        )
    
    @staticmethod
    def create_error_embed(description: str, title: str = "Error") -> discord.Embed:
        """Create an error embed"""
        return Utils.create_embed(
            title=f"❌ {title}",
            description=description,
            color=discord.Color.red()
        )
    
    @staticmethod
    def create_warning_embed(description: str, title: str = "Warning") -> discord.Embed:
        """Create a warning embed"""
        return Utils.create_embed(
            title=f"⚠️ {title}",
            description=description,
            color=discord.Color.yellow()
        )
    
    @staticmethod
    def create_info_embed(description: str, title: str = "Information") -> discord.Embed:
        """Create an info embed"""
        return Utils.create_embed(
            title=f"ℹ️ {title}",
            description=description,
            color=discord.Color.blue()
        )
    
    @staticmethod
    def create_moderation_embed(
        action: str,
        user: discord.Member,
        moderator: discord.Member,
        reason: str = None,
        duration: int = None
    ) -> discord.Embed:
        """Create a moderation action embed"""
        embed = Utils.create_embed(
            title=f"🔨 {action.capitalize()}",
            color=discord.Color.orange(),
            fields=[
                {"name": "User", "value": f"{user.mention} ({user.id})", "inline": True},
                {"name": "Moderator", "value": f"{moderator.mention} ({moderator.id})", "inline": True},
                {"name": "Reason", "value": reason or "No reason provided", "inline": False},
            ],
            thumbnail=user.display_avatar.url
        )
        
        if duration:
            embed.add_field(
                name="Duration",
                value=Utils.format_duration(duration),
                inline=True
            )
        
        return embed
    
    # Permission checking utilities
    @staticmethod
    async def check_permissions(
        interaction: discord.Interaction,
        permissions: list[discord.Permissions]
    ) -> bool:
        """Check if user has required permissions"""
        if not interaction.user.guild_permissions.administrator:
            missing_perms = []
            for perm in permissions:
                if not getattr(interaction.user.guild_permissions, perm):
                    missing_perms.append(perm.replace("_", " ").title())
            
            if missing_perms:
                embed = Utils.create_error_embed(
                    f"You are missing the following permissions: {', '.join(missing_perms)}",
                    "Missing Permissions"
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return False
        
        return True
    
    @staticmethod
    async def check_bot_permissions(
        interaction: discord.Interaction,
        permissions: list[str]
    ) -> bool:
        """Check if bot has required permissions"""
        missing_perms = []
        for perm in permissions:
            if not getattr(interaction.guild.me.guild_permissions, perm):
                missing_perms.append(perm.replace("_", " ").title())
        
        if missing_perms:
            embed = Utils.create_error_embed(
                f"I am missing the following permissions: {', '.join(missing_perms)}",
                "Missing Bot Permissions"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        
        return True
    
    # Hierarchy checking utilities
    @staticmethod
    def check_hierarchy(moderator: discord.Member, target: discord.Member) -> tuple[bool, str]:
        """Check if moderator can perform action on target"""
        if moderator.id == target.id:
            return False, "You cannot perform this action on yourself."
        
        if target.id == moderator.guild.owner_id:
            return False, "You cannot perform this action on the server owner."
        
        if (moderator.top_role.position <= target.top_role.position 
            and moderator.id != moderator.guild.owner_id):
            return False, "You cannot perform this action on a user with equal or higher role hierarchy."
        
        return True, ""
    
    @staticmethod
    def check_bot_hierarchy(bot_member: discord.Member, target: discord.Member) -> tuple[bool, str]:
        """Check if bot can perform action on target"""
        if target.id == target.guild.owner_id:
            return False, "I cannot perform this action on the server owner."
        
        if bot_member.top_role.position <= target.top_role.position:
            return False, "I cannot perform this action on a user with equal or higher role hierarchy."
        
        return True, ""
    
    # Text processing utilities
    @staticmethod
    def escape_markdown(text: str) -> str:
        """Escape markdown characters in text"""
        return discord.utils.escape_markdown(text)
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 2000) -> str:
        """Truncate text to fit within Discord limits"""
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."
    
    @staticmethod
    def format_list(items: list, max_items: int = 10) -> str:
        """Format a list for display"""
        if len(items) <= max_items:
            return "\n".join(f"• {item}" for item in items)
        else:
            displayed = items[:max_items]
            remaining = len(items) - max_items
            result = "\n".join(f"• {item}" for item in displayed)
            result += f"\n... and {remaining} more"
            return result
    
    # Validation utilities
    @staticmethod
    def is_valid_snowflake(snowflake: str) -> bool:
        """Check if a string is a valid Discord snowflake"""
        try:
            int(snowflake)
            return len(snowflake) >= 17 and len(snowflake) <= 19
        except ValueError:
            return False
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Check if a string is a valid URL"""
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE
        )
        return url_pattern.match(url) is not None
    
    # Pagination utilities
    @staticmethod
    def paginate(items: list, page: int, per_page: int = 10) -> dict:
        """Paginate a list of items"""
        total_pages = (len(items) + per_page - 1) // per_page
        page = max(1, min(page, total_pages))
        
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        
        return {
            "items": items[start_idx:end_idx],
            "current_page": page,
            "total_pages": total_pages,
            "total_items": len(items),
            "has_previous": page > 1,
            "has_next": page < total_pages,
            "start_index": start_idx + 1,
            "end_index": min(end_idx, len(items))
        }
    
    # Context utilities
    @staticmethod
    async def send_response(
        interaction: discord.Interaction,
        content: str = None,
        embed: discord.Embed = None,
        ephemeral: bool = False
    ):
        """Send a response to an interaction"""
        try:
            if interaction.response.is_done():
                await interaction.followup.send(content=content, embed=embed, ephemeral=ephemeral)
            else:
                await interaction.response.send_message(content=content, embed=embed, ephemeral=ephemeral)
        except discord.HTTPException:
            # If the interaction has expired, try to send a regular message
            if interaction.channel:
                await interaction.channel.send(content=content, embed=embed)
