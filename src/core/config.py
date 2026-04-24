import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    COMFY_URL = os.getenv("COMFY_URL", "http://127.0.0.1:8188").rstrip("/")
    FLUX_MODEL = os.getenv("FLUX_MODEL", "fluxFusionV24StepsGGUFNF4_V2GGUFQ3KM.gguf")
    FLUX_STEPS = int(os.getenv("FLUX_STEPS", "4"))
    COMFY_WS_URL = COMFY_URL.replace("http", "ws") + "/ws"
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/link.db")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Lockdown Settings
    _guild_id = os.getenv("ALLOWED_GUILD_ID")
    ALLOWED_GUILD_ID = int(_guild_id) if _guild_id else None
    
    _channel_id = os.getenv("ALLOWED_CHANNEL_ID")
    ALLOWED_CHANNEL_ID = int(_channel_id) if _channel_id else None
    
    # Paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    WORKFLOWS_DIR = os.path.join(BASE_DIR, "src", "workflows")
    LORAS_DIR = os.path.join(WORKFLOWS_DIR, "loras")
    DATA_DIR = os.path.join(BASE_DIR, "data")
    LOGS_DIR = os.path.join(BASE_DIR, "logs")
    ASSETS_DIR = os.path.join(DATA_DIR, "assets")

    # Create directories if they don't exist
    for path in [DATA_DIR, LOGS_DIR, ASSETS_DIR, WORKFLOWS_DIR, LORAS_DIR]:
        os.makedirs(path, exist_ok=True)
