import os
import logging
from datetime import datetime

class LoggingConfig:
    @staticmethod
    def setup_logging(logger_name, log_filename=None):
        """Set up logging with standardized configuration"""
        # Create logs directory if it doesn't exist
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        # If no specific filename is provided, use the logger name
        if not log_filename:
            log_filename = f"{logger_name}.log"
            
        # Add timestamp to filename to avoid overwriting
        timestamp = datetime.now().strftime("%Y%m%d")
        log_filepath = os.path.join(logs_dir, f"{log_filename.split('.')[0]}_{timestamp}.log")
        
        # Configure logger
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        
        # Clear existing handlers to avoid duplicate logs
        if logger.hasHandlers():
            logger.handlers.clear()
        
        # Create file handler
        file_handler = logging.FileHandler(log_filepath)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(file_formatter)
        
        # Add handlers to logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        # Log the path where logs are being saved
        logger.info(f"Logs will be saved to: {log_filepath}")
        
        return logger