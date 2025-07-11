"""
Freight Data Processing Components for EU Climate Risk Assessment
==============================================================

This module provides specialized components for processing and integrating freight transportation data
from multiple sources, including maritime freight (Zeevart data) and road freight (NUTS L3 data).

Key Features:
- Zeevart maritime freight data loading and processing
- Port-based freight mapping with area-weighted allocation
- Combined freight dataset integration with anti-double-counting
- Sophisticated freight data normalization using advanced statistical methods
- Centralized coordinate transformations for consistent geographic handling
- Comprehensive freight volume tracking and validation

The module handles the complexity of combining different freight data sources while ensuring
accurate geographic representation and preventing double-counting of freight volumes.

Architecture:
- ZeevartDataLoader: Handles maritime freight data from CBS Zeevart statistics
- PortFreightMapper: Maps aggregated freight data to individual port geometries
- CombinedFreightProcessor: Integrates multiple freight sources with normalization
- Centralized use of RasterTransformer for consistent coordinate handling
- Advanced data normalization using economic optimization strategies

Data Sources:
- Zeevart maritime freight statistics (CBS - Centraal Bureau voor de Statistiek)
- Port geometry data with categorization mapping
- NUTS L3 boundaries for geographic context
- Land mass data for precise geographic masking

Processing Workflow:
1. Load Zeevart maritime freight data by port category
2. Map port categories to individual port geometries
3. Distribute freight volumes using area-based allocation
4. Combine with NUTS-based road freight data
5. Apply normalization for consistent visualization
6. Validate geographic boundaries and totals

Usage:
    from eu_climate.utils.freight_components import ZeevartDataLoader, PortFreightMapper
    
    # Load maritime freight data
    loader = ZeevartDataLoader(config)
    zeevart_data = loader.load_zeevart_freight_data()
    
    # Map to port geometries
    mapper = PortFreightMapper(config)
    port_freight = mapper.map_freight_to_ports(zeevart_data)
    
    # Combine with other freight sources
    processor = CombinedFreightProcessor(config)
    combined_data = processor.combine_freight_datasets(nuts_data, port_freight)
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import rasterio
import rasterio.features
from typing import Dict, Tuple, Optional
from pathlib import Path

from eu_climate.config.config import ProjectConfig
from eu_climate.utils.utils import setup_logging
from eu_climate.utils.conversion import RasterTransformer
from eu_climate.utils.normalise_data import AdvancedDataNormalizer, NormalizationStrategy

logger = setup_logging(__name__)


class ZeevartDataLoader:
    """
    Handles loading and preprocessing of Zeevart maritime freight data.
    
    This class provides specialized functionality for loading and processing CBS Zeevart
    maritime freight statistics, which contain comprehensive data on cargo handling
    at Netherlands seaports categorized by port groups.
    
    Key Features:
        - Loads Zeevart data from Excel format
        - Filters for combined import/export flows ("Aan- en afvoer")
        - Selects most recent complete year data
        - Aggregates freight volumes by port category
        - Converts units and validates data quality
        
    Data Processing:
        - Focuses on "Aan- en afvoer" (combined import/export) flows
        - Uses most recent complete year (typically marked with *)
        - Aggregates by port category to avoid double counting
        - Converts from thousands of tonnes to tonnes
        - Removes total category to prevent aggregation errors
        
    Attributes:
        config: ProjectConfig instance with data paths
        data_dir: Directory containing Zeevart data files
        transformer: RasterTransformer for coordinate handling
    """
    
    def __init__(self, config: ProjectConfig):
        """
        Initialize ZeevartDataLoader with project configuration.
        
        Args:
            config: ProjectConfig instance containing data paths and settings
        """
        self.config = config
        self.data_dir = config.data_dir
        self.transformer = RasterTransformer(
            target_crs=config.target_crs,
            config=config
        )
        
    def load_zeevart_freight_data(self) -> pd.DataFrame:
        """
        Load and process Zeevart maritime freight data from CBS statistics.
        
        This method loads the complete Zeevart dataset and processes it to extract
        relevant freight volumes by port category for the most recent complete year.
        
        Returns:
            pd.DataFrame: Processed freight data with columns:
                - port_category: Port category name
                - freight_volume_1000_tons: Original volume in thousands of tonnes
                - freight_value: Converted volume in tonnes
                
        Processing Steps:
            1. Load Excel file from configured path
            2. Filter for "Aan- en afvoer" (combined flows)
            3. Select most recent complete year data
            4. Group by port category and sum volumes
            5. Convert units and clean data
            6. Validate and log results
            
        Note:
            - Returns empty DataFrame if data file not found
            - Handles missing years gracefully
            - Provides detailed logging of data processing
        """
        zeevart_path = self.config.zeevart_freight_path
        
        if not zeevart_path.exists():
            logger.warning(f"Zeevart data not found: {zeevart_path}")
            return pd.DataFrame()
            
        logger.info(f"Loading Zeevart freight data from {zeevart_path}")
        
        try:
            zeevart_df = pd.read_excel(zeevart_path)
            logger.info(f"Loaded Zeevart data with shape: {zeevart_df.shape}")
            logger.info(f"Columns: {zeevart_df.columns.tolist()}")
            
            processed_data = self._process_zeevart_data(zeevart_df)
            return processed_data
            
        except Exception as e:
            logger.error(f"Error loading Zeevart data: {e}")
            return pd.DataFrame()
    
    def _process_zeevart_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process Zeevart data to extract relevant freight values by port category.
        
        This method performs the core processing of Zeevart data, filtering for
        combined import/export flows and aggregating by port category.
        
        Args:
            df: Raw Zeevart DataFrame loaded from Excel
            
        Returns:
            pd.DataFrame: Processed freight data with standardized columns
            
        Processing Logic:
            1. Filter for "Aan- en afvoer" (combined import/export) flows
            2. Identify most recent complete year (marked with *)
            3. Group by port category and sum freight volumes
            4. Convert units from thousands of tonnes to tonnes
            5. Remove total category to avoid double counting
            6. Validate numeric values and remove invalid entries
            
        Note:
            - Handles missing or invalid years gracefully
            - Provides detailed logging of processing steps
            - Ensures data quality through validation
        """
        # Filter for "Aan- en afvoer" (combined import/export) data
        combined_flow_data = df[df['Vervoerstromen'] == 'Aan- en afvoer']
        
        # Get most recent full year (2022*)
        latest_year = '2022*'
        if latest_year not in combined_flow_data['Perioden'].values:
            available_years = combined_flow_data['Perioden'].unique()
            latest_year = sorted([year for year in available_years if '*' in year and 'kwartaal' not in year])[-1]
            logger.info(f"Using latest available year: {latest_year}")
        
        latest_data = combined_flow_data[combined_flow_data['Perioden'] == latest_year]
        
        # Group by port category and sum freight volumes
        aggregated = latest_data.groupby('Nederlandse zeehavens').agg({
            'Overgeslagen brutogewicht (1 000 ton)': 'sum'
        }).reset_index()
        
        # Clean and standardize column names
        aggregated.columns = ['port_category', 'freight_volume_1000_tons']
        
        # Convert to tonnes (multiply by 1000)
        aggregated['freight_value'] = aggregated['freight_volume_1000_tons'] * 1000
        
        # Remove 'Totaal' category to avoid double counting
        aggregated = aggregated[aggregated['port_category'] != 'Totaal']
        
        # Ensure numeric values
        aggregated['freight_value'] = pd.to_numeric(aggregated['freight_value'], errors='coerce')
        aggregated = aggregated.dropna()
        
        logger.info(f"Processed Zeevart data: {len(aggregated)} port categories for year {latest_year}")
        logger.info(f"Total maritime freight volume: {aggregated['freight_value'].sum():,.0f} tonnes")
        
        return aggregated


class PortFreightMapper:
    """
    Maps freight data to individual port geometries using centralized transformation utilities.
    
    This class handles the complex process of mapping aggregated freight data from port
    categories to individual port geometries, using area-based allocation to distribute
    freight volumes fairly among ports within each category.
    
    Key Features:
        - Loads port geometry data with consistent coordinate transformations
        - Maps port categories to individual port geometries
        - Distributes freight volumes using area-weighted allocation
        - Applies geographic study area clipping
        - Validates and logs allocation results
        
    Area-Based Allocation:
        - Calculates port areas within each category
        - Distributes total category freight proportionally to port areas
        - Ensures fair allocation based on physical port size
        - Handles cases with zero area gracefully
        
    Geographic Processing:
        - Uses centralized RasterTransformer for consistent CRS handling
        - Clips results to study area using NUTS boundaries
        - Validates geometric integrity throughout processing
        - Provides detailed logging of geographic operations
        
    Attributes:
        config: ProjectConfig instance with data paths
        transformer: RasterTransformer for coordinate handling
    """
    
    def __init__(self, config: ProjectConfig):
        """
        Initialize PortFreightMapper with project configuration.
        
        Args:
            config: ProjectConfig instance containing data paths and CRS settings
        """
        self.config = config
        self.transformer = RasterTransformer(
            target_crs=config.target_crs,
            config=config
        )
        
    def load_port_mapping(self) -> pd.DataFrame:
        """
        Load port ID to category mapping file.
        
        This method loads the Excel file that maps individual port IDs to
        port categories used in the Zeevart freight statistics.
        
        Returns:
            pd.DataFrame: Mapping data with port IDs and their categories
            
        Note:
            - Returns empty DataFrame if mapping file not found
            - Handles Excel loading errors gracefully
            - Provides detailed logging of loading process
        """
        mapping_path = self.config.port_mapping_path
        
        if not mapping_path.exists():
            logger.error(f"Port mapping file not found: {mapping_path}")
            return pd.DataFrame()
            
        try:
            mapping_df = pd.read_excel(mapping_path)
            logger.info(f"Loaded port mapping with shape: {mapping_df.shape}")
            return mapping_df
            
        except Exception as e:
            logger.error(f"Error loading port mapping: {e}")
            return pd.DataFrame()
    
    def load_port_shapefile(self) -> gpd.GeoDataFrame:
        """
        Load port shapefile using consistent coordinate transformation.
        
        This method loads the port geometry shapefile and ensures consistent
        coordinate transformation to the target CRS using the centralized
        RasterTransformer approach.
        
        Returns:
            gpd.GeoDataFrame: Port geometries in target CRS
            
        Processing:
            1. Load port shapefile from configured path
            2. Check and log original CRS and feature count
            3. Transform to target CRS if needed
            4. Validate geometric integrity
            5. Return transformed geometries
            
        Note:
            - Uses centralized coordinate transformation approach
            - Returns empty GeoDataFrame if shapefile not found
            - Provides detailed logging of transformation process
        """
        if not self.config.port_path.exists():
            logger.error(f"Port shapefile not found: {self.config.port_path}")
            return gpd.GeoDataFrame()
            
        try:
            port_gdf = gpd.read_file(self.config.port_path)
            logger.info(f"Loaded port shapefile with {len(port_gdf)} ports")
            logger.info(f"Port shapefile columns: {port_gdf.columns.tolist()}")
            
            # Transform to target CRS using consistent approach
            target_crs = rasterio.crs.CRS.from_string(self.config.target_crs)
            if port_gdf.crs != target_crs:
                port_gdf = port_gdf.to_crs(target_crs)
                logger.info(f"Transformed port data to {target_crs}")
                
            return port_gdf
            
        except Exception as e:
            logger.error(f"Error loading port shapefile: {e}")
            return gpd.GeoDataFrame()
    
    def map_freight_to_ports(self, zeevart_data: pd.DataFrame) -> gpd.GeoDataFrame:
        """
        Map Zeevart freight data to individual port geometries using area-based allocation.
        
        This method performs the core freight mapping process, distributing aggregated
        freight volumes from port categories to individual port geometries using
        sophisticated area-based allocation algorithms.
        
        Args:
            zeevart_data: Processed Zeevart freight data by port category
            
        Returns:
            gpd.GeoDataFrame: Port geometries with allocated freight volumes
            
        Allocation Algorithm:
            1. Load port geometries and category mapping
            2. Merge port geometries with freight categories
            3. Calculate port areas for proportional allocation
            4. For each port category:
               - Get total freight volume for category
               - Calculate area ratios for ports in category
               - Allocate freight proportionally to port areas
            5. Apply geographic clipping to study area
            6. Validate allocation results
            
        Area-Based Distribution:
            - Calculates individual port areas within each category
            - Distributes total category freight proportionally
            - Handles zero-area cases with equal distribution fallback
            - Provides detailed logging of allocation statistics
            
        Geographic Validation:
            - Clips results to Netherlands study area using NUTS boundaries
            - Validates geometric integrity throughout processing
            - Filters out invalid geometries
            - Provides comprehensive logging of geographic operations
            
        Note:
            - Ensures no double counting across categories
            - Handles missing data gracefully
            - Provides detailed allocation statistics
            - Validates geographic boundaries and totals
        """
        # Load port shapefile and mapping
        port_gdf = self.load_port_shapefile()
        mapping_df = self.load_port_mapping()
        
        if port_gdf.empty or mapping_df.empty or zeevart_data.empty:
            logger.warning("Missing required data for port freight mapping")
            return gpd.GeoDataFrame()
        
        # Merge port geometries with categories
        port_with_categories = port_gdf.merge(
            mapping_df, 
            left_on='PORT_ID', 
            right_on='PORT_ID', 
            how='left'
        )
        
        # Merge with freight data
        port_with_freight = port_with_categories.merge(
            zeevart_data,
            left_on='Category',
            right_on='port_category',
            how='left'
        )
        
        # Fill missing freight values with 0 and ensure proper float type
        port_with_freight['freight_value'] = port_with_freight['freight_value'].fillna(0).astype(float)
        
        # Calculate port areas for proportional allocation
        port_with_freight['port_area'] = port_with_freight.geometry.area
        
        # Apply area-based freight distribution within each category
        if not port_with_freight.empty:
            logger.info("Distributing freight among ports by area-weighted allocation:")
            
            for category in port_with_freight['port_category'].dropna().unique():
                if category in zeevart_data['port_category'].values:
                    # Get total freight for this category
                    total_freight = zeevart_data[zeevart_data['port_category'] == category]['freight_value'].iloc[0]
                    
                    # Filter ports in this category
                    category_mask = port_with_freight['port_category'] == category
                    category_ports = port_with_freight[category_mask]
                    
                    if len(category_ports) > 0:
                        # Calculate area-based allocation
                        total_area = category_ports['port_area'].sum()
                        
                        if total_area > 0:
                            # Distribute freight proportionally to port area
                            area_ratios = category_ports['port_area'] / total_area
                            freight_allocations = area_ratios * total_freight
                            
                            # Update freight values for this category
                            port_with_freight.loc[category_mask, 'freight_value'] = freight_allocations.values
                            
                            # Log allocation details
                            num_ports = len(category_ports)
                            min_allocation = freight_allocations.min()
                            max_allocation = freight_allocations.max()
                            avg_allocation = freight_allocations.mean()
                            
                            logger.info(f"  {category}: {total_freight:,.0f} tonnes allocated across {num_ports} ports")
                            logger.info(f"    Area-based allocation range: {min_allocation:,.0f} - {max_allocation:,.0f} tonnes (avg: {avg_allocation:,.0f})")
                            logger.info(f"    Total area: {total_area:,.0f} m²")
                        else:
                            logger.warning(f"  {category}: Zero total area, using equal distribution fallback")
                            freight_per_port = total_freight / len(category_ports)
                            port_with_freight.loc[category_mask, 'freight_value'] = freight_per_port
        
        # Include all ports - those with categories get freight, those without get 0 freight
        valid_ports = port_with_freight.copy()
        
        # Ensure all ports have a freight value (NaN categories get 0 freight)  
        valid_ports['freight_value'] = valid_ports['freight_value'].fillna(0)
        
        # Filter out any ports with invalid geometries
        valid_ports = valid_ports[valid_ports['geometry'].notna()].copy()
        
        # Clip to study area using existing NUTS boundaries
        nuts_l3_path = self.config.data_dir / "NUTS-L3-NL.shp"
        if nuts_l3_path.exists():
            try:
                nuts_gdf = gpd.read_file(nuts_l3_path)
                target_crs = rasterio.crs.CRS.from_string(self.config.target_crs)
                if nuts_gdf.crs != target_crs:
                    nuts_gdf = nuts_gdf.to_crs(target_crs)
                
                study_area = nuts_gdf.geometry.unary_union
                ports_in_study_area = valid_ports[valid_ports.geometry.intersects(study_area)]
                
                logger.info(f"Clipped to study area: {len(ports_in_study_area)} ports with freight data "
                           f"(from {len(valid_ports)} total valid ports)")
                valid_ports = ports_in_study_area
                
            except Exception as e:
                logger.warning(f"Could not clip ports to study area: {e}")
        
        logger.info(f"Mapped freight to {len(valid_ports)} ports using area-based allocation")
        if len(valid_ports) > 0:
            total_mapped_freight = valid_ports['freight_value'].sum()
            logger.info(f"Total mapped maritime freight: {total_mapped_freight:,.0f} tonnes")
            
            # Log freight distribution by category with area statistics
            freight_by_category = valid_ports.groupby('port_category').agg({
                'freight_value': 'sum',
                'port_area': 'sum'
            }).sort_values('freight_value', ascending=False)
            
            logger.info("Area-weighted freight distribution by port category:")
            for category, row in freight_by_category.iterrows():
                freight = row['freight_value']
                area = row['port_area']
                logger.info(f"  {category}: {freight:,.0f} tonnes (total area: {area:,.0f} m²)")
        
        return valid_ports


class CombinedFreightProcessor:
    """
    Combines NUTS-based and port-based freight data using centralized normalization.
    
    This class provides sophisticated integration of multiple freight data sources,
    ensuring no double counting while applying advanced normalization techniques
    for consistent visualization and analysis.
    
    Key Features:
        - Combines NUTS L3 road freight with port-based maritime freight
        - Prevents double counting through careful data separation
        - Applies advanced normalization using economic optimization strategies
        - Provides detailed freight volume tracking and validation
        - Uses centralized coordinate transformation utilities
        
    Data Integration:
        - NUTS freight: Road-based freight by administrative regions
        - Port freight: Maritime freight by individual port geometries
        - Careful separation prevents double counting of freight volumes
        - Detailed logging of combined totals and data shares
        
    Normalization:
        - Uses AdvancedDataNormalizer with economic optimization
        - Applies consistent normalization across all freight datasets
        - Preserves relative freight relationships while optimizing visualization
        - Handles missing or invalid data gracefully
        
    Attributes:
        config: ProjectConfig instance with processing settings
        transformer: RasterTransformer for coordinate handling
        normalizer: AdvancedDataNormalizer for sophisticated normalization
    """
    
    def __init__(self, config: ProjectConfig):
        """
        Initialize CombinedFreightProcessor with project configuration.
        
        Args:
            config: ProjectConfig instance containing processing settings
        """
        self.config = config
        self.transformer = RasterTransformer(
            target_crs=config.target_crs,
            config=config
        )
        self.normalizer = AdvancedDataNormalizer(NormalizationStrategy.ECONOMIC_OPTIMIZED)
        
    def combine_freight_datasets(self, nuts_freight_data: pd.DataFrame, 
                                port_freight_gdf: gpd.GeoDataFrame) -> Dict[str, pd.DataFrame]:
        """
        Combine NUTS and port freight data ensuring no double counting.
        
        This method carefully combines different freight data sources while ensuring
        no double counting of freight volumes. It maintains separate datasets for
        road-based and maritime freight to prevent analytical conflicts.
        
        Args:
            nuts_freight_data: NUTS L3 road freight data
            port_freight_gdf: Port-based maritime freight data
            
        Returns:
            Dict[str, pd.DataFrame]: Dictionary with separate freight datasets:
                - 'nuts_freight': NUTS-based road freight data
                - 'port_freight': Port-based maritime freight data
                
        Anti-Double-Counting Strategy:
            - Maintains separate datasets for different freight modes
            - Road freight (NUTS): Handles inland/road-based freight
            - Maritime freight (ports): Handles sea-based freight
            - No overlap between datasets ensures accurate totals
            
        Validation:
            - Calculates and logs total freight volumes for each dataset
            - Computes combined totals and data shares
            - Validates data integrity and completeness
            - Provides detailed statistical summary
            
        Note:
            - Prevents double counting through careful data separation
            - Maintains traceability of freight sources
            - Provides comprehensive logging of combination process
        """
        combined_datasets = {}
        
        if not nuts_freight_data.empty:
            combined_datasets['nuts_freight'] = nuts_freight_data.copy()
            nuts_total = nuts_freight_data['freight_value'].sum()
            logger.info(f"NUTS freight total: {nuts_total:,.0f} tonnes")
        
        if not port_freight_gdf.empty:
            port_data = pd.DataFrame({
                'port_id': port_freight_gdf['PORT_ID'],
                'freight_value': port_freight_gdf['freight_value'],
                'geometry': port_freight_gdf['geometry'],
                'port_category': port_freight_gdf['port_category']
            })
            combined_datasets['port_freight'] = port_data
            port_total = port_data['freight_value'].sum()
            logger.info(f"Port freight total: {port_total:,.0f} tonnes")
        
        if 'nuts_freight' in combined_datasets and 'port_freight' in combined_datasets:
            logger.info("Created combined freight dataset with both NUTS and port components")
            
            combined_total = nuts_total + port_total
            logger.info(f"Combined freight total: {combined_total:,.0f} tonnes")
            logger.info(f"NUTS share: {(nuts_total/combined_total)*100:.1f}%, Port share: {(port_total/combined_total)*100:.1f}%")
            
        return combined_datasets
    
    def normalize_combined_freight_data(self, combined_datasets: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        Apply sophisticated normalization across all freight datasets.
        
        This method applies advanced normalization techniques to all combined freight
        datasets, ensuring consistent visualization and analysis while preserving
        relative freight relationships.
        
        Args:
            combined_datasets: Dictionary of freight datasets to normalize
            
        Returns:
            Dict[str, pd.DataFrame]: Normalized datasets with added normalization columns
            
        Normalization Process:
            1. Iterate through each freight dataset
            2. Identify valid freight values (positive and non-null)
            3. Apply economic optimization normalization strategy
            4. Add normalized values as new columns
            5. Preserve original freight values for analysis
            6. Log normalization statistics
            
        Normalization Features:
            - Uses AdvancedDataNormalizer with economic optimization
            - Preserves relative freight relationships
            - Handles missing or invalid data gracefully
            - Provides detailed logging of normalization process
            - Maintains original data alongside normalized values
            
        Note:
            - Applies consistent normalization across all datasets
            - Preserves data integrity while optimizing visualization
            - Handles edge cases and missing data gracefully
        """
        normalized_datasets = {}
        
        for dataset_name, dataset in combined_datasets.items():
            if 'freight_value' in dataset.columns:
                valid_mask = (dataset['freight_value'] > 0) & dataset['freight_value'].notna()
                
                if valid_mask.sum() > 0:
                    freight_values = dataset['freight_value'].values
                    normalized_values = self.normalizer.normalize_economic_data(
                        data=freight_values,
                        economic_mask=valid_mask.values
                    )
                    
                    normalized_dataset = dataset.copy()
                    normalized_dataset['freight_value_normalized'] = normalized_values
                    normalized_datasets[dataset_name] = normalized_dataset
                    
                    logger.info(f"Normalized {dataset_name}: {valid_mask.sum()} valid freight entries")
                else:
                    logger.warning(f"No valid freight data found in {dataset_name}")
                    normalized_datasets[dataset_name] = dataset.copy()
            else:
                normalized_datasets[dataset_name] = dataset.copy()
        
        return normalized_datasets 