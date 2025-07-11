import rasterio
import rasterio.features
import rasterio.warp
import geopandas as gpd
import pandas as pd
from typing import Tuple, Dict, List
import numpy as np
from pathlib import Path
import os

from eu_climate.config.config import ProjectConfig
from eu_climate.utils.utils import setup_logging
from eu_climate.utils.conversion import RasterTransformer
from eu_climate.utils.visualization import LayerVisualizer
from eu_climate.utils.normalise_data import AdvancedDataNormalizer, NormalizationStrategy
from eu_climate.utils.freight_processor import SharedFreightProcessor
from eu_climate.risk_layers.exposition_layer import ExpositionLayer

logger = setup_logging(__name__)


class EconomicDataLoader:
    """
    Economic Data Loader for Relative Relevance Analysis
    =================================================
    
    The EconomicDataLoader class provides functionality for loading and preprocessing
    economic datasets used in relative relevance analysis. Unlike absolute analysis,
    relative analysis focuses on proportional relationships and normalized values
    for comparative assessment across regions.
    
    Key Features:
    - Comprehensive economic dataset loading (GDP, freight, HRST)
    - Standardized data preprocessing and validation
    - Integration with shared freight processor for enhanced logistics data
    - Flexible data format handling with error recovery
    - Quality assurance and data validation throughout the process
    
    Supported Economic Indicators:
    1. GDP (Gross Domestic Product): Regional economic output for relative comparison
    2. Freight: Maritime and logistics activities for transport assessment
    3. HRST (Human Resources in Science and Technology): Innovation capacity indicator
    
    Data Processing Pipeline:
    1. Load raw economic datasets from standardized Eurostat sources
    2. Apply dataset-specific preprocessing and filtering
    3. Standardize column names and data formats
    4. Validate data quality and handle missing values
    5. Integrate enhanced freight data from shared processor
    6. Provide comprehensive logging and error reporting
    
    The loader ensures data consistency and quality for downstream relative
    relevance analysis while maintaining flexibility for different data sources.
    """
    
    def __init__(self, config: ProjectConfig):
        """
        Initialize the Economic Data Loader for relative analysis.
        
        Args:
            config: Project configuration with data paths and processing parameters
        """
        self.config = config
        self.data_dir = config.data_dir
        self.freight_processor = SharedFreightProcessor(config)
        
    def load_economic_datasets(self) -> Dict[str, pd.DataFrame]:
        """
        Load all economic datasets and standardize format for relative analysis.
        
        This method orchestrates the loading of all economic datasets required for
        relative relevance analysis, applying standardized preprocessing and
        validation to ensure data quality and consistency.
        
        Returns:
            Dictionary mapping dataset names to processed DataFrames
        """
        datasets = {}
        
        # Load GDP dataset
        gdp_path = self.data_dir / "L3-estat_gdp.csv" / "estat_nama_10r_3gdp_en.csv"
        if gdp_path.exists():
            logger.info(f"Loading GDP dataset from {gdp_path}")
            gdp_df = pd.read_csv(gdp_path)
            datasets['gdp'] = self._process_gdp_data(gdp_df)
        else:
            logger.error(f"GDP dataset not found: {gdp_path}")
            
        # Load freight data using shared processor
        freight_data = self._load_maritime_freight_data()
        if not freight_data.empty:
            datasets['freight'] = freight_data
            
        # Load HRST dataset
        hrst_path = self.data_dir / getattr(self.config, 'hrst_file_path', 'L2_estat_hrst_st_rcat_filtered_en/estat_hrst_st_rcat_filtered_en.csv')
        if hrst_path.exists():
            logger.info(f"Loading HRST dataset from {hrst_path}")
            hrst_df = pd.read_csv(hrst_path)
            datasets['hrst'] = self._process_hrst_data(hrst_df)
        else:
            logger.error(f"HRST dataset not found: {hrst_path}")
            
        return datasets
    
    def _process_gdp_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process GDP dataset to extract NUTS L3 values for relative analysis.
        
        This method filters and processes GDP data to extract standardized values
        for Netherlands NUTS L3 regions, suitable for relative comparison and
        normalization in relevance analysis.
        
        Args:
            df: Raw GDP DataFrame from Eurostat
            
        Returns:
            Processed DataFrame with standardized GDP values
        """
        # Filter for Netherlands (NL) and NUTS L3 regions
        nl_data = df[df['geo'].str.startswith('NL') & df['geo'].str.len().eq(5)]
        
        # Filter for million EUR values
        nl_data_mio = nl_data[nl_data["unit"].str.contains("MIO_EUR")].reset_index(drop=True)

        # Get latest available year
        latest_year = nl_data_mio['TIME_PERIOD'].max()
        latest_data = nl_data_mio[nl_data_mio['TIME_PERIOD'] == latest_year]
        
        # Clean and standardize column names
        processed = latest_data[['geo', 'OBS_VALUE', 'unit', 'Geopolitical entity (reporting)']].copy()
        processed.columns = ['nuts_code', 'gdp_value', 'unit', 'region']
        processed['gdp_value'] = pd.to_numeric(processed['gdp_value'], errors='coerce')

        # Handle missing values with logging
        if processed.isna().any().any():
            logger.warning("NaN values detected in GDP data")
            len_before = len(processed)
            processed = processed.dropna()
            len_after = len(processed)
            logger.warning(f"Dropped {len_before - len_after} NaN values in GDP data")
        
        logger.info(f"Processed GDP data: {len(processed)} regions for year {latest_year}")
        return processed
    
    def _process_freight_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process freight dataset to extract NUTS L3 values for relative analysis.
        
        This method processes freight data to extract standardized values for
        Netherlands NUTS L3 regions, focusing on total freight volumes for
        comparative analysis.
        
        Args:
            df: Raw freight DataFrame from Eurostat
            
        Returns:
            Processed DataFrame with standardized freight values
        """
        # Filter for Netherlands and NUTS L3
        nl_data = df[df['geo'].str.startswith('NL') & df['geo'].str.len().eq(5)]
        
        # Get latest available year
        latest_year = nl_data['TIME_PERIOD'].max()
        latest_data = nl_data[nl_data['TIME_PERIOD'] == latest_year]
        
        # Filter for total freight data
        total_data = latest_data[latest_data['nst07'] == 'TOTAL']
        
        # Clean and standardize
        aggregated = total_data[['geo', 'OBS_VALUE', 'unit', 'Geopolitical entity (reporting)']].copy()
        aggregated.columns = ['nuts_code', 'freight_value', 'unit', 'region']
        aggregated['freight_value'] = pd.to_numeric(aggregated['freight_value'], errors='coerce')
        aggregated = aggregated.dropna()
        
        # Convert units if necessary
        if not aggregated.empty and aggregated['unit'].iloc[0] == 'THS_T':
            aggregated['freight_value'] = aggregated['freight_value'] * 1000
            aggregated['unit'] = 'T'
            logger.info("Converted NUTS freight data from thousands of tonnes to tonnes")
        
        logger.info(f"Processed freight data: {len(aggregated)} regions for year {latest_year}")
        logger.info(f"Total NUTS freight volume: {aggregated['freight_value'].sum():,.0f} tonnes")
        return aggregated
    
    def _process_hrst_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process HRST dataset to extract NUTS L2 values for relative analysis.
        
        This method processes Human Resources in Science and Technology data,
        extracting employment figures for high-skilled sectors that represent
        regional innovation capacity and competitiveness.
        
        Args:
            df: Raw HRST DataFrame from Eurostat
            
        Returns:
            Processed DataFrame with standardized HRST values
        """
        # Filter for Netherlands and NUTS L2 (4 character codes starting with NL)
        nl_data = df[df['geo'].str.startswith('NL') & df['geo'].str.len().eq(4)]
        
        # Get latest available year
        latest_year = nl_data['TIME_PERIOD'].max()
        latest_data = nl_data[nl_data['TIME_PERIOD'] == latest_year]
        
        # Clean and standardize column names
        processed = latest_data[['geo', 'OBS_VALUE', 'unit', 'Geopolitical entity (reporting)']].copy()
        processed.columns = ['nuts_code', 'hrst_value', 'unit', 'region']
        processed['hrst_value'] = pd.to_numeric(processed['hrst_value'], errors='coerce')
        
        # Handle missing values with logging
        if processed.isna().any().any():
            logger.warning("NaN values detected in HRST data")
            len_before = len(processed)
            processed = processed.dropna()
            len_after = len(processed)
            logger.warning(f"Dropped {len_before - len_after} NaN values in HRST data")
        
        logger.info(f"Processed HRST data: {len(processed)} regions for year {latest_year}")
        return processed
    
    def _load_maritime_freight_data(self) -> pd.DataFrame:
        """
        Load enhanced freight data using shared processor for relative analysis.
        
        This method leverages the shared freight processor to load comprehensive
        freight data including both NUTS-level statistics and enhanced datasets
        for improved spatial representation in relative analysis.
        
        Returns:
            Processed DataFrame with freight data ready for relative analysis
        """
        logger.info("Loading freight data using shared processor")
        
        try:
            nuts_freight_data, enhanced_datasets = self.freight_processor.load_and_process_freight_data()
            
            # Store enhanced datasets for later use in distribution
            if enhanced_datasets:
                self.enhanced_freight_datasets = enhanced_datasets
                logger.info("Enhanced freight datasets available for distribution")
            
            if nuts_freight_data.empty:
                logger.warning("No NUTS freight data available from shared processor")
                return pd.DataFrame()
            
            return nuts_freight_data
            
        except Exception as e:
            logger.error(f"Error loading freight data with shared processor: {e}")
            return pd.DataFrame()


class NUTSDataMapper:
    """
    NUTS Data Mapper for Geographic Integration
    =========================================
    
    The NUTSDataMapper class provides comprehensive functionality for mapping
    economic datasets to NUTS (Nomenclature of Territorial Units for Statistics)
    administrative boundaries at different hierarchical levels. This enables
    spatially-aware economic analysis by integrating statistical data with
    geographic boundaries.
    
    Key Features:
    - Multi-level NUTS boundary loading and processing
    - Automated coordinate system transformation
    - Flexible economic data integration at appropriate NUTS levels
    - NUTS code mapping and harmonization between different vintages
    - Comprehensive validation and error handling
    
    NUTS Levels Supported:
    - NUTS Level 0: Countries (NL - Netherlands)
    - NUTS Level 1: Major regions (4 regions in Netherlands)
    - NUTS Level 2: Provinces (12 provinces in Netherlands)
    - NUTS Level 3: Municipalities/counties (40+ regions in Netherlands)
    
    Integration Process:
    1. Load NUTS shapefiles at appropriate levels
    2. Transform to target coordinate reference system
    3. Map economic datasets to matching NUTS levels
    4. Handle NUTS code harmonization between different vintages
    5. Validate spatial and attribute data integrity
    6. Create spatially-enabled economic datasets
    
    The mapper ensures consistent spatial representation across all economic
    indicators while maintaining data quality and spatial accuracy.
    """
    
    def __init__(self, config: ProjectConfig):
        """
        Initialize the NUTS Data Mapper with project configuration.
        
        Args:
            config: Project configuration containing paths and spatial parameters
        """
        self.config = config
        
    def load_nuts_shapefile(self, nuts_level: str) -> gpd.GeoDataFrame:
        """
        Load and prepare NUTS shapefile for specified administrative level.
        
        This method loads NUTS boundary data for a specific administrative level,
        transforms it to the target coordinate system, and prepares it for
        integration with economic datasets.
        
        Args:
            nuts_level: NUTS level identifier ('l0', 'l1', 'l2', 'l3')
            
        Returns:
            GeoDataFrame with NUTS boundaries in target coordinate system
        """
        # Get NUTS file path from configuration
        nuts_filename = getattr(self.config, f'nuts_{nuts_level}_file_path', None)
        if nuts_filename is None:
            raise ValueError(f"NUTS {nuts_level.upper()} file path not found in config")
            
        nuts_path = self.config.data_dir / nuts_filename
        logger.info(f"Loading NUTS {nuts_level.upper()} shapefile from {nuts_path}")
        
        # Load shapefile
        nuts_gdf = gpd.read_file(nuts_path)
        
        # Transform to target CRS if necessary
        target_crs = rasterio.crs.CRS.from_string(self.config.target_crs)
        if nuts_gdf.crs != target_crs:
            nuts_gdf = nuts_gdf.to_crs(target_crs)
            logger.info(f"Transformed NUTS shapefile to {target_crs}")
            
        logger.info(f"Loaded {len(nuts_gdf)} NUTS {nuts_level.upper()} regions")
        return nuts_gdf
    
    def join_economic_data(self, nuts_gdfs: Dict[str, gpd.GeoDataFrame], 
                          economic_data: Dict[str, pd.DataFrame]) -> Dict[str, gpd.GeoDataFrame]:
        """
        Join economic datasets with NUTS geometries at appropriate administrative levels.
        
        This method performs spatial integration of economic data with NUTS boundaries,
        ensuring that each economic indicator is joined with the appropriate NUTS level
        and handling code harmonization between different data vintages.
        
        Args:
            nuts_gdfs: Dictionary mapping NUTS levels to GeoDataFrames
            economic_data: Dictionary mapping dataset names to economic DataFrames
            
        Returns:
            Dictionary mapping dataset names to spatially-enabled GeoDataFrames
        """
        result_gdfs = {}
        
        # Load NUTS code mapping for harmonization if available
        loading_nuts_mapping_path = os.path.join(self.config.data_dir, "Mapping_NL_NUTS_2021_2024.xlsx")
        mapping_df = pd.read_excel(loading_nuts_mapping_path) if os.path.exists(loading_nuts_mapping_path) else None

        # Process each dataset with its corresponding NUTS level
        for dataset_name, df in economic_data.items():
            # Get dataset configuration for NUTS level mapping
            dataset_config = self.config.economic_datasets.get(dataset_name, {})
            nuts_level = dataset_config.get('nuts_level', 'l3')
            
            # Validate NUTS level availability
            if nuts_level not in nuts_gdfs:
                logger.warning(f"NUTS level {nuts_level} not available for dataset {dataset_name}")
                continue
                
            nuts_gdf = nuts_gdfs[nuts_level].copy()
            logger.info(f"Joining {dataset_name} data with NUTS {nuts_level.upper()}")
            
            # Determine NUTS code column in shapefile
            nuts_code_col = None
            for col in ['NUTS_ID', 'nuts_id', 'geo', 'GEOCODE']:
                if col in nuts_gdf.columns:
                    nuts_code_col = col
                    break
            
            if nuts_code_col is None:
                raise ValueError(f"Could not find NUTS code column in {nuts_level} shapefile")
                
            logger.info(f"Using NUTS code column: {nuts_code_col}")
            
            # Create a copy for joining and standardize the value column name
            economic_df = df.copy()
            
            # Handle different dataset value columns
            if dataset_name == 'gdp':
                value_col = 'gdp_value'
            elif dataset_name == 'freight':
                value_col = 'freight_value'
            elif dataset_name == 'hrst':
                value_col = 'hrst_value'
            else:
                # Generic fallback
                value_col = f'{dataset_name}_value'
            
            # Ensure value column exists
            if value_col not in economic_df.columns:
                logger.warning(f"Value column '{value_col}' not found in {dataset_name} data")
                continue
            
            # Apply NUTS code mapping if available and needed
            if mapping_df is not None and not mapping_df.empty:
                logger.info(f"Applying NUTS code mapping for {dataset_name}")
                
                # Get appropriate mapping columns based on NUTS level
                if nuts_level == 'l3':
                    old_col = 'NUTS_ID_2021'
                    new_col = 'NUTS_ID_2024'
                elif nuts_level == 'l2':
                    old_col = 'NUTS_ID_2021_L2'
                    new_col = 'NUTS_ID_2024_L2'
                else:
                    old_col = new_col = None
                
                # Apply mapping if columns exist
                if old_col and new_col and old_col in mapping_df.columns and new_col in mapping_df.columns:
                    mapping_dict = dict(zip(mapping_df[old_col], mapping_df[new_col]))
                    economic_df['nuts_code'] = economic_df['nuts_code'].map(mapping_dict).fillna(economic_df['nuts_code'])
                    logger.info(f"Applied NUTS code mapping: {len(mapping_dict)} mappings")
            
            # Perform the join
            joined_gdf = nuts_gdf.merge(
                economic_df,
                left_on=nuts_code_col,
                right_on='nuts_code',
                how='left'
            )
            
            # Validate join results
            total_regions = len(nuts_gdf)
            joined_regions = len(joined_gdf[joined_gdf[value_col].notna()])
            missing_regions = total_regions - joined_regions
            
            logger.info(f"Join results for {dataset_name}:")
            logger.info(f"  Total NUTS regions: {total_regions}")
            logger.info(f"  Regions with data: {joined_regions}")
            logger.info(f"  Missing data: {missing_regions}")
            
            if missing_regions > 0:
                logger.warning(f"Some NUTS regions missing {dataset_name} data - check NUTS code matching")
                
                # Log missing regions for debugging
                missing_nuts_codes = joined_gdf[joined_gdf[value_col].isna()][nuts_code_col].tolist()
                logger.debug(f"Missing NUTS codes for {dataset_name}: {missing_nuts_codes}")
            
            # Store successful join
            if joined_regions > 0:
                result_gdfs[dataset_name] = joined_gdf
                logger.info(f"Successfully joined {dataset_name} data with {joined_regions} regions")
            else:
                logger.error(f"No regions joined for {dataset_name} - check data compatibility")
        
        return result_gdfs


class EconomicDistributor:
    """Handles spatial distribution of economic values using exposition layer."""
    
    def __init__(self, config: ProjectConfig, transformer: RasterTransformer):
        self.config = config
        self.transformer = transformer
        
    def rasterize_nuts_regions(self, nuts_gdf: gpd.GeoDataFrame, 
                              exposition_meta: dict,
                              economic_variable: str) -> Tuple[np.ndarray, dict]:
        """Rasterize NUTS regions with economic values using exposition layer metadata."""
        logger.info(f"Rasterizing NUTS regions for {economic_variable}")
        
        # Use exposition layer's transform and dimensions to ensure perfect alignment
        transform = exposition_meta['transform']
        height = exposition_meta['height']
        width = exposition_meta['width']
        
        # Prepare data for rasterization
        value_column = f"{economic_variable}_value"
        if value_column not in nuts_gdf.columns:
            raise ValueError(f"Economic variable {value_column} not found in data")
            
        # Create geometry-value pairs for rasterization
        shapes = [(geom, value) for geom, value in zip(
            nuts_gdf.geometry, nuts_gdf[value_column]
        ) if not np.isnan(value)]
        
        # Rasterize using exact exposition layer dimensions and transform
        raster = rasterio.features.rasterize(
            shapes,
            out_shape=(height, width),
            transform=transform,
            fill=0,
            dtype=np.float32
        )
        
        # Create metadata (copy from exposition layer)
        meta = exposition_meta.copy()
        meta['dtype'] = 'float32'
        
        logger.info(f"Rasterized {economic_variable}: shape {raster.shape}, "
                   f"min={np.nanmin(raster)}, max={np.nanmax(raster)}")
        
        return raster, meta
    
    def distribute_with_exposition(self, economic_raster: np.ndarray, 
                                 exposition_layer: np.ndarray,
                                 enhanced_freight_datasets: dict = None,
                                 reference_meta: dict = None) -> np.ndarray:
        """
        Distribute economic values using exposition layer as weights with enhanced freight integration.
        Uses centralized approaches for validation, normalization, and port freight handling.
        """
        logger.info("Distributing economic values using exposition layer with enhanced freight integration")
        
        # Store reference metadata for port rasterization
        if reference_meta:
            self._reference_meta = reference_meta
        
        if not self.transformer.validate_alignment(
            economic_raster, None, exposition_layer, None
        ):
            logger.warning("Raster alignment validation failed")
        
        distributed = self._apply_nuts_distribution(economic_raster, exposition_layer)
        
        if enhanced_freight_datasets and 'port_freight' in enhanced_freight_datasets:
            logger.info("Applying enhanced port freight data using centralized approaches")
            distributed = self._apply_port_freight_enhancement(
                distributed, enhanced_freight_datasets['port_freight']
            )
        
        # Apply final normalization using centralized approach
        normalizer = AdvancedDataNormalizer(NormalizationStrategy.ECONOMIC_OPTIMIZED)
        final_valid_mask = ~np.isnan(distributed) & (distributed > 0)
        
        if np.any(final_valid_mask):
            distributed = normalizer.normalize_economic_data(
                distributed, final_valid_mask
            )
        
        logger.info(f"Final distributed economic values: min={np.nanmin(distributed)}, "
                   f"max={np.nanmax(distributed)}, mean={np.nanmean(distributed)}")
        
        return distributed
    
    def _apply_nuts_distribution(self, economic_raster: np.ndarray, 
                               exposition_layer: np.ndarray) -> np.ndarray:
        """Apply standard NUTS-based economic distribution."""
        # Create distributed values
        distributed = np.zeros_like(economic_raster, dtype=np.float32)
        
        # Process each NUTS region separately
        unique_values = np.unique(economic_raster)
        unique_values = unique_values[unique_values > 0]  # Exclude zero/background
        
        for region_value in unique_values:
            # Create mask for this region
            region_mask = economic_raster == region_value
            
            # Get exposition weights for this region
            region_exposition = exposition_layer * region_mask
            
            # Calculate total exposition weight in region
            total_exposition = np.sum(region_exposition)
            
            if total_exposition > 0:
                # Distribute regional value proportionally
                distributed += (region_exposition / total_exposition) * region_value
            else:
                # Fallback: uniform distribution
                region_cells = np.sum(region_mask)
                if region_cells > 0:
                    distributed[region_mask] = region_value / region_cells
        
        return distributed
    def _apply_port_freight_enhancement(self, distributed_base: np.ndarray,
                                       port_freight_data: pd.DataFrame) -> np.ndarray:
        """Apply port freight enhancement using exact port locations (no exposition distribution)."""
        if port_freight_data.empty:
            logger.info("No port freight data available for enhancement")
            return distributed_base

        logger.info(f"Enhancing with {len(port_freight_data)} port freight entries")
        
        # Create port freight raster using centralized transformer
        port_raster = self._rasterize_port_freight(port_freight_data, distributed_base.shape)
        
        # Start with base distribution (NUTS data distributed over exposition)
        enhanced_distributed = distributed_base.copy()
        
        # Identify port pixels with freight data
        port_mask = (port_raster > 0) & (~np.isnan(port_raster))
        
        if np.any(port_mask):
            # ADD port freight values to existing NUTS distribution
            # This combines NUTS freight (distributed over exposition) with precise port freight
            enhanced_distributed[port_mask] += port_raster[port_mask]
            logger.info(f"Added precise port freight data to existing NUTS distribution at {np.sum(port_mask)} port pixels")
            logger.info(f"Total port freight added: {port_raster[port_mask].sum():,.0f}")
        
        return enhanced_distributed
    
    def _rasterize_port_freight(self, port_freight_data: pd.DataFrame, 
                              target_shape: Tuple[int, int]) -> np.ndarray:
        """Rasterize port freight data using high-resolution shapefile areas."""
        try:
            import rasterio.features
            from shapely.geometry import Polygon
            
            port_raster = np.zeros(target_shape, dtype=np.float32)
            
            # Use reference metadata from exposition layer if available
            if hasattr(self, '_reference_meta') and self._reference_meta:
                base_transform = self._reference_meta['transform']
            else:
                logger.warning("No reference metadata available for port rasterization")
                return port_raster
            
            
            target_resolution = self.config.target_resolution
            port_resolution = max(1.0, target_resolution / 2.0)
            
            logger.info(f"Using port rasterization resolution: {port_resolution}m (half of {target_resolution}m target)")
            
            hr_transform = rasterio.Affine(
                port_resolution, 0.0, base_transform.c,
                0.0, -port_resolution, base_transform.f
            )
            
            hr_width = int(target_shape[1] * (target_resolution / port_resolution))
            hr_height = int(target_shape[0] * (target_resolution / port_resolution))
            hr_shape = (hr_height, hr_width)
            
            logger.info(f"High-resolution raster shape: {hr_shape} (vs target: {target_shape})")
            
            # Create high-resolution raster for ports
            hr_port_raster = np.zeros(hr_shape, dtype=np.float32)
            
            # Process each port individually to distribute freight over its entire shapefile area
            for _, row in port_freight_data.iterrows():
                if 'geometry' in row and 'freight_value' in row:
                    # Debug logging for port processing
                    port_id = row.get('PORT_ID', row.get('port_id', 'unknown'))
                    freight_value = row.get('freight_value', 0)
                    logger.debug(f"Processing port {port_id}: freight={freight_value}, geometry_valid={row['geometry'] is not None}")
                    
                    if freight_value > 0 and row['geometry'] is not None:
                        
                        # Calculate area of the port polygon in square meters
                        port_area_m2 = row['geometry'].area
                        
                        if port_area_m2 > 0:
                            # Calculate freight density per square meter
                            freight_per_m2 = freight_value / port_area_m2
                            
                            # Calculate freight value per pixel (port_resolution x port_resolution)
                            pixel_area_m2 = port_resolution * port_resolution
                            freight_per_pixel = freight_per_m2 * pixel_area_m2
                            
                            # Rasterize this single port with its freight density
                            single_port_raster = rasterio.features.rasterize(
                                [(row['geometry'], freight_per_pixel)],
                                out_shape=hr_shape,
                                transform=hr_transform,
                                fill=0,
                                dtype=np.float32,
                                merge_alg=rasterio.enums.MergeAlg.add
                            )
                            
                            # Add to the combined high-resolution raster
                            hr_port_raster += single_port_raster
                            
                            logger.debug(f"Port {port_id}: "
                                       f"area={port_area_m2:,.0f}m², "
                                       f"freight={freight_value:,.0f}, "
                                       f"density={freight_per_pixel:.6f}/pixel")
            
            # Resample high-resolution raster back to target resolution
            from rasterio.warp import reproject, Resampling
            
            # Reproject from high-resolution to target resolution
            reproject(
                source=hr_port_raster,
                destination=port_raster,
                src_transform=hr_transform,
                src_crs=self.config.target_crs,
                dst_transform=base_transform,
                dst_crs=self.config.target_crs,
                resampling=Resampling.sum  # Use sum to preserve total freight values
            )
            
            logger.info(f"Rasterized {len(port_freight_data)} ports with area-based freight distribution")
            logger.info(f"Total rasterized freight: {port_raster.sum():,.0f}")
            
            return port_raster
            
        except Exception as e:
            logger.error(f"Error rasterizing port freight data: {e}")
            return np.zeros(target_shape, dtype=np.float32)


class RelevanceLayer:
    """
    Relative Relevance Layer Implementation for Economic Climate Risk Assessment
    ========================================================================
    
    The RelevanceLayer class provides comprehensive functionality for calculating
    relative economic relevance layers that represent the proportional importance
    of different economic activities across geographic regions. Unlike absolute
    analysis, this approach focuses on normalized relationships and comparative
    assessment for climate risk evaluation.
    
    Key Features:
    - Relative importance assessment across multiple economic indicators
    - Exposition-based spatial distribution within administrative regions
    - Advanced normalization and standardization techniques
    - Enhanced freight data integration for logistics activities
    - Comprehensive visualization and export capabilities
    - Flexible layer generation for targeted analysis
    
    Economic Indicators Processed:
    1. GDP (Gross Domestic Product): Relative economic output for regional comparison
    2. Freight: Maritime and logistics activities normalized for transport assessment
    3. HRST (Human Resources in Science and Technology): Innovation capacity indicator
    4. Combined layers: Integrated assessment across multiple indicators
    
    Core Processing Pipeline:
    1. Load and validate economic datasets from multiple sources
    2. Join economic data with appropriate NUTS administrative boundaries
    3. Rasterize NUTS regions with economic values
    4. Apply exposition-based spatial distribution within regions
    5. Integrate enhanced freight data for port and logistics areas
    6. Normalize and standardize values for relative comparison
    7. Generate combined relevance layers
    8. Export results and create comprehensive visualizations
    
    Normalization Approach:
    The layer applies advanced normalization techniques to ensure that different
    economic indicators are comparable and can be combined meaningfully. Values
    are normalized to [0,1] range while preserving spatial patterns and relative
    importance across regions.
    
    Integration with Climate Risk Assessment:
    The relative relevance layers provide the foundation for understanding which
    areas have higher relative economic importance, enabling risk assessment that
    considers both hazard exposure and economic significance in decision-making.
    """
    
    def __init__(self, config: ProjectConfig):
        """
        Initialize the Relevance Layer with all required components.
        
        Sets up data loaders, spatial transformers, distributors, and visualization
        tools needed for comprehensive relative relevance analysis.
        
        Args:
            config: Project configuration containing paths and processing parameters
        """
        self.config = config
        
        # Initialize core processing components
        self.economic_data_loader = EconomicDataLoader(config)
        self.nuts_mapper = NUTSDataMapper(config)
        self.transformer = RasterTransformer(
            target_crs=config.target_crs,
            config=config
        )
        self.economic_distributor = EconomicDistributor(config, self.transformer)
        self.exposition_layer = ExpositionLayer(config)
        self.visualizer = LayerVisualizer(config)
        
        # Initialize advanced normalizer for relative analysis
        self.normalizer = AdvancedDataNormalizer(NormalizationStrategy.ECONOMIC_OPTIMIZED)
        
        logger.info("Initialized Relevance Layer for relative economic analysis")
    
    def load_and_process_economic_data(self) -> Dict[str, gpd.GeoDataFrame]:
        """
        Load and process all economic datasets for relative relevance analysis.
        
        This method orchestrates the complete data loading pipeline, from raw
        economic datasets to spatially-enabled GeoDataFrames ready for analysis.
        
        Returns:
            Dictionary mapping dataset names to GeoDataFrames with economic data
        """
        # Load raw economic datasets
        economic_datasets = self.economic_data_loader.load_economic_datasets()
        
        if not economic_datasets:
            raise ValueError("No economic datasets could be loaded")
        
        # Define NUTS level requirements for each dataset
        required_nuts_levels = set()
        for dataset_name in economic_datasets.keys():
            dataset_config = self.config.economic_datasets.get(dataset_name, {})
            nuts_level = dataset_config.get('nuts_level', 'l3')
            required_nuts_levels.add(nuts_level)
        
        # Load required NUTS shapefiles
        nuts_gdfs = {}
        for nuts_level in required_nuts_levels:
            nuts_gdfs[nuts_level] = self.nuts_mapper.load_nuts_shapefile(nuts_level)
        
        # Join economic data with NUTS boundaries
        return self.nuts_mapper.join_economic_data(nuts_gdfs, economic_datasets)
    
    def calculate_relevance(self, layers_to_generate: List[str] = None) -> Tuple[Dict[str, np.ndarray], dict]:
        """
        Calculate relative economic relevance layers for all available indicators.
        
        This is the core method that processes economic data and creates spatially
        distributed relevance layers with proper normalization for comparative
        analysis across different economic indicators.
        
        Args:
            layers_to_generate: Optional list of specific indicators to generate
                             (e.g., ['gdp', 'freight']). If None, generates all available.
        
        Returns:
            Tuple containing:
            - Dictionary mapping indicator names to normalized relevance arrays
            - Metadata dictionary with spatial reference information
        """
        logger.info("Calculating relative economic relevance layers")
        
        # Load and process economic data
        nuts_economic_gdfs = self.load_and_process_economic_data()
        exposition_meta = self._get_exposition_metadata()
        
        # Define target economic variables for processing
        target_economic_variables = ['gdp', 'freight', 'hrst']
        
        # Filter to requested indicators if specified
        if layers_to_generate:
            target_economic_variables = [var for var in target_economic_variables if var in layers_to_generate]
            logger.info(f"Generating only requested indicators: {target_economic_variables}")
        
        # Filter to available indicators
        available_variables = [var for var in target_economic_variables if var in nuts_economic_gdfs]
        logger.info(f"Processing available indicators: {available_variables}")
        
        if not available_variables:
            raise ValueError("No economic variables available for relevance calculation")
        
        # Process each economic variable
        relevance_layers = {}
        for var_name in available_variables:
            nuts_gdf = nuts_economic_gdfs[var_name]
            
            logger.info(f"Processing {var_name} for relative relevance")
            
            # Rasterize NUTS regions with economic values
            economic_raster, raster_meta = self.economic_distributor.rasterize_nuts_regions(
                nuts_gdf, exposition_meta, var_name
            )
            
            # Get exposition layer for spatial distribution
            economic_exposition_data = self._get_economic_exposition_layer(var_name)
            
            # Ensure spatial alignment
            if economic_exposition_data.shape != economic_raster.shape:
                logger.warning(f"Shape mismatch for {var_name}, ensuring alignment")
                economic_exposition_data = self.transformer.ensure_alignment(
                    economic_exposition_data, exposition_meta['transform'], 
                    raster_meta['transform'], economic_raster.shape,
                    self.config.resampling_method
                )
            
            # Apply enhanced freight data if available
            enhanced_datasets = None
            if var_name == 'freight':
                if hasattr(self.economic_data_loader, 'enhanced_freight_datasets'):
                    enhanced_datasets = self.economic_data_loader.enhanced_freight_datasets
                    logger.info("Using enhanced freight datasets for distribution")
            
            # Apply economic distribution with exposition weighting
            distributed_economic_raster = self.economic_distributor.distribute_with_exposition(
                economic_raster, economic_exposition_data, enhanced_datasets, raster_meta
            )
            
            # Store result
            relevance_layers[var_name] = distributed_economic_raster
            
            # Log processing statistics
            valid_mask = ~np.isnan(distributed_economic_raster)
            if np.any(valid_mask):
                min_val = np.nanmin(distributed_economic_raster)
                max_val = np.nanmax(distributed_economic_raster)
                mean_val = np.nanmean(distributed_economic_raster)
                logger.info(f"Processed {var_name}: min={min_val:.6f}, max={max_val:.6f}, mean={mean_val:.6f}")
            
        # Create combined relevance layer if multiple indicators are available
        if len(relevance_layers) > 1:
            logger.info("Creating combined relevance layer from multiple indicators")
            
            # Normalize each layer to [0,1] range
            normalized_layers = {}
            for var_name, layer_data in relevance_layers.items():
                valid_mask = ~np.isnan(layer_data) & (layer_data > 0)
                if np.any(valid_mask):
                    normalized_layers[var_name] = self.normalizer.normalize_economic_data(
                        layer_data, valid_mask
                    )
                else:
                    normalized_layers[var_name] = layer_data
            
            # Combine normalized layers using weighted average
            combined_layer = np.zeros_like(list(normalized_layers.values())[0])
            weights = np.ones(len(normalized_layers)) / len(normalized_layers)  # Equal weights
            
            for i, (var_name, layer_data) in enumerate(normalized_layers.items()):
                combined_layer += weights[i] * layer_data
            
            relevance_layers['combined'] = combined_layer
            logger.info("Created combined relevance layer with equal weighting")
        
        logger.info(f"Completed relevance calculation for {len(relevance_layers)} layers")
        
        return relevance_layers, exposition_meta
    
    def _get_exposition_metadata(self) -> dict:
        """Get exposition metadata without expensive calculation."""
        # Use a lightweight approach to get metadata - check if default layer exists
        default_path = Path(self.config.output_dir) / "exposition" / "tif" / "exposition_layer.tif"
        
        if default_path.exists():
            # Load metadata from existing file
            with rasterio.open(default_path) as src:
                return src.meta
        else:
            # Generate metadata from config and reference data
            logger.info("No existing exposition layer found, generating metadata from config")
            
            # Use NUTS shapefile as reference for spatial extent and resolution
            nuts_l3_path = self.config.data_dir / "NUTS-L3-NL.shp"
            reference_bounds = self.transformer.get_reference_bounds(nuts_l3_path)
            
            # Calculate dimensions based on target resolution
            width = int((reference_bounds[2] - reference_bounds[0]) / self.config.target_resolution)
            height = int((reference_bounds[3] - reference_bounds[1]) / self.config.target_resolution)
            
            # Create transform
            transform = rasterio.transform.from_bounds(
                reference_bounds[0], reference_bounds[1], 
                reference_bounds[2], reference_bounds[3],
                width, height
            )
            
            return {
                'driver': 'GTiff',
                'dtype': 'float32',
                'width': width,
                'height': height,
                'count': 1,
                'crs': self.config.target_crs,
                'transform': transform,
                'nodata': None
            }
    
    def _get_economic_exposition_layer(self, dataset_name: str) -> np.ndarray:
        """Get economic exposition layer, creating it only if needed."""
        # Check if economic-specific layer exists
        tif_path = Path(self.config.output_dir) / "exposition" / "tif" / f"exposition_{dataset_name}.tif"
        
        if tif_path.exists():
            logger.info(f"Loading existing economic exposition layer for {dataset_name}")
            with rasterio.open(tif_path) as src:
                return src.read(1).astype(np.float32)
        else:
            # Create economic-specific layer only when needed
            logger.info(f"Creating economic exposition layer for {dataset_name}")
            
            # Get weights for this economic dataset
            economic_weights = self.config.economic_exposition_weights
            if dataset_name not in economic_weights:
                logger.warning(f"No specific exposition weights found for {dataset_name}, using default")
                # Fall back to default exposition layer
                default_data, _ = self.exposition_layer.calculate_exposition()
                return default_data
            
            weights = economic_weights[dataset_name]
            
            # Create the economic-specific exposition layer
            exposition_data, meta = self.exposition_layer.create_economic_exposition_layer(dataset_name, weights)
            
            # Save for future use
            tif_path.parent.mkdir(parents=True, exist_ok=True)
            self.exposition_layer.save_exposition_layer(exposition_data, meta, str(tif_path))
            logger.info(f"Created and saved economic exposition layer for {dataset_name}")
            
            return exposition_data
    
    def run_freight_relevance_only(self, visualize: bool = True, 
                                  export_tif: bool = True) -> Dict[str, np.ndarray]:
        """
        Convenience method to generate only the freight relevance layer with enhanced Zeevart data.
        
        Args:
            visualize: Whether to create visualization plots
            export_tif: Whether to export as GeoTIFF files
            
        Returns:
            Dictionary containing only the freight relevance layer
        """
        logger.info("Generating freight relevance layer only with enhanced Zeevart data")
        
        return self.run_relevance_analysis(
            visualize=visualize,
            export_individual_tifs=export_tif,
            layers_to_generate=['freight']
        )
    
    def _normalize_economic_layer(self, data: np.ndarray) -> np.ndarray:
        """Normalize economic layer using sophisticated economic optimization."""
        valid_mask = (data > 0) & ~np.isnan(data)
        return self.normalizer.normalize_economic_data(data, valid_mask)
    
    def save_relevance_layers(self, relevance_layers: Dict[str, np.ndarray], 
                            meta: dict):
        """Save all relevance layers as separate GeoTIFF files."""
        
        output_dir = self.config.output_dir / "relevance"
            
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_meta = meta.copy()
        output_meta.update({
            'driver': 'GTiff',
            'dtype': 'float32',
            'count': 1,
            'nodata': None
        })
        
        for layer_name, data in relevance_layers.items():
            output_path = output_dir / "tif" / f"relevance_{layer_name}.tif"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if output_path.exists():
                output_path.unlink()
                
            with rasterio.open(output_path, 'w', **output_meta) as dst:
                dst.write(data.astype(np.float32), 1)
                
            logger.info(f"Saved {layer_name} relevance layer to {output_path}")
    
    def visualize_relevance_layers(self, relevance_layers: Dict[str, np.ndarray], 
                                 meta: dict = None,
                                 save_plots: bool = True,
                                 plot_labels:bool = False):
        """Create and save visualization plots for each relevance layer using unified styling."""
        
        output_dir = self.config.output_dir / "relevance"
            
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("Creating relevance layer visualizations using unified styling...")
        
        land_mask = None
        try:
            with rasterio.open(self.config.land_mass_path) as src:
                if meta and 'transform' in meta:
                    land_mask, _ = rasterio.warp.reproject(
                        source=src.read(1),
                        destination=np.zeros((meta['height'], meta['width']), dtype=np.uint8),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=meta['transform'],
                        dst_crs=meta['crs'],
                        resampling=rasterio.enums.Resampling.nearest
                    )
                    land_mask = (land_mask > 0).astype(np.uint8)
                    logger.info("Loaded and transformed land mask for relevance visualizations")
                else:
                    logger.warning("No metadata available for land mask transformation")
        except Exception as e:
            logger.warning(f"Could not load land mask for relevance visualizations: {e}")
        
        for layer_name, data in relevance_layers.items():
            if save_plots:
                plot_path = output_dir / f"relevance_{layer_name}_plot.png"
                
                self.visualizer.visualize_relevance_layer(
                    data=data,
                    meta=meta,
                    layer_name=layer_name,
                    output_path=plot_path,
                    land_mask=land_mask
                )
                
                logger.info(f"Saved {layer_name} relevance layer PNG to {plot_path}")

    def run_relevance_analysis(self, visualize: bool = True, 
                             export_individual_tifs: bool = True,
                             layers_to_generate: List[str] = None) -> Dict[str, np.ndarray]:
        """Main execution flow for relevance layer analysis."""
        logger.info("Starting relevance layer analysis")
        
        relevance_layers, meta = self.calculate_relevance(layers_to_generate)
        
        if export_individual_tifs:
            self.save_relevance_layers(relevance_layers, meta)
            
        if visualize:
            self.visualize_relevance_layers(relevance_layers, meta)
            
        logger.info("Completed relevance layer analysis")
        return relevance_layers
