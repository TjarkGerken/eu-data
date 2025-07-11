import os
import sys
from pathlib import Path

# Add the code directory to the Python path
script_dir = Path(__file__).resolve().parent
code_dir = script_dir.parent
sys.path.insert(0, str(code_dir))

import logging
from dotenv import load_dotenv
from huggingface_hub import HfApi, upload_folder
from eu_climate.utils.data_loading import get_config, validate_env_vars

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def validate_upload_requirements():
    """Validate that all requirements for upload are met."""
    # Load environment variables from config directory
    env_path = code_dir / 'config' / '.env'
    if not env_path.exists():
        logger.error(f".env file not found at {env_path}")
        logger.error("Please ensure .env file exists in the config directory.")
        sys.exit(1)
        
    load_dotenv(env_path)
    
    # Check for API token
    api_token = os.getenv('HF_API_TOKEN')
    if not api_token:
        logger.error("HF_API_TOKEN environment variable is not set.")
        logger.error("Please set it in your config/.env file or environment variables.")
        sys.exit(1)
    
    # Log token status (safely)
    if len(api_token) > 8:
        logger.info(f"Found API token (starts with: {api_token[:4]}...)")
    else:
        logger.warning("API token seems too short - please check your token")
    
    # Get configuration
    try:
        config = get_config()
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        sys.exit(1)
    
    # Validate repository exists or create it
    try:
        api = HfApi(token=api_token)
        repo_id = config.config['huggingface_repo']
        logger.info(f"Checking repository: {repo_id}")
        
        # Check if repo exists first
        try:
            api.repo_info(repo_id=repo_id, repo_type="dataset")
            logger.info("Repository exists and is accessible")
        except Exception as e:
            if "404" in str(e):
                # Repository doesn't exist, try to create it
                try:
                    api.create_repo(repo_id=repo_id, repo_type="dataset", private=False)
                    logger.info("Created new repository")
                except Exception as create_e:
                    logger.error(f"Error creating repository: {str(create_e)}")
                    sys.exit(1)
            else:
                logger.error(f"Error accessing repository: {str(e)}")
                sys.exit(1)
    except Exception as e:
        logger.error(f"Error validating repository: {str(e)}")
        sys.exit(1)
    
    return config, api_token

def upload_directory(api: HfApi, dir_path: Path, repo_id: str) -> bool:
    """Upload a directory to Hugging Face."""
    if not dir_path.exists():
        logger.warning(f"Directory {dir_path} does not exist, skipping...")
        return False
    
    logger.info(f"Uploading {str(dir_path)}...")
    logger.info(f"Repo ID: {repo_id}")
    logger.info(f"Folder path: {str(dir_path)}")
    logger.info(f"Path in repo: {dir_path.name}")
    
    try:
        # First, ensure the directory is not empty
        if not any(dir_path.iterdir()):
            logger.error(f"Directory {dir_path} is empty!")
            return False
            
        # Attempt upload with explicit parameters
        upload_folder(
            repo_id=repo_id,
            folder_path=str(dir_path),
            path_in_repo=dir_path.name,
            repo_type="dataset",
            ignore_patterns=["*.pyc", "__pycache__", ".git*"],
            token=api.token
        )
        logger.info(f"Successfully uploaded {dir_path}")
        return True
    except Exception as e:
        logger.error(f"Error uploading {dir_path}")
        logger.error(f"Error details: {str(e)}")
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            logger.error(f"Response text: {e.response.text}")
        return False

def main():
    """Main execution function."""
    logger.info("Starting data upload process...")
    
    # Validate requirements
    config, api_token = validate_upload_requirements()
    
    # Initialize Hugging Face API
    api = HfApi(token=api_token)
    logger.debug(f"Token: {str(api_token[:4])}... (masked)")
    repo_id = config.config['huggingface_repo']
    
    # Use absolute paths resolved by ProjectConfig so that uploads work
    # regardless of the current working directory.
    data_dir = config.data_dir
    output_dir = config.output_dir
    
    # Upload directories
    success = True
    for directory in [data_dir, output_dir]:
        if not upload_directory(api, directory, repo_id):
            success = False
    
    if success:
        logger.info("All uploads completed successfully!")
    else:
        logger.warning("Some uploads failed. Check the logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main() 