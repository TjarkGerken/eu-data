import rasterio
import rasterio.warp
import rasterio.enums
from rasterio.enums import Resampling
import numpy as np
import logging
from typing import Tuple, Optional, Union
from pathlib import Path
import geopandas as gpd

from eu_climate.utils.cache_manager import get_cache_manager

logger = logging.getLogger(__name__)


class RasterTransformer:
    """
    Utility class for handling raster transformations and alignments.
    Ensures consistent coordinate transformations and grid alignment across different layers.

    This class provides a centralized solution for all raster transformation needs in the
    EU Climate Risk Assessment system. It handles:

    1. Coordinate Reference System (CRS) transformations
    2. Resolution changes and resampling
    3. Spatial extent alignment
    4. Two-step transformations for global data
    5. Cache integration for performance optimization
    6. Validation of spatial alignment

    The transformer is designed to work seamlessly with the caching system,
    automatically caching expensive transformation operations for reuse.
    """

    def __init__(
        self,
        target_crs: str = "EPSG:3035",
        intermediate_crs: str = "ESRI:54009",
        config=None,
    ):
        """
        Initialize the RasterTransformer.

        Args:
            target_crs: Target coordinate reference system (default: EPSG:3035 - European grid)
            intermediate_crs: Intermediate CRS for two-step transformations (default: ESRI:54009 - Mollweide)
            config: Configuration object containing target resolution and cache settings
        """
        self.target_crs = rasterio.crs.CRS.from_string(target_crs)
        self.config = config
        self.target_resolution = config.target_resolution if config else 30.0
        self.intermediate_crs = rasterio.crs.CRS.from_string(intermediate_crs)
        self._cache_manager = get_cache_manager(config)

    def get_reference_bounds(
        self, reference_path: Union[str, Path]
    ) -> Tuple[float, float, float, float]:
        """
        Get bounds from a reference file (e.g., NUTS boundaries) to ensure consistent alignment.

        This method extracts spatial bounds from either vector or raster reference data
        and transforms them to the target CRS. It also adds a small buffer to ensure
        complete coverage of the study area.

        Args:
            reference_path: Path to reference file (shapefile or raster)

        Returns:
            Tuple of (left, bottom, right, top) bounds in target CRS
        """
        reference_path = Path(reference_path)

        if reference_path.suffix == ".shp":
            # Handle vector reference (e.g., NUTS boundaries)
            gdf = gpd.read_file(reference_path)
            if gdf.crs != self.target_crs:
                gdf = gdf.to_crs(self.target_crs)
            bounds = gdf.total_bounds

            # Add small buffer (1%) to ensure complete coverage
            buffer_x = (bounds[2] - bounds[0]) * 0.01
            buffer_y = (bounds[3] - bounds[1]) * 0.01
            return (
                bounds[0] - buffer_x,
                bounds[1] - buffer_y,
                bounds[2] + buffer_x,
                bounds[3] + buffer_y,
            )
        else:
            # Handle raster reference
            with rasterio.open(reference_path) as src:
                if src.crs != self.target_crs:
                    bounds = rasterio.warp.transform_bounds(
                        src.crs, self.target_crs, *src.bounds
                    )
                else:
                    bounds = src.bounds
                return bounds

    def transform_raster(
        self,
        source_path: Union[str, Path],
        reference_bounds: Optional[Tuple[float, float, float, float]] = None,
        resampling_method: str = "bilinear",
    ) -> Tuple[np.ndarray, rasterio.Affine, rasterio.crs.CRS]:
        """
        Transform a raster to the target CRS and resolution, ensuring proper alignment.

        This is the main method for raster transformation. It handles:
        - Cache checking for previously transformed data
        - Coordinate system transformations (direct or two-step)
        - Resolution resampling
        - Spatial extent alignment
        - Result caching for future use

        The method automatically detects if two-step transformation is needed
        (e.g., for global WGS84 data) and applies the appropriate transformation pipeline.

        Args:
            source_path: Path to source raster file
            reference_bounds: Optional bounds to align with (if None, uses source bounds)
            resampling_method: Resampling method ('bilinear', 'nearest', 'cubic', etc.)

        Returns:
            Tuple of (transformed data array, affine transform, target CRS)
        """
        # Check cache first if available
        if self._cache_manager and self._cache_manager.enabled:
            source_path = Path(source_path)

            # Generate cache key based on transformation parameters
            input_files = [str(source_path)]
            parameters = {
                "reference_bounds": reference_bounds,
                "resampling_method": resampling_method,
                "target_crs": str(self.target_crs),
                "target_resolution": self.target_resolution,
                "intermediate_crs": str(self.intermediate_crs),
            }

            cache_key = self._cache_manager.generate_cache_key(
                "RasterTransformer.transform_raster", input_files, parameters, {}
            )

            # Try to load from cache
            cached_result = self._cache_manager.get(cache_key, "raster_data")
            if cached_result is not None:
                logger.info(f"Cache hit for raster transformation: {source_path}")
                data, metadata = cached_result
                transform_data = metadata["transform"]
                logger.debug(
                    f"Cached transform_data: {transform_data}, type: {type(transform_data)}, length: {len(transform_data)}"
                )

                # Reconstruct affine transform from cached data
                if isinstance(transform_data, (list, tuple, np.ndarray)):
                    # Handle different formats of cached transform data
                    if hasattr(transform_data, "flatten"):
                        transform_list = transform_data.flatten().tolist()
                    elif isinstance(transform_data, (list, tuple)):
                        transform_list = []
                        for item in transform_data:
                            if isinstance(item, (list, tuple, np.ndarray)):
                                if hasattr(item, "flatten"):
                                    transform_list.extend(item.flatten().tolist())
                                else:
                                    transform_list.extend(list(item))
                            else:
                                transform_list.append(item)
                    else:
                        transform_list = list(transform_data)

                    # Convert to float values
                    transform_floats = []
                    for item in transform_list:
                        try:
                            transform_floats.append(float(item))
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid transform coefficient: {item}")
                            continue

                    # Create affine transform if we have enough coefficients
                    if len(transform_floats) >= 6:
                        transform = rasterio.Affine(*transform_floats[:6])
                    else:
                        logger.warning(
                            f"Insufficient transform coefficients: {len(transform_floats)} < 6"
                        )
                        logger.info("Falling back to fresh transformation")
                        result = self._transform_raster_impl(
                            source_path, reference_bounds, resampling_method
                        )
                        return result
                else:
                    logger.warning(
                        f"Unexpected transform data type: {type(transform_data)}"
                    )
                    logger.info("Falling back to fresh transformation")
                    result = self._transform_raster_impl(
                        source_path, reference_bounds, resampling_method
                    )
                    return result

                # Reconstruct CRS
                crs = rasterio.crs.CRS.from_string(metadata["crs"])
                return data, transform, crs

            logger.info(f"Cache miss for raster transformation: {source_path}")

        # Perform actual transformation
        result = self._transform_raster_impl(
            source_path, reference_bounds, resampling_method
        )

        # Cache the result if caching is enabled
        if self._cache_manager and self._cache_manager.enabled:
            data, transform, crs = result

            # Prepare metadata for caching
            transform_coeffs = [
                float(transform.a),
                float(transform.b),
                float(transform.c),
                float(transform.d),
                float(transform.e),
                float(transform.f),
            ]
            metadata = {
                "transform": transform_coeffs,
                "crs": str(crs),
                "shape": data.shape,
            }
            cache_data = (data, metadata)

            # Store in cache
            success = self._cache_manager.set(cache_key, cache_data, "raster_data")
            if success:
                logger.info(f"Successfully cached raster transformation: {source_path}")
            else:
                logger.warning(f"Failed to cache raster transformation: {source_path}")

        return result

    def _transform_raster_impl(
        self,
        source_path: Union[str, Path],
        reference_bounds: Optional[Tuple[float, float, float, float]] = None,
        resampling_method: str = "bilinear",
    ) -> Tuple[np.ndarray, rasterio.Affine, rasterio.crs.CRS]:
        """
        Internal implementation of raster transformation (without caching).

        This method performs the actual raster transformation work. It:
        1. Opens and validates the source raster
        2. Determines the appropriate transformation strategy
        3. Applies either direct or two-step transformation
        4. Handles resolution resampling
        5. Returns the transformed result

        Two-step transformation is used for WGS84 data to minimize distortion:
        WGS84 → Intermediate CRS (Mollweide) → Target CRS (EPSG:3035)

        Args:
            source_path: Path to source raster file
            reference_bounds: Optional bounds for alignment
            resampling_method: Resampling method to use

        Returns:
            Tuple of (transformed data, affine transform, target CRS)
        """
        source_path = Path(source_path)
        logger.info(f"Transforming raster: {source_path}")

        # Validate and get resampling method
        try:
            resampling = getattr(Resampling, resampling_method.lower())
        except AttributeError:
            logger.warning(
                f"Invalid resampling method '{resampling_method}', defaulting to 'bilinear'"
            )
            resampling = Resampling.bilinear

        with rasterio.open(source_path) as src:
            # Log source information
            logger.info(f"Original CRS: {src.crs}")
            logger.info(f"Original bounds: {src.bounds}")
            logger.info(f"Original transform: {src.transform}")

            # Read the data and handle no-data values
            data = src.read(1)
            if src.nodata is not None:
                data = np.where(data == src.nodata, np.nan, data)

            # Determine transformation strategy
            if src.crs == "EPSG:4326":
                # Use two-step transformation for WGS84 data to minimize distortion
                logger.info(
                    "Applying two-step transformation: WGS84 → Mollweide → Target CRS"
                )

                # Step 1: WGS84 → Intermediate CRS (Mollweide)
                intermediate_bounds = rasterio.warp.transform_bounds(
                    src.crs, self.intermediate_crs, *src.bounds
                )

                intermediate_transform, intermediate_width, intermediate_height = (
                    rasterio.warp.calculate_default_transform(
                        src.crs,
                        self.intermediate_crs,
                        src.width,
                        src.height,
                        *src.bounds,
                    )
                )

                intermediate = np.empty(
                    (intermediate_height, intermediate_width), dtype=np.float32
                )

                rasterio.warp.reproject(
                    source=data,
                    destination=intermediate,
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=intermediate_transform,
                    dst_crs=self.intermediate_crs,
                    resampling=resampling,
                )

                # Step 2: Intermediate CRS → Target CRS
                if reference_bounds is None:
                    target_bounds = rasterio.warp.transform_bounds(
                        self.intermediate_crs, self.target_crs, *intermediate_bounds
                    )
                else:
                    target_bounds = reference_bounds

                # Calculate target grid dimensions
                width = int(
                    np.ceil(
                        (target_bounds[2] - target_bounds[0]) / self.target_resolution
                    )
                )
                height = int(
                    np.ceil(
                        (target_bounds[3] - target_bounds[1]) / self.target_resolution
                    )
                )

                # Create target transform
                dst_transform = rasterio.transform.from_origin(
                    target_bounds[0],
                    target_bounds[3],
                    self.target_resolution,
                    self.target_resolution,
                )

                destination = np.empty((height, width), dtype=np.float32)

                # Perform second transformation
                rasterio.warp.reproject(
                    source=intermediate,
                    destination=destination,
                    src_transform=intermediate_transform,
                    src_crs=self.intermediate_crs,
                    dst_transform=dst_transform,
                    dst_crs=self.target_crs,
                    resampling=resampling,
                )

                data = destination
                transform = dst_transform

            else:
                # Direct transformation for non-WGS84 data
                logger.info("Applying direct transformation to target CRS")

                # Determine target bounds
                if reference_bounds is None:
                    target_bounds = rasterio.warp.transform_bounds(
                        src.crs, self.target_crs, *src.bounds
                    )
                else:
                    target_bounds = reference_bounds

                # Calculate target grid dimensions
                width = int(
                    np.ceil(
                        (target_bounds[2] - target_bounds[0]) / self.target_resolution
                    )
                )
                height = int(
                    np.ceil(
                        (target_bounds[3] - target_bounds[1]) / self.target_resolution
                    )
                )

                # Create target transform
                dst_transform = rasterio.transform.from_origin(
                    target_bounds[0],
                    target_bounds[3],
                    self.target_resolution,
                    self.target_resolution,
                )

                destination = np.empty((height, width), dtype=np.float32)

                # Perform transformation
                rasterio.warp.reproject(
                    source=data,
                    destination=destination,
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=dst_transform,
                    dst_crs=self.target_crs,
                    resampling=resampling,
                )

                data = destination
                transform = dst_transform

            # Log transformation results
            logger.info(f"Transformed CRS: {self.target_crs}")
            logger.info(
                f"Transformed bounds: {rasterio.transform.array_bounds(height, width, transform)}"
            )
            logger.info(f"Transformed shape: {data.shape}")

            # Validate result
            if np.all(np.isnan(data)):
                raise ValueError("Transformed data contains only NaN values")

            return data, transform, self.target_crs

    def ensure_alignment(
        self,
        data: np.ndarray,
        transform: rasterio.Affine,
        reference_transform: rasterio.Affine,
        reference_shape: Tuple[int, int],
        resampling_method: str = "bilinear",
    ) -> np.ndarray:
        """
        Ensure a raster is aligned with a reference raster.

        This method is used when multiple rasters need to be perfectly aligned
        for overlay operations or analysis. It reprojects one raster to match
        the exact grid of another raster.

        Args:
            data: Input raster data to align
            transform: Current affine transform of the data
            reference_transform: Target transform to align with
            reference_shape: Target shape to match (height, width)
            resampling_method: Resampling method for alignment

        Returns:
            Aligned raster data with matching grid
        """
        # Check if alignment is already perfect
        if transform == reference_transform and data.shape == reference_shape:
            return data

        # Perform alignment reprojection
        destination = np.empty(reference_shape, dtype=np.float32)
        rasterio.warp.reproject(
            source=data,
            destination=destination,
            src_transform=transform,
            src_crs=self.target_crs,
            dst_transform=reference_transform,
            dst_crs=self.target_crs,
            resampling=Resampling[resampling_method.lower()],
        )

        return destination

    def validate_alignment(
        self,
        data1: np.ndarray,
        transform1: rasterio.Affine,
        data2: np.ndarray,
        transform2: rasterio.Affine,
    ) -> bool:
        """
        Validate that two rasters are properly aligned.

        This utility method checks whether two rasters have identical grids,
        which is required for pixel-by-pixel operations and overlays.

        Args:
            data1: First raster data array
            transform1: First raster affine transform
            data2: Second raster data array
            transform2: Second raster affine transform

        Returns:
            True if rasters are perfectly aligned, False otherwise
        """
        # Check shape alignment
        if data1.shape != data2.shape:
            logger.warning(f"Shape mismatch: {data1.shape} vs {data2.shape}")
            return False

        # Check transform alignment
        if transform1 != transform2:
            logger.warning(f"Transform mismatch: {transform1} vs {transform2}")
            return False

        return True
