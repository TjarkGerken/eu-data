import rasterio
import rasterio.features
import rasterio.warp
import geopandas as gpd
import pandas as pd
from scipy import ndimage
from typing import Optional, Tuple, Dict, List
import numpy as np
from rasterio.enums import Resampling
from pathlib import Path
import logging
import matplotlib.pyplot as plt
import os

from eu_climate.config.config import ProjectConfig
from eu_climate.utils.utils import setup_logging, suppress_warnings
from eu_climate.utils.conversion import RasterTransformer
from eu_climate.utils.caching_wrappers import CacheAwareMethod, cache_calculation_method, cache_raster_method, cache_result_method
from eu_climate.utils.visualization import LayerVisualizer
from eu_climate.risk_layers.exposition_layer import ExpositionLayer

logger = setup_logging(__name__)


class EconomicDataLoader:
    """Handles loading and preprocessing of NUTS L3 economic datasets."""
    
    def __init__(self, config: ProjectConfig):
        self.config = config
        self.data_dir = config.data_dir
        
    def load_economic_datasets(self) -> Dict[str, pd.DataFrame]:
        """Load all three economic datasets and standardize format."""
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


class NUTSDataMapper:
    """Handles mapping economic data to NUTS L3 geometries."""
    
    def __init__(self, config: ProjectConfig):
        self.config = config
        
    def load_nuts_shapefile(self) -> gpd.GeoDataFrame:
        """Load and prepare NUTS L3 shapefile."""
        nuts_path = self.config.data_dir / "NUTS-L3-NL.shp"
        logger.info(f"Loading NUTS L3 shapefile from {nuts_path}")
        
        nuts_gdf = gpd.read_file(nuts_path)
        
        # Transform to target CRS
        target_crs = rasterio.crs.CRS.from_string(self.config.target_crs)
        if nuts_gdf.crs != target_crs:
            nuts_gdf = nuts_gdf.to_crs(target_crs)
            logger.info(f"Transformed NUTS shapefile to {target_crs}")
            
        logger.info(f"Loaded {len(nuts_gdf)} NUTS L3 regions")
        return nuts_gdf
    
    def join_economic_data(self, nuts_gdf: gpd.GeoDataFrame, 
                          economic_data: Dict[str, pd.DataFrame]) -> gpd.GeoDataFrame:
        """Join economic datasets with NUTS geometries."""
        result_gdf = nuts_gdf.copy()
        
        # Determine NUTS code column in shapefile
        nuts_code_col = None

        loading_nuts_mapping_path = os.path.join(self.config.data_dir, "Mapping_NL_NUTS_2021_2024.xlsx")

        mapping_df = pd.read_excel(loading_nuts_mapping_path)


        for col in ['NUTS_ID', 'nuts_id', 'geo', 'GEOCODE']:
            if col in result_gdf.columns:
                nuts_code_col = col
                break
        

        if nuts_code_col is None:
            raise ValueError("Could not find NUTS code column in shapefile")
            
        logger.info(f"Using NUTS code column: {nuts_code_col}")
        
        # Join each economic dataset with proper column naming
        for dataset_name, df in economic_data.items():
            logger.info(f"Joining {dataset_name} data")
            
            # Create a copy and rename the value column to be dataset-specific
            df_renamed = df.copy()
            
            if 'gdp_value' in df_renamed.columns:
                pass
            elif 'freight_value' in df_renamed.columns:
                df_renamed = df_renamed.rename(columns={
                    'freight_value': f'{dataset_name}_value'
                })

            for idx, row in df_renamed.iterrows():
                if row['nuts_code'] in mapping_df[2021].values:
                    mapping_idx = mapping_df.index[mapping_df[2021] == row['nuts_code']].tolist()
                    if mapping_idx:
                        df_renamed.at[idx, 'nuts_code'] = mapping_df.at[mapping_idx[0], 2024]

 
            # Perform the merge
            result_gdf = result_gdf.merge(
                df_renamed, 
                left_on=nuts_code_col, 
                right_on='nuts_code', 
                how='left',
                suffixes=('', f'_{dataset_name}')
            )
            
        # Fill missing values with 0 for all economic columns
        economic_columns = [col for col in result_gdf.columns if col.endswith('_value')]
        result_gdf[economic_columns] = result_gdf[economic_columns].fillna(0)
        
        logger.info(f"Joined economic data for {len(economic_columns)} variables")
        
        # Debug: print column info
        logger.debug(f"Final columns: {list(result_gdf.columns)}")
        logger.debug(f"Economic columns: {economic_columns}")
        
        return result_gdf


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
        
        # Initialize components
        self.data_loader = EconomicDataLoader(config)
        self.nuts_mapper = NUTSDataMapper(config)
        self.transformer = RasterTransformer(
            target_crs=config.target_crs,
            target_resolution=30.0,
            config=config
        )
        self.distributor = EconomicDistributor(config, self.transformer)
        
        # Initialize exposition layer
        self.exposition_layer = ExpositionLayer(config)
        
        # Initialize visualizer for unified styling
        self.visualizer = LayerVisualizer(config)
        
        logger.info("Initialized Relevance Layer")
    
    def load_and_process_economic_data(self) -> gpd.GeoDataFrame:
        """Load economic datasets and join with NUTS geometries."""
        # Load economic datasets
        economic_data = self.data_loader.load_economic_datasets()
        
        # Check if any datasets were loaded
        if not economic_data:
            raise ValueError("No economic datasets could be loaded. Please check data paths and files.")
        
        # Load NUTS shapefile
        nuts_gdf = self.nuts_mapper.load_nuts_shapefile()
        
        # Join data
        joined_gdf = self.nuts_mapper.join_economic_data(nuts_gdf, economic_data)
        
        return joined_gdf
    
    def calculate_relevance(self) -> Tuple[Dict[str, np.ndarray], dict]:
        """Calculate economic relevance layers for each dataset."""
        logger.info("Calculating economic relevance layers")
        
        # Load and process economic data
        nuts_economic_gdf = self.load_and_process_economic_data()
        
        # Get exposition layer (now properly masked to study area)
        exposition_data, exposition_meta = self.exposition_layer.calculate_exposition()
        logger.info(f"Using exposition layer for spatial distribution - "
                   f"Min: {np.nanmin(exposition_data)}, Max: {np.nanmax(exposition_data)}, "
                   f"Non-zero pixels: {np.sum(exposition_data > 0)}")
        
        # Determine which economic variables are available from the loaded data
        available_economic_columns = [col for col in nuts_economic_gdf.columns if col.endswith('_value')]
        economic_variables = [col.replace('_value', '') for col in available_economic_columns]
        
        if not economic_variables:
            raise ValueError("No economic variables found in processed data")
        
        logger.info(f"Processing {len(economic_variables)} economic variables: {economic_variables}")
        
        relevance_layers = {}
        
        for variable in economic_variables:
            logger.info(f"Processing {variable}")
            
            # Rasterize NUTS regions with economic values using exposition metadata
            economic_raster, raster_meta = self.distributor.rasterize_nuts_regions(
                nuts_economic_gdf, exposition_meta, variable
            )
            
            # Distribute using exposition layer (which is now properly masked)
            distributed_raster = self.distributor.distribute_with_exposition(
                economic_raster, exposition_data
            )
            
            # Normalize to 0-1 range
            normalized_raster = self._normalize_economic_layer(distributed_raster)
            
            relevance_layers[variable] = normalized_raster
            
        # Calculate combined relevance layer with dynamic weights
        weights = getattr(self.config, 'relevance_weights', {})
        
        # If no weights specified or weights don't match variables, use equal weights
        if not weights or not all(var in weights for var in economic_variables):
            equal_weight = 1.0 / len(economic_variables)
            weights = {var: equal_weight for var in economic_variables}
            logger.info(f"Using equal weights for variables: {weights}")
        
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
                            meta: dict, output_dir: Optional[Path] = None):
        """Save all relevance layers as separate GeoTIFF files."""
        if output_dir is None:
            output_dir = self.config.output_dir
            
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
            output_path = output_dir / f"relevance_{layer_name}.tif"
            
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
                                 plot_labels:bool = False,
                                 output_dir: Optional[Path] = None):
        """Create and save visualization plots for each relevance layer using unified styling."""
        if output_dir is None:
            output_dir = self.config.output_dir
            
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
                             export_individual_tifs: bool = True,
                             output_dir: Optional[Path] = None) -> Dict[str, np.ndarray]:
        """Main execution flow for relevance layer analysis."""
        logger.info("Starting relevance layer analysis")
        
        # Calculate relevance layers
        relevance_layers, meta = self.calculate_relevance()
        
        # Save all layers as TIFFs
        if export_individual_tifs:
            self.save_relevance_layers(relevance_layers, meta, output_dir)
            
        # Create visualizations with metadata for proper coordinate alignment
        if visualize:
            self.visualize_relevance_layers(relevance_layers, meta, output_dir=output_dir)
            
        logger.info("Completed relevance layer analysis")
        return relevance_layers
