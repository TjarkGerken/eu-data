#!/usr/bin/env python3
"""
Test script for Relevance Layer implementation
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from eu_climate.config.config import ProjectConfig
from eu_climate.risk_layers.relevance_layer import RelevanceLayer
from eu_climate.utils.caching_wrappers import cache_relevance_layer
from eu_climate.utils.utils import setup_logging

def main():
    """Test the relevance layer implementation."""
    
    # Set up logging
    logger = setup_logging(__name__)
    logger.info("Starting Relevance Layer test")
    
    try:
        # Initialize configuration
        logger.info("Initializing project configuration")
        config = ProjectConfig()
        
        # Initialize relevance layer
        logger.info("Initializing Relevance Layer")
        relevance_layer = RelevanceLayer(config)
        
        # Apply caching
        logger.info("Applying caching wrapper")
        cached_relevance_layer = cache_relevance_layer(relevance_layer)
        
        # Test data loading
        logger.info("Testing economic data loading")
        try:
            economic_gdf = cached_relevance_layer.load_and_process_economic_data()
            logger.info(f"Successfully loaded economic data: {len(economic_gdf)} regions")
            
            # Show available columns
            logger.info(f"Available columns: {list(economic_gdf.columns)}")
            
            # Show economic data summary
            economic_cols = [col for col in economic_gdf.columns if col.endswith('_value')]
            for col in economic_cols:
                if col in economic_gdf.columns:
                    valid_data = economic_gdf[col].dropna()
                    if len(valid_data) > 0:
                        logger.info(f"{col}: {len(valid_data)} regions, "
                                   f"min={valid_data.min():.2f}, "
                                   f"max={valid_data.max():.2f}, "
                                   f"mean={valid_data.mean():.2f}")
                    else:
                        logger.warning(f"{col}: No valid data found")
                        
        except Exception as e:
            logger.error(f"Error loading economic data: {str(e)}")
            return False
            
        # Test full relevance calculation
        logger.info("Testing relevance layer calculation")
        try:
            relevance_layers = cached_relevance_layer.run_relevance_analysis(
                visualize=True,
                export_individual_tifs=True,
                output_dir=config.output_dir / "relevance_test"
            )
            
            logger.info(f"Successfully calculated {len(relevance_layers)} relevance layers:")
            for layer_name, data in relevance_layers.items():
                valid_data = data[data > 0]
                logger.info(f"  {layer_name}: shape {data.shape}, "
                           f"valid pixels={len(valid_data)}, "
                           f"min={np.min(valid_data) if len(valid_data) > 0 else 0:.3f}, "
                           f"max={np.max(valid_data) if len(valid_data) > 0 else 0:.3f}")
                           
        except Exception as e:
            logger.error(f"Error calculating relevance layers: {str(e)}")
            logger.error("This might be expected if exposition layer data is not available")
            return False
            
        logger.info("Relevance Layer test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import numpy as np
    success = main()
    sys.exit(0 if success else 1) 