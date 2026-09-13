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
    take_count: int = 0
    progress_message_id: Optional[str] = None
    opened_at: Optional[float] = None
    last_heartbeat: float = 0.0
    closed: bool = False
    closing: bool = False
    closed_at: Optional[float] = None

    def __post_init__(self):
        now = time.time()
        if self.created_at == 0.0:
            self.created_at = now
        if self.last_heartbeat == 0.0:
            self.last_heartbeat = now


class MusicSessionStore:
    def __init__(self, ttl_seconds: int = 3600):  # 1 hour max session lifetime
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
        user_id_str = str(user_id)

        # Invalidate any prior active session for this user so only the newest /music link works
        for s in self.sessions.values():
            if s.user_id == user_id_str and not s.closed and not s.expired:
                s.closed = True
                s.expired = True
                logger.info(f"Invalidated previous music session {s.token} for user {user_name} ({user_id_str})")

        token = uuid.uuid4().hex
        now = time.time()
        session = MusicSession(
            token=token,
            user_id=user_id_str,
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
            created_at=now,
            last_heartbeat=now,
        )
        self.sessions[token] = session
        logger.info(f"Created music studio session {token} for user {user_name} ({user_id})")
        return session

    def get_session(self, token: str) -> Optional[MusicSession]:
        self.cleanup_expired()
        session = self.sessions.get(token)
        if not session:
            return None

        now = time.time()
        # Explicitly closed or expired
        if session.closed or session.expired:
            return None

        # Check closing grace window (e.g. browser tab refresh within 8 seconds)
        if session.closing:
            if session.closed_at and (now - session.closed_at > 8.0):
                session.closed = True
                session.expired = True
                session.closing = False
                logger.info(f"Session {token} grace period expired -> marked permanently closed")
                return None
            else:
                # Reconnected during grace window
                session.closing = False
                session.last_heartbeat = now
                return session

        # Unopened session TTL: user must open the link within 15 minutes of running /music
        if session.opened_at is None:
            if now - session.created_at > 900.0:
                session.expired = True
                session.closed = True
                logger.info(f"Unopened music session {token} expired (>15 min)")
                return None
            return session

        # Opened session: check heartbeat timeout (60s without heartbeat means studio was abandoned)
        if now - session.last_heartbeat > 60.0:
            session.closed = True
            session.expired = True
            logger.info(f"Opened music session {token} timed out (no heartbeat for >60s)")
            return None

        # Max TTL check
        if now - session.created_at > self.ttl_seconds:
            session.expired = True
            session.closed = True
            logger.info(f"Music session {token} reached maximum TTL ({self.ttl_seconds}s)")
            return None

        return session

    def touch_session(self, token: str) -> bool:
        session = self.get_session(token)
        if not session:
            return False
        now = time.time()
        if session.opened_at is None:
            session.opened_at = now
        session.last_heartbeat = now
        session.closing = False
        return True

    def close_session(self, token: str, immediate: bool = False):
        session = self.sessions.get(token)
        if not session:
            return
        if immediate:
            session.closed = True
            session.expired = True
            session.closing = False
            logger.info(f"Immediately closed music session {token}")
        else:
            session.closing = True
            session.closed_at = time.time()
            logger.info(f"Marked music session {token} closing (8s grace window)")

    def get_active_session_for_user(self, user_id: str) -> Optional[MusicSession]:
        self.cleanup_expired()
        user_id_str = str(user_id)
        user_sessions = [
            s for s in self.sessions.values()
            if s.user_id == user_id_str and not s.closed and not s.expired and (time.time() - s.created_at <= self.ttl_seconds)
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
            session.last_heartbeat = time.time()
            logger.info(f"Marked music session {token} as completed")

    def cleanup_expired(self):
        now = time.time()
        to_delete = []
        for t, s in self.sessions.items():
            if s.closed or s.expired:
                # Keep tombstone around for 10 minutes so incoming requests know it was closed
                if s.closed_at and (now - s.closed_at > 600.0):
                    to_delete.append(t)
                elif now - s.created_at > self.ttl_seconds:
                    to_delete.append(t)
            elif now - s.created_at > self.ttl_seconds:
                s.expired = True
                s.closed = True
                to_delete.append(t)

        for t in to_delete:
            self.sessions.pop(t, None)


music_session_store = MusicSessionStore()
