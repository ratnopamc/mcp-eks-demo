import os
import logging
import json
import uuid
import time
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn
from typing import Dict, Any, Optional

from tools.weather import setup_weather_mcp

# Configure logging
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mcp-server")

# Initialize FastAPI app
app = FastAPI(title="MCP Weather Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize MCP with weather tools
weather_mcp = setup_weather_mcp()

# Store active sessions with timestamps
active_sessions: Dict[str, Dict[str, Any]] = {}

# Session expiration time in seconds
SESSION_EXPIRATION = 300  # 5 minutes

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "healthy", "service": "mcp-weather-server"}

@app.post("/v1/mcp")
async def handle_mcp_request(request: Request):
    """Handle initial MCP request and return SSE endpoint or direct response."""
    try:
        # Parse request body
        body = await request.json()
        logger.info(f"Received MCP request: {body}")
        
        # Check if streaming is requested
        stream = body.get("stream", True)
        
        if not stream:
            # For non-streaming requests, process directly
            query = body.get("messages", [{}])[0].get("content", "")
            logger.info(f"Processing non-streaming query: {query}")
            
            # Extract city from query
            import re
            city_match = re.search(r'weather like in ([^?.,]+)', query, re.IGNORECASE)
            if not city_match:
                city_match = re.search(r'forecast for ([^?.,]+)', query, re.IGNORECASE)
            if not city_match:
                city_match = re.search(r'weather forecast for ([^?.,]+)', query, re.IGNORECASE)
            city = city_match.group(1).strip() if city_match else "London"
            
            logger.info(f"Extracted city: {city}")
            
            try:
                # Use MCP tools to get weather data
                if "forecast" in query.lower() or "tomorrow" in query.lower() or "next" in query.lower():
                    # Get forecast using MCP tool
                    result = await weather_mcp.tools["get_weather_forecast"].function(city=city)
                else:
                    # Get current weather using MCP tool
                    result = await weather_mcp.tools["get_current_weather"].function(city=city)
                
                # Return direct response for non-streaming requests
                return {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": result
                            },
                            "finish_reason": "stop"
                        }
                    ]
                }
            except Exception as e:
                logger.error(f"Error getting weather data: {str(e)}")
                return {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": f"Error: Could not get weather data for {city}. {str(e)}"
                            },
                            "finish_reason": "stop"
                        }
                    ]
                }
        else:
            # For streaming requests, generate session ID
            session_id = str(uuid.uuid4()).replace("-", "")
            
            # Store session data with timestamp
            active_sessions[session_id] = {
                "query": body.get("messages", [{}])[0].get("content", ""),
                "stream": stream,
                "body": body,
                "timestamp": time.time()
            }
            
            logger.info(f"Generated session ID: {session_id}")
            
            # Return the SSE endpoint
            return f"event: endpoint\ndata: /v1/mcp/messages/?session_id={session_id}\n\n"
    except Exception as e:
        logger.error(f"Error processing MCP request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Cleanup expired sessions
def cleanup_expired_sessions():
    """Remove expired sessions."""
    current_time = time.time()
    expired_sessions = [
        session_id for session_id, data in active_sessions.items()
        if current_time - data.get("timestamp", 0) > SESSION_EXPIRATION
    ]
    
    for session_id in expired_sessions:
        logger.info(f"Removing expired session: {session_id}")
        active_sessions.pop(session_id, None)
    
    return len(expired_sessions)

async def stream_weather_response(session_id: str, query: str):
    """Stream weather response as SSE events."""
    try:
        # Extract city from query
        import re
        city_match = re.search(r'weather like in ([^?.,]+)', query, re.IGNORECASE)
        if not city_match:
            city_match = re.search(r'forecast for ([^?.,]+)', query, re.IGNORECASE)
        if not city_match:
            city_match = re.search(r'weather forecast for ([^?.,]+)', query, re.IGNORECASE)
        city = city_match.group(1).strip() if city_match else "London"
        
        logger.info(f"Extracted city: {city}")
        
        try:
            # Use MCP tools to get weather data
            if "forecast" in query.lower() or "tomorrow" in query.lower() or "next" in query.lower():
                # Get forecast using MCP tool
                result = await weather_mcp.tools["get_weather_forecast"].function(city=city)
            else:
                # Get current weather using MCP tool
                result = await weather_mcp.tools["get_current_weather"].function(city=city)
            
            # Stream the response as SSE events
            yield f"data: {json.dumps({'choices': [{'delta': {'role': 'assistant', 'content': result}}]})}\n\n"
            yield f"data: {json.dumps({'choices': [{'finish_reason': 'stop'}]})}\n\n"
        except Exception as e:
            logger.error(f"Error getting weather data: {str(e)}")
            error_message = f"Error: Could not get weather data for {city}. {str(e)}"
            yield f"data: {json.dumps({'choices': [{'delta': {'role': 'assistant', 'content': error_message}}]})}\n\n"
            yield f"data: {json.dumps({'choices': [{'finish_reason': 'stop'}]})}\n\n"
        
        # Update session timestamp instead of deleting
        if session_id in active_sessions:
            active_sessions[session_id]["timestamp"] = time.time()
            logger.info(f"Updated session timestamp: {session_id}")
        
    except Exception as e:
        logger.error(f"Error streaming weather response: {str(e)}")
        error_message = f"Sorry, I encountered an error while getting the weather information: {str(e)}"
        yield f"data: {json.dumps({'choices': [{'delta': {'role': 'assistant', 'content': error_message}}]})}\n\n"
        yield f"data: {json.dumps({'choices': [{'finish_reason': 'stop'}]})}\n\n"

@app.post("/v1/mcp/messages/")
async def handle_messages(request: Request, response: Response, session_id: Optional[str] = None):
    """Handle SSE messages with dynamic weather responses."""
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    
    try:
        # Clean up expired sessions
        num_expired = cleanup_expired_sessions()
        if num_expired > 0:
            logger.info(f"Cleaned up {num_expired} expired sessions")
        
        # Get session data
        session_data = active_sessions.get(session_id)
        if not session_data:
            logger.error(f"Session not found: {session_id}")
            raise HTTPException(status_code=404, detail="Session not found or expired")
        
        # Get request body
        body = await request.json()
        logger.info(f"Received SSE message: {body}")
        
        # Extract the query from the request or use the one from session
        query = session_data["query"]
        if "messages" in body and len(body["messages"]) > 0:
            query = body["messages"][0].get("content", query)
        
        logger.info(f"Processing query: {query}")
        
        # Set SSE headers
        response.headers["Content-Type"] = "text/event-stream"
        response.headers["Cache-Control"] = "no-cache"
        response.headers["Connection"] = "keep-alive"
        
        # Return streaming response
        return StreamingResponse(
            stream_weather_response(session_id, query),
            media_type="text/event-stream"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing SSE message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
