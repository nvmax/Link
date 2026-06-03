import logging
import sys
import os
from src.core.config import Config

def setup_logger(name: str):
    logger = logging.getLogger(name)
    logger.setLevel(Config.LOG_LEVEL)
    
    # Avoid duplicate handlers if setup_logger is called multiple times for the same name
    if logger.handlers:
        return logger

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Console handler
    # We wrap sys.stdout to ensure it handles Unicode gracefully on Windows
    try:
        # For newer Python, we can check if it supports reconfigure
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    # File handler - explicitly set UTF-8 encoding
    if not os.path.exists(Config.LOGS_DIR):
        os.makedirs(Config.LOGS_DIR, exist_ok=True)
        
    fh = logging.FileHandler(os.path.join(Config.LOGS_DIR, "link.log"), encoding='utf-8', errors='replace')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    return logger
