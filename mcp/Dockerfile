FROM python:3.10-slim

WORKDIR /app

# Install git for MCP SDK installation
RUN apt-get update && \
    apt-get install -y git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PORT=8000
ENV LOG_LEVEL=INFO
ENV HTTPX_TIMEOUT=5

# Expose the port
EXPOSE 8000

# Run the server
CMD ["python", "server.py"]
