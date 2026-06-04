from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from src.core.config import Config
from src.database.models import Base
from contextlib import contextmanager

engine = create_engine(Config.DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in Config.DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    if "sqlite" in Config.DATABASE_URL:
        import sqlite3
        import os
        db_path = Config.DATABASE_URL.replace("sqlite:///", "")
        if not os.path.isabs(db_path):
            # Resolve relative data/link.db to BASE_DIR if needed
            db_path = os.path.join(Config.BASE_DIR, db_path)
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(jobs);")
                columns = [col[1] for col in cursor.fetchall()]
                if "guild_id" not in columns:
                    cursor.execute("ALTER TABLE jobs ADD COLUMN guild_id VARCHAR;")
                    conn.commit()
                conn.close()
            except Exception:
                pass

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def db_session():
    """Provide a transactional scope around a series of operations."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

