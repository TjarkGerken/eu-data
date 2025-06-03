import rasterio
import rasterio.features
import rasterio.warp
import geopandas as gpd
from scipy import ndimage
from typing import Optional, Tuple
import numpy as np
from rasterio.enums import Resampling
from pathlib import Path
import logging
import matplotlib.pyplot as plt
import os

from eu_climate.config.config import ProjectConfig
from eu_climate.utils.utils import setup_logging, suppress_warnings


# Set up logging for the exposition layer
logger = setup_logging(__name__)


class ExpositionLayer:
    """
    Exposition Layer Implementation
    =============================
    
    Processes and analyzes exposure factors including:
    - Building Morphological Settlement Zone (MSZ) Delineation (GHS Built C) 
        - https://human-settlement.emergency.copernicus.eu/download.php?ds=builtC
        - Range: 0-25 | Explanation https://human-settlement.emergency.copernicus.eu/documents/GHSL_Data_Package_2023.pdf?t=1727170839
        - 2018, 10m Res, Cord System Mollweide, ESRI54009
    - Population density (GHS POP)
        - https://human-settlement.emergency.copernicus.eu/download.php?ds=pop
        - 2025, 100m Res, Cord System WGS84, EPSG:4326 
    - Building volume (GHS Built V) 
        - https://human-settlement.emergency.copernicus.eu/download.php?ds=builtV
        - 2025, 100m Res, Cord System Mollweide, ESRI54009
    """
    
    def __init__(self, config: ProjectConfig):
        """Initialize the Exposition Layer with project configuration."""
        self.config = config
        
        # Data paths
        self.ghs_built_c_path = self.config.ghs_built_c_path
        self.ghs_built_v_path = self.config.ghs_built_v_path
        self.population_path = self.config.population_path
        self.nuts_paths = self.config.nuts_paths
        self.transform = None
        self.crs = None
        self.nuts_data = {}
        
        logger.info(f"Initialized Exposition Layer")
        


    def load_ghs_built_c(self):
        """Load the GHS Built C data.Transform to the target CRS from the config file."""""
        # The GHS BUILT C uses the 
        return self.ghs_built_c_path
    
    def load_ghs_built_v(self):
        """Load the GHS Built V data. Transform to the target CRS from the config file."""
        return self.ghs_built_v_path
    
    def load_population(self):
        """Load the population data.Transform to the target CRS from the config file."""
        return self.population_path
    
    def normalize_data(self):
        """Normalize the data to a unified scale of 0-1."""
        pass
    
    def load_and_preprocess_raster(self, path: str) -> Tuple[np.ndarray, dict]:
        """Load and preprocess a single raster to target resolution and CRS."""
        logger.info(f"Loading raster: {path}")
        with rasterio.open(path) as src:
            # Log original CRS and bounds for debugging
            logger.info(f"Original CRS: {src.crs}, Bounds: {src.bounds}")
            
            data = src.read(1)
            logger.info(f"Loaded raster shape: {data.shape}, dtype: {data.dtype}")
            
            # Calculate target transform and shape for 30x30m grid
            target_crs = self.config.target_crs  # EPSG:3035
            res = 30  # 30x30m
            
            # Get the bounds in the target CRS
            left, bottom, right, top = rasterio.warp.transform_bounds(
                src.crs, target_crs, *src.bounds
            )
            
            # For population data (EPSG:4326), handle transformation differently
            if src.crs == 'EPSG:4326':
                # First transform the bounds to Mollweide to match other layers
                mollweide_bounds = rasterio.warp.transform_bounds(
                    src.crs, 'ESRI:54009', *src.bounds
                )
                
                # Calculate the transform in Mollweide
                mollweide_transform, mollweide_width, mollweide_height = rasterio.warp.calculate_default_transform(
                    src.crs, 'ESRI:54009', src.width, src.height, *src.bounds
                )
                
                # Create intermediate array
                intermediate = np.empty((mollweide_height, mollweide_width), dtype=np.float32)
                
                # Transform to Mollweide
                rasterio.warp.reproject(
                    source=data,
                    destination=intermediate,
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=mollweide_transform,
                    dst_crs='ESRI:54009',
                    resampling=self.config.resampling_method
                )
                
                # Now transform the Mollweide bounds to EPSG:3035
                left, bottom, right, top = rasterio.warp.transform_bounds(
                    'ESRI:54009', target_crs, *mollweide_bounds
                )
                
                # Calculate the final transform
                dst_transform = rasterio.transform.from_origin(
                    left, top, res, res
                )
                
                # Calculate dimensions
                width = int(np.ceil((right - left) / res))
                height = int(np.ceil((top - bottom) / res))
                
                # Create final destination array
                destination = np.empty((height, width), dtype=np.float32)
                
                # Transform from Mollweide to EPSG:3035
                rasterio.warp.reproject(
                    source=intermediate,
                    destination=destination,
                    src_transform=mollweide_transform,
                    src_crs='ESRI:54009',
                    dst_transform=dst_transform,
                    dst_crs=target_crs,
                    resampling=self.config.resampling_method
                )
                
                data = destination
                logger.info(f"Population data transformed - Mollweide bounds: {mollweide_bounds}")
                logger.info(f"Population data transformed - Final bounds: {left}, {bottom}, {right}, {top}")
            else:
                # For other data (already in Mollweide or similar)
                # Calculate the transform that aligns with the target grid
                dst_transform = rasterio.transform.from_origin(
                    left, top, res, res
                )
                
                # Calculate dimensions based on bounds and resolution
                width = int(np.ceil((right - left) / res))
                height = int(np.ceil((top - bottom) / res))
                
                # Create destination array
                destination = np.empty((height, width), dtype=np.float32)
                
                # Perform the reprojection with consistent grid alignment
                rasterio.warp.reproject(
                    source=data,
                    destination=destination,
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=dst_transform,
                    dst_crs=target_crs,
                    resampling=self.config.resampling_method
                )
                
                data = destination
            
            logger.info(f"Reprojected+resampled raster shape: {data.shape}, dtype: {data.dtype}")
            logger.info(f"New bounds: {rasterio.transform.array_bounds(height, width, dst_transform)}")
            
            if data.size == 0:
                raise ValueError(f"Loaded raster from {path} is empty after preprocessing!")
                
            meta = src.meta.copy()
            meta.update({
                'crs': target_crs,
                'transform': dst_transform,
                'height': data.shape[0],
                'width': data.shape[1],
                'dtype': 'float32'
            })
            
        return data, meta

    def normalize_ghs_built_c(self, data: np.ndarray) -> np.ndarray:
        """Normalize GHS Built-C using config-driven class weights."""
        class_weights = self.config.ghs_built_c_class_weights
        max_class = int(np.nanmax(data))
        lookup = np.zeros(max_class + 1)
        for k, v in class_weights.items():
            lookup[int(k)] = v
        normalized = lookup[data.astype(int)]
        logger.info(f"GHS Built-C normalization - Min: {np.nanmin(normalized)}, Max: {np.nanmax(normalized)}, Mean: {np.nanmean(normalized)}")
        return normalized

    def normalize_raster(self, data: np.ndarray) -> np.ndarray:
        """Normalize a raster to 0-1 based on min/max values, ignoring NaNs."""
        valid = ~np.isnan(data)
        min_val = np.nanmin(data)
        max_val = np.nanmax(data)
        logger.info(f"Raster normalization - Original Min: {min_val}, Max: {max_val}, Mean: {np.nanmean(data)}")
        norm = np.zeros_like(data, dtype=np.float32)
        if max_val > min_val:
            norm[valid] = (data[valid] - min_val) / (max_val - min_val)
        logger.info(f"Raster normalization - Normalized Min: {np.nanmin(norm)}, Max: {np.nanmax(norm)}, Mean: {np.nanmean(norm)}")
        return norm

    def calculate_exposition(self) -> Tuple[np.ndarray, dict]:
        """Calculate the final exposition layer using weighted combination."""
        # Load and preprocess rasters
        ghs_built_c, meta = self.load_and_preprocess_raster(self.ghs_built_c_path)
        logger.info(f"GHS Built-C after preprocessing - Min: {np.nanmin(ghs_built_c)}, Max: {np.nanmax(ghs_built_c)}, Mean: {np.nanmean(ghs_built_c)}")
        
        # Use the first layer's transform as reference for all other layers
        reference_transform = meta['transform']
        reference_crs = meta['crs']
        reference_shape = ghs_built_c.shape
        
        # Load other layers with the same transform
        ghs_built_v, _ = self.load_and_preprocess_raster(self.ghs_built_v_path)
        logger.info(f"GHS Built-V after preprocessing - Min: {np.nanmin(ghs_built_v)}, Max: {np.nanmax(ghs_built_v)}, Mean: {np.nanmean(ghs_built_v)}")
        
        # Load population data last to ensure proper alignment
        population, _ = self.load_and_preprocess_raster(self.population_path)
        logger.info(f"Population after preprocessing - Min: {np.nanmin(population)}, Max: {np.nanmax(population)}, Mean: {np.nanmean(population)}")
        
        # Ensure all layers have the same shape and transform
        if ghs_built_v.shape != reference_shape or ghs_built_v.dtype != np.float32:
            ghs_built_v = rasterio.warp.reproject(
                source=ghs_built_v,
                destination=np.empty(reference_shape, dtype=np.float32),
                src_transform=meta['transform'],
                src_crs=reference_crs,
                dst_transform=reference_transform,
                dst_crs=reference_crs,
                resampling=self.config.resampling_method
            )[0]
            logger.info(f"GHS Built-V after reprojection - Min: {np.nanmin(ghs_built_v)}, Max: {np.nanmax(ghs_built_v)}, Mean: {np.nanmean(ghs_built_v)}")
            
        if population.shape != reference_shape or population.dtype != np.float32:
            population = rasterio.warp.reproject(
                source=population,
                destination=np.empty(reference_shape, dtype=np.float32),
                src_transform=meta['transform'],
                src_crs=reference_crs,
                dst_transform=reference_transform,
                dst_crs=reference_crs,
                resampling=self.config.resampling_method
            )[0]
            logger.info(f"Population after reprojection - Min: {np.nanmin(population)}, Max: {np.nanmax(population)}, Mean: {np.nanmean(population)}")
        
        # Check for valid data
        if np.all(ghs_built_c == 0) or np.all(ghs_built_v == 0) or np.all(population == 0):
            logger.error("One or more input layers contain only zeros!")
            raise ValueError("Invalid input data: one or more layers contain only zeros")
        
        # Normalize
        norm_built_c = self.normalize_ghs_built_c(ghs_built_c)
        norm_built_v = self.normalize_raster(ghs_built_v)
        norm_population = self.normalize_raster(population)
        
        # Check normalized data
        if np.all(norm_built_c == 0) or np.all(norm_built_v == 0) or np.all(norm_population == 0):
            logger.error("One or more normalized layers contain only zeros!")
            raise ValueError("Invalid normalized data: one or more layers contain only zeros")
        
        # Weighted sum
        w = self.config.exposition_weights
        exposition = (
            w['ghs_built_c_weight'] * norm_built_c +
            w['ghs_built_v_weight'] * norm_built_v +
            w['population_weight'] * norm_population
        )
        logger.info(f"Final exposition - Min: {np.nanmin(exposition)}, Max: {np.nanmax(exposition)}, Mean: {np.nanmean(exposition)}")
        
        # Check final exposition
        if np.all(exposition == 0):
            logger.error("Final exposition layer contains only zeros!")
            raise ValueError("Invalid exposition layer: contains only zeros")
        
        # Optional smoothing
        if self.config.smoothing_sigma > 0:
            exposition = ndimage.gaussian_filter(exposition, sigma=self.config.smoothing_sigma)
            logger.info(f"Exposition after smoothing - Min: {np.nanmin(exposition)}, Max: {np.nanmax(exposition)}, Mean: {np.nanmean(exposition)}")
            
            # Check smoothed exposition
            if np.all(exposition == 0):
                logger.error("Smoothed exposition layer contains only zeros!")
                raise ValueError("Invalid smoothed exposition layer: contains only zeros")
            
        return exposition, meta

    def save_exposition_layer(self, data: np.ndarray, meta: dict, out_path: str):
        """Save the final exposition layer as GeoTIFF."""
        if os.path.exists(out_path):
            logger.info(f"Removing existing file at {out_path} before writing new output.")
            os.remove(out_path)
        vrt_path = os.path.splitext(out_path)[0] + '.vrt'
        if os.path.exists(vrt_path):
            logger.info(f"Removing existing VRT file at {vrt_path} before writing new output.")
            os.remove(vrt_path)
            
        # Ensure data is in valid range and not all zeros
        if np.all(data == 0):
            logger.warning("All values in the exposition layer are zero!")
            return
            
        data = np.clip(data, 0, 1)
        logger.info(f"Data before saving - Min: {np.nanmin(data)}, Max: {np.nanmax(data)}, Mean: {np.nanmean(data)}")
        
        meta.update({
            'driver': 'GTiff',
            'dtype': 'float32',
            'count': 1,
            'nodata': None  # Ensure no nodata value is set
        })
        
        with rasterio.open(out_path, 'w', **meta) as dst:
            dst.write(data.astype(np.float32), 1)
            logger.info(f"Successfully wrote data to {out_path}")

    def visualize_exposition(self, exposition: np.ndarray, title: str = "Exposition Layer"):
        """Visualize the exposition index for each cell."""
        plt.figure(figsize=(10, 8))
        im = plt.imshow(exposition, cmap='viridis')
        plt.colorbar(im, label='Exposition Index')
        plt.title(title)
        plt.axis('off')
        plt.show()

    def export_exposition(self, data: np.ndarray, meta: dict, out_path: str):
        """Export the exposition index for each cell to a specified GeoTIFF path."""
        meta.update({'dtype': 'float32', 'count': 1})
        with rasterio.open(out_path, 'w', **meta) as dst:
            dst.write(data.astype(np.float32), 1)
        logger.info(f"Exposition layer exported to {out_path}")

    def run_exposition(self, visualize: bool = False, export_path: str = None):
        """Main execution flow for the exposition layer."""
        exposition, meta = self.calculate_exposition()
        out_path = export_path or str(Path(self.config.local_output_dir) / 'exposition_layer.tif')
        self.save_exposition_layer(exposition, meta, out_path)
        logger.info(f"Exposition layer saved to {out_path}")
        if visualize:
            self.visualize_exposition(exposition)
        if export_path:
            self.export_exposition(exposition, meta, export_path)