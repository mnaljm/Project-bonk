# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot code
COPY . .

# Create data directory
RUN mkdir -p data logs

# Create non-root user
RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /app
USER botuser

# Expose health check port (optional)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import asyncio; print('healthy')" || exit 1

# Run the bot
CMD ["python", "main.py"]
