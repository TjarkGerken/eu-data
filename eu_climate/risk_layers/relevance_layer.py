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
    """Handles loading and preprocessing of NUTS L3 economic datasets."""
    
    def __init__(self, config: ProjectConfig):
        self.config = config
        self.data_dir = config.data_dir
        self.freight_processor = SharedFreightProcessor(config)
        
    def load_economic_datasets(self) -> Dict[str, pd.DataFrame]:
        """Load all economic datasets and standardize format."""
        datasets = {}
        
        # GDP dataset
        gdp_path = self.data_dir / "L3-estat_gdp.csv" / "estat_nama_10r_3gdp_en.csv"
        if gdp_path.exists():
            logger.info(f"Loading GDP dataset from {gdp_path}")
            gdp_df = pd.read_csv(gdp_path)
            datasets['gdp'] = self._process_gdp_data(gdp_df)
        else:
            logger.error(f"GDP dataset not found: {gdp_path}")
            
        # Use shared freight processor
        freight_data = self._load_maritime_freight_data()
        if not freight_data.empty:
            datasets['freight'] = freight_data
            
        hrst_path = self.data_dir / getattr(self.config, 'hrst_file_path', 'L2_estat_hrst_st_rcat_filtered_en/estat_hrst_st_rcat_filtered_en.csv')
        if hrst_path.exists():
            logger.info(f"Loading HRST dataset from {hrst_path}")
            hrst_df = pd.read_csv(hrst_path)
            datasets['hrst'] = self._process_hrst_data(hrst_df)
        else:
            logger.error(f"HRST dataset not found: {hrst_path}")
            
        return datasets
    
    def _process_gdp_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process GDP dataset to extract NUTS L3 values."""
        # Filter for Netherlands (NL) and NUTS L3 regions
        nl_data = df[df['geo'].str.startswith('NL') & df['geo'].str.len().eq(5)]
        
        nl_data_mio = nl_data[nl_data["unit"].str.contains("MIO_EUR")].reset_index(drop=True)


        # Get latest available year
        latest_year = nl_data_mio['TIME_PERIOD'].max()
        latest_data = nl_data_mio[nl_data_mio['TIME_PERIOD'] == latest_year]
        
        # Clean and standardize
        processed = latest_data[['geo', 'OBS_VALUE', 'unit', 'Geopolitical entity (reporting)']].copy()
        processed.columns = ['nuts_code', 'gdp_value', 'unit', 'region']
        processed['gdp_value'] = pd.to_numeric(processed['gdp_value'], errors='coerce')

        if processed.isna().any().any():
            logger.warning("NAN values in GDP data")
            len_before = len(processed)
            processed = processed.dropna()
            len_after = len(processed)
            logger.warning(f"Dropped {len_before - len_after} NAN values in GDP data")

        
        logger.info(f"Processed GDP data: {len(processed)} regions for year {latest_year}")
        return processed
    
    def _process_freight_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process freight dataset to extract NUTS L3 values."""
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
        
        logger.info(f"Processed freight data: {len(aggregated)} regions for year {latest_year}")
        logger.info(f"Total NUTS freight volume: {aggregated['freight_value'].sum():,.0f} tonnes")
        return aggregated
    
    def _process_hrst_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process HRST dataset to extract NUTS L2 values."""
        # Filter for Netherlands and NUTS L2 (4 character codes starting with NL)
        nl_data = df[df['geo'].str.startswith('NL') & df['geo'].str.len().eq(4)]
        
        # Get latest available year
        latest_year = nl_data['TIME_PERIOD'].max()
        latest_data = nl_data[nl_data['TIME_PERIOD'] == latest_year]
        
        # Clean and standardize
        processed = latest_data[['geo', 'OBS_VALUE', 'unit', 'Geopolitical entity (reporting)']].copy()
        processed.columns = ['nuts_code', 'hrst_value', 'unit', 'region']
        processed['hrst_value'] = pd.to_numeric(processed['hrst_value'], errors='coerce')
        
        if processed.isna().any().any():
            logger.warning("NAN values in HRST data")
            len_before = len(processed)
            processed = processed.dropna()
            len_after = len(processed)
            logger.warning(f"Dropped {len_before - len_after} NAN values in HRST data")
        
        logger.info(f"Processed HRST data: {len(processed)} regions for year {latest_year}")
        return processed
    
    def _load_maritime_freight_data(self) -> pd.DataFrame:
        """Load enhanced freight data using shared processor."""
        logger.info("Loading freight data using shared processor")
        
        try:
            nuts_freight_data, enhanced_datasets = self.freight_processor.load_and_process_freight_data()
            
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
    """Handles mapping economic data to NUTS geometries at different levels."""
    
    def __init__(self, config: ProjectConfig):
        self.config = config
        
    def load_nuts_shapefile(self, nuts_level: str) -> gpd.GeoDataFrame:
        """Load and prepare NUTS shapefile for specified level."""
        nuts_filename = getattr(self.config, f'nuts_{nuts_level}_file_path', None)
        if nuts_filename is None:
            raise ValueError(f"NUTS {nuts_level.upper()} file path not found in config")
            
        nuts_path = self.config.data_dir / nuts_filename
        logger.info(f"Loading NUTS {nuts_level.upper()} shapefile from {nuts_path}")
        
        nuts_gdf = gpd.read_file(nuts_path)
        
        # Transform to target CRS
        target_crs = rasterio.crs.CRS.from_string(self.config.target_crs)
        if nuts_gdf.crs != target_crs:
            nuts_gdf = nuts_gdf.to_crs(target_crs)
            logger.info(f"Transformed NUTS shapefile to {target_crs}")
            
        logger.info(f"Loaded {len(nuts_gdf)} NUTS {nuts_level.upper()} regions")
        return nuts_gdf
    
    def join_economic_data(self, nuts_gdfs: Dict[str, gpd.GeoDataFrame], 
                          economic_data: Dict[str, pd.DataFrame]) -> Dict[str, gpd.GeoDataFrame]:
        """Join economic datasets with NUTS geometries at appropriate levels."""
        result_gdfs = {}
        
        loading_nuts_mapping_path = os.path.join(self.config.data_dir, "Mapping_NL_NUTS_2021_2024.xlsx")
        mapping_df = pd.read_excel(loading_nuts_mapping_path) if os.path.exists(loading_nuts_mapping_path) else None

        # Process each dataset with its corresponding NUTS level
        for dataset_name, df in economic_data.items():
            # Get dataset configuration
            dataset_config = self.config.economic_datasets.get(dataset_name, {})
            nuts_level = dataset_config.get('nuts_level', 'l3')
            
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
            
            # Create a copy and standardize the value column name
            df_renamed = df.copy()
            
            # Standardize value column naming
            value_cols = [col for col in df_renamed.columns if col.endswith('_value')]
            if value_cols:
                original_value_col = value_cols[0]
                df_renamed = df_renamed.rename(columns={
                    original_value_col: f'{dataset_name}_value'
                })
            
            # Apply NUTS mapping if available and needed (mainly for L3 data)
            if mapping_df is not None and nuts_level == 'l3':
                for idx, row in df_renamed.iterrows():
                    if row['nuts_code'] in mapping_df[2021].values:
                        mapping_idx = mapping_df.index[mapping_df[2021] == row['nuts_code']].tolist()
                        if mapping_idx:
                            df_renamed.at[idx, 'nuts_code'] = mapping_df.at[mapping_idx[0], 2024]
            
            # Perform the merge
            merged_gdf = nuts_gdf.merge(
                df_renamed, 
                left_on=nuts_code_col, 
                right_on='nuts_code', 
                how='left',
                suffixes=('', f'_{dataset_name}')
            )
            
            # Fill missing values with 0 for economic columns
            economic_columns = [col for col in merged_gdf.columns if col.endswith('_value')]
            merged_gdf[economic_columns] = merged_gdf[economic_columns].fillna(0)
            
            result_gdfs[dataset_name] = merged_gdf
            
            logger.info(f"Joined {dataset_name} data: {len(economic_columns)} variables")
            logger.debug(f"Economic columns for {dataset_name}: {economic_columns}")
        
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
    Relevance Layer Implementation
    =============================
    
    Processes economic relevance using NUTS L3 data:
    - GDP (Gross Domestic Product)
    - Road freight loading 
    - Road freight unloading
    
    Uses exposition layer for spatial downsampling to 30x30m raster.
    """
    
    def __init__(self, config: ProjectConfig):
        self.config = config
        
        self.data_loader = EconomicDataLoader(config)
        self.nuts_mapper = NUTSDataMapper(config)
        self.transformer = RasterTransformer(
            target_crs=config.target_crs,
            config=config
        )

        self.distributor = EconomicDistributor(config, self.transformer)
        
        self.exposition_layer = ExpositionLayer(config)
        
        self.visualizer = LayerVisualizer(config)
        
        self.normalizer = AdvancedDataNormalizer(NormalizationStrategy.ECONOMIC_OPTIMIZED)
        
        logger.info("Initialized Relevance Layer")
    
    def load_and_process_economic_data(self) -> Dict[str, gpd.GeoDataFrame]:
        """Load economic datasets and join with NUTS geometries at appropriate levels."""
        
        economic_data = self.data_loader.load_economic_datasets()
        
        if not economic_data:
            raise ValueError("No economic datasets could be loaded. Please check data paths and files.")
        
        required_nuts_levels = set()
        for dataset_name in economic_data.keys():
            dataset_config = getattr(self.config, 'economic_datasets', {})
            nuts_level = dataset_config.get(dataset_name, {}).get('nuts_level', 'l3')
            required_nuts_levels.add(nuts_level)
        
        nuts_gdfs = {}
        for nuts_level in required_nuts_levels:
            nuts_gdfs[nuts_level] = self.nuts_mapper.load_nuts_shapefile(nuts_level)
        
        joined_gdfs = self.nuts_mapper.join_economic_data(nuts_gdfs, economic_data)
        
        return joined_gdfs
    
    def calculate_relevance(self, layers_to_generate: List[str] = None) -> Tuple[Dict[str, np.ndarray], dict]:
        """Calculate economic relevance layers for each dataset."""
        logger.info("Calculating economic relevance layers")
        
        nuts_economic_gdfs = self.load_and_process_economic_data()
        
        # Get exposition metadata without expensive calculation - use config-based approach
        exposition_meta = self._get_exposition_metadata()
        logger.info(f"Using exposition metadata for spatial distribution")
        
        if layers_to_generate:
            filtered_gdfs = {name: gdf for name, gdf in nuts_economic_gdfs.items() if name in layers_to_generate}
            logger.info(f"Generating only requested layers: {list(filtered_gdfs.keys())}")
            nuts_economic_gdfs = filtered_gdfs
        else:
            logger.info(f"Generating all available layers: {list(nuts_economic_gdfs.keys())}")
        
        relevance_layers = {}
        
        for dataset_name, nuts_gdf in nuts_economic_gdfs.items():
            logger.info(f"Processing {dataset_name} dataset")
            
            available_economic_columns = [col for col in nuts_gdf.columns if col.endswith('_value')]
            
            if not available_economic_columns:
                logger.warning(f"No economic columns found for {dataset_name}")
                continue
            
            variable = dataset_name
            
            economic_raster, raster_meta = self.distributor.rasterize_nuts_regions(
                nuts_gdf, exposition_meta, variable
            )
            
            # Get or create economic exposition layer for this dataset
            economic_exposition_data = self._get_economic_exposition_layer(dataset_name)
            logger.info(f"Loaded economic exposition layer for {dataset_name} - "
                       f"Min: {np.nanmin(economic_exposition_data)}, Max: {np.nanmax(economic_exposition_data)}, "
                       f"Non-zero pixels: {np.sum(economic_exposition_data > 0)}")
            
            if economic_exposition_data.shape != economic_raster.shape:
                logger.warning(f"Shape mismatch between economic exposition and economic raster for {dataset_name}")
                logger.warning(f"Economic exposition shape: {economic_exposition_data.shape}, Economic raster shape: {economic_raster.shape}")
                economic_exposition_data = self.transformer.ensure_alignment(
                    economic_exposition_data, exposition_meta['transform'], 
                    raster_meta['transform'], economic_raster.shape,
                    self.config.resampling_method
                )
            
            enhanced_datasets = None
            if variable == 'freight':
                if hasattr(self.data_loader, 'enhanced_freight_datasets'):
                    enhanced_datasets = self.data_loader.enhanced_freight_datasets
                    logger.info("Using enhanced freight datasets with Zeevart maritime data")
                else:
                    logger.info("No enhanced freight datasets available, using standard NUTS distribution")
            
            distributed_raster = self.distributor.distribute_with_exposition(
                economic_raster, economic_exposition_data, enhanced_datasets, raster_meta
            )
            
            normalized_raster = self._normalize_economic_layer(distributed_raster)
            
            relevance_layers[variable] = normalized_raster
            
        if not relevance_layers:
            raise ValueError("No relevance layers could be calculated")
            
        logger.info(f"Processed {len(relevance_layers)} economic variables: {list(relevance_layers.keys())}")
        
        economic_datasets_config = getattr(self.config, 'economic_datasets', {})
        weights = {}
        
        for variable in relevance_layers.keys():
            dataset_config = economic_datasets_config.get(variable, {})
            weights[variable] = dataset_config.get('weight', 1.0 / len(relevance_layers))
        
        logger.info(f"Using weights for variables: {weights}")
        
        combined_relevance = np.zeros_like(list(relevance_layers.values())[0])
        total_weight = 0
        for variable, weight in weights.items():
            if variable in relevance_layers:
                combined_relevance += weight * relevance_layers[variable]
                total_weight += weight
                
        if total_weight > 0 and abs(total_weight - 1.0) > 1e-6:
            combined_relevance /= total_weight
            logger.info(f"Normalized combined layer by total weight: {total_weight}")
                
        relevance_layers['combined'] = combined_relevance
        
        logger.info("Completed relevance layer calculation")
        logger.info(f"Final combined relevance layer - "
                   f"Min: {np.nanmin(combined_relevance)}, Max: {np.nanmax(combined_relevance)}, "
                   f"Non-zero pixels: {np.sum(combined_relevance > 0)}")
        
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
