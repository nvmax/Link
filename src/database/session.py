from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from src.core.config import Config
from src.database.models import Base

engine = create_engine(Config.DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in Config.DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
