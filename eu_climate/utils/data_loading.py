import os
import yaml
from pathlib import Path
from huggingface_hub import HfApi, upload_folder, snapshot_download
import shutil
from typing import Dict, Any
from dotenv import load_dotenv
import logging
from rasterio.enums import Resampling

logger = logging.getLogger(__name__)

REQUIRED_ENV_VARS = {
    'HF_API_TOKEN': 'Hugging Face API token for data upload'
}

def validate_env_vars() -> None:
    """Validate that all required environment variables are set."""
    load_dotenv()
    missing_vars = []
    
    for var, description in REQUIRED_ENV_VARS.items():
        if not os.getenv(var):
            missing_vars.append(f"{var} ({description})")
    
    if missing_vars:
        logger.warning("Missing environment variables:")
        for var in missing_vars:
            logger.warning(f"- {var}")
        logger.warning("Some functionality may be limited.")

def get_config() -> dict:
    """
    Load configuration from YAML file.
    
    Returns:
        dict: Configuration dictionary
    """
    # Try multiple possible config locations
    possible_paths = [
        Path("code/config/data_config.yaml"),
        Path("config/data_config.yaml"),
        Path(__file__).parent.parent / "config" / "data_config.yaml"
    ]
    
    for config_path in possible_paths:
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f).get('data', {})
                if not config:
                    raise ValueError("Invalid configuration file: 'data' section is missing")
                return config
    
    raise FileNotFoundError(
        "Configuration file not found! Ensure code/config/data_config.yaml exists."
    )

def check_data_availability() -> bool:
    """Check if required data directories exist and contain files."""
    config = get_config()
    data_dir = Path(config['data_paths']['local_data_dir'])
    output_dir = Path(config['data_paths']['local_output_dir'])
    
    return data_dir.exists() and output_dir.exists()

def download_data() -> bool:
    """Download data from Hugging Face if auto_download is enabled."""
    config = get_config()
    
    if not config.get('auto_download', False):
        logger.info("Auto-download is disabled. Please download the data manually from:")
        logger.info(f"https://huggingface.co/datasets/{config['huggingface_repo']}")
        logger.info("and place it in the following directories:")
        logger.info(f"- {config['data_paths']['local_data_dir']}")
        logger.info(f"- {config['data_paths']['local_output_dir']}")
        return False
    
    try:
        # Download the repository content
        snapshot_download(
            repo_id=config['huggingface_repo'],
            repo_type="dataset",
            local_dir="temp_download"
        )
        
        # Move the required directories to their destinations
        for dir_name, target_path in config['data_paths'].items():
            source = Path("temp_download") / Path(target_path).name
            target = Path(target_path)
            
            if source.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    shutil.rmtree(target)
                shutil.move(str(source), str(target))
        
        # Clean up temporary download directory
        if Path("temp_download").exists():
            shutil.rmtree("temp_download")
            
        return True
    
    except Exception as e:
        logger.error(f"Error downloading data: {str(e)}")
        return False

def upload_data() -> bool:
    """Upload data to Hugging Face if enabled."""
    config = get_config()
    
    if not config['upload']['enabled']:
        logger.info("Data upload is disabled.")
        return False
    
    if not config['upload']['api_token']:
        logger.error("Hugging Face API token is required for upload.")
        return False
    
    try:
        api = HfApi(token=config['upload']['api_token'])
        
        # Upload each directory
        for dir_path in config['data_paths'].values():
            if Path(dir_path).exists():
                upload_folder(
                    folder_path=dir_path,
                    repo_id=config['huggingface_repo'],
                    repo_type="dataset",
                    path_in_repo=Path(dir_path).name
                )
        logger.info("Data upload completed successfully")
        return True
    
    except Exception as e:
        logger.error(f"Error uploading data: {str(e)}")
        return False

def ensure_data_availability() -> bool:
    """Main function to ensure data is available."""
    if not check_data_availability():
        logger.info("Required data not found locally.")
        if not download_data():
            logger.error("Unable to download data automatically.")
            return False
    return True
