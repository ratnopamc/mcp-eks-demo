#!/usr/bin/env python3
import argparse
import asyncio
import json
import httpx
import sys
import re

async def get_weather(alb_url, city):
    """Get weather for a city from the MCP server in a single request."""
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
    
    # Prepare the request data
    request_data = {
        "model": "test-model",
        "messages": [
            {"role": "user", "content": query}
        ],
        "stream": False,  # Use non-streaming mode
        "max_tokens": 1000,
        "temperature": 0.7
    }
    
    # Make the request
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Make a direct request to the MCP endpoint
            response = await client.post(
                alb_url,
                json=request_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                print(f"Error: {response.status_code} {response.reason_phrase}")
                print(f"Response: {response.text}")
                return
            
            # Parse the response
            try:
                response_text = response.text
                
                # Try to parse as JSON
                try:
                    data = json.loads(response_text)
                    if "choices" in data and len(data["choices"]) > 0:
                        choice = data["choices"][0]
                        if "message" in choice and "content" in choice["message"]:
                            content = choice["message"]["content"]
                            print("\nWeather Information:")
                            print(content)
                        else:
                            print("\nResponse structure:")
                            print(json.dumps(data, indent=2))
                    else:
                        print("\nResponse structure:")
                        print(json.dumps(data, indent=2))
                except json.JSONDecodeError:
                    # Not JSON, might be SSE format
                    if "event: endpoint" in response_text:
                        print("\nReceived SSE endpoint instead of direct response.")
                        print("The server is still using streaming mode despite our request.")
                        print("Please redeploy the server with the latest changes.")
                    else:
                        print("\nCould not parse response as JSON:")
                        print(response_text)
            
            except Exception as e:
                print(f"Error parsing response: {str(e)}")
        
        except Exception as e:
            print(f"Error connecting to MCP server: {str(e)}")

def main():
    """Main function to parse arguments and run the client."""
    parser = argparse.ArgumentParser(description="MCP Weather Client")
    parser.add_argument("alb_url", help="ALB URL of the MCP server")
    parser.add_argument("city", help="City to get weather for")
    args = parser.parse_args()
    
    asyncio.run(get_weather(args.alb_url, args.city))

if __name__ == "__main__":
    main()
