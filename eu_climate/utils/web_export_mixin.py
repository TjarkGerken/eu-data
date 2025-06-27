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
    """
    
    def __init__(self, *args, **kwargs):
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
        
        Args:
            data: Raster data array
            meta: Rasterio metadata dict
            output_path: Path for legacy GeoTIFF output
            layer_name: Layer name for metadata
            create_web_formats: Whether to create web-optimized formats
            
        Returns:
            Dict with success status for each format created
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
        
        Args:
            gdf: GeoDataFrame to save
            output_path: Path for legacy output
            layer_name: Layer name for metadata
            create_web_formats: Whether to create web-optimized formats
            driver: Driver for legacy format (GPKG, ESRI Shapefile, etc.)
            
        Returns:
            Dict with success status for each format created
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
        
        Args:
            gdf: Original cluster GeoDataFrame
            
        Returns:
            Optimized GeoDataFrame
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
        
        Args:
            base_output_dir: Base output directory
            layer_name: Layer name
            
        Returns:
            Dict with paths for each web format
        """
        web_dir = base_output_dir / "web"
        
        return {
            'cog': web_dir / "cog" / f"{layer_name}.tif",
            'mvt': web_dir / "mvt" / f"{layer_name}.mbtiles"
        }
    
    def create_web_metadata(self, base_output_dir: Path) -> Dict:
        """
        Create metadata file for web consumption.
        
        Args:
            base_output_dir: Base output directory
            
        Returns:
            Metadata dictionary
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