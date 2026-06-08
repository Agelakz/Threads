import logging
import sys

def setup_logger(name: str) -> logging.Logger:
    """
    Setup and return a logger with the specified name.
    
    Args:
        name (str): The name of the logger, usually __name__.
        
    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)

        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # Add formatter to console handler
        console_handler.setFormatter(formatter)

        # Add console handler to logger
        logger.addHandler(console_handler)

    return logger
