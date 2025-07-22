import discord
from discord import app_commands
from discord.ext import commands

from bot.utils.utils import Utils


class NSFWManagement(commands.Cog):
    """NSFW content management functionality"""
    
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup_nsfw", description="Set up NSFW category with channels and role")
    @app_commands.describe(
        name="The name prefix for the NSFW category and role (e.g., 'Anime' -> 'Anime NSFW' category and 'Anime Gooner' role)"
    )
    async def setup_nsfw(
        self,
        interaction: discord.Interaction,
        name: str
    ):
        """Set up NSFW category with channels and role"""
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
                color=discord.Color.purple(),
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
                    nsfw=True,
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


async def setup(bot):
    await bot.add_cog(NSFWManagement(bot))