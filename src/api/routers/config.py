from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Request
import os
import asyncio
from src.core.config import Config
from src.core.logger import setup_logger

logger = setup_logger("api_config")

router = APIRouter()

@router.post("/api/bot/restart")
async def restart_bot() -> Dict[str, Any]:
    import sys
    from src.api import state

    async def _do_restart():
        logger.info("Graceful bot restart initiated. Cleaning up resources...")
        await asyncio.sleep(0.5)
        
        # 1. Stop queue processing and stuck-job monitor loop
        if state.bot_instance and state.bot_instance.queue_manager:
            if state.bot_instance.queue_manager.cleanup_task:
                state.bot_instance.queue_manager.cleanup_task.cancel()
                logger.info("Queue monitor cleanup task cancelled.")
        
        # 2. Close WS connection gracefully
        if state.ws_instance:
            try:
                await state.ws_instance.close()
                logger.info("Gracefully closed Comfy WebSocket connection.")
            except Exception as e:
                logger.warning(f"Error closing WebSocket: {e}")

        # 3. Close API client session
        if state.bot_instance and state.bot_instance.api_client:
            try:
                await state.bot_instance.api_client.close()
                logger.info("Gracefully closed API client session.")
            except Exception as e:
                logger.warning(f"Error closing API client: {e}")

        # 4. Close bot connection
        if state.bot_instance:
            try:
                await state.bot_instance.close()
                logger.info("Gracefully closed Discord Bot connection.")
            except Exception as e:
                logger.warning(f"Error closing Bot: {e}")

        logger.info("Restarting process via execv...")
        os.execv(sys.executable, [sys.executable] + sys.argv)

    asyncio.create_task(_do_restart())
    return {"status": "success", "message": "Bot is restarting. It will be back online in a few seconds."}

@router.post("/api/utils/select-folder")
async def select_folder() -> Dict[str, Any]:
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
async def reload_config() -> Dict[str, Any]:
    try:
        Config.reload()
        logger.info("[config] Config reloaded from .env")
        return {"status": "success", "comfy_path": Config.COMFY_PATH}
    except Exception as e:
        logger.error(f"[config] Reload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
