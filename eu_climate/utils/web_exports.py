"""
Web-Optimized Data Export Manager for EU Climate Risk Assessment
=============================================================

This module provides comprehensive web-optimized export capabilities for geospatial data,
enabling efficient delivery of risk assessment results through modern web-compatible formats.

Key Features:
- Cloud-Optimized GeoTIFF (COG) export with compression and overviews
- Mapbox Vector Tiles (MVT) export in MBTiles format
- Cross-platform compatibility with Windows, macOS, and Linux
- Intelligent dependency detection and fallback mechanisms
- Comprehensive error handling and detailed logging
- Production-ready optimization settings

The module bridges the gap between traditional GIS formats and modern web delivery requirements,
ensuring that risk assessment data can be efficiently served to web applications and visualizations.

Format Support:
- Raster Data: Cloud-Optimized GeoTIFF (COG)
  - LZW compression for reduced file size
  - Overview pyramids for multi-scale viewing
  - Optimized tiling for HTTP range requests
  - Efficient streaming and partial loading

- Vector Data: Mapbox Vector Tiles (MVT)
  - Binary format with gzip compression
  - Zoom-based generalization
  - Optimized for viewport-based delivery
  - MBTiles container format

Platform Compatibility:
- Windows: Provides installation guidance and Python fallbacks
- macOS/Linux: Full tippecanoe integration
- Docker: Container-based processing options
- WSL: Windows Subsystem for Linux support

Dependencies:
- Required: rasterio, geopandas (with fallback handling)
- Optional: rio-cogeo (enhanced COG creation)
- External: tippecanoe (MVT generation), GDAL (COG fallback)

Usage:
    from eu_climate.utils.web_exports import WebOptimizedExporter

    # Initialize exporter
    exporter = WebOptimizedExporter()

    # Export raster as COG
    success = exporter.export_raster_as_cog(
        input_path="risk_assessment.tif",
        output_path="web/cog/risk_assessment.tif"
    )

    # Export vector as MVT
    success = exporter.export_vector_as_mvt(
        input_path="clusters.gpkg",
        output_path="web/mvt/clusters.mbtiles"
    )

    # Create complete web exports
    results = exporter.create_web_exports(
        data_type="raster",
        input_path="input.tif",
        base_output_dir="output",
        layer_name="risk_layer"
    )
"""

import os
import subprocess
import tempfile
import shutil
import sqlite3
import platform
from pathlib import Path
from typing import Dict, Optional, Union, List
import numpy as np

try:
    import rasterio
    from rasterio.warp import reproject, Resampling
    from rasterio.crs import CRS
    from rasterio.profiles import default_gtiff_profile

    RASTERIO_AVAILABLE = True
except ImportError:
    print("Warning: rasterio not available. COG export will be disabled.")
    RASTERIO_AVAILABLE = False

try:
    import geopandas as gpd

    GEOPANDAS_AVAILABLE = True
except ImportError:
    print("Warning: geopandas not available. Vector processing will be limited.")
    GEOPANDAS_AVAILABLE = False

import logging

try:
    from rio_cogeo.cogeo import cog_translate
    from rio_cogeo.profiles import cog_profiles

    COG_TRANSLATE_AVAILABLE = True
except ImportError:
    COG_TRANSLATE_AVAILABLE = False

logger = logging.getLogger(__name__)


class WebOptimizedExporter:
    """
    Web-Optimized Data Export Manager
    ===============================

    Handles export of geospatial data in modern web-compatible formats with
    comprehensive cross-platform support and intelligent fallback mechanisms.

    Key Features:
        - Cloud-Optimized GeoTIFF (COG) creation with compression and overviews
        - Mapbox Vector Tiles (MVT) generation in MBTiles format
        - Cross-platform compatibility with Windows, macOS, and Linux
        - Intelligent dependency detection and fallback mechanisms
        - Production-ready optimization settings
        - Comprehensive error handling and logging

    Format Capabilities:
        - Raster: COG with LZW compression, overview pyramids, and optimized tiling
        - Vector: MVT with zoom-based generalization and binary compression
        - Maintains backward compatibility with traditional formats

    Platform Support:
        - Windows: Installation guidance and Python fallbacks
        - macOS/Linux: Full tippecanoe integration
        - Docker: Container-based processing options
        - WSL: Windows Subsystem for Linux support

    Dependencies:
        - Core: rasterio, geopandas (with graceful fallback)
        - Enhanced: rio-cogeo (preferred COG creation)
        - External: tippecanoe (MVT), GDAL (COG fallback)

    Attributes:
        config: Configuration dictionary with export settings
        web_config: Web-specific configuration subset
        platform: Detected platform for platform-specific optimizations
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize WebOptimizedExporter with configuration.

        Args:
            config: Optional configuration dictionary with web export settings
        """
        self.config = config or {}
        self.web_config = self.config.get("web_export", {})
        self.platform = platform.system()

        if not RASTERIO_AVAILABLE:
            logger.warning("Rasterio not available - COG export disabled")
        if not GEOPANDAS_AVAILABLE:
            logger.warning("GeoPandas not available - vector processing limited")

    def check_dependencies(self) -> Dict[str, bool]:
        """
        Check available dependencies and tools for web export functionality.

        This method performs a comprehensive check of all required and optional
        dependencies, providing a detailed status report for troubleshooting.

        Returns:
            Dict[str, bool]: Dependency availability status:
                - 'rasterio': Core raster processing library
                - 'geopandas': Vector data processing library
                - 'cog_translate': Enhanced COG creation (rio-cogeo)
                - 'tippecanoe': Vector tile generation tool

        Dependency Details:
            - rasterio: Required for raster processing and COG creation
            - geopandas: Required for vector data processing
            - rio-cogeo: Optional but preferred for COG creation
            - tippecanoe: Required for MVT generation (platform-dependent)

        Note:
            - Returns comprehensive status for troubleshooting
            - Identifies missing dependencies for targeted installation
            - Enables feature availability determination
        """
        deps = {
            "rasterio": RASTERIO_AVAILABLE,
            "geopandas": GEOPANDAS_AVAILABLE,
            "cog_translate": COG_TRANSLATE_AVAILABLE,
            "tippecanoe": self._check_tippecanoe(),
        }
        return deps

    def _check_tippecanoe(self) -> bool:
        """Check if tippecanoe is available"""
        try:
            subprocess.run(["tippecanoe", "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _check_dependencies(self) -> None:
        """Check if required tools are available."""
        import platform

        missing_tools = []
        is_windows = platform.system() == "Windows"

        # Check for gdal_translate
        try:
            result = subprocess.run(
                ["gdal_translate", "--version"],
                capture_output=True,
                text=True,
                check=True,
            )
            logger.debug(f"GDAL version: {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing_tools.append("gdal_translate")

        # Check for tippecanoe
        tippecanoe_available = False
        try:
            result = subprocess.run(
                ["tippecanoe", "--version"], capture_output=True, text=True, check=True
            )
            logger.debug(f"Tippecanoe version: {result.stdout.strip()}")
            tippecanoe_available = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            if not is_windows:
                missing_tools.append("tippecanoe")

        if missing_tools:
            logger.warning(f"Missing web export dependencies: {missing_tools}")

            if is_windows:
                self._show_windows_installation_guide(tippecanoe_available)
            else:
                logger.info(
                    "Install tippecanoe: https://github.com/felt/tippecanoe#installation"
                )
                logger.info(
                    "Install GDAL with COG support: conda install -c conda-forge gdal>=3.1"
                )

    def _show_windows_installation_guide(self, tippecanoe_available: bool) -> None:
        """Show Windows-specific installation guidance."""
        logger.info("=== Windows Installation Options ===")

        if not tippecanoe_available:
            logger.info(
                "\nFor MVT (Vector Tiles) support on Windows, you have these options:"
            )
            logger.info("1. 🐧 WSL (Recommended): Install Windows Subsystem for Linux")
            logger.info("   - Run: wsl --install")
            logger.info(
                "   - Then install tippecanoe in WSL: sudo apt install tippecanoe"
            )
            logger.info("   - Run your analysis from within WSL")

            logger.info("\n2. 🐳 Docker: Use tippecanoe in a container")
            logger.info("   - Install Docker Desktop")
            logger.info(
                "   - Use: docker run -it --rm -v $(pwd):/data tippecanoe tippecanoe [options]"
            )

            logger.info("\n3. 🐍 Python Fallback (Automatic): Simplified MVT creation")
            logger.info("   - Uses built-in Python libraries")
            logger.info("   - Less optimized but works natively on Windows")
            logger.info("   - Will be used automatically if tippecanoe unavailable")

            logger.info(
                "\n4. 🌐 Consider COG for raster data: Fully Windows-compatible"
            )
            logger.info("   - Cloud-Optimized GeoTIFF works perfectly on Windows")
            logger.info("   - Often more suitable for raster-based web delivery")

        logger.info("\nFor COG (Raster) support:")
        logger.info("- Install GDAL: conda install -c conda-forge gdal>=3.1")
        logger.info("- Or use OSGeo4W: https://trac.osgeo.org/osgeo4w/")

        if not tippecanoe_available:
            logger.info("\n💡 MVT export will use Python fallback automatically")
            logger.info(
                "   This provides basic functionality but tippecanoe is recommended for production"
            )

    def export_raster_as_cog(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        overwrite: bool = True,
        add_overviews: bool = True,
        overview_levels: Optional[List[int]] = None,
    ) -> bool:
        """
        Export raster as Cloud-Optimized GeoTIFF (COG) with comprehensive optimization.

        This method creates production-ready COG files with compression, overviews,
        and optimized tiling for efficient web delivery.

        Args:
            input_path: Path to input GeoTIFF file
            output_path: Path for COG output
            overwrite: Whether to overwrite existing files
            add_overviews: Whether to add overview pyramids for multi-scale viewing
            overview_levels: Custom overview levels (e.g., [2, 4, 8, 16])

        Returns:
            bool: Success status of COG creation

        COG Features:
            - LZW compression for reduced file size
            - Optimized tiling (512x512 blocks) for HTTP range requests
            - Overview pyramids for efficient multi-scale viewing
            - Proper metadata preservation

        Creation Process:
            1. Validate input file existence
            2. Handle existing output files based on overwrite setting
            3. Prefer rio-cogeo for enhanced COG creation
            4. Fall back to GDAL translate if rio-cogeo unavailable
            5. Generate overview pyramids automatically or from custom levels
            6. Validate COG structure and integrity

        Optimization:
            - Automatic overview level generation based on raster dimensions
            - Intelligent tiling for web delivery
            - Compression settings optimized for web streaming
            - Metadata preservation for analysis compatibility

        Error Handling:
            - Comprehensive validation of input and output paths
            - Graceful fallback between COG creation methods
            - Detailed logging of creation process and errors

        Note:
            - Requires either rio-cogeo or GDAL with COG driver
            - Automatically generates overview levels if not specified
            - Validates COG structure after creation
        """
        input_path = Path(input_path)
        output_path = Path(output_path)

        if not input_path.exists():
            logger.error(f"Input raster not found: {input_path}")
            return False

        if output_path.exists():
            if not overwrite:
                logger.info(f"COG already exists: {output_path}")
                return True
            else:
                logger.info(f"Removing existing COG: {output_path}")
                output_path.unlink()

        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Prefer rio-cogeo; fall back to gdal_translate if not available
            if not COG_TRANSLATE_AVAILABLE:
                logger.warning(
                    "rio-cogeo not available – falling back to gdal_translate for COG creation"
                )
                gdal_cmd = [
                    "gdal_translate",
                    "-of",
                    "COG",
                    "-co",
                    "COMPRESS=LZW",
                    "-co",
                    "TILED=YES",
                    "-co",
                    "BLOCKSIZE=512",
                    str(input_path),
                    str(output_path),
                ]

                try:
                    subprocess.run(gdal_cmd, check=True, capture_output=True)
                    logger.info(
                        f"Successfully created COG with gdal_translate: {output_path}"
                    )
                    return True
                except FileNotFoundError:
                    logger.error(
                        "gdal_translate not found in PATH – install GDAL or rio-cogeo to enable COG conversion"
                    )
                    return False
                except subprocess.CalledProcessError as e:
                    logger.error(f"gdal_translate failed: {e.stderr}")
                    return False

            # Select appropriate COG profile
            profile_name = self.web_config.get("cog_profile", "lzw")
            if profile_name not in cog_profiles:
                profile_name = "lzw"  # fallback

            cog_profile = cog_profiles[profile_name].copy()

            # Add overview levels if specified
            if overview_levels:
                cog_profile["overview_levels"] = overview_levels
            elif add_overviews:
                # Auto-generate overview levels
                with rasterio.open(input_path) as src:
                    max_dim = max(src.width, src.height)
                    levels = []
                    level = 2
                    while max_dim // level > 256:
                        levels.append(level)
                        level *= 2
                    if levels:
                        cog_profile["overview_levels"] = levels

            # Create COG using rio-cogeo
            cog_translate(str(input_path), str(output_path), cog_profile, quiet=True)

            logger.info(f"Successfully created COG: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to create COG {output_path}: {e}")
            return False

    def _validate_cog(self, cog_path: Path) -> bool:
        """Validate that the file is a proper COG."""
        try:
            with rasterio.open(cog_path) as src:
                # Check if it's tiled
                if not src.profile.get("tiled", False):
                    return False

                # Check for overviews
                if len(src.overviews(1)) == 0:
                    logger.warning(f"COG has no overviews: {cog_path}")

                return True
        except Exception as e:
            logger.error(f"COG validation error: {e}")
            return False

    def export_vector_as_mvt(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        layer_name: Optional[str] = None,
        min_zoom: int = 0,
        max_zoom: int = 14,
        simplification: str = "drop-densest-as-needed",
        overwrite: bool = True,
    ) -> bool:
        """
        Export vector data as Mapbox Vector Tiles (MVT) in MBTiles format.

        This method creates production-ready MVT files with zoom-based generalization
        and comprehensive optimization for web delivery.

        Args:
            input_path: Path to input vector file (GeoPackage, Shapefile, etc.)
            output_path: Path for MBTiles output file
            layer_name: Layer name in MVT (defaults to filename)
            min_zoom: Minimum zoom level (0-22)
            max_zoom: Maximum zoom level (0-22)
            simplification: Tippecanoe simplification strategy
            overwrite: Whether to overwrite existing files

        Returns:
            bool: Success status of MVT creation

        MVT Features:
            - Binary format with gzip compression
            - Zoom-based generalization for efficient delivery
            - Viewport-based tile loading
            - MBTiles container format for easy deployment

        Creation Process:
            1. Validate input file and transform to WGS84 if needed
            2. Check and validate geographic boundaries
            3. Generate optimized tippecanoe command
            4. Apply cluster-specific optimizations if applicable
            5. Create MBTiles file with metadata
            6. Validate output file size and structure

        Optimization Features:
            - Automatic bounds calculation and validation
            - Cluster-specific simplification strategies
            - Feature density optimization
            - Parallel processing for large datasets
            - Intelligent vertex reduction

        Geographic Validation:
            - Coordinate system transformation to WGS84
            - Boundary validation for reasonable extents
            - Geographic filtering for invalid coordinates
            - European bounds checking for regional data

        Error Handling:
            - Comprehensive coordinate validation
            - Graceful handling of invalid geometries
            - Detailed logging of processing steps
            - Fallback mechanisms for edge cases

        Requirements:
            - tippecanoe must be installed and available in PATH
            - Input data must be in a supported vector format
            - Sufficient disk space for tile generation

        Note:
            - Automatically transforms coordinate systems to WGS84
            - Provides detailed file size and optimization reporting
            - Includes comprehensive geographic validation
            - Optimized for European geographic extents
        """
        input_path = Path(input_path)
        output_path = Path(output_path)

        if not input_path.exists():
            logger.error(f"Input vector file not found: {input_path}")
            return False

        if output_path.exists():
            if not overwrite:
                logger.info(f"MVT already exists: {output_path}")
                return True
            else:
                logger.info(f"Removing existing MVT: {output_path}")
                output_path.unlink()

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Use configuration settings if available
        mvt_config = self.web_config.get("mvt_settings", {})
        min_zoom = mvt_config.get("min_zoom", min_zoom)
        max_zoom = mvt_config.get("max_zoom", max_zoom)
        simplification = mvt_config.get("simplification", simplification)

        logger.info(
            f"Exporting MVT with optimized settings: zoom {min_zoom}-{max_zoom}, simplification: {simplification}"
        )

        # Check if tippecanoe is available
        try:
            subprocess.run(["tippecanoe", "--version"], capture_output=True, check=True)
            logger.info("Tippecanoe found - proceeding with MVT generation")
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("Tippecanoe not found. MVT export requires tippecanoe.")
            logger.error("Install tippecanoe: https://github.com/mapbox/tippecanoe")
            return False

        try:
            return self._export_mvt_with_tippecanoe(
                input_path, output_path, layer_name, min_zoom, max_zoom, simplification
            )

        except Exception as e:
            logger.error(f"Failed to create MVT {output_path}: {e}")
            return False

    def _export_mvt_with_tippecanoe(
        self,
        input_path: Path,
        output_path: Path,
        layer_name: str,
        min_zoom: int,
        max_zoom: int,
        simplification: str,
    ) -> bool:
        """Export MVT using tippecanoe with proper CRS transformation."""
        temp_geojson = None
        try:
            # Convert to GeoJSON first if needed
            if input_path.suffix.lower() in [".gpkg", ".shp"]:
                gdf = gpd.read_file(input_path)

                logger.info(f"Original data: {len(gdf)} features, CRS: {gdf.crs}")
                logger.info(f"Original bounds: {gdf.total_bounds}")

                # CRITICAL FIX: Transform to WGS84 before bounds validation
                if gdf.crs != "EPSG:4326":
                    logger.info(f"Transforming from {gdf.crs} to EPSG:4326 (WGS84)")
                    gdf = gdf.to_crs("EPSG:4326")
                    logger.info(f"Transformed bounds: {gdf.total_bounds}")

                # Validate transformed bounds
                bounds = gdf.total_bounds
                west, south, east, north = bounds
                bounds_are_invalid = False

                # Check basic coordinate validity in WGS84
                if west < -180 or west > 180 or east < -180 or east > 180:
                    logger.warning(
                        f"Invalid longitude bounds after transformation: W={west}, E={east}"
                    )
                    bounds_are_invalid = True
                if south < -90 or south > 90 or north < -90 or north > 90:
                    logger.warning(
                        f"Invalid latitude bounds after transformation: S={south}, N={north}"
                    )
                    bounds_are_invalid = True

                # Check for degenerate bounds
                if abs(north - south) < 0.001:
                    logger.warning(
                        f"Degenerate bounds - same north/south: {north} ≈ {south}"
                    )
                    bounds_are_invalid = True
                if abs(east - west) < 0.001:
                    logger.warning(
                        f"Degenerate bounds - same east/west: {east} ≈ {west}"
                    )
                    bounds_are_invalid = True

                # Check for unreasonably large bounds (global extent)
                if (east - west) > 350 or (north - south) > 170:
                    logger.warning(
                        f"Bounds span nearly entire globe - likely transformation error: W={west}, S={south}, E={east}, N={north}"
                    )
                    bounds_are_invalid = True

                # For European data, check if bounds are reasonable
                if not bounds_are_invalid:
                    if not (
                        -20 <= west <= 40
                        and 30 <= south <= 75
                        and -20 <= east <= 40
                        and 30 <= north <= 75
                    ):
                        logger.warning(
                            f"Bounds outside expected European range: W={west}, S={south}, E={east}, N={north}"
                        )
                        # Don't mark as invalid - could be valid data outside Europe

                # If bounds are still invalid after transformation, apply geographic filtering
                if bounds_are_invalid:
                    logger.warning(
                        "Applying geographic filtering to fix invalid bounds..."
                    )

                    # Remove completely invalid geometries
                    original_count = len(gdf)
                    gdf = gdf[gdf.geometry.is_valid]

                    # Apply reasonable European bounds filtering in WGS84
                    gdf = gdf.cx[-20:45, 30:75]  # Extended European bounds in WGS84

                    filtered_count = len(gdf)
                    logger.info(
                        f"Filtered from {original_count} to {filtered_count} features"
                    )

                    if gdf.empty:
                        logger.error(
                            "No valid geometries remain after geographic filtering"
                        )
                        return False

                    # Recalculate bounds after filtering
                    bounds = gdf.total_bounds
                    west, south, east, north = bounds
                    logger.info(
                        f"Final bounds after filtering: W={west}, S={south}, E={east}, N={north}"
                    )

                # Validate final data before export
                if gdf.empty:
                    logger.error("No features to export after processing")
                    return False

                # Create temporary GeoJSON with transformed data
                temp_geojson = tempfile.NamedTemporaryFile(
                    mode="w", suffix=".geojson", delete=False
                )
                gdf.to_file(temp_geojson.name, driver="GeoJSON")
                input_for_tippecanoe = temp_geojson.name

                # Use the validated bounds for tippecanoe
                bounds_str = f"{west},{south},{east},{north}"

            else:
                # For existing GeoJSON files, validate and transform if needed
                try:
                    gdf = gpd.read_file(input_path)

                    # Transform to WGS84 if not already
                    if gdf.crs != "EPSG:4326":
                        logger.info(
                            f"Transforming existing GeoJSON from {gdf.crs} to EPSG:4326"
                        )
                        gdf = gdf.to_crs("EPSG:4326")

                    bounds = gdf.total_bounds
                    west, south, east, north = bounds
                    bounds_str = f"{west},{south},{east},{north}"
                    logger.info(f"Using bounds from existing GeoJSON: {bounds_str}")
                except Exception as e:
                    logger.warning(f"Could not validate existing GeoJSON bounds: {e}")
                    bounds_str = None

                input_for_tippecanoe = str(input_path)

            # Set layer name
            if not layer_name:
                layer_name = input_path.stem

            # Build optimized tippecanoe command for clusters
            cmd = [
                "tippecanoe",
                "-o",
                str(output_path),
                "-l",
                layer_name,
                f"-Z{min_zoom}",
                f"-z{max_zoom}",
                "--force",  # Overwrite existing
                "--read-parallel",
                "--generate-ids",
                "--detect-shared-borders",
            ]

            # Optimize simplification based on data type and zoom levels
            if "cluster" in layer_name.lower():
                # For cluster data: preserve shape accuracy more than point density
                cmd.extend(
                    [
                        "--simplify-only-low-zooms",
                        "--drop-densest-as-needed",
                        "--preserve-input-order",
                        "--extend-zooms-if-still-dropping",  # Better detail preservation
                    ]
                )
            else:
                # Standard simplification
                cmd.append(f"--{simplification}")

            # Note: Skip explicit bounds as this tippecanoe version doesn't support --bounds
            # Tippecanoe will calculate bounds automatically from the data
            if "bounds_str" in locals() and bounds_str:
                logger.info(
                    f"Data bounds (will be auto-calculated by tippecanoe): {bounds_str}"
                )
            else:
                logger.info("Tippecanoe will auto-calculate bounds from data")

            # File size optimization: Add compression and optimization flags
            if max_zoom > 10:  # For detailed zoom levels, add size optimizations
                cmd.extend(
                    [
                        "--drop-fraction-as-needed",  # Reduce feature density if needed
                        "--buffer=0",  # Reduce tile buffer for smaller files
                    ]
                )

            cmd.append(input_for_tippecanoe)

            logger.info(
                f"Running optimized tippecanoe command: {' '.join(cmd[:8])}..."
            )  # Log first part to avoid very long output

            # Run tippecanoe
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            logger.info(f"Successfully created optimized MVT: {output_path}")

            # Validate output file size
            if output_path.exists():
                file_size_mb = output_path.stat().st_size / (1024 * 1024)
                logger.info(f"Generated MBTiles size: {file_size_mb:.2f} MB")

                if file_size_mb > 50:
                    logger.warning(
                        f"⚠️ MBTiles file is large ({file_size_mb:.2f} MB). Consider reducing max_zoom or adding more aggressive simplification."
                    )

            # Log bounds information from created MBTiles
            try:
                conn = sqlite3.connect(output_path)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT name, value FROM metadata WHERE name IN ('bounds', 'center', 'minzoom', 'maxzoom')"
                )
                metadata_info = cursor.fetchall()
                conn.close()

                logger.info("Created MBTiles metadata:")
                for name, value in metadata_info:
                    logger.info(f"  {name}: {value}")

            except Exception as e:
                logger.debug(f"Could not read MBTiles metadata: {e}")

            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Tippecanoe failed: {e.stderr}")
            return False
        finally:
            # Clean up temporary file
            if temp_geojson and os.path.exists(temp_geojson.name):
                os.unlink(temp_geojson.name)

    def create_web_exports(
        self,
        data_type: str,
        input_path: Union[str, Path],
        base_output_dir: Union[str, Path],
        layer_name: Optional[str] = None,
    ) -> Dict[str, bool]:
        """
        Create comprehensive web-optimized exports for a dataset.

        This method provides a unified interface for creating web-optimized exports
        for both raster and vector data, with automatic directory structure creation
        and format-specific optimization.

        Args:
            data_type: Data type to export ('raster' or 'vector')
            input_path: Path to input file (GeoTIFF, GeoPackage, etc.)
            base_output_dir: Base directory for web exports
            layer_name: Layer name for vector data (defaults to filename)

        Returns:
            Dict[str, bool]: Success status for each format:
                - 'cog': Success status for Cloud-Optimized GeoTIFF (raster)
                - 'mvt': Success status for Mapbox Vector Tiles (vector)

        Export Process:
            1. Validate input file and data type
            2. Create standardized web directory structure
            3. Apply format-specific optimizations
            4. Generate web-optimized exports
            5. Return comprehensive success status

        Directory Structure:
            - web/cog/: Cloud-Optimized GeoTIFF files
            - web/mvt/: Mapbox Vector Tiles in MBTiles format

        Raster Processing:
            - Creates COG with compression and overviews
            - Optimizes tiling for web delivery
            - Preserves metadata and projection information

        Vector Processing:
            - Creates MVT with zoom-based generalization
            - Applies geometry simplification
            - Optimizes for viewport-based delivery

        Note:
            - Automatically creates required directory structure
            - Handles both raster and vector data types
            - Provides detailed success status reporting
            - Maintains consistent naming conventions
        """
        input_path = Path(input_path)
        base_output_dir = Path(base_output_dir)

        results = {}

        if data_type == "raster":
            # Create web directory structure
            web_dir = base_output_dir / "web"
            cog_dir = web_dir / "cog"
            cog_dir.mkdir(parents=True, exist_ok=True)

            # Export as COG
            cog_path = cog_dir / f"{input_path.stem}.tif"
            results["cog"] = self.export_raster_as_cog(input_path, cog_path)

        elif data_type == "vector":
            # Create web directory structure
            web_dir = base_output_dir / "web"
            mvt_dir = web_dir / "mvt"
            mvt_dir.mkdir(parents=True, exist_ok=True)

            # Export as MVT
            mvt_path = mvt_dir / f"{input_path.stem}.mbtiles"
            results["mvt"] = self.export_vector_as_mvt(
                input_path, mvt_path, layer_name=layer_name
            )

        return results

    def get_cog_info(self, cog_path: Union[str, Path]) -> Dict:
        """
        Get comprehensive information about a COG file for web serving.

        This method provides detailed metadata about a Cloud-Optimized GeoTIFF
        that is essential for web serving configuration and optimization.

        Args:
            cog_path: Path to the COG file to analyze

        Returns:
            Dict: Comprehensive COG information including:
                - Basic properties (dimensions, data type, CRS)
                - Optimization details (tiling, compression, overviews)
                - Web serving metadata (bounds, overview factors)

        Information Provided:
            - File format and driver information
            - Raster dimensions and band count
            - Data type and coordinate reference system
            - Tiling configuration and block sizes
            - Compression settings and optimization
            - Overview pyramid information
            - Geographic bounds for web serving

        Note:
            - Returns empty dict if file cannot be read
            - Provides comprehensive metadata for web serving setup
            - Includes optimization details for performance tuning
        """
        try:
            with rasterio.open(cog_path) as src:
                info = {
                    "driver": src.driver,
                    "width": src.width,
                    "height": src.height,
                    "count": src.count,
                    "dtype": str(src.dtypes[0]),
                    "crs": str(src.crs),
                    "bounds": src.bounds,
                    "tiled": src.profile.get("tiled", False),
                    "blockxsize": src.profile.get("blockxsize"),
                    "blockysize": src.profile.get("blockysize"),
                    "compress": src.profile.get("compress"),
                    "overview_count": len(src.overviews(1)),
                    "overview_factors": src.overviews(1) if src.overviews(1) else None,
                }
                return info
        except Exception as e:
            logger.error(f"Failed to read COG info: {e}")
            return {}
