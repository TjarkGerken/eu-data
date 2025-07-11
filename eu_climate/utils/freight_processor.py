"""
Shared Freight Processing Logic for EU Climate Risk Assessment
===========================================================

This module provides the main freight processing logic that combines multiple freight data sources
into a unified dataset for risk assessment. It implements a two-stage approach combining NUTS L3
road freight data with Zeevart maritime freight data mapped to individual port geometries.

Key Features:
- Two-stage freight data integration (NUTS L3 + Zeevart ports)
- Unified freight dataset creation with loading and unloading components
- Sophisticated data validation and quality control
- Comprehensive logging and error handling
- Seamless integration with both regular and absolute relevance layers

The module serves as the central coordinator for freight data processing, orchestrating the
various freight components to create a comprehensive and accurate freight dataset.

Architecture:
- SharedFreightProcessor: Main processing class used by multiple layers
- Stage 1: NUTS L3 road freight data (loading + unloading combined)
- Stage 2: Zeevart maritime freight data mapped to port geometries
- Unified dataset creation and validation
- Enhanced dataset integration with maritime data

Data Processing Pipeline:
1. Load and combine NUTS L3 road freight (loading + unloading)
2. Create unified freight dataset from component data
3. Load and process Zeevart maritime freight statistics
4. Map maritime freight to individual port geometries
5. Combine datasets with anti-double-counting measures
6. Validate and return processed freight data

Data Sources:
- NUTS L3 road freight loading data (estat_road_go_na_rl3g_en.csv)
- NUTS L3 road freight unloading data (estat_road_go_na_ru3g_en.csv)
- Zeevart maritime freight statistics (CBS data)
- Port geometry and category mapping data

Usage:
    from eu_climate.utils.freight_processor import SharedFreightProcessor
    
    # Initialize processor
    processor = SharedFreightProcessor(config)
    
    # Load and process all freight data
    nuts_data, enhanced_datasets = processor.load_and_process_freight_data()
    
    # Use processed data for risk assessment
    if enhanced_datasets:
        maritime_data = enhanced_datasets['port_freight']
        road_data = enhanced_datasets['nuts_freight']
"""

import pandas as pd
import geopandas as gpd
import numpy as np
from typing import Dict, Tuple, Optional
from pathlib import Path

from eu_climate.config.config import ProjectConfig
from eu_climate.utils.utils import setup_logging
from eu_climate.utils.freight_components import (
    ZeevartDataLoader, PortFreightMapper, CombinedFreightProcessor
)

logger = setup_logging(__name__)


class SharedFreightProcessor:
    """
    Shared freight processing logic for both regular and absolute relevance layers.
    
    This class provides the central freight processing functionality used by multiple
    layers in the risk assessment system. It implements a sophisticated two-stage
    approach that combines road freight and maritime freight data sources.
    
    Key Features:
        - Two-stage freight data integration approach
        - Unified freight dataset creation from loading and unloading components
        - Zeevart maritime freight integration with port mapping
        - Comprehensive data validation and quality control
        - Flexible data source handling with fallback mechanisms
        
    Processing Stages:
        Stage 1: NUTS L3 Road Freight
            - Combines loading and unloading freight data
            - Creates unified freight dataset
            - Handles multiple data source locations
            - Validates and processes freight volumes
            
        Stage 2: Zeevart Maritime Freight
            - Loads CBS Zeevart maritime freight statistics
            - Maps freight data to individual port geometries
            - Applies area-based allocation algorithms
            - Integrates with road freight data
            
    Data Integration:
        - Prevents double counting through careful data separation
        - Maintains traceability of different freight sources
        - Provides enhanced datasets with maritime data when available
        - Falls back gracefully to NUTS data only if needed
        
    Attributes:
        config: ProjectConfig instance with data paths and settings
        data_dir: Directory containing freight data files
    """
    
    def __init__(self, config: ProjectConfig):
        """
        Initialize SharedFreightProcessor with project configuration.
        
        Args:
            config: ProjectConfig instance containing data paths and processing settings
        """
        self.config = config
        self.data_dir = config.data_dir
        
    def load_and_process_freight_data(self) -> Tuple[pd.DataFrame, Optional[Dict[str, pd.DataFrame]]]:
        """
        Load freight data using the two-stage approach combining road and maritime freight.
        
        This method orchestrates the complete freight data processing pipeline, combining
        NUTS L3 road freight data with Zeevart maritime freight data to create a
        comprehensive freight dataset for risk assessment.
        
        Returns:
            Tuple containing:
            - Primary NUTS freight data (pd.DataFrame): Road freight data for rasterization
            - Enhanced datasets dict (Optional[Dict[str, pd.DataFrame]]): 
              Combined datasets with maritime data, or None if maritime data unavailable
              
        Processing Pipeline:
            Stage 1: NUTS L3 Road Freight
                1. Check for existing unified freight dataset
                2. If not found, create from loading and unloading components
                3. Process and validate unified freight data
                4. Return primary road freight dataset
                
            Stage 2: Zeevart Maritime Freight
                1. Load CBS Zeevart maritime freight statistics
                2. Map freight data to individual port geometries
                3. Apply area-based allocation algorithms
                4. Combine with road freight data
                5. Return enhanced datasets with maritime data
                
        Data Sources:
            - NUTS L3 road freight loading data
            - NUTS L3 road freight unloading data
            - Zeevart maritime freight statistics
            - Port geometry and category mapping data
            
        Error Handling:
            - Graceful fallback to NUTS data only if maritime data unavailable
            - Comprehensive logging of processing steps and issues
            - Validation of data integrity throughout pipeline
            
        Note:
            - Primary return value (NUTS data) is always available for rasterization
            - Enhanced datasets provide additional maritime freight information
            - Method handles missing data sources gracefully
        """
        logger.info("Loading freight data using two-stage approach (NUTS L3 + Zeevart ports)")
        
        # Stage 1: Load and process NUTS L3 road freight data
        nuts_freight_data = self._load_nuts_road_freight()
        
        # Stage 2: Load and process Zeevart maritime freight data
        enhanced_datasets = self._load_and_map_zeevart_freight(nuts_freight_data)
        
        return nuts_freight_data, enhanced_datasets
    
    def _load_nuts_road_freight(self) -> pd.DataFrame:
        """
        Load NUTS L3 road freight data (loading + unloading combined).
        
        This method handles the loading of NUTS L3 road freight data, checking for
        existing unified datasets or creating new ones from component data.
        
        Returns:
            pd.DataFrame: Unified road freight data with combined loading and unloading volumes
            
        Processing Logic:
            1. Check for existing unified freight dataset
            2. If found, load and process existing data
            3. If not found, create unified dataset from components
            4. Validate and return processed data
            
        Note:
            - Prioritizes existing unified datasets for efficiency
            - Falls back to component data processing if needed
            - Provides comprehensive logging of data loading process
        """
        logger.info("Stage 1: Loading NUTS L3 road freight data")
        
        # Check for existing unified freight data first
        unified_freight_path = self.data_dir / "unified_freight_data.csv"
        if unified_freight_path.exists():
            logger.info(f"Loading existing unified freight dataset from {unified_freight_path}")
            nuts_freight_df = pd.read_csv(unified_freight_path)
            return self._process_unified_freight_data(nuts_freight_df)
        else:
            logger.info("Creating unified freight dataset from loading and unloading data")
            return self._create_unified_freight_data()
    
    def _create_unified_freight_data(self) -> pd.DataFrame:
        """
        Create unified freight dataset by combining loading and unloading data.
        
        This method creates a comprehensive freight dataset by combining separate
        loading and unloading freight data sources into a single unified dataset.
        
        Returns:
            pd.DataFrame: Unified freight dataset with combined volumes
            
        Processing Steps:
            1. Locate loading and unloading data files from multiple possible paths
            2. Load both datasets and process them separately
            3. Merge datasets on NUTS codes and regions
            4. Sum loading and unloading values to get total freight
            5. Clean and validate the combined dataset
            6. Save unified dataset for future use
            
        Data Sources:
            - Loading data: estat_road_go_na_rl3g_en.csv
            - Unloading data: estat_road_go_na_ru3g_en.csv
            - Multiple possible directory structures supported
            
        Note:
            - Handles missing data gracefully with outer joins
            - Saves unified dataset to avoid reprocessing
            - Provides comprehensive logging of combination process
        """
        logger.info("Creating unified freight dataset from loading and unloading sources")
        
        # Load freight loading data
        loading_paths = [
            self.data_dir / "L3-estat_road_go_loading" / "estat_road_go_na_rl3g_en.csv",
            self.data_dir / "L3_estat_road_go_loading" / "estat_road_go_na_rl3g_en.csv",
            self.data_dir / "estat_road_go_na_rl3g_en.csv"
        ]
        
        loading_path = None
        for path in loading_paths:
            if path.exists():
                loading_path = path
                break
        
        if loading_path is None:
            raise FileNotFoundError("Freight loading dataset not found in any expected location")
        
        # Load freight unloading data  
        unloading_paths = [
            self.data_dir / "L3-estat_road_go_unloading" / "estat_road_go_na_ru3g_en.csv",
            self.data_dir / "L3_estat_road_go_unloading" / "estat_road_go_na_ru3g_en.csv",
            self.data_dir / "estat_road_go_na_ru3g_en.csv"
        ]
        
        unloading_path = None
        for path in unloading_paths:
            if path.exists():
                unloading_path = path
                break
        
        if unloading_path is None:
            raise FileNotFoundError("Freight unloading dataset not found in any expected location")
        
        logger.info(f"Loading freight loading data from {loading_path}")
        loading_df = pd.read_csv(loading_path)
        loading_processed = self._process_freight_component_data(loading_df)
        
        logger.info(f"Loading freight unloading data from {unloading_path}")
        unloading_df = pd.read_csv(unloading_path)
        unloading_processed = self._process_freight_component_data(unloading_df)
        
        # Merge and sum the freight values
        unified_data = loading_processed.merge(
            unloading_processed, 
            on=['nuts_code', 'region'], 
            how='outer',
            suffixes=('_loading', '_unloading')
        )
        
        # Fill NaN values with 0 for proper summing
        unified_data['freight_value_loading'] = unified_data['freight_value_loading'].fillna(0)
        unified_data['freight_value_unloading'] = unified_data['freight_value_unloading'].fillna(0)
        
        # Sum loading and unloading values
        unified_data['freight_value'] = (
            unified_data['freight_value_loading'] + 
            unified_data['freight_value_unloading']
        )
        
        # Clean up columns and standardize format
        result = unified_data[['nuts_code', 'freight_value', 'region']].copy()
        result['unit'] = 'T'  # Tonnes (standard freight unit)
        
        # Remove rows with zero or NaN total freight
        result = result[result['freight_value'] > 0].dropna()
        
        logger.info(f"Created unified freight data: {len(result)} regions with combined loading + unloading values")
        logger.info(f"Total road freight volume: {result['freight_value'].sum():,.0f} tonnes")
        
        # Save unified dataset for future use
        unified_freight_path = self.data_dir / "unified_freight_data.csv"
        result.to_csv(unified_freight_path, index=False)
        logger.info(f"Saved unified freight dataset to {unified_freight_path}")
        
        return result
    
    def _process_freight_component_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process individual freight component dataset (loading or unloading).
        
        This method processes a single freight component dataset, applying standardized
        filtering, aggregation, and validation procedures.
        
        Args:
            df: Raw freight component DataFrame
            
        Returns:
            pd.DataFrame: Processed freight component data
            
        Processing Steps:
            1. Filter for Netherlands NUTS L3 regions
            2. Select most recent year data
            3. Filter for total freight (all categories)
            4. Aggregate and clean column names
            5. Convert units if needed (thousands of tonnes to tonnes)
            6. Validate numeric values and remove invalid entries
            
        Note:
            - Filters for Netherlands regions (NL prefix, 5 characters)
            - Handles unit conversions automatically
            - Provides detailed logging of processing steps
        """
        # Filter for Netherlands and NUTS L3
        nl_data = df[df['geo'].str.startswith('NL') & df['geo'].str.len().eq(5)]
        
        latest_year = nl_data['TIME_PERIOD'].max()
        latest_data = nl_data[nl_data['TIME_PERIOD'] == latest_year]
        
        total_data = latest_data[latest_data['nst07'] == 'TOTAL']
        
        aggregated = total_data[['geo', 'OBS_VALUE', 'unit', 'Geopolitical entity (reporting)']].copy()
        
        # Clean and standardize
        aggregated.columns = ['nuts_code', 'freight_value', 'unit', 'region']
        aggregated['freight_value'] = pd.to_numeric(aggregated['freight_value'], errors='coerce')
        aggregated = aggregated.dropna()
        
        if not aggregated.empty and aggregated['unit'].iloc[0] == 'THS_T':
            aggregated['freight_value'] = aggregated['freight_value'] * 1000
            aggregated['unit'] = 'T'
            logger.info("Converted NUTS freight data from thousands of tonnes to tonnes")
        
        logger.info(f"Processed freight component data: {len(aggregated)} regions for year {latest_year}")
        if not aggregated.empty:
            logger.info(f"Component freight volume: {aggregated['freight_value'].sum():,.0f} tonnes")
        
        return aggregated
    
    def _process_unified_freight_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process pre-unified freight dataset that was already combined.
        
        This method processes a freight dataset that has already been unified,
        applying validation and cleaning procedures.
        
        Args:
            df: Pre-unified freight DataFrame
            
        Returns:
            pd.DataFrame: Cleaned and validated freight data
            
        Processing Steps:
            1. Ensure numeric values for freight volumes
            2. Remove invalid data (NaN, negative values)
            3. Filter for positive freight values
            4. Validate data integrity
            5. Log processing results
            
        Note:
            - Handles pre-combined datasets efficiently
            - Focuses on validation rather than combination
            - Provides detailed logging of data quality
        """
        logger.info(f"Processing unified freight data: {len(df)} regions")
        
        # Ensure numeric values
        df['freight_value'] = pd.to_numeric(df['freight_value'], errors='coerce')
        
        # Remove invalid data
        processed = df.dropna()
        processed = processed[processed['freight_value'] > 0]
        
        logger.info(f"Processed unified freight data: {len(processed)} regions")
        if not processed.empty:
            logger.info(f"Total road freight volume: {processed['freight_value'].sum():,.0f} tonnes")
        
        return processed
    
    def _load_and_map_zeevart_freight(self, nuts_freight_data: pd.DataFrame) -> Optional[Dict[str, pd.DataFrame]]:
        """
        Stage 2: Load Zeevart data and map to port geometries.
        
        This method implements the second stage of freight processing, loading
        Zeevart maritime freight data and mapping it to individual port geometries.
        
        Args:
            nuts_freight_data: NUTS L3 road freight data from Stage 1
            
        Returns:
            Optional[Dict[str, pd.DataFrame]]: Enhanced datasets with maritime data,
                                             or None if Zeevart data unavailable
                                             
        Processing Steps:
            1. Load CBS Zeevart maritime freight statistics
            2. Map freight data to individual port geometries
            3. Apply area-based allocation algorithms
            4. Combine with NUTS road freight data
            5. Return enhanced datasets with both road and maritime freight
            
        Enhanced Dataset Contents:
            - 'nuts_freight': Road freight data by NUTS L3 regions
            - 'port_freight': Maritime freight data by individual ports
            
        Error Handling:
            - Returns None if Zeevart data files are missing
            - Handles port mapping failures gracefully
            - Provides detailed logging of processing steps and issues
            
        Note:
            - Stage 2 is optional - system works with NUTS data only
            - Enhanced datasets provide additional maritime freight detail
            - Maritime and road freight are kept separate to prevent double counting
        """
        logger.info("Stage 2: Loading and mapping Zeevart maritime freight data to ports")
        
        try:
            # Load and process Zeevart maritime freight data
            zeevart_loader = ZeevartDataLoader(self.config)
            zeevart_data = zeevart_loader.load_zeevart_freight_data()
            
            if zeevart_data.empty:
                logger.warning("No Zeevart data available, using only NUTS road freight")
                return None
            
            # Map freight data to ports
            port_mapper = PortFreightMapper(self.config)
            port_freight_gdf = port_mapper.map_freight_to_ports(zeevart_data)
            
            if port_freight_gdf.empty:
                logger.warning("No port freight mapping successful, using only NUTS road freight")
                return None
            
            # Combine datasets
            freight_processor = CombinedFreightProcessor(self.config)
            combined_datasets = freight_processor.combine_freight_datasets(
                nuts_freight_data, 
                port_freight_gdf
            )
            
            logger.info("Successfully created enhanced freight datasets with maritime data")
            return combined_datasets
            
        except Exception as e:
            logger.warning(f"Could not load Zeevart freight data: {e}")
            logger.info("Continuing with NUTS road freight data only")
            return None 