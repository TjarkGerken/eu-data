import numpy as np
import geopandas as gpd
from sklearn.cluster import DBSCAN
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from typing import List, Tuple, Optional, Dict
import rasterio
from rasterio.transform import xy
from skimage.morphology import binary_closing, disk
from skimage.measure import find_contours
from skimage.filters import gaussian

try:
    import alphashape

    ALPHASHAPE_AVAILABLE = True
except ImportError:
    alphashape = None
    ALPHASHAPE_AVAILABLE = False

from eu_climate.utils.utils import setup_logging

logger = setup_logging(__name__)


class RiskClusterExtractor:
    """
    Extracts high-risk economic clusters from raster data using DBSCAN and alpha-shapes.

    This class implements a sophisticated pipeline for identifying and processing
    high-risk areas in spatial data. It combines:

    1. Binary thresholding to identify high-risk pixels
    2. Morphological operations to reduce noise and connect nearby areas
    3. Spatial clustering using DBSCAN to group related pixels
    4. Geometric processing using alpha-shapes or contour detection
    5. Scale-adaptive smoothing and polygon optimization

    The extractor is designed to handle different data sizes and scales, automatically
    adjusting parameters for optimal results across varying input data characteristics.
    """

    def __init__(
        self,
        risk_threshold: float = 0.25,
        cell_size_meters: float = 30,
        morphological_closing_disk_size: int = 3,
        cluster_epsilon_multiplier: float = 1.5,
        minimum_samples: int = 4,
        alpha_parameter_divisor: float = 1.0,
        hole_area_threshold: float = 0.10,
        minimum_polygon_area_square_meters: float = 5000,
        smoothing_buffer_meters: float = 45,
        polygon_simplification_tolerance: float = 15,
        natural_smoothing_iterations: int = 2,
        corner_rounding_radius: float = 30,
        use_contour_method: bool = False,
    ):
        """
        Initialize the risk cluster extractor with configurable parameters.

        Args:
            risk_threshold: Minimum risk value to consider for clustering (0-1)
            cell_size_meters: Size of raster cells in meters
            morphological_closing_disk_size: Size of morphological closing disk for noise reduction
            cluster_epsilon_multiplier: Multiplier for DBSCAN epsilon parameter
            minimum_samples: Minimum samples required for DBSCAN cluster formation
            alpha_parameter_divisor: Divisor for alpha-shape parameter (smaller = more detailed)
            hole_area_threshold: Threshold for filling holes in polygons (relative to polygon area)
            minimum_polygon_area_square_meters: Minimum area for polygon retention
            smoothing_buffer_meters: Base buffer distance for polygon smoothing
            polygon_simplification_tolerance: Tolerance for polygon simplification
            natural_smoothing_iterations: Number of smoothing iterations to apply
            corner_rounding_radius: Radius for corner rounding operations
            use_contour_method: Whether to use contour-based method instead of DBSCAN
        """
        self.risk_threshold = risk_threshold
        self.cell_size_meters = cell_size_meters
        self.morphological_closing_disk_size = morphological_closing_disk_size
        self.use_contour_method = use_contour_method

        # Calculate DBSCAN epsilon based on cell size
        self.cluster_epsilon = cluster_epsilon_multiplier * cell_size_meters
        self.minimum_samples = minimum_samples

        # Calculate alpha-shape parameter (inverse relationship with cell size)
        self.alpha_parameter = alpha_parameter_divisor / cell_size_meters

        # Area and smoothing parameters
        self.hole_area_threshold = hole_area_threshold
        self.minimum_polygon_area_square_meters = minimum_polygon_area_square_meters
        self.base_smoothing_buffer_meters = (
            smoothing_buffer_meters  # Keep as reference for scaling
        )
        self.base_polygon_simplification_tolerance = polygon_simplification_tolerance
        self.natural_smoothing_iterations = natural_smoothing_iterations
        self.base_corner_rounding_radius = corner_rounding_radius

        # Log configuration
        logger.info("RiskClusterExtractor initialized with enhanced fuzzy clustering:")
        logger.info(f"  - risk_threshold: {self.risk_threshold}")
        logger.info(f"  - cluster_epsilon: {self.cluster_epsilon} meters")
        logger.info(f"  - minimum_samples: {self.minimum_samples}")
        logger.info(
            f"  - minimum_polygon_area: {self.minimum_polygon_area_square_meters} m²"
        )
        logger.info(
            f"  - base_smoothing_buffer: {self.base_smoothing_buffer_meters} meters (scale-adaptive)"
        )
        logger.info(
            f"  - morphological_closing_disk: {self.morphological_closing_disk_size}"
        )
        logger.info(
            f"  - hole_area_threshold: {self.hole_area_threshold} (scale-adaptive)"
        )
        logger.info(
            "  - processing_order: morphology -> individual_smoothing -> merge -> area_filter"
        )

        # Log alpha-shape availability
        if not ALPHASHAPE_AVAILABLE:
            logger.warning(
                "Alpha-shape library not available, will use convex hull as fallback"
            )

    def extract_risk_clusters(
        self, risk_data: np.ndarray, transform: rasterio.Affine, target_crs: str
    ) -> gpd.GeoDataFrame:
        """
        Extract risk clusters from raster data and return as polygons.

        This is the main entry point for cluster extraction. The process follows these steps:
        1. Validate input data and check for sufficient high-risk values
        2. Create binary risk mask using threshold
        3. Extract coordinate points from high-risk areas
        4. Apply clustering algorithm (DBSCAN or contour-based)
        5. Create polygon geometries from clusters
        6. Process and optimize polygons
        7. Return results as GeoDataFrame

        Args:
            risk_data: 2D numpy array containing risk values (0-1)
            transform: Rasterio affine transform for coordinate conversion
            target_crs: Target coordinate reference system string

        Returns:
            GeoDataFrame containing risk cluster polygons with cluster IDs
        """
        # Validate input data
        if not self._has_sufficient_risk_data(risk_data):
            return self._create_empty_geodataframe(target_crs)

        # Create binary mask from risk data
        binary_risk_mask = self._create_binary_risk_mask(risk_data)

        # Extract coordinate points from high-risk areas
        risk_points = self._extract_risk_points(binary_risk_mask, transform)

        # Check if we have enough points for clustering
        if len(risk_points) < self.minimum_samples:
            logger.info(f"Insufficient risk points ({len(risk_points)}) for clustering")
            return self._create_empty_geodataframe(target_crs)

        # Apply clustering algorithm
        if self.use_contour_method:
            # Use contour-based method for more natural boundaries
            cluster_polygons = self._create_contour_polygons(
                binary_risk_mask, transform
            )
        else:
            # Use traditional DBSCAN + alpha-shape method
            cluster_labels = self._perform_clustering(risk_points)
            cluster_polygons = self._create_cluster_polygons(
                risk_points, cluster_labels
            )

        # Finalize and return results
        return self._finalize_geodataframe(cluster_polygons, target_crs)

    def _has_sufficient_risk_data(self, risk_data: np.ndarray) -> bool:
        """
        Check if risk data contains sufficient high-risk values.

        Args:
            risk_data: Input risk data array

        Returns:
            True if sufficient high-risk data exists, False otherwise
        """
        return np.any(risk_data >= self.risk_threshold)

    def _create_binary_risk_mask(self, risk_data: np.ndarray) -> np.ndarray:
        """
        Create binary mask from risk data with scale-aware morphological operations.

        This method applies:
        1. Thresholding to create binary mask
        2. Morphological closing to reduce noise and connect nearby areas
        3. Optional Gaussian smoothing for fuzzy outlines (contour method)

        Args:
            risk_data: Input risk data array

        Returns:
            Binary mask array indicating high-risk areas
        """
        # Create initial binary mask
        binary_mask = risk_data >= self.risk_threshold

        if self.use_contour_method:
            # Scale-aware morphological closing for contour method
            total_area = np.sum(binary_mask) * (self.cell_size_meters**2)
            scale_aware_radius = max(
                self.morphological_closing_disk_size,
                int(np.ceil((total_area**0.5) / 600)),
            )

            # Apply morphological closing
            processed_mask = binary_closing(binary_mask, disk(scale_aware_radius))

            # Optional Gaussian blur for fuzzy outlines
            processed_mask = gaussian(
                processed_mask.astype(float), sigma=scale_aware_radius / 2
            )

            return processed_mask >= 0.5
        else:
            # Standard morphological closing for DBSCAN method
            return binary_closing(
                binary_mask, disk(self.morphological_closing_disk_size)
            )

    def _extract_risk_points(
        self, binary_mask: np.ndarray, transform: rasterio.Affine
    ) -> np.ndarray:
        """
        Extract coordinate points from binary risk mask.

        Converts pixel coordinates to real-world coordinates using the raster transform.

        Args:
            binary_mask: Binary mask indicating high-risk areas
            transform: Rasterio affine transform

        Returns:
            Array of coordinate points (x, y) for high-risk areas
        """
        # Find indices of high-risk pixels
        row_indices, column_indices = np.where(binary_mask)

        if len(row_indices) == 0:
            return np.array([]).reshape(0, 2)

        # Convert pixel coordinates to real-world coordinates
        longitude_coordinates, latitude_coordinates = xy(
            transform, row_indices, column_indices
        )
        return np.column_stack([longitude_coordinates, latitude_coordinates])

    def _perform_clustering(self, points: np.ndarray) -> np.ndarray:
        """
        Perform DBSCAN clustering on risk points.

        DBSCAN is used because it:
        - Handles arbitrary cluster shapes
        - Automatically determines number of clusters
        - Identifies noise points (outliers)
        - Works well with spatial data

        Args:
            points: Array of coordinate points to cluster

        Returns:
            Array of cluster labels for each point (-1 for noise)
        """
        clustering_algorithm = DBSCAN(
            eps=self.cluster_epsilon,
            min_samples=self.minimum_samples,
            metric="euclidean",
        )
        return clustering_algorithm.fit(points).labels_

    def _create_cluster_polygons(
        self, points: np.ndarray, labels: np.ndarray
    ) -> List[Polygon]:
        """
        Create polygons from clustered points using alpha-shapes.

        Converts point clusters into polygon geometries using alpha-shapes
        for more natural, concave boundaries than convex hulls.

        Args:
            points: Array of coordinate points
            labels: Cluster labels for each point

        Returns:
            List of Polygon geometries representing clusters
        """
        # Get unique cluster IDs (excluding noise points labeled -1)
        unique_cluster_ids = np.unique(labels)
        valid_cluster_ids = unique_cluster_ids[unique_cluster_ids != -1]

        polygons = []
        for cluster_id in valid_cluster_ids:
            # Extract points for this cluster
            cluster_points = points[labels == cluster_id]
            polygon = self._create_single_cluster_polygon(cluster_points)

            if polygon is not None:
                polygons.append(polygon)

        return polygons

    def _create_single_cluster_polygon(
        self, cluster_points: np.ndarray
    ) -> Optional[Polygon]:
        """
        Create polygon from single cluster using alpha-shape or convex hull.

        Args:
            cluster_points: Points belonging to a single cluster

        Returns:
            Polygon geometry or None if creation fails
        """
        if len(cluster_points) < 3:
            return None

        # Try alpha-shape first for more natural boundaries
        polygon = self._try_alpha_shape_polygon(cluster_points)
        if polygon is None:
            # Fall back to convex hull
            polygon = self._create_convex_hull_polygon(cluster_points)

        return polygon

    def _try_alpha_shape_polygon(self, points: np.ndarray) -> Optional[Polygon]:
        """
        Try to create alpha-shape polygon, fallback to None if not available.

        Alpha-shapes create more natural, concave boundaries compared to convex hulls.

        Args:
            points: Points to create alpha-shape from

        Returns:
            Alpha-shape polygon or None if creation fails
        """
        if not ALPHASHAPE_AVAILABLE:
            return None

        try:
            alpha_polygon = alphashape.alphashape(points, self.alpha_parameter)
            return alpha_polygon if isinstance(alpha_polygon, Polygon) else None
        except Exception as e:
            logger.warning(f"Alpha-shape creation failed: {e}")
            return None

    def _create_convex_hull_polygon(self, points: np.ndarray) -> Optional[Polygon]:
        """
        Create convex hull polygon as fallback.

        Args:
            points: Points to create convex hull from

        Returns:
            Convex hull polygon or None if creation fails
        """
        try:
            point_geometries = [Point(x, y) for x, y in points]
            return unary_union(point_geometries).convex_hull
        except Exception as e:
            logger.warning(f"Convex hull creation failed: {e}")
            return None

    def _process_polygon_holes(self, polygon: Polygon) -> Polygon:
        """
        Fill small holes in polygon based on area threshold.

        Small holes are often artifacts of the clustering process and should be filled
        to create more coherent risk areas.

        Args:
            polygon: Input polygon that may contain holes

        Returns:
            Polygon with small holes filled
        """
        if not hasattr(polygon, "interiors") or len(polygon.interiors) == 0:
            return polygon

        # Find holes that should be filled
        filled_holes = []
        for interior_ring in polygon.interiors:
            hole_polygon = Polygon(interior_ring)
            if self._should_fill_hole(hole_polygon, polygon):
                filled_holes.append(hole_polygon)

        # Fill selected holes
        if filled_holes:
            exterior_polygon = Polygon(polygon.exterior).buffer(0)
            return unary_union([exterior_polygon] + filled_holes)

        return polygon

    def _scale_factor(self, polygon: Polygon) -> float:
        """
        Calculate scale factor based on polygon size (km-based scaling).

        Larger polygons need different processing parameters than smaller ones.

        Args:
            polygon: Input polygon

        Returns:
            Scale factor (1.0 for small polygons, larger for big polygons)
        """
        return max(1.0, (polygon.area**0.5) / 1_000)

    def _should_fill_hole(self, hole_polygon: Polygon, parent_polygon: Polygon) -> bool:
        """
        Determine if hole should be filled based on scale-adaptive area threshold.

        Args:
            hole_polygon: Hole polygon to evaluate
            parent_polygon: Parent polygon containing the hole

        Returns:
            True if hole should be filled, False otherwise
        """
        scale = self._scale_factor(parent_polygon)
        # Dynamic hole rule: threshold grows with size so small holes in large polygons survive
        adaptive_threshold = self.hole_area_threshold * (scale**0.5)
        return hole_polygon.area / parent_polygon.area < adaptive_threshold

    def _finalize_geodataframe(
        self, polygons: List[Polygon], target_crs: str
    ) -> gpd.GeoDataFrame:
        """
        Create final GeoDataFrame with processed polygons.

        Args:
            polygons: List of polygon geometries
            target_crs: Target coordinate reference system

        Returns:
            GeoDataFrame with processed polygons and cluster IDs
        """
        if not polygons:
            return self._create_empty_geodataframe(target_crs)

        # Process polygons through the complete pipeline
        processed_polygons = self._process_final_polygons(polygons)

        # Create GeoDataFrame with cluster IDs
        return gpd.GeoDataFrame(
            {
                "geometry": processed_polygons,
                "risk_cluster_id": range(len(processed_polygons)),
            },
            crs=target_crs,
        )

    def _process_final_polygons(self, polygons: List[Polygon]) -> List[Polygon]:
        """
        Apply scale-aware processing: individual smoothing -> merge -> area filter.

        This multi-step process ensures high-quality polygon outputs:
        1. Individual polygon processing (hole filling, smoothing)
        2. Merging of overlapping polygons
        3. Final area filtering

        Args:
            polygons: List of raw polygons

        Returns:
            List of processed, high-quality polygons
        """
        if not polygons:
            return []

        # Step 1: Process each polygon individually (no early merge to avoid melting)
        individually_processed = []
        for polygon in polygons:
            # Process holes with scale-aware threshold
            hole_processed = self._process_polygon_holes(polygon)

            # Apply scale-aware smoothing to preserve relative detail
            smoothed_polygon = self._apply_scale_aware_smoothing(hole_processed)

            individually_processed.append(smoothed_polygon)

        # Step 2: Merge only after individual processing to preserve detail
        if len(individually_processed) == 1:
            final_polygons = individually_processed
        else:
            merged_result = unary_union(individually_processed)
            if isinstance(merged_result, Polygon):
                final_polygons = [merged_result]
            else:
                final_polygons = [
                    geom for geom in merged_result.geoms if isinstance(geom, Polygon)
                ]

        # Step 3: Apply area filter as final step
        return [poly for poly in final_polygons if self._meets_minimum_area(poly)]

    def _apply_scale_aware_smoothing(self, polygon: Polygon) -> Polygon:
        """
        Apply scale-adaptive smoothing - keeps relative fuzziness constant across sizes.

        Different sized polygons need different smoothing parameters to maintain
        consistent visual appearance and geometric quality.

        Args:
            polygon: Input polygon to smooth

        Returns:
            Smoothed polygon with scale-appropriate parameters
        """
        scale = self._scale_factor(polygon)

        # Scale-adaptive parameters
        buffer_distance = self.base_smoothing_buffer_meters * scale
        corner_radius = self.base_corner_rounding_radius * scale
        simplify_tolerance = self.base_polygon_simplification_tolerance * scale

        # Adaptive resolution based on perimeter to avoid straight edges on large polygons
        perimeter = polygon.length
        resolution = max(16, min(64, int(perimeter / 1000)))  # 16-64 based on perimeter

        smoothed_polygon = polygon

        # Gradual smoothing iterations with scale-aware parameters
        for iteration in range(self.natural_smoothing_iterations):
            iteration_buffer = buffer_distance * (1.0 - iteration * 0.25)

            # Expand and contract with adaptive resolution
            smoothed_polygon = smoothed_polygon.buffer(
                iteration_buffer, resolution=resolution, cap_style=1, join_style=1
            )
            smoothed_polygon = smoothed_polygon.buffer(
                -iteration_buffer * 0.85,
                resolution=resolution,
                cap_style=1,
                join_style=1,
            )

        # Scale-aware corner rounding
        corner_rounded_polygon = smoothed_polygon.buffer(
            corner_radius, resolution=resolution
        ).buffer(-corner_radius * 0.9, resolution=resolution)

        # Final simplification
        return corner_rounded_polygon.simplify(
            simplify_tolerance, preserve_topology=True
        )

    def _meets_minimum_area(self, polygon: Polygon) -> bool:
        """
        Check if polygon meets minimum area threshold.

        Args:
            polygon: Polygon to check

        Returns:
            True if polygon meets minimum area requirement
        """
        return polygon.area >= self.minimum_polygon_area_square_meters

    def _create_empty_geodataframe(self, target_crs: str) -> gpd.GeoDataFrame:
        """
        Create empty GeoDataFrame with correct schema.

        Args:
            target_crs: Target coordinate reference system

        Returns:
            Empty GeoDataFrame with correct column structure
        """
        return gpd.GeoDataFrame({"geometry": [], "risk_cluster_id": []}, crs=target_crs)

    def _create_contour_polygons(
        self, binary_mask: np.ndarray, transform: rasterio.Affine
    ) -> List[Polygon]:
        """
        Create polygons from binary mask using contour extraction for natural boundaries.

        This method uses scikit-image's contour detection to create more natural,
        smooth boundaries compared to the point-based DBSCAN approach.

        Args:
            binary_mask: Binary mask indicating high-risk areas
            transform: Rasterio affine transform for coordinate conversion

        Returns:
            List of polygon geometries created from contours
        """
        # Find contours in the binary mask
        contours = find_contours(binary_mask, 0.5)
        polygons = []

        for contour in contours:
            if len(contour) < 4:  # Need at least 4 points for a polygon
                continue

            try:
                # Convert contour coordinates to map coordinates
                x_coords, y_coords = xy(
                    transform, contour[:, 0], contour[:, 1], offset="center"
                )
                coords = list(zip(x_coords, y_coords))

                # Close the polygon if not already closed
                if coords[0] != coords[-1]:
                    coords.append(coords[0])

                # Create polygon
                polygon = Polygon(coords)

                # Apply buffer(0) to fix any self-intersections
                polygon = polygon.buffer(0)

                # Validate polygon
                if (
                    isinstance(polygon, Polygon)
                    and polygon.is_valid
                    and polygon.area > 0
                ):
                    polygons.append(polygon)

            except Exception as e:
                logger.warning(f"Failed to create polygon from contour: {e}")
                continue

        return polygons


class RiskClusterAnalyzer:
    """
    Analyzes and enhances risk cluster data with statistical information.

    This class provides tools for adding statistical analysis to risk clusters,
    including:
    - Area calculations and geometric metrics
    - Risk value statistics (mean, max, distribution)
    - Pixel density and coverage analysis
    - Risk density calculations

    The analyzer integrates with the original raster data to provide comprehensive
    statistics about each cluster's risk characteristics.
    """

    def __init__(self):
        """Initialize the risk cluster analyzer."""
        # Define the statistics columns that will be added to cluster data
        self.statistics_columns = [
            "cluster_area_square_meters",  # Total area of the cluster
            "mean_risk_value",  # Average risk value within cluster
            "max_risk_value",  # Maximum risk value within cluster
            "pixel_count",  # Number of pixels in cluster
            "risk_density",  # Risk per unit area
        ]

    def enhance_clusters_with_statistics(
        self,
        cluster_geodataframe: gpd.GeoDataFrame,
        risk_data: np.ndarray,
        transform: rasterio.Affine,
    ) -> gpd.GeoDataFrame:
        """
        Add statistical information to cluster polygons.

        For each cluster polygon, this method calculates comprehensive statistics
        by intersecting the polygon with the original raster data and computing
        various risk metrics.

        Args:
            cluster_geodataframe: GeoDataFrame containing cluster polygons
            risk_data: Original raster data used for clustering
            transform: Rasterio affine transform for coordinate conversion

        Returns:
            Enhanced GeoDataFrame with statistical columns added
        """
        if cluster_geodataframe.empty:
            return self._add_empty_statistics_columns(cluster_geodataframe)

        # Create copy to avoid modifying original
        enhanced_geodataframe = cluster_geodataframe.copy()

        # Initialize statistics columns
        for column_name in self.statistics_columns:
            enhanced_geodataframe[column_name] = 0.0

        # Calculate statistics for each cluster
        for index, row in enhanced_geodataframe.iterrows():
            polygon_geometry = row["geometry"]
            statistics = self._calculate_polygon_statistics(
                polygon_geometry, risk_data, transform
            )

            # Update statistics columns
            for column_name, value in statistics.items():
                enhanced_geodataframe.at[index, column_name] = value

        return enhanced_geodataframe

    def _add_empty_statistics_columns(
        self, geodataframe: gpd.GeoDataFrame
    ) -> gpd.GeoDataFrame:
        """
        Add statistics columns to empty GeoDataFrame.

        Args:
            geodataframe: Empty GeoDataFrame to enhance

        Returns:
            GeoDataFrame with empty statistics columns
        """
        enhanced_geodataframe = geodataframe.copy()
        for column_name in self.statistics_columns:
            enhanced_geodataframe[column_name] = []
        return enhanced_geodataframe

    def _calculate_polygon_statistics(
        self, polygon: Polygon, risk_data: np.ndarray, transform: rasterio.Affine
    ) -> Dict[str, float]:
        """
        Calculate statistical measures for a single polygon.

        This method:
        1. Creates a raster mask for the polygon
        2. Extracts risk values within the polygon
        3. Calculates various statistics

        Args:
            polygon: Polygon geometry to analyze
            risk_data: Original raster data
            transform: Rasterio affine transform

        Returns:
            Dictionary containing calculated statistics
        """
        # Create mask for pixels within polygon
        polygon_mask = self._create_polygon_mask(polygon, risk_data.shape, transform)

        # Extract risk values within polygon
        masked_risk_values = risk_data[polygon_mask]

        # Handle empty masks
        if len(masked_risk_values) == 0:
            return self._create_zero_statistics()

        # Calculate statistics
        return {
            "cluster_area_square_meters": polygon.area,
            "mean_risk_value": float(np.mean(masked_risk_values)),
            "max_risk_value": float(np.max(masked_risk_values)),
            "pixel_count": len(masked_risk_values),
            "risk_density": float(np.sum(masked_risk_values) / polygon.area)
            if polygon.area > 0
            else 0.0,
        }

    def _create_polygon_mask(
        self,
        polygon: Polygon,
        raster_shape: Tuple[int, int],
        transform: rasterio.Affine,
    ) -> np.ndarray:
        """
        Create boolean mask for polygon within raster bounds.

        Uses rasterio's rasterize function to convert polygon geometry
        to a boolean mask matching the raster data dimensions.

        Args:
            polygon: Polygon geometry to rasterize
            raster_shape: Shape of the raster data (height, width)
            transform: Rasterio affine transform

        Returns:
            Boolean mask array indicating pixels within polygon
        """
        from rasterio.features import rasterize

        mask = rasterize(
            [polygon], out_shape=raster_shape, transform=transform, dtype=np.uint8
        )
        return mask.astype(bool)

    def _create_zero_statistics(self) -> Dict[str, float]:
        """
        Create statistics dictionary with zero values.

        Returns:
            Dictionary with all statistics set to zero
        """
        return {column: 0.0 for column in self.statistics_columns}
