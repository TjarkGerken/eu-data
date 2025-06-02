# Setup logging
import logging
import warnings
import rasterio
import sys

def setup_logging(name=__name__):
    """
    Set up logging configuration for the application.
    
    Args:
        name (str): The name of the logger, typically __name__ from the calling module
        
    Returns:
        logging.Logger: Configured logger instance
    """
    # Configure the root logger only once
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('risk_assessment.log')
            ]
        )
    
    # Get logger for the specific module
    logger = logging.getLogger(name)
    return logger


def suppress_warnings():
    warnings.filterwarnings('ignore', category=rasterio.errors.NotGeoreferencedWarning)
    warnings.filterwarnings('ignore', category=UserWarning)