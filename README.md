# Project Bonk - Discord Moderation Bot

A comprehensive Discord moderation bot built with discord.py, featuring slash commands and advanced moderation capabilities.

## Features

- 🔨 **Moderation Commands**: Ban, kick, timeout, warn, and more
- 🛡️ **Auto-moderation**: Spam detection, profanity filtering
- 📊 **Logging**: Comprehensive audit logs
- 📋 **Case Management**: Track moderation actions
- 🔧 **Configuration**: Customizable per-server settings
- 🎯 **Slash Commands**: Modern Discord command interface

## Setup

### Prerequisites

- Python 3.8 or higher
- A Discord application with bot token
- Discord server with appropriate permissions

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/project-bonk.git
   cd project-bonk
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Fill in your bot token and other required values

5. Start the bot:
   ```bash
   python main.py
   ```

## Configuration

Create a `.env` file in the root directory with the following variables:

```env
DISCORD_TOKEN=your_bot_token_here
GUILD_ID=your_server_id_here (optional, for guild-specific commands)
LOG_LEVEL=INFO
```

## Commands

### Moderation Commands

- `/ban` - Ban a user from the server
- `/kick` - Kick a user from the server
- `/timeout` - Timeout a user
- `/warn` - Warn a user
- `/unwarn` - Remove a warning
- `/warnings` - View user warnings
- `/purge` - Delete multiple messages
- `/lock` - Lock a channel
- `/unlock` - Unlock a channel

### Utility Commands

- `/userinfo` - Get information about a user
- `/serverinfo` - Get server information
- `/ping` - Check bot latency

## Development

### Running in Development Mode

```bash
python main.py
```

### Code Style

This project uses Black for code formatting and flake8 for linting:

```bash
pip install black flake8
black .
flake8 .
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support, please open an issue on GitHub or contact the maintainers.
