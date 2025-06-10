import os
import yaml
from pathlib import Path
from huggingface_hub import HfApi, upload_folder, snapshot_download
import shutil
from typing import Dict, Any
from dotenv import load_dotenv
import logging
from rasterio.enums import Resampling

from eu_climate.config.config import ProjectConfig

logger = logging.getLogger(__name__)

REQUIRED_ENV_VARS = {
    'HF_API_TOKEN': 'Hugging Face API token for data upload'
}

def validate_env_vars() -> None:
    """Validate that all required environment variables are set."""
    possible_env_paths = [
        Path(__file__).parent.parent / "config" / ".env",
    ]
    
    env_loaded = False
    for env_path in possible_env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            env_loaded = True
            logger.info(f"Loaded environment variables from {env_path}")
            break
    
    if not env_loaded:
        logger.warning("No .env file found in any of the expected locations")
    
    missing_vars = []
    for var, description in REQUIRED_ENV_VARS.items():
        if not os.getenv(var):
            missing_vars.append(f"{var} ({description})")
    
    if missing_vars:
        logger.warning("Missing environment variables:")
        for var in missing_vars:
            logger.warning(f"- {var}")
        logger.warning("Some functionality may be limited.")

def get_config() -> ProjectConfig:
    config = ProjectConfig()
    return config



def download_data() -> bool:
    """Download data from Hugging Face if auto_download is enabled."""
    config = get_config()
    
    if not config.config.get('auto_download', False):
        logger.info("Auto-download is disabled. Please download the data manually from:")
        logger.info(f"https://huggingface.co/datasets/{config.config['huggingface_repo']}")
        logger.info("and place it in the following directories:")
        logger.info(f"- {config.data_dir}")
        logger.info(f"- {config.output_dir}")
        return False
    
    try:
        # Download the repository content
        logger.info(f"Downloading data to {config.huggingface_folder}")
        temp_download_path = config.huggingface_folder / Path("temp_download")

        snapshot_download(
            repo_id=config.config['huggingface_repo'],
            repo_type="dataset",
            local_dir=temp_download_path
        )
        
        
        directory_mappings = {  
            "data": config.data_dir,
            "output": config.output_dir
        }
        
        for source_dir_name, target_path in directory_mappings.items():
            source = temp_download_path / source_dir_name
            target = Path(target_path)
            
            if source.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    shutil.rmtree(target)
                shutil.move(str(source), str(target))
                logger.info(f"Moved {source} to {target}")
            else:
                logger.warning(f"Source directory not found: {source}")
        
        # Clean up temporary download directory
        if temp_download_path.exists():
            shutil.rmtree(temp_download_path)
            
        return True
    
    except Exception as e:
        logger.error(f"Error downloading data: {str(e)}")
        return False

def upload_data() -> bool:
    """Upload data to Hugging Face if enabled."""
    config = get_config()
    
    if not config.config['upload']['enabled']:
        logger.info("Data upload is disabled.")
        return False
    
    if not config.config['upload']['api_token']:
        logger.error("Hugging Face API token is required for upload.")
        return False
    
    try:
        api = HfApi(token=config.config['upload']['api_token'])
        
        # Upload each directory
        for dir_path in [config.data_dir, config.output_dir]:
            if dir_path.exists():
                upload_folder(
                    folder_path=str(dir_path),
                    repo_id=config.config['huggingface_repo'],
                    repo_type="dataset",
                    path_in_repo=dir_path.name
                )
        logger.info("Data upload completed successfully")
        return True
    
    except Exception as e:
        logger.error(f"Error uploading data: {str(e)}")
        return False

def check_data_availability() -> bool:
    """Check if required data directories and key files exist."""
    config = get_config()
    
    data_dir = config.data_dir
    output_dir = config.output_dir
    
    if not data_dir.exists():
        logger.info(f"Data directory not found: {data_dir}")
        return False
    
    # Check for some key files to ensure data is properly downloaded
    key_files = [
        data_dir / config.config['file_paths']['dem_file'],
        data_dir / config.config['file_paths']['population_file']
    ]
    
    for file_path in key_files:
        if not file_path.exists():
            logger.info(f"Key data file missing: {file_path}")
            return False
    
    logger.info("Required data files found locally")
    return True

def ensure_data_availability() -> bool:
    """Main function to ensure data is available."""
    if not check_data_availability():
        logger.info("Required data not found locally.")
        if not download_data():
            logger.error("Unable to download data automatically.")
            return False
    return True
