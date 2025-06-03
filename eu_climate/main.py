#!/usr/bin/env python3
"""
EU Climate Risk Assessment System
=================================

A comprehensive geospatial analysis tool for assessing climate risks in European regions.
This system implements a three-layer approach: Hazard, Exposition, and Risk.

Technical Implementation:
- Robust and reproducible data processing pipeline
- ETL processes for harmonizing diverse datasets
- Standardized cartographic projections
- Risk approximation based on climate data and normalization factors
- Downsampling techniques for fine-grained spatial analysis
- Code-based visualizations in Python

Authors: EU Geolytics Team
Version: 1.0.0
"""

import os
from eu_climate.risk_layers.exposition_layer import ExpositionLayer
from eu_climate.risk_layers.hazard_layer import HazardLayer, SeaLevelScenario
from eu_climate.config.config import ProjectConfig
from eu_climate.utils.utils import setup_logging, suppress_warnings
from eu_climate.utils.data_loading import get_config
import numpy as np
import rasterio
import rasterio.mask
import rasterio.features
import rasterio.warp
from rasterio.enums import Resampling
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass
from enum import Enum
from sklearn.preprocessing import MinMaxScaler

# Set up logging for the main module
logger = setup_logging(__name__)

class RiskLayer(Enum):
    """Enumeration for the three risk assessment layers."""
    HAZARD = "hazard"
    EXPOSITION = "exposition"  
    RISK = "risk"

class RiskAssessment:
    """
    Risk Assessment Implementation
    ============================
    
    Integrates Hazard and Exposition layers to produce comprehensive
    climate risk assessments. Implements the three-layer approach:
    1. Hazard (sea level rise, climate indicators)
    2. Exposition (building density, population, economic factors)
    3. Risk (combined assessment with weighted factors)
    
    Features:
    - Multi-factor risk calculation
    - Scenario-based assessment
    - Spatial risk classification
    - Result visualization and export
    """
    
    def __init__(self, config: ProjectConfig):
        """Initialize Risk Assessment with configuration."""
        self.config = config
        self.hazard_layer = HazardLayer(config)
        self.exposition_layer = ExpositionLayer(config)
        
        # Results storage
        self.risk_indices = {}
        self.risk_classifications = {}
        
        logger.info("Initialized Risk Assessment System")
        
    def prepare_data(self) -> None:
        """Prepare all necessary data from both layers."""
        # Load and process hazard data
        logger.info("Preparing hazard data...")
        dem_data, transform, crs = self.hazard_layer.load_and_prepare_dem()
        dem_shape = dem_data.shape
        
        # Set reference grid for exposition layer
        self.exposition_layer.set_reference_grid(transform, crs, dem_shape)
        
        # Load and process exposition data
        logger.info("Preparing exposition data...")
        self.exposition_layer.load_building_data()
        self.exposition_layer.load_population_data()
        
    def calculate_integrated_risk(self, 
                                scenarios: Optional[List[SeaLevelScenario]] = None,
                                hazard_weight: float = 0.4,
                                exposition_weight: float = 0.4,
                                economic_weight: float = 0.2) -> Dict[str, np.ndarray]:
        """
        Calculate integrated risk assessment for given scenarios.
        
        Args:
            scenarios: List of sea level scenarios to assess
            hazard_weight: Weight for hazard factors
            exposition_weight: Weight for exposition factors
            economic_weight: Weight for economic factors
            
        Returns:
            Dictionary mapping scenario names to risk indices
        """
        if scenarios is None:
            scenarios = SeaLevelScenario.get_default_scenarios()
            
        # Process hazard scenarios
        flood_extents = self.hazard_layer.process_scenarios(scenarios)
        
        # Calculate exposition index
        exposure_index = self.exposition_layer.calculate_exposure_index()
        
        # Process economic exposure
        economic_exposure = self.exposition_layer.process_economic_exposure()
        
        # Calculate risk for each scenario
        for scenario in scenarios:
            logger.info(f"Calculating risk for scenario: {scenario.name}")
            
            # Get flood extent for this scenario
            flood_extent = flood_extents[scenario.name]
            
            # Normalize flood extent
            norm_flood = flood_extent.astype(float)
            
            # Calculate combined risk index
            risk_index = (
                hazard_weight * norm_flood +
                exposition_weight * exposure_index +
                economic_weight * economic_exposure
            )
            
            # Store results
            self.risk_indices[scenario.name] = risk_index
            
            # Classify risk levels
            risk_classes = self._classify_risk_levels(risk_index)
            self.risk_classifications[scenario.name] = risk_classes
            
            # Log statistics
            self._log_risk_statistics(scenario.name, risk_index, risk_classes)
            
        return self.risk_indices
    
    def _classify_risk_levels(self, risk_index: np.ndarray, n_classes: int = 5) -> np.ndarray:
        """Classify risk index into discrete risk levels."""
        # Use sklearn's MinMaxScaler for robust normalization
        scaler = MinMaxScaler()
        normalized_risk = scaler.fit_transform(risk_index.reshape(-1, 1))
        
        # Create risk classes
        risk_classes = np.digitize(
            normalized_risk,
            bins=np.linspace(0, 1, n_classes+1)[1:-1]
        )
        
        return risk_classes.reshape(risk_index.shape)
    
    def _log_risk_statistics(self, scenario_name: str, 
                           risk_index: np.ndarray,
                           risk_classes: np.ndarray) -> None:
        """Log risk assessment statistics."""
        logger.info(f"Risk Assessment Statistics for {scenario_name}:")
        logger.info(f"  Mean risk index: {np.nanmean(risk_index):.3f}")
        logger.info(f"  Max risk index: {np.nanmax(risk_index):.3f}")
        
        # Calculate area percentages for each risk class
        total_valid = np.sum(~np.isnan(risk_index))
        for class_idx in range(1, 6):
            class_percentage = np.sum(risk_classes == class_idx) / total_valid * 100
            logger.info(f"  Risk Class {class_idx}: {class_percentage:.1f}% of area")
    
    def visualize_risk_assessment(self, save_plots: bool = True) -> None:
        """Create visualizations of risk assessment results."""
        if not self.risk_indices:
            raise ValueError("No risk assessment results to visualize")
            
        for scenario_name, risk_index in self.risk_indices.items():
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=self.config.figure_size)
            
            # Plot risk index
            im1 = ax1.imshow(risk_index, cmap='RdYlBu_r')
            ax1.set_title(f'Risk Index - {scenario_name}')
            plt.colorbar(im1, ax=ax1)
            
            # Plot risk classification
            risk_classes = self.risk_classifications[scenario_name]
            im2 = ax2.imshow(risk_classes, cmap='RdYlBu_r', vmin=1, vmax=5)
            ax2.set_title(f'Risk Classification - {scenario_name}')
            plt.colorbar(im2, ax=ax2, ticks=[1, 2, 3, 4, 5])
            
            if save_plots:
                output_path = self.config.output_dir / f"risk_assessment_{scenario_name}.png"
                plt.savefig(output_path, dpi=self.config.dpi, bbox_inches='tight')
                logger.info(f"Saved visualization to {output_path}")
            
            plt.close()
    
    def export_results(self) -> None:
        """Export risk assessment results to GeoTIFF files."""
        if not self.risk_indices:
            raise ValueError("No risk assessment results to export")
            
        for scenario_name, risk_index in self.risk_indices.items():
            # Export risk index
            risk_path = self.config.output_dir / f"risk_index_{scenario_name}.tif"
            with rasterio.open(
                risk_path,
                'w',
                driver='GTiff',
                height=risk_index.shape[0],
                width=risk_index.shape[1],
                count=1,
                dtype=risk_index.dtype,
                crs=self.hazard_layer.crs,
                transform=self.hazard_layer.transform
            ) as dst:
                dst.write(risk_index, 1)
            
            # Export risk classification
            class_path = self.config.output_dir / f"risk_classes_{scenario_name}.tif"
            risk_classes = self.risk_classifications[scenario_name]
            with rasterio.open(
                class_path,
                'w',
                driver='GTiff',
                height=risk_classes.shape[0],
                width=risk_classes.shape[1],
                count=1,
                dtype=risk_classes.dtype,
                crs=self.hazard_layer.crs,
                transform=self.hazard_layer.transform
            ) as dst:
                dst.write(risk_classes, 1)
                
        logger.info(f"Exported risk assessment results to {self.config.output_dir}")


    def run_exposition(self, config:ProjectConfig) -> None:
        # Future layers (placeholders)
        logger.info("="*40)
        logger.info("EXPOSITION LAYER ANALYSIS")
        logger.info("="*40)
        exposition_layer = ExpositionLayer(config)
        exposition_layer.run_exposition(visualize=True, export_path=str(config.output_dir / 'exposition_layer.tif'))

    def run_risk_assessment(self, config: ProjectConfig) -> None:
        """
        Run the complete risk assessment process.
        This includes preparing data, calculating risk indices,
        visualizing results, and exporting to files.
        """
        logger.info("\n" + "="*40)
        logger.info("RISK ASSESSMENT INTEGRATION")
        logger.info("="*40)
        risk_assessment = RiskAssessment(config)
        # Prepare data for risk assessment
        risk_assessment.prepare_data()
        
        # Calculate integrated risk
        risk_indices = risk_assessment.calculate_integrated_risk()
        
        # Visualize risk assessment
        risk_assessment.visualize_risk_assessment(save_plots=True)
        
        # Export results
        risk_assessment.export_results()
        
        logger.info("\n" + "="*60)
        logger.info("ANALYSIS COMPLETE")
        logger.info("="*60)
        logger.info(f"Results saved to: {config.output_dir}")

        
    @staticmethod
    def run_hazard_layer_analysis(config: ProjectConfig) -> None:
        """
        Run the Hazard Layer analysis for the EU Climate Risk Assessment System.
        
        Args:
            config: Project configuration object containing paths and settings.
        """
        logger.info("\n" + "="*40)
        logger.info("HAZARD LAYER ANALYSIS")
        logger.info("="*40)
        
        hazard_layer = HazardLayer(config)
        
        # Process default scenarios (1m, 2m, 3m sea level rise)
        flood_extents = hazard_layer.process_scenarios()
        
        # Create visualizations
        hazard_layer.visualize_hazard_assessment(flood_extents, save_plots=True)
        
        # Export results
        hazard_layer.export_results(flood_extents)




def main():
    """
    Main execution function for the EU Climate Risk Assessment System.
    """
    suppress_warnings()
    logger.info("=" * 60)
    logger.info("EU CLIMATE RISK ASSESSMENT SYSTEM")
    logger.info("=" * 60)
    
    # Initialize project configuration
    config = ProjectConfig()
    logger.info(f"Project initialized with data directory: {config.data_dir}")
    
    try:
        # RiskAssessment.run_hazard_layer_analysis(config)
        RiskAssessment(config).run_exposition(config)
        
    except Exception as e:
        logger.error(f"Error during analysis: {str(e)}")
        raise

if __name__ == "__main__":
    main()
