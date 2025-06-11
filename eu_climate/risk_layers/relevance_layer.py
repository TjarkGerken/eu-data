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
from eu_climate.utils.data_loading import download_data
from eu_climate.utils.utils import setup_logging, suppress_warnings
from eu_climate.utils.conversion import RasterTransformer
from eu_climate.utils.caching_wrappers import CacheAwareMethod, cache_calculation_method, cache_raster_method, cache_result_method
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
        
        # Get latest available year
        latest_year = nl_data['TIME_PERIOD'].max()
        latest_data = nl_data[nl_data['TIME_PERIOD'] == latest_year]
        
        # Clean and standardize
        processed = latest_data[['geo', 'OBS_VALUE']].copy()
        processed.columns = ['nuts_code', 'gdp_value']
        processed['gdp_value'] = pd.to_numeric(processed['gdp_value'], errors='coerce')
        processed = processed.dropna()
        
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
        aggregated = latest_data.groupby('geo')['OBS_VALUE'].sum().reset_index()
        
        # Clean and standardize
        aggregated.columns = ['nuts_code', 'freight_value']
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
            
            # Map original column names to dataset-specific names
            if 'gdp_value' in df_renamed.columns:
                # GDP dataset keeps its name
                pass
            elif 'freight_value' in df_renamed.columns:
                # Freight datasets get renamed based on dataset name
                df_renamed = df_renamed.rename(columns={
                    'freight_value': f'{dataset_name}_value'
                })
            
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
            target_resolution=30.0
        )
        self.distributor = EconomicDistributor(config, self.transformer)
        
        # Initialize exposition layer
        self.exposition_layer = ExpositionLayer(config)
        
        logger.info("Initialized Relevance Layer")
    
    def load_and_process_economic_data(self) -> gpd.GeoDataFrame:
        """Load economic datasets and join with NUTS geometries."""
        # Load economic datasets
        economic_data = self.data_loader.load_economic_datasets()
        
        # Check if any datasets were loaded
        if not economic_data:
            #  Use the dataloader to load the data from huggingface
            if self.config.auto_download:
                download_data()
            else:
                raise ValueError("No economic datasets could be loaded. Downloading from huggingface is disabled.")
            
        
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
        
        # Get exposition layer
        exposition_data, exposition_meta = self.exposition_layer.calculate_exposition()
        
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
            
            # Distribute using exposition layer
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
                                 save_plots: bool = True, output_dir: Optional[Path] = None):
        """Create and save visualization plots for each relevance layer."""
        if output_dir is None:
            output_dir = self.config.output_dir
            
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Define titles and colormaps for each layer
        layer_configs = {
            'gdp': {'title': 'GDP Economic Relevance', 'cmap': 'viridis'},
            'freight_loading': {'title': 'Freight Loading Economic Relevance', 'cmap': 'plasma'},
            'freight_unloading': {'title': 'Freight Unloading Economic Relevance', 'cmap': 'inferno'},
            'combined': {'title': 'Combined Economic Relevance', 'cmap': 'magma'}
        }
        
        for layer_name, data in relevance_layers.items():
            if layer_name not in layer_configs:
                continue
                
            config = layer_configs[layer_name]
            
            # Create figure
            plt.figure(figsize=self.config.figure_size, dpi=self.config.dpi)
            
            # Create plot
            im = plt.imshow(data, cmap=config['cmap'], aspect='equal')
            plt.colorbar(im, label='Economic Relevance Index (0-1)', shrink=0.6)
            plt.title(config['title'], fontsize=14, fontweight='bold')
            plt.axis('off')
            
            # Add statistics text
            valid_data = data[data > 0]
            if len(valid_data) > 0:
                stats_text = (f'Min: {np.min(valid_data):.3f}\n'
                            f'Max: {np.max(valid_data):.3f}\n'
                            f'Mean: {np.mean(valid_data):.3f}')
                plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes,
                        verticalalignment='top', bbox=dict(boxstyle='round', 
                        facecolor='white', alpha=0.8))
            
            if save_plots:
                # Save as PNG for visualization
                plot_path = output_dir / f"relevance_{layer_name}_plot.png"
                plt.savefig(plot_path, bbox_inches='tight', dpi=self.config.dpi)
                logger.info(f"Saved {layer_name} plot to {plot_path}")
                
            plt.close()
    
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
            
        # Create visualizations
        if visualize:
            self.visualize_relevance_layers(relevance_layers, True, output_dir)
            
        logger.info("Completed relevance layer analysis")
        return relevance_layers
