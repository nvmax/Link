from fastapi import APIRouter, HTTPException, Request
import os
import asyncio
from src.core.config import Config
from src.core.logger import setup_logger

logger = setup_logger("api_config")

router = APIRouter()

@router.post("/api/bot/restart")
async def restart_bot():
    import sys

    async def _do_restart():
        await asyncio.sleep(0.5)
        logger.info("Bot restart initiated via /api/bot/restart")
        os.execv(sys.executable, [sys.executable] + sys.argv)

    asyncio.create_task(_do_restart())
    return {"status": "success", "message": "Bot is restarting. It will be back online in a few seconds."}

@router.post("/api/utils/select-folder")
async def select_folder():
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

@router.post("/api/config/reload")
async def reload_config():
    try:
        Config.reload()
        logger.info("[config] Config reloaded from .env")
        return {"status": "success", "comfy_path": Config.COMFY_PATH}
    except Exception as e:
        logger.error(f"[config] Reload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
