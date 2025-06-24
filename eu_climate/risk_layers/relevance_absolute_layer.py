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
    """Handles absolute value distribution with mass conservation."""
    
    def __init__(self, config: ProjectConfig, transformer: RasterTransformer):
        self.config = config
        self.transformer = transformer
        
    def distribute_absolute_values(self, economic_raster: np.ndarray,
                                 exposition_layer: np.ndarray,
                                 land_mask: np.ndarray,
                                 enhanced_freight_datasets: dict = None,
                                 reference_meta: dict = None) -> np.ndarray:
        """Distribute absolute economic values ensuring mass conservation."""
        logger.info("Distributing absolute economic values with mass conservation")
        
        if reference_meta:
            self._reference_meta = reference_meta
        
        if not self.transformer.validate_alignment(
            economic_raster, None, exposition_layer, None
        ):
            logger.warning("Raster alignment validation failed")
        
        original_total = self._calculate_original_total(economic_raster)
        logger.info(f"Original total value: {original_total:,.0f}")
        
        distributed_absolute = self._apply_nuts_absolute_distribution(
            economic_raster, exposition_layer
        )
        
        if enhanced_freight_datasets and 'port_freight' in enhanced_freight_datasets:
            logger.info("Applying enhanced port freight data")
            distributed_absolute = self._apply_port_freight_enhancement(
                distributed_absolute, enhanced_freight_datasets['port_freight']
            )
        
        distributed_total = np.sum(distributed_absolute[~np.isnan(distributed_absolute)])
        logger.info(f"Distributed total before conservation: {distributed_total:,.0f}")
        
        conserved_distribution = self._apply_mass_conservation(
            distributed_absolute, original_total, land_mask
        )
        
        final_total = np.sum(conserved_distribution[~np.isnan(conserved_distribution)])
        logger.info(f"Final conserved total: {final_total:,.0f}")
        logger.info(f"Mass conservation accuracy: {(final_total/original_total)*100:.6f}%")
        
        return conserved_distribution
    
    def _calculate_original_total(self, economic_raster: np.ndarray) -> float:
        """Calculate total value from original NUTS raster."""
        unique_values = np.unique(economic_raster)
        unique_values = unique_values[unique_values > 0]
        return float(np.sum(unique_values))
    
    def _apply_nuts_absolute_distribution(self, economic_raster: np.ndarray,
                                        exposition_layer: np.ndarray) -> np.ndarray:
        """Apply NUTS-based absolute distribution preserving original values."""
        distributed = np.zeros_like(economic_raster, dtype=np.float32)
        
        unique_values = np.unique(economic_raster)
        unique_values = unique_values[unique_values > 0]
        
        for region_value in unique_values:
            region_mask = economic_raster == region_value
            region_exposition = exposition_layer * region_mask
            total_exposition = np.sum(region_exposition)
            
            if total_exposition > 0:
                distributed += (region_exposition / total_exposition) * region_value
            else:
                region_cells = np.sum(region_mask)
                if region_cells > 0:
                    distributed[region_mask] = region_value / region_cells
        
        return distributed
    
    def _apply_port_freight_enhancement(self, distributed_base: np.ndarray,
                                      port_freight_data: pd.DataFrame) -> np.ndarray:
        """Apply port freight enhancement preserving absolute values."""
        if port_freight_data.empty:
            logger.info("No port freight data available for enhancement")
            return distributed_base

        logger.info(f"Enhancing with {len(port_freight_data)} port freight entries")
        
        port_raster = self._rasterize_port_freight(port_freight_data, distributed_base.shape)
        enhanced_distributed = distributed_base.copy()
        port_mask = (port_raster > 0) & (~np.isnan(port_raster))
        
        if np.any(port_mask):
            enhanced_distributed[port_mask] += port_raster[port_mask]
            logger.info(f"Added port freight to {np.sum(port_mask)} port pixels")
        
        return enhanced_distributed
    
    def _rasterize_port_freight(self, port_freight_data: pd.DataFrame,
                               target_shape: Tuple[int, int]) -> np.ndarray:
        """Rasterize port freight data using high-resolution approach."""
        try:
            import rasterio.features
            
            port_raster = np.zeros(target_shape, dtype=np.float32)
            
            if hasattr(self, '_reference_meta') and self._reference_meta:
                base_transform = self._reference_meta['transform']
            else:
                logger.warning("No reference metadata available for port rasterization")
                return port_raster
            
            target_resolution = self.config.target_resolution
            port_resolution = max(1.0, target_resolution / 2.0)
            
            hr_transform = rasterio.Affine(
                port_resolution, 0.0, base_transform.c,
                0.0, -port_resolution, base_transform.f
            )
            
            hr_width = int(target_shape[1] * (target_resolution / port_resolution))
            hr_height = int(target_shape[0] * (target_resolution / port_resolution))
            hr_shape = (hr_height, hr_width)
            hr_port_raster = np.zeros(hr_shape, dtype=np.float32)
            
            for _, row in port_freight_data.iterrows():
                if 'geometry' in row and 'freight_value' in row:
                    freight_value = row.get('freight_value', 0)
                    
                    if freight_value > 0 and row['geometry'] is not None:
                        port_area_square_meters = row['geometry'].area
                        
                        if port_area_square_meters > 0:
                            freight_per_square_meter = freight_value / port_area_square_meters
                            pixel_area_square_meters = port_resolution * port_resolution
                            freight_per_pixel = freight_per_square_meter * pixel_area_square_meters
                            
                            single_port_raster = rasterio.features.rasterize(
                                [(row['geometry'], freight_per_pixel)],
                                out_shape=hr_shape,
                                transform=hr_transform,
                                fill=0,
                                dtype=np.float32,
                                merge_alg=rasterio.enums.MergeAlg.add
                            )
                            
                            hr_port_raster += single_port_raster
            
            from rasterio.warp import reproject, Resampling
            
            reproject(
                source=hr_port_raster,
                destination=port_raster,
                src_transform=hr_transform,
                src_crs=self.config.target_crs,
                dst_transform=base_transform,
                dst_crs=self.config.target_crs,
                resampling=Resampling.sum
            )
            
            logger.info(f"Rasterized ports: total freight = {port_raster.sum():,.0f}")
            return port_raster
            
        except Exception as e:
            logger.error(f"Error rasterizing port freight data: {e}")
            return np.zeros(target_shape, dtype=np.float32)
    
    def _apply_mass_conservation(self, distributed_values: np.ndarray,
                               original_total: float,
                               land_mask: np.ndarray) -> np.ndarray:
        """Apply mass conservation ensuring total value preservation."""
        distributed_total = np.sum(distributed_values[~np.isnan(distributed_values)])
        value_difference = original_total - distributed_total
        
        logger.info(f"Value difference to redistribute: {value_difference:,.0f}")
        
        if abs(value_difference) < 1e-6:
            logger.info("No significant value difference, returning original distribution")
            return distributed_values
        
        valid_cells_mask = (land_mask == 1) & (~np.isnan(distributed_values))
        valid_cell_count = np.sum(valid_cells_mask)
        
        if valid_cell_count == 0:
            logger.warning("No valid cells found for mass conservation")
            return distributed_values
        
        cell_area_square_meters = self.config.target_resolution * self.config.target_resolution
        difference_per_cell = value_difference / valid_cell_count
        
        logger.info(f"Redistributing {difference_per_cell:.6f} per cell across {valid_cell_count} valid cells")
        
        conserved_values = distributed_values.copy()
        conserved_values[valid_cells_mask] = np.maximum(
            0.0, conserved_values[valid_cells_mask] + difference_per_cell
        )
        
        return conserved_values


class AbsoluteEconomicDataLoader:
    """Enhanced economic data loader with debugging for absolute relevance layer."""
    
    def __init__(self, config: ProjectConfig):
        self.config = config
        self.data_dir = config.data_dir
        self.freight_processor = SharedFreightProcessor(config)
        
    def load_economic_datasets(self) -> Dict[str, pd.DataFrame]:
        """Load all economic datasets with enhanced debugging and error handling."""
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
        """Load GDP data with multiple path attempts."""
        # Try multiple potential GDP file paths
        potential_gdp_paths = [
            self.data_dir / "L3-estat_gdp.csv" / "estat_nama_10r_3gdp_en.csv",
            self.data_dir / "L3-estat_nama_10r_3gdp" / "estat_nama_10r_3gdp_en.csv", 
            self.data_dir / "L3_estat_nama_10r_3gdp" / "estat_nama_10r_3gdp_en.csv",
            self.data_dir / "estat_nama_10r_3gdp_en.csv",
            self.data_dir / "GDP" / "estat_nama_10r_3gdp_en.csv"
        ]
        
        for gdp_path in potential_gdp_paths:
            if gdp_path.exists():
                logger.info(f"Loading GDP dataset from {gdp_path}")
                try:
                    gdp_df = pd.read_csv(gdp_path)
                    datasets['gdp'] = self._process_gdp_data(gdp_df)
                    return True
                except Exception as e:
                    logger.error(f"Error loading GDP from {gdp_path}: {e}")
                    continue
            else:
                logger.debug(f"GDP path not found: {gdp_path}")
                
        logger.error("GDP dataset not found in any expected location")
        return False
    
    def _load_hrst_data(self, datasets: Dict[str, pd.DataFrame]) -> bool:
        """Load HRST data with enhanced debugging."""
        # Try multiple potential HRST file paths
        potential_hrst_paths = [
            self.data_dir / getattr(self.config, 'hrst_file_path', 'L2_estat_hrst_st_rcat_filtered_en/estat_hrst_st_rcat_filtered_en.csv'),
            self.data_dir / "L2_estat_hrst_st_rcat_filtered_en" / "estat_hrst_st_rcat_filtered_en.csv",
            self.data_dir / "L2-estat_hrst_st_rcat_filtered_en" / "estat_hrst_st_rcat_filtered_en.csv",
            self.data_dir / "estat_hrst_st_rcat_filtered_en.csv",
            self.data_dir / "HRST" / "estat_hrst_st_rcat_filtered_en.csv"
        ]
        
        for hrst_path in potential_hrst_paths:
            if hrst_path.exists():
                logger.info(f"Loading HRST dataset from {hrst_path}")
                try:
                    hrst_df = pd.read_csv(hrst_path)
                    datasets['hrst'] = self._process_hrst_data(hrst_df)
                    return True
                except Exception as e:
                    logger.error(f"Error loading HRST from {hrst_path}: {e}")
                    continue
            else:
                logger.debug(f"HRST path not found: {hrst_path}")
                
        logger.error("HRST dataset not found in any expected location")
        return False
    
    def _load_freight_data_shared(self) -> Tuple[pd.DataFrame, Optional[Dict[str, pd.DataFrame]]]:
        """Load freight data using the shared two-stage processor."""
        logger.info("Loading freight data using shared processor (two-stage approach)")
        
        try:
            nuts_freight_data, enhanced_datasets = self.freight_processor.load_and_process_freight_data()
            
            if nuts_freight_data.empty:
                logger.error("No NUTS freight data loaded from shared processor")
                return pd.DataFrame(), None
            
            logger.info(f"Loaded NUTS freight data: {len(nuts_freight_data)} regions")
            logger.info(f"Enhanced datasets available: {enhanced_datasets is not None}")
            
            return nuts_freight_data, enhanced_datasets
            
        except Exception as e:
            logger.error(f"Error loading freight data with shared processor: {e}")
            return pd.DataFrame(), None
    
    def _process_gdp_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process GDP dataset with enhanced validation."""
        logger.info(f"Processing GDP data with {len(df)} total rows")
        
        # Filter for Netherlands (NL) and NUTS L3 regions
        nl_data = df[df['geo'].str.startswith('NL') & df['geo'].str.len().eq(5)]
        logger.info(f"Found {len(nl_data)} Netherlands NUTS L3 entries")
        
        # Filter for million EUR units
        nl_data_mio = nl_data[nl_data["unit"].str.contains("MIO_EUR", na=False)].reset_index(drop=True)
        logger.info(f"Found {len(nl_data_mio)} entries with MIO_EUR units")
        
        if nl_data_mio.empty:
            logger.error("No GDP data found with MIO_EUR units")
            return pd.DataFrame()
        
        # Get latest available year
        latest_year = nl_data_mio['TIME_PERIOD'].max()
        latest_data = nl_data_mio[nl_data_mio['TIME_PERIOD'] == latest_year]
        logger.info(f"Using latest year {latest_year} with {len(latest_data)} entries")
        
        # Clean and standardize
        processed = latest_data[['geo', 'OBS_VALUE', 'unit', 'Geopolitical entity (reporting)']].copy()
        processed.columns = ['nuts_code', 'gdp_value', 'unit', 'region']
        processed['gdp_value'] = pd.to_numeric(processed['gdp_value'], errors='coerce')
        
        # Remove NaN values
        len_before = len(processed)
        processed = processed.dropna()
        len_after = len(processed)
        if len_before != len_after:
            logger.warning(f"Dropped {len_before - len_after} NaN values from GDP data")
        
        # Convert millions to actual values (keep as millions for readability)
        total_gdp = processed['gdp_value'].sum()
        logger.info(f"Processed GDP data: {len(processed)} regions, total GDP: {total_gdp:,.0f} million EUR")
        
        return processed
    
    def _process_hrst_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process HRST dataset with enhanced validation and debugging."""
        logger.info(f"Processing HRST data with {len(df)} total rows")
        
        # Filter for Netherlands and NUTS L2 (4 character codes starting with NL)
        nl_data = df[df['geo'].str.startswith('NL') & df['geo'].str.len().eq(4)]
        logger.info(f"Found {len(nl_data)} Netherlands NUTS L2 entries")
        
        if nl_data.empty:
            logger.error("No HRST data found for Netherlands NUTS L2 regions")
            return pd.DataFrame()
        
        # Get latest available year
        latest_year = nl_data['TIME_PERIOD'].max()
        latest_data = nl_data[nl_data['TIME_PERIOD'] == latest_year]
        logger.info(f"Using latest year {latest_year} with {len(latest_data)} entries")
        
        # Clean and standardize
        processed = latest_data[['geo', 'OBS_VALUE', 'unit', 'Geopolitical entity (reporting)']].copy()
        processed.columns = ['nuts_code', 'hrst_value', 'unit', 'region']
        processed['hrst_value'] = pd.to_numeric(processed['hrst_value'], errors='coerce')
        
        # Remove NaN values
        len_before = len(processed)
        processed = processed.dropna()
        len_after = len(processed)
        if len_before != len_after:
            logger.warning(f"Dropped {len_before - len_after} NaN values from HRST data")
        
        # CRITICAL FIX: Convert THS_PER (thousands of persons) to actual persons
        if not processed.empty:
            unique_units = processed['unit'].unique()
            logger.info(f"HRST units found: {unique_units}")
            
            if 'THS_PER' in unique_units:
                logger.info("Converting HRST data from thousands of persons to actual persons")
                processed.loc[processed['unit'] == 'THS_PER', 'hrst_value'] *= 1000
                processed.loc[processed['unit'] == 'THS_PER', 'unit'] = 'PER'
                logger.info("HRST unit conversion completed: THS_PER -> PER (multiplied by 1000)")
            
            total_hrst = processed['hrst_value'].sum()
            max_hrst = processed['hrst_value'].max()
            min_hrst = processed['hrst_value'].min()
            logger.info(f"HRST values after conversion - Total: {total_hrst:,.0f}, Max: {max_hrst:,.0f}, Min: {min_hrst:,.0f}")
        
        logger.info(f"Processed HRST data: {len(processed)} regions")
        return processed


class RelevanceAbsoluteLayer:
    """
    Absolute Relevance Layer Implementation
    =====================================
    
    Processes economic relevance preserving absolute values with mass conservation:
    - GDP (Gross Domestic Product) 
    - Freight (combined loading, unloading, maritime)
    - HRST (Human Resources in Science and Technology)
    - Population (total population count)
    
    Uses exposition layer weights for spatial distribution while ensuring
    total values sum to original NUTS totals.
    """
    
    def __init__(self, config: ProjectConfig):
        self.config = config
        
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
        """Load economic datasets including population for absolute value processing."""
        economic_datasets = self.economic_data_loader.load_economic_datasets()
        
        if not economic_datasets:
            raise ValueError("No economic datasets could be loaded for absolute processing")
        
        required_nuts_levels = set()
        dataset_nuts_mapping = {
            'gdp': 'l3',       # GDP is available at NUTS L3 level
            'freight': 'l3',   # Freight is available at NUTS L3 level  
            'hrst': 'l2'       # HRST is available at NUTS L2 level
        }
        
        for dataset_name in economic_datasets.keys():
            nuts_level = dataset_nuts_mapping.get(dataset_name, 'l3')
            required_nuts_levels.add(nuts_level)
            logger.info(f"Dataset {dataset_name} mapped to NUTS level {nuts_level}")
        
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
        """Calculate absolute economic relevance layers preserving original values."""
        logger.info("Calculating absolute economic relevance layers")
        
        nuts_economic_gdfs = self.load_and_process_absolute_economic_data()
        exposition_meta = self._get_exposition_metadata()
        
        target_indicators = ['gdp', 'freight', 'hrst']
        
        if layers_to_generate:
            target_indicators = [indicator for indicator in target_indicators if indicator in layers_to_generate]
            logger.info(f"Generating only requested indicators: {target_indicators}")
        
        available_indicators = [indicator for indicator in target_indicators if indicator in nuts_economic_gdfs]
        logger.info(f"Processing available indicators: {available_indicators}")
        
        land_mask = self._load_land_mask(exposition_meta)
        absolute_relevance_layers = {}
        
        for indicator_name in available_indicators:
            nuts_gdf = nuts_economic_gdfs[indicator_name]
            
            logger.info(f"Processing {indicator_name} for absolute relevance")
            
            economic_raster, raster_meta = self._rasterize_nuts_regions_absolute(
                nuts_gdf, exposition_meta, indicator_name
            )
            
            economic_exposition_data = self._get_economic_exposition_layer(indicator_name)
            
            if economic_exposition_data.shape != economic_raster.shape:
                logger.warning(f"Shape mismatch for {indicator_name}, ensuring alignment")
                economic_exposition_data = self.transformer.ensure_alignment(
                    economic_exposition_data, exposition_meta['transform'],
                    raster_meta['transform'], economic_raster.shape,
                    self.config.resampling_method
                )
            
            enhanced_datasets = None
            if indicator_name == 'freight':
                if hasattr(self.economic_data_loader, 'enhanced_freight_datasets'):
                    enhanced_datasets = self.economic_data_loader.enhanced_freight_datasets
                    logger.info("Using enhanced freight datasets for absolute distribution")
                else:
                    logger.warning("Enhanced freight datasets not available in economic data loader")
            
            absolute_distributed_raster = self.absolute_distributor.distribute_absolute_values(
                economic_raster, economic_exposition_data, land_mask,
                enhanced_datasets, raster_meta
            )
            
            absolute_relevance_layers[indicator_name] = absolute_distributed_raster
            
            # Log final statistics for this indicator
            final_total = np.sum(absolute_distributed_raster[~np.isnan(absolute_distributed_raster)])
            max_value = np.nanmax(absolute_distributed_raster)
            min_value = np.nanmin(absolute_distributed_raster[absolute_distributed_raster > 0])
            logger.info(f"Final {indicator_name} distribution - Total: {final_total:,.0f}, Max: {max_value:,.6f}, Min: {min_value:,.6f}")
        
        if not absolute_relevance_layers:
            raise ValueError("No absolute relevance layers could be calculated")
        
        logger.info(f"Completed absolute relevance calculation for {len(absolute_relevance_layers)} indicators")
        
        return absolute_relevance_layers, exposition_meta
    
    def _get_exposition_metadata(self) -> dict:
        """Get exposition metadata for consistent spatial alignment."""
        default_path = Path(self.config.output_dir) / "exposition" / "tif" / "exposition_layer.tif"
        
        if default_path.exists():
            with rasterio.open(default_path) as src:
                return src.meta
        else:
            logger.info("Generating metadata from config for absolute relevance")
            nuts_l3_path = self.config.data_dir / self.config.nuts_l3_file_path
            reference_bounds = self.transformer.get_reference_bounds(nuts_l3_path)
            
            width = int((reference_bounds[2] - reference_bounds[0]) / self.config.target_resolution)
            height = int((reference_bounds[3] - reference_bounds[1]) / self.config.target_resolution)
            
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