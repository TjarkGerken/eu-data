"""
Data Loading and Management Utilities for EU Climate Risk Assessment
===================================================================

This module provides comprehensive data management capabilities for the EU Climate Risk Assessment system,
including automated data downloading, validation, integrity checking, and specialized population data processing.

Key Features:
- Automated data downloading from Hugging Face repositories
- Environment variable validation and configuration management
- Data integrity checking with remote synchronization
- Specialized population data loading with resolution adaptation
- Geographic study area masking and validation
- Population total validation against ground truth data
- Comprehensive error handling and logging

The module handles the complexity of data management while providing a simple interface for ensuring
data availability and integrity across the entire risk assessment workflow.

Architecture:
- Environment variable validation and loading
- Hugging Face repository integration for data synchronization
- Specialized population data processing with CRS transformations
- Geographic masking using NUTS boundaries and land mass data
- Statistical validation against known population totals
- Comprehensive logging and error reporting

Data Sources:
- Hugging Face repositories for automated data distribution
- Global Human Settlement (GHS) population data for 2025 projections
- NUTS Level 3 boundaries for geographic study area definition
- Land mass data for precise geographic masking
- Ground truth population statistics for validation

Usage:
    from eu_climate.utils.data_loading import ensure_data_availability, load_population_2025_with_validation

    # Ensure all required data is available
    if ensure_data_availability():
        print("Data ready for analysis")

    # Load population data with validation
    pop_data, metadata, validation_passed = load_population_2025_with_validation(
        config,
        apply_study_area_mask=True
    )

    if validation_passed:
        print("Population data validated successfully")
"""

from datetime import datetime
import os
from pathlib import Path
from typing import Tuple
from huggingface_hub import HfApi, upload_folder, snapshot_download
from dotenv import load_dotenv
import logging
import rasterio
import rasterio.warp
import numpy as np
import geopandas as gpd

from eu_climate.config.config import ProjectConfig
from eu_climate.utils.conversion import RasterTransformer

logger = logging.getLogger(__name__)

# Required environment variables for data operations
REQUIRED_ENV_VARS = {
    "HF_API_TOKEN": "Hugging Face API token for data upload and authenticated repository access"
}


def validate_env_vars() -> None:
    """
    Validate that all required environment variables are set for data operations.

    This function checks for the presence of required environment variables and loads
    them from .env files if available. It provides detailed warnings for missing
    variables while allowing the system to continue with limited functionality.

    Environment Variables:
        HF_API_TOKEN: Hugging Face API token for repository operations

    Environment File Locations:
        - {project_root}/eu_climate/config/.env

    Note:
        Missing environment variables will result in warnings but won't prevent
        the system from functioning. Some features may be limited without tokens.
    """
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
    """
    Get the project configuration instance.

    Returns:
        ProjectConfig: Configured project settings including data paths,
                      repository settings, and processing parameters
    """
    config = ProjectConfig()
    return config


def download_data() -> bool:
    """
    Download data from Hugging Face repository if auto_download is enabled.

    This function handles the complete data download workflow including:
    - Configuration validation and environment setup
    - Remote repository cleanup (if authenticated)
    - Data download with resume capability
    - Validation of downloaded data integrity

    The function respects the auto_download configuration setting and will
    provide guidance for manual download if automatic download is disabled.

    Returns:
        bool: True if data was successfully downloaded and validated,
              False if download failed or is disabled

    Note:
        - Requires HF_API_TOKEN environment variable for authenticated operations
        - Supports resume download for interrupted transfers
        - Validates downloaded data against expected directory structure
        - Provides detailed logging for troubleshooting
    """
    config = get_config()

    if not config.config.get("auto_download", False):
        logger.info(
            "Auto-download is disabled. Please download the data manually from:"
        )
        logger.info(
            f"https://huggingface.co/datasets/{config.config['huggingface_repo']}"
        )
        logger.info("and place it in the following directories:")
        logger.info(f"- {config.data_dir}")
        logger.info(f"- {config.output_dir}")
        return False

    try:
        validate_env_vars()

        repo_id = config.config["huggingface_repo"]

        api_token = os.getenv("HF_API_TOKEN")
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
                    if file_path.startswith("data/"):
                        files_to_delete.append(file_path)

                if files_to_delete:
                    logger.info(
                        f"Deleting {len(files_to_delete)} files from remote repository..."
                    )
                    for file_path in files_to_delete:
                        try:
                            api.delete_file(
                                path_in_repo=file_path,
                                repo_id=repo_id,
                                repo_type="dataset",
                                commit_message=f"Remove {file_path} for cleanup",
                            )
                            logger.debug(f"Deleted: {file_path}")
                        except Exception as e:
                            logger.warning(f"Could not delete {file_path}: {str(e)}")
                    logger.info("Remote repository cleanup completed")
                else:
                    logger.info("No data or output folders found in remote repository")

            except Exception as e:
                logger.warning(
                    f"Could not clean up remote repository: {str(e)}. Continuing with download..."
                )
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
            token=api_token,
        )

        logger.info(
            f"Successfully downloaded repository to {config.huggingface_folder}"
        )

        required_items_checks = [
            (config.data_dir, "source data directory"),
            (config.output_dir, "output directory"),
            (config.huggingface_folder / "README.md", "README.md file"),
            (config.huggingface_folder / ".gitattributes", ".gitattributes file"),
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
    """
    Check if required data directories and key files exist locally.

    This function performs a comprehensive check of the local data directory
    to ensure all required files are present for risk assessment processing.

    Returns:
        bool: True if all required data files are found locally,
              False if any required files are missing

    Checks:
        - Data directory exists and is accessible
        - Key data files (DEM, boundaries, etc.) are present
        - File integrity and basic validation

    Note:
        This function only checks for file existence, not content validity.
        Use check_data_integrity() for comprehensive validation.
    """
    config = get_config()

    data_dir = config.data_dir

    if not data_dir.exists():
        logger.info(f"Data directory not found: {data_dir}")
        return False

    # Check for some key files to ensure data is properly downloaded
    key_files = [
        data_dir / config.config["file_paths"]["dem_file"],
    ]

    for file_path in key_files:
        if not file_path.exists():
            logger.info(f"Key data file missing: {file_path}")
            return False

    logger.info("Required data files found locally")
    return True


def upload_data() -> bool:
    """
    Upload all contents from the huggingface folder to Hugging Face repository.

    This function handles the complete data upload workflow for sharing processed
    results and datasets with the research community via Hugging Face repositories.

    Returns:
        bool: True if upload was successful, False if upload failed or is disabled

    Requirements:
        - HF_API_TOKEN environment variable must be set
        - Upload must be enabled in configuration
        - Hugging Face folder must exist and contain data to upload

    Upload Process:
        1. Validates environment and configuration
        2. Checks for valid API token
        3. Uploads directory contents to repository
        4. Provides detailed logging of upload progress

    Note:
        - Requires authenticated Hugging Face account
        - Respects configuration upload.enabled setting
        - Uploads all subdirectories except temporary files
    """
    # First, ensure environment variables are loaded
    validate_env_vars()

    config = get_config()

    # Check if upload is enabled
    if not config.config.get("upload", {}).get("enabled", False):
        logger.info("Data upload is disabled in configuration.")
        return False

    # Get API token from environment variables only
    api_token = os.getenv("HF_API_TOKEN")
    if not api_token:
        logger.error(
            "Hugging Face API token is required for upload. Set HF_API_TOKEN environment variable."
        )
        return False

    if not config.huggingface_folder.exists():
        logger.error(f"Hugging Face folder not found: {config.huggingface_folder}")
        return False

    try:
        logger.info(
            f"Starting upload of {config.huggingface_folder} to {config.config['huggingface_repo']}"
        )
        HfApi(token=api_token)

        for item in config.huggingface_folder.iterdir():
            if (
                item.is_dir()
                and not item.name.startswith(".")
                and item.name != "temp_download"
            ):
                logger.info(f"Uploading directory: {item.name}")
                upload_folder(
                    folder_path=str(item),
                    repo_id=config.config["huggingface_repo"],
                    repo_type="dataset",
                    path_in_repo=item.name,
                    token=api_token,
                )
                logger.info(f"Successfully uploaded {item.name}")

        logger.info("All data upload completed successfully")
        return True

    except Exception as e:
        logger.error(f"Error uploading data: {str(e)}")
        return False


def ensure_data_availability() -> bool:
    """
    Main function to ensure data is available for risk assessment processing.

    This is the primary entry point for data availability management. It checks
    for local data availability and automatically downloads data if needed and
    configured to do so.

    Returns:
        bool: True if data is available and ready for processing,
              False if data is not available and cannot be obtained

    Workflow:
        1. Check if required data files exist locally
        2. If missing, attempt automatic download (if enabled)
        3. Provide user guidance if automatic download fails
        4. Return availability status

    Note:
        This function should be called before any risk assessment processing
        to ensure all required data is available and accessible.
    """
    if not check_data_availability():
        logger.info("Required data not found locally.")
        if not download_data():
            logger.error("Unable to download data automatically.")
            return False
    return True


def check_data_integrity(config: ProjectConfig) -> None:
    """
    Check data integrity and sync with remote repository if needed.

    This function performs comprehensive data integrity checking including:
    - Local file validation against expected structure
    - Remote repository synchronization checks
    - Automatic data updates when configured
    - Age-based data freshness validation

    Args:
        config: ProjectConfig instance with validation and sync settings

    Raises:
        FileNotFoundError: If required data files are missing and cannot be obtained

    Validation Process:
        1. Validate local data files against expected structure
        2. Check remote repository for updates (if token available)
        3. Download updates if auto_download is enabled and data is outdated
        4. Re-validate data after any updates

    Note:
        - Requires HF_API_TOKEN for remote repository access
        - Respects auto_download configuration setting
        - Considers data older than 1 day as potentially outdated
    """
    logger.info("Checking data integrity...")

    try:
        # Load config settings
        repo_id = config.config["huggingface_repo"]
        auto_download = config.config.get("auto_download", True)

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
                logger.error(
                    f"Please download data from: https://huggingface.co/datasets/{repo_id}"
                )
                raise

        # Check for updates if possible
        try:
            from huggingface_hub import HfApi

            api_token = os.getenv("HF_API_TOKEN")
            if api_token:
                api = HfApi(token=api_token)
            else:
                api = HfApi()
            repo_info = api.dataset_info(repo_id=repo_id)
            logger.info(f"Remote data last modified: {repo_info.last_modified}")

            if auto_download:
                # Simple check: if data directory is older than 1 day, consider update
                data_age = (
                    datetime.now()
                    - datetime.fromtimestamp(config.data_dir.stat().st_mtime)
                ).days
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


def load_population_2025_with_validation(
    config, apply_study_area_mask: bool = True
) -> Tuple[np.ndarray, dict, bool]:
    """
    Load 2025 population data with proper resolution handling and validation.

    This function provides specialized loading of Global Human Settlement (GHS) 2025
    population projection data with comprehensive resolution adaptation, geographic
    masking, and statistical validation against ground truth population totals.

    Args:
        config: ProjectConfig instance with data paths and validation parameters
        apply_study_area_mask: Whether to apply Netherlands study area masking

    Returns:
        Tuple of (population_data, metadata, validation_passed):
            - population_data: Processed population raster as numpy array
            - metadata: Dictionary with transformation and processing metadata
            - validation_passed: Boolean indicating if validation against ground truth succeeded

    Key Features:
        - Intelligent resolution adaptation preserving population totals
        - Geographic masking using NUTS boundaries and land mass data
        - Statistical validation against known population totals
        - Proper handling of coordinate transformations
        - Area-based scaling corrections for resolution changes

    Resolution Handling:
        - Source: 3 arcsecond GHS data (~92.8m × 57.1m in Netherlands)
        - Target: 30m × 30m grid for consistent analysis
        - Uses bilinear resampling with area scaling to preserve totals
        - Avoids population inflation from improper density resampling

    Validation:
        - Compares processed totals against expected Netherlands population
        - Applies configurable tolerance thresholds
        - Provides detailed analysis of validation results
        - Identifies potential issues with masking or transformation

    Note:
        - Critical for accurate population-based risk assessments
        - Requires careful validation due to resolution and masking complexity
        - Uses RasterTransformer for consistent coordinate handling
    """
    logger.info(
        "Loading 2025 population data with resolution adaptation and validation..."
    )

    # Initialize transformer with GHS-aware parameters
    transformer = RasterTransformer(target_crs=config.target_crs, config=config)

    # Get reference bounds from NUTS L3 shapefile
    nuts_l3_path = config.data_dir / "NUTS-L3-NL.shp"
    reference_bounds = transformer.get_reference_bounds(nuts_l3_path)

    # Load the 2025 population file (3 arcsecond, WGS84)
    population_2025_path = config.population_2025_path

    if not population_2025_path.exists():
        raise FileNotFoundError(
            f"2025 population file not found: {population_2025_path}"
        )

    logger.info(f"Loading 2025 population from: {population_2025_path}")

    # Check source resolution and coordinate system
    with rasterio.open(population_2025_path) as src:
        logger.info(f"Source CRS: {src.crs}")
        logger.info(f"Source resolution: {src.res}")
        logger.info(f"Source bounds: {src.bounds}")
        logger.info(f"Source shape: {src.shape}")

    # Transform to target resolution and CRS with appropriate resampling
    # CRITICAL FIX: Population data must preserve TOTAL count, not density
    # Source: 57.1m x 92.8m pixels (5,298 m²)
    # Target: 30m x 30m pixels (900 m²)
    # Problem: 'average' resampling copies density to all new pixels → inflates total by ~6x

    effective_resolution = config.ghs_native_resolution_meters_netherlands

    if effective_resolution > config.target_resolution:
        # For population downsampling, we need to preserve TOTAL population
        # Use 'bilinear' for smooth interpolation while attempting to preserve totals
        resampling_method = "bilinear"

        # Calculate the area scaling factor
        source_pixel_area = effective_resolution * config.ghs_latitude_resolution_meters
        target_pixel_area = config.target_resolution * config.target_resolution
        area_ratio = target_pixel_area / source_pixel_area

        logger.info(
            f"Downsampling GHS data from {effective_resolution}m x {config.ghs_latitude_resolution_meters}m to {config.target_resolution}m"
        )
        logger.info(
            f"Source pixel area: {source_pixel_area:.0f} m², Target: {target_pixel_area:.0f} m²"
        )
        logger.info("Using bilinear resampling to preserve spatial distribution")
        logger.info(
            f"Area ratio: {area_ratio:.3f} - population values will be scaled by this factor"
        )
    else:
        # Upsampling: use sum to preserve population totals
        resampling_method = "sum"
        area_ratio = 1.0
        logger.info(
            f"Upsampling GHS data from {effective_resolution}m to {config.target_resolution}m using sum aggregation"
        )

    population_data, transform, crs = transformer.transform_raster(
        population_2025_path,
        reference_bounds=reference_bounds,
        resampling_method=resampling_method,
    )

    # Apply area scaling correction for downsampling
    if effective_resolution > config.target_resolution:
        logger.info(
            f"Applying area scaling correction: multiplying by {area_ratio:.3f}"
        )
        total_before = np.sum(population_data[population_data > 0])
        population_data = population_data * area_ratio
        total_after = np.sum(population_data[population_data > 0])
        logger.info(
            f"Population total: {total_before:,.0f} -> {total_after:,.0f} (correction factor: {total_after / total_before:.3f})"
        )

    metadata = {
        "transform": transform,
        "crs": crs,
        "height": population_data.shape[0],
        "width": population_data.shape[1],
        "source_file": str(population_2025_path),
        "resampling_method": resampling_method,
        "area_scaling_applied": effective_resolution > config.target_resolution,
        "area_scaling_factor": area_ratio
        if effective_resolution > config.target_resolution
        else 1.0,
    }

    # Apply study area masking if requested
    if apply_study_area_mask:
        population_data = _apply_netherlands_study_area_mask(
            population_data, transform, population_data.shape, config, transformer
        )

    # Validate against ground truth if validation parameters are available
    validation_passed = True
    if hasattr(config, "expected_nl_population_2025") and hasattr(
        config, "population_tolerance_percent"
    ):
        validation_passed = _validate_population_total(
            population_data,
            config.expected_nl_population_2025,
            config.population_tolerance_percent,
        )
    else:
        logger.info(
            "Population validation parameters not configured - skipping validation"
        )

    logger.info(
        f"2025 population data loaded successfully. Validation: {'PASSED' if validation_passed else 'FAILED'}"
    )

    return population_data, metadata, validation_passed


def _apply_netherlands_study_area_mask(
    data: np.ndarray,
    transform: rasterio.Affine,
    shape: Tuple[int, int],
    config,
    transformer: RasterTransformer,
) -> np.ndarray:
    """
    Apply Netherlands study area mask to population data.

    This function creates a precise geographic mask combining NUTS L3 boundaries
    and land mass data to ensure population data is restricted to the relevant
    study area (Netherlands land areas only).

    Args:
        data: Population raster data to mask
        transform: Rasterio affine transformation for the data
        shape: Shape of the raster data (height, width)
        config: ProjectConfig with data paths
        transformer: RasterTransformer for coordinate handling

    Returns:
        np.ndarray: Masked population data with values outside study area set to 0

    Masking Process:
        1. Load NUTS L3 boundaries for Netherlands
        2. Transform boundaries to match raster CRS
        3. Create rasterized mask from NUTS boundaries
        4. Load and align land mass data
        5. Combine both masks (must be within NUTS AND on land)
        6. Apply combined mask to population data

    Note:
        - Ensures population data is geographically accurate
        - Prevents inclusion of water areas and foreign territories
        - Provides detailed logging of masking statistics
        - Falls back gracefully if masking fails
    """
    logger.info("Applying Netherlands study area mask to 2025 population data...")

    try:
        # Load NUTS-L3 boundaries for study area definition
        nuts_l3_path = config.data_dir / "NUTS-L3-NL.shp"
        nuts_gdf = gpd.read_file(nuts_l3_path)

        # Ensure NUTS is in target CRS
        target_crs = rasterio.crs.CRS.from_string(config.target_crs)
        if nuts_gdf.crs != target_crs:
            nuts_gdf = nuts_gdf.to_crs(target_crs)

        # Create NUTS mask
        from rasterio.features import rasterize

        nuts_mask = rasterize(
            [(geom, 1) for geom in nuts_gdf.geometry],
            out_shape=shape,
            transform=transform,
            dtype=np.uint8,
        )
        logger.info(
            f"Created NUTS mask: {np.sum(nuts_mask)} pixels within Netherlands boundaries"
        )

        # Load and align land mass data
        resampling_method_str = (
            config.resampling_method.name.lower()
            if hasattr(config.resampling_method, "name")
            else str(config.resampling_method).lower()
        )

        land_mass_data, land_transform, _ = transformer.transform_raster(
            config.land_mass_path,
            reference_bounds=transformer.get_reference_bounds(nuts_l3_path),
            resampling_method=resampling_method_str,
        )

        # Ensure land mass data is aligned with population data
        if not transformer.validate_alignment(
            land_mass_data, land_transform, data, transform
        ):
            land_mass_data = transformer.ensure_alignment(
                land_mass_data, land_transform, transform, shape, resampling_method_str
            )

        # Create land mask (1=land, 0=water/no data)
        land_mask = (land_mass_data > 0).astype(np.uint8)
        logger.info(f"Created land mask: {np.sum(land_mask)} pixels identified as land")

        # Combine masks: only areas that are both within NUTS and on land
        combined_mask = (nuts_mask == 1) & (land_mask == 1)
        logger.info(
            f"Combined study area mask: {np.sum(combined_mask)} pixels in relevant study area"
        )

        # Apply mask to population data
        masked_data = data.copy()
        masked_data[~combined_mask] = 0.0

        # Log masking statistics
        original_nonzero = np.sum(data > 0)
        masked_nonzero = np.sum(masked_data > 0)
        original_total = np.sum(data[data > 0]) if original_nonzero > 0 else 0
        masked_total = np.sum(masked_data[masked_data > 0]) if masked_nonzero > 0 else 0

        logger.info(
            f"Population masking removed {original_nonzero - masked_nonzero} non-zero pixels "
            f"({(original_nonzero - masked_nonzero) / original_nonzero * 100:.1f}% reduction)"
        )
        logger.info(
            f"Population total reduced from {original_total:,.0f} to {masked_total:,.0f} "
            f"({(original_total - masked_total) / original_total * 100:.1f}% reduction)"
        )

        return masked_data

    except Exception as e:
        logger.warning(
            f"Could not apply study area mask to 2025 population data: {str(e)}"
        )
        logger.warning("Proceeding with unmasked population data")
        return data


def _validate_population_total(
    population_data: np.ndarray, expected_total: int, tolerance_percent: float
) -> bool:
    """
    Validate population total against ground truth with tolerance.

    This function performs statistical validation of processed population data
    against known ground truth totals, providing detailed analysis of any
    deviations and potential causes.

    Args:
        population_data: Processed population raster data
        expected_total: Expected total population (ground truth)
        tolerance_percent: Acceptable deviation percentage

    Returns:
        bool: True if validation passed (within tolerance), False otherwise

    Validation Process:
        1. Calculate actual population total from processed data
        2. Compare against expected ground truth total
        3. Check if deviation is within acceptable tolerance
        4. Provide detailed analysis of validation results
        5. Identify potential issues if validation fails

    Detailed Reporting:
        - Expected vs actual population totals
        - Absolute and percentage deviations
        - Tolerance thresholds and acceptable ranges
        - Diagnostic information for validation failures

    Common Validation Issues:
        - Source data covers broader geographic area than expected
        - Study area masking not restrictive enough
        - Resolution handling affecting population totals
        - Ground truth applies to different geographic scope

    Note:
        - Critical for ensuring data quality and accuracy
        - Provides comprehensive diagnostic information
        - Helps identify processing pipeline issues
    """

    # Calculate actual total
    valid_data = population_data[~np.isnan(population_data) & (population_data > 0)]
    actual_total = int(valid_data.sum()) if len(valid_data) > 0 else 0

    # Calculate tolerance range
    tolerance_absolute = int(expected_total * tolerance_percent / 100)
    min_acceptable = expected_total - tolerance_absolute
    max_acceptable = expected_total + tolerance_absolute

    # Check if within tolerance
    validation_passed = min_acceptable <= actual_total <= max_acceptable

    logger.info("=" * 70)
    logger.info("POPULATION VALIDATION RESULTS")
    logger.info("=" * 70)
    logger.info(f"Expected total (Netherlands 2025): {expected_total:,} persons")
    logger.info(f"Actual total (processed): {actual_total:,} persons")
    logger.info(f"Difference: {actual_total - expected_total:,} persons")
    logger.info(f"Tolerance: ±{tolerance_percent}% (±{tolerance_absolute:,} persons)")
    logger.info(f"Acceptable range: {min_acceptable:,} - {max_acceptable:,} persons")
    logger.info(f"Validation: {'✓ PASSED' if validation_passed else '✗ FAILED'}")

    if not validation_passed:
        deviation_percent = abs(actual_total - expected_total) / expected_total * 100
        logger.warning(
            f"Population total deviates by {deviation_percent:.1f}% from expected ground truth"
        )
        logger.warning("This may indicate issues with:")
        logger.warning("- Source data covers broader geographic area than Netherlands")
        logger.warning("- Study area masking not restrictive enough")
        logger.warning("- Resolution handling during transformation")
        logger.warning("- Ground truth applies to different geographic scope")

        # Specific analysis for high totals
        if actual_total > expected_total * 2:
            logger.warning("ANALYSIS: Population total is much higher than expected")
            logger.warning(
                "- 2025 GHS file appears to cover multiple countries (Germany, Belgium, etc.)"
            )
            logger.warning(
                "- Current masking using NUTS-L3 + land mask may not be sufficient"
            )
            logger.warning("- Consider using more restrictive geographic boundaries")

    logger.info("=" * 70)

    return validation_passed
