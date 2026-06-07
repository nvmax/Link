from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import time
from collections import defaultdict
from src.core.config import Config
from src.core.logger import setup_logger
from src.api import state
from src.api.routers import comfy, models, discord, ai, config

logger = setup_logger("api_server")

app = FastAPI()

# Rate limits config: {path: (max_requests, period_in_seconds)}
RATE_LIMITS = {
    "/api/ai/enhance": (10, 60),        # 10 requests per minute
    "/api/models/download": (5, 3600),   # 5 requests per hour
    "/api/comfy/setup": (5, 3600),       # 5 requests per hour
}

# In-memory database of requests: {ip: {path: [timestamps]}}
request_history = defaultdict(lambda: defaultdict(list))

# Enable CORS for the dashboard with standard localhost and environment-aware fallbacks
cors_origins_env = os.getenv("ALLOWED_CORS_ORIGINS", "")
if cors_origins_env:
    origins = [x.strip() for x in cors_origins_env.split(",") if x.strip()]
else:
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "127.0.0.1"
    path = request.url.path
    if path in RATE_LIMITS and request.method != "OPTIONS":
        limit, period = RATE_LIMITS[path]
        now = time.time()
        
        # Get history for this IP and path
        history = request_history[client_ip][path]
        
        # Remove timestamps older than the period
        while history and history[0] < now - period:
            history.pop(0)
            
        if len(history) >= limit:
            origin = request.headers.get("origin")
            headers = {}
            if origin and (origin in origins or "*" in origins):
                headers["Access-Control-Allow-Origin"] = origin
            elif origins:
                headers["Access-Control-Allow-Origin"] = origins[0]
            else:
                headers["Access-Control-Allow-Origin"] = "*"
                
            headers["Access-Control-Allow-Credentials"] = "true"
            
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
                headers=headers
            )
            
        history.append(now)
        
    return await call_next(request)

@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    api_key = Config.API_KEY
    if not api_key:
        return await call_next(request)
        
    path = request.url.path
    if path.startswith("/api/") and request.method != "OPTIONS":
        req_key = request.headers.get("x-api-key") or request.query_params.get("api_key")
        if req_key != api_key:
            if path == "/api/config/reload":
                from dotenv import load_dotenv
                load_dotenv(override=True)
                new_key = os.getenv("API_KEY")
                if req_key == new_key:
                    return await call_next(request)
                    
            origin = request.headers.get("origin")
            headers = {}
            if origin and (origin in origins or "*" in origins):
                headers["Access-Control-Allow-Origin"] = origin
            elif origins:
                headers["Access-Control-Allow-Origin"] = origins[0]
            else:
                headers["Access-Control-Allow-Origin"] = "*"
                
            headers["Access-Control-Allow-Credentials"] = "true"
            headers["Access-Control-Allow-Methods"] = "*"
            headers["Access-Control-Allow-Headers"] = "*"
            
            return JSONResponse(
                status_code=401,
                content={"detail": "Unauthorized: Invalid or missing API Key"},
                headers=headers
            )
            
    return await call_next(request)

# Include Modular Routers
app.include_router(comfy.router)
app.include_router(models.router)
app.include_router(discord.router)
app.include_router(ai.router)
app.include_router(config.router)

@app.get("/health")
async def health():
    comfy_connected = False
    if state.bot_instance and state.bot_instance.api_client:
        comfy_connected = await state.bot_instance.api_client.check_connection()
        
    return {
        "status": "ok", 
        "bot_connected": state.bot_instance is not None and state.bot_instance.is_ready(),
        "comfy_connected": comfy_connected
    }

async def start_api_server(bot, port=8001):
    state.bot_instance = bot
    host = "0.0.0.0" if Config.IS_DOCKER else "127.0.0.1"
    config_server = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config_server)
    logger.info(f"Starting API Server on port {port}...")
    await server.serve()
