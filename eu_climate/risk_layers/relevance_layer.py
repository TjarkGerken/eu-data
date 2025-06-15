import rasterio
import rasterio.features
import rasterio.warp
import geopandas as gpd
import pandas as pd
from typing import Tuple, Dict
import numpy as np
from pathlib import Path
import os

from eu_climate.config.config import ProjectConfig
from eu_climate.utils.utils import setup_logging
from eu_climate.utils.conversion import RasterTransformer
from eu_climate.utils.visualization import LayerVisualizer
from eu_climate.risk_layers.exposition_layer import ExpositionLayer

logger = setup_logging(__name__)


class EconomicDataLoader:
    """Handles loading and preprocessing of NUTS L3 economic datasets."""
    
    def __init__(self, config: ProjectConfig):
        self.config = config
        self.data_dir = config.data_dir
        
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
            
        # Road freight loading
        loading_path = self.data_dir / "L3-estat_road_go_loading" / "estat_road_go_na_rl3g_en.csv"
        if loading_path.exists():
            logger.info(f"Loading freight loading dataset from {loading_path}")
            loading_df = pd.read_csv(loading_path)
            datasets['freight_loading'] = self._process_freight_data(loading_df)
        else:
            logger.error(f"Freight loading dataset not found: {loading_path}")
            
        # Road freight unloading
        unloading_path = self.data_dir / "L3-estat_road_go_unloading" / "estat_road_go_na_ru3g_en.csv"
        if unloading_path.exists():
            logger.info(f"Loading freight unloading dataset from {unloading_path}")
            unloading_df = pd.read_csv(unloading_path)
            datasets['freight_unloading'] = self._process_freight_data(unloading_df)
        else:
            logger.error(f"Freight unloading dataset not found: {unloading_path}")
            
        # HRST dataset
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
        
        # Get latest available year and aggregate all goods types
        latest_year = nl_data['TIME_PERIOD'].max()
        latest_data = nl_data[nl_data['TIME_PERIOD'] == latest_year]
        
        # Aggregate by NUTS region (sum across all goods categories)
        aggregated = latest_data.groupby('geo').agg({
            'OBS_VALUE': 'sum',
            'unit': 'first', 
            'Geopolitical entity (reporting)': 'first'
        }).reset_index()
        
        # Clean and standardize
        aggregated.columns = ['nuts_code', 'freight_value', 'unit', 'region']
        aggregated['freight_value'] = pd.to_numeric(aggregated['freight_value'], errors='coerce')
        aggregated = aggregated.dropna()
        
        logger.info(f"Processed freight data: {len(aggregated)} regions for year {latest_year}")
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
                                 exposition_layer: np.ndarray) -> np.ndarray:
        """Distribute economic values using exposition layer as weights."""
        logger.info("Distributing economic values using exposition layer")
        
        # Ensure alignment
        if economic_raster.shape != exposition_layer.shape:
            raise ValueError(f"Shape mismatch: economic {economic_raster.shape} "
                           f"vs exposition {exposition_layer.shape}")
        
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
                    
        logger.info(f"Distributed economic values: min={np.nanmin(distributed)}, "
                   f"max={np.nanmax(distributed)}, mean={np.nanmean(distributed)}")
        
        return distributed


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
        
        logger.info("Initialized Relevance Layer")
    
    def load_and_process_economic_data(self) -> Dict[str, gpd.GeoDataFrame]:
        """Load economic datasets and join with NUTS geometries at appropriate levels."""
        # Load economic datasets
        economic_data = self.data_loader.load_economic_datasets()
        
        if not economic_data:
            raise ValueError("No economic datasets could be loaded. Please check data paths and files.")
        
        # Determine which NUTS levels are needed
        required_nuts_levels = set()
        for dataset_name in economic_data.keys():
            dataset_config = getattr(self.config, 'economic_datasets', {}).get(dataset_name, {})
            nuts_level = dataset_config.get('nuts_level', 'l3')
            required_nuts_levels.add(nuts_level)
        
        # Load NUTS shapefiles for required levels
        nuts_gdfs = {}
        for nuts_level in required_nuts_levels:
            nuts_gdfs[nuts_level] = self.nuts_mapper.load_nuts_shapefile(nuts_level)
        
        # Join economic data with appropriate NUTS levels
        joined_gdfs = self.nuts_mapper.join_economic_data(nuts_gdfs, economic_data)
        
        return joined_gdfs
    
    def calculate_relevance(self) -> Tuple[Dict[str, np.ndarray], dict]:
        """Calculate economic relevance layers for each dataset."""
        logger.info("Calculating economic relevance layers")
        
        # Load and process economic data
        nuts_economic_gdfs = self.load_and_process_economic_data()
        
        # Get default exposition layer metadata for reference
        default_exposition_data, exposition_meta = self.exposition_layer.calculate_exposition()
        logger.info(f"Using default exposition layer metadata for spatial distribution")
        
        # Process each dataset separately since they may have different NUTS levels and exposition weights
        relevance_layers = {}
        
        for dataset_name, nuts_gdf in nuts_economic_gdfs.items():
            logger.info(f"Processing {dataset_name} dataset")
            
            # Get available economic columns for this dataset
            available_economic_columns = [col for col in nuts_gdf.columns if col.endswith('_value')]
            
            if not available_economic_columns:
                logger.warning(f"No economic columns found for {dataset_name}")
                continue
            
            # Extract the variable name (should match dataset_name)
            variable = dataset_name
            
            # Rasterize NUTS regions with economic values using exposition metadata
            economic_raster, raster_meta = self.distributor.rasterize_nuts_regions(
                nuts_gdf, exposition_meta, variable
            )
            
            # Get the specific exposition layer for this economic dataset
            logger.info(f"Ensuring economic exposition layer exists for {dataset_name}")
            economic_exposition_path = self.exposition_layer.ensure_economic_exposition_layer_exists(dataset_name)
            
            # Load the economic-specific exposition layer
            with rasterio.open(economic_exposition_path) as src:
                economic_exposition_data = src.read(1).astype(np.float32)
                logger.info(f"Loaded economic exposition layer for {dataset_name} - "
                           f"Min: {np.nanmin(economic_exposition_data)}, Max: {np.nanmax(economic_exposition_data)}, "
                           f"Non-zero pixels: {np.sum(economic_exposition_data > 0)}")
            
            # Ensure alignment between economic raster and economic exposition layer
            if economic_exposition_data.shape != economic_raster.shape:
                logger.warning(f"Shape mismatch between economic exposition and economic raster for {dataset_name}")
                logger.warning(f"Economic exposition shape: {economic_exposition_data.shape}, Economic raster shape: {economic_raster.shape}")
                # Resample economic exposition to match economic raster
                economic_exposition_data = self.transformer.ensure_alignment(
                    economic_exposition_data, exposition_meta['transform'], 
                    raster_meta['transform'], economic_raster.shape,
                    self.config.resampling_method
                )
            
            # Distribute using the economic-specific exposition layer
            distributed_raster = self.distributor.distribute_with_exposition(
                economic_raster, economic_exposition_data
            )
            
            # Normalize to 0-1 range
            normalized_raster = self._normalize_economic_layer(distributed_raster)
            
            relevance_layers[variable] = normalized_raster
            
        if not relevance_layers:
            raise ValueError("No relevance layers could be calculated")
            
        logger.info(f"Processed {len(relevance_layers)} economic variables: {list(relevance_layers.keys())}")
        
        # Calculate combined relevance layer with configured weights
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
                
        # Normalize combined layer if total weight != 1.0
        if total_weight > 0 and abs(total_weight - 1.0) > 1e-6:
            combined_relevance /= total_weight
            logger.info(f"Normalized combined layer by total weight: {total_weight}")
                
        relevance_layers['combined'] = combined_relevance
        
        logger.info("Completed relevance layer calculation")
        logger.info(f"Final combined relevance layer - "
                   f"Min: {np.nanmin(combined_relevance)}, Max: {np.nanmax(combined_relevance)}, "
                   f"Non-zero pixels: {np.sum(combined_relevance > 0)}")
        
        return relevance_layers, exposition_meta
    
    def _normalize_economic_layer(self, data: np.ndarray) -> np.ndarray:
        """Normalize economic layer to 0-1 range."""
        valid_mask = (data > 0) & ~np.isnan(data)
        
        if not np.any(valid_mask):
            logger.warning("No valid economic data found for normalization")
            return data
            
        min_val = np.min(data[valid_mask])
        max_val = np.max(data[valid_mask])
        
        if max_val <= min_val:
            logger.warning("No variation in economic data")
            return np.where(valid_mask, 1.0, 0.0).astype(np.float32)
            
        normalized = np.zeros_like(data, dtype=np.float32)
        normalized[valid_mask] = (data[valid_mask] - min_val) / (max_val - min_val)
        
        return normalized
    
    def save_relevance_layers(self, relevance_layers: Dict[str, np.ndarray], 
                            meta: dict):
        """Save all relevance layers as separate GeoTIFF files."""
        
        output_dir = self.config.output_dir / "relevance"
            
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Update metadata for output
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
            
            # Remove existing file
            if output_path.exists():
                output_path.unlink()
                
            # Save as GeoTIFF
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
        
        # Load land mask for proper water/land separation
        land_mask = None
        try:
            with rasterio.open(self.config.land_mass_path) as src:
                # Transform land mask to match relevance layer resolution and extent
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
                    # Ensure proper data type (1=land, 0=water)
                    land_mask = (land_mask > 0).astype(np.uint8)
                    logger.info("Loaded and transformed land mask for relevance visualizations")
                else:
                    logger.warning("No metadata available for land mask transformation")
        except Exception as e:
            logger.warning(f"Could not load land mask for relevance visualizations: {e}")
        
        for layer_name, data in relevance_layers.items():
            if save_plots:
                # Create output path
                plot_path = output_dir / f"relevance_{layer_name}_plot.png"
                
                # Use unified visualizer for consistent styling with land mask
                self.visualizer.visualize_relevance_layer(
                    data=data,
                    meta=meta,
                    layer_name=layer_name,
                    output_path=plot_path,
                    land_mask=land_mask
                )
                
                logger.info(f"Saved {layer_name} relevance layer PNG to {plot_path}")

    def _add_nuts_labels(self, ax, nuts_gdf: gpd.GeoDataFrame):
        """Add NUTS code and region name labels to the plot at polygon centroids."""
        # Determine the NUTS code column
        nuts_code_col = None
        for col in ['NUTS_ID', 'nuts_id', 'geo', 'GEOCODE']:
            if col in nuts_gdf.columns:
                nuts_code_col = col
                break
        
        if nuts_code_col is None:
            logger.warning("Could not find NUTS code column for labeling")
            return
            
        # Determine region name column (prefer original shapefile column if available, otherwise use merged 'region')
        region_name_col = None
        for col in ['NAME_LATN', 'NUTS_NAME', 'region']:
            if col in nuts_gdf.columns:
                region_name_col = col
                break
                
        if region_name_col is None:
            logger.warning("Could not find region name column for labeling")
            region_name_col = nuts_code_col  # Fallback to just showing codes
        
        logger.debug(f"Using NUTS code column: {nuts_code_col}, region name column: {region_name_col}")
        
        # Add labels at polygon centroids
        for idx, row in nuts_gdf.iterrows():
            try:
                # Calculate centroid for label placement
                centroid = row.geometry.centroid
                
                # Get NUTS code and region name
                nuts_code = str(row[nuts_code_col])
                region_name = str(row[region_name_col]) if region_name_col != nuts_code_col else ""
                
                # Create label text
                if region_name and region_name != nuts_code and region_name.lower() != 'nan':
                    # Truncate long region names for better readability
                    if len(region_name) > 15:
                        region_name = region_name[:12] + "..."
                    label_text = f"{nuts_code}\n{region_name}"
                else:
                    label_text = nuts_code
                
                # Add text annotation with background for better readability
                ax.annotate(
                    label_text,
                    xy=(centroid.x, centroid.y),
                    xytext=(0, 0),
                    textcoords='offset points',
                    ha='center',
                    va='center',
                    fontsize=8,
                    fontweight='bold',
                    color='white',
                    bbox=dict(
                        boxstyle='round,pad=0.3',
                        facecolor='black',
                        alpha=0.7,
                        edgecolor='white',
                        linewidth=0.5
                    ),
                    zorder=15  # Ensure labels are on top of everything
                )
                
            except Exception as e:
                logger.debug(f"Could not add label for region {row.get(nuts_code_col, 'unknown')}: {e}")
                continue
    
    def _get_raster_extent(self, data: np.ndarray, meta: dict = None) -> Tuple[float, float, float, float]:
        """Get raster extent for proper plotting coordinate alignment."""
        if meta is not None and 'transform' in meta:
            # Use actual geospatial transform for proper coordinate alignment
            transform = meta['transform']
            height, width = data.shape
            
            # Calculate bounds using affine transform
            left = transform.c
            right = left + width * transform.a
            top = transform.f  
            bottom = top + height * transform.e
            
            return (left, right, bottom, top)
        else:
            # Fallback to simple pixel coordinates
            height, width = data.shape
            return (0, width, 0, height)
    
    def run_relevance_analysis(self, visualize: bool = True, 
                             export_individual_tifs: bool = True) -> Dict[str, np.ndarray]:
        """Main execution flow for relevance layer analysis."""
        logger.info("Starting relevance layer analysis")
        
        # Calculate relevance layers
        relevance_layers, meta = self.calculate_relevance()
        
        # Save all layers as TIFFs
        if export_individual_tifs:
            self.save_relevance_layers(relevance_layers, meta)
            
        # Create visualizations with metadata for proper coordinate alignment
        if visualize:
            self.visualize_relevance_layers(relevance_layers, meta)
            
        logger.info("Completed relevance layer analysis")
        return relevance_layers
