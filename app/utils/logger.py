"""
This module is responsible for configuring the logger
"""
import os
from loguru import logger
from dotenv import load_dotenv
load_dotenv()
LOG_FILE = os.environ.get("LOG_FILE")

def setup_logger():
    """**Summary:**
    Loguru Config Details:
    ---------------------
    1. serialize: This paramiter is responsible for json like log entry in the file.
    2. level: This paramiter is responsible for setting the level of logging.
    3. backtrace: This paramiter is responsible for adding the stack trace to the message in case of any exception.
    4. rotation: This paramiter is responsible for creating a new file depending on the value. like '10 MB','1 Week','12:00' etc.
    5. compression: This paramiter is responsible for defining the compressed file type while creating a new file depending on rotation(Cleanup some space).
    6. retention: Cleanup after some time.
    """

    # Log message format
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    
    # Set the SQL logging level to INFO
    if os.getenv("SQL_LOG", "0") == "1":
        logger.add(
            LOG_FILE,
            format="{message}",
            serialize=True,
            level="INFO",
            backtrace=True,
            compression="zip",
            rotation="100 MB",
            filter=lambda record: record["name"] == "sqlalchemy.engine"
        )
    else:
        logger.add(
            LOG_FILE,
            format="{message}",
            serialize=True,
            level="INFO",
            backtrace=True,
            compression="zip",
            rotation="100 MB",
        )