# Setup logging
import logging
import os
import warnings
import rasterio
import sys

def setup_logging(name=__name__):
    """
    Set up logging configuration for the application.
    
    Creates a centralized logging system that outputs to both console and file.
    Ensures consistent logging format across all modules in the EU Climate Risk Assessment system.
    
    Features:
    - Dual output: console (stdout) and file logging
    - Standardized format with timestamp, module name, level, and message
    - Automatic debug directory creation
    - Single configuration to avoid duplicate handlers
    
    Args:
        name (str): The name of the logger, typically __name__ from the calling module.
                   This allows for module-specific logging identification.
        
    Returns:
        logging.Logger: Configured logger instance ready for use
        
    Example:
        >>> from eu_climate.utils.utils import setup_logging
        >>> logger = setup_logging(__name__)
        >>> logger.info("Starting data processing")
        >>> logger.warning("Potential issue detected")
        >>> logger.error("Critical error occurred")
    """
    # Create debug directory for log files if it doesn't exist
    debug_dir = "eu_climate/debug"
    if not os.path.exists(debug_dir):
        os.makedirs(debug_dir)
        
    # Configure the root logger only once to avoid duplicate handlers
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),  # Console output
                logging.FileHandler(f'{debug_dir}/risk_assessment.log')  # File output
            ]
        )   
    
    # Get logger for the specific module
    logger = logging.getLogger(name)
    
    # Log the logger name for debugging purposes
    logger.info("Logger initialized with name: %s", name)
    return logger


def suppress_warnings():
    """
    Suppress known non-critical warnings that can clutter the output.
    
    This function filters out specific warning types that are known to be non-critical
    but can flood the console output during normal operation. These warnings typically
    relate to:
    - Rasterio georeferencing warnings for data that doesn't need georeferencing
    - General user warnings that don't affect functionality
    
    Should be called early in the application initialization to ensure clean output.
    
    Suppressed Warning Types:
    - rasterio.errors.NotGeoreferencedWarning: When raster data lacks georeferencing
    - UserWarning: General warnings that don't impact functionality
    
    Example:
        >>> from eu_climate.utils.utils import suppress_warnings
        >>> suppress_warnings()  # Call early in your application
    """
    # Suppress rasterio warnings about non-georeferenced data
    warnings.filterwarnings('ignore', category=rasterio.errors.NotGeoreferencedWarning)
    
    # Suppress general user warnings that don't impact functionality
    warnings.filterwarnings('ignore', category=UserWarning)
