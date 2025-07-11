"""
Web Export Mixin for EU Climate Risk Assessment Layers
=====================================================

This module provides a mixin class that extends existing risk assessment layers with
web-optimized export capabilities. It enables seamless integration of modern web-compatible
formats while maintaining backward compatibility with existing legacy formats.

Key Features:
- Non-intrusive mixin design for easy integration with existing layers
- Simultaneous export to legacy and web-optimized formats
- Automatic format detection and optimization
- Cluster-specific optimizations for complex geometries
- Comprehensive error handling and fallback mechanisms
- Detailed export status reporting and validation

The mixin approach allows existing layer classes to gain web export capabilities
without modifying their core functionality, maintaining clean separation of concerns.

Web Format Support:
- Raster Data: Cloud-Optimized GeoTIFF (COG) with compression and overviews
- Vector Data: Mapbox Vector Tiles (MVT) in MBTiles format
- Cluster Data: Geometry simplification and vertex reduction for web delivery
- Metadata: Structured metadata for web serving recommendations

Export Workflow:
1. Save data in legacy format (existing functionality)
2. Create web-optimized versions using WebOptimizedExporter
3. Apply format-specific optimizations
4. Generate serving metadata and recommendations
5. Return comprehensive export status

Integration Pattern:
- Inherit from WebExportMixin in layer classes
- Use save_raster_with_web_exports() instead of standard raster saving
- Use save_vector_with_web_exports() instead of standard vector saving
- Access web export paths and metadata through provided methods

Usage:
    from eu_climate.utils.web_export_mixin import WebExportMixin
    
    class MyRiskLayer(WebExportMixin, BaseRiskLayer):
        def save_results(self):
            # Save with both legacy and web formats
            results = self.save_raster_with_web_exports(
                data=self.risk_data,
                meta=self.metadata,
                output_path=self.output_path,
                layer_name="risk_assessment"
            )
            
            if results.get('cog', False):
                print("Web-optimized COG created successfully")
"""

from pathlib import Path
from typing import Dict, Optional, Union
import numpy as np
import rasterio
import geopandas as gpd

from eu_climate.utils.web_exports import WebOptimizedExporter
from eu_climate.utils.utils import setup_logging

logger = setup_logging(__name__)


class WebExportMixin:
    """
    Mixin to add web-optimized export capabilities to existing layer classes.
    
    This mixin extends existing layer classes with methods to export their
    outputs in modern web-compatible formats while maintaining existing functionality.
    
    Key Features:
        - Non-intrusive design that doesn't affect existing layer functionality
        - Simultaneous export to legacy and web-optimized formats
        - Automatic format detection and optimization
        - Comprehensive error handling with graceful fallbacks
        - Detailed export status reporting
        
    Web Format Support:
        - Raster: Cloud-Optimized GeoTIFF (COG) with compression and overviews
        - Vector: Mapbox Vector Tiles (MVT) in MBTiles format
        - Cluster: Geometry simplification for web delivery
        
    Integration:
        - Inherit from this mixin in layer classes
        - Use enhanced save methods instead of standard ones
        - Access web export utilities through provided methods
        
    Attributes:
        web_exporter: WebOptimizedExporter instance for format conversion
    """
    
    def __init__(self, *args, **kwargs):
        """
        Initialize WebExportMixin with web export capabilities.
        
        Args:
            *args: Arguments passed to parent class
            **kwargs: Keyword arguments passed to parent class
        """
        super().__init__(*args, **kwargs)
        self.web_exporter = WebOptimizedExporter()
    
    def save_raster_with_web_exports(self,
                                   data: np.ndarray,
                                   meta: dict,
                                   output_path: Union[str, Path],
                                   layer_name: str,
                                   create_web_formats: bool = True) -> Dict[str, bool]:
        """
        Save raster data in both legacy format and web-optimized formats.
        
        This method provides a comprehensive raster export solution that creates
        both traditional GeoTIFF files and modern web-optimized formats.
        
        Args:
            data: Raster data array (numpy array)
            meta: Rasterio metadata dictionary with projection and extent info
            output_path: Path for legacy GeoTIFF output
            layer_name: Layer name for metadata and web export naming
            create_web_formats: Whether to create web-optimized formats (COG)
            
        Returns:
            Dict[str, bool]: Success status for each format:
                - 'geotiff': Success status for legacy GeoTIFF
                - 'cog': Success status for Cloud-Optimized GeoTIFF
                
        Export Process:
            1. Save legacy GeoTIFF with LZW compression
            2. Add layer metadata and tags
            3. Create web-optimized COG version
            4. Apply compression and overview pyramids
            5. Validate export success
            
        Web Optimizations:
            - Cloud-Optimized GeoTIFF (COG) format
            - LZW compression for reduced file size
            - Overview pyramids for multi-scale viewing
            - Optimized tiling for HTTP range requests
            
        Error Handling:
            - Graceful fallback if web export fails
            - Detailed logging of export process
            - Preserves legacy format even if web export fails
            
        Note:
            - Legacy GeoTIFF is always created for backward compatibility
            - Web formats are created only if legacy export succeeds
            - Returns detailed status for each format
        """
        output_path = Path(output_path)
        results = {}
        
        # Save legacy GeoTIFF format (existing functionality)
        try:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Update metadata for standard GeoTIFF
            output_meta = meta.copy()
            output_meta.update({
                'driver': 'GTiff',
                'dtype': 'float32',
                'count': 1,
                'compress': 'lzw'
            })
            
            # Remove existing file if it exists
            if output_path.exists():
                output_path.unlink()
            
            # Write legacy GeoTIFF
            with rasterio.open(output_path, 'w', **output_meta) as dst:
                dst.write(data.astype(np.float32), 1)
                dst.set_band_description(1, layer_name)
                dst.update_tags(layer=layer_name, created_by='eu_climate')
            
            results['geotiff'] = True
            logger.info(f"Saved legacy GeoTIFF: {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to save legacy GeoTIFF {output_path}: {e}")
            results['geotiff'] = False
        
        # Create web-optimized formats
        if create_web_formats and results.get('geotiff', False):
            try:
                # Get base output directory (parent of tif directory)
                base_output_dir = output_path.parent.parent
                
                # Create COG version
                web_results = self.web_exporter.create_web_exports(
                    data_type='raster',
                    input_path=output_path,
                    base_output_dir=base_output_dir,
                    layer_name=layer_name
                )
                
                results.update(web_results)
                
                if web_results.get('cog', False):
                    logger.info(f"Created web-optimized COG for {layer_name}")
                
            except Exception as e:
                logger.error(f"Failed to create web exports for {layer_name}: {e}")
                results['cog'] = False
        
        return results
    
    def save_vector_with_web_exports(self,
                                   gdf: gpd.GeoDataFrame,
                                   output_path: Union[str, Path],
                                   layer_name: str,
                                   create_web_formats: bool = True,
                                   driver: str = 'GPKG') -> Dict[str, bool]:
        """
        Save vector data in both legacy format and web-optimized formats.
        
        This method provides comprehensive vector export capabilities that create
        both traditional vector formats and modern web-optimized tile formats.
        
        Args:
            gdf: GeoDataFrame to save with vector geometries and attributes
            output_path: Path for legacy output file
            layer_name: Layer name for metadata and web export naming
            create_web_formats: Whether to create web-optimized formats (MVT)
            driver: Driver for legacy format (GPKG, ESRI Shapefile, etc.)
            
        Returns:
            Dict[str, bool]: Success status for each format:
                - 'gpkg'/'shapefile': Success status for legacy format
                - 'mvt': Success status for Mapbox Vector Tiles
                
        Export Process:
            1. Apply cluster-specific optimizations if applicable
            2. Save legacy format (GeoPackage or Shapefile)
            3. Create web-optimized MVT version
            4. Apply geometry simplification for web delivery
            5. Validate export success
            
        Web Optimizations:
            - Mapbox Vector Tiles (MVT) in MBTiles format
            - Geometry simplification for reduced file size
            - Vertex reduction for complex polygons
            - Optimized for zoom-based delivery
            
        Cluster Optimizations:
            - Automatic geometry simplification
            - Vertex count reduction
            - Topology preservation options
            - Web-appropriate coordinate precision
            
        Error Handling:
            - Graceful fallback if web export fails
            - Detailed logging of export process
            - Preserves legacy format even if web export fails
            
        Note:
            - Legacy format is always created for backward compatibility
            - Web formats are created only if legacy export succeeds
            - Special handling for cluster data with complex geometries
        """
        output_path = Path(output_path)
        results = {}
        
        # Apply cluster-specific optimizations if this is cluster data
        if 'cluster' in layer_name.lower() and hasattr(self, 'cluster_config'):
            gdf = self._optimize_clusters_for_web(gdf)
        
        # Save legacy format (existing functionality)
        try:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Remove existing file if it exists
            if output_path.exists():
                output_path.unlink()
            
            # Write legacy format
            gdf.to_file(output_path, driver=driver)
            results[driver.lower()] = True
            logger.info(f"Saved legacy {driver}: {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to save legacy {driver} {output_path}: {e}")
            results[driver.lower()] = False
        
        # Create web-optimized formats
        if create_web_formats and results.get(driver.lower(), False):
            try:
                # Get base output directory
                if 'gpkg' in str(output_path):
                    base_output_dir = output_path.parent.parent
                else:
                    base_output_dir = output_path.parent
                
                # Create MVT version with cluster-specific optimization
                web_results = self.web_exporter.create_web_exports(
                    data_type='vector',
                    input_path=output_path,
                    base_output_dir=base_output_dir,
                    layer_name=layer_name
                )
                
                results.update(web_results)
                
                if web_results.get('mvt', False):
                    logger.info(f"Created web-optimized MVT for {layer_name}")
                
            except Exception as e:
                logger.error(f"Failed to create web exports for {layer_name}: {e}")
                results['mvt'] = False
        
        return results
    
    def _optimize_clusters_for_web(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Apply cluster-specific optimizations for web delivery.
        
        This method applies sophisticated geometry optimizations specifically designed
        for cluster polygons to ensure efficient web delivery while preserving
        essential shape characteristics.
        
        Args:
            gdf: Original cluster GeoDataFrame with complex geometries
            
        Returns:
            gpd.GeoDataFrame: Optimized GeoDataFrame with simplified geometries
            
        Optimization Process:
            1. Extract web optimization settings from cluster configuration
            2. Apply geometry simplification with configurable tolerance
            3. Reduce vertex count for complex polygons
            4. Preserve topology while reducing complexity
            5. Validate geometric integrity after optimization
            
        Optimization Settings:
            - max_vertices_per_polygon: Maximum vertices per polygon (default: 1000)
            - simplify_tolerance_meters: Simplification tolerance in meters (default: 100)
            - preserve_topology: Whether to preserve topology during simplification
            
        Simplification Algorithm:
            - Converts to WGS84 for web-appropriate simplification
            - Applies Douglas-Peucker algorithm for vertex reduction
            - Handles coordinate system transformations automatically
            - Provides fallback for optimization failures
            
        Web Considerations:
            - Optimized for web map rendering performance
            - Reduces file size while maintaining visual quality
            - Ensures compatibility with web mapping libraries
            - Balances detail preservation with performance
            
        Error Handling:
            - Graceful fallback to original geometry if optimization fails
            - Detailed logging of optimization process
            - Validates geometric integrity throughout process
            
        Note:
            - Specifically designed for cluster data with complex boundaries
            - Preserves essential cluster shape characteristics
            - Optimizes for web delivery without losing analytical value
        """
        try:
            from shapely.geometry import Polygon
            from shapely.ops import transform
            import numpy as np
            
            logger.info(f"Applying web optimizations to {len(gdf)} cluster polygons")
            
            # Get optimization settings
            web_opt = getattr(self.cluster_config, 'web_optimization', {})
            max_vertices = web_opt.get('max_vertices_per_polygon', 1000)
            simplify_tolerance = web_opt.get('simplify_tolerance_meters', 100)
            preserve_topology = web_opt.get('preserve_topology', True)
            
            optimized_geometries = []
            
            for idx, row in gdf.iterrows():
                geom = row.geometry
                
                if geom is None or geom.is_empty:
                    optimized_geometries.append(geom)
                    continue
                
                try:
                    # Convert to WGS84 for web optimization if not already
                    if gdf.crs != 'EPSG:4326':
                        # Transform to WGS84 for web-appropriate simplification
                        geom_wgs84 = gpd.GeoSeries([geom], crs=gdf.crs).to_crs('EPSG:4326').iloc[0]
                        
                        # Apply simplification in degrees (approximately 100m at European latitudes)
                        # 1 degree ≈ 111km, so 100m ≈ 0.0009 degrees
                        simplify_tolerance_deg = simplify_tolerance / 111000
                        
                        # Simplify geometry
                        if preserve_topology:
                            simplified = geom_wgs84.simplify(simplify_tolerance_deg, preserve_topology=True)
                        else:
                            simplified = geom_wgs84.simplify(simplify_tolerance_deg)
                        
                        # Transform back to original CRS
                        optimized_geom = gpd.GeoSeries([simplified], crs='EPSG:4326').to_crs(gdf.crs).iloc[0]
                    else:
                        # Already in WGS84, simplify directly
                        simplify_tolerance_deg = simplify_tolerance / 111000
                        if preserve_topology:
                            optimized_geom = geom.simplify(simplify_tolerance_deg, preserve_topology=True)
                        else:
                            optimized_geom = geom.simplify(simplify_tolerance_deg)
                    
                    # Check vertex count and apply additional simplification if needed
                    if hasattr(optimized_geom, 'exterior') and optimized_geom.exterior is not None:
                        vertex_count = len(optimized_geom.exterior.coords)
                        
                        if vertex_count > max_vertices:
                            # Calculate required tolerance to reach target vertex count
                            current_tolerance = simplify_tolerance_deg
                            while vertex_count > max_vertices and current_tolerance < 0.01:  # Max 0.01 degrees
                                current_tolerance *= 1.5
                                if preserve_topology:
                                    test_geom = geom.simplify(current_tolerance, preserve_topology=True)
                                else:
                                    test_geom = geom.simplify(current_tolerance)
                                
                                if hasattr(test_geom, 'exterior') and test_geom.exterior is not None:
                                    vertex_count = len(test_geom.exterior.coords)
                                    if vertex_count <= max_vertices:
                                        optimized_geom = test_geom
                                        break
                                else:
                                    break
                            
                            logger.debug(f"Reduced polygon vertices from {len(geom.exterior.coords)} to {vertex_count}")
                    
                    optimized_geometries.append(optimized_geom)
                    
                except Exception as e:
                    logger.warning(f"Failed to optimize geometry for cluster {idx}: {e}")
                    optimized_geometries.append(geom)  # Keep original if optimization fails
            
            # Create optimized GeoDataFrame
            optimized_gdf = gdf.copy()
            optimized_gdf.geometry = optimized_geometries
            
            # Remove any invalid geometries that might have been created
            optimized_gdf = optimized_gdf[optimized_gdf.geometry.is_valid]
            
            logger.info(f"Web optimization complete: {len(optimized_gdf)} valid polygons")
            
            return optimized_gdf
            
        except Exception as e:
            logger.error(f"Cluster web optimization failed: {e}")
            return gdf  # Return original if optimization fails
    
    def get_web_export_paths(self, base_output_dir: Path, layer_name: str) -> Dict[str, Path]:
        """
        Get standardized paths for web-optimized exports.
        
        This method provides standardized path generation for web-optimized export
        formats, ensuring consistent directory structure across all layers.
        
        Args:
            base_output_dir: Base output directory for the layer
            layer_name: Layer name for file naming
            
        Returns:
            Dict[str, Path]: Dictionary with standardized paths:
                - 'cog': Path for Cloud-Optimized GeoTIFF
                - 'mvt': Path for Mapbox Vector Tiles
                
        Directory Structure:
            - web/cog/: Cloud-Optimized GeoTIFF files
            - web/mvt/: Mapbox Vector Tiles in MBTiles format
            
        Note:
            - Creates consistent directory structure across all layers
            - Separates web formats from legacy formats
            - Enables efficient web serving and CDN integration
        """
        web_dir = base_output_dir / "web"
        
        return {
            'cog': web_dir / "cog" / f"{layer_name}.tif",
            'mvt': web_dir / "mvt" / f"{layer_name}.mbtiles"
        }
    
    def create_web_metadata(self, base_output_dir: Path) -> Dict:
        """
        Create comprehensive metadata file for web consumption.
        
        This method generates detailed metadata that provides guidance for web
        serving, format descriptions, and deployment recommendations.
        
        Args:
            base_output_dir: Base output directory containing web exports
            
        Returns:
            Dict: Comprehensive metadata dictionary with:
                - Format descriptions and usage guidelines
                - Serving recommendations for each format
                - Directory structure documentation
                - Performance optimization suggestions
                
        Metadata Contents:
            - Format specifications for COG and MVT
            - Web serving recommendations and best practices
            - Directory structure documentation
            - CORS and compression guidelines
            - CDN and caching recommendations
            
        Usage Guidelines:
            - COG: HTTP range requests, dynamic tiling, overview pyramids
            - MVT: Tile server integration, zoom-based delivery, binary compression
            
        Note:
            - Provides comprehensive deployment guidance
            - Includes performance optimization recommendations
            - Supports both self-hosted and CDN deployment scenarios
        """
        web_dir = base_output_dir / "web"
        metadata = {
            'formats': {
                'raster': {
                    'cog': {
                        'description': 'Cloud-Optimized GeoTIFF for efficient web delivery',
                        'directory': 'web/cog/',
                        'usage': 'Can be served directly via HTTP range requests',
                        'compression': 'LZW with overviews for multi-scale viewing'
                    }
                },
                'vector': {
                    'mvt': {
                        'description': 'Mapbox Vector Tiles in MBTiles format',
                        'directory': 'web/mvt/',
                        'usage': 'Optimized for viewport-based delivery',
                        'compression': 'Binary format with gzip compression'
                    }
                }
            },
            'serving_recommendations': {
                'cog': [
                    'Serve with HTTP/2 and gzip/brotli compression',
                    'Enable Access-Control-Allow-Origin: * for cross-origin requests',
                    'Consider using a CDN for global distribution',
                    'Use libraries like rio-tiler or titiler for dynamic tiling'
                ],
                'mvt': [
                    'Serve MBTiles directly via tile server (e.g., TileServer GL)',
                    'Enable gzip compression for .pbf tiles',
                    'Use CDN with appropriate cache headers',
                    'Configure CORS headers for web map access'
                ]
            },
            'directory_structure': {
                'web/cog/': 'Cloud-Optimized GeoTIFF files',
                'web/mvt/': 'Mapbox Vector Tiles (MBTiles)',
                'tif/': 'Legacy GeoTIFF files (for analysis)',
                'gpkg/': 'Legacy GeoPackage files (for analysis)'
            }
        }
        
        return metadata 