import os
import asyncio
import tempfile
import json
from src.core.config import Config
from src.core.logger import setup_logger

logger = setup_logger("api_helpers")

MANUAL_NODE_MAPPING = {
    "AutoMegapixelReducer": "https://github.com/nvmax/aspect-ratio-resizer",
    # Krea 2 vision-aware text encoder — not yet in ComfyUI-Manager registry
    "TextEncoderKrea2": "https://github.com/ethanfel/ComfyUI-Krea2TextEncoder",
    "Krea2SystemPrompt": "https://github.com/ethanfel/ComfyUI-Krea2TextEncoder",
}

def find_python_embeded(workspace_path: str) -> str | None:
    if not workspace_path or os.name != 'nt':
        return None
    p_root = workspace_path.replace("/", os.sep).replace("\\", os.sep).rstrip(os.sep)
    candidates = [
        p_root,
        os.path.dirname(p_root) if p_root else "",
        os.path.dirname(os.path.dirname(p_root)) if os.path.dirname(p_root) else "",
    ]
    for c in candidates:
        if c and os.path.isdir(c):
            embed_py = os.path.join(c, "python_embeded", "python.exe")
            if os.path.exists(embed_py):
                return embed_py
    return None

def resolve_comfy_workspace(base_path: str) -> str:
    if not base_path:
        base_path = ""
    
    normalized = base_path.replace("/", os.sep).replace("\\", os.sep).rstrip(os.sep)

    def _check_dir(path: str) -> str | None:
        if not path or not os.path.exists(path):
            return None
        if os.path.exists(os.path.join(path, "main.py")):
            return path
        sub = os.path.join(path, "ComfyUI")
        if os.path.exists(os.path.join(sub, "main.py")):
            return sub
        try:
            if os.path.isdir(path):
                for name in os.listdir(path):
                    p = os.path.join(path, name)
                    if os.path.isdir(p) and os.path.exists(os.path.join(p, "main.py")):
                        return p
        except Exception:
            pass
        return None

    # 1. Check if configured base_path resolves
    if normalized:
        found = _check_dir(normalized)
        if found:
            return found

    # 2. Check if username in path is mismatched (e.g., C:\Users\Admin\... copied from another PC)
    if normalized:
        import re
        user_home = os.path.expanduser("~")
        match = re.match(r"^[A-Za-z]:[\\/]Users[\\/][^\\/]+([\\/].*)$", normalized, re.IGNORECASE)
        if match:
            remapped = user_home + match.group(1)
            found = _check_dir(remapped)
            if found:
                logger.info(f"Auto-remapped COMFY_PATH to current user profile: {found}")
                return found

    # 3. Check common desktop / user locations
    home = os.path.expanduser("~")
    common_locations = [
        os.path.join(home, "Desktop", "ComfyUI_windows_portable"),
        os.path.join(home, "Desktop", "ComfyUI"),
        os.path.join(home, "ComfyUI_windows_portable"),
        os.path.join(home, "ComfyUI"),
    ]
    for loc in common_locations:
        found = _check_dir(loc)
        if found:
            logger.info(f"Auto-discovered ComfyUI workspace at: {found}")
            return found

def sanitize_custom_nodes_permissions(workspace_path: str):
    """
    On Windows NTFS, dotfiles (.cursorrules, .gitignore, .comfyignore, .editorconfig, etc.)
    and git files often receive the Hidden (+H) or Read-Only (+R) attributes.
    When ComfyUI-Manager extracts or updates node packages (e.g. #LAZY-CNR-SWITCH-SCRIPT),
    Python's standard file-write operations fail with [Errno 13] Permission denied on hidden files.
    This helper recursively removes Hidden and Read-Only flags from all files in custom_nodes.
    """
    if not workspace_path or os.name != 'nt':
        return
    custom_nodes_dir = os.path.join(workspace_path, "custom_nodes")
    if not os.path.isdir(custom_nodes_dir):
        return

    try:
        import ctypes
        FILE_ATTRIBUTE_READONLY = 0x01
        FILE_ATTRIBUTE_HIDDEN = 0x02
        FILE_ATTRIBUTE_NORMAL = 0x80

        for root, dirs, files in os.walk(custom_nodes_dir):
            for name in files + dirs:
                full_p = os.path.join(root, name)
                try:
                    attrs = ctypes.windll.kernel32.GetFileAttributesW(full_p)
                    if attrs != -1 and (attrs & (FILE_ATTRIBUTE_READONLY | FILE_ATTRIBUTE_HIDDEN)):
                        new_attrs = attrs & ~(FILE_ATTRIBUTE_READONLY | FILE_ATTRIBUTE_HIDDEN)
                        if new_attrs == 0:
                            new_attrs = FILE_ATTRIBUTE_NORMAL
                        ctypes.windll.kernel32.SetFileAttributesW(full_p, new_attrs)
                except Exception:
                    pass
    except Exception as e:
        logger.debug(f"Failed to sanitize custom_nodes permissions: {e}")

async def execute_comfy_command(workspace_path: str, cmd: list[str]) -> tuple[bool, str]:
    if not workspace_path or not os.path.exists(workspace_path):
        err_msg = f"ComfyUI workspace directory not found: '{workspace_path}'"
        logger.error(f"[comfy-cli] {err_msg}")
        return False, err_msg

    # Ensure custom_nodes files are writable and not hidden on Windows
    if os.name == 'nt':
        sanitize_custom_nodes_permissions(workspace_path)

    python_exe = find_python_embeded(workspace_path)

    exec_args = list(cmd)
    if python_exe and cmd and cmd[0] == "comfy":
        cmd_parts = []
        i = 1
        while i < len(cmd):
            part = cmd[i]
            if part == "--workspace":
                i += 2
            elif part == "--skip-prompt":
                i += 1
            elif part == "node":
                i += 1
            elif part == "--deps":
                i += 1
            else:
                cmd_parts.append(part)
                i += 1
        exec_args = [python_exe, "-m", "cm_cli"] + cmd_parts

    logger.info(f"[comfy-cli] Execute from: {workspace_path}")
    logger.info(f"[comfy-cli] Command arguments: {exec_args}")
    
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

    process = await asyncio.create_subprocess_exec(
        *exec_args,
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

async def run_comfy_install_deps(workspace_path: str, workflow_path: str, extra_repos: dict[str, str] | None = None) -> tuple[bool, list[str]]:
    """Run comfy-cli dependency installation for the given workflow dummy JSON.

    Returns (success, unknown_nodes):
      - success=True, unknown_nodes=[]  → everything installed fine
      - success=False, unknown_nodes=[...]  → these class names couldn't be
        resolved from the ComfyUI-Manager registry or MANUAL_NODE_MAPPING;
        the caller should ask the user to supply a GitHub repo URL for them.
    """
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        deps_path = tf.name

    try:
        if os.name == 'nt':
            sanitize_custom_nodes_permissions(workspace_path)
        python_exe = find_python_embeded(workspace_path)

        async def _run_cm(args: list[str]) -> tuple[bool, str]:
            exec_args = [python_exe, "-m", "cm_cli"] + args if python_exe else args
            logger.info(f"[comfy-cli] Execute from: {workspace_path}")
            logger.info(f"[comfy-cli] Command arguments: {exec_args}")
            full_output: list[str] = []
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            if workspace_path:
                env["PYTHONPATH"] = workspace_path + os.pathsep + env.get("PYTHONPATH", "")
                env["COMFYUI_PATH"] = workspace_path
            proc = await asyncio.create_subprocess_exec(
                *exec_args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
                cwd=workspace_path if os.path.exists(workspace_path) else None,
            )
            if proc.stdin:
                proc.stdin.write(b"y\n")
                await proc.stdin.drain()
                proc.stdin.close()
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                decoded = line.decode().strip()
                if decoded:
                    logger.info(f"[comfy-cli] {decoded}")
                    full_output.append(decoded)
            await proc.wait()
            return proc.returncode == 0, "\n".join(full_output)

        # ── Step 1: resolve deps from the workflow dummy ──────────────────────
        success1, _ = await _run_cm(["deps-in-workflow", "--workflow", workflow_path, "--output", deps_path])
        if not success1:
            return False, []

        # ── Step 2: patch unknown_nodes with known mappings ───────────────────
        still_unknown: list[str] = []
        if os.path.exists(deps_path):
            try:
                with open(deps_path, "r", encoding="utf-8") as f:
                    deps_data = json.load(f)

                unknowns: list[str] = deps_data.get("unknown_nodes", [])
                customs: dict = deps_data.setdefault("custom_nodes", {})

                combined_mapping = dict(MANUAL_NODE_MAPPING)
                if extra_repos:
                    combined_mapping.update(extra_repos)

                updated = False
                for node in list(unknowns):
                    if node in combined_mapping:
                        repo_url = combined_mapping[node]
                        customs[repo_url] = {"state": "not-installed"}
                        unknowns.remove(node)
                        updated = True

                # Nodes still in unknowns after all mappings — we cannot resolve them
                still_unknown = list(unknowns)

                if updated:
                    logger.info(f"[comfy-cli] Patched deps.json with repos: {list(combined_mapping.keys())}")
                if still_unknown:
                    logger.warning(f"[comfy-cli] Unresolvable nodes (no repo known): {still_unknown}")

                with open(deps_path, "w", encoding="utf-8") as f:
                    json.dump(deps_data, f, indent=2)

            except Exception as e:
                logger.error(f"Failed to patch deps.json: {e}")

        # ── Step 3: if unknowns remain, abort and tell the caller ─────────────
        if still_unknown:
            return False, still_unknown

        # ── Step 4: install the resolved deps ─────────────────────────────────
        success2, _ = await _run_cm(["install-deps", deps_path])
        return success2, []

    finally:
        if os.path.exists(deps_path):
            try:
                os.unlink(deps_path)
            except Exception:
                pass

