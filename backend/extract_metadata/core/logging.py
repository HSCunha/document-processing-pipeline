import logging
import os

def get_logger(name: str) -> logging.Logger:
    """
    Returns a configured logger instance.

    Args:
        name (str): The name of the logger, typically __name__ of the module.

    Returns:
        logging.Logger: A configured logger instance.
    """
    logger = logging.getLogger(name)
    if not logger.handlers: # Prevent adding multiple handlers if logger already exists
        logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
        # Optional: File handler
        # log_file = os.getenv("LOG_FILE")
        # if log_file:
        #     fh = logging.FileHandler(log_file)
        #     fh.setFormatter(formatter)
        #     logger.addHandler(fh)

    return logger
