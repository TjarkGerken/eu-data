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
import argparse
from eu_climate.risk_layers.exposition_layer import ExpositionLayer
from eu_climate.risk_layers.hazard_layer import HazardLayer, SeaLevelScenario
from eu_climate.risk_layers.relevance_layer import RelevanceLayer
from eu_climate.risk_layers.risk_layer import RiskLayer
from eu_climate.config.config import ProjectConfig
from eu_climate.utils.utils import setup_logging, suppress_warnings
from eu_climate.utils.data_loading import check_data_integrity, get_config, upload_data, validate_env_vars
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

class AssessmentLayer(Enum):
    """Enumeration for the risk assessment layers."""
    HAZARD = "hazard"
    EXPOSITION = "exposition"  
    RELEVANCE = "relevance"
    RISK = "risk"
    POPULATION = "population"

def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments for controlling which risk layers to process.
    
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="EU Climate Risk Assessment System - Control which layers to process",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m main --hazard                    # Run only hazard layer analysis
  python -m main --exposition                # Run only exposition layer analysis  
  python -m main --relevance                 # Run only relevance layer analysis
  python -m main --risk                      # Run only risk layer analysis
  python -m main --population                # Run only population risk layer analysis
  python -m main --hazard --exposition       # Run hazard and exposition layers
  python -m main --all                       # Run all layers (default behavior)
  python -m main --verbose --risk            # Run risk layer with verbose logging
  python -m main --no-cache --hazard         # Run hazard layer without caching
  python -m main --no-upload --all           # Run all layers without data upload
        """
    )
    
    # Layer selection arguments
    layer_group = parser.add_argument_group('Layer Selection', 
                                           'Choose which risk assessment layers to process')
    
    layer_group.add_argument('--hazard', 
                           action='store_true',
                           help='Process Hazard Layer (sea level rise scenarios)')
    
    layer_group.add_argument('--exposition', 
                           action='store_true',
                           help='Process Exposition Layer (building density, population)')
    
    layer_group.add_argument('--relevance', 
                           action='store_true',
                           help='Process Relevance Layer (economic factors, GDP)')
    
    layer_group.add_argument('--risk', 
                           action='store_true',
                           help='Process Risk Layer (integrated risk assessment)')
    
    layer_group.add_argument('--population', 
                           action='store_true',
                           help='Process Population Risk Layer (population-based risk assessment)')
    
    layer_group.add_argument('--all', 
                           action='store_true',
                           help='Process all layers (hazard, exposition, relevance, risk, population)')
    
    # Configuration arguments
    config_group = parser.add_argument_group('Configuration Options',
                                           'Control execution behavior and output')
    
    config_group.add_argument('--verbose', '-v',
                            action='store_true',
                            help='Enable verbose logging output')
    
    config_group.add_argument('--no-cache',
                            action='store_true',
                            help='Disable caching system')
    
    config_group.add_argument('--no-upload',
                            action='store_true',
                            help='Skip data upload to Hugging Face')
    
    config_group.add_argument('--no-visualize',
                            action='store_true',
                            help='Skip visualization generation')
    
    config_group.add_argument('--output-dir',
                            type=str,
                            help='Custom output directory for results')
    
    # Quality control arguments
    quality_group = parser.add_argument_group('Quality Control',
                                            'Data validation and integrity checks')
    
    quality_group.add_argument('--skip-integrity-check',
                             action='store_true',
                             help='Skip data integrity validation')
    
    quality_group.add_argument('--force-regenerate',
                             action='store_true',
                             help='Force regeneration of all outputs (ignore existing files)')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not any([args.hazard, args.exposition, args.relevance, args.risk, args.population, args.all]):
        # If no specific layers are chosen, default to --all
        logger.info("No specific layers selected, defaulting to --all")
        args.all = True
    
    # If --all is specified, enable all individual layers
    if args.all:
        args.hazard = True
        args.exposition = True  
        args.relevance = True
        args.risk = True
        args.population = True
    
    return args

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
        self.risk_layer = RiskLayer(config)
        
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
        exposition_layer.run_exposition_with_all_economic_layers(visualize=False, create_png=True, show_ports=True, show_port_buffers=False)

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
        
        risk_layer = RiskLayer(config)
        
        # Run complete risk assessment with all scenario combinations
        risk_scenarios = risk_layer.run_risk_assessment(
            visualize=visualize,
            export_results=True
        )
        
        logger.info("\n" + "="*60)
        logger.info("ANALYSIS COMPLETE")
        logger.info("="*60)
        logger.info(f"Results saved to: {config.output_dir}")

        return risk_scenarios
        
    def run_hazard_layer_analysis(self, config: ProjectConfig) -> None:
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

        slr_scenarios = [
            SeaLevelScenario("Current", 0.0, "Current sea level - todays scenario"),
            SeaLevelScenario("Conservative", 1.0, "1m sea level rise - conservative scenario"),
            SeaLevelScenario("Moderate", 2.0, "2m sea level rise - moderate scenario"),
            SeaLevelScenario("Severe", 3.0, "3m sea level rise - severe scenario")
        ]
        
        flood_extents = hazard_layer.process_scenarios(slr_scenarios)
        
        # hazard_layer.visualize_hazard_assessment(flood_extents, save_plots=True)
        
        hazard_layer.export_results(flood_extents)
    
    def run_relevance_layer_analysis(self, config: ProjectConfig) -> None:
        """
        Run the Relevance Layer analysis for the EU Climate Risk Assessment System.
        
        Args:
            config: Project configuration object containing paths and settings.
        """
        logger.info("\n" + "="*40)
        logger.info("RELEVANCE LAYER ANALYSIS")
        logger.info("="*40)
    
        try:
            cached_relevance_layer = cache_relevance_layer(self.relevance_layer)
            self.relevance_layer = cached_relevance_layer
        except Exception as e:
            logger.warning(f"Could not apply caching to relevance layer: {e}")
        
        # Process relevance layer analysis
        relevance_layers = self.relevance_layer.run_relevance_analysis(
            visualize=True,
            export_individual_tifs=True
        )
        
        logger.info(f"Relevance layer analysis completed - Generated {len(relevance_layers)} layers")
    
    def run_risk_layer_analysis(self, config: ProjectConfig) -> Dict[str, Dict[str, np.ndarray]]:
        """
        Run the Risk Layer analysis for the EU Climate Risk Assessment System.
        
        Args:
            config: Project configuration object containing paths and settings.
            
        Returns:
            Dictionary of risk scenarios
        """
        logger.info("\n" + "="*40)  
        logger.info("RISK LAYER ANALYSIS")
        logger.info("="*40)
        
        try:
            risk_layer = RiskLayer(config)
            
            # Run complete risk assessment
            risk_scenarios = risk_layer.run_risk_assessment(
                visualize=True,
                export_results=True
            )
            
            logger.info(f"Risk layer analysis completed successfully")
            logger.info(f"Processed {len(risk_scenarios)} sea level scenarios")
            
            return risk_scenarios
            
        except Exception as e:
            logger.error(f"Could not execute risk layer analysis: {e}")
            raise e

    def run_population_risk_layer_analysis(self, config: ProjectConfig) -> Dict[str, np.ndarray]:
        """
        Run the Population Risk Layer analysis for the EU Climate Risk Assessment System.
        
        Args:
            config: Project configuration object containing paths and settings.
            
        Returns:
            Dictionary of population risk scenarios
        """
        logger.info("\n" + "="*40)  
        logger.info("POPULATION RISK LAYER ANALYSIS")
        logger.info("="*40)
        
        try:
            risk_layer = RiskLayer(config)
            
            # Run complete population risk assessment
            population_risk_scenarios = risk_layer.run_population_risk_assessment(
                visualize=True,
                export_results=True
            )
            
            logger.info(f"Population risk layer analysis completed successfully")
            logger.info(f"Processed {len(population_risk_scenarios)} sea level scenarios")
            
            return population_risk_scenarios
            
        except Exception as e:
            logger.error(f"Could not execute population risk layer analysis: {e}")
            raise e

def main():
    """
    Main execution function for the EU Climate Risk Assessment System.
    """
    # Parse command line arguments
    args = parse_arguments()
    
    # Configure logging level based on verbose flag
    if args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("Verbose logging enabled")
    
    suppress_warnings()
    logger.info("=" * 60)
    logger.info("EU CLIMATE RISK ASSESSMENT SYSTEM")
    logger.info("=" * 60)
    
    # Log selected layers
    selected_layers = []
    if args.hazard:
        selected_layers.append("Hazard")
    if args.exposition:
        selected_layers.append("Exposition")
    if args.relevance:
        selected_layers.append("Relevance")
    if args.risk:
        selected_layers.append("Risk")
    if args.population:
        selected_layers.append("Population Risk")
    
    logger.info(f"Selected layers: {', '.join(selected_layers)}")
    if args.no_cache:
        logger.info("Caching disabled")
    if args.no_upload:
        logger.info("Data upload disabled")
    if args.no_visualize:
        logger.info("Visualization disabled")
    
    # Initialize project configuration
    config = ProjectConfig()
    
    # Override output directory if specified
    if args.output_dir:
        config.output_dir = Path(args.output_dir)
        config.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using custom output directory: {config.output_dir}")
    
    logger.info(f"Project initialized with data directory: {config.data_dir}")
    
    # Perform data integrity check (unless skipped)
    if not args.skip_integrity_check:
        logger.info("\n" + "="*40)
        logger.info("DATA INTEGRITY CHECK")
        logger.info("="*40)
        check_data_integrity(config)
    else:
        logger.info("Skipping data integrity check")
    
    # Create RiskAssessment instance
    risk_assessment = RiskAssessment(config)
    
    # Initialize caching system (unless disabled)
    if not args.no_cache:
        try:
            initialize_caching(config)
            logger.info("Caching system initialized")
        except Exception as e:
            logger.warning(f"Could not initialize caching: {e}")
            logger.info("Continuing without caching...")
    else:
        logger.info("Caching system disabled")
    
    try:
        # Execute selected layers in logical dependency order
        if args.hazard:
            logger.info(f"\n{'='*50}")
            logger.info("EXECUTING HAZARD LAYER ANALYSIS")
            logger.info(f"{'='*50}")
            risk_assessment.run_hazard_layer_analysis(config)
            
        if args.exposition:
            logger.info(f"\n{'='*50}")
            logger.info("EXECUTING EXPOSITION LAYER ANALYSIS")
            logger.info(f"{'='*50}")
            risk_assessment.run_exposition(config)
            
        if args.relevance:
            logger.info(f"\n{'='*50}")
            logger.info("EXECUTING RELEVANCE LAYER ANALYSIS")
            logger.info(f"{'='*50}")
            risk_assessment.run_relevance_layer_analysis(config)
            
        if args.risk:
            logger.info(f"\n{'='*50}")
            logger.info("EXECUTING RISK LAYER ANALYSIS")
            logger.info(f"{'='*50}")
            risk_scenarios = risk_assessment.run_risk_layer_analysis(config)
            logger.info(f"Risk analysis completed with {len(risk_scenarios)} scenarios")
        
        if args.population:
            logger.info(f"\n{'='*50}")
            logger.info("EXECUTING POPULATION RISK LAYER ANALYSIS")
            logger.info(f"{'='*50}")
            population_risk_scenarios = risk_assessment.run_population_risk_layer_analysis(config)
            logger.info(f"Population risk analysis completed with {len(population_risk_scenarios)} scenarios")
        
        # Data upload (unless disabled)
        if not args.no_upload:
            logger.info("\n" + "="*40)
            logger.info("DATA UPLOAD CHECK")
            logger.info("="*40)
            upload_data()
        else:
            logger.info("Skipping data upload")
        
        # Print cache statistics (unless caching is disabled)
        if not args.no_cache:
            try:
                print_cache_status(config)
            except Exception as e:
                logger.debug(f"Could not print cache statistics: {e}")
        
        logger.info(f"\n{'='*60}")
        logger.info("EXECUTION COMPLETED SUCCESSFULLY")
        logger.info(f"{'='*60}")
        logger.info(f"Results saved to: {config.output_dir}")
        
    except Exception as e:
        logger.error(f"Error during analysis: {str(e)}")
        if args.verbose:
            import traceback
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
        raise

if __name__ == "__main__":
    main()
