import os
import httpx
from typing import Optional, Dict, Any
from mcp.server.fastmcp import FastMCP

async def get_weather_data(city: str, country_code: Optional[str] = None, units: str = "metric") -> Dict[str, Any]:
    """Get weather data from OpenWeather API."""
    api_key = os.environ.get("OPENWEATHER_API_KEY")
    if not api_key:
        raise ValueError("OPENWEATHER_API_KEY environment variable is not set")
    
    base_url = "https://api.openweathermap.org/data/2.5/weather"
    
    # Format the query
    query = city
    if country_code:
        query = f"{query},{country_code}"
        
    request_params = {
        "q": query,
        "appid": api_key,
        "units": units
    }
    
    # Make the API request with a timeout
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(base_url, params=request_params)
        response.raise_for_status()
        return response.json()

async def get_forecast_data(city: str, country_code: Optional[str] = None, units: str = "metric") -> Dict[str, Any]:
    """Get forecast data from OpenWeather API."""
    api_key = os.environ.get("OPENWEATHER_API_KEY")
    if not api_key:
        raise ValueError("OPENWEATHER_API_KEY environment variable is not set")
    
    base_url = "https://api.openweathermap.org/data/2.5/forecast"
    
    # Format the query
    query = city
    if country_code:
        query = f"{query},{country_code}"
        
    request_params = {
        "q": query,
        "appid": api_key,
        "units": units
    }
    
    # Make the API request with a timeout
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(base_url, params=request_params)
        response.raise_for_status()
        return response.json()

def setup_weather_mcp() -> FastMCP:
    """Initialize and configure the FastMCP server for weather tools."""
    # Initialize FastMCP server
    mcp = FastMCP("weather")
    
    # Define weather tools
    async def get_current_weather_impl(city: str, country_code: Optional[str] = None, units: str = "metric") -> str:
        """Get current weather information for a city.
        
        Args:
            city: The city to get weather for
            country_code: Optional two-letter country code (ISO 3166)
            units: Units of measurement (standard, metric, imperial)
        """
        try:
            data = await get_weather_data(city, country_code, units)
            
            # Format the response
            result = f"Current weather in {data['name']}, {data['sys']['country']}:\n"
            result += f"Temperature: {data['main']['temp']}°C\n"
            result += f"Feels like: {data['main']['feels_like']}°C\n"
            result += f"Humidity: {data['main']['humidity']}%\n"
            result += f"Wind speed: {data['wind']['speed']} m/s\n"
            result += f"Conditions: {data['weather'][0]['description']}\n"
            
            return result
        except httpx.TimeoutException:
            return f"Error: Timeout while getting weather data for {city}. Please try again later."
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return f"Error: Could not find weather data for {city}. Please check the city name and try again."
            return f"Error: Could not retrieve weather data for {city}. The weather service might be unavailable."
        except Exception as e:
            return f"Error: An unexpected error occurred while getting weather data for {city}."
    
    async def get_weather_forecast_impl(city: str, country_code: Optional[str] = None, units: str = "metric") -> str:
        """Get a 5-day weather forecast for a city.
        
        Args:
            city: The city to get forecast for
            country_code: Optional two-letter country code (ISO 3166)
            units: Units of measurement (standard, metric, imperial)
        """
        try:
            data = await get_forecast_data(city, country_code, units)
            
            # Format the response
            result = f"5-day forecast for {data['city']['name']}, {data['city']['country']}:\n\n"
            
            # Group forecasts by day
            forecasts_by_day = {}
            for item in data['list']:
                date = item['dt_txt'].split(' ')[0]
                if date not in forecasts_by_day:
                    forecasts_by_day[date] = []
                forecasts_by_day[date].append(item)
            
            # Format each day's forecast
            for date, items in list(forecasts_by_day.items())[:5]:  # Limit to 5 days
                result += f"Date: {date}\n"
                
                # Get min/max temperatures for the day
                temps = [item['main']['temp'] for item in items]
                min_temp = min(temps)
                max_temp = max(temps)
                
                # Get the most common weather condition
                conditions = {}
                for item in items:
                    condition = item['weather'][0]['description']
                    conditions[condition] = conditions.get(condition, 0) + 1
                most_common_condition = max(conditions.items(), key=lambda x: x[1])[0]
                
                result += f"Temperature: {min_temp}°C to {max_temp}°C\n"
                result += f"Conditions: {most_common_condition}\n\n"
            
            return result
        except httpx.TimeoutException:
            return f"Error: Timeout while getting forecast data for {city}. Please try again later."
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return f"Error: Could not find forecast data for {city}. Please check the city name and try again."
            return f"Error: Could not retrieve forecast data for {city}. The weather service might be unavailable."
        except Exception as e:
            return f"Error: An unexpected error occurred while getting forecast data for {city}."
    
    # Register tools manually in the tools dictionary
    mcp.tools = {
        "get_current_weather": type('Tool', (), {'function': get_current_weather_impl}),
        "get_weather_forecast": type('Tool', (), {'function': get_weather_forecast_impl})
    }
    
    assert isinstance(mcp, FastMCP), "setup_weather_mcp must return a FastMCP object"
    return mcp
