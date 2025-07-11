import sys
from pathlib import Path
import logging
import geopandas as gpd

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from eu_climate.config.config import ProjectConfig
from eu_climate.utils.web_exports import WebOptimizedExporter
from eu_climate.utils.utils import setup_logging

logger = setup_logging(__name__)

def validate_gpkg_data(gpkg_file):
    """Validate GPKG data before processing."""
    try:
        gdf = gpd.read_file(gpkg_file)
        logger.info(f"GPKG Validation for {gpkg_file.name}:")
        logger.info(f"  Features: {len(gdf)}")
        logger.info(f"  CRS: {gdf.crs}")
        logger.info(f"  Bounds: {gdf.total_bounds}")
        logger.info(f"  Columns: {list(gdf.columns)}")
        
        # Check for valid geometries
        invalid_count = (~gdf.geometry.is_valid).sum()
        if invalid_count > 0:
            logger.warning(f"  Invalid geometries: {invalid_count}")
        
        # Transform to WGS84 to check bounds
        if gdf.crs != 'EPSG:4326':
            gdf_wgs84 = gdf.to_crs('EPSG:4326')
            logger.info(f"  WGS84 bounds: {gdf_wgs84.total_bounds}")
            
            # Check if WGS84 bounds are reasonable
            west, south, east, north = gdf_wgs84.total_bounds
            if not (-20 <= west <= 45 and 30 <= south <= 75):
                logger.warning(f"  WGS84 bounds outside expected European range")
                return False
        
        return len(gdf) > 0
        
    except Exception as e:
        logger.error(f"GPKG validation failed: {e}")
        return False

def find_cluster_files(config):
    """Find all cluster .gpkg files that need MBTiles regeneration."""
    cluster_output_dir = Path(config.output_dir) / "clusters"
    
    if not cluster_output_dir.exists():
        logger.error(f"Cluster output directory not found: {cluster_output_dir}")
        return []
    
    cluster_files = []
    for scenario_dir in cluster_output_dir.iterdir():
        if scenario_dir.is_dir():
            gpkg_dir = scenario_dir / "gpkg"
            if gpkg_dir.exists():
                for gpkg_file in gpkg_dir.glob("clusters_*.gpkg"):
                    if validate_gpkg_data(gpkg_file):
                        cluster_files.append(gpkg_file)
                    else:
                        logger.warning(f"Skipping invalid GPKG: {gpkg_file}")
    
    logger.info(f"Found {len(cluster_files)} valid cluster files to process")
    return cluster_files

def regenerate_mbtiles_optimized(config):
    """Regenerate MBTiles files with optimized settings and proper CRS handling."""
    
    # Initialize web exporter with updated config
    web_exporter = WebOptimizedExporter(config=config.__dict__)
    
    # Check dependencies
    deps = web_exporter.check_dependencies()
    logger.info("Dependencies check:")
    for dep, available in deps.items():
        status = '✓' if available else '✗'
        logger.info(f"  {dep}: {status}")
    
    if not deps.get('tippecanoe', False):
        logger.warning("Tippecanoe not available - will use Python fallback")
    
    # Find cluster files
    cluster_files = find_cluster_files(config)
    
    if not cluster_files:
        logger.warning("No valid cluster files found to process")
        return
    
    success_count = 0
    error_count = 0
    total_size_mb = 0
    
    for gpkg_file in cluster_files:
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {gpkg_file}")
        logger.info(f"{'='*60}")
        
        try:
            # Determine output paths
            scenario_dir = gpkg_file.parent.parent
            web_dir = scenario_dir / "web" / "mvt"
            web_dir.mkdir(parents=True, exist_ok=True)
            
            output_path = web_dir / f"{gpkg_file.stem}.mbtiles"
            layer_name = gpkg_file.stem
            
            # Remove existing MBTiles to start fresh
            if output_path.exists():
                output_path.unlink()
                logger.info(f"Removed existing MBTiles: {output_path}")
            
            logger.info(f"Creating optimized MBTiles: {output_path}")
            
            # Get optimized settings from config
            mvt_settings = config.web_exports.get('mvt_settings', {})
            min_zoom = mvt_settings.get('min_zoom', 0)
            max_zoom = mvt_settings.get('max_zoom', 12)
            simplification = mvt_settings.get('simplification', 'drop-densest-as-needed')
            
            logger.info(f"Using optimized settings: zoom {min_zoom}-{max_zoom}, {simplification}")
            
            # Export with enhanced bounds validation and CRS transformation
            success = web_exporter.export_vector_as_mvt(
                input_path=gpkg_file,
                output_path=output_path,
                layer_name=layer_name,
                min_zoom=min_zoom,
                max_zoom=max_zoom,
                simplification=simplification,
                overwrite=True
            )
            
            if success and output_path.exists():
                # Check file size
                file_size_mb = output_path.stat().st_size / (1024 * 1024)
                total_size_mb += file_size_mb
                
                if file_size_mb > 50:
                    logger.warning(f"⚠️  Large file ({file_size_mb:.2f} MB) - consider further optimization")
                else:
                    logger.info(f"✓ File size optimal: {file_size_mb:.2f} MB")
                
                # Validate the created MBTiles
                if validate_mbtiles_output(output_path):
                    logger.info(f"✓ Successfully created and validated: {output_path}")
                    success_count += 1
                else:
                    logger.error(f"✗ MBTiles validation failed: {output_path}")
                    error_count += 1
            else:
                logger.error(f"✗ Failed to create: {output_path}")
                error_count += 1
                
        except Exception as e:
            logger.error(f"✗ Error processing {gpkg_file}: {e}")
            error_count += 1
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info(f"REGENERATION SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {error_count}")
    logger.info(f"Total size: {total_size_mb:.2f} MB")
    logger.info(f"Average size: {total_size_mb/max(success_count, 1):.2f} MB per file")
    
    if success_count > 0:
        logger.info("✓ MBTiles regeneration completed successfully!")
        logger.info("The coordinate transformation issues should now be resolved.")
    else:
        logger.error("✗ No files were successfully processed.")

def validate_mbtiles_output(mbtiles_path):
    """Validate the generated MBTiles file."""
    try:
        import sqlite3
        
        conn = sqlite3.connect(mbtiles_path)
        cursor = conn.cursor()
        
        # Check metadata
        cursor.execute("SELECT name, value FROM metadata WHERE name='bounds'")
        bounds_row = cursor.fetchone()
        
        if bounds_row:
            bounds_str = bounds_row[1]
            bounds = [float(x) for x in bounds_str.split(',')]
            west, south, east, north = bounds
            
            # Validate bounds are in reasonable WGS84 range
            if not (-20 <= west <= 45 and 30 <= south <= 75 and -20 <= east <= 45 and 30 <= north <= 75):
                logger.warning(f"Bounds may be outside expected range: {bounds_str}")
                return False
            
            logger.info(f"Validated bounds: {bounds_str}")
        
        # Check tiles exist
        cursor.execute("SELECT COUNT(*) FROM tiles")
        tile_count = cursor.fetchone()[0]
        
        if tile_count == 0:
            logger.error("No tiles found in MBTiles file")
            return False
        
        logger.info(f"Validated {tile_count} tiles")
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"MBTiles validation error: {e}")
        return False

def main():
    """Main execution function."""
    try:
        # Load project configuration
        config = ProjectConfig()
        
        logger.info("Starting optimized MBTiles regeneration...")
        logger.info("This will fix CRS transformation and optimize file sizes.")
        
        regenerate_mbtiles_optimized(config)
        
    except Exception as e:
        logger.error(f"Script failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 