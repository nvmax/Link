import os
import io
import base64
import uuid
import asyncio
import aiohttp
import aiofiles
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image

from src.core.config import Config
from src.core.logger import setup_logger
from src.inpaint.session_store import session_store
from src.api import state

logger = setup_logger("inpaint_server")

app = FastAPI(title="LINK Inpaint Activity Server")

# Allow CORS for Discord embedded iframe
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files directory
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_inpaint_app():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="Inpaint HTML template not found.")
    return FileResponse(index_path)

@app.get("/api/inpaint/asset/{filename}")
async def get_inpaint_asset(filename: str):
    """Serves local asset files (e.g. generated images or uploaded files) for inpainting."""
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(Config.ASSETS_DIR, safe_filename)
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail=f"Asset '{safe_filename}' not found.")
    return FileResponse(file_path)

@app.get("/api/inpaint/session/{token}")
async def get_session(token: str):
    session = session_store.get_session(token)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired.")
    return {
        "token": session.token,
        "user_id": session.user_id,
        "user_name": session.user_name,
        "source_image_url": session.source_image_url,
        "prompt": session.prompt,
        "channel_id": session.channel_id,
    }

@app.get("/api/inpaint/session/user/{user_id}")
async def get_session_by_user(user_id: str):
    session = session_store.get_active_session_for_user(user_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"No active session found for user '{user_id}'.")
    return {
        "token": session.token,
        "user_id": session.user_id,
        "user_name": session.user_name,
        "source_image_url": session.source_image_url,
        "prompt": session.prompt,
        "channel_id": session.channel_id,
    }


class SubmitInpaintRequest(BaseModel):
    token: str
    prompt: str
    mask_data_url: str # Base64 PNG data URL of the painted mask (white on black)

@app.post("/api/inpaint/submit")
async def submit_inpaint(req: SubmitInpaintRequest):
    session = session_store.get_session(req.token)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired.")

    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")

    try:
        # 1. Download source image bytes
        async with aiohttp.ClientSession() as http_sess:
            async with http_sess.get(session.source_image_url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status != 200:
                    raise HTTPException(status_code=500, detail=f"Failed to fetch source image ({resp.status})")
                source_bytes = await resp.read()

        source_img = Image.open(io.BytesIO(source_bytes)).convert("RGBA")

        # 2. Decode mask base64 PNG
        header, encoded = req.mask_data_url.split(",", 1)
        mask_bytes = base64.b64decode(encoded)
        mask_img = Image.open(io.BytesIO(mask_bytes)).convert("L") # Grayscale

        # Ensure mask is same size as source image
        if mask_img.size != source_img.size:
            mask_img = mask_img.resize(source_img.size, Image.Resampling.BILINEAR)

        # 3. Create painted masked image (alpha channel transparent where mask is white)
        # ComfyUI LoadImage node expects an RGBA image where alpha channel encodes mask
        r, g, b, _ = source_img.split()
        
        # Invert mask: white areas in mask become 0 (transparent alpha = paint area)
        # Opaque alpha (255) = keep original
        inverted_alpha = Image.eval(mask_img, lambda p: 255 - p)
        
        composite_img = Image.merge("RGBA", (r, g, b, inverted_alpha))

        # Save composited image to bytes
        output_buffer = io.BytesIO()
        composite_img.save(output_buffer, format="PNG")
        output_bytes = output_buffer.getvalue()

        filename = f"clipspace-painted-masked-{uuid.uuid4().hex[:12]}.png"
        local_path = os.path.join(Config.ASSETS_DIR, filename)

        async with aiofiles.open(local_path, "wb") as f:
            await f.write(output_bytes)
        logger.info(f"Saved inpaint composited image to {local_path}")

        # 4. Upload composited image to ComfyUI if bot instance is active
        bot = state.bot_instance
        if not bot or not bot.api_client:
            raise HTTPException(status_code=503, detail="Discord Bot / ComfyUI client unavailable.")

        class DummyAttachment:
            def __init__(self, data_bytes, fn):
                self.data_bytes = data_bytes
                self.filename = fn
            async def read(self):
                return self.data_bytes

        try:
            uploaded_name = await bot.api_client.upload_file(DummyAttachment(output_bytes, filename))
            logger.info(f"Uploaded inpaint image to ComfyUI as '{uploaded_name}'")
        except Exception as upload_err:
            logger.error(f"ComfyUI upload failed ({Config.COMFY_URL}): {upload_err}")
            raise HTTPException(
                status_code=503, 
                detail=f"Cannot connect to ComfyUI at {Config.COMFY_URL}. Please make sure ComfyUI is running on your machine."
            )

        # 5. Route job to generation cog
        gen_cog = bot.get_cog("GenerationCog")
        if not gen_cog:
            raise HTTPException(status_code=503, detail="Generation system not loaded.")

        # Prepare user values for Krea2_Inpaint
        user_values = {
            "prompt": req.prompt.strip(),
            "image": uploaded_name,
        }

        # Trigger generation asynchronously
        asyncio.create_task(
            gen_cog.handle_inpaint_completion(
                session=session,
                user_values=user_values,
                uploaded_filename=uploaded_name
            )
        )

        # Mark session completed
        session_store.mark_completed(req.token)

        return {"status": "success", "message": "Inpaint job submitted successfully!"}

    except Exception as e:
        logger.error(f"Inpaint submit failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def start_inpaint_server(bot, port: int = 8000):
    import uvicorn
    state.bot_instance = bot
    host = "0.0.0.0"
    config_server = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config_server)
    logger.info(f"Starting Inpaint Activity Server on http://{host}:{port} (Domain: {Config.INPAINT_SERVER_DOMAIN})...")
    await server.serve()
