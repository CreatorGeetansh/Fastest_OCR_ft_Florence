# Placeholder for logging configuration
import sys
import os
from loguru import logger
import json
from contextvars import ContextVar

# ContextVar to hold the request ID
request_id_var: ContextVar[str] = ContextVar("request_id", default=None)

class LoggingConfig:
    """
    Configures the Loguru logger for the application.
    """
    def __init__(self, log_level="INFO", log_dir="logs"):
        self.log_level = log_level.upper()
        self.log_dir = log_dir
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    def _json_formatter(self, record):
        """
        Custom formatter to structure logs as JSON and include the request_id.
        """
        log_object = {
            "timestamp": record["time"].isoformat(),
            "level": record["level"].name,
            "message": record["message"],
            "request_id": request_id_var.get(), # Get request_id from ContextVar
            "source": {
                "name": record["name"],
                "file": record["file"].path,
                "line": record["line"],
            },
        }
        # Add exception details if present
        if record["exception"]:
            log_object["exception"] = {
                "type": record["exception"].type.__name__,
                "value": str(record["exception"].value),
                "traceback": True,
            }
        
        # Serialize the log object to a JSON string
        record["extra"]["json"] = json.dumps(log_object)
        return "{extra[json]}\n"
    
    def setup_logging(self):
        """
        Removes default handlers and sets up new console and file sinks.
        """
        logger.remove()

        # Console sink - for human-readable logs during development
        logger.add(
            sys.stdout,
            level=self.log_level,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<yellow>ID: {extra[request_id]}</yellow> - <level>{message}</level>"
            ),
            colorize=True,
            # Patch the logger to add request_id to every log record's 'extra'
            filter=lambda record: record["extra"].update(request_id=request_id_var.get())
        )

        # File sink - for structured JSON logs, suitable for production
        log_file_path = os.path.join(self.log_dir, "app_{time}.log")
        logger.add(
            log_file_path,
            level=self.log_level,
            format=self._json_formatter,
            rotation="10 MB",  # Rotates the log file when it reaches 10 MB
            retention="10 days", # Keeps logs for 10 days
            compression="zip", # Compresses old log files
            serialize=False, # We are doing custom serialization
            enqueue=True, # Makes logging non-blocking, important for performance
            backtrace=True, # Show full stack trace on errors
            diagnose=True, # Adds exception variable values for easier debugging
        )

        logger.info("Logger configured successfully.")

# Create and configure the logger instance
# This code runs once when the module is imported.
log_config = LoggingConfig(log_level=os.getenv("LOG_LEVEL", "INFO"))
log_config.setup_logging()

# Export the configured logger instance for use in other modules
__all__ = ["logger", "request_id_var"]