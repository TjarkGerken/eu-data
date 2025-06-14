import os
from pathlib import Path
from typing import Dict
import numpy as np
from rasterio.enums import Resampling
import yaml
from eu_climate.utils.utils import setup_logging
# from eu_climate.utils.data_loading import get_config

# Set up logging for the config module
logger = setup_logging(__name__)

class ProjectConfig:
    """
    Project Configuration Management
    ==============================
    
    Handles configuration for the risk assessment project, including:
    - Data paths and file locations
    - Processing parameters
    - Risk assessment weights
    - Building parameters
    - Visualization settings
    """
    
    def get_config(self) -> dict:
        """
            Load configuration from YAML file.

            Returns:
                dict: Configuration dictionary
        """
        # Try multiple possible config locations
        possible_paths = [
            Path(__file__).parent.parent / "config" / "config.yaml"
        ]
        
        for config_path in possible_paths:
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f).get('data', {})
                    if not config:
                        raise ValueError("Invalid configuration file: 'data' section is missing")
                    return config
        
        raise FileNotFoundError(
            "Configuration file not found! Ensure code/config/config.yaml exists."
        )

    def __init__(self):
        """Initialize configuration from YAML file."""
        self.config = self.get_config()
        
        # Set up paths
        self.workspace_root = Path(os.getcwd())
        self.huggingface_folder = self.workspace_root / "eu_climate" / self.config['data_paths']['local_data_dir']
        self.data_dir =  self.huggingface_folder / self.config['data_paths']['source_data_dir']
        self.output_dir = self.huggingface_folder / self.config['data_paths']['local_output_dir']
        
        
        # Ensure directories exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Store processing parameters
        self._set_resampling_method()
        self.smoothing_sigma = self.config['processing']['smoothing_sigma']
        self.target_crs = self.config['processing']['target_crs']
        self.target_resolution = self.config['processing']['target_resolution']
        
        # Store risk assessment parameters
        self.n_risk_classes = self.config['risk_assessment']['n_risk_classes']
        self.risk_weights = self.config['risk_assessment']['weights']
        self.ghs_built_c_class_weights = self.config['risk_assessment']['ghs_built_c_class_weights']
        # Store exposition weights
        self.exposition_weights = self.config['exposition']
        
        # Store relevance weights
        self.relevance_weights = self.config.get('relevance', {}).get('economic_datasets')
        
        # Store building parameters
        self.base_floor_height = self.config['building']['base_floor_height']
        self.max_floors = self.config['building']['max_floors']
        
        # Store visualization parameters
        self.figure_size = tuple(self.config['visualization']['figure_size'])
        self.dpi = self.config['visualization']['dpi']
        
        # Store hazard layer parameters
        hazard_config = self.config.get('hazard', {})
        
        self.river_zones = hazard_config.get('river_zones')
        self.elevation_risk = hazard_config.get('elevation_risk')
        
        # Log loaded hazard configuration for debugging
        logger.debug(f"Loaded river zones config: {self.river_zones}")
        logger.debug(f"Loaded elevation risk config: {self.elevation_risk}")

        # Validate configuration
        self._validate_config()
        
        logger.debug(f"Project initialized with data directory: {self.data_dir}")
        logger.debug(f"Output directory: {self.output_dir}")
        logger.debug(f"Workspace root: {self.workspace_root}")
    
    def _set_resampling_method(self):
        """Convert resampling method string to Resampling enum value."""
        resampling_map = {
            'nearest': Resampling.nearest,
            'bilinear': Resampling.bilinear,
            'cubic': Resampling.cubic,
            'cubic_spline': Resampling.cubic_spline,
            'lanczos': Resampling.lanczos,
            'average': Resampling.average,
            'mode': Resampling.mode,
            'max': Resampling.max,
            'min': Resampling.min,
            'med': Resampling.med,
            'q1': Resampling.q1,
            'q3': Resampling.q3,
            'sum': Resampling.sum,
            'rms': Resampling.rms
        }
        
        method = self.config['processing']['resampling_method']
        if method not in resampling_map:
            raise ValueError(f"Invalid resampling method: {method}. Must be one of: {list(resampling_map.keys())}")
        
        self.resampling_method = resampling_map[method]
    
    def _validate_config(self):
        """Validate configuration values."""
        weights = self.risk_weights
        total_weight = sum(weights.values())
        if not np.isclose(total_weight, 1.0):
            raise ValueError(f"Risk weights must sum to 1.0, got {total_weight}")
    
    @property
    def dem_path(self) -> Path:
        """Get path to DEM file."""
        return self.data_dir / self.config['file_paths']['dem_file']
    
    @property
    def population_path(self) -> Path:
        """Get path to population density file."""
        return self.data_dir / self.config['file_paths']['population_file']
    
    @property
    def ghs_built_c_path(self) -> Path:
        """Get path to GHS Built C file."""
        return self.data_dir / self.config['file_paths']['ghs_built_c_file']
    
    @property
    def ghs_built_v_path(self) -> Path:
        """Get path to GHS Built V file."""
        return self.data_dir / self.config['file_paths']['ghs_built_v_file']
    
    @property
    def nuts_paths(self) -> Dict[str, Path]:
        """Get paths to NUTS shapefiles."""
        return {
            level: self.data_dir / path
            for level, path in self.config['file_paths']['nuts_files'].items()
        }
    
    @property
    def relevant_area_path(self) -> Path:
        """Get path to relevant area shapefile."""
        return self.data_dir / self.config['file_paths']['relevant_area_file']
    
    @property
    def river_segments_path(self) -> Path:
        """Get path to river segments shapefile."""
        return self.data_dir / self.config['file_paths']['river_segments_file']
    
    @property
    def river_nodes_path(self) -> Path:
        """Get path to river nodes shapefile."""
        return self.data_dir / self.config['file_paths']['river_nodes_file']
    
    @property
    def land_mass_path(self) -> Path:
        """Get path to land mass raster file."""
        return self.data_dir / self.config['file_paths']['land_mass_file']
    
    def validate_files(self) -> bool:
        """Validate that all required input files exist."""
        required_files = [
            (self.dem_path, "DEM"),
            (self.ghs_built_c_path, "GHS Built C"),
            (self.ghs_built_v_path, "GHS Built V"),
            (self.population_path, "Population Density"),
            (self.river_segments_path, "River Segments"),
            (self.river_nodes_path, "River Nodes"),
            (self.land_mass_path, "Land Mass"),
            *[(path, f"NUTS {level}") for level, path in self.nuts_paths.items()],
            (self.relevant_area_path, "Relevant Area")
        ]
        
        missing_files = []
        for file_path, file_desc in required_files:
            if not file_path.exists():
                missing_files.append(f"{file_desc} file not found: {file_path}")
                
        if missing_files:
            raise FileNotFoundError("\n".join(missing_files)) 