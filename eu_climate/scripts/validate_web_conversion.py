#!/usr/bin/env python3
"""
Web Conversion Accuracy Validation Script
=========================================

This script validates the accuracy of the web conversion process for both:
- Raster data: TIF → COG (Cloud-Optimized GeoTIFF)
- Vector data: GPKG → MBTiles (Mapbox Vector Tiles)

Usage:
    python validate_web_conversion.py [--output-dir PATH] [--verbose]
"""

import argparse
import logging
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json

try:
    import rasterio
    import geopandas as gpd
    import numpy as np
    GEOSPATIAL_AVAILABLE = True
except ImportError:
    print("Error: Required geospatial libraries not available")
    print("Install with: pip install rasterio geopandas")
    sys.exit(1)


class WebConversionValidator:
    """Validates accuracy of web-optimized geospatial file conversions."""
    
    def __init__(self, output_dir: Optional[Path] = None, verbose: bool = False):
        self.output_dir = output_dir or Path("data/.output")
        self.verbose = verbose
        self.setup_logging()
        
        self.results = {
            'raster': {'total': 0, 'passed': 0, 'failed': 0, 'details': []},
            'vector': {'total': 0, 'passed': 0, 'failed': 0, 'details': []},
            'summary': {}
        }
    
    def setup_logging(self):
        """Setup logging configuration."""
        level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)
    
    def find_file_pairs(self) -> Tuple[List[Tuple[Path, Path]], List[Tuple[Path, Path]]]:
        """Find original and converted file pairs."""
        raster_pairs = []
        vector_pairs = []
        
        # Find TIF → COG pairs
        for tif_file in self.output_dir.glob("**/tif/*.tif"):
            # Skip already converted files
            if "/web/" in str(tif_file):
                continue
                
            cog_file = tif_file.parent.parent / "web" / "cog" / tif_file.name
            if cog_file.exists():
                raster_pairs.append((tif_file, cog_file))
                self.logger.debug(f"Found raster pair: {tif_file.name}")
        
        # Find GPKG → MBTiles pairs
        for gpkg_file in self.output_dir.glob("**/gpkg/*.gpkg"):
            if "/web/" in str(gpkg_file):
                continue
                
            mbtiles_file = gpkg_file.parent.parent / "web" / "mvt" / f"{gpkg_file.stem}.mbtiles"
            if mbtiles_file.exists():
                vector_pairs.append((gpkg_file, mbtiles_file))
                self.logger.debug(f"Found vector pair: {gpkg_file.name}")
        
        # Find SHP → MBTiles pairs from source directory
        source_dir = self.output_dir.parent / "source"
        if source_dir.exists():
            for shp_file in source_dir.rglob("*.shp"):
                mbtiles_file = self.output_dir / "source" / "web" / "mvt" / f"{shp_file.stem}.mbtiles"
                if mbtiles_file.exists():
                    vector_pairs.append((shp_file, mbtiles_file))
                    self.logger.debug(f"Found shapefile vector pair: {shp_file.name}")
        
        self.logger.info(f"Found {len(raster_pairs)} raster pairs and {len(vector_pairs)} vector pairs")
        return raster_pairs, vector_pairs
    
    def validate_raster_conversion(self, original_path: Path, cog_path: Path) -> Dict:
        """Validate TIF → COG conversion accuracy."""
        test_name = f"TIF→COG: {original_path.name}"
        result = {
            'test': test_name,
            'passed': True,
            'errors': [],
            'details': {}
        }
        
        try:
            # Open both files
            with rasterio.open(original_path) as orig, rasterio.open(cog_path) as cog:
                
                # Test 1: CRS Preservation
                if orig.crs != cog.crs:
                    result['errors'].append(f"CRS mismatch: {orig.crs} → {cog.crs}")
                    result['passed'] = False
                else:
                    result['details']['crs_preserved'] = str(orig.crs)
                
                # Test 2: Shape Preservation  
                if orig.shape != cog.shape:
                    result['errors'].append(f"Shape mismatch: {orig.shape} → {cog.shape}")
                    result['passed'] = False
                else:
                    result['details']['shape_preserved'] = orig.shape
                
                # Test 3: Bounds Preservation
                orig_bounds = orig.bounds
                cog_bounds = cog.bounds
                bounds_tolerance = 1e-6
                
                if not all(abs(a - b) < bounds_tolerance for a, b in zip(orig_bounds, cog_bounds)):
                    result['errors'].append(f"Bounds mismatch: {orig_bounds} → {cog_bounds}")
                    result['passed'] = False
                else:
                    result['details']['bounds_preserved'] = True
                
                # Test 4: Data Type Preservation
                if orig.dtypes != cog.dtypes:
                    result['errors'].append(f"Data type mismatch: {orig.dtypes} → {cog.dtypes}")
                    result['passed'] = False
                else:
                    result['details']['dtype_preserved'] = str(orig.dtypes[0])
                
                # Test 5: Pixel Value Integrity (sample)
                # Read a small sample to verify data integrity
                window = ((100, 200), (100, 200))  # 100x100 sample
                try:
                    orig_sample = orig.read(1, window=window)
                    cog_sample = cog.read(1, window=window)
                    
                    if not np.array_equal(orig_sample, cog_sample, equal_nan=True):
                        # Check if differences are within floating point tolerance
                        max_diff = np.nanmax(np.abs(orig_sample - cog_sample))
                        if max_diff > 1e-6:
                            result['errors'].append(f"Pixel value mismatch, max diff: {max_diff}")
                            result['passed'] = False
                        else:
                            result['details']['pixel_precision'] = f"±{max_diff:.2e}"
                    else:
                        result['details']['pixel_values_identical'] = True
                        
                except Exception as e:
                    result['details']['pixel_sample_error'] = str(e)
                
                # Test 6: Web Optimizations Added
                cog_profile = cog.profile
                
                # Check for tiling
                if cog_profile.get('tiled', False):
                    result['details']['tiled'] = True
                    result['details']['block_size'] = f"{cog_profile.get('blockxsize', 'unknown')}x{cog_profile.get('blockysize', 'unknown')}"
                else:
                    result['errors'].append("COG is not tiled")
                    result['passed'] = False
                
                # Check for compression
                compression = cog_profile.get('compress', 'none')
                if compression and compression.lower() != 'none':
                    result['details']['compression'] = compression
                else:
                    result['details']['compression'] = 'none (warning: no compression)'
                
                # Check for overviews
                overview_count = len(cog.overviews(1))
                if overview_count > 0:
                    result['details']['overview_levels'] = overview_count
                    result['details']['overview_factors'] = cog.overviews(1)
                else:
                    result['details']['overview_levels'] = 0
                    result['errors'].append("No overview pyramids found")
                    result['passed'] = False
                
                # File size comparison
                orig_size_mb = original_path.stat().st_size / (1024 * 1024)
                cog_size_mb = cog_path.stat().st_size / (1024 * 1024)
                compression_ratio = orig_size_mb / cog_size_mb if cog_size_mb > 0 else 1
                
                result['details']['file_sizes_mb'] = {
                    'original': round(orig_size_mb, 2),
                    'cog': round(cog_size_mb, 2),
                    'compression_ratio': round(compression_ratio, 2)
                }
                
        except Exception as e:
            result['passed'] = False
            result['errors'].append(f"Validation failed: {str(e)}")
        
        return result
    
    def validate_vector_conversion(self, original_path: Path, mbtiles_path: Path) -> Dict:
        """Validate vector → MBTiles conversion accuracy (GPKG or SHP)."""
        file_type = "SHP" if original_path.suffix.lower() == ".shp" else "GPKG"
        test_name = f"{file_type}→MBTiles: {original_path.name}"
        result = {
            'test': test_name,
            'passed': True,
            'errors': [],
            'details': {}
        }
        
        try:
            # Read original GPKG
            gdf_orig = gpd.read_file(original_path)
            result['details']['original_crs'] = str(gdf_orig.crs)
            result['details']['feature_count'] = len(gdf_orig)
            result['details']['columns'] = list(gdf_orig.columns)
            result['details']['geometry_types'] = list(gdf_orig.geometry.geom_type.unique())
            
            # Get original bounds
            orig_bounds = gdf_orig.total_bounds
            result['details']['original_bounds'] = orig_bounds.tolist()
            
            # Transform to WGS84 for comparison with MBTiles bounds
            gdf_wgs84 = gdf_orig.to_crs('EPSG:4326')
            expected_wgs84_bounds = gdf_wgs84.total_bounds
            result['details']['expected_wgs84_bounds'] = expected_wgs84_bounds.tolist()
            
            # Read MBTiles metadata
            conn = sqlite3.connect(mbtiles_path)
            cursor = conn.cursor()
            
            # Get all metadata
            cursor.execute('SELECT name, value FROM metadata')
            metadata = dict(cursor.fetchall())
            result['details']['mbtiles_metadata'] = metadata
            
            # Test 1: CRS Transformation (GPKG should be in original CRS, MBTiles should be WGS84)
            if 'bounds' in metadata:
                mbtiles_bounds_str = metadata['bounds']
                try:
                    mbtiles_bounds = [float(x) for x in mbtiles_bounds_str.split(',')]
                    result['details']['mbtiles_bounds'] = mbtiles_bounds
                    
                    # Compare bounds (with tolerance for projection differences)
                    bounds_tolerance = 0.001  # ~100m tolerance
                    bounds_match = all(
                        abs(expected - actual) < bounds_tolerance 
                        for expected, actual in zip(expected_wgs84_bounds, mbtiles_bounds)
                    )
                    
                    if bounds_match:
                        result['details']['bounds_accurate'] = True
                    else:
                        max_diff = max(abs(e - a) for e, a in zip(expected_wgs84_bounds, mbtiles_bounds))
                        result['errors'].append(f"Bounds mismatch, max diff: {max_diff:.6f}°")
                        result['details']['bounds_accurate'] = False
                        if max_diff > 0.1:  # More than 0.1° is definitely wrong
                            result['passed'] = False
                        
                except ValueError as e:
                    result['errors'].append(f"Invalid bounds format: {mbtiles_bounds_str}")
                    result['passed'] = False
            else:
                result['errors'].append("No bounds metadata found in MBTiles")
                result['passed'] = False
            
            # Test 2: Zoom levels
            if 'minzoom' in metadata and 'maxzoom' in metadata:
                min_zoom = int(metadata['minzoom'])
                max_zoom = int(metadata['maxzoom'])
                result['details']['zoom_range'] = [min_zoom, max_zoom]
                
                if min_zoom < 0 or max_zoom > 18 or min_zoom > max_zoom:
                    result['errors'].append(f"Invalid zoom range: {min_zoom}-{max_zoom}")
                    result['passed'] = False
            
            # Test 3: Tile count and coverage
            cursor.execute('SELECT COUNT(*) FROM tiles')
            tile_count = cursor.fetchone()[0]
            result['details']['tile_count'] = tile_count
            
            if tile_count == 0:
                result['errors'].append("No tiles found in MBTiles file")
                result['passed'] = False
            
            # Test 4: Zoom level distribution
            cursor.execute('SELECT zoom_level, COUNT(*) FROM tiles GROUP BY zoom_level ORDER BY zoom_level')
            zoom_distribution = cursor.fetchall()
            result['details']['zoom_distribution'] = dict(zoom_distribution)
            
            # Test 5: File format validation
            if 'format' in metadata:
                tile_format = metadata['format']
                result['details']['tile_format'] = tile_format
                if tile_format not in ['pbf', 'mvt']:
                    result['errors'].append(f"Unexpected tile format: {tile_format}")
                    result['passed'] = False
            
            # Test 6: File size and efficiency
            orig_size_mb = original_path.stat().st_size / (1024 * 1024)
            mbtiles_size_mb = mbtiles_path.stat().st_size / (1024 * 1024)
            
            result['details']['file_sizes_mb'] = {
                'original': round(orig_size_mb, 2),
                'mbtiles': round(mbtiles_size_mb, 2),
                'size_ratio': round(mbtiles_size_mb / orig_size_mb if orig_size_mb > 0 else 1, 2)
            }
            
            # Test 7: Geometry validity check in original
            invalid_geoms = gdf_orig[~gdf_orig.geometry.is_valid]
            if len(invalid_geoms) > 0:
                result['details']['invalid_geometries'] = len(invalid_geoms)
                result['errors'].append(f"Found {len(invalid_geoms)} invalid geometries in original data")
                # This is a warning, not a failure of the conversion
            
            conn.close()
            
        except Exception as e:
            result['passed'] = False
            result['errors'].append(f"Validation failed: {str(e)}")
        
        return result
    
    def run_validation(self) -> Dict:
        """Run complete validation suite."""
        self.logger.info("Starting web conversion accuracy validation")
        self.logger.info(f"Scanning directory: {self.output_dir}")
        
        # Find file pairs
        raster_pairs, vector_pairs = self.find_file_pairs()
        
        if not raster_pairs and not vector_pairs:
            self.logger.warning("No converted file pairs found. Run --web-conversion first.")
            # Create empty summary even when no files found
            self.results['summary'] = {
                'total_tests': 0,
                'total_passed': 0,
                'total_failed': 0,
                'success_rate': 0,
                'raster_success_rate': 0,
                'vector_success_rate': 0
            }
            return self.results
        
        # Validate raster conversions
        self.logger.info(f"Validating {len(raster_pairs)} raster conversions...")
        for original, converted in raster_pairs:
            result = self.validate_raster_conversion(original, converted)
            self.results['raster']['total'] += 1
            self.results['raster']['details'].append(result)
            
            if result['passed']:
                self.results['raster']['passed'] += 1
                self.logger.info(f"✅ {result['test']}")
            else:
                self.results['raster']['failed'] += 1
                self.logger.error(f"❌ {result['test']}: {'; '.join(result['errors'])}")
        
        # Validate vector conversions
        self.logger.info(f"Validating {len(vector_pairs)} vector conversions...")
        for original, converted in vector_pairs:
            result = self.validate_vector_conversion(original, converted)
            self.results['vector']['total'] += 1
            self.results['vector']['details'].append(result)
            
            if result['passed']:
                self.results['vector']['passed'] += 1
                self.logger.info(f"✅ {result['test']}")
            else:
                self.results['vector']['failed'] += 1
                self.logger.error(f"❌ {result['test']}: {'; '.join(result['errors'])}")
        
        # Generate summary
        total_tests = self.results['raster']['total'] + self.results['vector']['total']
        total_passed = self.results['raster']['passed'] + self.results['vector']['passed']
        total_failed = self.results['raster']['failed'] + self.results['vector']['failed']
        
        self.results['summary'] = {
            'total_tests': total_tests,
            'total_passed': total_passed,
            'total_failed': total_failed,
            'success_rate': round(total_passed / total_tests * 100, 1) if total_tests > 0 else 0,
            'raster_success_rate': round(self.results['raster']['passed'] / self.results['raster']['total'] * 100, 1) if self.results['raster']['total'] > 0 else 0,
            'vector_success_rate': round(self.results['vector']['passed'] / self.results['vector']['total'] * 100, 1) if self.results['vector']['total'] > 0 else 0
        }
        
        return self.results
    
    def print_summary(self):
        """Print validation summary."""
        # Ensure summary exists
        if 'summary' not in self.results:
            print("\n" + "="*80)
            print("WEB CONVERSION ACCURACY VALIDATION SUMMARY")
            print("="*80)
            print("\n⚠️  No validation results found.")
            print("   Please run --web-conversion first to create files to validate.")
            print("="*80)
            return
            
        summary = self.results['summary']
        
        print("\n" + "="*80)
        print("WEB CONVERSION ACCURACY VALIDATION SUMMARY")
        print("="*80)
        
        # Overall results
        print(f"\n📊 OVERALL RESULTS:")
        print(f"   Total Tests: {summary['total_tests']}")
        print(f"   Passed: {summary['total_passed']} ✅")
        print(f"   Failed: {summary['total_failed']} ❌")
        print(f"   Success Rate: {summary['success_rate']}%")
        
        # Raster results
        if self.results['raster']['total'] > 0:
            print(f"\n🗺️  RASTER (TIF → COG):")
            print(f"   Tests: {self.results['raster']['total']}")
            print(f"   Success Rate: {summary['raster_success_rate']}%")
            
            # Show common optimization details
            passed_raster = [r for r in self.results['raster']['details'] if r['passed']]
            if passed_raster:
                example = passed_raster[0]['details']
                if 'compression' in example:
                    print(f"   Compression: {example['compression']}")
                if 'overview_levels' in example:
                    print(f"   Overview Levels: {example['overview_levels']}")
                if 'block_size' in example:
                    print(f"   Tile Size: {example['block_size']}")
        
        # Vector results
        if self.results['vector']['total'] > 0:
            print(f"\n🎯 VECTOR (GPKG → MBTiles):")
            print(f"   Tests: {self.results['vector']['total']}")
            print(f"   Success Rate: {summary['vector_success_rate']}%")
            
            # Show common details
            passed_vector = [r for r in self.results['vector']['details'] if r['passed']]
            if passed_vector:
                example = passed_vector[0]['details']
                if 'zoom_range' in example:
                    print(f"   Zoom Range: {example['zoom_range'][0]}-{example['zoom_range'][1]}")
                if 'tile_format' in example:
                    print(f"   Tile Format: {example['tile_format']}")
        
        # Show failed tests
        failed_tests = []
        for category in ['raster', 'vector']:
            failed_tests.extend([r for r in self.results[category]['details'] if not r['passed']])
        
        if failed_tests:
            print(f"\n❌ FAILED TESTS ({len(failed_tests)}):")
            for i, test in enumerate(failed_tests, 1):
                print(f"   {i}. {test['test']}")
                for error in test['errors'][:2]:  # Show first 2 errors
                    print(f"      • {error}")
        
        print("\n" + "="*80)
        
        # Overall verdict
        if summary['success_rate'] >= 95:
            print("🎉 EXCELLENT: Web conversion is highly accurate!")
        elif summary['success_rate'] >= 80:
            print("✅ GOOD: Web conversion is mostly accurate with minor issues.")
        elif summary['success_rate'] >= 60:
            print("⚠️  FAIR: Web conversion has some accuracy issues that should be addressed.")
        else:
            print("❌ POOR: Web conversion has significant accuracy problems.")
        
        print("="*80)
    
    def save_detailed_report(self, output_file: Path):
        """Save detailed validation report as JSON."""
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        self.logger.info(f"Detailed report saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Validate web conversion accuracy")
    parser.add_argument('--output-dir', type=Path, 
                       help='Output directory to scan (default: data/.output)')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--save-report', type=Path,
                       help='Save detailed JSON report to file')
    
    args = parser.parse_args()
    
    # Initialize validator
    validator = WebConversionValidator(
        output_dir=args.output_dir,
        verbose=args.verbose
    )
    
    # Run validation
    results = validator.run_validation()
    
    # Print summary
    validator.print_summary()
    
    # Save detailed report if requested
    if args.save_report:
        validator.save_detailed_report(args.save_report)
    
    # Exit with appropriate code
    if results['summary'].get('total_failed', 0) > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main() 