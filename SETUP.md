# Project Bonk - Discord Moderation Bot Setup Guide

## Overview
Project Bonk is a comprehensive Discord moderation bot built with Python and discord.py. It features advanced moderation tools, auto-moderation, logging, and configuration management.

## Features
- 🔨 **Moderation Commands**: ban, kick, timeout, warn, purge
- 🛡️ **Auto-Moderation**: spam, profanity, caps, links, invites
- 📊 **Comprehensive Logging**: member events, message events, voice events
- 📋 **Case Management**: track all moderation actions
- ⚙️ **Configuration**: customizable per-server settings
- 🎯 **Slash Commands**: modern Discord interface

## Prerequisites
- Python 3.8+ (recommended: 3.11)
- Discord bot token
- Server with appropriate permissions

## Installation

### Method 1: Local Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/project-bonk.git
   cd project-bonk
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/macOS
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your bot token and settings
   ```

5. **Test setup**
   ```bash
   python test_setup.py
   ```

6. **Run the bot**
   ```bash
   python main.py
   ```

### Method 2: Using Start Scripts

**Windows:**
```bash
start.bat
```

**Linux/macOS:**
```bash
chmod +x start.sh
./start.sh
```

### Method 3: Docker Deployment

1. **Build and run with Docker Compose**
   ```bash
   docker-compose up -d
   ```

2. **Or build manually**
   ```bash
   docker build -t project-bonk .
   docker run -d --name project-bonk-bot --env-file .env project-bonk
   ```

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Required
DISCORD_TOKEN=your_bot_token_here
GUILD_ID=your_server_id_here  # Optional: for faster command sync during development

# Optional
DATABASE_URL=sqlite:///data/bot.db
LOG_LEVEL=INFO
MAX_WARNINGS=3
DEFAULT_TIMEOUT_DURATION=600
COMMAND_PREFIX=!
```

### Discord Bot Setup

1. **Create Discord Application**
   - Go to https://discord.com/developers/applications
   - Click "New Application"
   - Name your application "Project Bonk"

2. **Create Bot**
   - Go to "Bot" section
   - Click "Add Bot"
   - Copy the token to your `.env` file

3. **Set Bot Permissions**
   Required permissions:
   - `Send Messages`
   - `Use Slash Commands`
   - `Manage Messages`
   - `Kick Members`
   - `Ban Members`
   - `Moderate Members`
   - `Read Message History`
   - `View Audit Log`

4. **Generate Invite Link**
   - Go to "OAuth2" > "URL Generator"
   - Select "bot" and "applications.commands"
   - Select required permissions
   - Copy the generated URL

## Commands

### Moderation Commands
- `/ban <user> [reason] [duration] [delete_messages]` - Ban a user
- `/kick <user> [reason]` - Kick a user
- `/timeout <user> <duration> [reason]` - Timeout a user
- `/untimeout <user> [reason]` - Remove timeout
- `/warn <user> <reason>` - Warn a user
- `/warnings <user>` - View user warnings
- `/removewarning <warning_id> [reason]` - Remove a specific warning
- `/clearwarnings <user> [reason]` - Clear all warnings for a user
- `/purge <amount> [user] [reason]` - Delete messages

### Utility Commands
- `/ping` - Check bot latency
- `/userinfo [user]` - Get user information
- `/serverinfo` - Get server information
- `/avatar [user]` - Get user avatar
- `/roleinfo <role>` - Get role information
- `/channelinfo [channel]` - Get channel information
- `/help` - Show help message

### Configuration Commands
- `/config [setting] [value]` - Configure server settings
- `/automod [feature] [enabled]` - Configure auto-moderation
- `/settings` - View all settings

## Database

The bot uses SQLite by default, storing data in `data/bot.db`. The database includes:

- **guild_config**: Server settings
- **moderation_cases**: All moderation actions
- **warnings**: User warnings
- **temp_punishments**: Temporary bans/timeouts
- **automod_settings**: Auto-moderation configuration

## Logging

The bot provides comprehensive logging:

- **Console**: Colored output with timestamps
- **File**: Detailed logs in `logs/bot.log`
- **Discord**: Moderation actions logged to configured channel

## Auto-Moderation

Configurable auto-moderation features:
- **Spam Detection**: Multiple messages in short time
- **Profanity Filter**: Configurable word list
- **Caps Filter**: Excessive uppercase text
- **Link Filter**: Unauthorized links
- **Invite Filter**: Discord invite links

## Development

### Project Structure
```
project-bonk/
├── main.py                 # Bot entry point
├── requirements.txt        # Python dependencies
├── .env.example           # Environment template
├── bot/
│   ├── __init__.py
│   ├── database.py        # Database management
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py      # Logging utilities
│   │   └── utils.py       # Helper functions
│   └── cogs/
│       ├── __init__.py
│       ├── moderation.py  # Moderation commands
│       ├── utility.py     # Utility commands
│       ├── config.py      # Configuration commands
│       ├── automod.py     # Auto-moderation
│       └── logging.py     # Event logging
├── data/                  # Database files
├── logs/                  # Log files
├── test_setup.py          # Setup verification
├── start.bat             # Windows start script
├── start.sh              # Linux/macOS start script
├── Dockerfile            # Docker configuration
└── docker-compose.yml    # Docker Compose configuration
```

### Adding New Features

1. **Create a new cog** in `bot/cogs/`
2. **Add command handlers** using `@app_commands.command`
3. **Update database schema** if needed in `bot/database.py`
4. **Add logging** using the logger utilities
5. **Test thoroughly** before deployment

### Code Style
- Use Black for formatting: `black .`
- Use flake8 for linting: `flake8 .`
- Follow PEP 8 guidelines
- Add type hints where appropriate

## Deployment

### Production Deployment

1. **Use Docker** for consistent deployment
2. **Set up proper logging** with log rotation
3. **Configure backups** for database
4. **Monitor performance** and logs
5. **Set up alerts** for critical errors

### Security Best Practices

- Keep bot token secure
- Use environment variables
- Limit bot permissions
- Regular security updates
- Monitor for suspicious activity

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure all dependencies are installed
   - Check Python version compatibility

2. **Permission Errors**
   - Verify bot has required permissions
   - Check role hierarchy

3. **Database Errors**
   - Ensure data directory exists
   - Check file permissions

4. **Command Not Found**
   - Verify commands are synced
   - Check guild_id configuration

### Getting Help

1. Check the logs in `logs/bot.log`
2. Run `python test_setup.py` to verify setup
3. Review Discord bot permissions
4. Check environment variables

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please:
1. Check this documentation
2. Review the troubleshooting section
3. Open an issue on GitHub
4. Contact the maintainers

---

**Note**: This bot is designed for educational and community management purposes. Always follow Discord's Terms of Service and Community Guidelines when using moderation tools.
