import discord
from discord import app_commands
from discord.ext import commands
from typing import List

from bot.utils.utils import Utils


class RoleAssignment(commands.Cog):
    """Role assignment functionality for self-assignable roles"""
    
    def __init__(self, bot):
        self.bot = bot

    def get_gooner_roles(self, guild: discord.Guild) -> List[discord.Role]:
        """Get all roles that contain 'Gooner' in their name"""
        return [role for role in guild.roles if "gooner" in role.name.lower() and not role.managed]

    @app_commands.command(name="roles", description="View and assign available Gooner roles")
    async def view_roles(self, interaction: discord.Interaction):
        """Display available Gooner roles for self-assignment"""
        gooner_roles = self.get_gooner_roles(interaction.guild)
        
        if not gooner_roles:
            await Utils.send_response(
                interaction,
                embed=Utils.create_info_embed(
                    "No Gooner roles are currently available for assignment.",
                    "No Roles Available"
                ),
                ephemeral=True
            )
            return

        # Create embed showing available roles
        embed = Utils.create_embed(
            title="🎭 Available Gooner Roles",
            description="Select the roles you'd like to join or leave:",
            color=discord.Color.purple()
        )

        # Group roles by whether user has them
        user_roles = [role.id for role in interaction.user.roles]
        has_roles = [role for role in gooner_roles if role.id in user_roles]
        available_roles = [role for role in gooner_roles if role.id not in user_roles]

        if has_roles:
            embed.add_field(
                name="✅ Your Current Roles",
                value="\n".join([f"• {role.mention}" for role in has_roles]),
                inline=False
            )

        if available_roles:
            embed.add_field(
                name="📝 Available to Join",
                value="\n".join([f"• {role.mention}" for role in available_roles]),
                inline=False
            )

        embed.add_field(
            name="💡 How to Use",
            value="Use `/join_role` to get a role or `/leave_role` to remove one",
            inline=False
        )

        await Utils.send_response(interaction, embed=embed, ephemeral=True)

    @app_commands.command(name="join_role", description="Join a Gooner role")
    @app_commands.describe(role="The Gooner role you want to join")
    async def join_role(self, interaction: discord.Interaction, role: discord.Role):
        """Allow users to join a Gooner role"""
        # Check if role is a valid Gooner role
        if "gooner" not in role.name.lower():
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed("You can only assign Gooner roles to yourself."),
                ephemeral=True
            )
            return

        # Check if role is manageable by bot
        if role.managed or role >= interaction.guild.me.top_role:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed("This role cannot be assigned by the bot."),
                ephemeral=True
            )
            return

        # Check if user already has the role
        if role in interaction.user.roles:
            await Utils.send_response(
                interaction,
                embed=Utils.create_info_embed(f"You already have the {role.mention} role."),
                ephemeral=True
            )
            return

        try:
            # Add the role to the user
            await interaction.user.add_roles(role, reason=f"Self-assigned Gooner role")
            
            embed = Utils.create_success_embed(
                f"Successfully joined {role.mention}!",
                "Role Added"
            )
            embed.add_field(
                name="🎉 Welcome!",
                value=f"You now have access to content associated with {role.mention}",
                inline=False
            )
            
            await Utils.send_response(interaction, embed=embed, ephemeral=True)
            
            # Log the action
            self.bot.logger.info(f"User {interaction.user} self-assigned role {role.name} in {interaction.guild.name}")

        except discord.Forbidden:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed("I don't have permission to assign this role."),
                ephemeral=True
            )
        except discord.HTTPException as e:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed(f"Failed to assign role: {str(e)}"),
                ephemeral=True
            )

    @app_commands.command(name="leave_role", description="Leave a Gooner role")
    @app_commands.describe(role="The Gooner role you want to leave")
    async def leave_role(self, interaction: discord.Interaction, role: discord.Role):
        """Allow users to leave a Gooner role"""
        # Check if role is a valid Gooner role
        if "gooner" not in role.name.lower():
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed("You can only remove Gooner roles from yourself."),
                ephemeral=True
            )
            return

        # Check if user has the role
        if role not in interaction.user.roles:
            await Utils.send_response(
                interaction,
                embed=Utils.create_info_embed(f"You don't have the {role.mention} role."),
                ephemeral=True
            )
            return

        try:
            # Remove the role from the user
            await interaction.user.remove_roles(role, reason=f"Self-removed Gooner role")
            
            embed = Utils.create_success_embed(
                f"Successfully left {role.mention}!",
                "Role Removed"
            )
            embed.add_field(
                name="👋 Goodbye!",
                value=f"You no longer have access to content associated with {role.mention}",
                inline=False
            )
            
            await Utils.send_response(interaction, embed=embed, ephemeral=True)
            
            # Log the action
            self.bot.logger.info(f"User {interaction.user} self-removed role {role.name} in {interaction.guild.name}")

        except discord.Forbidden:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed("I don't have permission to remove this role."),
                ephemeral=True
            )
        except discord.HTTPException as e:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed(f"Failed to remove role: {str(e)}"),
                ephemeral=True
            )

    @join_role.autocomplete('role')
    async def join_role_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Autocomplete for join_role command - shows available Gooner roles"""
        gooner_roles = self.get_gooner_roles(interaction.guild)
        user_role_ids = [role.id for role in interaction.user.roles]
        
        # Only show roles the user doesn't have
        available_roles = [role for role in gooner_roles if role.id not in user_role_ids]
        
        # Filter by current input
        if current:
            available_roles = [role for role in available_roles if current.lower() in role.name.lower()]
        
        # Return up to 25 choices (Discord limit)
        return [
            app_commands.Choice(name=role.name, value=str(role.id))
            for role in available_roles[:25]
        ]

    @leave_role.autocomplete('role')
    async def leave_role_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Autocomplete for leave_role command - shows user's current Gooner roles"""
        gooner_roles = self.get_gooner_roles(interaction.guild)
        user_role_ids = [role.id for role in interaction.user.roles]
        
        # Only show roles the user has
        user_gooner_roles = [role for role in gooner_roles if role.id in user_role_ids]
        
        # Filter by current input
        if current:
            user_gooner_roles = [role for role in user_gooner_roles if current.lower() in role.name.lower()]
        
        # Return up to 25 choices (Discord limit)
        return [
            app_commands.Choice(name=role.name, value=str(role.id))
            for role in user_gooner_roles[:25]
        ]

    @app_commands.command(name="toggle_role", description="Toggle a Gooner role (join if you don't have it, leave if you do)")
    @app_commands.describe(role="The Gooner role you want to toggle")
    async def toggle_role(self, interaction: discord.Interaction, role: discord.Role):
        """Toggle a Gooner role - join if not present, leave if present"""
        # Check if role is a valid Gooner role
        if "gooner" not in role.name.lower():
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed("You can only toggle Gooner roles."),
                ephemeral=True
            )
            return

        # Check if role is manageable by bot
        if role.managed or role >= interaction.guild.me.top_role:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed("This role cannot be managed by the bot."),
                ephemeral=True
            )
            return

        try:
            if role in interaction.user.roles:
                # Remove the role
                await interaction.user.remove_roles(role, reason=f"Self-toggled Gooner role")
                
                embed = Utils.create_success_embed(
                    f"Successfully left {role.mention}!",
                    "Role Removed"
                )
                embed.add_field(
                    name="👋 Goodbye!",
                    value=f"You no longer have access to content associated with {role.mention}",
                    inline=False
                )
                
                action = "removed"
            else:
                # Add the role
                await interaction.user.add_roles(role, reason=f"Self-toggled Gooner role")
                
                embed = Utils.create_success_embed(
                    f"Successfully joined {role.mention}!",
                    "Role Added"
                )
                embed.add_field(
                    name="🎉 Welcome!",
                    value=f"You now have access to content associated with {role.mention}",
                    inline=False
                )
                
                action = "added"
            
            await Utils.send_response(interaction, embed=embed, ephemeral=True)
            
            # Log the action
            self.bot.logger.info(f"User {interaction.user} self-{action} role {role.name} in {interaction.guild.name}")

        except discord.Forbidden:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed("I don't have permission to manage this role."),
                ephemeral=True
            )
        except discord.HTTPException as e:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed(f"Failed to toggle role: {str(e)}"),
                ephemeral=True
            )

    @toggle_role.autocomplete('role')
    async def toggle_role_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Autocomplete for toggle_role command - shows all Gooner roles"""
        gooner_roles = self.get_gooner_roles(interaction.guild)
        
        # Filter by current input
        if current:
            gooner_roles = [role for role in gooner_roles if current.lower() in role.name.lower()]
        
        # Return up to 25 choices (Discord limit)
        return [
            app_commands.Choice(name=role.name, value=str(role.id))
            for role in gooner_roles[:25]
        ]


async def setup(bot):
    await bot.add_cog(RoleAssignment(bot))
