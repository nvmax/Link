from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import os
import json
import tempfile
import aiohttp
from src.core.comfy_parser import parse_node_list, parse_snapshot_list
from src.core.model_extractor import extract_required_models
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
    success, _ = await execute_comfy_command(workspace_path, cmd)
    return success

async def run_comfy_install_deps(workspace_path: str, workflow_path: str) -> bool:
    """Runs 'comfy node deps-in-workflow' and 'comfy node install-deps'"""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        deps_path = tf.name

    try:
        # Step 1: Generate deps
        cmd1 = f'comfy --workspace "{workspace_path}" node deps-in-workflow --workflow "{workflow_path}" --output "{deps_path}"'
        success1, _ = await execute_comfy_command(workspace_path, cmd1)
        if not success1: return False

        # Step 2: Install deps
        cmd2 = f'comfy --workspace "{workspace_path}" --skip-prompt node install-deps "{deps_path}"'
        success2, _ = await execute_comfy_command(workspace_path, cmd2)
        return success2
    finally:
        if os.path.exists(deps_path):
            try: os.unlink(deps_path)
            except: pass

@app.get("/api/comfy/nodes")
async def get_nodes(force: bool = False):
    """Returns list of installed nodes via comfy-cli"""
    try:
        workspace = resolve_comfy_workspace(Config.COMFY_PATH)
        
        # Only force an expensive network sync if explicitly requested via the refresh button
        if force:
            await execute_comfy_command(workspace, f'comfy --workspace "{workspace}" node update-cache')
        
        # Show only installed nodes
        _, output = await execute_comfy_command(workspace, f'comfy --workspace "{workspace}" node show installed')
        nodes = parse_node_list(output)
        
        # Augment with latest version info from ComfyUI Manager cache
        try:
            import glob
            manager_cache = os.path.join(workspace, "user", "__manager", "cache")
            latest_versions = {}
            
            # Read all *_nodes.json files
            for registry_file in glob.glob(os.path.join(manager_cache, "*_nodes.json")):
                with open(registry_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for n in data.get("nodes", []):
                        node_id = n.get("id")
                        latest_ver = n.get("latest_version", {}).get("version")
                        if node_id and latest_ver:
                            latest_versions[node_id] = latest_ver
            
            # Map them back to the CLI output
            import re
            
            def is_newer_version(installed: str, latest: str) -> bool:
                if not installed or not latest: return False
                v1 = installed.lower()
                v2 = latest.lower()
                if v1 in ['unknown', 'nightly'] or v1 == v2: return False
                
                p1 = [int(x) for x in re.findall(r'\d+', v1)]
                p2 = [int(x) for x in re.findall(r'\d+', v2)]
                
                if not p1 or not p2: return False
                
                for a, b in zip(p1, p2):
                    if b > a: return True
                    if a > b: return False
                return len(p2) > len(p1)

            for node in nodes:
                node_id = node.get("name")
                if node_id in latest_versions:
                    node["latest_version"] = latest_versions[node_id]
                    v1 = node.get("version", "").strip()
                    v2 = node.get("latest_version", "").strip()
                    node["update_available"] = is_newer_version(v1, v2)
        except Exception as cache_err:
            logger.warning(f"Failed to parse latest versions from cache: {cache_err}")

        return {"nodes": nodes}
    except Exception as e:
        logger.error(f"Error listing nodes: {e}")
        return {"nodes": [], "error": str(e)}

@app.post("/api/comfy/nodes/update")
async def update_nodes_api(request: Request):
    """Updates selected nodes or all nodes"""
    try:
        body = await request.json()
        target_nodes = body.get("nodes", []) # Empty list means update all
        workspace = resolve_comfy_workspace(Config.COMFY_PATH)
        
        # Auto-backup
        ts = asyncio.get_event_loop().time()
        backup_cmd = f'comfy --workspace "{workspace}" node save-snapshot "auto_pre_update_{int(ts)}"'
        await execute_comfy_command(workspace, backup_cmd)
        
        # Update
        target_str = " ".join(target_nodes) if target_nodes else "all"
        update_cmd = f'comfy --workspace "{workspace}" --skip-prompt node update {target_str}'
        success, _ = await execute_comfy_command(workspace, update_cmd)
        
        return {"success": success}
    except Exception as e:
        logger.error(f"Error updating nodes: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/comfy/snapshots")
async def get_snapshots():
    """Returns list of environment snapshots"""
    try:
        workspace = resolve_comfy_workspace(Config.COMFY_PATH)
        _, output = await execute_comfy_command(workspace, f'comfy --workspace "{workspace}" node show snapshot-list')
        snapshots = parse_snapshot_list(output)
        return {"snapshots": snapshots}
    except Exception as e:
        logger.error(f"Error listing snapshots: {e}")
        return {"snapshots": [], "error": str(e)}

@app.get("/api/comfy/snapshots/{snapshot_id}")
async def get_snapshot_details(snapshot_id: str):
    """Returns content of a specific snapshot"""
    try:
        workspace = resolve_comfy_workspace(Config.COMFY_PATH)
        manager_dir = os.path.join(workspace, "user", "__manager")
        
        # 1. Try common locations first
        common_paths = [
            os.path.join(manager_dir, "snapshots", snapshot_id),
            os.path.join(manager_dir, snapshot_id),
        ]
        
        target_path = None
        for p in common_paths:
            if os.path.exists(p):
                target_path = p
                break
                
        # 2. Fallback: Recursive search (if common ones fail)
        if not target_path:
            for root, dirs, files in os.walk(manager_dir):
                if snapshot_id in files:
                    target_path = os.path.join(root, snapshot_id)
                    break
        
        if not target_path:
            logger.error(f"Snapshot not found: {snapshot_id} in {manager_dir}")
            raise HTTPException(status_code=404, detail=f"Snapshot file '{snapshot_id}' not found")
            
        with open(target_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"Error reading snapshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/comfy/snapshots/restore")
async def restore_snapshot_api(request: Request):
    """Restores a specific snapshot"""
    try:
        body = await request.json()
        snapshot_id = body.get("id")
        if not snapshot_id:
            return {"success": False, "error": "No snapshot ID provided"}
            
        workspace = resolve_comfy_workspace(Config.COMFY_PATH)
        restore_cmd = f'comfy --workspace "{workspace}" --skip-prompt node restore-snapshot "{snapshot_id}"'
        success, _ = await execute_comfy_command(workspace, restore_cmd)
        return {"success": success}
    except Exception as e:
        logger.error(f"Error restoring snapshot: {e}")
        return {"success": False, "error": str(e)}

async def execute_comfy_command(workspace_path: str, cmd: str) -> tuple[bool, str]:
    """Executes a comfy-cli command and returns (success, full_output)"""
    logger.info(f"[comfy-cli] Execute from: {workspace_path}")
    logger.info(f"[comfy-cli] Command: {cmd}")
    
    full_output = []
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    
    # Ensure critical Windows paths are present for wmic and other tools
    system32 = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32")
    wbem = os.path.join(system32, "wbem")
    current_path = env.get("PATH", "")
    if system32 not in current_path:
        env["PATH"] = system32 + os.pathsep + wbem + os.pathsep + current_path

    if workspace_path:
        # Inject paths so cm-cli can find dependencies
        env["PYTHONPATH"] = workspace_path + os.pathsep + env.get("PYTHONPATH", "")
        env["COMFYUI_PATH"] = workspace_path

    process = await asyncio.create_subprocess_shell(
        cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=env,
        cwd=workspace_path if os.path.exists(workspace_path) else None
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
            full_output.append(decoded_line)

    await process.wait()
    return process.returncode == 0, "\n".join(full_output)

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

@app.post("/api/models/check")
async def check_models(request: Request):
    """
    Accepts a ComfyUI workflow JSON body.
    Returns which required model files are missing from the ComfyUI instance.

    Response:
        {
          "required": [{"folder": str, "filename": str, "installed": bool}, ...],
          "missing":  [{"folder": str, "filename": str, "installed": false}, ...]
        }

    If ComfyUI is unreachable, returns empty missing list so import can proceed.
    """
    try:
        workflow = await request.json()
        required = extract_required_models(workflow)
        if not required:
            return {"required": [], "missing": []}

        # Query ComfyUI /models/{folder} for each distinct folder needed
        installed_by_folder: dict[str, set] = {}
        folders_needed = {r["folder"] for r in required}

        try:
            async with aiohttp.ClientSession() as session:
                for folder in folders_needed:
                    try:
                        async with session.get(
                            f"{Config.COMFY_URL}/models/{folder}",
                            timeout=aiohttp.ClientTimeout(total=5)
                        ) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                # ComfyUI returns a flat list of filename strings
                                installed_by_folder[folder] = set(data)
                            else:
                                logger.warning(f"ComfyUI returned {resp.status} for /models/{folder}")
                                installed_by_folder[folder] = set()
                    except Exception as folder_err:
                        logger.warning(f"Could not query ComfyUI /models/{folder}: {folder_err}")
                        installed_by_folder[folder] = set()
        except Exception as session_err:
            logger.warning(f"ComfyUI unreachable during model check: {session_err}")
            # Graceful degradation — treat all as installed so import proceeds
            return {"required": required, "missing": []}

        result = [
            {**item, "installed": item["filename"] in installed_by_folder.get(item["folder"], set())}
            for item in required
        ]
        missing = [r for r in result if not r["installed"]]
        logger.info(f"Model check: {len(required)} required, {len(missing)} missing")
        return {"required": result, "missing": missing}

    except Exception as e:
        logger.error(f"Model check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/models/download")
async def download_model(request: Request):
    """
    Downloads a single model file from HuggingFace into the correct ComfyUI models subfolder.

    Request body:
        {
          "folder":   str,           # e.g. "unet", "vae", "clip"
          "filename": str,           # e.g. "flux1-dev.safetensors"
          "repo_id":  str,           # e.g. "black-forest-labs/FLUX.1-dev"
          "hf_path":  str (optional) # path within the repo; defaults to filename
        }

    Returns:
        200 { "status": "success", "path": str }
        401 { "status": "auth",  "detail": str }  -- missing/invalid HF_TOKEN
        403 { "status": "gated", "repo_url": str } -- user must accept license first
        404 { "status": "not_found", "detail": str }
    """
    try:
        body = await request.json()
        folder   = body.get("folder")
        filename = body.get("filename")
        repo_id  = body.get("repo_id")
        hf_path  = body.get("hf_path") or filename
        hf_token = os.getenv("HF_TOKEN", "").strip()

        if not all([folder, filename, repo_id]):
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: folder, filename, repo_id"
            )

        comfy_workspace = resolve_comfy_workspace(Config.COMFY_PATH)
        dest_dir  = os.path.join(comfy_workspace, "models", folder)
        os.makedirs(dest_dir, exist_ok=True)
        dest_path = os.path.join(dest_dir, filename)

        url = f"https://huggingface.co/{repo_id}/resolve/main/{hf_path}"
        headers: dict = {"User-Agent": "atlas-model-downloader/1.0"}
        if hf_token:
            headers["Authorization"] = f"Bearer {hf_token}"

        logger.info(f"Downloading model: {url} -> {dest_path}")

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=3600),
                allow_redirects=True
            ) as resp:

                if resp.status == 401:
                    from fastapi.responses import JSONResponse
                    return JSONResponse(
                        status_code=401,
                        content={
                            "status": "auth",
                            "detail": (
                                "HuggingFace authentication failed. "
                                "Set your HF_TOKEN in Mission Control → Settings."
                            )
                        }
                    )

                if resp.status == 403:
                    # Gated model — user must accept the license on HuggingFace
                    from fastapi.responses import JSONResponse
                    repo_url = f"https://huggingface.co/{repo_id}"
                    logger.warning(f"Gated model, license required: {repo_url}")
                    return JSONResponse(
                        status_code=403,
                        content={"status": "gated", "repo_url": repo_url}
                    )

                if resp.status == 404:
                    from fastapi.responses import JSONResponse
                    return JSONResponse(
                        status_code=404,
                        content={
                            "status": "not_found",
                            "detail": f"File not found on HuggingFace: {url}"
                        }
                    )

                if resp.status != 200:
                    raise HTTPException(
                        status_code=resp.status,
                        detail=f"HuggingFace returned HTTP {resp.status} for {url}"
                    )

                # Stream to disk in 1 MB chunks
                bytes_written = 0
                with open(dest_path, "wb") as f:
                    async for chunk in resp.content.iter_chunked(1024 * 1024):
                        f.write(chunk)
                        bytes_written += len(chunk)

        logger.info(f"Downloaded {filename} ({bytes_written / 1024 / 1024:.1f} MB) -> {dest_path}")
        return {"status": "success", "path": dest_path, "bytes": bytes_written}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Model download error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
