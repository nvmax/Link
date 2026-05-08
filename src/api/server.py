from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import os
import json
import tempfile
import aiohttp
from src.core.config import Config
from src.core.logger import setup_logger
import tkinter as tk
from tkinter import filedialog

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
async def restore_nodes(request: Request):
    """
    Analyzes a workflow JSON for missing nodes and attempts to install them.
    Now also accepts a list of missing_nodes class names for direct resolution.
    """
    try:
        body = await request.json()
        
        # Determine if we got a full workflow or a wrapper with missing_nodes
        workflow_data = body
        missing_nodes_override = []
        
        if isinstance(body, dict) and ("workflow" in body or "missing_nodes" in body):
            workflow_data = body.get("workflow", {})
            missing_nodes_override = body.get("missing_nodes", [])

        if not workflow_data and not missing_nodes_override:
            return {"status": "skipped", "message": "No workflow or missing nodes provided"}

        comfy_path = Config.COMFY_PATH
        resolved_path = resolve_comfy_workspace(comfy_path)
        logger.info(f"Auto-resolved ComfyUI workspace to: {resolved_path}")
        
        # Ensure __init__.py exists for compatibility
        if resolved_path:
            init_file = os.path.join(resolved_path, "comfy", "__init__.py")
            if not os.path.exists(init_file):
                try:
                    os.makedirs(os.path.dirname(init_file), exist_ok=True)
                    with open(init_file, 'w') as f:
                        pass
                except: pass

        # 1. Try installing by class names first if provided (this is more reliable for new nodes)
        installed_any = False
        if missing_nodes_override:
            logger.info(f"Attempting to resolve {len(missing_nodes_override)} missing nodes by class name...")
            resolved_urls = find_urls_for_classes(resolved_path, missing_nodes_override)
            if resolved_urls:
                logger.info(f"Found {len(resolved_urls)} matching repositories: {resolved_urls}")
                for url in resolved_urls:
                    success = await run_comfy_install(resolved_path, url)
                    if success:
                        installed_any = True
            else:
                logger.warning("Could not find any matching repositories for the specified class names in the Manager cache.")

        # 2. Fallback or parallel: Try the standard workflow-based install
        if workflow_data:
            with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode='w', encoding='utf-8') as tf:
                json.dump(workflow_data, tf)
                temp_path = tf.name

            try:
                success = await run_comfy_install_deps(resolved_path, temp_path)
                if success:
                    installed_any = True
            finally:
                if os.path.exists(temp_path):
                    try: os.unlink(temp_path)
                    except: pass

        if not installed_any:
            return {"status": "skipped", "message": "No missing nodes were found or installation could not be resolved."}

        logger.info("Nodes installed successfully. Attempting to reboot ComfyUI...")
        
        # Attempt reboot via ComfyUI-Manager API
        reboot_success = False
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{Config.COMFY_URL}/manager/reboot", timeout=10) as resp:
                    reboot_success = resp.status == 200
        except: pass

        return {
            "status": "success", 
            "message": "Nodes installed successfully." + (" ComfyUI is restarting." if reboot_success else " Please restart ComfyUI manually."),
            "reboot_triggered": reboot_success
        }
    except Exception as e:
        logger.error(f"Error during node restoration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def run_comfy_install(workspace_path: str, target: str) -> bool:
    """Runs 'comfy node install <target>'"""
    cmd = f'comfy --workspace "{workspace_path}" --skip-prompt node install "{target}"'
    return await execute_comfy_command(workspace_path, cmd)

async def run_comfy_install_deps(workspace_path: str, workflow_path: str) -> bool:
    """Runs 'comfy node install-deps --workflow <path>'"""
    cmd = f'comfy --workspace "{workspace_path}" --skip-prompt node install-deps --workflow "{workflow_path}"'
    return await execute_comfy_command(workspace_path, cmd)

async def execute_comfy_command(workspace_path: str, cmd: str) -> bool:
    """Helper to execute a comfy-cli command with environment and stdin handling"""
    env = os.environ.copy()
    if workspace_path:
        env["PYTHONPATH"] = workspace_path + os.pathsep + env.get("PYTHONPATH", "")
        env["COMFYUI_PATH"] = workspace_path

    process = await asyncio.create_subprocess_shell(
        cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=env,
        cwd=workspace_path
    )
    
    if process.stdin:
        process.stdin.write(b"y\n")
        await process.stdin.drain()
        process.stdin.close()

    while True:
        line = await process.stdout.readline()
        if not line:
            break
        decoded_line = line.decode().strip()
        if decoded_line:
            logger.info(f"[comfy-cli] {decoded_line}")

    await process.wait()
    return process.returncode == 0

def find_urls_for_classes(workspace_path: str, class_names: list) -> list:
    """Searches ComfyUI-Manager's cache files for class names and returns repo URLs"""
    cache_dir = os.path.join(workspace_path, "user", "__manager", "cache")
    if not os.path.exists(cache_dir):
        return []
    
    urls = set()
    try:
        # Search all extension-node-map files (usually named like <hash>_extension-node-map.json)
        for filename in os.listdir(cache_dir):
            if "extension-node-map" in filename and filename.endswith(".json"):
                with open(os.path.join(cache_dir, filename), "r", encoding='utf-8') as f:
                    data = json.load(f)
                    for url, info in data.items():
                        if isinstance(info, list) and len(info) > 0:
                            node_classes = info[0]
                            if any(cls in node_classes for cls in class_names):
                                urls.add(url)
    except Exception as e:
        logger.error(f"Error searching Manager cache: {e}")
        
    return list(urls)

def resolve_comfy_workspace(base_path: str):
    if not base_path: return ""
    if os.path.exists(os.path.join(base_path, "main.py")): return base_path
    subfolder = os.path.join(base_path, "ComfyUI")
    if os.path.exists(os.path.join(subfolder, "main.py")): return subfolder
    return base_path

@app.post("/api/utils/select-folder")
async def select_folder():
    """Opens a native folder selection dialog and returns the path."""
    def get_path():
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        path = filedialog.askdirectory()
        root.destroy()
        return path

    path = await asyncio.to_thread(get_path)
    return {"path": path}

async def start_api_server(bot, port=8001):
    global bot_instance
    bot_instance = bot
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="info")
    server = uvicorn.Server(config)
    logger.info(f"Starting API Server on port {port}...")
    await server.serve()
