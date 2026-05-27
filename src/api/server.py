from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
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
from src.api.ai_service import AiService

logger = setup_logger("api_server")

MANUAL_NODE_MAPPING = {
    "AutoMegapixelReducer": "https://github.com/nvmax/aspect-ratio-resizer"
}

app = FastAPI()

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
async def api_key_middleware(request: Request, call_next):
    # Retrieve the API key from config/env
    api_key = Config.API_KEY
    if not api_key:
        return await call_next(request)
        
    path = request.url.path
    if path.startswith("/api/") and request.method != "OPTIONS":
        # Check X-API-Key header or api_key query parameter
        req_key = request.headers.get("x-api-key") or request.query_params.get("api_key")
        if req_key != api_key:
            # Rotation Guard: If key changed in .env and this is /api/config/reload,
            # allow authorizing with the newly saved key so we don't get locked out.
            if path == "/api/config/reload":
                from dotenv import load_dotenv
                load_dotenv(override=True)
                new_key = os.getenv("API_KEY")
                if req_key == new_key:
                    return await call_next(request)
                    
            # Build CORS response headers to ensure browser is not blocked by CORS on a 401 response
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

# We'll store a reference to the bot instance here
bot_instance = None
ai_service = AiService()

# Store active downloads progress: { "filename": { "total": int, "downloaded": int, "status": str } }
active_downloads = {}

@app.get("/api/models/progress")
async def get_download_progress():
    return active_downloads

@app.get("/health")
async def health():
    comfy_connected = False
    if bot_instance and bot_instance.api_client:
        comfy_connected = await bot_instance.api_client.check_connection()
        
    return {
        "status": "ok", 
        "bot_connected": bot_instance is not None and bot_instance.is_ready(),
        "comfy_connected": comfy_connected
    }

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

@app.get("/api/ai/config")
async def get_ai_config():
    return ai_service.load_config().dict()

@app.post("/api/ai/config")
async def save_ai_config(request: Request):
    try:
        data = await request.json()
        ai_service.save_config(data)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ai/prompts")
async def get_ai_prompts():
    return [p.dict() for p in ai_service.load_prompts()]

@app.post("/api/ai/prompts")
async def save_ai_prompts(request: Request):
    try:
        data = await request.json()
        ai_service.save_prompts(data)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/enhance")
async def enhance_prompt(request: Request):
    data = await request.json()
    user_prompt = data.get("prompt")
    system_prompt_id = data.get("system_prompt_id")
    
    if not user_prompt or not system_prompt_id:
        raise HTTPException(status_code=400, detail="Missing prompt or system_prompt_id")
        
    try:
        enhanced = await ai_service.enhance_prompt(user_prompt, system_prompt_id)
        return {"enhanced": enhanced}
    except Exception as e:
        logger.error(f"AI Enhancement failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/test")
async def test_ai_connection():
    try:
        response = await ai_service.test_connection()
        return {"status": "success", "response": response}
    except Exception as e:
        logger.error(f"AI Test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
        if not comfy_path:
            return {"status": "error", "message": "COMFY_PATH not set in .env"}

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

        installed_any = False
        
        # comfy-cli deps-in-workflow ONLY supports WebUI format JSON files.
        # Since the API often provides a dictionary-based API workflow format,
        # we construct a dummy WebUI format workflow from the missing nodes or the API dict.
        dummy_webui = {"nodes": [], "links": []}
        
        if missing_nodes_override:
            logger.info(f"Using {len(missing_nodes_override)} explicit missing nodes to construct dependency dummy...")
            for i, class_name in enumerate(missing_nodes_override):
                dummy_webui["nodes"].append({"id": i, "type": class_name, "pos": [0,0]})
        elif workflow_data:
            logger.info("Scanning workflow API dict to construct dependency dummy...")
            for node_id, node_info in workflow_data.items():
                if isinstance(node_info, dict) and "class_type" in node_info:
                    dummy_webui["nodes"].append({"id": node_id, "type": node_info["class_type"], "pos": [0,0]})
        
        if dummy_webui["nodes"]:
            with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode='w', encoding='utf-8') as tf:
                json.dump(dummy_webui, tf)
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

        return {
            "status": "success", 
            "message": "Nodes installed successfully."
        }
    except Exception as e:
        logger.error(f"Error during node restoration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def run_comfy_install_deps(workspace_path: str, workflow_path: str) -> bool:
    """Runs 'comfy node deps-in-workflow' and 'comfy node install-deps'"""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        deps_path = tf.name

    try:
        # Step 1: Generate deps
        cmd1 = f'comfy --workspace "{workspace_path}" node deps-in-workflow --workflow "{workflow_path}" --output "{deps_path}"'
        success1, _ = await execute_comfy_command(workspace_path, cmd1)
        if not success1: return False

        # Patch dependencies file with any manual node mappings
        if os.path.exists(deps_path):
            try:
                with open(deps_path, 'r', encoding='utf-8') as f:
                    deps_data = json.load(f)
                
                unknowns = deps_data.get("unknown_nodes", [])
                customs = deps_data.setdefault("custom_nodes", {})
                
                updated = False
                for node in list(unknowns):
                    if node in MANUAL_NODE_MAPPING:
                        repo_url = MANUAL_NODE_MAPPING[node]
                        customs[repo_url] = {"state": "not-installed"}
                        unknowns.remove(node)
                        updated = True
                
                if updated:
                    logger.info(f"Patched deps.json, mapped nodes: {list(MANUAL_NODE_MAPPING.keys())}")
                    with open(deps_path, 'w', encoding='utf-8') as f:
                        json.dump(deps_data, f, indent=2)
            except Exception as e:
                logger.error(f"Failed to patch deps.json: {e}")

        # Step 2: Install deps
        cmd2 = f'comfy --workspace "{workspace_path}" --skip-prompt node install-deps --deps "{deps_path}"'
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
    # Locate embedded python if possible to run commands in the correct env
    python_exe = None
    if workspace_path and os.name == 'nt':
        p_root = workspace_path.replace("/", os.sep).rstrip(os.sep)
        if os.path.exists(os.path.join(p_root, "python_embeded")):
            pass
        elif os.path.exists(os.path.join(os.path.dirname(p_root), "python_embeded")):
            p_root = os.path.dirname(p_root)
        elif os.path.basename(p_root).lower() == "comfyui":
            p_root = os.path.dirname(p_root)
        
        embed_py = os.path.join(p_root, "python_embeded", "python.exe")
        if os.path.exists(embed_py):
            python_exe = embed_py

    if python_exe and cmd.startswith("comfy"):
        # Translate to cm_cli execution using the embedded python interpreter
        import shlex
        try:
            parts = shlex.split(cmd)
            cmd_parts = []
            i = 1
            while i < len(parts):
                part = parts[i]
                if part == "--workspace":
                    i += 2
                elif part == "--skip-prompt":
                    i += 1
                elif part == "node":
                    i += 1
                elif part == "--deps":
                    i += 1
                else:
                    if ' ' in part or '\\' in part or '/' in part or '"' in part:
                        escaped = part.replace('"', '\\"')
                        cmd_parts.append(f'"{escaped}"')
                    else:
                        cmd_parts.append(part)
                    i += 1
            cmd = f'"{python_exe}" -m cm_cli {" ".join(cmd_parts)}'
        except Exception as e:
            logger.warning(f"Failed to translate comfy command: {e}")

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

    if os.name != 'nt':
        # Create symlinks to cm_cli and comfyui_manager from the mounted volume if present
        try:
            links_dir = "/app/comfy_links"
            os.makedirs(links_dir, exist_ok=True)
            
            src_cm_cli = "/comfyui/python_embeded/Lib/site-packages/cm_cli"
            src_manager = "/comfyui/python_embeded/Lib/site-packages/comfyui_manager"
            
            dest_cm_cli = os.path.join(links_dir, "cm_cli")
            dest_manager = os.path.join(links_dir, "comfyui_manager")
            
            if os.path.exists(src_cm_cli) and not os.path.exists(dest_cm_cli):
                os.symlink(src_cm_cli, dest_cm_cli)
                logger.info(f"Created symlink for cm_cli: {dest_cm_cli} -> {src_cm_cli}")
            if os.path.exists(src_manager) and not os.path.exists(dest_manager):
                os.symlink(src_manager, dest_manager)
                logger.info(f"Created symlink for comfyui_manager: {dest_manager} -> {src_manager}")
                
            current_pythonpath = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = links_dir + (os.pathsep + current_pythonpath if current_pythonpath else "")
        except Exception as e:
            logger.warning(f"Failed to setup comfy_links symlinks: {e}")

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

def resolve_comfy_workspace(base_path: str):
    if not base_path: return ""
    base_path = base_path.replace("/", os.sep).rstrip(os.sep)
    if os.path.exists(os.path.join(base_path, "main.py")): return base_path
    subfolder = os.path.join(base_path, "ComfyUI")
    if os.path.exists(os.path.join(subfolder, "main.py")): return subfolder
    
    # Case-insensitive/renamed subfolder fallback search for main.py
    try:
        if os.path.isdir(base_path):
            for name in os.listdir(base_path):
                p = os.path.join(base_path, name)
                if os.path.isdir(p) and os.path.exists(os.path.join(p, "main.py")):
                    return p
    except Exception:
        pass
        
    return base_path

@app.post("/api/comfy/reboot")
async def reboot_comfy():
    """
    Tells ComfyUI to reboot (requires ComfyUI-Manager).
    """
    try:
        async with aiohttp.ClientSession() as session:
            # Prioritize the paths confirmed by the user's manual script
            paths = ["/v2/manager/reboot", "/manager/reboot", "/api/manager/reboot", "/reboot"]
            methods = ["POST", "GET"]
            
            for path in paths:
                url = f"{Config.COMFY_URL}{path}"
                for method in methods:
                    try:
                        # We use a short timeout because a successful reboot often cuts the connection
                        async with session.request(method, url, timeout=3) as resp:
                            if resp.status == 200:
                                return {"status": "success", "message": f"Reboot accepted ({method} {path})"}
                    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                        # If the connection is reset or timed out immediately after the request, 
                        # it almost certainly means the server is shutting down to reboot.
                        logger.info(f"Reboot likely successful (connection reset/timeout): {e}")
                        return {"status": "success", "message": "Reboot triggered successfully."}
            
            return {"status": "error", "message": "Could not verify reboot command was accepted."}
    except Exception as e:
        logger.error(f"Reboot handler error: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/api/bot/restart")
async def restart_bot():
    """
    Restarts the entire bot process (Discord bot + API server) by replacing
    the current process with a fresh Python execution of the same entry point.

    This is needed after importing a new workflow so that the new slash
    command is registered with Discord and becomes available immediately.

    The response is returned *before* the restart begins (0.5 s delay).
    """
    import sys

    async def _do_restart():
        await asyncio.sleep(0.5)
        logger.info("Bot restart initiated via /api/bot/restart")
        # Replace the current process with a fresh copy of itself.
        # os.execv() does not return — all existing state is wiped.
        os.execv(sys.executable, [sys.executable] + sys.argv)

    asyncio.create_task(_do_restart())
    return {"status": "success", "message": "Bot is restarting. It will be back online in a few seconds."}

@app.post("/api/models/check")
async def check_models(request: Request):
    """
    Accepts a ComfyUI workflow JSON body.
    Returns which required model files are missing from the ComfyUI instance.

    Strategy
    --------
    Phase 1 – ComfyUI /prompt validation (preferred)
        POST the workflow directly to ComfyUI's /prompt endpoint.
        ComfyUI validates it against its own model scanner and returns
        node_errors for any missing files.  This requires zero folder-mapping
        heuristics — ComfyUI is the source of truth.

        If validation passes (all models present), the queued prompt is
        cancelled immediately so nothing actually runs.

    Phase 2 – Local filesystem fallback
        Used only when ComfyUI is unreachable.  Falls back to the
        extract_required_models() heuristic + disk check.

    Response:
        {
          "required": [{"folder": str, "filename": str, "installed": bool}, ...],
          "missing":  [{"folder": str, "filename": str, "installed": false}, ...]
        }
    """
    try:
        workflow = await request.json()
        comfy_url = Config.COMFY_URL

        # ── Phase 1: ask ComfyUI directly ────────────────────────────────────
        missing = await _check_models_via_comfy_validation(workflow, comfy_url)
        if missing is not None:
            # ComfyUI was reachable — trust its answer completely.
            logger.info(f"Model check (ComfyUI validation): {len(missing)} missing")
            return {"required": missing, "missing": [m for m in missing if not m["installed"]]}

        # ── Phase 2: filesystem fallback (ComfyUI offline) ───────────────────
        logger.warning("ComfyUI unreachable for model check — falling back to heuristic extractor")
        required = extract_required_models(workflow)
        if not required:
            return {"required": [], "missing": []}

        comfy_workspace = resolve_comfy_workspace(Config.COMFY_PATH)
        result = []
        for item in required:
            disk_path = os.path.join(comfy_workspace or "", "models", item["folder"], item["filename"])
            is_installed = bool(comfy_workspace and os.path.isfile(disk_path))
            result.append({**item, "installed": is_installed})

        missing_list = [r for r in result if not r["installed"]]
        logger.info(f"Model check (fallback): {len(required)} required, {len(missing_list)} missing")
        return {"required": result, "missing": missing_list}

    except Exception as e:
        logger.error(f"Model check error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def _check_models_via_comfy_validation(workflow: dict, comfy_url: str) -> list[dict] | None:
    """
    Posts *workflow* to ComfyUI's /prompt endpoint for synchronous validation.

    Returns
    -------
    list[dict]
        A flat list of all model inputs found in the workflow, each with an
        "installed" flag.  Missing items are those ComfyUI reported in
        node_errors.  Returns None if ComfyUI is unreachable.

    How it works
    ------------
    ComfyUI validates inputs against its own scanned models directory before
    queuing.  If any model file is absent it returns node_errors without
    queueing anything.  If all models are present the prompt is queued;
    we cancel it immediately via DELETE /queue.

    The node_errors structure per missing model:
        {
          "type": "value_not_in_list",
          "extra_info": {
            "input_name": "clip_name1",           # field name
            "input_config": [["a.gguf", "b.safetensors"], {}],  # available files
            "received_value": "gemma-3-12b-it-Q4_1.gguf"       # what was requested
          }
        }

    We cross-reference with our extractor to infer the folder, but ComfyUI
    determines whether the file is actually present — no heuristics for that.
    """
    import uuid
    validation_client_id = str(uuid.uuid4())
    payload = {"prompt": workflow, "client_id": validation_client_id}

    try:
        async with aiohttp.ClientSession() as session:
            # POST to /prompt — ComfyUI validates synchronously
            async with session.post(
                f"{comfy_url}/prompt",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                data = await resp.json()

        node_errors: dict = data.get("node_errors", {})
        prompt_id: str | None = data.get("prompt_id")

        # If the prompt was queued (validation passed), cancel it immediately
        if prompt_id and not node_errors:
            try:
                async with aiohttp.ClientSession() as session:
                    await session.post(
                        f"{comfy_url}/queue",
                        json={"delete": [prompt_id]},
                        timeout=aiohttp.ClientTimeout(total=5)
                    )
                logger.info(f"Model check: all models present (queued {prompt_id} cancelled)")
            except Exception:
                pass  # Non-fatal — job will sit idle until something else runs it
            return []  # Nothing missing

        # Parse node_errors to extract missing filenames
        # Build a lookup of node_id -> node data from the workflow for folder resolution
        missing_filenames: dict[str, dict] = {}  # filename -> {"folder": str, "field": str, "node_class": str}

        # Pre-compute our extractor's view so we can match folders
        extractor_map: dict[str, str] = {}  # filename -> folder
        for item in extract_required_models(workflow):
            extractor_map[item["filename"]] = item["folder"]

        for node_id, node_err in node_errors.items():
            node_class = node_err.get("class_type", "")
            for err in node_err.get("errors", []):
                if err.get("type") != "value_not_in_list":
                    continue
                extra = err.get("extra_info", {})
                field_name: str = extra.get("input_name", "")
                missing_file: str = extra.get("received_value", "")
                if not missing_file or not isinstance(missing_file, str):
                    continue
                # Infer folder: prefer our extractor's answer, fall back to field name
                folder = extractor_map.get(missing_file, "")
                if not folder:
                    # Ask our field-name semantics helper
                    from src.core.model_extractor import _folder_from_field_name
                    folder = _folder_from_field_name(field_name) or "models"
                missing_filenames[missing_file] = {
                    "folder": folder,
                    "filename": missing_file,
                    "installed": False,
                    "node_class": node_class,
                    "field": field_name,
                }
                logger.info(
                    f"Model check: missing '{missing_file}' "
                    f"(node {node_id} / {node_class} / field {field_name}) → {folder}/"
                )

        # Build required list: missing ones + all others (marked installed=True)
        all_required = extract_required_models(workflow)
        result = []
        for item in all_required:
            fname = item["filename"]
            if fname in missing_filenames:
                result.append(missing_filenames[fname])
            else:
                result.append({**item, "installed": True})

        # Also include any missing items not caught by our extractor
        for fname, info in missing_filenames.items():
            if not any(r["filename"] == fname for r in result):
                result.append(info)

        return result

    except aiohttp.ClientConnectorError:
        logger.warning("ComfyUI unreachable for model validation")
        return None
    except asyncio.TimeoutError:
        logger.warning("ComfyUI model validation timed out")
        return None
    except Exception as e:
        logger.warning(f"ComfyUI model validation failed: {e}")
        return None




MODEL_SEARCH_CACHE = {}

@app.post("/api/models/search")
async def search_models(request: Request):
    """
    Accepts a list of filenames and searches HuggingFace for the best matching repo.
    Uses pre-seeded known ComfyUI model repositories and an in-memory cache to stay robust against 429 rate limits.
    Returns: {"results": {"filename": "repo_id", ...}}
    """
    import re
    import urllib.parse
    import asyncio
    try:
        body = await request.json()
        filenames = body.get("filenames", [])
        
        results = {}
        # Preseeded popular ComfyUI model repositories by family
        preseeded_by_family = {
            "ltx": {
                "Comfy-Org/ltx-2",
                "Kijai/LTX2.3_comfy",
                "Lightricks/LTX-2.3"
            },
            "flux": {
                "black-forest-labs/FLUX.1-dev",
                "black-forest-labs/FLUX.1-schnell",
                "Kijai/flux-fp8",
                "comfyanonymous/flux_flux8_repack"
            },
            "wan": {
                "Kijai/Wan2.1_comfy",
                "Comfy-Org/Wan2.1-ComfyUI",
                "comfyanonymous/wan2.1_repack"
            },
            "sd": {
                "stabilityai/stable-diffusion-3.5-large",
                "Comfy-Org/stable-diffusion-3.5-fp8",
                "stabilityai/stable-diffusion-xl-base-1.0",
                "runwayml/stable-diffusion-v1-5"
            }
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        }
        async with aiohttp.ClientSession(headers=headers) as session:
            for filename in filenames:
                if filename in MODEL_SEARCH_CACHE:
                    logger.info(f"[cache] Resolved {filename} to {MODEL_SEARCH_CACHE[filename]} from memory cache.")
                    results[filename] = MODEL_SEARCH_CACHE[filename]
                    continue
                
                # 1. First try exact filename search (the original logic)
                exact_url = f"https://huggingface.co/api/search/full-text?q={urllib.parse.quote(filename)}&type=model"
                found_repo = None
                try:
                    async with session.get(exact_url, timeout=5) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            hits = data.get("hits", [])
                            if hits:
                                hits.sort(key=lambda x: x.get("likes", 0), reverse=True)
                                for hit in hits[:5]:
                                    repo_name = hit.get("name")
                                    if not repo_name: continue
                                    check_url = f"https://huggingface.co/{repo_name}/resolve/main/{filename}"
                                    try:
                                        async with session.head(check_url, timeout=3, allow_redirects=True) as check_resp:
                                            if check_resp.status == 200:
                                                found_repo = repo_name
                                                break
                                    except Exception:
                                        pass
                        elif resp.status == 429:
                            logger.warning(f"Exact search hit HuggingFace 429 rate limit for {filename}")
                except Exception as e:
                    logger.warning(f"Exact search HTTP error for {filename}: {e}")

                if found_repo:
                    results[filename] = found_repo
                    MODEL_SEARCH_CACHE[filename] = found_repo
                    continue

                # 2. Relaxed/Dynamic Resolution fallback
                logger.info(f"Exact search failed or rate-limited for {filename}. Running relaxed dynamic HuggingFace search...")
                stem = filename.rsplit('.', 1)[0]
                tokens = re.split(r'[-_]', stem)
                tokens = [t.strip() for t in tokens if t.strip()]
                
                queries = []
                if len(tokens) >= 1:
                    queries.append(tokens[0])
                if len(tokens) >= 2:
                    queries.append(f"{tokens[0]} {tokens[1]}")
                if len(tokens) >= 3:
                    queries.append(f"{tokens[0]} {tokens[1]} {tokens[2]}")
                queries.append(stem.replace('_', ' ').replace('-', ' '))
                
                filename_lower = filename.lower()
                family = "other"
                if "ltx" in filename_lower or "gemma" in filename_lower:
                    family = "ltx"
                elif "flux" in filename_lower:
                    family = "flux"
                elif "wan" in filename_lower:
                    family = "wan"
                elif "stable-diffusion" in filename_lower or "sd" in filename_lower or "sdxl" in filename_lower:
                    family = "sd"
                
                family_repos = preseeded_by_family.get(family, set())
                candidate_repos = set(family_repos)
                keyword_repos = set()
                
                # Fetch query-based search candidates
                for q in queries:
                    q_quoted = urllib.parse.quote(q)
                    # Standard API search
                    url_std = f"https://huggingface.co/api/models?search={q_quoted}&limit=40"
                    try:
                        async with session.get(url_std, timeout=5) as resp:
                            if resp.status == 200:
                                repos = await resp.json()
                                for r in repos:
                                    if isinstance(r, dict) and r.get("id"):
                                        candidate_repos.add(r.get("id"))
                                        keyword_repos.add(r.get("id"))
                            elif resp.status == 429:
                                logger.warning(f"url_std hit HF 429 for query '{q}'")
                    except Exception as e:
                        logger.warning(f"url_std error: {e}")
                        
                    # Full text search
                    url_ft = f"https://huggingface.co/api/search/full-text?q={q_quoted}&type=model&limit=40"
                    try:
                        async with session.get(url_ft, timeout=5) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                hits = data.get("hits", [])
                                for h in hits:
                                    if isinstance(h, dict) and h.get("name"):
                                        candidate_repos.add(h.get("name"))
                                        keyword_repos.add(h.get("name"))
                            elif resp.status == 429:
                                logger.warning(f"url_ft hit HF 429 for query '{q}'")
                    except Exception as e:
                        logger.warning(f"url_ft error: {e}")

                 # Prioritize candidate repos
                def get_repo_priority(repo_name):
                    score = 0
                    if repo_name in family_repos:
                        score += 100  # Massive boost for our curated, gold-standard family repositories
                        
                    repo_lower = repo_name.lower()
                    if "comfy-org" in repo_lower:
                        score += 50  # Absolute top priority for official ComfyUI repackaged models
                    elif "kijai" in repo_lower:
                        score += 40  # Extreme priority for Kijai (most popular ComfyUI porter)
                    elif "comfy" in repo_lower:
                        score += 30
                    elif "lightricks" in repo_lower:
                        score += 20
                    elif "black-forest-labs" in repo_lower:
                        score += 20
                    elif "stabilityai" in repo_lower:
                        score += 20
                    
                    if repo_name in keyword_repos:
                        score += 15  # Good bonus for keyword-matched repositories
                        
                    for t in tokens[:3]:
                        if t.lower() in repo_lower:
                            score += 3
                    return score

                sorted_candidates = sorted(list(candidate_repos), key=get_repo_priority, reverse=True)
                
                # Check candidates in parallel for existence of target file with concurrency limit of 5
                sem = asyncio.Semaphore(5)
                
                async def check_candidate(repo_id):
                    async with sem:
                        # Method A: Check API metadata page (lists siblings)
                        repo_api_url = f"https://huggingface.co/api/models/{repo_id}"
                        try:
                            async with session.get(repo_api_url, timeout=4) as resp:
                                if resp.status == 200:
                                    model_info = await resp.json()
                                    siblings = model_info.get("siblings", [])
                                    matches = [s.get("rfilename") for s in siblings if s.get("rfilename") == filename or s.get("rfilename", "").endswith(f"/{filename}")]
                                    if matches:
                                        logger.info(f"Concurrently resolved {filename} to {repo_id} via siblings metadata match!")
                                        return repo_id
                                elif resp.status == 429:
                                    logger.warning(f"check_candidate siblings api hit HF 429 for {repo_id}")
                        except Exception:
                            pass
                            
                        # Method B: HEAD checks (Root & Standard ComfyUI Subfolders)
                        subpaths = [
                            f"{filename}",
                            f"diffusion_models/{filename}",
                            f"text_encoders/{filename}",
                            f"unet/{filename}",
                            f"vae/{filename}",
                            f"loras/{filename}"
                        ]
                        for subpath in subpaths:
                            check_url = f"https://huggingface.co/{repo_id}/resolve/main/{subpath}"
                            try:
                                async with session.head(check_url, timeout=3, allow_redirects=True) as resp:
                                    if resp.status == 200:
                                        logger.info(f"Concurrently resolved {filename} to {repo_id} via HEAD resolve match at '{subpath}'!")
                                        return repo_id
                                    elif resp.status == 429:
                                        logger.warning(f"check_candidate HEAD resolve check hit HF 429 for {repo_id} at {subpath}")
                            except Exception:
                                pass
                        return None

                tasks = [check_candidate(rid) for rid in sorted_candidates[:5]]
                completed_results = await asyncio.gather(*tasks)
                
                # The first non-None result in completed_results matches the highest priority repository
                for res in completed_results:
                    if res:
                        found_repo = res
                        break

                results[filename] = found_repo
                MODEL_SEARCH_CACHE[filename] = found_repo

        return {"results": results}
    except Exception as e:
        logger.error(f"Search models error: {e}")
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
        hf_token = os.getenv("HF_TOKEN", "").strip()
        hf_path  = body.get("hf_path")

        if not folder or not filename:
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: folder, filename"
            )

        url = ""
        headers: dict = {"User-Agent": "atlas-model-downloader/1.0"}

        if repo_id and repo_id.startswith("http"):
            url = repo_id # Direct URL download
        else:
            if not repo_id:
                raise HTTPException(status_code=400, detail="Missing repo_id or direct url")

            if not hf_path:
                try:
                    def get_repo_files():
                        from huggingface_hub import HfApi
                        return HfApi(token=hf_token).list_repo_files(repo_id=repo_id)
                    
                    files = await asyncio.to_thread(get_repo_files)
                    matches = [f for f in files if f == filename or f.endswith(f"/{filename}")]
                    if matches:
                        hf_path = matches[0]
                        logger.info(f"Auto-discovered {filename} at {hf_path} in {repo_id}")
                    else:
                        hf_path = filename
                except Exception as e:
                    logger.warning(f"Failed to list repo files for {repo_id}: {e}")
                    hf_path = filename

            url = f"https://huggingface.co/{repo_id}/resolve/main/{hf_path}"
            if hf_token:
                headers["Authorization"] = f"Bearer {hf_token}"

        comfy_workspace = resolve_comfy_workspace(Config.COMFY_PATH)
        dest_dir  = os.path.join(comfy_workspace, "models", folder)
        os.makedirs(dest_dir, exist_ok=True)
        dest_path = os.path.join(dest_dir, filename)

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
                total_bytes = int(resp.headers.get("Content-Length", 0))
                
                active_downloads[filename] = {
                    "total": total_bytes,
                    "downloaded": 0,
                    "status": "downloading"
                }

                try:
                    with open(dest_path, "wb") as f:
                        async for chunk in resp.content.iter_chunked(1024 * 1024):
                            f.write(chunk)
                            bytes_written += len(chunk)
                            active_downloads[filename]["downloaded"] = bytes_written
                    active_downloads[filename]["status"] = "done"
                except Exception as stream_err:
                    active_downloads[filename]["status"] = "error"
                    raise stream_err

        logger.info(f"Downloaded {filename} ({bytes_written / 1024 / 1024:.1f} MB) -> {dest_path}")
        return {"status": "success", "path": dest_path, "bytes": bytes_written}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Model download error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/comfy/setup")
async def setup_comfyui(request: Request):
    """
    Full ComfyUI setup:
      1. Install ComfyUI Manager requirements via embedded Python
      2. Install SageAttention wheel from src/files
      3. Patch run_nvidia_gpu.bat with --use-sage-attention --enable-manager
    """
    # Always re-read COMFY_PATH directly from .env at call time so we pick up
    # any changes saved via the dashboard without needing a bot restart.
    from dotenv import load_dotenv
    load_dotenv(override=True)
    comfy_base = os.getenv("COMFY_PATH", "").rstrip("/\\")

    if not comfy_base:
        raise HTTPException(status_code=400, detail="COMFY_PATH not set in .env")

    # Normalise to the *portable root* and *workspace* using robust filesystem resolution
    comfy_base = comfy_base.replace("/", os.sep)
    
    # Resolve portable_root (must contain python_embeded)
    if os.path.exists(os.path.join(comfy_base, "python_embeded")):
        portable_root = comfy_base
    elif os.path.exists(os.path.join(os.path.dirname(comfy_base), "python_embeded")):
        portable_root = os.path.dirname(comfy_base)
    elif os.path.basename(comfy_base).lower() == "comfyui":
        portable_root = os.path.dirname(comfy_base)
    else:
        portable_root = comfy_base

    python_exe  = os.path.join(portable_root, "python_embeded", "python.exe")
    bat_file    = os.path.join(portable_root, "run_nvidia_gpu.bat")

    # Resolve path to the Atlas src/files directory (holds bundled wheels)
    atlas_root  = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    files_dir   = os.path.join(atlas_root, "src", "files")

    steps = []

    # ── Step 0: Clone ComfyUI-Manager if missing ─────────────────────────────
    comfy_workspace = resolve_comfy_workspace(comfy_base)
    custom_nodes_dir = os.path.join(comfy_workspace, "custom_nodes")
    manager_dir = os.path.join(custom_nodes_dir, "ComfyUI-Manager")
    kjnodes_dir = os.path.join(custom_nodes_dir, "ComfyUI-KJNodes")
    
    clone_success = True
    clone_output = "ComfyUI-Manager is already installed."
    
    if not os.path.exists(manager_dir):
        logger.info(f"[setup] Git cloning ComfyUI-Manager into: {custom_nodes_dir}")
        try:
            os.makedirs(custom_nodes_dir, exist_ok=True)
            clone_cmd = 'git clone https://github.com/Comfy-Org/ComfyUI-Manager.git'
            proc_clone = await asyncio.create_subprocess_shell(
                clone_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=custom_nodes_dir
            )
            out_clone_bytes, _ = await proc_clone.communicate()
            clone_output = out_clone_bytes.decode("utf-8", errors="replace")
            clone_success = proc_clone.returncode == 0
            logger.info(f"[setup] Git clone exit={proc_clone.returncode}")
        except Exception as clone_err:
            clone_success = False
            clone_output = f"Git clone failed: {clone_err}"
            logger.error(f"[setup] {clone_output}")

    steps.append({"step": "clone_manager", "success": clone_success, "output": clone_output})

    # ── Step 0.5: Clone ComfyUI-KJNodes if missing ───────────────────────────
    clone_kj_success = True
    clone_kj_output = "ComfyUI-KJNodes is already installed."
    
    if not os.path.exists(kjnodes_dir):
        logger.info(f"[setup] Git cloning ComfyUI-KJNodes into: {custom_nodes_dir}")
        try:
            os.makedirs(custom_nodes_dir, exist_ok=True)
            clone_kj_cmd = 'git clone https://github.com/kijai/ComfyUI-KJNodes.git'
            proc_clone_kj = await asyncio.create_subprocess_shell(
                clone_kj_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=custom_nodes_dir
            )
            out_clone_kj_bytes, _ = await proc_clone_kj.communicate()
            clone_kj_output = out_clone_kj_bytes.decode("utf-8", errors="replace")
            clone_kj_success = proc_clone_kj.returncode == 0
            logger.info(f"[setup] KJNodes Git clone exit={proc_clone_kj.returncode}")
        except Exception as clone_err:
            clone_kj_success = False
            clone_kj_output = f"Git clone failed: {clone_err}"
            logger.error(f"[setup] {clone_kj_output}")

    steps.append({"step": "clone_kjnodes", "success": clone_kj_success, "output": clone_kj_output})

    # ── Step 1: ComfyUI Manager requirements ─────────────────────────────────
    if not os.path.exists(python_exe):
        raise HTTPException(status_code=400, detail=f"python_embeded not found at: {python_exe}")

    # Gather any requirements files that exist
    req_files = []
    
    # 1. Check for legacy/portable manager_requirements.txt
    legacy_req = os.path.join(comfy_workspace, "manager_requirements.txt")
    if os.path.exists(legacy_req):
        req_files.append(legacy_req)
        
    # 2. Check for ComfyUI-Manager custom node requirements.txt
    cloned_req = os.path.join(manager_dir, "requirements.txt")
    if os.path.exists(cloned_req):
        req_files.append(cloned_req)
        
    # 3. Check for ComfyUI-KJNodes custom node requirements.txt
    kjnodes_req = os.path.join(kjnodes_dir, "requirements.txt")
    if os.path.exists(kjnodes_req):
        req_files.append(kjnodes_req)
        
    if not req_files:
        raise HTTPException(status_code=400, detail="No ComfyUI Manager or KJNodes requirements file was found.")

    # Install all resolved requirements files
    outputs = []
    success1 = True
    for req in req_files:
        cmd1 = f'"{python_exe}" -m pip install -r "{req}"'
        logger.info(f"[setup] Running: {cmd1}")
        proc1 = await asyncio.create_subprocess_shell(
            cmd1,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=portable_root
        )
        out1_bytes, _ = await proc1.communicate()
        out1 = out1_bytes.decode("utf-8", errors="replace")
        outputs.append(f"=== Installed {os.path.basename(os.path.dirname(req)) or 'ComfyUI'}/{os.path.basename(req)} ===\n" + out1[-1000:])
        if proc1.returncode != 0:
            success1 = False

    steps.append({"step": "comfyui_manager", "success": success1, "output": "\n\n".join(outputs)})
    logger.info(f"[setup] Manager install success={success1}")

    # ── Step 2: SageAttention — detect Python version, pick matching wheel ────
    # Run python --version to get the exact version (e.g. "Python 3.13.2")
    ver_proc = await asyncio.create_subprocess_shell(
        f'"{python_exe}" --version',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=portable_root
    )
    ver_bytes, _ = await ver_proc.communicate()
    py_version_str = ver_bytes.decode("utf-8", errors="replace").strip()  # e.g. "Python 3.13.2"
    logger.info(f"[setup] Embedded Python: {py_version_str}")

    # Build the cp-tag (e.g. 3.13 → "cp313", 3.12 → "cp312")
    import re as _re
    ver_match = _re.search(r"Python (\d+)\.(\d+)", py_version_str, _re.IGNORECASE)
    py_tag = f"cp{ver_match.group(1)}{ver_match.group(2)}" if ver_match else None

    # Scan src/files for a sageattention wheel that matches the detected tag
    matched_whl = None
    if py_tag and os.path.isdir(files_dir):
        for fname in sorted(os.listdir(files_dir)):
            if fname.lower().startswith("sageattention") and fname.endswith(".whl") and py_tag in fname:
                matched_whl = os.path.join(files_dir, fname)
                break

    if matched_whl:
        logger.info(f"[setup] Installing: {os.path.basename(matched_whl)}")
        cmd2 = f'"{python_exe}" -m pip install "{matched_whl}"'
        proc2 = await asyncio.create_subprocess_shell(
            cmd2,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=portable_root
        )
        out2_bytes, _ = await proc2.communicate()
        out2 = out2_bytes.decode("utf-8", errors="replace")
        msg2 = f"[{py_version_str}] Wheel: {os.path.basename(matched_whl)}\n" + out2[-2000:]
        steps.append({"step": "sage_attention", "success": proc2.returncode == 0, "output": msg2})
        logger.info(f"[setup] SageAttention exit={proc2.returncode}")
    else:
        available = [
            f for f in os.listdir(files_dir)
            if f.lower().startswith("sageattention") and f.endswith(".whl")
        ] if os.path.isdir(files_dir) else []
        msg2 = (
            f"[{py_version_str}] No bundled wheel found for tag '{py_tag}'.\n"
            f"Available in src/files:\n" + "\n".join(f"  • {f}" for f in available) +
            ("\n\nAdd the matching wheel to src/files/ and try again." if available else "\n\nNo sageattention wheels found in src/files/.")
        )
        steps.append({"step": "sage_attention", "success": False, "output": msg2})
        logger.warning(f"[setup] No SageAttention wheel for {py_tag} in {files_dir}")


    # ── Step 3: Triton ────────────────────────────────────────────────────────
    # Check src/files for a bundled triton wheel first; fall back to pip install
    triton_whl = None
    if py_tag and os.path.isdir(files_dir):
        for fname in sorted(os.listdir(files_dir)):
            if fname.lower().startswith("triton") and fname.endswith(".whl") and py_tag in fname:
                triton_whl = os.path.join(files_dir, fname)
                break

    if triton_whl:
        logger.info(f"[setup] Installing triton from bundled wheel: {os.path.basename(triton_whl)}")
        cmd3 = f'"{python_exe}" -m pip install "{triton_whl}"'
    else:
        logger.info("[setup] No bundled triton wheel found — installing triton-windows from PyPI")
        cmd3 = f'"{python_exe}" -m pip install triton-windows'

    proc3 = await asyncio.create_subprocess_shell(
        cmd3,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=portable_root
    )
    out3_bytes, _ = await proc3.communicate()
    out3 = out3_bytes.decode("utf-8", errors="replace")
    source3 = os.path.basename(triton_whl) if triton_whl else "triton-windows (PyPI)"
    msg3 = f"[{py_version_str}] Source: {source3}\n" + out3[-2000:]
    steps.append({"step": "triton", "success": proc3.returncode == 0, "output": msg3})
    logger.info(f"[setup] Triton install exit={proc3.returncode}")

    # ── Step 3.5: Extra Packages (numba, gguf, cv2) ──────────────────────────
    logger.info("[setup] Installing extra packages: numba, gguf, opencv-python...")
    cmd_extra = f'"{python_exe}" -m pip install numba gguf opencv-python'
    proc_extra = await asyncio.create_subprocess_shell(
        cmd_extra,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=portable_root
    )
    out_extra_bytes, _ = await proc_extra.communicate()
    out_extra = out_extra_bytes.decode("utf-8", errors="replace")
    msg_extra = f"[{py_version_str}] Extra Packages:\n" + out_extra[-2000:]
    steps.append({"step": "extra_packages", "success": proc_extra.returncode == 0, "output": msg_extra})
    logger.info(f"[setup] Extra packages install exit={proc_extra.returncode}")

    manager_arg = "--enable-manager-legacy-ui"
    try:
        body = await request.json()
        if body and "manager_type" in body:
            manager_arg = body["manager_type"]
    except Exception:
        pass

    # ── Step 4: Patch run_nvidia_gpu.bat ─────────────────────────────────────
    bat_patched = False
    bat_message = ""
    ws_rel = os.path.relpath(comfy_workspace, portable_root).replace("/", "\\").replace("\\\\", "\\")
    desired_line = f".\\python_embeded\\python.exe -s {ws_rel}\\main.py --windows-standalone-build --use-sage-attention {manager_arg}"
    new_bat_content = desired_line + "\necho \npause\n"

    try:
        if os.path.exists(bat_file):
            with open(bat_file, "r", encoding="utf-8", errors="replace") as f:
                existing = f.read()
            # Only rewrite if we need to (idempotent)
            if "--use-sage-attention" in existing and manager_arg in existing:
                bat_patched = True
                bat_message = f"Already patched with {manager_arg} – no changes made."
            else:
                with open(bat_file, "w", encoding="utf-8") as f:
                    f.write(new_bat_content)
                bat_patched = True
                bat_message = f"Patched with {manager_arg} successfully."
        else:
            # Create the bat file
            with open(bat_file, "w", encoding="utf-8") as f:
                f.write(new_bat_content)
            bat_patched = True
            bat_message = f"Created new run_nvidia_gpu.bat with {manager_arg}."
    except Exception as bat_err:
        bat_message = f"Error patching bat: {bat_err}"

    steps.append({"step": "patch_bat", "success": bat_patched, "output": bat_message})
    logger.info(f"[setup] Bat patch: {bat_message}")

    overall_success = all(s["success"] for s in steps)
    return {"success": overall_success, "steps": steps}


@app.post("/api/utils/select-folder")
async def select_folder():
    """Opens a native folder selection dialog and returns the path, safely falling back on headless environments."""
    # Check if a graphical user interface (display) is available
    has_display = True
    if os.name != 'nt' and not os.environ.get('DISPLAY'):
        has_display = False

    if not has_display:
        logger.warning("[select-folder] Headless environment detected (no DISPLAY). Skipping native folder dialog.")
        return {
            "path": "",
            "error": "Headless environment detected. Please type or paste the ComfyUI workspace folder path manually."
        }

    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        logger.warning("[select-folder] tkinter components are not available on this platform.")
        return {
            "path": "",
            "error": "Tkinter GUI components not available on this system. Please input the path manually."
        }

    def get_path():
        try:
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            path = filedialog.askdirectory()
            root.destroy()
            return path
        except Exception as e:
            logger.error(f"[select-folder] Tkinter failed to open graphical dialog: {e}")
            return ""

    path = await asyncio.to_thread(get_path)
    return {"path": path}

@app.post("/api/config/reload")
async def reload_config():
    """Hot-reloads .env values into the running Config class."""
    try:
        Config.reload()
        logger.info("[config] Config reloaded from .env")
        return {"status": "success", "comfy_path": Config.COMFY_PATH}
    except Exception as e:
        logger.error(f"[config] Reload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def start_api_server(bot, port=8001):
    global bot_instance
    bot_instance = bot
    host = "0.0.0.0" if Config.IS_DOCKER else "127.0.0.1"
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    logger.info(f"Starting API Server on port {port}...")
    await server.serve()

@app.post("/api/nodes/check")
async def check_nodes(request: Request):
    """
    Accepts an API-format workflow JSON.
    Generates a dummy WebUI workflow, runs `comfy node deps-in-workflow`,
    and returns a list of missing node class names or repositories.
    """
    try:
        workflow = await request.json()
        comfy_workspace = resolve_comfy_workspace(Config.COMFY_PATH)
        if not comfy_workspace:
            raise HTTPException(status_code=500, detail="Invalid COMFY_PATH")

        # Extract all node classes
        node_classes = set()
        for node in workflow.values():
            if isinstance(node, dict) and "class_type" in node:
                node_classes.add(node["class_type"])

        if not node_classes:
            return {"missing": []}

        # Create dummy webui format
        dummy_workflow = {
            "last_node_id": len(node_classes),
            "last_link_id": 0,
            "nodes": [],
            "links": [],
            "groups": [],
            "config": {},
            "extra": {},
            "version": 0.4
        }
        for i, node_class in enumerate(node_classes, 1):
            dummy_workflow["nodes"].append({
                "id": i,
                "type": node_class,
                "pos": [0, 0],
                "size": [100, 100],
                "flags": {},
                "order": 0,
                "mode": 0,
                "inputs": [],
                "outputs": [],
                "properties": {},
                "widgets_values": []
            })

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as wf, \
             tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as outf:
            json.dump(dummy_workflow, wf)
            wf_path = wf.name
            out_path = outf.name

        try:
            logger.info(f"Node check: running comfy node deps-in-workflow")
            cmd = ["comfy", "--workspace", comfy_workspace, "node", "deps-in-workflow", "--workflow", wf_path, "--output", out_path]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(f"comfy node deps-in-workflow failed: {stderr.decode()}")
                return {"missing": []}

            with open(out_path, 'r', encoding='utf-8') as f:
                deps_data = json.load(f)

            missing_repos = []
            if "custom_nodes" in deps_data:
                for repo, info in deps_data["custom_nodes"].items():
                    if info.get("state") == "not-installed" or info.get("state") == "missing":
                        missing_repos.append(repo)
            
            unknown_nodes = deps_data.get("unknown_nodes", [])
            
            # Check if any unknown nodes are in our manual mapping list
            for node in list(unknown_nodes):
                if node in MANUAL_NODE_MAPPING:
                    repo_url = MANUAL_NODE_MAPPING[node]
                    repo_folder_name = repo_url.split('/')[-1]
                    custom_nodes_path = os.path.join(comfy_workspace, "custom_nodes", repo_folder_name)
                    if not os.path.exists(custom_nodes_path):
                        missing_repos.append(repo_url)
                    unknown_nodes.remove(node)
            
            # Combine missing repos and unknown nodes as strings
            missing = missing_repos + unknown_nodes
            return {"missing": missing}

        finally:
            if os.path.exists(wf_path):
                os.remove(wf_path)
            if os.path.exists(out_path):
                os.remove(out_path)

    except Exception as e:
        logger.error(f"Node check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/discord/guilds")
async def get_discord_guilds():
    """
    Returns all connected guilds the bot is in, along with their sorted roles list and icons.
    """
    if not bot_instance:
        return {"guilds": [], "status": "offline"}
    
    if not bot_instance.is_ready():
        return {"guilds": [], "status": "loading"}
        
    try:
        guilds_data = []
        for guild in bot_instance.guilds:
            roles_data = []
            for role in guild.roles:
                color_str = f"#{role.color.value:06x}" if role.color.value != 0 else None
                roles_data.append({
                    "id": str(role.id),
                    "name": role.name,
                    "color": color_str,
                    "is_everyone": role.is_default(),
                    "position": role.position
                })
            
            roles_data.sort(key=lambda r: r["position"], reverse=True)
            
            guilds_data.append({
                "id": str(guild.id),
                "name": guild.name,
                "icon": guild.icon.url if guild.icon else None,
                "roles": roles_data
            })
            
        return {"guilds": guilds_data, "status": "online"}
    except Exception as e:
        logger.error(f"Error fetching Discord guilds: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/discord/permissions")
async def get_discord_permissions():
    """
    Reads and returns the persistent permissions mapping from permissions.json.
    """
    permissions_path = os.path.join(Config.DATA_DIR, "permissions.json")
    if not os.path.exists(permissions_path):
        return {"guild_permissions": {}}
    try:
        with open(permissions_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading permissions.json: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read permissions: {str(e)}")


@app.post("/api/discord/permissions")
async def save_discord_permissions(request: Request):
    """
    Persists updated permissions mapping to permissions.json.
    """
    try:
        data = await request.json()
        permissions_path = os.path.join(Config.DATA_DIR, "permissions.json")
        os.makedirs(os.path.dirname(permissions_path), exist_ok=True)
        with open(permissions_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error saving permissions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
