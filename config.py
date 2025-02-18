from datetime import datetime
import logging.config
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


def assign_config_dict(prefix: str = "") -> SettingsConfigDict:
    return SettingsConfigDict(
        env_prefix=prefix,
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )


class Settings(BaseSettings):
    API_URL: str
    WIKI_TOKEN: SecretStr
    FOLDER_NAME: str = "text"
    COUNTER_FILE: str = "counter.txt"
    DEFAULT_START: int = 100001

    model_config = assign_config_dict()


settings = Settings()


class CustomFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        ct = datetime.fromtimestamp(record.created).astimezone()
        if datefmt:
            base_time = ct.strftime("%d.%m.%Y %H:%M:%S")
            msecs = f"{int(record.msecs):03d}"
            tz = ct.strftime("%z")
            return f"{base_time}.{msecs}{tz}"
        else:
            return super().formatTime(record, datefmt)


main_template = {
    "format": "%(asctime)s | %(message)s",
    "datefmt": "%d.%m.%Y %H:%M:%S%z",
}
error_template = {
    "format": "%(asctime)s [%(levelname)8s] [%(module)s:%(funcName)s:%(lineno)d] %(message)s",
    "datefmt": "%d.%m.%Y %H:%M:%S%z",
}


def set_up_app(app_name: str):
    Path("logs").mkdir(parents=True, exist_ok=True)
    Path("text").mkdir(parents=True, exist_ok=True)

    logging_config = get_logging_config(app_name)
    logging.config.dictConfig(logging_config)


def get_logging_config(app_name: str):
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "main": {
                "()": CustomFormatter,
                "format": main_template["format"],
                "datefmt": main_template["datefmt"],
            },
            "errors": {
                "()": CustomFormatter,
                "format": error_template["format"],
                "datefmt": error_template["datefmt"],
            },
        },
        "handlers": {
            "stdout": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "main",
                "stream": sys.stdout,
            },
            "stderr": {
                "class": "logging.StreamHandler",
                "level": "WARNING",
                "formatter": "errors",
                "stream": sys.stderr,
            },
            "file": {
                "()": RotatingFileHandler,
                "level": "INFO",
                "formatter": "main",
                "filename": f"logs/{app_name}.log",
                "maxBytes": 50000000,
                "backupCount": 3,
                "encoding": "utf-8",
            },
        },
        "loggers": {
            "root": {
                "level": "DEBUG",
                "handlers": ["stdout", "stderr", "file"],
            },
        },
    }
