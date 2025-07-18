import discord
from discord import app_commands
from discord.ext import commands

from bot.utils.utils import Utils


class Config(commands.Cog):
    """Configuration commands for the bot"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="config", description="Configure server settings")
    @app_commands.describe(
        setting="The setting to configure",
        value="The value to set"
    )
    @app_commands.choices(setting=[
        app_commands.Choice(name="Log Channel", value="log_channel"),
        app_commands.Choice(name="Max Warnings", value="max_warnings"),
        app_commands.Choice(name="Auto-Moderation", value="auto_mod"),
    ])
    async def config(
        self,
        interaction: discord.Interaction,
        setting: str,
        value: str = None
    ):
        """Configure server settings"""
        # Check permissions
        if not await Utils.check_permissions(interaction, ["manage_guild"]):
            return
        
        guild_config = await self.bot.database.get_guild_config(interaction.guild.id)
        
        if value is None:
            # Show current configuration
            embed = Utils.create_embed(
                title="⚙️ Server Configuration",
                description="Current server settings:",
                color=discord.Color.blue()
            )
            
            # Log channel
            log_channel = None
            if guild_config.get("log_channel_id"):
                log_channel = interaction.guild.get_channel(guild_config["log_channel_id"])
            
            embed.add_field(
                name="Log Channel",
                value=log_channel.mention if log_channel else "Not set",
                inline=True
            )
            
            # Max warnings
            embed.add_field(
                name="Max Warnings",
                value=str(guild_config.get("max_warnings", 3)),
                inline=True
            )
            
            # Auto-moderation
            embed.add_field(
                name="Auto-Moderation",
                value="Enabled" if guild_config.get("auto_mod_enabled") else "Disabled",
                inline=True
            )
            
            embed.add_field(
                name="Usage",
                value="Use `/config <setting> <value>` to change settings",
                inline=False
            )
            
            await Utils.send_response(interaction, embed=embed)
            return
        
        # Update configuration
        try:
            if setting == "log_channel":
                # Parse channel mention or ID
                channel_id = None
                if value.startswith("<#") and value.endswith(">"):
                    channel_id = int(value[2:-1])
                elif value.isdigit():
                    channel_id = int(value)
                else:
                    await Utils.send_response(
                        interaction,
                        embed=Utils.create_error_embed("Invalid channel format. Use #channel or channel ID."),
                        ephemeral=True
                    )
                    return
                
                # Verify channel exists
                channel = interaction.guild.get_channel(channel_id)
                if not channel:
                    await Utils.send_response(
                        interaction,
                        embed=Utils.create_error_embed("Channel not found."),
                        ephemeral=True
                    )
                    return
                
                # Check bot permissions in channel
                if not channel.permissions_for(interaction.guild.me).send_messages:
                    await Utils.send_response(
                        interaction,
                        embed=Utils.create_error_embed("I don't have permission to send messages in that channel."),
                        ephemeral=True
                    )
                    return
                
                await self.bot.database.update_guild_config(
                    interaction.guild.id,
                    log_channel_id=channel_id
                )
                
                embed = Utils.create_success_embed(
                    f"Log channel set to {channel.mention}",
                    "Configuration Updated"
                )
                
            elif setting == "max_warnings":
                try:
                    max_warnings = int(value)
                    if max_warnings < 1 or max_warnings > 20:
                        await Utils.send_response(
                            interaction,
                            embed=Utils.create_error_embed("Max warnings must be between 1 and 20."),
                            ephemeral=True
                        )
                        return
                    
                    await self.bot.database.update_guild_config(
                        interaction.guild.id,
                        max_warnings=max_warnings
                    )
                    
                    embed = Utils.create_success_embed(
                        f"Max warnings set to {max_warnings}",
                        "Configuration Updated"
                    )
                    
                except ValueError:
                    await Utils.send_response(
                        interaction,
                        embed=Utils.create_error_embed("Invalid number format."),
                        ephemeral=True
                    )
                    return
                
            elif setting == "auto_mod":
                if value.lower() in ["true", "on", "enable", "enabled", "1"]:
                    auto_mod_enabled = True
                elif value.lower() in ["false", "off", "disable", "disabled", "0"]:
                    auto_mod_enabled = False
                else:
                    await Utils.send_response(
                        interaction,
                        embed=Utils.create_error_embed("Invalid value. Use: true/false, on/off, enable/disable"),
                        ephemeral=True
                    )
                    return
                
                await self.bot.database.update_guild_config(
                    interaction.guild.id,
                    auto_mod_enabled=auto_mod_enabled
                )
                
                embed = Utils.create_success_embed(
                    f"Auto-moderation {'enabled' if auto_mod_enabled else 'disabled'}",
                    "Configuration Updated"
                )
            
            await Utils.send_response(interaction, embed=embed)
            
        except Exception as e:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed(f"Failed to update configuration: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="automod", description="Configure auto-moderation settings")
    @app_commands.describe(
        feature="The auto-moderation feature to configure",
        enabled="Whether to enable or disable the feature",
        threshold="Threshold value for caps filter (1-100) or spam filter (1-20)"
    )
    @app_commands.choices(feature=[
        app_commands.Choice(name="Spam Detection", value="spam_detection"),
        app_commands.Choice(name="Profanity Filter", value="profanity_filter"),
        app_commands.Choice(name="Link Filter", value="link_filter"),
        app_commands.Choice(name="Invite Filter", value="invite_filter"),
        app_commands.Choice(name="Caps Filter", value="caps_filter"),
        app_commands.Choice(name="Caps Threshold", value="caps_threshold"),
        app_commands.Choice(name="Spam Threshold", value="spam_threshold"),
    ])
    async def automod(
        self,
        interaction: discord.Interaction,
        feature: str = None,
        enabled: bool = None,
        threshold: int = None
    ):
        """Configure auto-moderation settings"""
        # Check permissions
        if not await Utils.check_permissions(interaction, ["manage_guild"]):
            return
        
        automod_settings = await self.bot.database.get_automod_settings(interaction.guild.id)
        
        if feature is None:
            # Show current auto-moderation settings
            embed = Utils.create_embed(
                title="🛡️ Auto-Moderation Settings",
                description="Current auto-moderation configuration:",
                color=discord.Color.blue()
            )
            
            settings = [
                ("Spam Detection", automod_settings.get("spam_detection", True)),
                ("Profanity Filter", automod_settings.get("profanity_filter", True)),
                ("Link Filter", automod_settings.get("link_filter", False)),
                ("Invite Filter", automod_settings.get("invite_filter", True)),
                ("Caps Filter", automod_settings.get("caps_filter", True)),
            ]
            
            for name, value in settings:
                embed.add_field(
                    name=name,
                    value="✅ Enabled" if value else "❌ Disabled",
                    inline=True
                )
            
            # Add thresholds
            embed.add_field(
                name="Caps Threshold",
                value=f"{automod_settings.get('caps_threshold', 70)}%",
                inline=True
            )
            
            embed.add_field(
                name="Spam Threshold",
                value=f"{automod_settings.get('spam_threshold', 5)} messages",
                inline=True
            )
            
            embed.add_field(
                name="Usage",
                value="Use `/automod <feature> <enabled>` to toggle features\nUse `/automod <threshold> threshold:<value>` to set thresholds",
                inline=False
            )
            
            await Utils.send_response(interaction, embed=embed)
            return
        
        # Handle threshold settings
        if feature in ["caps_threshold", "spam_threshold"]:
            if threshold is None:
                await Utils.send_response(
                    interaction,
                    embed=Utils.create_error_embed("Please provide a threshold value."),
                    ephemeral=True
                )
                return
            
            # Validate threshold values
            if feature == "caps_threshold":
                if not 1 <= threshold <= 100:
                    await Utils.send_response(
                        interaction,
                        embed=Utils.create_error_embed("Caps threshold must be between 1 and 100."),
                        ephemeral=True
                    )
                    return
                feature_name = "Caps Threshold"
                unit = "%"
            else:  # spam_threshold
                if not 1 <= threshold <= 20:
                    await Utils.send_response(
                        interaction,
                        embed=Utils.create_error_embed("Spam threshold must be between 1 and 20."),
                        ephemeral=True
                    )
                    return
                feature_name = "Spam Threshold"
                unit = " messages"
            
            # Update threshold
            try:
                update_data = {feature: threshold}
                await self.bot.database.update_automod_settings(
                    interaction.guild.id,
                    **update_data
                )
                
                embed = Utils.create_success_embed(
                    f"{feature_name} set to {threshold}{unit}",
                    "Auto-Moderation Updated"
                )
                
                await Utils.send_response(interaction, embed=embed)
                
            except Exception as e:
                await Utils.send_response(
                    interaction,
                    embed=Utils.create_error_embed(f"Failed to update threshold: {str(e)}"),
                    ephemeral=True
                )
            return
        
        # Handle feature toggles
        if enabled is None:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed("Please specify whether to enable or disable the feature."),
                ephemeral=True
            )
            return
        
        # Update auto-moderation setting
        try:
            update_data = {feature: enabled}
            
            await self.bot.database.update_automod_settings(
                interaction.guild.id,
                **update_data
            )
            
            feature_name = feature.replace("_", " ").title()
            embed = Utils.create_success_embed(
                f"{feature_name} {'enabled' if enabled else 'disabled'}",
                "Auto-Moderation Updated"
            )
            
            await Utils.send_response(interaction, embed=embed)
            
        except Exception as e:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed(f"Failed to update auto-moderation: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="settings", description="View all server settings")
    async def settings(self, interaction: discord.Interaction):
        """View all server settings"""
        # Check permissions
        if not await Utils.check_permissions(interaction, ["manage_guild"]):
            return
        
        try:
            guild_config = await self.bot.database.get_guild_config(interaction.guild.id)
            automod_settings = await self.bot.database.get_automod_settings(interaction.guild.id)
            
            embed = Utils.create_embed(
                title="📋 Complete Server Settings",
                description=f"All settings for {interaction.guild.name}",
                color=discord.Color.blue()
            )
            
            # Basic settings
            log_channel = None
            if guild_config.get("log_channel_id"):
                log_channel = interaction.guild.get_channel(guild_config["log_channel_id"])
            
            basic_settings = [
                f"**Log Channel:** {log_channel.mention if log_channel else 'Not set'}",
                f"**Max Warnings:** {guild_config.get('max_warnings', 3)}",
                f"**Auto-Moderation:** {'Enabled' if guild_config.get('auto_mod_enabled') else 'Disabled'}",
            ]
            
            embed.add_field(
                name="⚙️ Basic Settings",
                value="\n".join(basic_settings),
                inline=False
            )
            
            # Auto-moderation settings
            automod_list = [
                f"**Spam Detection:** {'✅' if automod_settings.get('spam_detection') else '❌'}",
                f"**Profanity Filter:** {'✅' if automod_settings.get('profanity_filter') else '❌'}",
                f"**Link Filter:** {'✅' if automod_settings.get('link_filter') else '❌'}",
                f"**Invite Filter:** {'✅' if automod_settings.get('invite_filter') else '❌'}",
                f"**Caps Filter:** {'✅' if automod_settings.get('caps_filter') else '❌'}",
                f"**Caps Threshold:** {automod_settings.get('caps_threshold', 70)}%",
                f"**Spam Threshold:** {automod_settings.get('spam_threshold', 5)} messages",
            ]
            
            embed.add_field(
                name="🛡️ Auto-Moderation",
                value="\n".join(automod_list),
                inline=False
            )
            
            embed.set_footer(text="Use /config or /automod to change these settings")
            
            await Utils.send_response(interaction, embed=embed)
            
        except Exception as e:
            await Utils.send_response(
                interaction,
                embed=Utils.create_error_embed(f"Failed to retrieve settings: {str(e)}"),
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(Config(bot))
