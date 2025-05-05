#!/usr/bin/env python3
import argparse
import asyncio
import json
import httpx
import re
import sys
import uuid
import sseclient

async def stream_weather(alb_url, city):
    """Get weather for a city from the MCP server using streaming mode (SSE)."""
    # Format the URL
    if not alb_url.startswith("http"):
        alb_url = f"http://{alb_url}"
    if not alb_url.endswith("/v1/mcp"):
        alb_url = f"{alb_url}/v1/mcp"
    
    # Prepare the query
    is_forecast = "forecast" in city.lower()
    
    # Extract the actual city name if this is a forecast query
    if is_forecast:
        city_match = re.search(r'forecast for ([^?.,]+)', city, re.IGNORECASE)
        if city_match:
            actual_city = city_match.group(1).strip()
            query = f"What is the weather forecast for {actual_city}?"
            print(f"Getting forecast for: {actual_city}")
        else:
            # If we can't extract the city, just use the original input
            query = f"What is the weather like in {city}?"
            print(f"Getting weather for: {city}")
    else:
        query = f"What is the weather like in {city}?"
        print(f"Getting weather for: {city}")
    
    print(f"Connecting to MCP server at: {alb_url}")
    
    # Prepare the request data with streaming enabled
    request_data = {
        "model": "test-model",
        "messages": [
            {"role": "user", "content": query}
        ],
        "stream": True,  # Enable streaming mode
        "max_tokens": 1000,
        "temperature": 0.7
    }
    
    # Make the initial request to get the SSE endpoint
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Make a request to the MCP endpoint
            response = await client.post(
                alb_url,
                json=request_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                print(f"Error: {response.status_code} {response.reason_phrase}")
                print(f"Response: {response.text}")
                return
            
            # Parse the response to get the SSE endpoint
            response_text = response.text
            
            if "event: endpoint" in response_text:
                # Extract the SSE endpoint URL
                sse_endpoint_match = re.search(r'data: (.*)', response_text)
                if sse_endpoint_match:
                    sse_endpoint = sse_endpoint_match.group(1).strip()
                    
                    # Ensure the endpoint is a complete URL
                    if not sse_endpoint.startswith("http"):
                        # Extract base URL from the original ALB URL
                        base_url = alb_url.split("/v1/mcp")[0]
                        sse_endpoint = f"{base_url}{sse_endpoint}"
                    
                    print(f"Connecting to SSE endpoint: {sse_endpoint}")
                    
                    # Connect to the SSE endpoint
                    session_id = None
                    if "session_id=" not in sse_endpoint:
                        # Generate a session ID if not provided
                        session_id = str(uuid.uuid4())
                        if "?" in sse_endpoint:
                            sse_endpoint = f"{sse_endpoint}&session_id={session_id}"
                        else:
                            sse_endpoint = f"{sse_endpoint}?session_id={session_id}"
                    
                    # Make the SSE request
                    sse_response = await client.post(
                        sse_endpoint,
                        json=request_data,
                        headers={"Content-Type": "application/json"},
                        timeout=60.0
                    )
                    
                    if sse_response.status_code != 200:
                        print(f"Error connecting to SSE endpoint: {sse_response.status_code} {sse_response.reason_phrase}")
                        print(f"Response: {sse_response.text}")
                        return
                    
                    # Process the SSE stream
                    client = sseclient.SSEClient(sse_response)
                    
                    print("\nStreaming Weather Information:")
                    full_content = ""
                    
                    for event in client.events():
                        if event.data:
                            try:
                                data = json.loads(event.data)
                                if "choices" in data and len(data["choices"]) > 0:
                                    choice = data["choices"][0]
                                    if "delta" in choice and "content" in choice["delta"]:
                                        content = choice["delta"]["content"]
                                        full_content += content
                                        print(content, end="", flush=True)
                                    elif "finish_reason" in choice and choice["finish_reason"] == "stop":
                                        print("\n\nStream completed.")
                            except json.JSONDecodeError:
                                print(f"Could not parse event data: {event.data}")
                    
                    print("\n\nFull response:")
                    print(full_content)
                else:
                    print("Could not extract SSE endpoint from response.")
            else:
                print("Server did not return an SSE endpoint. Make sure streaming is enabled on the server.")
                print(f"Response: {response_text}")
        
        except Exception as e:
            print(f"Error connecting to MCP server: {str(e)}")

def main():
    """Main function to parse arguments and run the client."""
    parser = argparse.ArgumentParser(description="MCP Weather Streaming Client")
    parser.add_argument("alb_url", help="ALB URL of the MCP server")
    parser.add_argument("city", help="City to get weather for")
    args = parser.parse_args()
    
    asyncio.run(stream_weather(args.alb_url, args.city))

if __name__ == "__main__":
    main()
