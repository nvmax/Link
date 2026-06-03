import os
import asyncio
import tempfile
import json
from src.core.config import Config
from src.core.logger import setup_logger

logger = setup_logger("api_helpers")

MANUAL_NODE_MAPPING = {
    "AutoMegapixelReducer": "https://github.com/nvmax/aspect-ratio-resizer"
}

def resolve_comfy_workspace(base_path: str):
    if not base_path: return ""
    base_path = base_path.replace("/", os.sep).rstrip(os.sep)
    if os.path.exists(os.path.join(base_path, "main.py")): return base_path
    subfolder = os.path.join(base_path, "ComfyUI")
    if os.path.exists(os.path.join(subfolder, "main.py")): return subfolder
    
    try:
        if os.path.isdir(base_path):
            for name in os.listdir(base_path):
                p = os.path.join(base_path, name)
                if os.path.isdir(p) and os.path.exists(os.path.join(p, "main.py")):
                    return p
    except Exception:
        pass
        
    return base_path

async def execute_comfy_command(workspace_path: str, cmd: str) -> tuple[bool, str]:
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
    
    system32 = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32")
    wbem = os.path.join(system32, "wbem")
    current_path = env.get("PATH", "")
    if system32 not in current_path:
        env["PATH"] = system32 + os.pathsep + wbem + os.pathsep + current_path

    if os.name != 'nt':
        try:
            links_dir = "/app/comfy_links"
            os.makedirs(links_dir, exist_ok=True)
            
            src_cm_cli = "/comfyui/python_embeded/Lib/site-packages/cm_cli"
            src_manager = "/comfyui/python_embeded/Lib/site-packages/comfyui_manager"
            
            dest_cm_cli = os.path.join(links_dir, "cm_cli")
            dest_manager = os.path.join(links_dir, "comfyui_manager")
            
            if os.path.exists(src_cm_cli) and not os.path.exists(dest_cm_cli):
                os.symlink(src_cm_cli, dest_cm_cli)
            if os.path.exists(src_manager) and not os.path.exists(dest_manager):
                os.symlink(src_manager, dest_manager)
                
            current_pythonpath = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = links_dir + (os.pathsep + current_pythonpath if current_pythonpath else "")
        except Exception as e:
            logger.warning(f"Failed to setup comfy_links symlinks: {e}")

    if workspace_path:
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

async def run_comfy_install_deps(workspace_path: str, workflow_path: str) -> bool:
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        deps_path = tf.name

    try:
        cmd1 = f'comfy --workspace "{workspace_path}" node deps-in-workflow --workflow "{workflow_path}" --output "{deps_path}"'
        success1, _ = await execute_comfy_command(workspace_path, cmd1)
        if not success1: return False

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

        cmd2 = f'comfy --workspace "{workspace_path}" --skip-prompt node install-deps --deps "{deps_path}"'
        success2, _ = await execute_comfy_command(workspace_path, cmd2)
        return success2
    finally:
        if os.path.exists(deps_path):
            try: os.unlink(deps_path)
            except: pass
