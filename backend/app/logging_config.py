import os
import logging
import logging.handlers


LOG_DIR = "data/logs"
MAX_BYTES = 10 * 1024 * 1024  # 10MB
BACKUP_COUNT = 5


def setup_logging(log_level=logging.INFO):
    os.makedirs(LOG_DIR, exist_ok=True)

    log_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)

    app_log = os.path.join(LOG_DIR, "homegallery.log")
    file_handler = logging.handlers.RotatingFileHandler(
        app_log, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(log_format)
    root_logger.addHandler(file_handler)

    error_log = os.path.join(LOG_DIR, "error.log")
    error_handler = logging.handlers.RotatingFileHandler(
        error_log, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(log_format)
    root_logger.addHandler(error_handler)

    access_log = os.path.join(LOG_DIR, "access.log")
    access_handler = logging.handlers.RotatingFileHandler(
        access_log, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    access_handler.setLevel(logging.INFO)
    access_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    )
    access_logger = logging.getLogger("homegallery.access")
    access_logger.addHandler(access_handler)
    access_logger.propagate = False

    return root_logger


def get_logger(name: str = "homegallery") -> logging.Logger:
    return logging.getLogger(name)
