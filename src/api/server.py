from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
from src.core.logger import setup_logger

logger = setup_logger("api_server")

app = FastAPI()

# Enable CORS for the dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# We'll store a reference to the bot instance here
bot_instance = None

@app.get("/health")
async def health():
    return {"status": "ok", "bot_connected": bot_instance is not None and bot_instance.is_ready()}

@app.get("/api/discord/guild/{guild_id}")
async def get_guild(guild_id: int):
    if not bot_instance:
        raise HTTPException(status_code=503, detail="Bot not initialized")
    
    guild = bot_instance.get_guild(guild_id)
    if not guild:
        # Try to fetch if not in cache
        try:
            guild = await bot_instance.fetch_guild(guild_id)
        except:
            raise HTTPException(status_code=404, detail="Guild not found")
            
    return {
        "id": str(guild.id),
        "name": guild.name,
        "icon": str(guild.icon.url) if guild.icon else None
    }

@app.get("/api/discord/channel/{channel_id}")
async def get_channel(channel_id: int):
    if not bot_instance:
        raise HTTPException(status_code=503, detail="Bot not initialized")
    
    channel = bot_instance.get_channel(channel_id)
    if not channel:
        try:
            channel = await bot_instance.fetch_channel(channel_id)
        except:
            raise HTTPException(status_code=404, detail="Channel not found")
            
    return {
        "id": str(channel.id),
        "name": channel.name,
        "guild_name": channel.guild.name if hasattr(channel, 'guild') else "Unknown",
        "guild_id": str(channel.guild.id) if hasattr(channel, 'guild') else None
    }

async def start_api_server(bot, port=8001):
    global bot_instance
    bot_instance = bot
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="info")
    server = uvicorn.Server(config)
    logger.info(f"Starting API Server on port {port}...")
    await server.serve()
