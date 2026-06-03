from fastapi import APIRouter, HTTPException, Request
import tempfile
import json
import os
import aiohttp
import asyncio
from src.core.config import Config
from src.core.logger import setup_logger
from src.core.comfy_parser import parse_node_list, parse_snapshot_list
from src.api import state
from src.api.helpers import (
    resolve_comfy_workspace,
    execute_comfy_command,
    run_comfy_install_deps,
    MANUAL_NODE_MAPPING
)

logger = setup_logger("api_comfy")

router = APIRouter()

@router.post("/api/comfy/restore")
async def restore_nodes(request: Request):
    try:
        body = await request.json()
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
        
        if resolved_path:
            init_file = os.path.join(resolved_path, "comfy", "__init__.py")
            if not os.path.exists(init_file):
                try:
                    os.makedirs(os.path.dirname(init_file), exist_ok=True)
                    with open(init_file, 'w') as f:
                        pass
                except: pass

        installed_any = False
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

@router.get("/api/comfy/nodes")
async def get_nodes(force: bool = False):
    try:
        workspace = resolve_comfy_workspace(Config.COMFY_PATH)
        if force:
            await execute_comfy_command(workspace, f'comfy --workspace "{workspace}" node update-cache')
        
        _, output = await execute_comfy_command(workspace, f'comfy --workspace "{workspace}" node show installed')
        nodes = parse_node_list(output)
        
        try:
            import glob
            manager_cache = os.path.join(workspace, "user", "__manager", "cache")
            latest_versions = {}
            
            for registry_file in glob.glob(os.path.join(manager_cache, "*_nodes.json")):
                with open(registry_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for n in data.get("nodes", []):
                        node_id = n.get("id")
                        latest_ver = n.get("latest_version", {}).get("version")
                        if node_id and latest_ver:
                            latest_versions[node_id] = latest_ver
            
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

@router.post("/api/comfy/nodes/update")
async def update_nodes_api(request: Request):
    try:
        body = await request.json()
        target_nodes = body.get("nodes", [])
        workspace = resolve_comfy_workspace(Config.COMFY_PATH)
        
        ts = asyncio.get_event_loop().time()
        backup_cmd = f'comfy --workspace "{workspace}" node save-snapshot "auto_pre_update_{int(ts)}"'
        await execute_comfy_command(workspace, backup_cmd)
        
        target_str = " ".join(target_nodes) if target_nodes else "all"
        update_cmd = f'comfy --workspace "{workspace}" --skip-prompt node update {target_str}'
        success, _ = await execute_comfy_command(workspace, update_cmd)
        
        return {"success": success}
    except Exception as e:
        logger.error(f"Error updating nodes: {e}")
        return {"success": False, "error": str(e)}

@router.get("/api/comfy/snapshots")
async def get_snapshots():
    try:
        workspace = resolve_comfy_workspace(Config.COMFY_PATH)
        _, output = await execute_comfy_command(workspace, f'comfy --workspace "{workspace}" node show snapshot-list')
        snapshots = parse_snapshot_list(output)
        return {"snapshots": snapshots}
    except Exception as e:
        logger.error(f"Error listing snapshots: {e}")
        return {"snapshots": [], "error": str(e)}

@router.get("/api/comfy/snapshots/{snapshot_id}")
async def get_snapshot_details(snapshot_id: str):
    try:
        workspace = resolve_comfy_workspace(Config.COMFY_PATH)
        manager_dir = os.path.join(workspace, "user", "__manager")
        
        common_paths = [
            os.path.join(manager_dir, "snapshots", snapshot_id),
            os.path.join(manager_dir, snapshot_id),
        ]
        
        target_path = None
        for p in common_paths:
            if os.path.exists(p):
                target_path = p
                break
                
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

@router.post("/api/comfy/snapshots/restore")
async def restore_snapshot_api(request: Request):
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

@router.post("/api/comfy/reboot")
async def reboot_comfy():
    try:
        async with aiohttp.ClientSession() as session:
            paths = ["/v2/manager/reboot", "/manager/reboot", "/api/manager/reboot", "/reboot"]
            methods = ["POST", "GET"]
            
            for path in paths:
                url = f"{Config.COMFY_URL}{path}"
                for method in methods:
                    try:
                        async with session.request(method, url, timeout=3) as resp:
                            if resp.status == 200:
                                return {"status": "success", "message": f"Reboot accepted ({method} {path})"}
                    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                        logger.info(f"Reboot likely successful (connection reset/timeout): {e}")
                        return {"status": "success", "message": "Reboot triggered successfully."}
            
            return {"status": "error", "message": "Could not verify reboot command was accepted."}
    except Exception as e:
        logger.error(f"Reboot handler error: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/api/comfy/setup")
async def setup_comfyui(request: Request):
    from dotenv import load_dotenv
    load_dotenv(override=True)
    comfy_base = os.getenv("COMFY_PATH", "").rstrip("/\\")

    if not comfy_base:
        raise HTTPException(status_code=400, detail="COMFY_PATH not set in .env")

    comfy_base = comfy_base.replace("/", os.sep)
    
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

    atlas_root  = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    files_dir   = os.path.join(atlas_root, "src", "files")

    steps = []

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
        except Exception as clone_err:
            clone_success = False
            clone_output = f"Git clone failed: {clone_err}"

    steps.append({"step": "clone_manager", "success": clone_success, "output": clone_output})

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
        except Exception as clone_err:
            clone_kj_success = False
            clone_kj_output = f"Git clone failed: {clone_err}"

    steps.append({"step": "clone_kjnodes", "success": clone_kj_success, "output": clone_kj_output})

    if not os.path.exists(python_exe):
        raise HTTPException(status_code=400, detail=f"python_embeded not found at: {python_exe}")

    req_files = []
    
    legacy_req = os.path.join(comfy_workspace, "manager_requirements.txt")
    if os.path.exists(legacy_req):
        req_files.append(legacy_req)
        
    cloned_req = os.path.join(manager_dir, "requirements.txt")
    if os.path.exists(cloned_req):
        req_files.append(cloned_req)
        
    kjnodes_req = os.path.join(kjnodes_dir, "requirements.txt")
    if os.path.exists(kjnodes_req):
        req_files.append(kjnodes_req)
        
    if not req_files:
        raise HTTPException(status_code=400, detail="No ComfyUI Manager or KJNodes requirements file was found.")

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

    ver_proc = await asyncio.create_subprocess_shell(
        f'"{python_exe}" --version',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=portable_root
    )
    ver_bytes, _ = await ver_proc.communicate()
    py_version_str = ver_bytes.decode("utf-8", errors="replace").strip()

    import re as _re
    ver_match = _re.search(r"Python (\d+)\.(\d+)", py_version_str, _re.IGNORECASE)
    py_tag = f"cp{ver_match.group(1)}{ver_match.group(2)}" if ver_match else None

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

    manager_arg = "--enable-manager-legacy-ui"
    try:
        body = await request.json()
        if body and "manager_type" in body:
            manager_arg = body["manager_type"]
    except Exception:
        pass

    bat_patched = False
    bat_message = ""
    ws_rel = os.path.relpath(comfy_workspace, portable_root).replace("/", "\\").replace("\\\\", "\\")
    desired_line = f".\\python_embeded\\python.exe -s {ws_rel}\\main.py --windows-standalone-build --use-sage-attention {manager_arg}"
    new_bat_content = desired_line + "\necho \npause\n"

    try:
        if os.path.exists(bat_file):
            with open(bat_file, "r", encoding="utf-8", errors="replace") as f:
                existing = f.read()
            if "--use-sage-attention" in existing and manager_arg in existing:
                bat_patched = True
                bat_message = f"Already patched with {manager_arg} – no changes made."
            else:
                with open(bat_file, "w", encoding="utf-8") as f:
                    f.write(new_bat_content)
                bat_patched = True
                bat_message = f"Patched with {manager_arg} successfully."
        else:
            with open(bat_file, "w", encoding="utf-8") as f:
                f.write(new_bat_content)
            bat_patched = True
            bat_message = f"Created new run_nvidia_gpu.bat with {manager_arg}."
    except Exception as bat_err:
        bat_message = f"Error patching bat: {bat_err}"

    steps.append({"step": "patch_bat", "success": bat_patched, "output": bat_message})

    overall_success = all(s["success"] for s in steps)
    return {"success": overall_success, "steps": steps}

@router.post("/api/nodes/check")
async def check_nodes(request: Request):
    try:
        workflow = await request.json()
        comfy_workspace = resolve_comfy_workspace(Config.COMFY_PATH)
        if not comfy_workspace:
            raise HTTPException(status_code=500, detail="Invalid COMFY_PATH")

        node_classes = set()
        for node in workflow.values():
            if isinstance(node, dict) and "class_type" in node:
                node_classes.add(node["class_type"])

        if not node_classes:
            return {"missing": []}

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
            
            for node in list(unknown_nodes):
                if node in MANUAL_NODE_MAPPING:
                    repo_url = MANUAL_NODE_MAPPING[node]
                    repo_folder_name = repo_url.split('/')[-1]
                    custom_nodes_path = os.path.join(comfy_workspace, "custom_nodes", repo_folder_name)
                    if not os.path.exists(custom_nodes_path):
                        missing_repos.append(repo_url)
                    unknown_nodes.remove(node)
            
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
