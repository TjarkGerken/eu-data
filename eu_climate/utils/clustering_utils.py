import numpy as np
import geopandas as gpd
from sklearn.cluster import DBSCAN
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from typing import List, Tuple, Optional, Dict
import rasterio
from rasterio.transform import xy
from skimage.morphology import binary_closing, disk
try:
    import alphashape
except ImportError:
    alphashape = None

from eu_climate.utils.utils import setup_logging

logger = setup_logging(__name__)


class RiskClusterExtractor:
    """Extracts high-risk economic clusters from raster data using DBSCAN and alpha-shapes."""
    
    def __init__(self, 
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
                 corner_rounding_radius: float = 30):
        self.risk_threshold = risk_threshold
        self.cell_size_meters = cell_size_meters
        self.morphological_closing_disk_size = morphological_closing_disk_size
        self.cluster_epsilon = cluster_epsilon_multiplier * cell_size_meters
        self.minimum_samples = minimum_samples
        self.alpha_parameter = alpha_parameter_divisor / cell_size_meters
        self.hole_area_threshold = hole_area_threshold
        self.minimum_polygon_area_square_meters = minimum_polygon_area_square_meters
        self.smoothing_buffer_meters = smoothing_buffer_meters
        self.polygon_simplification_tolerance = polygon_simplification_tolerance
        self.natural_smoothing_iterations = natural_smoothing_iterations
        self.corner_rounding_radius = corner_rounding_radius
        
        logger.info(f"RiskClusterExtractor initialized with:")
        logger.info(f"  - risk_threshold: {self.risk_threshold}")
        logger.info(f"  - cluster_epsilon: {self.cluster_epsilon} meters")
        logger.info(f"  - minimum_samples: {self.minimum_samples}")
        logger.info(f"  - minimum_polygon_area: {self.minimum_polygon_area_square_meters} m²")
        logger.info(f"  - smoothing_buffer: {self.smoothing_buffer_meters} meters")
        
    def extract_risk_clusters(self, 
                             risk_data: np.ndarray, 
                             transform: rasterio.Affine,
                             target_crs: str) -> gpd.GeoDataFrame:
        """Extract risk clusters from raster data and return as polygons."""
        if not self._has_sufficient_risk_data(risk_data):
            return self._create_empty_geodataframe(target_crs)
            
        binary_risk_mask = self._create_binary_risk_mask(risk_data)
        risk_points = self._extract_risk_points(binary_risk_mask, transform)
        
        if len(risk_points) < self.minimum_samples:
            logger.info(f"Insufficient risk points ({len(risk_points)}) for clustering")
            return self._create_empty_geodataframe(target_crs)
            
        cluster_labels = self._perform_clustering(risk_points)
        cluster_polygons = self._create_cluster_polygons(risk_points, cluster_labels)
        
        return self._finalize_geodataframe(cluster_polygons, target_crs)
    
    def _has_sufficient_risk_data(self, risk_data: np.ndarray) -> bool:
        """Check if risk data contains sufficient high-risk values."""
        return np.any(risk_data >= self.risk_threshold)
    
    def _create_binary_risk_mask(self, risk_data: np.ndarray) -> np.ndarray:
        """Create binary mask from risk data with configurable morphological closing."""
        binary_mask = risk_data >= self.risk_threshold
        return binary_closing(binary_mask, disk(self.morphological_closing_disk_size))
    
    def _extract_risk_points(self, binary_mask: np.ndarray, transform: rasterio.Affine) -> np.ndarray:
        """Extract coordinate points from binary risk mask."""
        row_indices, column_indices = np.where(binary_mask)
        
        if len(row_indices) == 0:
            return np.array([]).reshape(0, 2)
            
        longitude_coordinates, latitude_coordinates = xy(transform, row_indices, column_indices)
        return np.column_stack([longitude_coordinates, latitude_coordinates])
    
    def _perform_clustering(self, points: np.ndarray) -> np.ndarray:
        """Perform DBSCAN clustering on risk points."""
        clustering_algorithm = DBSCAN(
            eps=self.cluster_epsilon,
            min_samples=self.minimum_samples,
            metric='euclidean'
        )
        return clustering_algorithm.fit(points).labels_
    
    def _create_cluster_polygons(self, points: np.ndarray, labels: np.ndarray) -> List[Polygon]:
        """Create polygons from clustered points using alpha-shapes."""
        unique_cluster_ids = np.unique(labels)
        valid_cluster_ids = unique_cluster_ids[unique_cluster_ids != -1]
        
        polygons = []
        for cluster_id in valid_cluster_ids:
            cluster_points = points[labels == cluster_id]
            polygon = self._create_single_cluster_polygon(cluster_points)
            
            if polygon is not None:
                polygons.append(polygon)
                
        return polygons
    
    def _create_single_cluster_polygon(self, cluster_points: np.ndarray) -> Optional[Polygon]:
        """Create polygon from single cluster using alpha-shape or convex hull."""
        if len(cluster_points) < 3:
            return None
            
        polygon = self._try_alpha_shape_polygon(cluster_points)
        if polygon is None:
            polygon = self._create_convex_hull_polygon(cluster_points)
            
        return self._process_polygon_holes(polygon) if polygon else None
    
    def _try_alpha_shape_polygon(self, points: np.ndarray) -> Optional[Polygon]:
        """Try to create alpha-shape polygon, fallback to None if not available."""
        if alphashape is None:
            return None
            
        try:
            alpha_polygon = alphashape.alphashape(points, self.alpha_parameter)
            return alpha_polygon if isinstance(alpha_polygon, Polygon) else None
        except Exception as e:
            logger.warning(f"Alpha-shape creation failed: {e}")
            return None
    
    def _create_convex_hull_polygon(self, points: np.ndarray) -> Optional[Polygon]:
        """Create convex hull polygon as fallback."""
        try:
            point_geometries = [Point(x, y) for x, y in points]
            return unary_union(point_geometries).convex_hull
        except Exception as e:
            logger.warning(f"Convex hull creation failed: {e}")
            return None
    
    def _process_polygon_holes(self, polygon: Polygon) -> Polygon:
        """Fill small holes in polygon based on area threshold."""
        if not hasattr(polygon, 'interiors') or len(polygon.interiors) == 0:
            return polygon
            
        filled_holes = []
        for interior_ring in polygon.interiors:
            hole_polygon = Polygon(interior_ring)
            if self._should_fill_hole(hole_polygon, polygon):
                filled_holes.append(hole_polygon)
        
        if filled_holes:
            exterior_polygon = Polygon(polygon.exterior).buffer(0)
            return unary_union([exterior_polygon] + filled_holes)
            
        return polygon
    
    def _should_fill_hole(self, hole_polygon: Polygon, parent_polygon: Polygon) -> bool:
        """Determine if hole should be filled based on area threshold."""
        return hole_polygon.area / parent_polygon.area < self.hole_area_threshold
    
    def _finalize_geodataframe(self, polygons: List[Polygon], target_crs: str) -> gpd.GeoDataFrame:
        """Create final GeoDataFrame with processed polygons."""
        if not polygons:
            return self._create_empty_geodataframe(target_crs)
            
        processed_polygons = self._process_final_polygons(polygons)
        return gpd.GeoDataFrame(
            {'geometry': processed_polygons, 'risk_cluster_id': range(len(processed_polygons))},
            crs=target_crs
        )
    
    def _process_final_polygons(self, polygons: List[Polygon]) -> List[Polygon]:
        """Apply final processing to polygons: smoothing buffer, simplify, filter by area."""
        merged_polygons = unary_union(polygons)
        
        if isinstance(merged_polygons, Polygon):
            processed_geometry = self._apply_smoothing_operations(merged_polygons)
            return [processed_geometry] if self._meets_minimum_area(processed_geometry) else []
        else:
            final_polygons = []
            for geometry in merged_polygons.geoms:
                if isinstance(geometry, Polygon):
                    processed_geometry = self._apply_smoothing_operations(geometry)
                    if self._meets_minimum_area(processed_geometry):
                        final_polygons.append(processed_geometry)
            return final_polygons
    
    def _apply_smoothing_operations(self, polygon: Polygon) -> Polygon:
        """Apply natural smoothing operations to create organic-looking polygons."""
        smoothed_polygon = polygon
        
        for iteration in range(self.natural_smoothing_iterations):
            buffer_distance = self.smoothing_buffer_meters * (1.0 - iteration * 0.3)
            
            smoothed_polygon = smoothed_polygon.buffer(
                buffer_distance, 
                resolution=16, 
                cap_style=1, 
                join_style=1
            )
            smoothed_polygon = smoothed_polygon.buffer(
                -buffer_distance * 0.9,
                resolution=16,
                cap_style=1,
                join_style=1
            )
        
        corner_rounded_polygon = smoothed_polygon.buffer(
            self.corner_rounding_radius,
            resolution=32
        ).buffer(
            -self.corner_rounding_radius,
            resolution=32
        )
        
        return corner_rounded_polygon.simplify(
            self.polygon_simplification_tolerance,
            preserve_topology=True
        )
    
    def _meets_minimum_area(self, polygon: Polygon) -> bool:
        """Check if polygon meets minimum area threshold."""
        return polygon.area >= self.minimum_polygon_area_square_meters
    
    def _create_empty_geodataframe(self, target_crs: str) -> gpd.GeoDataFrame:
        """Create empty GeoDataFrame with correct schema."""
        return gpd.GeoDataFrame(
            {'geometry': [], 'risk_cluster_id': []},
            crs=target_crs
        )


class RiskClusterAnalyzer:
    """Analyzes and enhances risk cluster data with statistical information."""
    
    def __init__(self):
        self.statistics_columns = [
            'cluster_area_square_meters',
            'mean_risk_value',
            'max_risk_value',
            'pixel_count',
            'risk_density'
        ]
    
    def enhance_clusters_with_statistics(self,
                                       cluster_geodataframe: gpd.GeoDataFrame,
                                       risk_data: np.ndarray,
                                       transform: rasterio.Affine) -> gpd.GeoDataFrame:
        """Add statistical information to cluster polygons."""
        if cluster_geodataframe.empty:
            return self._add_empty_statistics_columns(cluster_geodataframe)
            
        enhanced_geodataframe = cluster_geodataframe.copy()
        
        for column_name in self.statistics_columns:
            enhanced_geodataframe[column_name] = 0.0
            
        for index, row in enhanced_geodataframe.iterrows():
            polygon_geometry = row['geometry']
            statistics = self._calculate_polygon_statistics(polygon_geometry, risk_data, transform)
            
            for column_name, value in statistics.items():
                enhanced_geodataframe.at[index, column_name] = value
                
        return enhanced_geodataframe
    
    def _add_empty_statistics_columns(self, geodataframe: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Add statistics columns to empty GeoDataFrame."""
        enhanced_geodataframe = geodataframe.copy()
        for column_name in self.statistics_columns:
            enhanced_geodataframe[column_name] = []
        return enhanced_geodataframe
    
    def _calculate_polygon_statistics(self,
                                    polygon: Polygon,
                                    risk_data: np.ndarray,
                                    transform: rasterio.Affine) -> Dict[str, float]:
        """Calculate statistical measures for a single polygon."""
        polygon_mask = self._create_polygon_mask(polygon, risk_data.shape, transform)
        masked_risk_values = risk_data[polygon_mask]
        
        if len(masked_risk_values) == 0:
            return self._create_zero_statistics()
            
        return {
            'cluster_area_square_meters': polygon.area,
            'mean_risk_value': float(np.mean(masked_risk_values)),
            'max_risk_value': float(np.max(masked_risk_values)),
            'pixel_count': len(masked_risk_values),
            'risk_density': float(np.sum(masked_risk_values) / polygon.area) if polygon.area > 0 else 0.0
        }
    
    def _create_polygon_mask(self,
                           polygon: Polygon,
                           raster_shape: Tuple[int, int],
                           transform: rasterio.Affine) -> np.ndarray:
        """Create boolean mask for polygon within raster bounds."""
        from rasterio.features import rasterize
        
        mask = rasterize(
            [polygon],
            out_shape=raster_shape,
            transform=transform,
            dtype=np.uint8
        )
        return mask.astype(bool)
    
    def _create_zero_statistics(self) -> Dict[str, float]:
        """Create statistics dictionary with zero values."""
        return {column: 0.0 for column in self.statistics_columns} 