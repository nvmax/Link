import os
from dotenv import load_dotenv

load_dotenv(override=True)

class Config:
    IS_DOCKER = os.path.exists('/.dockerenv') or os.path.exists('/run/.containerenv')

    # Paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    LOGS_DIR = os.path.join(BASE_DIR, "logs")
    ASSETS_DIR = os.path.join(DATA_DIR, "assets")
    WORKFLOWS_DIR = os.path.join(BASE_DIR, "src", "workflows")
    LORAS_DIR = os.path.join(WORKFLOWS_DIR, "loras")
    AI_STUDIO_DIR = os.path.join(BASE_DIR, "src", "ai_studio")

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(DATA_DIR, 'link.db')}")
    
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

    COMFY_URL = os.getenv("COMFY_URL", "http://127.0.0.1:8188").rstrip("/")
    if IS_DOCKER:
        COMFY_URL = COMFY_URL.replace("127.0.0.1", "host.docker.internal").replace("localhost", "host.docker.internal")

    FLUX_MODEL = os.getenv("FLUX_MODEL", "fluxFusionV24StepsGGUFNF4_V2GGUFQ3KM.gguf")
    FLUX_STEPS = int(os.getenv("FLUX_STEPS", "4"))
    COMFY_WS_URL = COMFY_URL.replace("http", "ws") + "/ws"

    COMFY_PATH = os.getenv("COMFY_PATH", "").rstrip("/\\")
    if IS_DOCKER:
        COMFY_PATH = "/comfyui"

    HF_TOKEN = os.getenv("HF_TOKEN", "").strip()
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    API_KEY = os.getenv("API_KEY")
    
    # Inpaint Activity Settings
    DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "").strip()
    INPAINT_SERVER_DOMAIN = os.getenv("INPAINT_SERVER_DOMAIN", "").strip()
    INPAINT_SERVER_PORT = int(os.getenv("INPAINT_SERVER_PORT", "8000"))
    
    # Lockdown Settings
    _guild_ids = os.getenv("ALLOWED_GUILD_ID", "")
    ALLOWED_GUILD_IDS = [int(x.strip()) for x in _guild_ids.split(",") if x.strip().isdigit()]
    ALLOWED_GUILD_ID = ALLOWED_GUILD_IDS[0] if ALLOWED_GUILD_IDS else None
    
    _channel_ids = os.getenv("ALLOWED_CHANNEL_ID", "")
    ALLOWED_CHANNEL_IDS = [int(x.strip()) for x in _channel_ids.split(",") if x.strip().isdigit()]
    ALLOWED_CHANNEL_ID = ALLOWED_CHANNEL_IDS[0] if ALLOWED_CHANNEL_IDS else None

    @classmethod
    def ensure_directories(cls):
        """Creates standard directories if they don't exist yet."""
        for path in [cls.DATA_DIR, cls.LOGS_DIR, cls.ASSETS_DIR, cls.WORKFLOWS_DIR, cls.LORAS_DIR, cls.AI_STUDIO_DIR]:
            os.makedirs(path, exist_ok=True)

    @classmethod
    def validate_environment(cls):
        """Verifies the presence of required environment variables."""
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            print("\n" + "="*50)
            print("❌ ERROR: DISCORD_TOKEN not found!")
            print("="*50)
            print("It looks like you haven't set up your .env file yet.")
            print("1. Create a file named '.env' in the root directory.")
            print("2. Add your token: DISCORD_TOKEN=your_token_here")
            print("3. Restart the bot.")
            print("="*50 + "\n")
            import sys
            sys.exit(1)

    @classmethod
    def reload(cls):
        """Re-read .env so changes saved via the dashboard take effect immediately."""
        load_dotenv(override=True)
        cls.API_KEY       = os.getenv("API_KEY")
        
        comfy_path = os.getenv("COMFY_PATH", "").rstrip("/\\")
        cls.COMFY_PATH    = "/comfyui" if cls.IS_DOCKER else comfy_path
        
        comfy_url = os.getenv("COMFY_URL",  "http://127.0.0.1:8188").rstrip("/")
        if cls.IS_DOCKER:
            comfy_url = comfy_url.replace("127.0.0.1", "host.docker.internal").replace("localhost", "host.docker.internal")
        cls.COMFY_URL     = comfy_url
        cls.COMFY_WS_URL  = cls.COMFY_URL.replace("http", "ws") + "/ws"
        
        cls.HF_TOKEN      = os.getenv("HF_TOKEN", "").strip()
        _guild_ids        = os.getenv("ALLOWED_GUILD_ID", "")
        cls.ALLOWED_GUILD_IDS  = [int(x.strip()) for x in _guild_ids.split(",") if x.strip().isdigit()]
        cls.ALLOWED_GUILD_ID   = cls.ALLOWED_GUILD_IDS[0] if cls.ALLOWED_GUILD_IDS else None
        _channel_ids      = os.getenv("ALLOWED_CHANNEL_ID", "")
        cls.ALLOWED_CHANNEL_IDS  = [int(x.strip()) for x in _channel_ids.split(",") if x.strip().isdigit()]
        cls.ALLOWED_CHANNEL_ID   = cls.ALLOWED_CHANNEL_IDS[0] if cls.ALLOWED_CHANNEL_IDS else None

        cls.DISCORD_CLIENT_ID     = os.getenv("DISCORD_CLIENT_ID", "").strip()
        cls.INPAINT_SERVER_DOMAIN = os.getenv("INPAINT_SERVER_DOMAIN", "").strip()
        try:
            cls.INPAINT_SERVER_PORT = int(os.getenv("INPAINT_SERVER_PORT", "8000"))
        except ValueError:
            cls.INPAINT_SERVER_PORT = 8000
