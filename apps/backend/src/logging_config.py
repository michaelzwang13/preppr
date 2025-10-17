"""
Logging configuration for the Preppr application.
Provides structured logging with different levels and proper formatting.
"""

import logging
import logging.config
import os
from datetime import datetime
from typing import Dict, Any


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        if hasattr(record, "cart_id"):
            log_entry["cart_id"] = record.cart_id
        if hasattr(record, "duration"):
            log_entry["duration_ms"] = record.duration

        return str(log_entry)


def get_logging_config() -> Dict[str, Any]:
    """Get logging configuration based on environment"""

    # Determine log level from environment
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
            "detailed": {
                "format": "%(asctime)s [%(levelname)s] %(name)s [%(filename)s:%(lineno)d] %(message)s"
            },
            "json": {
                "()": JSONFormatter,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "standard",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": log_level,
                "formatter": "detailed",
                "filename": os.path.join(log_dir, "preppr.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf8",
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "json",
                "filename": os.path.join(log_dir, "errors.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf8",
            },
        },
        "loggers": {
            "preppr": {
                "level": log_level,
                "handlers": ["console", "file", "error_file"],
                "propagate": False,
            },
            "preppr.auth": {
                "level": log_level,
                "handlers": ["console", "file", "error_file"],
                "propagate": False,
            },
            "preppr.shopping": {
                "level": log_level,
                "handlers": ["console", "file", "error_file"],
                "propagate": False,
            },
            "preppr.api": {
                "level": log_level,
                "handlers": ["console", "file", "error_file"],
                "propagate": False,
            },
            "preppr.database": {
                "level": log_level,
                "handlers": ["console", "file", "error_file"],
                "propagate": False,
            },
        },
        "root": {"level": "WARNING", "handlers": ["console"]},
    }

    return config


def setup_logging():
    """Setup logging configuration"""
    config = get_logging_config()
    logging.config.dictConfig(config)

    # Get the main logger and log startup
    logger = logging.getLogger("preppr")
    logger.info(
        "Logging system initialized",
        extra={
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "environment": os.getenv("FLASK_ENV", "development"),
        },
    )


def get_logger(name: str = "preppr") -> logging.Logger:
    """Get a logger instance with the specified name"""
    return logging.getLogger(name)


class RequestLogger:
    """Context manager for request logging"""

    def __init__(self, logger: logging.Logger, request_info: Dict[str, Any]):
        self.logger = logger
        self.request_info = request_info
        self.start_time = None

    def __enter__(self):
        self.start_time = datetime.utcnow()
        self.logger.info(
            "Request started",
            extra={
                "request_id": self.request_info.get("request_id"),
                "method": self.request_info.get("method"),
                "path": self.request_info.get("path"),
                "user_id": self.request_info.get("user_id"),
            },
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.utcnow() - self.start_time).total_seconds() * 1000

        if exc_type is None:
            self.logger.info(
                "Request completed",
                extra={
                    "request_id": self.request_info.get("request_id"),
                    "duration": duration,
                    "status": "success",
                },
            )
        else:
            self.logger.error(
                "Request failed",
                extra={
                    "request_id": self.request_info.get("request_id"),
                    "duration": duration,
                    "status": "error",
                    "error_type": exc_type.__name__,
                    "error_message": str(exc_val),
                },
            )
