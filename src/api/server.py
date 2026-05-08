from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import os
import json
import tempfile
import aiohttp
from src.core.config import Config
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

@app.post("/api/comfy/restore")
async def restore_nodes(workflow: dict):
    """
    Executes 'comfy node restore' for the provided workflow JSON.
    This will attempt to install all missing custom nodes found in the workflow.
    """
    # Save workflow to a temp file
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode='w', encoding='utf-8') as tf:
        json.dump(workflow, tf)
        temp_path = tf.name

    try:
        logger.info(f"Running comfy node restore for {temp_path}")
        # Run comfy-cli
        # We use 'asyncio.create_subprocess_exec' to avoid blocking the API
        process = await asyncio.create_subprocess_exec(
            "comfy", "node", "restore", "--workflow", temp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode().strip()
            logger.error(f"comfy-cli failed: {error_msg}")
            # Try to return a meaningful error if possible
            raise HTTPException(status_code=500, detail=f"Installation failed: {error_msg}")

        logger.info("Nodes installed successfully. Attempting to reboot ComfyUI...")

        # Attempt reboot via ComfyUI-Manager API
        reboot_success = False
        try:
            # We use a 10s timeout for the reboot call
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{Config.COMFY_URL}/manager/reboot", timeout=10) as resp:
                    reboot_success = resp.status == 200
                    if reboot_success:
                        logger.info("ComfyUI reboot triggered via Manager API")
        except Exception as e:
            logger.warning(f"Could not trigger auto-reboot (Manager API might be missing or unreachable): {e}")

        return {
            "status": "success",
            "reboot_triggered": reboot_success,
            "message": "Nodes installed successfully." + (" ComfyUI is restarting." if reboot_success else " Please restart ComfyUI manually.")
        }
    except Exception as e:
        logger.error(f"Error during node restoration: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass

async def start_api_server(bot, port=8001):
    global bot_instance
    bot_instance = bot
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="info")
    server = uvicorn.Server(config)
    logger.info(f"Starting API Server on port {port}...")
    await server.serve()
