#!/bin/bash

echo "Starting Project Bonk Discord Bot..."
echo

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo
fi

# Activate virtual environment
source venv/bin/activate

# Install/upgrade dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
echo

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "WARNING: .env file not found!"
    echo "Please copy .env.example to .env and configure your bot token."
    echo
    exit 1
fi

# Start the bot
echo "Starting bot..."
python main.py
