import os
import json
import uuid
import time
import asyncio
import random
import aiohttp
import aiofiles
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.core.config import Config
from src.core.logger import setup_logger
from src.api import state
from src.music_studio.session_store import music_session_store

logger = setup_logger("music_studio_server")

router = APIRouter(tags=["music_studio"])

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
WORKFLOW_PATH = os.path.join(Config.WORKFLOWS_DIR, "yue2_full_producer_studio_workflow.json")

# In-memory progress tracking for prompt IDs
prompt_progress: Dict[str, Dict[str, Any]] = {}

GENRE_PRESETS = [
    "Custom / Keep Only Lyrics",
    "Pop / Dance Pop",
    "Pop / Pop Funk",
    "Pop / Indie Pop",
    "Rock / Classic Rock",
    "Rock / Indie Rock",
    "Rock / Arena Rock",
    "Ballad / Power Ballad",
    "R&B / Neo-Soul",
    "Hip-Hop / Rap",
    "Hip-Hop / Trap",
    "Hip-Hop / Conscious Rap",
    "Hip-Hop / Melodic Rap",
    "Hip-Hop / West Coast",
    "Hip-Hop / Golden Age 90s",
    "Synthwave / Retro 80s Electro",
    "EDM / Melodic Progressive House",
    "Country / Modern Country",
    "Country / Country Pop",
    "Country / Country Americana",
    "Country / Outlaw Country",
    "Cinematic / Epic Orchestral",
    "Alternative / 90s Alternative",
    "Lo-Fi / Chillhop",
    "Metal / Heavy Metal",
    "Metal / Thrash Metal",
    "Metal / Symphonic Metal",
    "Grunge / 90s Seattle Sound",
    "Britpop / 90s UK Anthem",
    "College Rock / 80s-90s Jangle",
    "Jazz / Modern Smooth Jazz",
    "Folk / Acoustic Indie Folk",
    "Reggae / Modern Dub Pop",
    "Punk / High-Energy Pop Punk"
]

VOCAL_PROFILES = [
    "Warm Smooth Baritone (Male)",
    "Bright Soaring Tenor (Male)",
    "Deep Resonant Bass (Male)",
    "Airy Crystalline Soprano (Female)",
    "Velvety Mezzo-Soprano (Female)",
    "Smoky Deep Alto (Female)",
    "Male & Female Duet (Baritone + Soprano)",
    "Male Trio Harmonies (Tenor Lead + Backing)",
    "Female Pop Harmony Group",
    "Emotional Ballad Duo",
    "None / Pure Instrumental"
]

INTRO_STYLES = [
    "None",
    "Instrumental Intro",
    "Ambient Nature Intro",
    "Immediate Vocal Entry (No Intro)"
]

ACTIONS = [
    "Generate Full Song Concept",
    "Polish & Arrange Lyrics",
    "Optimize Acoustic Style String"
]

DEFAULT_LYRICS = """[Hook]
I’m slowing it down for the one that I love
Like the earth’s standing still while the stars crash above

[Verse 1]
[Soft piano only] [Intimate vocal]
The clock on the wall is a liar tonight
Spinning too fast while we chase the light
I’m holding your hand like a lifeline in June
The only thing quiet in a world out of tune

[Chorus]
[Chorus | Energy: Maximum] [Explosive vocal delivery] [Full band burst]
Oh, I’m slowing it down for the one that I love!
Like the earth’s standing still while the stars crash above!
It’s a beautiful weight, it’s a terrifying grace
I’m finally home in the light of your grace!
(In your grace)

[Verse 2]
[Drums settle into a driving backbeat]
We used to be shadows just passing through doors
But I’m not a ghost on these hardwood floors
Every bridge that I burned was a lesson I learned
To wait for the peace that I’ve finally earned

[Chorus]
[Chorus | Energy: Maximum] [Anthemic energy]
Oh, I’m slowing it down for the one that I love!
Like the earth’s standing still while the stars crash above!
It’s a beautiful weight, it’s a terrifying grace
I’m finally home in the light of your grace!

[Verse 3]
[Building intensity] [Gritty piano chords]
Don't let the sun rise, don't let it go cold
I’ve found a story that never gets old
The seconds are dripping like honey and wine
I’m finally yours, and I’m glad that you’re mine

[Chorus]
[Chorus | Energy: Maximum] [Maximum intensity] [Hard hitting drums]
Oh, I’m slowing it down for the one that I love!
Like the earth’s standing still while the stars crash above!
It’s a beautiful weight, it’s a terrifying grace
I’m finally home in the light of your grace!

[Outro]
[OUTRO - BIG FINAL HIT + HARD STOP, massive hall reverb tail]
[Instrumental: Final sustained piano note]
Slowing it down...
For the one I love...
[Precision Landing: Instrumental: Single piano chord]
[End]"""


def _load_base_workflow() -> Dict[str, Any]:
    if not os.path.exists(WORKFLOW_PATH):
        raise FileNotFoundError(f"Workflow file not found at {WORKFLOW_PATH}")
    with open(WORKFLOW_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/music", response_class=HTMLResponse)
@router.get("/music/", response_class=HTMLResponse)
async def serve_music_studio():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="Music Studio HTML template not found.")
    return FileResponse(index_path)


@router.get("/music/static/{filename:path}")
async def serve_music_static(filename: str):
    file_path = os.path.join(STATIC_DIR, filename)
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail=f"Static file '{filename}' not found.")
    return FileResponse(file_path)


@router.get("/api/music/options")
async def get_music_options():
    """Returns available options, presets, and defaults for the studio interface."""
    comfy_ok = False
    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.get(f"{Config.COMFY_URL}/system_stats", timeout=aiohttp.ClientTimeout(total=2)) as resp:
                comfy_ok = (resp.status == 200)
    except Exception:
        pass

    lmstudio_ok = False
    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.get("http://localhost:1234/v1/models", timeout=aiohttp.ClientTimeout(total=2)) as resp:
                lmstudio_ok = (resp.status == 200)
    except Exception:
        pass

    return {
        "status": "ok",
        "comfy_connected": comfy_ok,
        "lmstudio_connected": lmstudio_ok,
        "genre_presets": GENRE_PRESETS,
        "vocal_profiles": VOCAL_PROFILES,
        "intro_styles": INTRO_STYLES,
        "actions": ACTIONS,
        "bpm_default": 120,
        "bpm_min": 40,
        "bpm_max": 240,
        "default_custom_style": "Style of Bruno Mars song Risk It All",
        "default_lyrics": DEFAULT_LYRICS,
        "default_genre": "Custom / Keep Only Lyrics",
        "default_vocal": "Warm Smooth Baritone (Male)",
        "default_intro": "None",
        "default_action": "Generate Full Song Concept",
    }


@router.get("/api/music/session/{token}")
async def get_session(token: str):
    session = music_session_store.get_session(token)
    if not session:
        raise HTTPException(status_code=404, detail="Music session not found or expired.")
    return {
        "token": session.token,
        "user_id": session.user_id,
        "user_name": session.user_name,
        "genre_preset": session.genre_preset,
        "vocal_profile": session.vocal_profile,
        "bpm": session.bpm,
        "intro_style": session.intro_style,
        "custom_style": session.custom_style,
        "lyrics": session.lyrics,
        "action": session.action,
        "status": session.status,
        "audio_url": session.audio_url,
    }


class GenerateLyricsRequest(BaseModel):
    token: Optional[str] = None
    genre_preset: str = "Custom / Keep Only Lyrics"
    vocal_profile: str = "Warm Smooth Baritone (Male)"
    bpm: int = 120
    intro_style: str = "None"
    custom_style: str = "Style of Bruno Mars song Risk It All"
    lyrics: str = ""
    action: str = "Generate Full Song Concept"


@router.post("/api/music/lyrics")
async def generate_lyrics(req: GenerateLyricsRequest):
    """
    Executes the workflow to generate lyrics only.
    Disables Node 5 (YuE2 Neural Song Generator) and Node 6 (Audio Saver).
    Executes Node 1 (Style & Lyrics Studio), Node 3 (LLM Co-Producer), and Node 14 (Output Lyrics).
    Extracts the generated lyrics from Node 14.
    """
    try:
        wf = _load_base_workflow()
        
        # 1. Update Node 1
        wf["1"]["inputs"]["genre_preset"] = req.genre_preset
        wf["1"]["inputs"]["vocal_profile"] = req.vocal_profile
        wf["1"]["inputs"]["bpm"] = int(req.bpm)
        wf["1"]["inputs"]["intro_style"] = req.intro_style
        wf["1"]["inputs"]["custom_style"] = req.custom_style
        wf["1"]["inputs"]["lyrics"] = req.lyrics if req.lyrics.strip() else DEFAULT_LYRICS
        
        # 2. Update Node 3
        wf["3"]["inputs"]["action"] = req.action
        
        # 3. Lean prompt payload: ONLY Node 1, 3, 14
        # Node 5 and 6 are omitted, completely disabling audio generation
        lyrics_prompt = {
            "1": wf["1"],
            "3": wf["3"],
            "14": wf["14"]
        }
        
        client_id = f"music_studio_{uuid.uuid4().hex[:8]}"
        
        # 4. Submit prompt to ComfyUI
        async with aiohttp.ClientSession() as sess:
            async with sess.post(
                f"{Config.COMFY_URL}/prompt",
                json={"prompt": lyrics_prompt, "client_id": client_id},
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status != 200:
                    err_text = await resp.text()
                    raise HTTPException(status_code=500, detail=f"ComfyUI rejected prompt: {err_text}")
                result = await resp.json()
                prompt_id = result.get("prompt_id")
                if not prompt_id:
                    raise HTTPException(status_code=500, detail="No prompt_id returned by ComfyUI")
        
        logger.info(f"Queued lyrics generation prompt: {prompt_id}")
        prompt_progress[prompt_id] = {
            "stage": "co_producing_lyrics",
            "percent": 25,
            "status": "Co-producing lyrics with LLM...",
            "started_at": time.time()
        }

        # 5. Poll ComfyUI history for completion (timeout: 120s for LLM reasoning)
        max_attempts = 120
        generated_lyrics = ""
        
        for _ in range(max_attempts):
            await asyncio.sleep(1.0)
            async with aiohttp.ClientSession() as sess:
                async with sess.get(f"{Config.COMFY_URL}/history/{prompt_id}", timeout=aiohttp.ClientTimeout(total=5)) as h_resp:
                    if h_resp.status == 200:
                        h_data = await h_resp.json()
                        if prompt_id in h_data:
                            prompt_entry = h_data[prompt_id]
                            outputs = prompt_entry.get("outputs", {})
                            if "14" in outputs:
                                text_list = outputs["14"].get("text", [])
                                if text_list:
                                    generated_lyrics = text_list[0]
                                    break
                            # Check if status has error
                            status_obj = prompt_entry.get("status", {})
                            if status_obj.get("status_str") == "error":
                                raise HTTPException(status_code=500, detail=f"ComfyUI execution error: {status_obj.get('messages', 'Unknown error')}")

        if not generated_lyrics:
            raise HTTPException(status_code=504, detail="Timed out waiting for lyrics generation to complete.")

        prompt_progress[prompt_id] = {
            "stage": "completed",
            "percent": 100,
            "status": "Lyrics generated successfully!",
            "lyrics": generated_lyrics
        }

        # Update session if token provided
        if req.token:
            session = music_session_store.get_session(req.token)
            if session:
                session.lyrics = generated_lyrics
                session.genre_preset = req.genre_preset
                session.vocal_profile = req.vocal_profile
                session.bpm = req.bpm
                session.intro_style = req.intro_style
                session.custom_style = req.custom_style
                session.action = req.action

        return {
            "status": "success",
            "prompt_id": prompt_id,
            "lyrics": generated_lyrics
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Generate lyrics failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class GenerateSongRequest(BaseModel):
    token: Optional[str] = None
    genre_preset: str = "Custom / Keep Only Lyrics"
    vocal_profile: str = "Warm Smooth Baritone (Male)"
    bpm: int = 120
    intro_style: str = "None"
    custom_style: str = "Style of Bruno Mars song Risk It All"
    lyrics: str = ""
    action: str = "Generate Full Song Concept"
    direct_lyrics: bool = False
    seed: Optional[int] = None
    ode_steps: Optional[int] = 24


@router.post("/api/music/generate")
async def generate_song(req: GenerateSongRequest):
    """
    Executes the full music studio workflow.
    Enables Node 5 (YuE2 Neural Song Generator) and Node 6 (YuE2 Audio Preview & Saver).
    Returns the prompt_id for progress tracking.
    """
    try:
        wf = _load_base_workflow()
        
        # 1. Update Node 1
        lyrics_text = req.lyrics if req.lyrics.strip() else DEFAULT_LYRICS
        wf["1"]["inputs"]["genre_preset"] = req.genre_preset
        wf["1"]["inputs"]["vocal_profile"] = req.vocal_profile
        wf["1"]["inputs"]["bpm"] = int(req.bpm)
        wf["1"]["inputs"]["intro_style"] = req.intro_style
        wf["1"]["inputs"]["custom_style"] = req.custom_style
        wf["1"]["inputs"]["lyrics"] = lyrics_text
        
        # 2. Update Node 3
        wf["3"]["inputs"]["action"] = req.action
        
        # 3. Seed Handling (Node 4)
        if req.seed is not None and req.seed >= 0:
            final_seed = int(req.seed)
        else:
            final_seed = random.randint(100000000000, 999999999999)
        wf["4"]["inputs"]["seed"] = final_seed

        # 4. Direct lyrics mode vs Co-producer routing
        if req.direct_lyrics:
            # Connect Node 13 (Lyrics Switch) directly to Node 1's lyrics output
            wf["13"]["inputs"]["any_01"] = ["1", 1]
            # Connect Node 12 (Style Switch) directly to Node 1's style output
            wf["12"]["inputs"]["any_01"] = ["1", 0]
            logger.info("Direct lyrics mode enabled: routing Node 1 directly to Node 12 & 13")
        else:
            wf["13"]["inputs"]["any_01"] = ["3", 0]
            wf["12"]["inputs"]["any_01"] = ["3", 1]

        # 5. ODE Steps if specified
        if req.ode_steps and 12 <= req.ode_steps <= 64:
            wf["5"]["inputs"]["ode_steps"] = int(req.ode_steps)

        client_id = f"music_studio_{uuid.uuid4().hex[:8]}"
        
        # 6. Submit prompt to ComfyUI
        async with aiohttp.ClientSession() as sess:
            async with sess.post(
                f"{Config.COMFY_URL}/prompt",
                json={"prompt": wf, "client_id": client_id},
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status != 200:
                    err_text = await resp.text()
                    raise HTTPException(status_code=500, detail=f"ComfyUI rejected prompt: {err_text}")
                result = await resp.json()
                prompt_id = result.get("prompt_id")
                if not prompt_id:
                    raise HTTPException(status_code=500, detail="No prompt_id returned by ComfyUI")
        
        logger.info(f"Queued full song generation prompt: {prompt_id} (seed={final_seed})")

        prompt_progress[prompt_id] = {
            "stage": "starting",
            "percent": 5,
            "status": "Starting full music generation pipeline...",
            "started_at": time.time(),
            "seed": final_seed,
            "lyrics": lyrics_text,
            "token": req.token
        }

        # Launch background monitor to track execution, save audio, and notify Discord if applicable
        asyncio.create_task(_monitor_song_generation(prompt_id, req))

        return {
            "status": "queued",
            "prompt_id": prompt_id,
            "seed": final_seed,
            "message": "Full song generation started!"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Generate song failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def _monitor_song_generation(prompt_id: str, req: GenerateSongRequest):
    """Background monitor that waits for ComfyUI to produce audio, saves it locally, and posts to Discord."""
    logger.info(f"Monitoring song generation for prompt {prompt_id}")
    max_wait_seconds = 600 # 10 minutes maximum for neural audio synthesis
    start_time = time.time()
    
    try:
        while time.time() - start_time < max_wait_seconds:
            await asyncio.sleep(2.0)
            
            async with aiohttp.ClientSession() as sess:
                async with sess.get(f"{Config.COMFY_URL}/history/{prompt_id}", timeout=aiohttp.ClientTimeout(total=5)) as h_resp:
                    if h_resp.status != 200:
                        continue
                    h_data = await h_resp.json()
                    if prompt_id not in h_data:
                        continue
                    
                    prompt_entry = h_data[prompt_id]
                    outputs = prompt_entry.get("outputs", {})
                    
                    # Check for audio output in Node 6
                    if "6" in outputs and "audio" in outputs["6"]:
                        audio_list = outputs["6"]["audio"]
                        if audio_list:
                            audio_meta = audio_list[0]
                            filename = audio_meta.get("filename")
                            subfolder = audio_meta.get("subfolder", "")
                            folder_type = audio_meta.get("type", "output")
                            
                            logger.info(f"Song completed for {prompt_id}: {filename} (subfolder={subfolder})")
                            
                            # Download audio bytes from ComfyUI
                            audio_url_params = f"?filename={filename}&subfolder={subfolder}&type={folder_type}"
                            async with sess.get(f"{Config.COMFY_URL}/view{audio_url_params}", timeout=aiohttp.ClientTimeout(total=30)) as v_resp:
                                if v_resp.status == 200:
                                    audio_bytes = await v_resp.read()
                                    
                                    # Save to assets directory
                                    local_filename = f"music_{prompt_id}_{os.path.basename(filename)}"
                                    local_path = os.path.join(Config.ASSETS_DIR, local_filename)
                                    async with aiofiles.open(local_path, "wb") as f:
                                        await f.write(audio_bytes)
                                    
                                    audio_serve_url = f"/api/music/audio/{local_filename}"
                                    
                                    # Check for output lyrics in Node 14
                                    output_lyrics = ""
                                    if "14" in outputs and "text" in outputs["14"] and outputs["14"]["text"]:
                                        output_lyrics = outputs["14"]["text"][0]
                                    
                                    prompt_progress[prompt_id] = {
                                        "stage": "completed",
                                        "percent": 100,
                                        "status": "Song generated successfully!",
                                        "audio_url": audio_serve_url,
                                        "filename": local_filename,
                                        "lyrics": output_lyrics or req.lyrics,
                                        "completed_at": time.time()
                                    }
                                    
                                    # If Discord session exists, notify channel
                                    if req.token:
                                        await _dispatch_discord_completion(req.token, local_path, local_filename, req, output_lyrics)
                                    
                                    return
                    
                    # Check for errors
                    status_obj = prompt_entry.get("status", {})
                    if status_obj.get("status_str") == "error":
                        err_msg = status_obj.get("messages", "Generation error")
                        logger.error(f"Song generation error for {prompt_id}: {err_msg}")
                        prompt_progress[prompt_id] = {
                            "stage": "failed",
                            "percent": 0,
                            "status": f"Generation failed: {err_msg}",
                            "error": str(err_msg)
                        }
                        return

        # Timeout reached
        logger.warning(f"Song generation timed out for {prompt_id}")
        prompt_progress[prompt_id] = {
            "stage": "failed",
            "percent": 0,
            "status": "Song generation timed out after 10 minutes.",
            "error": "Timeout"
        }

    except Exception as e:
        logger.error(f"Song monitor error for {prompt_id}: {e}", exc_info=True)
        prompt_progress[prompt_id] = {
            "stage": "failed",
            "percent": 0,
            "status": f"Monitoring error: {e}",
            "error": str(e)
        }


async def _dispatch_discord_completion(token: str, local_path: str, filename: str, req: GenerateSongRequest, lyrics: str):
    """Posts the generated audio and lyrics back to the Discord channel."""
    session = music_session_store.get_session(token)
    if not session:
        return

    bot = state.bot_instance
    if not bot:
        logger.warning("Discord bot instance not available for music completion dispatch")
        return

    try:
        import discord
        channel = bot.get_channel(int(session.channel_id))
        if not channel:
            logger.error(f"Channel {session.channel_id} not found for music delivery")
            return

        embed = discord.Embed(
            title="🎵 LINK Music Studio — Song Generated!",
            description=(
                f"**Producer**: <@{session.user_id}>\n"
                f"**Genre**: `{req.genre_preset}`\n"
                f"**Vocal Profile**: `{req.vocal_profile}`\n"
                f"**Tempo**: `{req.bpm} BPM`\n"
                f"**Intro**: `{req.intro_style}`\n"
                f"**Style**: *{req.custom_style[:120]}*\n\n"
                f"🎧 **Listen to your master track below!**"
            ),
            color=discord.Color.from_rgb(168, 85, 247) # Vibrant Purple
        )
        embed.set_footer(text="YuE2 Neural Music Generator & Studio")

        file_to_send = discord.File(local_path, filename=filename)
        
        # If there's an original interaction message, edit or send to channel
        if session.message_id:
            try:
                orig_msg = await channel.fetch_message(int(session.message_id))
                await orig_msg.edit(content=f"🎵 <@{session.user_id}>, your song is ready!", embed=embed, view=None)
                await channel.send(file=file_to_send)
            except Exception:
                await channel.send(content=f"🎵 <@{session.user_id}>, your song is ready!", embed=embed, file=file_to_send)
        else:
            await channel.send(content=f"🎵 <@{session.user_id}>, your song is ready!", embed=embed, file=file_to_send)

        music_session_store.mark_completed(token, f"/api/music/audio/{filename}")
        logger.info(f"Dispatched music completion to Discord channel {session.channel_id}")

    except Exception as e:
        logger.error(f"Failed to dispatch music to Discord: {e}", exc_info=True)


@router.get("/api/music/status/{prompt_id}")
async def get_prompt_status(prompt_id: str):
    """Returns the current execution stage and progress percentage for a prompt."""
    info = prompt_progress.get(prompt_id)
    if not info:
        # Check if ComfyUI knows about this prompt
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(f"{Config.COMFY_URL}/history/{prompt_id}", timeout=aiohttp.ClientTimeout(total=3)) as resp:
                    if resp.status == 200:
                        h_data = await resp.json()
                        if prompt_id in h_data:
                            outputs = h_data[prompt_id].get("outputs", {})
                            lyrics = ""
                            if "14" in outputs and outputs["14"].get("text"):
                                lyrics = outputs["14"]["text"][0]
                            audio_url = None
                            if "6" in outputs and outputs["6"].get("audio"):
                                fn = outputs["6"]["audio"][0].get("filename")
                                if fn:
                                    audio_url = f"/api/music/audio/{fn}"
                            return {
                                "stage": "completed",
                                "percent": 100,
                                "status": "Completed",
                                "lyrics": lyrics,
                                "audio_url": audio_url
                            }
        except Exception:
            pass

        return {
            "stage": "executing",
            "percent": 50,
            "status": "Processing in YuE2 Studio..."
        }

    return info


@router.get("/api/music/audio/{filename}")
async def get_music_audio(filename: str):
    """Serves the generated audio file with correct audio/mpeg MIME type."""
    safe_filename = os.path.basename(filename)
    local_path = os.path.join(Config.ASSETS_DIR, safe_filename)
    
    if not os.path.exists(local_path) or not os.path.isfile(local_path):
        # Fallback: check ComfyUI output folder
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(f"{Config.COMFY_URL}/view?filename={safe_filename}&subfolder=YuE2&type=output") as resp:
                    if resp.status == 200:
                        audio_data = await resp.read()
                        async with aiofiles.open(local_path, "wb") as f:
                            await f.write(audio_data)
                        return Response(content=audio_data, media_type="audio/mpeg")
        except Exception:
            pass
        raise HTTPException(status_code=404, detail=f"Audio file '{safe_filename}' not found.")
        
    return FileResponse(
        local_path, 
        media_type="audio/mpeg", 
        filename=safe_filename,
        headers={"Accept-Ranges": "bytes"}
    )
