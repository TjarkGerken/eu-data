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
    """Shared freight processing logic for both regular and absolute relevance layers."""
    
    def __init__(self, config: ProjectConfig):
        self.config = config
        self.data_dir = config.data_dir
        
    def load_and_process_freight_data(self) -> Tuple[pd.DataFrame, Optional[Dict[str, pd.DataFrame]]]:
        """
        Load freight data using the two-stage approach:
        1. NUTS L3 road freight (loading + unloading)
        2. Zeevart maritime freight mapped to ports
        
        Returns:
            Tuple containing:
            - Primary NUTS freight data for rasterization
            - Enhanced datasets dict with port freight data (or None if not available)
        """
        logger.info("Loading freight data using two-stage approach (NUTS L3 + Zeevart ports)")
        
        # Stage 1: Load and process NUTS L3 road freight data
        nuts_freight_data = self._load_nuts_road_freight()
        
        # Stage 2: Load and process Zeevart maritime freight data
        enhanced_datasets = self._load_and_map_zeevart_freight(nuts_freight_data)
        
        return nuts_freight_data, enhanced_datasets
    
    def _load_nuts_road_freight(self) -> pd.DataFrame:
        """Load NUTS L3 road freight data (loading + unloading combined)."""
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
        """Create unified freight dataset by combining loading and unloading data."""
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
        """Process individual freight component dataset (loading or unloading)."""
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
        """Process pre-unified freight dataset that was already combined."""
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
        """Stage 2: Load Zeevart data and map to port geometries."""
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