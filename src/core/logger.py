import logging
import sys
import os
from src.core.config import Config

def setup_logger(name: str):
    logger = logging.getLogger(name)
    logger.setLevel(Config.LOG_LEVEL)
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    # File handler
    fh = logging.FileHandler(os.path.join(Config.LOGS_DIR, "link.log"))
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    return logger
