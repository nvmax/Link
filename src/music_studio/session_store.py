import time
import uuid
from dataclasses import dataclass
from typing import Dict, Optional
from src.core.logger import setup_logger

logger = setup_logger(__name__)

@dataclass
class MusicSession:
    token: str
    user_id: str
    user_name: str
    guild_id: Optional[str]
    channel_id: str
    message_id: Optional[str]
    genre_preset: str = "Custom / Keep Only Lyrics"
    vocal_profile: str = "Warm Smooth Baritone (Male)"
    bpm: int = 120
    intro_style: str = "None"
    custom_style: str = "Style of Bruno Mars song Risk It All"
    song_title: str = ""
    lyrics: str = ""
    action: str = "Generate Full Song Concept"
    audio_url: Optional[str] = None
    status: str = "idle"
    created_at: float = 0.0
    completed_at: Optional[float] = None
    expired: bool = False

    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()

class MusicSessionStore:
    def __init__(self, ttl_seconds: int = 3600): # 1 hour default
        self.sessions: Dict[str, MusicSession] = {}
        self.ttl_seconds = ttl_seconds

    def create_session(
        self,
        user_id: str,
        user_name: str,
        channel_id: str,
        guild_id: Optional[str] = None,
        message_id: Optional[str] = None,
        custom_style: str = "",
        song_title: str = "",
        lyrics: str = "",
        genre_preset: str = "Custom / Keep Only Lyrics",
        vocal_profile: str = "Warm Smooth Baritone (Male)",
        bpm: int = 120,
        intro_style: str = "None",
        action: str = "Generate Full Song Concept",
    ) -> MusicSession:
        self.cleanup_expired()
        token = uuid.uuid4().hex
        session = MusicSession(
            token=token,
            user_id=str(user_id),
            user_name=user_name,
            guild_id=str(guild_id) if guild_id else None,
            channel_id=str(channel_id),
            message_id=str(message_id) if message_id else None,
            genre_preset=genre_preset,
            vocal_profile=vocal_profile,
            bpm=bpm,
            intro_style=intro_style,
            custom_style=custom_style or "Style of Bruno Mars song Risk It All",
            song_title=song_title,
            lyrics=lyrics,
            action=action,
        )
        self.sessions[token] = session
        logger.info(f"Created music studio session {token} for user {user_name} ({user_id})")
        return session

    def get_session(self, token: str) -> Optional[MusicSession]:
        self.cleanup_expired()
        session = self.sessions.get(token)
        if not session:
            return None
        if time.time() - session.created_at > self.ttl_seconds or session.expired:
            session.expired = True
            logger.info(f"Music session {token} has expired")
            return None
        return session

    def get_active_session_for_user(self, user_id: str) -> Optional[MusicSession]:
        self.cleanup_expired()
        user_id_str = str(user_id)
        user_sessions = [
            s for s in self.sessions.values()
            if s.user_id == user_id_str and not s.expired and (time.time() - s.created_at <= self.ttl_seconds)
        ]
        if not user_sessions:
            return None
        return max(user_sessions, key=lambda s: s.created_at)

    def mark_completed(self, token: str, audio_url: Optional[str] = None):
        session = self.sessions.get(token)
        if session:
            session.status = "completed"
            session.audio_url = audio_url
            session.completed_at = time.time()
            logger.info(f"Marked music session {token} as completed")

    def cleanup_expired(self):
        now = time.time()
        expired_tokens = [
            t for t, s in self.sessions.items()
            if (now - s.created_at > self.ttl_seconds) or s.expired
        ]
        for t in expired_tokens:
            del self.sessions[t]

music_session_store = MusicSessionStore()
