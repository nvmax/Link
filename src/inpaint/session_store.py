import time
import uuid
import logging
from dataclasses import dataclass
from typing import Dict, Optional
from src.core.logger import setup_logger

logger = setup_logger(__name__)

@dataclass
class InpaintSession:
    token: str
    user_id: str
    user_name: str
    guild_id: Optional[str]
    channel_id: str
    message_id: Optional[str]
    source_image_url: str
    prompt: str
    created_at: float = 0.0
    expired: bool = False

    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()

class SessionStore:
    def __init__(self, ttl_seconds: int = 900): # 15 minutes default
        self.sessions: Dict[str, InpaintSession] = {}
        self.ttl_seconds = ttl_seconds

    def create_session(
        self,
        user_id: str,
        user_name: str,
        channel_id: str,
        source_image_url: str,
        prompt: str = "",
        guild_id: Optional[str] = None,
        message_id: Optional[str] = None,
    ) -> InpaintSession:
        self.cleanup_expired()
        token = uuid.uuid4().hex
        session = InpaintSession(
            token=token,
            user_id=str(user_id),
            user_name=user_name,
            guild_id=str(guild_id) if guild_id else None,
            channel_id=str(channel_id),
            message_id=str(message_id) if message_id else None,
            source_image_url=source_image_url,
            prompt=prompt,
        )
        self.sessions[token] = session
        logger.info(f"Created inpaint session {token} for user {user_name} ({user_id})")
        return session

    def get_session(self, token: str) -> Optional[InpaintSession]:
        self.cleanup_expired()
        session = self.sessions.get(token)
        if not session:
            return None
        if time.time() - session.created_at > self.ttl_seconds or session.expired:
            session.expired = True
            logger.info(f"Session {token} has expired")
            return None
        return session

    def get_active_session_for_user(self, user_id: str) -> Optional[InpaintSession]:
        self.cleanup_expired()
        user_id_str = str(user_id)
        user_sessions = [
            s for s in self.sessions.values()
            if s.user_id == user_id_str and not s.expired and (time.time() - s.created_at <= self.ttl_seconds)
        ]
        if not user_sessions:
            return None
        return max(user_sessions, key=lambda s: s.created_at)

    def get_latest_active_session(self) -> Optional[InpaintSession]:
        self.cleanup_expired()
        user_sessions = [
            s for s in self.sessions.values()
            if not s.expired and (time.time() - s.created_at <= self.ttl_seconds)
        ]
        if not user_sessions:
            return None
        return max(user_sessions, key=lambda s: s.created_at)


    def mark_completed(self, token: str) -> None:
        if token in self.sessions:
            self.sessions[token].expired = True
            logger.info(f"Marked session {token} as completed/expired")

    def cleanup_expired(self) -> None:
        now = time.time()
        expired_tokens = [
            t for t, s in self.sessions.items()
            if s.expired or (now - s.created_at > self.ttl_seconds)
        ]
        for t in expired_tokens:
            del self.sessions[t]

session_store = SessionStore()
