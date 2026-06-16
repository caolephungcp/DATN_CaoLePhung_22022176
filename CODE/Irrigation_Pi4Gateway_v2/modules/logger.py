# ============================================================================
# LOGGING SETUP
# ============================================================================

import logging
from .config import LOG_FILE, LOG_LEVEL

def setup_logging():
    """Setup logging configuration"""
    logger = logging.getLogger("GatewayPi4")
    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))

    # File handler
    try:
        fh = logging.FileHandler(LOG_FILE)
    except:
        fh = logging.FileHandler("gateway.log")
    fh.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))

    # Formatter
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger

# Global logger instance
logger = setup_logging()