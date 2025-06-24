from datetime import datetime
import os
from pathlib import Path
from huggingface_hub import HfApi, upload_folder, snapshot_download
from dotenv import load_dotenv
import logging

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
        validate_env_vars()
        
        repo_id = config.config['huggingface_repo']
        
        api_token = os.getenv('HF_API_TOKEN')
        if api_token:
            api = HfApi(token=api_token)
            logger.info("Using authenticated API for repository operations")
        else:
            api = HfApi()
            logger.info("Using unauthenticated API (cleanup will be skipped)")
        
        if api_token:
            logger.info("Cleaning up remote repository...")
            try:
                repo_files = api.list_repo_files(repo_id=repo_id, repo_type="dataset")
                
                files_to_delete = []
                for file_path in repo_files:
                    if file_path.startswith('data/') or file_path.startswith('output/'):
                        files_to_delete.append(file_path)
                
                if files_to_delete:
                    logger.info(f"Deleting {len(files_to_delete)} files from remote repository...")
                    for file_path in files_to_delete:
                        try:
                            api.delete_file(
                                path_in_repo=file_path,
                                repo_id=repo_id,
                                repo_type="dataset",
                                commit_message=f"Remove {file_path} for cleanup"
                            )
                            logger.debug(f"Deleted: {file_path}")
                        except Exception as e:
                            logger.warning(f"Could not delete {file_path}: {str(e)}")
                    logger.info("Remote repository cleanup completed")
                else:
                    logger.info("No data or output folders found in remote repository")
                    
            except Exception as e:
                logger.warning(f"Could not clean up remote repository: {str(e)}. Continuing with download...")
        else:
            logger.info("Skipping repository cleanup (no API token available)")
        
        config.huggingface_folder.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Downloading repository directly to {config.huggingface_folder}")
        
        snapshot_download(
            repo_id=repo_id,
            repo_type="dataset",
            local_dir=config.huggingface_folder,
            local_dir_use_symlinks=False,
            resume_download=True,
            token=api_token
        )
        
        logger.info(f"Successfully downloaded repository to {config.huggingface_folder}")
        
        required_items_checks = [
            (config.data_dir, "source data directory"),
            (config.huggingface_folder / "README.md", "README.md file"),
            (config.huggingface_folder / ".gitattributes", ".gitattributes file")
        ]
        
        all_items_present = True
        for item_path, item_name in required_items_checks:
            if item_path.exists():
                logger.info(f"+ {item_name} found at: {item_path}")
            else:
                logger.warning(f"- {item_name} not found at: {item_path}")
                if item_name == "source data directory":
                    all_items_present = False
        if all_items_present:
            logger.info("Data download completed successfully!")
            return True
        else:
            logger.error("Download completed but some required items are missing")
            return False
            
    except Exception as e:
        logger.error(f"Error downloading data: {str(e)}")
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

def upload_data() -> bool:
    """Upload all contents from the huggingface folder to Hugging Face repository."""
    # First, ensure environment variables are loaded
    validate_env_vars()
    
    config = get_config()
    
    # Check if upload is enabled
    if not config.config.get('upload', {}).get('enabled', False):
        logger.info("Data upload is disabled in configuration.")
        return False
    
    # Get API token from environment variables only
    api_token = os.getenv('HF_API_TOKEN')
    if not api_token:
        logger.error("Hugging Face API token is required for upload. Set HF_API_TOKEN environment variable.")
        return False
    
    if not config.huggingface_folder.exists():
        logger.error(f"Hugging Face folder not found: {config.huggingface_folder}")
        return False
    
    try:
        logger.info(f"Starting upload of {config.huggingface_folder} to {config.config['huggingface_repo']}")
        api = HfApi(token=api_token)
        
        for item in config.huggingface_folder.iterdir():
            if item.is_dir() and not item.name.startswith('.') and item.name != 'temp_download':
                logger.info(f"Uploading directory: {item.name}")
                upload_folder(
                    folder_path=str(item),
                    repo_id=config.config['huggingface_repo'],
                    repo_type="dataset",
                    path_in_repo=item.name,
                    token=api_token
                )
                logger.info(f"Successfully uploaded {item.name}")
        
        logger.info("All data upload completed successfully")
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


def check_data_integrity(config: ProjectConfig) -> None:
    """Check data integrity and sync with remote repository if needed."""
    logger.info("Checking data integrity...")
    
    try:
        # Load config settings
        repo_id = config.config['huggingface_repo']
        auto_download = config.config.get('auto_download', True)
        
        # Check local data files
        try:
            config.validate_files()
            logger.info("Local data validation passed")
        except FileNotFoundError as e:
            logger.warning(f"Missing data files: {e}")
            if auto_download:
                logger.info("Downloading missing data...")
                from eu_climate.utils.data_loading import download_data
                download_data()
                config.validate_files()  # Re-validate after download
            else:
                logger.error(f"Please download data from: https://huggingface.co/datasets/{repo_id}")
                raise
        
        # Check for updates if possible
        try:
            from huggingface_hub import HfApi
            api_token = os.getenv('HF_API_TOKEN')
            if api_token:
                api = HfApi(token=api_token)
            else:
                api = HfApi()
            repo_info = api.dataset_info(repo_id=repo_id)
            logger.info(f"Remote data last modified: {repo_info.last_modified}")
            
            if auto_download:
                # Simple check: if data directory is older than 1 day, consider update
                data_age = (datetime.now() - datetime.fromtimestamp(config.data_dir.stat().st_mtime)).days
                if data_age > 1:
                    logger.info("Data might be outdated, updating...")
                    from eu_climate.utils.data_loading import download_data
                    download_data()
                    
        except Exception as e:
            logger.debug(f"Could not check remote updates: {e}")
            
        logger.info("Data integrity check completed")
        
    except Exception as e:
        logger.error(f"Data integrity check failed: {e}")
        raise