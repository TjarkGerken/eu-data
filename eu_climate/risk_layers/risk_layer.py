from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import rasterio
import rasterio.features
import rasterio.warp
import geopandas as gpd
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import os

from eu_climate.config.config import ProjectConfig
from eu_climate.utils.utils import setup_logging
from eu_climate.utils.conversion import RasterTransformer
from eu_climate.utils.visualization import LayerVisualizer
from eu_climate.utils.caching_wrappers import CacheAwareMethod
from eu_climate.risk_layers.hazard_layer import HazardLayer, SeaLevelScenario
from eu_climate.risk_layers.relevance_layer import RelevanceLayer

logger = setup_logging(__name__)

class RiskLayer:
    """
    Risk Layer Implementation
    ========================
    
    The Risk Layer integrates hazard scenarios and economic layers to produce
    comprehensive climate risk assessments for each region.
    
    Key Features:
    - Integration of hazard and economic data
    - Sea level rise scenario analysis
    - Regional risk aggregation
    - Standardized output structure
    - Unified visualization approach
    """
    
    def __init__(self, config: ProjectConfig):
        """Initialize the Risk Layer with project configuration."""
        self.config = config
        self.hazard_layer = HazardLayer(config)
        self.relevance_layer = RelevanceLayer(config)
        
        self.sea_level_scenarios = SeaLevelScenario.get_default_scenarios()
        
        self.transformer = RasterTransformer(
            target_crs=self.config.target_crs,
            config=self.config
        )
        
        self.visualizer = LayerVisualizer(self.config)
        
        logger.info("Initialized Risk Layer")
    
    def load_existing_hazard_outputs(self, 
                                   sea_level_scenarios: List[SeaLevelScenario]) -> Optional[Dict[str, np.ndarray]]:
        """Load existing hazard outputs if they exist."""
        output_dir = Path(self.config.output_dir)
        
        hazard_results = {}
        all_files_exist = True
        
        for scenario in sea_level_scenarios:
            hazard_file = output_dir / f"flood_risk_{scenario.name.lower()}.tif"
            
            if hazard_file.exists():
                logger.info(f"Loading existing hazard data for {scenario.name} from {hazard_file}")
                try:
                    with rasterio.open(hazard_file) as src:
                        hazard_results[scenario.name] = src.read(1)
                except Exception as e:
                    logger.warning(f"Failed to load existing hazard file {hazard_file}: {e}")
                    all_files_exist = False
                    break
            else:
                logger.info(f"Hazard file not found for {scenario.name}: {hazard_file}")
                all_files_exist = False
                break
        
        if all_files_exist:
            logger.info("Successfully loaded all existing hazard outputs")
            return hazard_results
        else:
            logger.info("Not all hazard outputs exist, will regenerate")
            return None
    
    def load_existing_relevance_outputs(self) -> Optional[Dict[str, np.ndarray]]:
        """Load existing relevance outputs if they exist."""
        output_dir = Path(self.config.output_dir)
        
        economic_variables = self.config.config['relevance']['economic_variables']
        relevance_files = {}
        
        for variable in economic_variables:
            relevance_files[variable] = output_dir / f"relevance_{variable}.tif"
        
        relevance_files['combined'] = output_dir / 'relevance_combined.tif'
        
        relevance_results = {}
        all_files_exist = True
        
        for layer_name, file_path in relevance_files.items():
            if file_path.exists():
                logger.info(f"Loading existing relevance data for {layer_name} from {file_path}")
                try:
                    with rasterio.open(file_path) as src:
                        relevance_results[layer_name] = src.read(1)
                except Exception as e:
                    logger.warning(f"Failed to load existing relevance file {file_path}: {e}")
                    all_files_exist = False
                    break
            else:
                logger.info(f"Relevance file not found: {file_path}")
                all_files_exist = False
                break
        
        if all_files_exist:
            logger.info("Successfully loaded all existing relevance outputs")
            return relevance_results
        else:
            logger.info("Not all relevance outputs exist, will regenerate")
            return None

    @CacheAwareMethod(cache_type='raster_data', 
                     input_files=['land_mass_path'],
                     config_attrs=['target_crs', 'target_resolution'])
    def load_land_mask(self) -> Tuple[np.ndarray, rasterio.Affine, rasterio.crs.CRS]:
        """Load and prepare land mass mask for valid study area."""
        logger.info("Loading land mass mask...")
        
        nuts_l3_path = self.config.data_dir / "NUTS-L3-NL.shp"
        reference_bounds = self.transformer.get_reference_bounds(nuts_l3_path)
        
        land_mass_data, transform, crs = self.transformer.transform_raster(
            self.config.land_mass_path,
            reference_bounds=reference_bounds,
            resampling_method=self.config.resampling_method.name.lower() 
            if hasattr(self.config.resampling_method, 'name') 
            else str(self.config.resampling_method).lower()
        )
        
        land_mask = (land_mass_data > 0).astype(np.uint8)
        
        logger.info(f"Land mask shape: {land_mask.shape}")
        logger.info(f"Land coverage: {np.sum(land_mask) / land_mask.size * 100:.1f}%")
        
        return land_mask, transform, crs
    
    @CacheAwareMethod(cache_type='final_results',
                     input_files=['dem_path', 'land_mass_path'],
                     config_attrs=['target_crs', 'target_resolution', 'risk_weights'])
    def process_risk_scenarios(self, 
                             custom_sea_level_scenarios: Optional[List[SeaLevelScenario]] = None) -> Dict[str, np.ndarray]:
        """
        Process sea level rise scenarios with current GDP levels.
        
        Returns:
            Dictionary with structure: {sea_level_scenario: risk_data}
        """
        logger.info("Processing risk scenarios with current GDP levels...")
        
        sea_level_scenarios = custom_sea_level_scenarios or self.sea_level_scenarios
        
        land_mask, transform, crs = self.load_land_mask()
        
        # Try to load existing hazard outputs first
        logger.info("Checking for existing hazard outputs...")
        hazard_results = self.load_existing_hazard_outputs(sea_level_scenarios)
        
        if hazard_results is None:
            logger.info("Regenerating hazard scenarios...")
            hazard_results = self.hazard_layer.process_scenarios(sea_level_scenarios)
        
        # Try to load existing relevance outputs first
        logger.info("Checking for existing relevance outputs...")
        economic_results = self.load_existing_relevance_outputs()
        
        if economic_results is None:
            logger.info("Regenerating economic layers...")
            economic_results = self.relevance_layer.run_relevance_analysis(
                visualize=False, 
                export_individual_tifs=False
            )
        
        risk_scenarios = {}
        
        for slr_scenario in sea_level_scenarios:
            scenario_name = f"SLR-{slr_scenario.name}"
            
            hazard_data = hazard_results[slr_scenario.name]
            
            logger.info(f"Calculating risk for {scenario_name} with current GDP")
            
            risk_data = self.calculate_integrated_risk(
                hazard_data=hazard_data,
                economic_data=economic_results,
                land_mask=land_mask
            )
            
            risk_scenarios[scenario_name] = risk_data
        
        logger.info(f"Processed {len(risk_scenarios)} sea level scenarios")
        return risk_scenarios
    
    def calculate_integrated_risk(self,
                                hazard_data: np.ndarray,
                                economic_data: Dict[str, np.ndarray],
                                land_mask: np.ndarray) -> np.ndarray:
        """
        Calculate integrated risk from hazard and economic data using current GDP levels.
        Uses filtered calculation that only applies economic risk where flood risk exists.
        
        Args:
            hazard_data: Hazard layer data (0-1 normalized)
            economic_data: Dictionary of economic layer data
            land_mask: Valid study area mask
            
        Returns:
            Integrated risk data (0-1 normalized)
        """
        weights = self.config.risk_weights
        hazard_weight = weights['hazard']
        economic_weight = weights['economic']
        
        # Get thresholds from config
        max_safe_flood_risk = self.config.max_safe_flood_risk
        min_economic_value = self.config.min_economic_value
        logger.info(f"Using flood risk threshold: {max_safe_flood_risk}")
        logger.info(f"Using minimum economic value threshold: {min_economic_value}")
        
        # Use current GDP levels (multiplier = 1.0)
        economic_multiplier = 1.0
        
        # Check if economic_data is actually a dictionary of layers or a combined layer
        if isinstance(economic_data, dict) and all(isinstance(v, np.ndarray) for v in economic_data.values()):
            combined_economic = self.combine_economic_layers(
                economic_data, 
                economic_multiplier
            )
        else:
            # If it's already a single combined array, use it directly
            if isinstance(economic_data, dict) and 'combined' in economic_data:
                combined_economic = economic_data['combined'] * economic_multiplier
            else:
                logger.warning(f"Unexpected economic data format: {type(economic_data)}")
                combined_economic = np.zeros_like(land_mask, dtype=np.float32) if isinstance(land_mask, np.ndarray) else np.zeros((100, 100))
        
        if hazard_data.shape != combined_economic.shape:
            logger.info("Aligning economic data to hazard grid...")
            from scipy.ndimage import zoom
            zoom_factors = (
                hazard_data.shape[0] / combined_economic.shape[0],
                hazard_data.shape[1] / combined_economic.shape[1]
            )
            combined_economic = zoom(combined_economic, zoom_factors, order=1)
        
        # Initialize risk data with zeros
        risk_data = np.zeros_like(hazard_data, dtype=np.float32)
        
        # Create masks for filtered calculation
        flood_risk_mask = hazard_data > max_safe_flood_risk
        economic_relevance_mask = combined_economic > min_economic_value
        land_valid_mask = land_mask > 0
        
        # Combined mask: only calculate risk where there is both flood risk AND economic relevance
        calculation_mask = flood_risk_mask & economic_relevance_mask & land_valid_mask
        
        # Apply weighted calculation only where both conditions are met
        if np.any(calculation_mask):
            risk_data[calculation_mask] = (
                hazard_weight * hazard_data[calculation_mask] + 
                economic_weight * combined_economic[calculation_mask]
            )
            
            # Normalize risk data for areas where calculation was applied
            risk_min = np.min(risk_data[calculation_mask])
            risk_max = np.max(risk_data[calculation_mask])
            if risk_max > risk_min:
                risk_data[calculation_mask] = (risk_data[calculation_mask] - risk_min) / (risk_max - risk_min)
            
            logger.info(f"Economic risk calculated for {np.sum(calculation_mask)} cells")
            logger.info(f"Flood risk cells: {np.sum(flood_risk_mask & land_valid_mask)}")
            logger.info(f"Economic relevance cells: {np.sum(economic_relevance_mask & land_valid_mask)}")
            logger.info(f"Combined risk cells: {np.sum(calculation_mask)}")
        else:
            logger.warning("No cells meet both flood risk and economic relevance criteria")
        
        return risk_data
    
    def combine_economic_layers(self, 
                              economic_data: Dict[str, np.ndarray],
                              multiplier: float) -> np.ndarray:
        """Combine multiple economic layers using configured weights."""
        if not economic_data:
            logger.warning("No economic data available, returning zeros")
            return np.zeros((100, 100))  # Placeholder
        
        weights = self.config.relevance_weights or {}
        combined = None
        total_weight = 0
        
        for layer_name, data in economic_data.items():
            weight_key = f"{layer_name}_weight"
            weight = weights.get(weight_key, 1.0 / len(economic_data))
            
            scaled_data = data * multiplier * weight
            
            if combined is None:
                combined = scaled_data
            else:
                if combined.shape != scaled_data.shape:
                    logger.warning(f"Shape mismatch in economic layer {layer_name}")
                    continue
                combined += scaled_data
            
            total_weight += weight
        
        if combined is not None and total_weight > 0:
            combined = combined / total_weight
        
        return combined if combined is not None else np.zeros((100, 100))
    
    def export_risk_scenarios(self, 
                            risk_scenarios: Dict[str, np.ndarray],
                            transform: rasterio.Affine,
                            crs: rasterio.crs.CRS,
                            land_mask: Optional[np.ndarray] = None) -> None:
        """Export risk scenarios to the specified directory structure."""
        logger.info("Exporting risk scenarios...")
        
        # Create metadata dict for visualization
        meta = {
            'transform': transform,
            'crs': crs
        }
        
        for scenario_name, risk_data in risk_scenarios.items():
            output_dir = self.config.output_dir / "risk" / scenario_name
            output_dir.mkdir(parents=True, exist_ok=True)
            
            tif_path = output_dir / f"risk_{scenario_name}.tif"
            
            self.save_risk_raster(risk_data, transform, crs, tif_path)
            
            png_path = output_dir / f"risk_{scenario_name}.png"
            
            self.visualizer.visualize_risk_layer(
                risk_data=risk_data,
                meta=meta,
                scenario_title=scenario_name,
                output_path=png_path,
                land_mask=land_mask
            )
        
        logger.info("Risk scenario export complete")
    
    def save_risk_raster(self, 
                        risk_data: np.ndarray,
                        transform: rasterio.Affine,
                        crs: rasterio.crs.CRS,
                        output_path: Path) -> None:
        """Save risk data as GeoTIFF."""
        with rasterio.open(
            output_path,
            'w',
            driver='GTiff',
            height=risk_data.shape[0],
            width=risk_data.shape[1],
            count=1,
            dtype=risk_data.dtype,
            crs=crs,
            transform=transform,
            compress='lzw'
        ) as dst:
            dst.write(risk_data, 1)
        
        logger.info(f"Saved risk raster: {output_path}")
    
    def run_risk_assessment(self,
                          visualize: bool = True,
                          export_results: bool = True,
                          custom_sea_level_scenarios: Optional[List[SeaLevelScenario]] = None) -> Dict[str, np.ndarray]:
        """
        Run complete risk assessment process using current GDP levels.
        
        Args:
            visualize: Whether to create visualizations
            export_results: Whether to export results to files
            custom_sea_level_scenarios: Custom sea level scenarios
            
        Returns:
            Risk scenario results
        """
        logger.info("Starting risk assessment with current GDP levels...")
        
        risk_scenarios = self.process_risk_scenarios(custom_sea_level_scenarios)
        
        if export_results or visualize:
            land_mask, transform, crs = self.load_land_mask()
            
            if export_results:
                self.export_risk_scenarios(risk_scenarios, transform, crs, land_mask)
        
        logger.info("Risk assessment complete")
        return risk_scenarios 