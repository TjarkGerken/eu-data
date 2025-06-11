"""
Central utility module for handling coordinate transformations and raster alignment.
Provides consistent methods for converting between different coordinate reference systems
and ensuring proper alignment of raster data.
"""

import rasterio
import rasterio.warp
import rasterio.enums
from rasterio.enums import Resampling
import numpy as np
import logging
from typing import Tuple, Dict, Optional, Union
from pathlib import Path
import geopandas as gpd

from eu_climate.utils.cache_manager import get_cache_manager

logger = logging.getLogger(__name__)

class RasterTransformer:
    """
    Utility class for handling raster transformations and alignments.
    Ensures consistent coordinate transformations and grid alignment across different layers.
    """
    
    def __init__(self, target_crs: str = "EPSG:3035", target_resolution: float = 30.0, intermediate_crs: str = "ESRI:54009", config=None):
        """
        Initialize the RasterTransformer.
        
        Args:
            target_crs: Target coordinate reference system (default: EPSG:3035)
            target_resolution: Target resolution in meters (default: 30m)
            intermediate_crs: Intermediate CRS for two-step transformations (default: ESRI:54009)
            config: Configuration object for cache manager
        """
        self.target_crs = rasterio.crs.CRS.from_string(target_crs)
        self.target_resolution = target_resolution
        self.intermediate_crs = rasterio.crs.CRS.from_string(intermediate_crs)
        self._cache_manager = get_cache_manager(config)
        
    def get_reference_bounds(self, reference_path: Union[str, Path]) -> Tuple[float, float, float, float]:
        """
        Get bounds from a reference file (e.g., NUTS boundaries) to ensure consistent alignment.
        
        Args:
            reference_path: Path to reference file (shapefile or raster)
            
        Returns:
            Tuple of (left, bottom, right, top) bounds
        """
        reference_path = Path(reference_path)
        if reference_path.suffix == '.shp':
            gdf = gpd.read_file(reference_path)
            if gdf.crs != self.target_crs:
                gdf = gdf.to_crs(self.target_crs)
            bounds = gdf.total_bounds
            # Add small buffer (1%)
            buffer_x = (bounds[2] - bounds[0]) * 0.01
            buffer_y = (bounds[3] - bounds[1]) * 0.01
            return (
                bounds[0] - buffer_x,
                bounds[1] - buffer_y,
                bounds[2] + buffer_x,
                bounds[3] + buffer_y
            )
        else:
            with rasterio.open(reference_path) as src:
                if src.crs != self.target_crs:
                    bounds = rasterio.warp.transform_bounds(
                        src.crs, self.target_crs, *src.bounds
                    )
                else:
                    bounds = src.bounds
                return bounds

    def transform_raster(self, 
                        source_path: Union[str, Path],
                        reference_bounds: Optional[Tuple[float, float, float, float]] = None,
                        resampling_method: str = "bilinear") -> Tuple[np.ndarray, rasterio.Affine, rasterio.crs.CRS]:
        """
        Transform a raster to the target CRS and resolution, ensuring proper alignment.
        
        Args:
            source_path: Path to source raster
            reference_bounds: Optional bounds to align with (if None, uses source bounds)
            resampling_method: Resampling method to use (e.g., 'bilinear', 'nearest', 'cubic')
            
        Returns:
            Tuple of (transformed data, transform, CRS)
        """
        # Check cache first
        if self._cache_manager and self._cache_manager.enabled:
            # Generate cache key
            source_path = Path(source_path)
            
            # Include file timestamp and size in cache key
            input_files = [str(source_path)]
            
            # Parameters that affect the transformation
            parameters = {
                'reference_bounds': reference_bounds,
                'resampling_method': resampling_method,
                'target_crs': str(self.target_crs),
                'target_resolution': self.target_resolution,
                'intermediate_crs': str(self.intermediate_crs)
            }
            
            cache_key = self._cache_manager.generate_cache_key(
                'RasterTransformer.transform_raster',
                input_files,
                parameters,
                {}
            )
            
            # Try to get from cache
            cached_result = self._cache_manager.get(cache_key, 'raster_data')
            if cached_result is not None:
                logger.info(f"Cache hit for raster transformation: {source_path}")
                # Reconstruct the result from cached data
                data, metadata = cached_result
                # Reconstruct transform from metadata
                transform_data = metadata['transform']
                logger.debug(f"Cached transform_data: {transform_data}, type: {type(transform_data)}, length: {len(transform_data)}")
                
                # Handle different transform formats and convert to list of floats
                if isinstance(transform_data, (list, tuple, np.ndarray)):
                    # Convert to flat list and ensure all are floats
                    if hasattr(transform_data, 'flatten'):
                        # It's a numpy array
                        transform_list = transform_data.flatten().tolist()
                    elif isinstance(transform_data, (list, tuple)):
                        # It's already a list/tuple, but might be nested
                        transform_list = []
                        for item in transform_data:
                            if isinstance(item, (list, tuple, np.ndarray)):
                                # Flatten nested structures
                                if hasattr(item, 'flatten'):
                                    transform_list.extend(item.flatten().tolist())
                                else:
                                    transform_list.extend(list(item))
                            else:
                                transform_list.append(item)
                    else:
                        transform_list = list(transform_data)
                    
                    # Ensure we have at least 6 numeric values
                    transform_floats = []
                    for item in transform_list:
                        try:
                            transform_floats.append(float(item))
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid transform coefficient: {item}")
                            continue
                    
                    if len(transform_floats) >= 6:
                        # Use the first 6 coefficients
                        transform = rasterio.Affine(*transform_floats[:6])
                    else:
                        logger.warning(f"Insufficient transform coefficients: {len(transform_floats)} < 6")
                        logger.info("Falling back to fresh transformation")
                        # Fall back to fresh transformation
                        result = self._transform_raster_impl(source_path, reference_bounds, resampling_method)
                        return result
                else:
                    logger.warning(f"Unexpected transform data type: {type(transform_data)}")
                    logger.info("Falling back to fresh transformation")
                    # Fall back to fresh transformation
                    result = self._transform_raster_impl(source_path, reference_bounds, resampling_method)
                    return result
                    
                # Reconstruct CRS
                crs = rasterio.crs.CRS.from_string(metadata['crs'])
                return data, transform, crs
                
            logger.info(f"Cache miss for raster transformation: {source_path}")
        
        # Perform the transformation
        result = self._transform_raster_impl(source_path, reference_bounds, resampling_method)
        
        # Cache the result
        if self._cache_manager and self._cache_manager.enabled:
            # Package the result for caching: (data, metadata)
            data, transform, crs = result
            # Ensure transform coefficients are stored as a simple list of floats
            transform_coeffs = [
                float(transform.a), float(transform.b), float(transform.c),
                float(transform.d), float(transform.e), float(transform.f)
            ]
            metadata = {
                'transform': transform_coeffs,  # Save the 6 affine coefficients as simple float list
                'crs': str(crs),
                'shape': data.shape
            }
            cache_data = (data, metadata)
            
            success = self._cache_manager.set(cache_key, cache_data, 'raster_data')
            if success:
                logger.info(f"Successfully cached raster transformation: {source_path}")
            else:
                logger.warning(f"Failed to cache raster transformation: {source_path}")
            
        return result
    
    def _transform_raster_impl(self, 
                              source_path: Union[str, Path],
                              reference_bounds: Optional[Tuple[float, float, float, float]] = None,
                              resampling_method: str = "bilinear") -> Tuple[np.ndarray, rasterio.Affine, rasterio.crs.CRS]:
        """
        Internal implementation of raster transformation (without caching).
        """
        source_path = Path(source_path)
        logger.info(f"Transforming raster: {source_path}")
        
        # Convert resampling method string to Resampling enum
        try:
            resampling = getattr(Resampling, resampling_method.lower())
        except AttributeError:
            logger.warning(f"Invalid resampling method '{resampling_method}', defaulting to 'bilinear'")
            resampling = Resampling.bilinear
        
        with rasterio.open(source_path) as src:
            # Log original properties
            logger.info(f"Original CRS: {src.crs}")
            logger.info(f"Original bounds: {src.bounds}")
            logger.info(f"Original transform: {src.transform}")
            
            # Read source data
            data = src.read(1)
            
            # Handle nodata values
            if src.nodata is not None:
                data = np.where(data == src.nodata, np.nan, data)
            
            # If source is in EPSG:4326, use two-step transformation
            if src.crs == 'EPSG:4326':
                # First transform to intermediate CRS
                intermediate_bounds = rasterio.warp.transform_bounds(
                    src.crs, self.intermediate_crs, *src.bounds
                )
                
                # Calculate intermediate transform
                intermediate_transform, intermediate_width, intermediate_height = rasterio.warp.calculate_default_transform(
                    src.crs, self.intermediate_crs, src.width, src.height, *src.bounds
                )
                
                # Create intermediate array
                intermediate = np.empty((intermediate_height, intermediate_width), dtype=np.float32)
                
                # Transform to intermediate CRS
                rasterio.warp.reproject(
                    source=data,
                    destination=intermediate,
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=intermediate_transform,
                    dst_crs=self.intermediate_crs,
                    resampling=resampling
                )
                
                # Now transform from intermediate to target CRS
                if reference_bounds is None:
                    target_bounds = rasterio.warp.transform_bounds(
                        self.intermediate_crs, self.target_crs, *intermediate_bounds
                    )
                else:
                    target_bounds = reference_bounds
                
                # Calculate dimensions
                width = int(np.ceil((target_bounds[2] - target_bounds[0]) / self.target_resolution))
                height = int(np.ceil((target_bounds[3] - target_bounds[1]) / self.target_resolution))
                
                # Create target transform
                dst_transform = rasterio.transform.from_origin(
                    target_bounds[0], target_bounds[3],
                    self.target_resolution, self.target_resolution
                )
                
                # Create destination array
                destination = np.empty((height, width), dtype=np.float32)
                
                # Final transformation
                rasterio.warp.reproject(
                    source=intermediate,
                    destination=destination,
                    src_transform=intermediate_transform,
                    src_crs=self.intermediate_crs,
                    dst_transform=dst_transform,
                    dst_crs=self.target_crs,
                    resampling=resampling
                )
                
                data = destination
                transform = dst_transform
                
            else:
                # Direct transformation for other CRS
                if reference_bounds is None:
                    target_bounds = rasterio.warp.transform_bounds(
                        src.crs, self.target_crs, *src.bounds
                    )
                else:
                    target_bounds = reference_bounds
                
                # Calculate dimensions
                width = int(np.ceil((target_bounds[2] - target_bounds[0]) / self.target_resolution))
                height = int(np.ceil((target_bounds[3] - target_bounds[1]) / self.target_resolution))
                
                # Create target transform
                dst_transform = rasterio.transform.from_origin(
                    target_bounds[0], target_bounds[3],
                    self.target_resolution, self.target_resolution
                )
                
                # Create destination array
                destination = np.empty((height, width), dtype=np.float32)
                
                # Transform
                rasterio.warp.reproject(
                    source=data,
                    destination=destination,
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=dst_transform,
                    dst_crs=self.target_crs,
                    resampling=resampling
                )
                
                data = destination
                transform = dst_transform
            
            # Log transformed properties
            logger.info(f"Transformed CRS: {self.target_crs}")
            logger.info(f"Transformed bounds: {rasterio.transform.array_bounds(height, width, transform)}")
            logger.info(f"Transformed shape: {data.shape}")
            
            # Validate data
            if np.all(np.isnan(data)):
                raise ValueError("Transformed data contains only NaN values")
            
            return data, transform, self.target_crs

    def ensure_alignment(self, 
                        data: np.ndarray,
                        transform: rasterio.Affine,
                        reference_transform: rasterio.Affine,
                        reference_shape: Tuple[int, int],
                        resampling_method: str = "bilinear") -> np.ndarray:
        """
        Ensure a raster is aligned with a reference raster.
        
        Args:
            data: Input raster data
            transform: Current transform
            reference_transform: Reference transform to align with
            reference_shape: Reference shape to match
            resampling_method: Resampling method to use
            
        Returns:
            Aligned raster data
        """
        if transform == reference_transform and data.shape == reference_shape:
            return data
            
        destination = np.empty(reference_shape, dtype=np.float32)
        rasterio.warp.reproject(
            source=data,
            destination=destination,
            src_transform=transform,
            src_crs=self.target_crs,
            dst_transform=reference_transform,
            dst_crs=self.target_crs,
            resampling=Resampling[resampling_method.lower()]
        )
        
        return destination

    def validate_alignment(self, 
                          data1: np.ndarray,
                          transform1: rasterio.Affine,
                          data2: np.ndarray,
                          transform2: rasterio.Affine) -> bool:
        """
        Validate that two rasters are properly aligned.
        
        Args:
            data1: First raster data
            transform1: First raster transform
            data2: Second raster data
            transform2: Second raster transform
            
        Returns:
            True if rasters are aligned, False otherwise
        """
        if data1.shape != data2.shape:
            logger.warning(f"Shape mismatch: {data1.shape} vs {data2.shape}")
            return False
            
        if transform1 != transform2:
            logger.warning(f"Transform mismatch: {transform1} vs {transform2}")
            return False
            
        return True