import os
import re
import json
import yaml
import uuid
import time
import math
import urllib.parse
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


def sanitize_song_title(title: Optional[str], fallback: str = "YuE2_Master_Track") -> str:
    """Sanitizes user-specified song title for safe file naming and ComfyUI prefixing."""
    if not title:
        return fallback
    clean = re.sub(r'[\\/*?:"<>|]', '', str(title)).strip()
    clean = re.sub(r'[\s\-]+', '_', clean)
    clean = clean.strip('._')
    clean = clean[:60]
    return clean or fallback


def resolve_song_title(req: Any, session: Optional[Any] = None) -> str:
    """
    Robustly resolves the intended song title across:
    1. req.song_title / req.title / req.song_name / req.track_name
    2. session.song_title
    3. Lyrics structure tags: [Title: ...] or # Title: ...
    4. Custom style fallback (if user entered song title in custom_style or 'song XYZ')
    """
    # 1. Direct fields on request
    for field in ["song_title", "title", "song_name", "track_name"]:
        val = getattr(req, field, None)
        if val and str(val).strip():
            return str(val).strip()

    # 2. Session store
    if session and getattr(session, "song_title", None):
        if str(session.song_title).strip():
            return str(session.song_title).strip()

    # 3. Check for [Title: ...] in lyrics
    lyrics = getattr(req, "lyrics", "") or (session.lyrics if session else "") or ""
    m = re.search(r'\[(?:Title|Song|Track):\s*([^\]\n\r]+)\]', lyrics, re.IGNORECASE)
    if m and m.group(1).strip():
        return m.group(1).strip()

    # 4. Check custom_style for song title patterns
    style = getattr(req, "custom_style", "") or (session.custom_style if session else "") or ""
    style = style.strip()
    if style and style != "Style of Bruno Mars song Risk It All":
        # Check patterns like "song 'xyz'", "song: xyz", "title: xyz"
        m = re.search(r'(?:song|track|title)\s*[:=]?\s*["\']?([^,"\';\n]+)["\']?', style, re.IGNORECASE)
        if m and m.group(1).strip():
            extracted = m.group(1).strip()
            if len(extracted) > 1 and not any(k in extracted.lower() for k in ["tempo", "genre", "vocal", "bpm", "profile"]):
                return extracted
        # If the entire custom_style is short (e.g. "slowing it down") and not a descriptive prompt
        if len(style) <= 45 and not any(k in style.lower() for k in ["bpm", "genre", "drums", "guitar", "synth", "tempo"]):
            clean_style = re.sub(r'^(?:style\s+of\s+)+', '', style, flags=re.IGNORECASE).strip()
            if clean_style:
                return clean_style

    return ""

GENRE_PRESETS = [
    "Custom / Keep Typed Style",
    "Custom / Keep Only Lyrics",
    "Rock / Classic Rock",
    "Rock / Indie Rock",
    "Rock / Arena Rock",
    "Pop / Pop Funk",
    "Pop / Indie Pop",
    "Pop / Dance Pop",
    "Ballad / Power Ballad",
    "Country / Modern Country",
    "Country / Country Pop",
    "Country / Country Americana",
    "Country / Outlaw Country",
    "Hip-Hop / Rap",
    "Hip-Hop / Trap",
    "Hip-Hop / Conscious Rap",
    "Hip-Hop / Melodic Rap",
    "Hip-Hop / West Coast",
    "Hip-Hop / Golden Age 90s",
    "Cinematic / Epic Orchestral",
    "R&B / Neo-Soul",
    "Alternative / 90s Alternative",
    "Lo-Fi / Chillhop",
    "Metal / Heavy Metal",
    "Metal / Thrash Metal",
    "Metal / Symphonic Metal",
    "Grunge / 90s Seattle Sound",
    "Britpop / 90s UK Anthem",
    "College Rock / 80s-90s Jangle",
    "Synthwave / Retro 80s Electro",
    "EDM / Melodic Progressive House",
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
    "Vamp / Groove Intro",
    "Vocal/Lyrical Hook Intro",
    "Vocal / Lyrical Hook Intro",
    "Turnaround Intro",
    "Stand-Alone Instrumental",
    'The "Cold Start" (No Intro / Attacca)',
    "Acapella Intro",
    "Drone / Ambient Pad Intro",
    "Solo Instrument Feature",
    "Drum / Percussion Groove",
    "Count-In / Dialogue Intro",
    "SFX / Found Sound Intro",
    "Modulating Intro",
    "Crescendo / Fade-In Intro",
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


def _get_lmstudio_config() -> Dict[str, Any]:
    """
    Resolves LM Studio configuration dynamically:
    1. Node 3 in yue2_full_producer_studio_workflow.json (Source of truth configured in Architect View)
    2. src/ai_studio/ai_config.yaml (Atlas AI Studio configuration)
    3. Fallback to http://localhost:1234/v1
    """
    # 1. Check base workflow JSON (saved by Architect View)
    try:
        wf = _load_base_workflow()
        node3 = wf.get("3", {}).get("inputs", {})
        if node3.get("model") or node3.get("base_url"):
            return {
                "provider": node3.get("provider", "LMStudio"),
                "model": node3.get("model", "qwen3.8-27b-uncensored-hauhaucs-aggressive-mtp"),
                "base_url": (node3.get("base_url") or "http://192.168.1.174:1234/v1").rstrip("/")
            }
    except Exception as e:
        logger.warning(f"Could not read base workflow for LM Studio config: {e}")

    # 2. Check ai_config.yaml
    try:
        config_path = os.path.join(Config.AI_STUDIO_DIR, "ai_config.yaml")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                providers = data.get("providers", {})
                lm = providers.get("lmstudio", {})
                if lm.get("base_url") or lm.get("model"):
                    return {
                        "provider": "LMStudio",
                        "model": lm.get("model") or "qwen3.8-27b-uncensored-hauhaucs-aggressive-mtp",
                        "base_url": (lm.get("base_url") or "http://192.168.1.174:1234/v1").rstrip("/")
                    }
    except Exception as e:
        logger.warning(f"Could not read ai_config.yaml for music studio: {e}")

    return {
        "provider": "LMStudio",
        "model": "qwen3.8-27b-uncensored-hauhaucs-aggressive-mtp",
        "base_url": "http://192.168.1.174:1234/v1"
    }


async def _check_lmstudio_reachability(base_url: Optional[str] = None) -> tuple[bool, str]:
    """
    Checks if LM Studio is reachable at base_url or known network/local endpoints.
    Returns (is_reachable, working_base_url).
    """
    candidates = []
    if base_url:
        candidates.append(base_url.rstrip("/"))
    for fb in ["http://192.168.1.174:1234/v1", "http://localhost:1234/v1", "http://127.0.0.1:1234/v1"]:
        if fb not in candidates:
            candidates.append(fb)

    for host in candidates:
        endpoint = f"{host}/models"
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(endpoint, timeout=aiohttp.ClientTimeout(total=2)) as resp:
                    if resp.status == 200:
                        return True, host
        except Exception:
            pass
    return False, base_url or "http://localhost:1234/v1"


async def _fetch_live_models(provider: str = "LMStudio", base_url: Optional[str] = None, api_key: str = "") -> tuple[list[str], bool, str]:
    """
    Dynamically fetches available models for the LLM provider.
    1. Tries ComfyUI's /yue2/models endpoint (from nodes_llm.py).
    2. Directly queries LM Studio / Ollama / OpenAI / OpenRouter endpoints.
    Returns (models_list, is_live, working_base_url).
    """
    p = str(provider or "LMStudio").strip()
    p_lower = p.lower()

    # 1. Try ComfyUI /yue2/models
    try:
        query_params = f"?provider={urllib.parse.quote(p)}"
        if base_url:
            query_params += f"&base_url={urllib.parse.quote(base_url)}"
        if api_key:
            query_params += f"&api_key={urllib.parse.quote(api_key)}"
        async with aiohttp.ClientSession() as sess:
            async with sess.get(f"{Config.COMFY_URL}/yue2/models{query_params}", timeout=aiohttp.ClientTimeout(total=2)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    mods = data.get("models", [])
                    if mods:
                        return mods, data.get("live", True), base_url or ""
    except Exception:
        pass

    # 2. Direct provider fetch
    if p_lower == "lmstudio":
        candidates = []
        if base_url:
            candidates.append(base_url.rstrip("/"))
        for fb in ["http://localhost:1234/v1", "http://127.0.0.1:1234/v1", "http://192.168.1.174:1234/v1"]:
            if fb not in candidates:
                candidates.append(fb)

        for host in candidates:
            try:
                async with aiohttp.ClientSession() as sess:
                    async with sess.get(f"{host}/models", timeout=aiohttp.ClientTimeout(total=2)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            raw_models = [m.get("id") for m in data.get("data", []) if m.get("id")]
                            if raw_models:
                                chat_models = [m for m in raw_models if "embed" not in m.lower()]
                                embed_models = [m for m in raw_models if "embed" in m.lower()]
                                return chat_models + embed_models, True, host
            except Exception:
                pass
        return ["gemma-4-e4b-it", "qwen2.5:7b", "llama-3.2-3b"], False, candidates[0]

    elif p_lower == "ollama":
        url = (base_url or "http://localhost:11434").rstrip("/")
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(f"{url}/api/tags", timeout=aiohttp.ClientTimeout(total=2)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        mods = [m.get("name") for m in data.get("models", []) if m.get("name")]
                        if mods:
                            return mods, True, url
        except Exception:
            pass
        return ["qwen2.5:7b", "llama3.2:latest"], False, url

    elif p_lower in ("openai", "openrouter", "deepseek", "grok"):
        key = api_key or os.getenv("OPENAI_API_KEY", "")
        if key:
            url = (base_url or ("https://openrouter.ai/api/v1" if p_lower == "openrouter" else "https://api.openai.com/v1")).rstrip("/")
            try:
                headers = {"Authorization": f"Bearer {key}"}
                async with aiohttp.ClientSession() as sess:
                    async with sess.get(f"{url}/models", headers=headers, timeout=aiohttp.ClientTimeout(total=3)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            mods = [m.get("id") for m in data.get("data", []) if m.get("id")]
                            if mods:
                                return mods, True, url
            except Exception:
                pass

    return ["gemma-4-e4b-it"], False, base_url or ""


def _render_access_denied_page(title: str, heading: str, message: str, hint: str) -> HTMLResponse:
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — YuE2 Music Studio</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background: #0b0914 radial-gradient(circle at 50% 30%, rgba(139, 92, 246, 0.15), transparent 70%);
      color: #f3f4f6;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px;
    }}
    .auth-card {{
      background: rgba(22, 18, 38, 0.9);
      border: 1px solid rgba(139, 92, 246, 0.3);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      box-shadow: 0 24px 64px rgba(0, 0, 0, 0.6), 0 0 32px rgba(139, 92, 246, 0.15);
      border-radius: 20px;
      max-width: 480px;
      width: 100%;
      padding: 40px 32px;
      text-align: center;
      animation: fadeIn 0.4s ease-out;
    }}
    @keyframes fadeIn {{
      from {{ opacity: 0; transform: translateY(12px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}
    .icon-wrap {{
      width: 72px;
      height: 72px;
      margin: 0 auto 20px;
      background: rgba(139, 92, 246, 0.12);
      border: 1px solid rgba(139, 92, 246, 0.35);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 32px;
      box-shadow: 0 0 24px rgba(139, 92, 246, 0.2);
    }}
    h1 {{
      font-size: 22px;
      font-weight: 700;
      color: #ffffff;
      margin-bottom: 12px;
      letter-spacing: -0.02em;
    }}
    p.message {{
      font-size: 14.5px;
      color: #9ca3af;
      line-height: 1.6;
      margin-bottom: 20px;
    }}
    .command-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: rgba(139, 92, 246, 0.18);
      border: 1px solid rgba(139, 92, 246, 0.4);
      color: #c4b5fd;
      font-family: 'JetBrains Mono', monospace;
      font-size: 15px;
      font-weight: 600;
      padding: 8px 16px;
      border-radius: 10px;
      margin-bottom: 24px;
    }}
    p.hint {{
      font-size: 13px;
      color: #6b7280;
      line-height: 1.5;
    }}
    .footer-brand {{
      margin-top: 28px;
      padding-top: 20px;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
      font-size: 12px;
      color: #4b5563;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
    }}
  </style>
</head>
<body>
  <div class="auth-card">
    <div class="icon-wrap">🔒</div>
    <h1>{heading}</h1>
    <p class="message">{message}</p>
    <div>
      <span class="command-badge">/music</span>
    </div>
    <p class="hint">{hint}</p>
    <div class="footer-brand">
      <span>YuE2 Neural Music Studio</span>
      <span>•</span>
      <span>Powered by LINK</span>
    </div>
  </div>
</body>
</html>"""
    return HTMLResponse(
        content=html,
        status_code=403,
        headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"}
    )


@router.get("/music", response_class=HTMLResponse)
@router.get("/music/", response_class=HTMLResponse)
async def serve_music_studio(token: Optional[str] = None):
    # Enforce active session from Discord: users must launch via /music
    if not token:
        return _render_access_denied_page(
            title="Discord Authorization Required",
            heading="Studio Access via Discord",
            message="The YuE2 Music Studio is integrated with Discord. To open a private studio session, please use the <code>/music</code> command in your Discord server.",
            hint="Each session link is private and tied directly to the Discord user who requested it."
        )

    session = music_session_store.get_session(token)
    if not session:
        return _render_access_denied_page(
            title="Session Expired or Closed",
            heading="Studio Session Ended",
            message="This studio session link is no longer active or has already been closed.",
            hint="To start a new song session or generate new takes, please return to Discord and run <code>/music</code>."
        )

    # Touch session to record opening and reset heartbeat
    music_session_store.touch_session(token)

    index_path = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="Music Studio HTML template not found.")
    try:
        async with aiofiles.open(index_path, "r", encoding="utf-8") as f:
            html_content = await f.read()
        cache_buster = int(time.time())
        # Dynamically append timestamp cache-buster to completely defeat CDN/Cloudflare caching
        html_content = re.sub(r'app\.js(\?v=[^"\'\s>]*)?', f'app.js?v={cache_buster}', html_content)
        html_content = re.sub(r'style\.css(\?v=[^"\'\s>]*)?', f'style.css?v={cache_buster}', html_content)
        return HTMLResponse(
            content=html_content,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            }
        )
    except Exception as e:
        logger.error(f"Error serving dynamic music studio template: {e}")
        return FileResponse(
            index_path,
            headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"}
        )


@router.get("/music/static/{filename:path}")
async def serve_music_static(filename: str):
    file_path = os.path.join(STATIC_DIR, filename)
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail=f"Static file '{filename}' not found.")
    return FileResponse(
        file_path,
        headers={"Cache-Control": "no-cache, no-store, must-revalidate, max-age=0", "Pragma": "no-cache", "Expires": "0"}
    )


@router.get("/api/music/options")
async def get_music_options():
    """Returns available options, presets, defaults, and connection status for the studio interface."""
    lm_cfg = _get_lmstudio_config()

    async def check_comfy():
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(f"{Config.COMFY_URL}/system_stats", timeout=aiohttp.ClientTimeout(total=2.0)) as resp:
                    return resp.status == 200
        except Exception:
            return False

    async def check_lm():
        try:
            target_url = lm_cfg.get("base_url", "http://192.168.1.174:1234/v1").rstrip("/")
            async with aiohttp.ClientSession() as sess:
                async with sess.get(f"{target_url}/models", timeout=aiohttp.ClientTimeout(total=2.0)) as resp:
                    return resp.status == 200
        except Exception:
            return False

    results = await asyncio.gather(check_comfy(), check_lm(), return_exceptions=True)
    comfy_ok = bool(results[0]) if not isinstance(results[0], Exception) else False
    lmstudio_ok = bool(results[1]) if not isinstance(results[1], Exception) else False

    return {
        "status": "ok",
        "comfy_connected": comfy_ok,
        "lmstudio_connected": lmstudio_ok,
        "lm_provider": lm_cfg["provider"],
        "lm_model": lm_cfg["model"],
        "lm_base_url": lm_cfg["base_url"],
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
        "default_ode_steps": 24,
        "default_checkpoint": "yue2_3b_bf16.safetensors",
        "cot_modes": ["full", "melody", "off"],
        "default_cot": "full",
    }


@router.get("/api/music/models")
async def get_live_models(provider: str = "LMStudio", base_url: Optional[str] = None, api_key: Optional[str] = ""):
    """Returns live models available from the LLM provider (or ComfyUI's /yue2/models endpoint)."""
    lm_cfg = _get_lmstudio_config()
    target_base = base_url or lm_cfg["base_url"]
    models, is_live, working_base = await _fetch_live_models(provider=provider, base_url=target_base, api_key=api_key or "")
    if lm_cfg.get("model") and lm_cfg["model"] in models:
        active_model = lm_cfg["model"]
    else:
        active_model = models[0] if models else lm_cfg.get("model", "qwen3.8-27b-uncensored-hauhaucs-aggressive-mtp")
    return {
        "status": "ok",
        "provider": provider,
        "models": models,
        "active_model": active_model,
        "live": is_live,
        "base_url": working_base
    }


@router.get("/api/music/session/{token}")
async def get_session(token: str):
    session = music_session_store.get_session(token)
    if not session:
        raise HTTPException(status_code=404, detail="Music session not found, closed, or expired.")
    music_session_store.touch_session(token)
    return {
        "token": session.token,
        "user_id": session.user_id,
        "user_name": session.user_name,
        "song_title": getattr(session, "song_title", ""),
        "genre_preset": session.genre_preset,
        "vocal_profile": session.vocal_profile,
        "bpm": session.bpm,
        "intro_style": session.intro_style,
        "custom_style": session.custom_style,
        "lyrics": session.lyrics,
        "action": session.action,
        "status": session.status,
        "audio_url": session.audio_url,
        "take_count": getattr(session, "take_count", 0),
    }


class SessionHeartbeatRequest(BaseModel):
    token: str


@router.post("/api/music/session/heartbeat")
async def session_heartbeat(req: SessionHeartbeatRequest):
    ok = music_session_store.touch_session(req.token)
    if not ok:
        raise HTTPException(status_code=403, detail="Session expired or closed.")
    return {"status": "ok"}


@router.post("/api/music/session/close")
@router.get("/api/music/session/close")
async def session_close(token: str):
    music_session_store.close_session(token, immediate=False)
    return {"status": "closing"}


class GenerateLyricsRequest(BaseModel):
    token: Optional[str] = None
    song_title: Optional[str] = ""
    genre_preset: str = "Custom / Keep Only Lyrics"
    vocal_profile: str = "Warm Smooth Baritone (Male)"
    bpm: int = 120
    intro_style: str = "None"
    custom_style: str = "Style of Bruno Mars song Risk It All"
    lyrics: str = ""
    action: str = "Generate Full Song Concept"
    provider: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = ""


def _clean_and_parse_lyrics(raw_text: str, fallback_title: str = "") -> tuple[str, str]:
    raw_text = (raw_text or "").strip()
    clean_json_text = raw_text
    # Strip markdown code blocks if present
    if "```" in clean_json_text:
        m_fence = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', clean_json_text, re.IGNORECASE)
        if m_fence:
            clean_json_text = m_fence.group(1).strip()
        else:
            clean_json_text = re.sub(r'^```[^\n]*\n|```$', '', clean_json_text).strip()

    # Try parsing JSON
    try:
        data = json.loads(clean_json_text)
        if isinstance(data, dict):
            lyrics = data.get("lyrics", "") or data.get("song_lyrics", "") or ""
            title = data.get("suggested_title", "") or data.get("title", "") or fallback_title
            if lyrics.strip():
                l_clean = lyrics.strip()
                if not re.search(r'\[End\]\s*$', l_clean, re.IGNORECASE):
                    l_clean = f"{l_clean}\n\n[End]"
                return l_clean, title.strip()
    except Exception:
        pass

    # If not valid JSON, treat raw_text as full lyrics
    lyrics = raw_text
    lyrics = re.sub(r'```[a-zA-Z]*\n|```', '', lyrics).strip()
    title = fallback_title

    # Extract title tag if present: [Title: ...] or # Title: ...
    m_tag = re.search(r'(?:^|\n)\s*\[?(?:Title|Song|Track)\s*[:=]\s*([^\]\n\r]+)\]?', lyrics, re.IGNORECASE)
    if m_tag and m_tag.group(1).strip():
        title = m_tag.group(1).strip()
        lyrics = re.sub(r'(?:^|\n)\s*\[?(?:Title|Song|Track)\s*[:=]\s*[^\]\n\r]+\]?\s*', '\n', lyrics, flags=re.IGNORECASE).strip()

    # If title still empty, check hook/chorus for title
    if not title:
        m_hook = re.search(r'\[(?:Hook|Chorus)[^\]]*\]\s*(?:\[[^\]]*\]\s*)*([^\n\r]+)', lyrics, re.IGNORECASE)
        if m_hook:
            raw_hook = re.sub(r'^[!\'"\(\)]+|[!\'"\(\)]+$', '', m_hook.group(1).strip()).strip()
            words = raw_hook.split()
            if 1 <= len(words) <= 5:
                title = " ".join(words)
            elif len(words) > 5:
                title = " ".join(words[:4])

    # Ensure concludes with [End]
    if not re.search(r'\[End\]\s*$', lyrics, re.IGNORECASE):
        lyrics = f"{lyrics}\n\n[End]"

    return lyrics.strip(), title.strip()


async def _query_llm_direct(provider: str, model: str, base_url: str, api_key: str, sys_prompt: str, user_prompt: str, temperature: float = 0.7, max_tokens: int = 4096) -> str:
    p = (provider or "lmstudio").strip().lower()
    
    if p == "lmstudio":
        lm_ok, working_base = await _check_lmstudio_reachability(base_url)
        if lm_ok:
            base_url = working_base
        else:
            raise HTTPException(
                status_code=503,
                detail=f"⚠️ LM Studio is not reachable at {base_url}. Please ensure LM Studio is running on that machine."
            )
        
        endpoint = f"{base_url.rstrip('/')}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            
        payload = {
            "model": model or "qwen3.8-27b-uncensored-hauhaucs-aggressive-mtp",
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        async with aiohttp.ClientSession() as sess:
            async with sess.post(endpoint, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=90)) as resp:
                if resp.status != 200:
                    err = await resp.text()
                    raise HTTPException(status_code=500, detail=f"LM Studio error ({resp.status}): {err}")
                data = await resp.json()
                choices = data.get("choices", [])
                if not choices:
                    raise HTTPException(status_code=500, detail="Empty response from LM Studio")
                return choices[0].get("message", {}).get("content", "")

    elif p in ["google", "gemini"]:
        gemini_key = api_key or os.getenv("GEMINI_API_KEY", "")
        if not gemini_key:
            raise HTTPException(status_code=400, detail="GEMINI_API_KEY is not configured.")
        from google import genai
        client = genai.Client(api_key=gemini_key)
        full_content = f"{sys_prompt}\n\nUser Request:\n{user_prompt}"
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=model or "gemini-2.5-flash",
            contents=full_content
        )
        return response.text

    elif p in ["openai", "custom"]:
        endpoint = f"{base_url.rstrip('/')}/chat/completions"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        async with aiohttp.ClientSession() as sess:
            async with sess.post(endpoint, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=90)) as resp:
                if resp.status != 200:
                    err = await resp.text()
                    raise HTTPException(status_code=500, detail=f"LLM API error ({resp.status}): {err}")
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported LLM provider: {provider}")


YUE2_ENHANCE_EXISTING_LYRICS_SYS_PROMPT = """You are an elite AI Music Producer and Audio Director specializing in the YuE2 Neural Audio Engine.
The user has provided their own custom song lyrics. Your ONLY task is to enhance their lyrics for neural audio synthesis by injecting structural performance markers, instrumentation cues, and vocal styling tags above each section.

════ ABSOLUTE SACRED RULES ════
1. NEVER REPLACE, REWRITE, DELETE, OR TRANSLATE THE USER'S ACTUAL LYRICAL WORDS OR LINES.
2. Every single sung word and line written by the user MUST be preserved 100% VERBATIM in the exact order written.
3. The user's lyrics may be in English, Danish, Spanish, or any other language. DO NOT translate them.
4. DO NOT invent or substitute new sung lyric words for what the user wrote.

════ PRODUCTION ENHANCEMENT TAGS TO INJECT AT EACH SECTION ════
At the start of every section (e.g. [Intro], [Verse 1], [Pre-Chorus], [Chorus], [Verse 2], [Bridge], [Final Chorus], [Outro]), inject precise acoustic production tags matching the requested Genre, Vocal Profile, BPM, and Style:

1. SECTION & VOCAL HEADER:
   e.g. [Intro], [Verse 1 - Male Vocal], [Pre-Chorus - Male Vocal], [Chorus - Full Band], [Final Chorus - Male Vocal], [Outro]

2. INSTRUMENTATION TAG [Instrumentation: ...]:
   Detail the exact arrangement, dynamic intensity, and instrument layers for that section.
   Example:
   [Instrumentation: Biggest section. Full drums, deep melodic bass, wide synths, Rhodes, muted guitar accents, stacked harmonies, tasteful vocal ad-libs.]

3. VOCAL STYLING TAG [Vocal: ...]:
   Detail the vocal timbre, delivery intensity, backing harmonies, runs, or ad-libs for that section.
   Example:
   [Vocal: Strongest delivery of the song, still controlled and intimate; add tasteful runs only on the final two lines.]

4. USER'S EXACT LYRICS:
   Place the user's exact original lyrics for that section immediately below the tags.

5. CONCLUDING MARKER:
   The song MUST conclude with [End] on its own line.

════ RESPONSE FORMAT ════
Output a valid JSON object strictly matching this schema:
{
  "suggested_title": "Catchy Song Title based on lyrics or hook",
  "lyrics": "The full enhanced lyrics containing all production tags and the user's 100% verbatim lyrics, ending with [End]."
}
IMPORTANT: Output ONLY the raw JSON object. No Markdown code fences, no extra text."""


YUE2_GENERATE_FROM_SCRATCH_SYS_PROMPT = """You are an elite hit songwriter, topline producer, and lyricist specializing in the YuE2 Neural Audio Engine.
The user wants a complete, radio-ready song crafted from scratch for neural audio synthesis, including structural section headers and acoustic performance tags.

════ ARCHITECTURE & TAGGING RULES ════
1. SECTION HEADERS & TAGS:
   For every section ([Intro], [Verse 1], [Pre-Chorus], [Chorus], [Verse 2], [Bridge], [Final Chorus], [Outro], [End]):
   - Include section name and vocal role: e.g. [Verse 1 - Male Vocal], [Final Chorus - Male Vocal]
   - Include [Instrumentation: ...] tag detailing arrangement, instruments, and dynamics matching the Genre and BPM.
   - Include [Vocal: ...] tag detailing vocal delivery, tone, and harmony.
   - Example structure for a chorus:
     [Final Chorus - Male Vocal]
     [Instrumentation: Biggest section. Full drums, deep melodic bass, wide synths, Rhodes, muted guitar accents, stacked harmonies, tasteful vocal ad-libs.]
     [Vocal: Strongest delivery of the song, still controlled and intimate; add tasteful runs only on the final two lines.]
     (Singable chorus lyrics...)
   - The song MUST conclude with [End] on its own line.

2. RHYTHM & METER:
   - Write lyrics that groove tightly at the requested BPM and genre.
   - Strong rhyme schemes and vivid emotional imagery.

════ OUTPUT REQUIREMENT ════
Output a valid JSON object strictly matching this schema:
{
  "suggested_title": "Catchy Song Title",
  "lyrics": "Full song lyrics with [Verse 1 - ...], [Instrumentation: ...], [Vocal: ...], [Chorus - ...], ending with [End]."
}
IMPORTANT: Output ONLY the raw JSON object. No Markdown code fences, no extra text."""


@router.post("/api/music/lyrics")
async def generate_lyrics(req: GenerateLyricsRequest):
    """
    Generates or enhances structured YuE2 song lyrics directly via LLM (LM Studio / Gemini / OpenAI).
    
    RULES:
    1. If genre_preset == 'Custom / Keep Only Lyrics':
       Preserves the user's lyrics 100% verbatim without any LLM alteration.
    2. If req.lyrics contains user lyrics:
       ENHANCES them by injecting acoustic tags ([Section - Vocal Profile], [Instrumentation: ...], [Vocal: ...])
       matching the genre and style, while preserving ALL user lyrics 100% verbatim.
    3. If req.lyrics is empty:
       Generates a complete song concept from scratch matching the genre, vocal profile, BPM, and acoustic direction.
    """
    try:
        user_lyrics = (req.lyrics or "").strip()
        has_existing_lyrics = bool(user_lyrics and user_lyrics != DEFAULT_LYRICS)
        is_keep_only = (req.genre_preset or "").strip() == "Custom / Keep Only Lyrics"
        prompt_id = f"lyrics_{uuid.uuid4().hex[:10]}"

        # Case 1: Custom / Keep Only Lyrics -> Preserve user's text 100% untouched
        if is_keep_only and has_existing_lyrics:
            clean_lyrics = user_lyrics
            if not re.search(r'\[End\]\s*$', clean_lyrics, re.IGNORECASE):
                clean_lyrics = f"{clean_lyrics}\n\n[End]"
            
            # Extract suggested title from lyrics if not provided
            suggested_title = req.song_title or ""
            if not suggested_title:
                m_tag = re.search(r'(?:^|\n)\s*\[?(?:Title|Song|Track)\s*[:=]\s*([^\]\n\r]+)\]?', clean_lyrics, re.IGNORECASE)
                if m_tag and m_tag.group(1).strip():
                    suggested_title = m_tag.group(1).strip()
            
            prompt_progress[prompt_id] = {
                "stage": "completed",
                "percent": 100,
                "status": "Lyrics preserved verbatim (Keep Only Lyrics).",
                "lyrics": clean_lyrics,
                "suggested_title": suggested_title
            }
            if req.token:
                session = music_session_store.get_session(req.token)
                if session:
                    if suggested_title:
                        session.song_title = suggested_title
                    session.lyrics = clean_lyrics
            
            logger.info(f"Preserved user lyrics verbatim for Custom / Keep Only Lyrics ({len(clean_lyrics)} chars)")
            return {
                "status": "success",
                "prompt_id": prompt_id,
                "lyrics": clean_lyrics,
                "suggested_title": suggested_title
            }

        # Resolve Provider & Model Settings
        lm_cfg = _get_lmstudio_config()
        provider = req.provider or lm_cfg["provider"]
        base_url = req.base_url or lm_cfg["base_url"]
        api_key = req.api_key or ""
        model = req.model

        if not model:
            live_mods, is_live, _ = await _fetch_live_models(provider, base_url, api_key)
            if lm_cfg.get("model") and is_live and (lm_cfg["model"] in live_mods):
                model = lm_cfg["model"]
            elif is_live and live_mods:
                model = live_mods[0]
            else:
                model = lm_cfg.get("model") or "qwen3.8-27b-uncensored-hauhaucs-aggressive-mtp"

        # Pre-flight check for LM Studio
        if provider == "LMStudio":
            lm_ok, working_base = await _check_lmstudio_reachability(base_url)
            if not lm_ok:
                raise HTTPException(
                    status_code=503,
                    detail=(
                        f"⚠️ LM Studio server is NOT reachable at {base_url} (or port 1234)! "
                        "Please verify LM Studio is running on that machine, your model is loaded, "
                        "and the local server is started."
                    )
                )
            base_url = working_base

        if (provider in ["google", "gemini"]) and not api_key:
            api_key = os.getenv("GEMINI_API_KEY", "")

        # Case 2: User has existing lyrics -> ENHANCE them with production tags (NEVER replace words)
        if has_existing_lyrics:
            sys_prompt = YUE2_ENHANCE_EXISTING_LYRICS_SYS_PROMPT
            user_prompt = (
                f"════ MUSICAL ARRANGEMENT TARGETS ════\n"
                f"Genre Preset: {req.genre_preset}\n"
                f"Vocal Profile: {req.vocal_profile}\n"
                f"Tempo: {req.bpm} BPM\n"
                f"Intro Style: {req.intro_style}\n"
                f"Custom Style & Direction: {req.custom_style or 'Match genre aesthetic'}\n"
                f"Song Title: {req.song_title or '(Derive from lyrics)'}\n\n"
                f"════ USER'S ORIGINAL LYRICS (MUST BE KEPT 100% VERBATIM) ════\n"
                f"{user_lyrics}\n\n"
                f"════ INSTRUCTIONS ════\n"
                f"1. Inject section & vocal headers: e.g. [Verse 1 - {req.vocal_profile}], [Chorus - Full Band], [Final Chorus - {req.vocal_profile}], [Outro].\n"
                f"2. Inject [Instrumentation: ...] tag for each section with specific instruments, dynamics, and arrangement for {req.genre_preset} at {req.bpm} BPM.\n"
                f"3. Inject [Vocal: ...] tag for each section with vocal delivery cues.\n"
                f"4. KEEP EVERY SINGLE WORD AND LINE OF THE USER'S LYRICS 100% VERBATIM. DO NOT CHANGE, DELETE, OR REWRITE THEIR LYRICS.\n"
                f"5. End with [End] on its own line.\n"
                f"Output raw JSON matching the schema."
            )
            logger.info(f"Enhancing user lyrics with production tags: genre={req.genre_preset}, vocal={req.vocal_profile}, bpm={req.bpm}")
        else:
            # Case 3: No existing lyrics -> Generate complete song from scratch
            sys_prompt = YUE2_GENERATE_FROM_SCRATCH_SYS_PROMPT
            prompt_lines = [
                f"Genre / Style: {req.genre_preset}",
                f"Vocal Profile: {req.vocal_profile}",
                f"Tempo: {req.bpm} BPM",
                f"Intro Style: {req.intro_style}",
                f"Action: Generate complete song with full structure and lyrics from scratch."
            ]
            if req.custom_style:
                prompt_lines.append(f"Acoustic Direction / Theme: {req.custom_style}")
            if req.song_title:
                prompt_lines.append(f"Song Title / Concept: {req.song_title}")
            user_prompt = "\n".join(prompt_lines)
            logger.info(f"Generating full song concept from scratch: genre={req.genre_preset}, model={model}")

        # Direct LLM generation
        raw_output = await _query_llm_direct(
            provider=provider,
            model=model,
            base_url=base_url,
            api_key=api_key,
            sys_prompt=sys_prompt,
            user_prompt=user_prompt,
            temperature=0.72,
            max_tokens=4096
        )

        generated_lyrics, suggested_title = _clean_and_parse_lyrics(raw_output, fallback_title=req.song_title or "")
        if not generated_lyrics:
            raise HTTPException(status_code=500, detail="LLM returned empty lyrics response.")

        prompt_progress[prompt_id] = {
            "stage": "completed",
            "percent": 100,
            "status": "Lyrics processed successfully!",
            "lyrics": generated_lyrics,
            "suggested_title": suggested_title
        }

        # Update session if token provided
        if req.token:
            session = music_session_store.get_session(req.token)
            if session:
                if req.song_title:
                    session.song_title = req.song_title.strip()
                elif suggested_title:
                    session.song_title = suggested_title
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
            "lyrics": generated_lyrics,
            "suggested_title": suggested_title
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Generate lyrics failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class ReviseLyricsRequest(BaseModel):
    instruction: str
    current_lyrics: str
    song_title: Optional[str] = ""
    genre_preset: Optional[str] = "Custom / Keep Only Lyrics"
    vocal_profile: Optional[str] = "Warm Smooth Baritone (Male)"
    bpm: Optional[int] = 120
    custom_style: Optional[str] = ""
    provider: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = ""


REVISION_SYS_PROMPT = """You are an elite AI Music Co-Producer, Topline Writer, and Lyricist in the LINK YuE2 Music Studio.
The user is chatting with you in the Studio Control Room to either:
1. CREATE A BRAND NEW SONG FROM SCRATCH (when no lyrics exist or user asks for a new song with specific structure).
2. SURGICALLY REFINE OR ENHANCE AN EXISTING SONG (modifying a specific section or adding audio production tags while keeping user's lyrics).

════ CASE A: CREATING A NEW SONG FROM SCRATCH ════
If the user asks to write or create a song (or if the lyric sheet is empty):
- Produce a full song strictly matching the structure requested by the user (e.g. Intro, Verse 1, Chorus, Verse 2, Chorus, Bridge, Final Chorus, Outro, or whatever stanzas they ask for).
- Include rich audio tags at each section:
  [Section Name - Vocal Profile]
  [Instrumentation: Dynamic arrangement, instruments, and energy matching the genre and tempo]
  [Vocal: Delivery style, harmonies, ad-libs]
  Example for a chorus:
  [Final Chorus - Male Vocal]
  [Instrumentation: Biggest section. Full drums, deep melodic bass, wide synths, Rhodes, muted guitar accents, stacked harmonies, tasteful vocal ad-libs.]
  [Vocal: Strongest delivery of the song, still controlled and intimate; add tasteful runs only on the final two lines.]
- Always conclude with [End] on its own line.
- Suggest a punchy song title.
- In 'producer_note', describe the song structure you built.

════ CASE B: REVISING AN EXISTING SONG ════
If existing lyrics are provided:
- If user requests a change to a SPECIFIC section (e.g. "change verse 2", "rewrite the hook", "add a bridge"):
  You MUST modify ONLY that section. All other sections, verses, and lines MUST remain 100% UNCHANGED and VERBATIM.
- If user requests to enhance or add instrumentation/vocal tags:
  Inject the tags above each section while keeping ALL existing user lyric lines 100% VERBATIM.
- Always conclude with [End] on its own line.
- In 'producer_note', explain what was modified in a warm, collaborative studio producer tone.

════ RESPONSE FORMAT ════
You MUST respond with a valid JSON object strictly matching this schema:
{
  "producer_note": "Friendly, conversational producer explanation of what you created or changed.",
  "changed_section": "Name of section modified, e.g. 'Verse 2', 'Full Song Structure', or 'Arrangement Tags'",
  "suggested_title": "A punchy 1-4 word song title (or empty string if title already established)",
  "revised_lyrics": "The complete assembled lyrics ready to drop directly into the DAW editor, ending with [End]."
}
IMPORTANT: Output ONLY the raw JSON object. No Markdown code fences, no extra text."""


@router.post("/api/music/revise")
async def revise_lyrics(req: ReviseLyricsRequest):
    """
    Surgically revises existing song lyrics or produces new structured songs via Co-Producer chat,
    preserving non-targeted verses and user lyrics verbatim.
    """
    instruction = req.instruction.strip()
    current_lyrics = (req.current_lyrics or "").strip()

    if not instruction:
        raise HTTPException(status_code=400, detail="Revision instruction cannot be empty.")

    lm_cfg = _get_lmstudio_config()
    provider = req.provider or lm_cfg["provider"]
    base_url = req.base_url or lm_cfg["base_url"]
    api_key = req.api_key or ""
    model = req.model
    if not model:
        live_mods, is_live, _ = await _fetch_live_models(provider, base_url, api_key)
        if lm_cfg.get("model") and is_live and (lm_cfg["model"] in live_mods):
            model = lm_cfg["model"]
        elif is_live and live_mods:
            model = live_mods[0]
        else:
            model = lm_cfg.get("model") or "qwen3.8-27b-uncensored-hauhaucs-aggressive-mtp"

    is_scratch_creation = not current_lyrics or current_lyrics == DEFAULT_LYRICS

    if not is_scratch_creation:
        user_prompt = (
            f"════ MUSICAL CONTEXT ════\n"
            f"Song Title: {req.song_title or '(Not set yet)'}\n"
            f"Genre Preset: {req.genre_preset}\n"
            f"Vocal Profile: {req.vocal_profile}\n"
            f"Tempo: {req.bpm} BPM\n"
            f"Style / Direction: {req.custom_style}\n\n"
            f"════ CURRENT SONG LYRICS (ABOVE) ════\n"
            f"{current_lyrics}\n\n"
            f"════ USER INSTRUCTION / CHANGE REQUEST ════\n"
            f"The user says: \"{instruction}\"\n\n"
            f"Look closely at the CURRENT SONG LYRICS above and execute this requested change.\n"
            f"RULES:\n"
            f"- If the user specified a particular section (e.g. 'change verse 2 out for something different', 'rewrite the chorus', 'add a bridge'), "
            f"you MUST modify ONLY that section and leave ALL other verses, choruses, and structure markers 100% UNTOUCHED and VERBATIM.\n"
            f"- If the user asks to enhance lyrics with instrumentation/vocal tags, add tags while preserving user words 100%.\n"
            f"- Ensure the song concludes with [End]. Respond with raw JSON strictly matching the schema."
        )
    else:
        user_prompt = (
            f"════ MUSICAL CONTEXT ════\n"
            f"Song Title: {req.song_title or '(Not set yet)'}\n"
            f"Genre Preset: {req.genre_preset}\n"
            f"Vocal Profile: {req.vocal_profile}\n"
            f"Tempo: {req.bpm} BPM\n"
            f"Style / Direction: {req.custom_style}\n\n"
            f"════ USER SONG INSTRUCTION (CREATE FROM SCRATCH) ════\n"
            f"The user says: \"{instruction}\"\n\n"
            f"Create a complete song from scratch with the exact structure and theme requested by the user. "
            f"Include section headers ([Verse 1 - {req.vocal_profile}], [Chorus - Full Band], etc.) and "
            f"[Instrumentation: ...] and [Vocal: ...] tags at the start of each section. "
            f"Ensure the song concludes with [End]. Suggest a catchy song title, and write a friendly producer note. Respond with raw JSON."
        )

    raw_resp = await _query_llm_direct(provider, model, base_url, api_key, REVISION_SYS_PROMPT, user_prompt)
    
    parsed = {}
    try:
        cleaned = re.sub(r'^```(?:json)?\s*', '', raw_resp.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r'\s*```$', '', cleaned.strip(), flags=re.MULTILINE)
        parsed = json.loads(cleaned)
    except Exception:
        revised_match = re.search(r'"revised_lyrics"\s*:\s*"([^"]+)"', raw_resp, re.DOTALL)
        note_match = re.search(r'"producer_note"\s*:\s*"([^"]+)"', raw_resp)
        title_match = re.search(r'"suggested_title"\s*:\s*"([^"]+)"', raw_resp)
        parsed = {
            "revised_lyrics": revised_match.group(1).encode().decode('unicode_escape') if revised_match else raw_resp,
            "producer_note": note_match.group(1) if note_match else "Lyrics revised according to your instructions.",
            "suggested_title": title_match.group(1) if title_match else ""
        }

    revised_lyrics = parsed.get("revised_lyrics", req.current_lyrics)
    producer_note = parsed.get("producer_note", "Lyrics updated on screen!")
    suggested_title = parsed.get("suggested_title", "")
    changed_section = parsed.get("changed_section", "Song Structure" if is_scratch_creation else "Updated Section")

    if not revised_lyrics.rstrip().endswith("[End]"):
        revised_lyrics = revised_lyrics.rstrip() + "\n\n[End]"

    return {
        "status": "success",
        "revised_lyrics": revised_lyrics,
        "producer_note": producer_note,
        "suggested_title": suggested_title,
        "changed_section": changed_section
    }


class GenerateSongRequest(BaseModel):
    token: Optional[str] = None
    song_title: Optional[str] = ""
    title: Optional[str] = None
    song_name: Optional[str] = None
    track_name: Optional[str] = None
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
    cot: Optional[str] = "full"
    checkpoint: Optional[str] = "yue2_3b_bf16.safetensors"
    sampler_name: Optional[str] = "dpm_2"
    scheduler: Optional[str] = "sgm_uniform"
    max_duration: Optional[float] = 360.0
    provider: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = ""


@router.post("/api/music/generate")
async def generate_song(req: GenerateSongRequest):
    """
    Executes the full music studio workflow.
    Enables Node 5 (YuE2 Neural Song Generator) and Node 6 (YuE2 Audio Preview & Saver).
    Returns the prompt_id for progress tracking.
    """
    try:
        wf = _load_base_workflow()

        # Resolve effective song title from request, session, or smart fallbacks
        session = music_session_store.get_session(req.token) if req.token else None
        if not session:
            raise HTTPException(
                status_code=403,
                detail="Active studio session required. Please run /music in Discord to start a session."
            )
        music_session_store.touch_session(req.token)
        effective_title = resolve_song_title(req, session)
        req.song_title = effective_title
        logger.info(f"Resolved song title for prompt: '{effective_title}' (raw req.song_title='{getattr(req, 'song_title', '')}')")

        # Update session with current values
        session.take_count = getattr(session, "take_count", 0) + 1
        session.status = "generating"
        if effective_title:
            session.song_title = effective_title
        session.custom_style = req.custom_style
        session.genre_preset = req.genre_preset
        session.vocal_profile = req.vocal_profile
        session.bpm = int(req.bpm)
        session.intro_style = req.intro_style
        session.action = req.action
        session.lyrics = req.lyrics

        # Update Node 6 filename prefix so ComfyUI outputs clean song name
        clean_prefix = sanitize_song_title(effective_title, fallback="studio_song")
        if "6" in wf and "inputs" in wf["6"]:
            wf["6"]["inputs"]["filename_prefix"] = f"YuE2/{clean_prefix}"
        
        # 1. Update Node 1
        lyrics_text = req.lyrics if req.lyrics.strip() else DEFAULT_LYRICS
        wf["1"]["inputs"]["genre_preset"] = req.genre_preset
        wf["1"]["inputs"]["vocal_profile"] = req.vocal_profile
        wf["1"]["inputs"]["bpm"] = int(req.bpm)
        wf["1"]["inputs"]["intro_style"] = req.intro_style
        wf["1"]["inputs"]["custom_style"] = req.custom_style
        wf["1"]["inputs"]["lyrics"] = lyrics_text
        
        # 2. Seed Handling
        if req.seed is not None and req.seed >= 0:
            final_seed = int(req.seed)
        else:
            final_seed = random.randint(100000000000, 999999999999)

        # 3. Dynamic Generator Node Discovery & Parameter Injection
        # Finds whichever node is YuE2SongGenerator (e.g. Node 16 or Node 5)
        gen_node_id = None
        for nid, node in wf.items():
            if isinstance(node, dict) and node.get("class_type") == "YuE2SongGenerator":
                gen_node_id = nid
                break

        if gen_node_id and gen_node_id in wf:
            gen_inputs = wf[gen_node_id].setdefault("inputs", {})
            gen_inputs["seed"] = final_seed
            if req.ode_steps and 12 <= req.ode_steps <= 64:
                gen_inputs["ode_steps"] = int(req.ode_steps)
            if req.cot in ["full", "melody", "off"]:
                gen_inputs["cot"] = req.cot
            if req.checkpoint:
                gen_inputs["checkpoint"] = req.checkpoint
            if req.sampler_name:
                gen_inputs["sampler_name"] = req.sampler_name
            if req.scheduler:
                gen_inputs["scheduler"] = req.scheduler
            if req.max_duration:
                gen_inputs["max_duration"] = float(req.max_duration)
            logger.info(f"Configured generator Node {gen_node_id} (YuE2SongGenerator): seed={final_seed}, ode_steps={gen_inputs.get('ode_steps')}, cot={gen_inputs.get('cot')}")

        # Support legacy Node 4 and Node 5 if present in older custom workflows
        if "4" in wf and "inputs" in wf["4"]:
            wf["4"]["inputs"]["seed"] = final_seed
        if "5" in wf and "inputs" in wf["5"] and req.ode_steps and 12 <= req.ode_steps <= 64:
            wf["5"]["inputs"]["ode_steps"] = int(req.ode_steps)

        # 4. Routing: Disables LLM (Node 3) so generated lyrics are NEVER overwritten
        # Route Node 1's custom style & acoustic direction directly to Node 12 (Style Switch)
        if "12" in wf and "inputs" in wf["12"]:
            wf["12"]["inputs"]["any_01"] = ["1", 0]
        # Route Node 1's lyrics (from editor / generated lyrics) directly to Node 13 (Lyrics Switch)
        if "13" in wf and "inputs" in wf["13"]:
            wf["13"]["inputs"]["any_01"] = ["1", 1]
        # Route Node 13 directly to Node 14 so Output Lyrics captures the exact synthesized lyrics
        if "14" in wf and "inputs" in wf["14"]:
            wf["14"]["inputs"]["text"] = ["13", 0]
            wf["14"]["inputs"].pop("text_0", None)
        # Disconnect and remove Node 3 completely so ComfyUI NEVER runs the LLM during song generation
        wf.pop("3", None)
        logger.info(f"Song generation: Node 3 (LLM) disabled. Node 1 style -> Node 12, Node 1 lyrics -> Node 13 -> Node 14 -> Node {gen_node_id or '16'}")

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
            "percent": 8,
            "status": "Starting full music generation pipeline...",
            "started_at": time.time(),
            "seed": final_seed,
            "lyrics": lyrics_text,
            "token": req.token,
            "client_id": client_id
        }

        # Launch background monitor to track execution, save audio, and notify Discord if applicable
        asyncio.create_task(_monitor_song_generation(prompt_id, req, client_id))

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


async def _track_comfy_ws(prompt_id: str, client_id: str):
    """Listens to ComfyUI WebSocket events for live execution step and diffusion progress."""
    ws_url = f"{Config.COMFY_WS_URL}?clientId={client_id}"
    logger.info(f"Connecting to ComfyUI WebSocket for prompt {prompt_id}: {ws_url}")
    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.ws_connect(ws_url, timeout=aiohttp.ClientTimeout(total=10)) as ws:
                async for msg in ws:
                    curr = prompt_progress.get(prompt_id)
                    if not curr or curr.get("stage") in ["completed", "failed"]:
                        break
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            payload = json.loads(msg.data)
                            m_type = payload.get("type")
                            m_data = payload.get("data", {})

                            if m_data.get("prompt_id") and m_data.get("prompt_id") != prompt_id:
                                continue

                            if m_type == "execution_start":
                                curr["stage"] = "executing"
                                curr["percent"] = max(curr.get("percent", 8), 12)
                                curr["status"] = "ComfyUI pipeline initialized..."
                            
                            elif m_type == "executing":
                                node = str(m_data.get("node"))
                                if node in ["1", "12", "13", "14"]:
                                    curr["stage"] = "executing"
                                    curr["percent"] = max(curr.get("percent", 8), 16)
                                    curr["status"] = "Conditioning acoustic tokens & lyrics..."
                                elif node in ["16", "5", "4"]:
                                    curr["stage"] = "executing"
                                    curr["percent"] = max(curr.get("percent", 8), 20)
                                    curr["status"] = "YuE2 ODE Neural Diffusion running..."
                                elif node == "6":
                                    curr["stage"] = "executing"
                                    curr["percent"] = max(curr.get("percent", 8), 94)
                                    curr["status"] = "Encoding 24-bit studio MP3 master..."

                            elif m_type == "progress":
                                val = m_data.get("value", 0)
                                max_val = m_data.get("max", 1)
                                if max_val > 0:
                                    diff_pct = val / max_val
                                    # Scale diffusion smoothly between 20% and 92%
                                    overall_pct = int(20 + diff_pct * 72)
                                    curr["stage"] = "executing"
                                    curr["percent"] = max(curr.get("percent", 20), min(92, overall_pct))
                                    curr["current_step"] = val
                                    curr["total_steps"] = max_val
                                    curr["status"] = f"Neural Diffusion: Step {val}/{max_val} ({int(diff_pct * 100)}%)"

                            elif m_type == "execution_error":
                                curr["stage"] = "failed"
                                curr["error"] = m_data.get("exception_message", "ComfyUI execution error")
                                curr["status"] = f"Execution failed: {curr['error']}"
                                break

                        except Exception:
                            pass
                    elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                        break
    except Exception as e:
        logger.debug(f"ComfyUI WS listener connection skipped or ended for {prompt_id}: {e}")


async def _send_discord_progress_start(session, req: GenerateSongRequest, prompt_id: str):
    """Sends an initial real-time progress card into the Discord channel."""
    bot = state.bot_instance
    if not bot or not getattr(session, "channel_id", None):
        return
    try:
        import discord
        channel = bot.get_channel(int(session.channel_id))
        if not channel:
            return

        take_num = getattr(session, "take_count", 1)
        effective_title = resolve_song_title(req, session) or "YuE2 Studio Master Track"
        take_label = f" (Take #{take_num})" if take_num > 1 else ""

        empty_bar = "░" * 10
        embed = discord.Embed(
            title=f"🎵 Generating: {effective_title}{take_label}",
            description=(
                f"**Producer**: <@{session.user_id}>\n"
                f"**Genre**: `{req.genre_preset}` • **Tempo**: `{req.bpm} BPM`\n"
                f"**Vocal Profile**: `{req.vocal_profile}`\n\n"
                f"**Status**: `Starting neural generation pipeline...`\n"
                f"`[{empty_bar}]` **0%** (0s elapsed)\n\n"
                f"🎛️ *Synthesizing in YuE2 Studio...*"
            ),
            color=discord.Color.from_rgb(139, 92, 246)
        )
        embed.set_footer(text="YuE2 Neural Music Generator • Powered by LINK")

        msg = await channel.send(
            content=f"🎶 <@{session.user_id}> started generating **{effective_title}**{take_label}...",
            embed=embed,
            view=None
        )
        session.progress_message_id = str(msg.id)
        logger.info(f"Dispatched initial Discord progress message {msg.id} for prompt {prompt_id}")
    except Exception as e:
        logger.warning(f"Failed to post initial Discord progress: {e}")


async def _update_discord_progress(session, req: GenerateSongRequest, prompt_id: str, curr_info: dict, elapsed_sec: int):
    """Edits the active Discord progress card with current percentage and stage."""
    bot = state.bot_instance
    if not bot or not getattr(session, "progress_message_id", None):
        return
    try:
        import discord
        channel = bot.get_channel(int(session.channel_id))
        if not channel:
            return
        try:
            msg = channel.get_partial_message(int(session.progress_message_id))
        except Exception:
            msg = await channel.fetch_message(int(session.progress_message_id))
        if not msg:
            return

        pct = max(0, min(100, int(curr_info.get("percent", 10))))
        bar_len = 10
        filled = int(bar_len * pct // 100)
        bar = "█" * filled + "░" * (bar_len - filled)

        status_text = curr_info.get("status", "YuE2 ODE Neural Diffusion running...")
        effective_title = resolve_song_title(req, session) or "YuE2 Studio Master Track"
        take_num = getattr(session, "take_count", 1)
        take_label = f" (Take #{take_num})" if take_num > 1 else ""

        embed = discord.Embed(
            title=f"🎵 Generating: {effective_title}{take_label}",
            description=(
                f"**Producer**: <@{session.user_id}>\n"
                f"**Genre**: `{req.genre_preset}` • **Tempo**: `{req.bpm} BPM`\n"
                f"**Vocal Profile**: `{req.vocal_profile}`\n\n"
                f"**Status**: `{status_text}`\n"
                f"`[{bar}]` **{pct}%** ({elapsed_sec}s elapsed)\n\n"
                f"🎛️ *Synthesizing in YuE2 Studio...*"
            ),
            color=discord.Color.from_rgb(168, 85, 247)
        )
        embed.set_footer(text="YuE2 Neural Music Generator • Powered by LINK")

        await msg.edit(
            content=f"🎶 <@{session.user_id}> generating **{effective_title}**{take_label}... (`{pct}%`)",
            embed=embed,
            view=None
        )
    except Exception as e:
        logger.debug(f"Discord progress update skipped: {e}")


async def _monitor_song_generation(prompt_id: str, req: GenerateSongRequest, client_id: str):
    """Background monitor that tracks ComfyUI execution, saves audio, and posts live progress to Discord."""
    logger.info(f"Monitoring song generation for prompt {prompt_id} (client_id={client_id})")
    max_wait_seconds = 600 # 10 minutes maximum for neural audio synthesis
    start_time = time.time()
    
    # Start real-time WebSocket progress tracker
    ws_task = asyncio.create_task(_track_comfy_ws(prompt_id, client_id))

    # Send initial Discord progress post
    session = music_session_store.get_session(req.token) if req.token else None
    if session:
        await _send_discord_progress_start(session, req, prompt_id)
    last_discord_update = time.time()
    last_discord_percent = -1
    consecutive_poll_errors = 0
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as sess:
            while time.time() - start_time < max_wait_seconds:
                await asyncio.sleep(2.0)
                elapsed = time.time() - start_time
                
                # Smooth fallback progression if WebSocket ODE steps aren't reported
                curr = prompt_progress.get(prompt_id)
                if curr and curr.get("stage") not in ["completed", "failed"]:
                    if "current_step" not in curr:
                        # Asymptotic curve that rises smoothly towards 93% over 90s without stalling at 88%
                        sim_pct = int(12 + (81 * (1 - math.exp(-elapsed / 45))))
                        curr["percent"] = max(curr.get("percent", 12), min(93, sim_pct))
                        if curr["percent"] < 20:
                            curr["status"] = f"Conditioning acoustic tokens & lyrics ({int(elapsed)}s elapsed)..."
                        elif curr["percent"] < 92:
                            curr["status"] = f"YuE2 ODE Neural Diffusion in progress ({int(elapsed)}s elapsed)..."
                        else:
                            curr["status"] = f"Finalizing audio master ({int(elapsed)}s elapsed)..."

                # Discord progress update (throttled to every 4.0s or on step milestone)
                now = time.time()
                if session and getattr(session, "progress_message_id", None):
                    curr_pct = curr.get("percent", 10) if curr else 10
                    if (now - last_discord_update >= 4.0 and curr_pct != last_discord_percent) or curr_pct >= 94:
                        last_discord_update = now
                        last_discord_percent = curr_pct
                        try:
                            await _update_discord_progress(session, req, prompt_id, curr or {}, int(elapsed))
                        except Exception as prog_e:
                            logger.debug(f"Discord progress update failed: {prog_e}")

                # Poll ComfyUI history with dedicated timeout and error catching
                try:
                    async with sess.get(f"{Config.COMFY_URL}/history/{prompt_id}") as h_resp:
                        if h_resp.status != 200:
                            continue
                        h_data = await h_resp.json()
                        if prompt_id not in h_data:
                            continue
                        
                        consecutive_poll_errors = 0
                        prompt_entry = h_data[prompt_id]
                        outputs = prompt_entry.get("outputs", {})
                        
                        # Check for audio output in Node 6 or any audio-producing node
                        audio_list = None
                        if "6" in outputs and "audio" in outputs["6"]:
                            audio_list = outputs["6"]["audio"]
                        else:
                            for n_id, n_out in outputs.items():
                                if isinstance(n_out, dict) and "audio" in n_out and n_out["audio"]:
                                    audio_list = n_out["audio"]
                                    break

                        if audio_list:
                            audio_meta = audio_list[0]
                            filename = audio_meta.get("filename")
                            subfolder = audio_meta.get("subfolder", "")
                            folder_type = audio_meta.get("type", "output")
                            
                            logger.info(f"Song completed for {prompt_id}: {filename} (subfolder={subfolder})")
                            
                            # Download audio bytes from ComfyUI
                            audio_url_params = f"?filename={filename}&subfolder={subfolder}&type={folder_type}"
                            audio_bytes = None
                            try:
                                async with sess.get(f"{Config.COMFY_URL}/view{audio_url_params}", timeout=aiohttp.ClientTimeout(total=60)) as v_resp:
                                    if v_resp.status == 200:
                                        audio_bytes = await v_resp.read()
                            except Exception as dl_e:
                                logger.warning(f"Error reading audio bytes from ComfyUI: {dl_e}")

                            if audio_bytes:
                                effective_title = resolve_song_title(req, session)
                                clean_name = sanitize_song_title(effective_title, fallback="studio_song")
                                display_title = effective_title or "YuE2 Studio Master Track"
                                take_num = getattr(session, "take_count", 1) if session else 1
                                
                                # Save to assets directory with clean name + prompt id suffix for disk uniqueness
                                local_filename = f"{clean_name}_{prompt_id[:8]}.mp3"
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
                                    "song_title": display_title,
                                    "clean_title": clean_name,
                                    "take_count": take_num,
                                    "lyrics": output_lyrics or req.lyrics,
                                    "completed_at": time.time()
                                }
                                
                                # Cancel WS task
                                if not ws_task.done():
                                    ws_task.cancel()

                                # If Discord session exists, notify channel with full audio + persistent Fine-Tune button
                                if req.token:
                                    try:
                                        await _dispatch_discord_completion(req.token, local_path, local_filename, req, output_lyrics)
                                    except Exception as disp_e:
                                        logger.error(f"Error dispatching completion to Discord: {disp_e}", exc_info=True)
                                
                                return
                        
                        # Check for errors reported by ComfyUI
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
                            if not ws_task.done():
                                ws_task.cancel()
                            if session and getattr(session, "progress_message_id", None):
                                try:
                                    bot = state.bot_instance
                                    if bot:
                                        ch = bot.get_channel(int(session.channel_id))
                                        if ch:
                                            try:
                                                p_msg = ch.get_partial_message(int(session.progress_message_id))
                                            except Exception:
                                                p_msg = await ch.fetch_message(int(session.progress_message_id))
                                            await p_msg.edit(content=f"❌ <@{session.user_id}>, song generation failed: `{err_msg}`")
                                except Exception: pass
                            return

                except (asyncio.TimeoutError, aiohttp.ClientError) as poll_err:
                    consecutive_poll_errors += 1
                    if consecutive_poll_errors % 5 == 0:
                        logger.debug(f"ComfyUI history endpoint busy or slow to respond ({consecutive_poll_errors} consecutive timeouts): {poll_err}")
                    continue
                except Exception as loop_e:
                    logger.warning(f"Transient error in ComfyUI history loop for {prompt_id} (will retry): {loop_e}")
                    continue

        # Timeout reached
        logger.warning(f"Song generation timed out for {prompt_id}")
        prompt_progress[prompt_id] = {
            "stage": "failed",
            "percent": 0,
            "status": "Song generation timed out after 10 minutes.",
            "error": "Timeout"
        }
        if not ws_task.done():
            ws_task.cancel()

    except Exception as e:
        logger.error(f"Song monitor error for {prompt_id}: {e}", exc_info=True)
        prompt_progress[prompt_id] = {
            "stage": "failed",
            "percent": 0,
            "status": f"Monitoring error: {e}",
            "error": str(e)
        }
        if not ws_task.done():
            ws_task.cancel()


async def _dispatch_discord_completion(token: str, local_path: str, filename: str, req: GenerateSongRequest, lyrics: str):
    """Posts the generated audio and lyrics back to the Discord channel with a persistent Fine-Tune button."""
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

        clean_name = sanitize_song_title(req.song_title, fallback="YuE2_Master_Track")
        effective_title = resolve_song_title(req, session)
        if effective_title:
            clean_name = sanitize_song_title(effective_title, fallback="YuE2_Master_Track")
        display_title = effective_title or "YuE2 Studio Master Track"
        take_num = getattr(session, "take_count", 1)
        take_label = f" (Take #{take_num})" if take_num > 1 else ""

        domain = (Config.INPAINT_SERVER_DOMAIN or "").strip()
        studio_url = f"https://{domain}/music/?token={session.token}" if domain else f"http://localhost:{Config.INPAINT_SERVER_PORT}/music/?token={session.token}"

        desc_lines = []
        if effective_title:
            desc_lines.append(f"🎶 **Track**: **{display_title}**{take_label}")
        desc_lines.extend([
            f"**Producer**: <@{session.user_id}>",
            f"**Genre**: `{req.genre_preset}`",
            f"**Vocal Profile**: `{req.vocal_profile}`",
            f"**Tempo**: `{req.bpm} BPM`",
            f"**Intro**: `{req.intro_style}`",
            f"**Style**: *{req.custom_style[:120]}*",
            "",
            "🎧 **Master audio delivered below!**"
        ])

        embed = discord.Embed(
            title="🎵 LINK Music Studio — Song Generated!",
            description="\n".join(desc_lines),
            color=discord.Color.from_rgb(16, 185, 129) # Vibrant Emerald Green
        )
        embed.set_footer(text="YuE2 Neural Music Generator • Powered by LINK")

        discord_filename = f"{clean_name}_Take{take_num}.mp3" if take_num > 1 else f"{clean_name}.mp3"
        file_to_send = discord.File(local_path, filename=discord_filename)
        msg_content = f"🎵 <@{session.user_id}>, your song **{display_title}**{take_label} is ready!"

        # If a live progress message was created, update it to completion and send the audio file
        if getattr(session, "progress_message_id", None):
            try:
                prog_msg = await channel.fetch_message(int(session.progress_message_id))
                await prog_msg.edit(content=msg_content, embed=embed, view=None)
                await channel.send(
                    content=f"🎧 **Master Audio Track**{take_label} for **{display_title}**:",
                    file=file_to_send
                )
            except Exception:
                await channel.send(content=msg_content, embed=embed, file=file_to_send)
        else:
            await channel.send(content=msg_content, embed=embed, file=file_to_send)

        music_session_store.mark_completed(token, f"/api/music/audio/{filename}")
        session.status = "completed"
        logger.info(f"Dispatched music completion to Discord channel {session.channel_id} with file {discord_filename}")

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
