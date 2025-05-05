# MCP Weather Server

A Python-based implementation of a Machine Conversation Protocol (MCP) server that provides weather information using the OpenWeather API.

## Overview

This project demonstrates how to build and deploy an MCP-compliant server that uses the FastMCP SDK to expose weather-related tools on an Amazon EKS cluster. The server supports both streaming (SSE) and non-streaming modes, allowing clients to retrieve current weather data and forecasts for cities around the world through an Application Load Balancer (ALB).

## Architecture

### Infrastructure Components

- **Amazon EKS**: Managed Kubernetes service for running containerized applications
- **BottleRocket MNG**: Secure, minimal-footprint Linux-based OS for container hosting
- **AWS ALB Controller**: Manages AWS Application Load Balancers for Kubernetes ingress
- **AWS ECR**: Container registry for storing Docker images

### Server Components

- **FastAPI Application**: The core server built with FastAPI, providing HTTP endpoints that comply with the MCP specification
- **FastMCP Integration**: Uses the MCP Python SDK to register and expose weather tools
- **OpenWeather API Client**: Retrieves real-time weather data and forecasts
- **SSE Transport**: Implements Server-Sent Events for streaming responses

### Client Components

- **MCP Client**: A Python client that demonstrates how to interact with the MCP server
- **Non-Streaming Mode**: Supports simple one-shot requests for weather data

## EKS Deployment

This project demonstrates how to deploy an MCP server on Amazon EKS with the following features:

1. **BottleRocket Managed Node Groups**: Secure, purpose-built OS for running containers
2. **ALB Ingress Controller**: Automatically provisions AWS Application Load Balancers
3. **ECR Integration**: Stores and manages container images
4. **Kubernetes Secrets**: Securely manages the OpenWeather API key

### Deployment Process

1. **EKS Cluster Setup**: Create an EKS cluster with BottleRocket MNG using Terraform
2. **ALB Controller Installation**: Deploy the AWS ALB Controller for ingress management
3. **Container Build**: Build the Docker image for the MCP server
4. **ECR Push**: Push the image to Amazon ECR
5. **Kubernetes Deployment**: Deploy the MCP server with appropriate resources and ingress

## Server-Sent Events (SSE) Implementation

The server implements the Server-Sent Events (SSE) protocol for streaming responses, which offers several advantages:

1. **Long-lived Connections**: Allows the server to push updates to the client over a single HTTP connection
2. **Simple Protocol**: Uses standard HTTP with a specialized content type (`text/event-stream`)
3. **Automatic Reconnection**: Browsers automatically attempt to reconnect if the connection is dropped
4. **Event Formatting**: Messages are sent with a `data:` prefix and separated by double newlines

### SSE Flow in the MCP Server

1. **Initial Connection**: Client makes a POST request to `/v1/mcp` with `stream: true`
2. **Session Creation**: Server generates a unique session ID and returns an SSE endpoint URL
3. **Stream Establishment**: Client connects to the SSE endpoint with the session ID
4. **Data Streaming**: Server streams weather data as formatted SSE events
5. **Session Management**: Server maintains active sessions with expiration handling

## MCP Tool Implementation

The server registers two main weather tools using the FastMCP SDK:

1. **get_current_weather**: Retrieves and formats current weather conditions for a city
2. **get_weather_forecast**: Provides a 5-day weather forecast with daily temperature ranges and conditions

Tools are registered in the FastMCP instance's `tools` dictionary, making them accessible through:

```python
result = await weather_mcp.tools["get_current_weather"].function(city=city)
```

## Usage

### Server Setup

1. Clone the repository:
   ```
   git clone <repository-url>
   cd mcp-eks-example
   ```

2. Set up the OpenWeather API key:
   ```
   kubectl create secret generic openweather-api --from-literal=API_KEY=your_api_key_here
   ```

3. Build and deploy the server:
   ```
   cd mcp-eks-demo/mcp
   ./build-deploy.sh
   ```

4. Get the ALB URL:
   ```
   kubectl get ingress mcp-server-py-ingress -n default -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
   ```

### Client Usage

The MCP client supports both current weather and forecast queries:

1. For current weather:
   ```
   python mcp_client.py $ALB_URL "London"
   ```

2. For weather forecasts:
   ```
   python mcp_client.py $ALB_URL "forecast for New York"
   ```

## Environment Variables

- `OPENWEATHER_API_KEY`: Required for API access
- `PORT`: Server port (default: 8000)
- `LOG_LEVEL`: Logging level (default: INFO)
- `HTTPX_TIMEOUT`: HTTP request timeout in seconds (default: 5)

## Security Considerations

- **API Key Management**: The OpenWeather API key is stored as a Kubernetes secret
- **Network Security**: Traffic is managed through the ALB, which can be configured with appropriate security groups
- **Container Security**: BottleRocket provides enhanced security for container workloads with minimal attack surface

## Error Handling

The server implements comprehensive error handling:

- API timeouts
- City not found errors
- General API errors
- Session management errors

## Development

### Prerequisites

- Python 3.10 or higher
- Docker
- kubectl configured for your EKS cluster
- AWS CLI configured with appropriate permissions
- Terraform (for infrastructure deployment)


