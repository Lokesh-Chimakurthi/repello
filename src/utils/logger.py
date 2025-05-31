import logging
import os
import inspect


def get_repo_root() -> str:
    """
    Returns the absolute path to the repository root.
    """
    current = os.path.abspath(__file__)
    while True:
        parent = os.path.dirname(current)
        if os.path.isdir(os.path.join(parent, "logs")):
            return parent
        if parent == current:
            # fallback: use current file's directory if logs not found
            return os.path.dirname(__file__)
        current = parent


def get_caller_file() -> str:
    """Get the filename (without extension) of the calling file efficiently."""
    # Go up 2 frames: current frame -> get_logger frame -> actual caller frame
    frame = inspect.currentframe().f_back.f_back
    filename = os.path.splitext(os.path.basename(frame.f_code.co_filename))[0]

    return filename


def get_logger() -> logging.Logger:
    """
    Returns a logger configured to write to the repo-level logs directory and to stdout.
    The logger name and log file are automatically set to the caller's filename.
    Only configures handlers if not already set for this logger.
    """
    name = get_caller_file()
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        # Create formatters
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

        if os.getenv("CURRENT_ENV") == "DEV":
            repo_root = get_repo_root()
            logs_dir = os.path.join(repo_root, "logs")
            os.makedirs(logs_dir, exist_ok=True)
            log_file = os.path.join(logs_dir, f"{name}.log")
            # File handler
            file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Prevent propagation to root logger
        logger.propagate = False

    return logger
