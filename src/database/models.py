from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, Enum
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
    user_id = Column(String, nullable=False)
    workflow_name = Column(String, nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING)
    input_params = Column(JSON)
    discord_message_id = Column(String)
    channel_id = Column(String)
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
