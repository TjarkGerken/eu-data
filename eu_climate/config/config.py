import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import numpy as np
try:
    from rasterio.enums import Resampling
    RASTERIO_AVAILABLE = True
except ImportError:
    print("Warning: rasterio not available. Web export features will be limited.")
    RASTERIO_AVAILABLE = False
    
    # Create a fallback Resampling enum
    class Resampling:
        nearest = 'nearest'
        bilinear = 'bilinear'
        cubic = 'cubic'
        average = 'average'
import yaml
from eu_climate.utils.utils import setup_logging
# from utils.data_loading import get_config

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
        # Use the eu_climate package directory as the root so that all
        # data-related folders live inside <repo>/eu_climate/ rather than at
        # repository root. This guarantees consistent paths regardless of the
        # current working directory when the code is executed.
        self.workspace_root = Path(__file__).resolve().parent.parent
        self.huggingface_folder = self.workspace_root / self.config['data_paths']['local_data_dir']
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
        
        # Store GHS native resolution parameters (latitude-dependent)
        self.ghs_native_resolution_arcsec = self.config['processing']['ghs_native_resolution_arcsec']
        self.ghs_native_resolution_meters_equator = self.config['processing']['ghs_native_resolution_meters_equator']
        self.ghs_native_resolution_meters_netherlands = self.config['processing']['ghs_native_resolution_meters_netherlands']
        self.ghs_latitude_resolution_meters = self.config['processing']['ghs_latitude_resolution_meters']
        
        # Store risk assessment parameters
        self.n_risk_classes = self.config['risk_assessment']['n_risk_classes']
        self.risk_weights = self.config['risk_assessment']['weights']
        self.ghs_built_c_class_weights = self.config['risk_assessment']['ghs_built_c_class_weights']
        # Store exposition weights
        self.exposition_weights = self.config['exposition']
        
        # Store vierkant stats multipliers
        self.vierkant_stats_multipliers = self.config['exposition']['vierkant_stats_multipliers']
        
        # Store relevance configuration
        relevance_config = self.config.get('relevance', {})
        self.relevance_weights = relevance_config.get('economic_datasets')
        self.economic_datasets = relevance_config.get('economic_datasets', {})
        
        # Store building parameters
        self.base_floor_height = self.config['building']['base_floor_height']
        self.max_floors = self.config['building']['max_floors']
        
        # Store clustering parameters
        self.clustering = self.config.get('clustering', {})
        
        # Store visualization parameters
        self.figure_size = tuple(self.config['visualization']['figure_size'])
        self.dpi = self.config['visualization']['dpi']
        
        # Store web export parameters
        self.web_exports = self.config.get('web_exports', {})
        self.web_exports_enabled = self.web_exports.get('enabled', True)
        self.create_cog = self.web_exports.get('create_cog', True)
        self.create_mvt = self.web_exports.get('create_mvt', True)
        self.cog_settings = self.web_exports.get('cog_settings', {})
        self.mvt_settings = self.web_exports.get('mvt_settings', {})
        
        # Store hazard layer parameters
        hazard_config = self.config.get('hazard', {})
        
        self.river_zones = hazard_config.get('river_zones')
        self.river_risk_decay = hazard_config.get('river_risk_decay')
        self.elevation_risk = hazard_config.get('elevation_risk')
        
        # Store coastline risk parameters
        self.coastline_risk = hazard_config.get('coastline_risk', {})
        
        # Log loaded hazard configuration for debugging
        logger.debug(f"Loaded river zones config: {self.river_zones}")
        logger.debug(f"Loaded river risk decay config: {self.river_risk_decay}")
        logger.debug(f"Loaded elevation risk config: {self.elevation_risk}")
        logger.debug(f"Loaded coastline risk config: {self.coastline_risk}")

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
        # Use higher precision tolerance for decimal validation (up to 6 decimal places)
        tolerance = 1e-6
        
        # Validate risk weights
        weights = self.risk_weights
        total_weight = sum(weights.values())
        if not np.isclose(total_weight, 1.0, atol=tolerance):
            raise ValueError(f"Risk weights must sum to 1.0, got {total_weight:.6f}")
        
        # Validate exposition weights
        exposition_weights = self.exposition_weights
        main_exposition_weight_keys = ['ghs_built_c_weight', 'ghs_built_v_weight', 'population_weight', 'electricity_consumption_weight', 'vierkant_stats_weight']
        main_exposition_total = sum(exposition_weights.get(key, 0) for key in main_exposition_weight_keys)
        if not np.isclose(main_exposition_total, 1.0, atol=tolerance):
            raise ValueError(f"Main exposition weights must sum to 1.0, got {main_exposition_total:.6f}")
        
        # Validate economic dataset exposition weights
        economic_weights = self.economic_exposition_weights
        for dataset_name, dataset_weights in economic_weights.items():
            economic_exposition_total = sum(dataset_weights.values())
            if not np.isclose(economic_exposition_total, 1.0, atol=tolerance):
                raise ValueError(f"Economic dataset '{dataset_name}' exposition weights must sum to 1.0, got {economic_exposition_total:.6f}")
    
    @property
    def dem_path(self) -> Path:
        """Get path to DEM file."""
        return self.data_dir / self.config['file_paths']['dem_file']
    
    @property
    def population_path(self) -> Path:
        """Get path to population density file (2025 GHS data with corrected resolution)."""
        return self.data_dir / self.config['file_paths']['population_2025_file']
    
    @property
    def population_2025_path(self) -> Path:
        """Get path to 2025 population density file (3 arcsecond resolution)."""
        return self.data_dir / self.config['file_paths']['population_2025_file']
    
    @property
    def ghs_built_c_path(self) -> Path:
        """Get path to GHS Built C file."""
        return self.data_dir / self.config['file_paths']['ghs_built_c_file']
    
    @property
    def ghs_built_v_path(self) -> Path:
        """Get path to GHS Built V file."""
        return self.data_dir / self.config['file_paths']['ghs_built_v_file']
    
    @property
    def electricity_consumption_path(self) -> Path:
        """Get path to electricity consumption file."""
        return self.data_dir / self.config['file_paths']['electricity_consumption_file']
    
    @property
    def vierkant_stats_path(self) -> Path:
        """Get path to vierkant stats file."""
        return self.data_dir / self.config['file_paths']['vierkant_stats_file']
    
    @property
    def nuts_paths(self) -> Dict[str, Path]:
        """Get paths to NUTS shapefiles."""
        return {
            level: self.data_dir / path
            for level, path in self.config['file_paths']['nuts_files'].items()
        }
    

    
    @property
    def river_polygons_path(self) -> Path:
        """Get path to river polygons shapefile."""
        return self.data_dir / self.config['file_paths']['river_polygons_file']
    
    @property
    def land_mass_path(self) -> Path:
        """Get path to land mass raster file."""
        return self.data_dir / self.config['file_paths']['land_mass_file']
    
    @property
    def hrst_file_path(self) -> str:
        """Get path to HRST file."""
        return self.config['file_paths']['hrst_file']
    
    @property
    def ghs_duc_path(self) -> Path:
        """Get path to GHS DUC Excel file."""
        return self.data_dir / self.config['file_paths']['ghs_duc_file']
    
    @property
    def gadm_l2_path(self) -> Path:
        """Get path to GADM Level 2 shapefile."""
        return self.data_dir / self.config['file_paths']['gadm_l2_file']
    
    @property
    def port_path(self) -> Path:
        """Get path to port shapefile."""
        return self.data_dir / self.config['file_paths']['port_file']
    
    @property
    def zeevart_freight_path(self) -> Path:
        """Get path to Zeevart freight Excel file."""
        return self.data_dir / self.config['file_paths']['zeevart_freight_file']
    
    @property
    def port_mapping_path(self) -> Path:
        """Get path to port mapping Excel file."""
        return self.data_dir / self.config['file_paths']['port_mapping_file']
    
    @property
    def coastline_path(self) -> Path:
        """Get path to coastline shapefile."""
        return self.data_dir / self.config['file_paths']['coastline_file']
    
    @property
    def nl_forecast_path(self) -> Path:
        """Get path to NL forecast/risk zone GML file."""
        return self.data_dir / self.config['file_paths']['nl_forecast_file']
    
    @property
    def nuts_l0_file_path(self) -> str:
        """Get path to NUTS L0 file."""
        return self.config['file_paths']['nuts_files']['l0']
        
    @property
    def nuts_l1_file_path(self) -> str:
        """Get path to NUTS L1 file."""
        return self.config['file_paths']['nuts_files']['l1']
        
    @property
    def nuts_l2_file_path(self) -> str:
        """Get path to NUTS L2 file."""
        return self.config['file_paths']['nuts_files']['l2']
        
    @property
    def nuts_l3_file_path(self) -> str:
        """Get path to NUTS L3 file."""
        return self.config['file_paths']['nuts_files']['l3']
    
    @property
    def max_safe_flood_risk(self) -> float:
        """Get maximum safe flood risk threshold from config."""
        return self.config['hazard']['flood_risk']['max_safe_flood_risk']
    
    @property
    def min_economic_value(self) -> float:
        """Get minimum economic value threshold from config."""
        return self.config['relevance']['min_economic_value']
    
    @property
    def economic_exposition_weights(self) -> Dict[str, Dict[str, float]]:
        """Get exposition weights for each economic dataset."""
        economic_weights = {}
        for dataset_name, dataset_config in self.economic_datasets.items():
            if 'exposition_weights' in dataset_config:
                economic_weights[dataset_name] = dataset_config['exposition_weights']
        return economic_weights
    
    def validate_files(self) -> bool:
        """Validate that all required input files exist."""
        required_files = [
            (self.dem_path, "DEM"),
            (self.ghs_built_c_path, "GHS Built C"),
            (self.ghs_built_v_path, "GHS Built V"),
            (self.population_2025_path, "Population Density (2025)"),
            (self.electricity_consumption_path, "Electricity Consumption"),
            (self.vierkant_stats_path, "Vierkant Stats"),
            (self.river_polygons_path, "River Polygons"),
            (self.land_mass_path, "Land Mass"),
            (self.coastline_path, "Coastline"),
            *[(path, f"NUTS {level}") for level, path in self.nuts_paths.items()],
            (self.data_dir / self.hrst_file_path, "HRST Data"),
            (self.ghs_duc_path, "GHS DUC Excel"),
            (self.gadm_l2_path, "GADM L2 Shapefile"),
            (self.port_path, "Port Shapefile"),
            (self.zeevart_freight_path, "Zeevart Freight Data"),
            (self.port_mapping_path, "Port Mapping Data")
        ]
        
        missing_files = []
        for file_path, file_desc in required_files:
            if not file_path.exists():
                missing_files.append(f"{file_desc} file not found: {file_path}")
                
        if missing_files:
            raise FileNotFoundError("\n".join(missing_files)) 