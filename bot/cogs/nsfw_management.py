import discord
from discord import app_commands
from discord.ext import commands
from datetime import timedelta
import json
import os

from bot.utils.utils import Utils

NSFW_RESPONSIBLES_PATH = os.path.join(os.path.dirname(__file__), '..', 'nsfw_responsibles.json')

def set_responsible(category_id: int, user_id: int):
    try:
        with open(NSFW_RESPONSIBLES_PATH, 'r') as f:
            data = json.load(f)
    except Exception:
        data = {}
    data[str(category_id)] = user_id
    with open(NSFW_RESPONSIBLES_PATH, 'w') as f:
        json.dump(data, f)

def get_responsible(category_id: int):
    try:
        with open(NSFW_RESPONSIBLES_PATH, 'r') as f:
            data = json.load(f)
        return data.get(str(category_id))
    except Exception:
        return None

class NSFWManagement(commands.Cog):
    """NSFW content management functionality"""
    
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup_nsfw", description="Set up NSFW category with channels, role, and responsible user")
    @app_commands.describe(
        name="The name prefix for the NSFW category and role (e.g., 'Anime' -> 'Anime NSFW' category and 'Anime Gooner' role)",
        responsible="The user responsible for this NSFW category"
    )
    async def setup_nsfw(
        self,
        interaction: discord.Interaction,
        name: str,
        responsible: discord.Member = None
    ):
        """Set up NSFW category with channels, role, and responsible user"""
        # Check permissions
        if not await Utils.check_permissions(interaction, ["manage_channels", "manage_roles"]):
            return
        
        if not await Utils.check_bot_permissions(interaction, ["manage_channels", "manage_roles"]):
            return

        # Validate name length
        if len(name) > 50:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed("Name must be 50 characters or less"),
                ephemeral=True
            )
            return

        try:
            # Create role first
            role_name = f"{name} Gooner"
            role = await interaction.guild.create_role(
                name=role_name,
                mentionable=False,
                reason=f"NSFW setup by {interaction.user}"
            )

            # Create category
            category_name = f"{name} NSFW"
              # Set up permissions for the category
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(
                    view_channel=False,
                    send_messages=False
                ),
                role: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_messages=True,
                    read_message_history=True,
                    attach_files=True,
                    embed_links=True,
                    add_reactions=True,
                    use_external_emojis=True
                ),
                interaction.guild.me: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    manage_messages=True,
                    read_messages=True,
                    read_message_history=True
                )
            }

            # Add Moderator role permissions if it exists
            moderator_role = discord.utils.get(interaction.guild.roles, name="Moderator")
            if moderator_role:
                overwrites[moderator_role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_messages=True,
                    read_message_history=True,
                    manage_messages=True,
                    attach_files=True,
                    embed_links=True,
                    add_reactions=True,
                    use_external_emojis=True,
                    manage_threads=True
                )

            category = await interaction.guild.create_category(
                name=category_name,
                overwrites=overwrites,
                reason=f"NSFW setup by {interaction.user}"
            )

            # Save responsible user info (store in JSON file, not topic)
            if responsible:
                set_responsible(category.id, responsible.id)

            # Define channels to create
            channels_to_create = [
                {"name": "dm-requests", "topic": "Request DMs and private content"},
                {"name": "pics", "topic": "Share and discuss pictures"},
                {"name": "vids", "topic": "Share and discuss videos"},
                {"name": "nsfw-chat", "topic": "General NSFW discussion"},
                {"name": "ai-content", "topic": "AI-generated NSFW content"},
                {"name": "tributes", "topic": "Tribute content and requests"}
            ]

            created_channels = []
            
            for channel_info in channels_to_create:
                channel = await interaction.guild.create_text_channel(
                    name=channel_info["name"],
                    category=category,
                    topic=channel_info["topic"],
                    nsfw=False,
                    reason=f"NSFW setup by {interaction.user}"
                )
                created_channels.append(channel)

            # Create success embed
            embed = Utils.create_success_embed(
                f"Successfully set up NSFW content area!",
                "NSFW Setup Complete"
            )
            
            embed.add_field(
                name="🏷️ Role Created",
                value=f"{role.mention} (ID: {role.id})",
                inline=False
            )
            
            embed.add_field(
                name="📁 Category Created",
                value=f"{category.name} (ID: {category.id})",
                inline=False
            )
            
            channel_list = "\n".join([f"• {channel.mention}" for channel in created_channels])
            embed.add_field(
                name="📺 Channels Created",
                value=channel_list,
                inline=False            )
            
            embed.add_field(
                name="🔒 Access Control",
                value=f"Only members with the {role.mention} role can access these channels." + 
                      (f"\nModerators can also view and moderate these channels." if moderator_role else 
                       f"\n⚠️ No 'Moderator' role found - only {role.mention} members have access."),
                inline=False
            )
            
            if responsible:
                embed.add_field(
                    name="👤 Responsible User",
                    value=f"{responsible.mention}",
                    inline=False
                )
            
            embed.add_field(
                name="ℹ️ Next Steps",
                value="• Assign the role to trusted members\n• Configure additional channel settings if needed\n• Set up channel-specific rules",
                inline=False
            )

            await Utils.send_response(interaction, embed=embed)            # Log the action
            moderator_access = "with Moderator role access" if moderator_role else "without Moderator role (not found)"
            self.bot.logger.info(f"NSFW setup completed by {interaction.user} in {interaction.guild.name}: Role '{role_name}', Category '{category_name}', {len(created_channels)} channels, {moderator_access}")

        except discord.Forbidden:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed("I don't have permission to create roles or channels in this server."),
                ephemeral=True
            )
        except discord.HTTPException as e:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed(f"Failed to set up NSFW area: {str(e)}"),
                ephemeral=True
            )
        except Exception as e:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed(f"An unexpected error occurred: {str(e)}"),
                ephemeral=True
            )

    @app_commands.command(name="cleanup_nsfw", description="Remove NSFW category, channels, and role")
    @app_commands.describe(
        name="The name prefix used when creating the NSFW setup (same as used in setup_nsfw)"
    )
    async def cleanup_nsfw(
        self,
        interaction: discord.Interaction,
        name: str
    ):
        """Remove NSFW category, channels, and role"""
        # Check permissions
        if not await Utils.check_permissions(interaction, ["manage_channels", "manage_roles"]):
            return
        
        if not await Utils.check_bot_permissions(interaction, ["manage_channels", "manage_roles"]):
            return

        try:
            role_name = f"{name} Gooner"
            category_name = f"{name} NSFW"
            
            # Find the role
            role = discord.utils.get(interaction.guild.roles, name=role_name)
            
            # Find the category
            category = discord.utils.get(interaction.guild.categories, name=category_name)
            
            if not role and not category:
                await Utils.send_response(
                    interaction,
                    embed=Utils.create_error_embed(f"No NSFW setup found with name '{name}'"),
                    ephemeral=True
                )
                return

            deleted_items = []
            
            # Delete channels in category
            if category:
                channels_deleted = 0
                for channel in category.channels:
                    await channel.delete(reason=f"NSFW cleanup by {interaction.user}")
                    channels_deleted += 1
                
                # Delete category
                await category.delete(reason=f"NSFW cleanup by {interaction.user}")
                deleted_items.append(f"Category '{category_name}' and {channels_deleted} channels")

            # Delete role
            if role:
                await role.delete(reason=f"NSFW cleanup by {interaction.user}")
                deleted_items.append(f"Role '{role_name}'")

            # Create success embed
            embed = Utils.create_success_embed(
                f"Successfully cleaned up NSFW setup for '{name}'",
                "NSFW Cleanup Complete"
            )
            
            embed.add_field(
                name="🗑️ Deleted Items",
                value="\n".join([f"• {item}" for item in deleted_items]),
                inline=False
            )

            await Utils.send_response(interaction, embed=embed)

            # Log the action
            self.bot.logger.info(f"NSFW cleanup completed by {interaction.user} in {interaction.guild.name}: {', '.join(deleted_items)}")

        except discord.Forbidden:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed("I don't have permission to delete roles or channels in this server."),
                ephemeral=True
            )
        except discord.HTTPException as e:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed(f"Failed to cleanup NSFW area: {str(e)}"),
                ephemeral=True
            )
        except Exception as e:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed(f"An unexpected error occurred: {str(e)}"),
                ephemeral=True
            )

    @app_commands.command(name="clear_commands", description="Clear all slash commands (Admin only)")
    async def clear_commands(self, interaction: discord.Interaction):
        """Clear all slash commands to fix duplicates"""
        # Check permissions - only administrators
        if not interaction.user.guild_permissions.administrator:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed("Only administrators can use this command."),
                ephemeral=True
            )
            return

        try:
            # Clear guild commands
            interaction.client.tree.clear_commands(guild=interaction.guild)
            await interaction.client.tree.sync(guild=interaction.guild)
            
            embed = Utils.create_success_embed(
                "All slash commands have been cleared from this server. The bot will need to be restarted to re-register commands.",
                "Commands Cleared"
            )
            await Utils.send_response(interaction, embed=embed, ephemeral=True)
            
            self.bot.logger.info(f"Commands cleared by {interaction.user} in {interaction.guild.name}")
            
        except Exception as e:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed(f"Failed to clear commands: {str(e)}"),
                ephemeral=True
            )

    @app_commands.command(name="prune_nsfw_inactive", description="List or close inactive NSFW categories and associated roles")
    @app_commands.describe(
        days="Number of days of inactivity before a category is considered for closure (default: 30)",
        name="The name prefix for the NSFW category (optional, leave blank to check all NSFW categories)",
        dry_run="If true, only list inactive categories and roles without deleting them (default: False)"
    )
    async def prune_nsfw_inactive(
        self,
        interaction: discord.Interaction,
        days: int = 30,
        name: str = None,
        dry_run: bool = False
    ):
        """List or close inactive NSFW categories and associated roles"""
        # Check permissions
        if not await Utils.check_permissions(interaction, ["manage_channels", "manage_roles"]):
            return
        if not await Utils.check_bot_permissions(interaction, ["manage_channels", "manage_roles"]):
            return

        threshold = discord.utils.utcnow() - timedelta(days=days)
        checked_categories = 0
        categories_to_delete = []
        roles_to_delete = []

        # Find NSFW categories (optionally filter by name)
        nsfw_categories = [cat for cat in interaction.guild.categories if (name is None or cat.name == f"{name} NSFW")]
        if not nsfw_categories:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed(f"No NSFW categories found{' with name ' + name if name else ''}.") ,
                ephemeral=True
            )
            return

        for category in nsfw_categories:
            checked_categories += 1
            all_inactive = True
            for channel in category.text_channels:
                try:
                    last_message = None
                    async for msg in channel.history(limit=1, oldest_first=False):
                        last_message = msg
                        break
                    if last_message and last_message.created_at >= threshold:
                        all_inactive = False
                        break
                except discord.Forbidden:
                    continue  # Skip channels we can't access
                except Exception:
                    continue
            if all_inactive and category.text_channels:
                categories_to_delete.append(category)
                # Try to find the associated role
                prefix = category.name[:-5] if category.name.endswith(" NSFW") else category.name
                role_name = f"{prefix} Gooner"
                role = discord.utils.get(interaction.guild.roles, name=role_name)
                if role:
                    roles_to_delete.append(role)

        # Dry run: only list
        if dry_run:
            embed = Utils.create_success_embed(
                f"Inactive NSFW categories and roles that would be deleted (dry run)",
                "NSFW Prune Preview"
            )
            if categories_to_delete:
                embed.add_field(
                    name="Categories to Delete",
                    value="\n".join([f"• {cat.name}" for cat in categories_to_delete]),
                    inline=False
                )
            else:
                embed.add_field(
                    name="No Inactive Categories",
                    value=f"Checked {checked_categories} category(ies).",
                    inline=False
                )
            if roles_to_delete:
                embed.add_field(
                    name="Roles to Delete (if category is deleted)",
                    value="\n".join([f"• {role.name}" for role in roles_to_delete]),
                    inline=False
                )
            await Utils.send_response(interaction, embed=embed, ephemeral=True)
            return

        # Actually delete inactive categories and roles
        deleted_categories = []
        deleted_roles = []
        for category in categories_to_delete:
            # Get responsible user from JSON file
            responsible_id = get_responsible(category.id)
            try:
                for channel in category.text_channels:
                    await channel.delete(reason=f"Pruned due to inactivity (>{days} days) by {interaction.user}")
                await category.delete(reason=f"Pruned due to inactivity (>{days} days) by {interaction.user}")
                deleted_categories.append(category.name)
                # DM responsible user if found
                if responsible_id:
                    user = interaction.guild.get_member(responsible_id)
                    if user:
                        try:
                            await user.send(f"Your NSFW category '{category.name}' was purged due to inactivity.")
                        except Exception:
                            pass
            except Exception:
                continue
        for role in roles_to_delete:
            try:
                await role.delete(reason=f"Pruned due to inactivity (>{days} days) by {interaction.user}")
                deleted_roles.append(role.name)
            except Exception:
                continue

        # Report results
        if deleted_categories or deleted_roles:
            embed = Utils.create_success_embed(
                f"Closed {len(deleted_categories)} inactive NSFW category(ies) and {len(deleted_roles)} role(s).",
                "NSFW Prune Complete"
            )
            if deleted_categories:
                embed.add_field(
                    name="🗑️ Categories Closed",
                    value="\n".join([f"• {cat}" for cat in deleted_categories]),
                    inline=False
                )
            if deleted_roles:
                embed.add_field(
                    name="Roles Deleted",
                    value="\n".join([f"• {role}" for role in deleted_roles]),
                    inline=False
                )
        else:
            embed = Utils.create_success_embed(
                f"No inactive NSFW categories or roles found (checked {checked_categories} category(ies)).",
                "NSFW Prune Complete"
            )
        await Utils.send_response(interaction, embed=embed, ephemeral=True)
        self.bot.logger.info(f"NSFW prune by {interaction.user} in {interaction.guild.name}: {len(deleted_categories)} categories and {len(deleted_roles)} roles closed.")


async def setup(bot):
    await bot.add_cog(NSFWManagement(bot))