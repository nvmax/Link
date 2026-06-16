from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid

Base = declarative_base()

class JobStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class GenerationJob(Base):
    __tablename__ = "jobs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    comfy_prompt_id = Column(String, unique=True, index=True)
    guild_id = Column(String, nullable=True, index=True)
    user_id = Column(String, nullable=False)
    workflow_name = Column(String, nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING)
    input_params = Column(JSON)
    discord_message_id = Column(String)
    channel_id = Column(String)
    node_map = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    assets = relationship("Asset", back_populates="job")

class Asset(Base):
    __tablename__ = "assets"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String, ForeignKey("jobs.id"))
    file_path = Column(String, nullable=False)
    file_type = Column(String) # e.g., "image/png", "video/mp4"
    created_at = Column(DateTime, default=datetime.utcnow)
    
    job = relationship("GenerationJob", back_populates="assets")

class Workflow(Base):
    __tablename__ = "workflows"
    
    name = Column(String, primary_key=True)
    description = Column(String)
    json_path = Column(String)
    yaml_path = Column(String)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ServerLimit(Base):
    __tablename__ = "server_limits"
    
    guild_id = Column(String, primary_key=True)
    rate_limit_per_minute = Column(Integer, default=0)  # 0 means disabled
    rate_limit_per_hour = Column(Integer, default=0)
    quota_per_day = Column(Integer, default=0)
    tos_required = Column(Boolean, default=False)

class UserBan(Base):
    __tablename__ = "user_bans"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    guild_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    username = Column(String)
    banned_by = Column(String)
    reason = Column(String)
    ban_type = Column(String)  # "ban" or "restrict"
    duration_seconds = Column(Integer, nullable=True)  # Null for permanent
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # Null for permanent

class UserAgreement(Base):
    __tablename__ = "user_agreements"
    
    user_id = Column(String, primary_key=True)
    agreed = Column(Boolean, default=True)
    agreed_at = Column(DateTime, default=datetime.utcnow)
