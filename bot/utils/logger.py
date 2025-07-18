import logging
import os
from pathlib import Path

import colorlog


def setup_logger():
    """Setup logging configuration"""
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Get log level from environment
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Create formatter
    formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
    )
    
    # Setup console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Setup file handler
    file_handler = logging.FileHandler(log_dir / "bot.log", encoding="utf-8")
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    
    # Setup error file handler
    error_handler = logging.FileHandler(log_dir / "error.log", encoding="utf-8")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level),
        handlers=[console_handler, file_handler, error_handler],
    )
    
    # Reduce discord.py logging verbosity
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.http").setLevel(logging.WARNING)


def get_logger(name):
    """Get a logger with the specified name"""
    return logging.getLogger(name)


def log_command(interaction, success=True):
    """Log command execution"""
    logger = get_logger("commands")
    
    user = f"{interaction.user} (ID: {interaction.user.id})"
    guild = f"{interaction.guild.name} (ID: {interaction.guild.id})" if interaction.guild else "DM"
    command = interaction.command.name if interaction.command else "Unknown"
    
    message = f"Command {'executed' if success else 'failed'} - User: {user}, Guild: {guild}, Command: {command}"
    
    if success:
        logger.info(message)
    else:
        logger.warning(message)


def log_moderation_action(action, moderator, target, reason, guild):
    """Log moderation actions"""
    logger = get_logger("moderation")
    
    message = (
        f"Moderation action - Action: {action}, "
        f"Moderator: {moderator} (ID: {moderator.id}), "
        f"Target: {target} (ID: {target.id}), "
        f"Reason: {reason or 'No reason provided'}, "
        f"Guild: {guild.name} (ID: {guild.id})"
    )
    
    logger.info(message)
