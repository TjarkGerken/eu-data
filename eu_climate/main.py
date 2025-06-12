#!/usr/bin/env python3
"""
EU Climate Risk Assessment System
=================================

A comprehensive geospatial analysis tool for assessing climate risks in European regions.
This system implements a four-layer approach: Hazard, Exposition, Relevance, and Risk.

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
import sys
from eu_climate.risk_layers.exposition_layer import ExpositionLayer
from eu_climate.risk_layers.hazard_layer import HazardLayer, SeaLevelScenario
from eu_climate.risk_layers.relevance_layer import RelevanceLayer
from eu_climate.config.config import ProjectConfig
from eu_climate.utils.utils import setup_logging, suppress_warnings
from eu_climate.utils.data_loading import get_config, upload_data, validate_env_vars
from eu_climate.utils.cache_utils import initialize_caching, create_cached_layers, print_cache_status
from eu_climate.utils.caching_wrappers import cache_relevance_layer
import numpy as np
import rasterio
import rasterio.mask
import rasterio.features
import rasterio.warp
from rasterio.enums import Resampling
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Tuple, List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
from sklearn.preprocessing import MinMaxScaler
import subprocess
from datetime import datetime
from huggingface_hub import HfApi
from dotenv import load_dotenv

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
    

    """
    
    def __init__(self, config: ProjectConfig):
        """Initialize Risk Assessment with configuration."""
        self.config = config
        
        # Create layer instances
        self.hazard_layer = HazardLayer(config)
        self.exposition_layer = ExpositionLayer(config)
        self.relevance_layer = RelevanceLayer(config)
        
        self._apply_caching()
        
        # Results storage
        self.risk_indices = {}
        self.risk_classifications = {}
        
        logger.info("Initialized Risk Assessment System")
        
    def _apply_caching(self):
        """Apply caching to layer instances if enabled."""
        try:
            # Create cached versions of the layers
            cached_layers = create_cached_layers(
                hazard_layer=self.hazard_layer,
                exposition_layer=self.exposition_layer,
                relevance_layer=self.relevance_layer,
                risk_assessment=self,
                config=self.config
            )
            
            # Replace instances with cached versions
            if 'hazard' in cached_layers:
                self.hazard_layer = cached_layers['hazard']
            if 'exposition' in cached_layers:
                self.exposition_layer = cached_layers['exposition']
            if 'relevance' in cached_layers:
                self.relevance_layer = cached_layers['relevance']
                
            logger.info("Caching applied to risk assessment layers")
            
        except Exception as e:
            logger.warning(f"Could not apply caching: {e}")
            logger.info("Continuing without caching...")

    def run_exposition(self, config:ProjectConfig) -> None:

        logger.info("="*40)
        logger.info("EXPOSITION LAYER ANALYSIS")
        logger.info("="*40)
        exposition_layer = ExpositionLayer(config)
        exposition_layer.run_exposition(visualize=True, export_path=str(config.output_dir / 'exposition_layer.tif'), create_png=True)

    def run_risk_assessment(self, config: ProjectConfig, 
                           run_hazard: bool = True,
                           run_exposition: bool = True, 
                           run_relevance: bool = True,
                           create_png_outputs: bool = True,
                           visualize: bool = False) -> Dict[str, Any]:
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

        return risk_indices
        
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
        
        # Create hazard layer instance
        hazard_layer = HazardLayer(config)
        
        # Apply caching if enabled
        try:
            cached_layers = create_cached_layers(hazard_layer=hazard_layer, config=config)
            if 'hazard' in cached_layers:
                hazard_layer = cached_layers['hazard']
        except Exception as e:
            logger.warning(f"Could not apply caching to hazard layer: {e}")
        
        # Process default scenarios (1m, 2m, 3m sea level rise)
        flood_extents = hazard_layer.process_scenarios()
        
        # Create visualizations
        # hazard_layer.visualize_hazard_assessment(flood_extents, save_plots=True)
        
        # Export results
        hazard_layer.export_results(flood_extents, create_png=True)
    
    def run_relevance_layer_analysis(self, config: ProjectConfig) -> None:
        """
        Run the Relevance Layer analysis for the EU Climate Risk Assessment System.
        
        Args:
            config: Project configuration object containing paths and settings.
        """
        logger.info("\n" + "="*40)
        logger.info("RELEVANCE LAYER ANALYSIS")
        logger.info("="*40)
        
        # Apply caching if enabled
        try:
            cached_relevance_layer = cache_relevance_layer(self.relevance_layer)
            self.relevance_layer = cached_relevance_layer
        except Exception as e:
            logger.warning(f"Could not apply caching to relevance layer: {e}")
        
        # Process relevance layer analysis
        relevance_layers = self.relevance_layer.run_relevance_analysis(
            visualize=True,
            export_individual_tifs=True,
            output_dir=config.output_dir
        )
        
        logger.info(f"Relevance layer analysis completed - Generated {len(relevance_layers)} layers")

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
    
    # Perform data integrity check BEFORE creating any layers
    logger.info("\n" + "="*40)
    logger.info("DATA INTEGRITY CHECK")
    logger.info("="*40)
    check_data_integrity(config)
    
    # Now create RiskAssessment instance after data is confirmed available
    risk_assessment = RiskAssessment(config)
    
    # Initialize caching system
    try:
        cache_integrator = initialize_caching(config)
        logger.info("Caching system initialized")
    except Exception as e:
        logger.warning(f"Could not initialize caching: {e}")
        logger.info("Continuing without caching...")
    
    try:
        # Run the analysis
        # risk_assessment.run_hazard_layer_analysis(config)
        risk_assessment.run_exposition(config)
        # risk_assessment.run_relevance_layer_analysis(config)
        
        # Upload data after successful analysis (if enabled)
        logger.info("\n" + "="*40)
        logger.info("DATA UPLOAD CHECK")
        logger.info("="*40)
        upload_data()
        
        # Print cache statistics if caching is enabled
        try:
            print_cache_status(config)
        except Exception as e:
            logger.debug(f"Could not print cache statistics: {e}")
        
    except Exception as e:
        logger.error(f"Error during analysis: {str(e)}")
        raise

if __name__ == "__main__":
    main()
