import rasterio
import rasterio.features
import rasterio.warp
import geopandas as gpd
import pandas as pd
from typing import Tuple, Dict, List, Optional
import numpy as np
from pathlib import Path

from eu_climate.config.config import ProjectConfig
from eu_climate.utils.utils import setup_logging
from eu_climate.utils.conversion import RasterTransformer
from eu_climate.utils.visualization import LayerVisualizer
from eu_climate.risk_layers.exposition_layer import ExpositionLayer
from eu_climate.risk_layers.relevance_layer import (
    EconomicDataLoader, NUTSDataMapper, EconomicDistributor
)
from eu_climate.utils.freight_processor import SharedFreightProcessor

logger = setup_logging(__name__)


class AbsoluteValueDistributor:
    """
    Absolute Value Distribution System for Economic Climate Risk Assessment
    ====================================================================
    
    The AbsoluteValueDistributor class handles the distribution of absolute economic values
    across geographic regions while maintaining strict mass conservation principles. Unlike
    relative distribution approaches, this system preserves the total economic value and
    distributes it spatially based on exposition layer patterns.
    
    Key Features:
    - Strict mass conservation ensuring no economic value is lost or artificially created
    - Spatial distribution based on exposition layer patterns (population, infrastructure, etc.)
    - Enhanced freight data integration for port areas and logistics hubs
    - High-resolution rasterization for accurate spatial representation
    - Comprehensive validation and error handling
    
    Core Principles:
    1. Mass Conservation: Total economic value before = Total economic value after
    2. Spatial Accuracy: Distribution follows real-world exposition patterns
    3. Data Integration: Incorporates multiple data sources (NUTS, exposition, freight)
    4. Quality Assurance: Extensive validation and logging throughout the process
    
    Processing Pipeline:
    1. Load economic data from NUTS regions (absolute values)
    2. Apply exposition-based spatial distribution within each region
    3. Integrate enhanced freight data for port areas
    4. Apply strict mass conservation to ensure total value preservation
    5. Validate results and provide comprehensive statistics
    
    The system is designed to handle various economic indicators including GDP, employment,
    and freight data while maintaining spatial accuracy and economic validity.
    """
    
    def __init__(self, config: ProjectConfig, transformer: RasterTransformer):
        """
        Initialize the Absolute Value Distributor with configuration and transformation tools.
        
        Args:
            config: Project configuration containing paths and processing parameters
            transformer: RasterTransformer instance for coordinate system handling
        """
        self.config = config
        self.transformer = transformer
        
    def distribute_absolute_values(self, economic_raster: np.ndarray,
                                 exposition_layer: np.ndarray,
                                 land_mask: np.ndarray,
                                 enhanced_freight_datasets: dict = None,
                                 reference_meta: dict = None) -> np.ndarray:
        """
        Distribute absolute economic values across geographic space with mass conservation.
        
        This is the main method for absolute value distribution that takes economic data
        in raster format and distributes it spatially based on exposition patterns while
        strictly preserving the total economic value.
        
        Args:
            economic_raster: Input raster with economic values by region
            exposition_layer: Exposition layer data for spatial distribution
            land_mask: Binary mask defining land areas (1=land, 0=water)
            enhanced_freight_datasets: Optional freight data for port enhancement
            reference_meta: Optional metadata for spatial reference
            
        Returns:
            Distributed economic values maintaining mass conservation
        """
        logger.info("Distributing absolute economic values with mass conservation")
        
        if reference_meta:
            self._reference_meta = reference_meta
        
        # Validate spatial alignment between input datasets
        if not self.transformer.validate_alignment(
            economic_raster, None, exposition_layer, None
        ):
            logger.warning("Raster alignment validation failed")
        
        # Calculate original total value for mass conservation validation
        original_total = self._calculate_original_total(economic_raster)
        logger.info(f"Original total value: {original_total:,.0f}")
        
        # Apply NUTS-based absolute distribution using exposition patterns
        distributed_absolute = self._apply_nuts_absolute_distribution(
            economic_raster, exposition_layer
        )
        
        # Apply enhanced freight data if available
        if enhanced_freight_datasets and 'port_freight' in enhanced_freight_datasets:
            logger.info("Applying enhanced port freight data")
            distributed_absolute = self._apply_port_freight_enhancement(
                distributed_absolute, enhanced_freight_datasets['port_freight']
            )
        
        # Check distributed total before mass conservation
        distributed_total = np.sum(distributed_absolute[~np.isnan(distributed_absolute)])
        logger.info(f"Distributed total before conservation: {distributed_total:,.0f}")
        
        # Apply mass conservation to ensure total value preservation
        conserved_distribution = self._apply_mass_conservation(
            distributed_absolute, original_total, land_mask
        )
        
        # Final validation of mass conservation
        final_total = np.sum(conserved_distribution[~np.isnan(conserved_distribution)])
        logger.info(f"Final conserved total: {final_total:,.0f}")
        logger.info(f"Mass conservation accuracy: {(final_total/original_total)*100:.6f}%")
        
        return conserved_distribution
    
    def _calculate_original_total(self, economic_raster: np.ndarray) -> float:
        """
        Calculate the total economic value from original NUTS raster data.
        
        This method determines the total economic value that must be preserved
        throughout the distribution process to ensure mass conservation.
        
        Args:
            economic_raster: Input raster with economic values by region
            
        Returns:
            Total economic value from all regions
        """
        unique_values = np.unique(economic_raster)
        unique_values = unique_values[unique_values > 0]
        return float(np.sum(unique_values))
    
    def _apply_nuts_absolute_distribution(self, economic_raster: np.ndarray,
                                        exposition_layer: np.ndarray) -> np.ndarray:
        """
        Apply NUTS-based absolute distribution preserving original regional values.
        
        This method distributes economic values within each NUTS region based on
        the exposition layer patterns, ensuring that the total value for each
        region is preserved exactly.
        
        Args:
            economic_raster: Input raster with economic values by region
            exposition_layer: Exposition layer for spatial distribution patterns
            
        Returns:
            Spatially distributed economic values maintaining regional totals
        """
        distributed = np.zeros_like(economic_raster, dtype=np.float32)
        
        # Get unique economic values representing different regions
        unique_values = np.unique(economic_raster)
        unique_values = unique_values[unique_values > 0]
        
        # Process each region individually
        for region_value in unique_values:
            # Create mask for current region
            region_mask = economic_raster == region_value
            
            # Get exposition values within this region
            region_exposition = exposition_layer * region_mask
            total_exposition = np.sum(region_exposition)
            
            # Distribute regional value proportionally based on exposition
            if total_exposition > 0:
                # Proportional distribution based on exposition patterns
                distributed += (region_exposition / total_exposition) * region_value
            else:
                # Fallback: uniform distribution within region if no exposition data
                region_cells = np.sum(region_mask)
                if region_cells > 0:
                    distributed[region_mask] = region_value / region_cells
        
        return distributed
    
    def _apply_port_freight_enhancement(self, distributed_base: np.ndarray,
                                      port_freight_data: pd.DataFrame) -> np.ndarray:
        """
        Apply port freight enhancement to distributed economic values.
        
        This method adds freight-specific economic activity to port areas,
        enhancing the base economic distribution with logistics and freight
        handling activities.
        
        Args:
            distributed_base: Base distributed economic values
            port_freight_data: DataFrame with port freight information
            
        Returns:
            Enhanced economic distribution including port freight activities
        """
        if port_freight_data.empty:
            logger.info("No port freight data available for enhancement")
            return distributed_base

        logger.info(f"Enhancing with {len(port_freight_data)} port freight entries")
        
        # Create port freight raster
        port_raster = self._rasterize_port_freight(port_freight_data, distributed_base.shape)
        
        # Add port freight to base distribution
        enhanced_distributed = distributed_base.copy()
        port_mask = (port_raster > 0) & (~np.isnan(port_raster))
        
        if np.any(port_mask):
            enhanced_distributed[port_mask] += port_raster[port_mask]
            logger.info(f"Added port freight to {np.sum(port_mask)} port pixels")
        
        return enhanced_distributed
    
    def _rasterize_port_freight(self, port_freight_data: pd.DataFrame,
                               target_shape: Tuple[int, int]) -> np.ndarray:
        """
        Rasterize port freight data using high-resolution approach for accuracy.
        
        This method converts port freight data from vector format to raster format,
        using a high-resolution intermediate grid to ensure accurate spatial
        representation of port activities.
        
        Args:
            port_freight_data: DataFrame containing port geometries and freight values
            target_shape: Shape of the target raster grid
            
        Returns:
            Rasterized port freight data aligned with target grid
        """
        try:
            import rasterio.features
            
            port_raster = np.zeros(target_shape, dtype=np.float32)
            
            # Get reference metadata for spatial transformation
            if hasattr(self, '_reference_meta') and self._reference_meta:
                base_transform = self._reference_meta['transform']
            else:
                logger.warning("No reference metadata available for port rasterization")
                return port_raster
            
            # Use high-resolution intermediate grid for accuracy
            target_resolution = self.config.target_resolution
            port_resolution = max(1.0, target_resolution / 2.0)  # Higher resolution for ports
            
            # Create high-resolution transform
            hr_transform = rasterio.Affine(
                port_resolution, 0.0, base_transform.c,
                0.0, -port_resolution, base_transform.f
            )
            
            # Calculate high-resolution grid dimensions
            hr_width = int(target_shape[1] * (target_resolution / port_resolution))
            hr_height = int(target_shape[0] * (target_resolution / port_resolution))
            hr_shape = (hr_height, hr_width)
            hr_port_raster = np.zeros(hr_shape, dtype=np.float32)
            
            # Process each port individually
            for _, row in port_freight_data.iterrows():
                if 'geometry' in row and 'freight_value' in row:
                    freight_value = row.get('freight_value', 0)
                    
                    if freight_value > 0 and row['geometry'] is not None:
                        # Calculate freight density per unit area
                        port_area_square_meters = row['geometry'].area
                        
                        if port_area_square_meters > 0:
                            freight_per_square_meter = freight_value / port_area_square_meters
                            pixel_area_square_meters = port_resolution * port_resolution
                            freight_per_pixel = freight_per_square_meter * pixel_area_square_meters
                            
                            # Rasterize this port
                            single_port_raster = rasterio.features.rasterize(
                                [(row['geometry'], freight_per_pixel)],
                                out_shape=hr_shape,
                                transform=hr_transform,
                                fill=0,
                                dtype=np.float32,
                                merge_alg=rasterio.enums.MergeAlg.add
                            )
                            
                            # Add to high-resolution port raster
                            hr_port_raster += single_port_raster
            
            # Reproject high-resolution port raster to target resolution
            from rasterio.warp import reproject, Resampling
            
            reproject(
                source=hr_port_raster,
                destination=port_raster,
                src_transform=hr_transform,
                src_crs=self.config.target_crs,
                dst_transform=base_transform,
                dst_crs=self.config.target_crs,
                resampling=Resampling.sum  # Use sum to preserve total freight value
            )
            
            logger.info(f"Rasterized ports: total freight = {port_raster.sum():,.0f}")
            return port_raster
            
        except Exception as e:
            logger.error(f"Error rasterizing port freight data: {e}")
            return np.zeros(target_shape, dtype=np.float32)
    
    def _apply_mass_conservation(self, distributed_values: np.ndarray,
                               original_total: float,
                               land_mask: np.ndarray) -> np.ndarray:
        """
        Apply mass conservation to ensure total value preservation.
        
        This method ensures that the total economic value is exactly preserved
        after spatial distribution, redistributing any discrepancies proportionally
        across valid land areas.
        
        Args:
            distributed_values: Spatially distributed economic values
            original_total: Original total economic value that must be preserved
            land_mask: Binary mask defining valid land areas
            
        Returns:
            Mass-conserved economic distribution with exact total preservation
        """
        # Calculate current total
        distributed_total = np.sum(distributed_values[~np.isnan(distributed_values)])
        value_difference = original_total - distributed_total
        
        logger.info(f"Value difference to redistribute: {value_difference:,.0f}")
        
        # If difference is negligible, return original distribution
        if abs(value_difference) < 1e-6:
            logger.info("No significant value difference, returning original distribution")
            return distributed_values
        
        # Get valid land areas with existing values for redistribution
        valid_land_with_values = (land_mask == 1) & (distributed_values > 0) & (~np.isnan(distributed_values))
        
        if not np.any(valid_land_with_values):
            logger.warning("No valid land areas with values for redistribution")
            return distributed_values
        
        # Calculate redistribution weights based on existing values
        existing_values = distributed_values[valid_land_with_values]
        total_existing = np.sum(existing_values)
        
        if total_existing > 0:
            # Proportional redistribution based on existing values
            redistribution_weights = existing_values / total_existing
            redistribution_per_pixel = value_difference * redistribution_weights
            
            # Apply redistribution
            conserved_distribution = distributed_values.copy()
            conserved_distribution[valid_land_with_values] += redistribution_per_pixel
            
            logger.info(f"Redistributed {value_difference:,.0f} across {np.sum(valid_land_with_values)} pixels")
        else:
            logger.warning("No existing values for proportional redistribution")
            conserved_distribution = distributed_values.copy()
        
        return conserved_distribution


class AbsoluteEconomicDataLoader:
    """
    Enhanced Economic Data Loader for Absolute Relevance Analysis
    ==========================================================
    
    The AbsoluteEconomicDataLoader class provides specialized functionality for loading
    and preprocessing economic datasets used in absolute relevance analysis. Unlike
    relative analysis, absolute analysis requires precise economic values that will
    be spatially distributed while maintaining total value conservation.
    
    Key Features:
    - Comprehensive economic dataset loading (GDP, HRST, freight data)
    - Enhanced error handling and debugging capabilities
    - Shared freight processor integration for logistics data
    - Data validation and quality assurance
    - Flexible fallback mechanisms for missing data
    
    Supported Economic Indicators:
    1. GDP (Gross Domestic Product): Regional economic output values
    2. HRST (Human Resources in Science and Technology): Employment in innovation sectors
    3. Freight Data: Maritime and logistics economic activities
    
    Data Processing Pipeline:
    1. Load raw economic datasets from multiple sources
    2. Apply standardized preprocessing and cleaning
    3. Validate data quality and completeness
    4. Integrate enhanced freight data from shared processor
    5. Provide comprehensive logging and error reporting
    
    The loader ensures that economic values are preserved exactly as they will be
    spatially distributed later in the analysis pipeline.
    """
    
    def __init__(self, config: ProjectConfig):
        """
        Initialize the Absolute Economic Data Loader.
        
        Args:
            config: Project configuration with data paths and processing parameters
        """
        self.config = config
        self.data_dir = config.data_dir
        self.freight_processor = SharedFreightProcessor(config)
        
    def load_economic_datasets(self) -> Dict[str, pd.DataFrame]:
        """
        Load all economic datasets with enhanced debugging and error handling.
        
        This method orchestrates the loading of all economic datasets required for
        absolute relevance analysis, providing comprehensive error handling and
        data validation throughout the process.
        
        Returns:
            Dictionary mapping dataset names to processed DataFrames
        """
        datasets = {}
        
        # GDP dataset with fallback paths
        gdp_loaded = self._load_gdp_data(datasets)
        if not gdp_loaded:
            logger.warning("GDP data could not be loaded - check file paths")
            
        # Freight dataset using shared processor
        freight_data, enhanced_datasets = self._load_freight_data_shared()
        if not freight_data.empty:
            datasets['freight'] = freight_data
            # Store enhanced datasets for later use in distribution
            if enhanced_datasets:
                self.enhanced_freight_datasets = enhanced_datasets
        else:
            logger.warning("Freight data could not be loaded")
            
        # HRST dataset with enhanced debugging  
        hrst_loaded = self._load_hrst_data(datasets)
        if not hrst_loaded:
            logger.warning("HRST data could not be loaded - check file paths")
        
        # Log comprehensive dataset statistics
        logger.info(f"Successfully loaded datasets: {list(datasets.keys())}")
        for dataset_name, dataset in datasets.items():
            if not dataset.empty:
                value_col = f"{dataset_name}_value"
                if value_col in dataset.columns:
                    total_value = dataset[value_col].sum()
                    max_value = dataset[value_col].max() 
                    min_value = dataset[value_col].min()
                    logger.info(f"{dataset_name.upper()} - Total: {total_value:,.0f}, Max: {max_value:,.0f}, Min: {min_value:,.0f}")
        
        return datasets
    
    def _load_gdp_data(self, datasets: Dict[str, pd.DataFrame]) -> bool:
        """
        Load GDP (Gross Domestic Product) data with enhanced error handling.
        
        This method attempts to load GDP data from the configured path, applying
        preprocessing to extract NUTS L3 values and ensuring data quality.
        
        Args:
            datasets: Dictionary to store the loaded GDP dataset
            
        Returns:
            True if GDP data was successfully loaded, False otherwise
        """
        try:
            # Try primary GDP file path
            gdp_path = self.data_dir / "L3-estat_gdp.csv" / "estat_nama_10r_3gdp_en.csv"
            if gdp_path.exists():
                logger.info(f"Loading GDP dataset from {gdp_path}")
                gdp_df = pd.read_csv(gdp_path)
                datasets['gdp'] = self._process_gdp_data(gdp_df)
                logger.info(f"Successfully loaded GDP data with {len(datasets['gdp'])} regions")
                return True
            else:
                logger.error(f"GDP dataset not found: {gdp_path}")
                return False
                
        except Exception as e:
            logger.error(f"Error loading GDP data: {e}")
            return False
    
    def _load_hrst_data(self, datasets: Dict[str, pd.DataFrame]) -> bool:
        """
        Load HRST (Human Resources in Science and Technology) data.
        
        This method loads employment data for science and technology sectors,
        which represents innovation capacity and high-skilled employment.
        
        Args:
            datasets: Dictionary to store the loaded HRST dataset
            
        Returns:
            True if HRST data was successfully loaded, False otherwise
        """
        try:
            # Try configured HRST file path
            hrst_path = self.data_dir / getattr(self.config, 'hrst_file_path', 'L2_estat_hrst_st_rcat_filtered_en/estat_hrst_st_rcat_filtered_en.csv')
            if hrst_path.exists():
                logger.info(f"Loading HRST dataset from {hrst_path}")
                hrst_df = pd.read_csv(hrst_path)
                datasets['hrst'] = self._process_hrst_data(hrst_df)
                logger.info(f"Successfully loaded HRST data with {len(datasets['hrst'])} regions")
                return True
            else:
                logger.error(f"HRST dataset not found: {hrst_path}")
                return False
                
        except Exception as e:
            logger.error(f"Error loading HRST data: {e}")
            return False
    
    def _load_freight_data_shared(self) -> Tuple[pd.DataFrame, Optional[Dict[str, pd.DataFrame]]]:
        """
        Load enhanced freight data using shared processor.
        
        This method leverages the shared freight processor to load both NUTS-level
        freight statistics and enhanced datasets including port-specific data.
        
        Returns:
            Tuple of (NUTS freight data, enhanced datasets dictionary)
        """
        logger.info("Loading freight data using shared processor")
        
        try:
            nuts_freight_data, enhanced_datasets = self.freight_processor.load_and_process_freight_data()
            
            if enhanced_datasets:
                logger.info("Enhanced freight datasets available for distribution")
                return nuts_freight_data, enhanced_datasets
            
            if nuts_freight_data.empty:
                logger.warning("No NUTS freight data available from shared processor")
                return pd.DataFrame(), None
            
            return nuts_freight_data, enhanced_datasets
            
        except Exception as e:
            logger.error(f"Error loading freight data with shared processor: {e}")
            return pd.DataFrame(), None
    
    def _process_gdp_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process GDP dataset to extract NUTS L3 values for absolute analysis.
        
        This method filters and processes GDP data to extract the most recent
        values for Netherlands NUTS L3 regions, ensuring data quality and
        consistency for absolute value distribution.
        
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

        # Handle missing values with comprehensive logging
        if processed.isna().any().any():
            logger.warning("NaN values detected in GDP data")
            len_before = len(processed)
            processed = processed.dropna()
            len_after = len(processed)
            logger.warning(f"Dropped {len_before - len_after} NaN values from GDP data")

        logger.info(f"Processed GDP data: {len(processed)} regions for year {latest_year}")
        return processed
    
    def _process_hrst_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process HRST dataset to extract NUTS L2 values for absolute analysis.
        
        This method processes Human Resources in Science and Technology data,
        extracting employment figures for high-skilled sectors that represent
        innovation capacity and economic competitiveness.
        
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
        
        # Handle missing values with comprehensive logging
        if processed.isna().any().any():
            logger.warning("NaN values detected in HRST data")
            len_before = len(processed)
            processed = processed.dropna()
            len_after = len(processed)
            logger.warning(f"Dropped {len_before - len_after} NaN values from HRST data")
        
        logger.info(f"Processed HRST data: {len(processed)} regions for year {latest_year}")
        return processed


class RelevanceAbsoluteLayer:
    """
    Absolute Relevance Layer Implementation for Economic Climate Risk Assessment
    ========================================================================
    
    The RelevanceAbsoluteLayer class provides comprehensive functionality for calculating
    absolute economic relevance layers while preserving exact economic values through
    mass conservation. This approach maintains the total economic value of each region
    while distributing it spatially based on exposition patterns.
    
    Key Features:
    - Absolute value preservation with strict mass conservation
    - Multi-indicator economic analysis (GDP, freight, HRST, population)
    - Exposition-based spatial distribution within regions
    - Enhanced freight data integration for logistics activities
    - Comprehensive visualization and export capabilities
    
    Economic Indicators Processed:
    1. GDP (Gross Domestic Product): Regional economic output in millions of EUR
    2. Freight: Combined maritime, loading, and unloading activities in tonnes
    3. HRST (Human Resources in Science and Technology): Employment in innovation sectors
    4. Population: Total population count for demographic analysis
    
    Core Processing Pipeline:
    1. Load economic datasets from multiple sources with validation
    2. Join economic data with appropriate NUTS administrative boundaries
    3. Rasterize NUTS regions with economic values
    4. Apply exposition-based spatial distribution with mass conservation
    5. Integrate enhanced freight data for port and logistics areas
    6. Export results and create comprehensive visualizations
    
    Mass Conservation Principle:
    The layer ensures that the sum of all spatially distributed values equals
    the original regional totals, maintaining economic accuracy while providing
    detailed spatial distribution for climate risk assessment.
    
    Integration with Climate Risk Assessment:
    The absolute relevance layers provide the economic foundation for risk
    calculation, representing the actual economic value at stake in each
    geographic location under different climate scenarios.
    """
    
    def __init__(self, config: ProjectConfig):
        """
        Initialize the Absolute Relevance Layer with all required components.
        
        Sets up data loaders, spatial transformers, distributors, and visualization
        tools needed for comprehensive absolute relevance analysis.
        
        Args:
            config: Project configuration containing paths and processing parameters
        """
        self.config = config
        
        # Initialize core components
        self.economic_data_loader = AbsoluteEconomicDataLoader(config)
        self.nuts_mapper = NUTSDataMapper(config)
        self.transformer = RasterTransformer(
            target_crs=config.target_crs,
            config=config
        )
        self.absolute_distributor = AbsoluteValueDistributor(config, self.transformer)
        self.exposition_layer = ExpositionLayer(config)
        self.visualizer = LayerVisualizer(config)
        
        logger.info("Initialized Absolute Relevance Layer with enhanced data loading")
    
    def load_and_process_absolute_economic_data(self) -> Dict[str, gpd.GeoDataFrame]:
        """
        Load and process all economic datasets for absolute value analysis.
        
        This method orchestrates the loading of economic datasets from multiple
        sources and joins them with appropriate NUTS administrative boundaries
        to create spatially-enabled economic data ready for distribution.
        
        Returns:
            Dictionary mapping dataset names to GeoDataFrames with economic data
        """
        # Load raw economic datasets
        economic_datasets = self.economic_data_loader.load_economic_datasets()
        
        if not economic_datasets:
            raise ValueError("No economic datasets could be loaded for absolute processing")
        
        # Define NUTS level mapping for each dataset
        dataset_nuts_mapping = {
            'gdp': 'l3',       # GDP is available at NUTS L3 level
            'freight': 'l3',   # Freight is available at NUTS L3 level  
            'hrst': 'l2'       # HRST is available at NUTS L2 level
        }
        
        # Determine required NUTS levels
        required_nuts_levels = set()
        for dataset_name in economic_datasets.keys():
            nuts_level = dataset_nuts_mapping.get(dataset_name, 'l3')
            required_nuts_levels.add(nuts_level)
            logger.info(f"Dataset {dataset_name} mapped to NUTS level {nuts_level}")
        
        # Load NUTS shapefiles for required levels
        nuts_gdfs = {}
        for nuts_level in required_nuts_levels:
            nuts_gdfs[nuts_level] = self.nuts_mapper.load_nuts_shapefile(nuts_level)
        
        # Join each dataset with its appropriate NUTS level
        joined_gdfs = {}
        
        for dataset_name, dataset_data in economic_datasets.items():
            nuts_level = dataset_nuts_mapping.get(dataset_name, 'l3')
            nuts_gdf = nuts_gdfs[nuts_level].copy()
            
            logger.info(f"Joining {dataset_name} data with NUTS {nuts_level.upper()}")
            
            # Use the standard economic data joining approach for all datasets
            single_dataset = {dataset_name: dataset_data}
            single_nuts = {nuts_level: nuts_gdf}
            joined_result = self.nuts_mapper.join_economic_data(single_nuts, single_dataset)
            
            if dataset_name in joined_result:
                joined_gdfs[dataset_name] = joined_result[dataset_name]
                logger.info(f"Successfully joined {dataset_name} data: {len(joined_result[dataset_name])} regions")
            else:
                logger.warning(f"Failed to join {dataset_name} data with NUTS {nuts_level.upper()}")
        
        return joined_gdfs
    
    def calculate_absolute_relevance(self, layers_to_generate: List[str] = None) -> Tuple[Dict[str, np.ndarray], dict]:
        """
        Calculate absolute economic relevance layers with mass conservation.
        
        This is the core method that processes economic data and creates spatially
        distributed relevance layers while preserving exact economic values through
        mass conservation principles.
        
        Args:
            layers_to_generate: Optional list of specific indicators to generate
                             (e.g., ['gdp', 'freight']). If None, generates all available.
        
        Returns:
            Tuple containing:
            - Dictionary mapping indicator names to relevance arrays
            - Metadata dictionary with spatial reference information
        """
        logger.info("Calculating absolute economic relevance layers")
        
        # Load and process economic data
        nuts_economic_gdfs = self.load_and_process_absolute_economic_data()
        exposition_meta = self._get_exposition_metadata()
        
        # Define target indicators for processing
        target_indicators = ['gdp', 'freight', 'hrst']
        
        # Filter to requested indicators if specified
        if layers_to_generate:
            target_indicators = [indicator for indicator in target_indicators if indicator in layers_to_generate]
            logger.info(f"Generating only requested indicators: {target_indicators}")
        
        # Filter to available indicators
        available_indicators = [indicator for indicator in target_indicators if indicator in nuts_economic_gdfs]
        logger.info(f"Processing available indicators: {available_indicators}")
        
        # Load land mask for spatial constraint
        land_mask = self._load_land_mask(exposition_meta)
        absolute_relevance_layers = {}
        
        # Process each indicator individually
        for indicator_name in available_indicators:
            nuts_gdf = nuts_economic_gdfs[indicator_name]
            
            logger.info(f"Processing {indicator_name} for absolute relevance")
            
            # Rasterize NUTS regions with economic values
            economic_raster, raster_meta = self._rasterize_nuts_regions_absolute(
                nuts_gdf, exposition_meta, indicator_name
            )
            
            # Get exposition layer for spatial distribution
            economic_exposition_data = self._get_economic_exposition_layer(indicator_name)
            
            # Ensure spatial alignment
            if economic_exposition_data.shape != economic_raster.shape:
                logger.warning(f"Shape mismatch for {indicator_name}, ensuring alignment")
                economic_exposition_data = self.transformer.ensure_alignment(
                    economic_exposition_data, exposition_meta['transform'],
                    raster_meta['transform'], economic_raster.shape,
                    self.config.resampling_method
                )
            
            # Apply enhanced freight data if available
            enhanced_datasets = None
            if indicator_name == 'freight':
                if hasattr(self.economic_data_loader, 'enhanced_freight_datasets'):
                    enhanced_datasets = self.economic_data_loader.enhanced_freight_datasets
                    logger.info("Using enhanced freight datasets for absolute distribution")
                else:
                    logger.warning("Enhanced freight datasets not available in economic data loader")
            
            # Apply absolute distribution with mass conservation
            absolute_distributed_raster = self.absolute_distributor.distribute_absolute_values(
                economic_raster, economic_exposition_data, land_mask,
                enhanced_datasets, raster_meta
            )
            
            # Store result
            absolute_relevance_layers[indicator_name] = absolute_distributed_raster
            
            # Log final statistics for validation
            final_total = np.sum(absolute_distributed_raster[~np.isnan(absolute_distributed_raster)])
            max_value = np.nanmax(absolute_distributed_raster)
            min_value = np.nanmin(absolute_distributed_raster[absolute_distributed_raster > 0])
            logger.info(f"Final {indicator_name} distribution - Total: {final_total:,.0f}, Max: {max_value:,.6f}, Min: {min_value:,.6f}")
        
        # Validate results
        if not absolute_relevance_layers:
            raise ValueError("No absolute relevance layers could be calculated")
        
        logger.info(f"Completed absolute relevance calculation for {len(absolute_relevance_layers)} indicators")
        
        return absolute_relevance_layers, exposition_meta
    
    def _get_exposition_metadata(self) -> dict:
        """
        Get exposition metadata for consistent spatial alignment.
        
        This method retrieves spatial reference information from the exposition
        layer to ensure all processing uses consistent coordinate systems and
        spatial resolutions.
        
        Returns:
            Dictionary containing spatial metadata (transform, CRS, dimensions)
        """
        default_path = Path(self.config.output_dir) / "exposition" / "tif" / "exposition_layer.tif"
        
        if default_path.exists():
            with rasterio.open(default_path) as src:
                return {
                    'transform': src.transform,
                    'crs': src.crs,
                    'height': src.height,
                    'width': src.width,
                    'dtype': src.dtypes[0]
                }
        else:
            # Generate exposition layer if it doesn't exist
            logger.info("Exposition layer not found, generating new one")
            exposition_data, exposition_meta = self.exposition_layer.calculate_exposition()
            self.exposition_layer.save_exposition_layer(exposition_data, exposition_meta)
            return exposition_meta
    
    def _rasterize_nuts_regions_absolute(self, nuts_gdf: gpd.GeoDataFrame,
                                       exposition_meta: dict,
                                       economic_variable: str) -> Tuple[np.ndarray, dict]:
        """Rasterize NUTS regions preserving absolute economic values."""
        logger.info(f"Rasterizing NUTS regions for absolute {economic_variable}")
        
        transform = exposition_meta['transform']
        height = exposition_meta['height']
        width = exposition_meta['width']
        
        value_column = f"{economic_variable}_value"
        if value_column not in nuts_gdf.columns:
            raise ValueError(f"Economic variable {value_column} not found in data")
        
        shapes = [(geom, value) for geom, value in zip(
            nuts_gdf.geometry, nuts_gdf[value_column]
        ) if not np.isnan(value) and value > 0]
        
        raster = rasterio.features.rasterize(
            shapes,
            out_shape=(height, width),
            transform=transform,
            fill=0,
            dtype=np.float32
        )
        
        meta = exposition_meta.copy()
        meta['dtype'] = 'float32'
        
        logger.info(f"Rasterized absolute {economic_variable}: "
                   f"shape={raster.shape}, min={np.min(raster)}, max={np.max(raster)}")
        
        return raster, meta
    
    def _get_economic_exposition_layer(self, dataset_name: str) -> np.ndarray:
        """Get economic exposition layer for spatial distribution."""
        tif_path = Path(self.config.output_dir) / "exposition" / "tif" / f"exposition_{dataset_name}.tif"
        
        if tif_path.exists():
            logger.info(f"Loading existing economic exposition layer for {dataset_name}")
            with rasterio.open(tif_path) as src:
                return src.read(1).astype(np.float32)
        else:
            logger.info(f"Creating economic exposition layer for {dataset_name}")
            
            economic_weights = self.config.economic_exposition_weights
            if dataset_name not in economic_weights:
                logger.warning(f"No specific exposition weights found for {dataset_name}, using default")
                default_data, _ = self.exposition_layer.calculate_exposition()
                return default_data
            
            weights = economic_weights[dataset_name]
            exposition_data, meta = self.exposition_layer.create_economic_exposition_layer(dataset_name, weights)
            
            tif_path.parent.mkdir(parents=True, exist_ok=True)
            self.exposition_layer.save_exposition_layer(exposition_data, meta, str(tif_path))
            logger.info(f"Created and saved economic exposition layer for {dataset_name}")
            
            return exposition_data
    
    def _load_land_mask(self, exposition_meta: dict) -> np.ndarray:
        """Load land mask for mass conservation calculations."""
        try:
            with rasterio.open(self.config.land_mass_path) as src:
                land_mask, _ = rasterio.warp.reproject(
                    source=src.read(1),
                    destination=np.zeros((exposition_meta['height'], exposition_meta['width']), dtype=np.uint8),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=exposition_meta['transform'],
                    dst_crs=exposition_meta['crs'],
                    resampling=rasterio.enums.Resampling.nearest
                )
                land_mask = (land_mask > 0).astype(np.uint8)
                logger.info("Loaded land mask for absolute relevance processing")
                return land_mask
        except Exception as e:
            logger.warning(f"Could not load land mask: {e}")
            exposition_shape = (exposition_meta['height'], exposition_meta['width'])
            return np.ones(exposition_shape, dtype=np.uint8)
    
    def save_absolute_relevance_layers(self, relevance_layers: Dict[str, np.ndarray], meta: dict):
        """Save absolute relevance layers to dedicated folder structure."""
        output_dir = self.config.output_dir / "relevance_absolute"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        tif_dir = output_dir / "tif"
        tif_dir.mkdir(parents=True, exist_ok=True)
        
        output_meta = meta.copy()
        output_meta.update({
            'driver': 'GTiff',
            'dtype': 'float32',
            'count': 1,
            'nodata': None
        })
        
        for layer_name, data in relevance_layers.items():
            output_path = tif_dir / f"absolute_relevance_{layer_name}.tif"
            
            if output_path.exists():
                output_path.unlink()
            
            with rasterio.open(output_path, 'w', **output_meta) as dst:
                dst.write(data.astype(np.float32), 1)
            
            logger.info(f"Saved absolute {layer_name} relevance layer to {output_path}")
    
    def visualize_absolute_relevance_layers(self, relevance_layers: Dict[str, np.ndarray],
                                          meta: dict = None, save_plots: bool = True):
        """Create visualizations for absolute relevance layers using unified styling."""
        output_dir = self.config.output_dir / "relevance_absolute"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("Creating absolute relevance layer visualizations...")
        
        land_mask = self._load_land_mask(meta)
        
        for layer_name, data in relevance_layers.items():
            if save_plots:
                plot_path = output_dir / f"absolute_relevance_{layer_name}_plot.png"
                
                self.visualizer.visualize_relevance_layer(
                    data=data,
                    meta=meta,
                    layer_name=f"absolute_{layer_name}",
                    output_path=plot_path,
                    land_mask=land_mask
                )
                
                logger.info(f"Saved absolute {layer_name} relevance visualization to {plot_path}")
    
    def run_absolute_relevance_analysis(self, visualize: bool = True,
                                      export_individual_tifs: bool = True,
                                      layers_to_generate: List[str] = None) -> Dict[str, np.ndarray]:
        """Main execution flow for absolute relevance layer analysis."""
        logger.info("Starting absolute relevance layer analysis with mass conservation")
        
        absolute_relevance_layers, meta = self.calculate_absolute_relevance(layers_to_generate)
        
        if export_individual_tifs:
            self.save_absolute_relevance_layers(absolute_relevance_layers, meta)
        
        if visualize:
            self.visualize_absolute_relevance_layers(absolute_relevance_layers, meta)
        
        logger.info("Completed absolute relevance layer analysis")
        return absolute_relevance_layers 