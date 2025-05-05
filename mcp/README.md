# MCP Weather Server

A FastAPI-based weather service that implements the Machine Conversation Protocol (MCP) to provide real-time weather information and forecasts using the OpenWeather API.

## Overview

The MCP Weather Server is designed to run on Kubernetes (specifically Amazon EKS) and provides weather information through a simple API interface. It supports both streaming and non-streaming modes, making it versatile for different client needs.

## Features

- **Current Weather**: Get real-time weather information for any city
- **5-Day Forecast**: Get a 5-day weather forecast with daily temperature ranges and conditions
- **Non-Streaming Mode**: Get weather data in a single request without session management
- **Streaming Mode**: Connect to an SSE endpoint for streaming weather updates
- **Error Handling**: Comprehensive error handling for API requests and responses
- **Kubernetes Ready**: Designed to run on Kubernetes with proper health checks and resource management

## Components

### Server (`server.py`)

The main server implementation using FastAPI. It handles:
- Processing MCP requests in both streaming and non-streaming modes
- Extracting city names from natural language queries
- Fetching weather data from the OpenWeather API
- Formatting responses according to the MCP protocol
- Session management for streaming connections

### Weather Tools (`tools/weather.py`)

Contains functions for interacting with the OpenWeather API:
- `get_weather_data()`: Fetches current weather for a city
- `get_forecast_data()`: Fetches a 5-day forecast for a city
- `setup_weather_mcp()`: Sets up MCP tools for weather queries

### Client (`mcp_client.py`)

A simplified client that uses the non-streaming mode to get weather data in a single request. It can handle both current weather and forecast queries.

### Deployment Files

- `Dockerfile`: Builds the Docker image for the server
- `mcp-deploy.yaml`: Kubernetes deployment configuration
- `build-deploy.sh`: Script to build and deploy the server to EKS
- `requirements.txt`: Python dependencies

## Usage

### Deploying the Server

```bash
./build-deploy.sh
```

This script builds the Docker image, pushes it to ECR, and deploys it to your EKS cluster.

### Getting Weather Information

Use the MCP client to get weather information:

```bash
# For current weather
python mcp_client.py $ALB_URL "New York"

# For forecast
python mcp_client.py $ALB_URL "forecast for London"
```

Replace `$ALB_URL` with the URL of your Application Load Balancer.

## Environment Variables

- `OPENWEATHER_API_KEY`: Required for accessing the OpenWeather API
- `PORT`: Server port (default: 8000)
- `LOG_LEVEL`: Logging level (default: INFO)
- `HTTPX_TIMEOUT`: HTTP request timeout in seconds (default: 5)

## Architecture

The server follows a simple architecture:
1. Client sends a request to the MCP endpoint
2. Server extracts the city name from the query
3. Server fetches weather data from the OpenWeather API
4. Server formats the response and returns it to the client

For non-streaming requests, the response is returned directly. For streaming requests, the server generates a session ID and returns an SSE endpoint for the client to connect to.

## Error Handling

The server includes comprehensive error handling for:
- Invalid queries
- OpenWeather API errors
- Network timeouts
- Session management issues

## Security Considerations

- The OpenWeather API key is stored as a Kubernetes secret
- The server is designed to run in a private subnet with access controlled by an ALB
- No authentication is implemented in this version, as it's designed for internal use

## Future Improvements

- Add authentication for the MCP endpoint
- Implement caching for weather data to reduce API calls
- Add support for more weather data types (e.g., air quality, historical data)
- Improve natural language processing for more complex weather queries
