#!/usr/bin/env python3
"""
EU Climate Risk Assessment System
=================================

A comprehensive geospatial analysis tool for assessing climate risks in European regions.
This system implements a four-layer approach: Hazard, Exposition, Relevance, and Risk.

Technical Implementation:
- Robust and reproducible data processing pipeline
- ETL processes for harmonizing diverse datasets
- Standardized cartographic projections
- Risk approximation based on climate data and normalization factors
- Downsampling techniques for fine-grained spatial analysis
- Code-based visualizations in Python

Authors: EU Geolytics Team
Version: 1.0.0
"""

import os
import sys
import argparse

# Add parent directory to path to handle imports correctly
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from eu_climate.risk_layers.exposition_layer import ExpositionLayer
from eu_climate.risk_layers.hazard_layer import HazardLayer, SeaLevelScenario
from eu_climate.risk_layers.relevance_layer import RelevanceLayer
from eu_climate.risk_layers.relevance_absolute_layer import RelevanceAbsoluteLayer
from eu_climate.risk_layers.risk_layer import RiskLayer
from eu_climate.risk_layers.cluster_layer import ClusterLayer
from eu_climate.risk_layers.economic_impact_analyzer import EconomicImpactAnalyzer
from eu_climate.config.config import ProjectConfig
from eu_climate.utils.utils import setup_logging, suppress_warnings
from eu_climate.utils.data_loading import check_data_integrity, upload_data
from eu_climate.utils.cache_utils import (
    initialize_caching,
    create_cached_layers,
    print_cache_status,
)
from eu_climate.utils.caching_wrappers import cache_relevance_layer
import numpy as np
from pathlib import Path
from typing import List, Dict, Any
from enum import Enum

# Set up logging for the main module
logger = setup_logging(__name__)


class AssessmentLayer(Enum):
    """Enumeration for the risk assessment layers."""

    HAZARD = "hazard"
    EXPOSITION = "exposition"
    RELEVANCE = "relevance"
    RISK = "risk"
    POPULATION = "population"
    CLUSTERS = "clusters"
    ECONOMIC_IMPACT = "economic_impact"


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments for controlling which risk layers to process.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="EU Climate Risk Assessment System - Control which layers to process",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m main --hazard                    # Run only hazard layer analysis
  python -m main --exposition                # Run only exposition layer analysis  
  python -m main --relevance                 # Run only relevance layer analysis
  python -m main --freight-only              # Run only freight relevance layer (with Zeevart data)
  python -m main --relevance-absolute        # Run only absolute relevance layer (preserves original values)
  python -m main --risk                      # Run only risk layer analysis
  python -m main --population-relevance      # Generate population relevance layer (2025 GHS data)
  python -m main --population                # Run only population risk layer analysis
  python -m main --hazard --exposition       # Run hazard and exposition layers
  python -m main --all                       # Run all layers (default behavior)
  python -m main --verbose --freight-only    # Run freight layer with verbose logging
  python -m main --no-cache --hazard         # Run hazard layer without caching
  python -m main --no-upload --all           # Run all layers without data upload
  python -m main --clusters                  # Extract risk cluster polygons from existing results
  python -m main --web-conversion            # Convert existing .tif to .cog and .gpkg to .mbtiles for web delivery
  python -m main --upload                    # Only upload existing data to Hugging Face (skip analysis)
  python -m main --download                  # Only download data from Hugging Face (skip analysis)
        """,
    )

    # Layer selection arguments
    layer_group = parser.add_argument_group(
        "Layer Selection", "Choose which risk assessment layers to process"
    )

    layer_group.add_argument(
        "--hazard",
        action="store_true",
        help="Process Hazard Layer (sea level rise scenarios)",
    )

    layer_group.add_argument(
        "--exposition",
        action="store_true",
        help="Process Exposition Layer (building density, population)",
    )

    layer_group.add_argument(
        "--relevance",
        action="store_true",
        help="Process Relevance Layer (economic factors, GDP)",
    )

    layer_group.add_argument(
        "--freight-only",
        action="store_true",
        help="Process only Freight Relevance Layer (with enhanced Zeevart maritime data)",
    )

    layer_group.add_argument(
        "--relevance-absolute",
        action="store_true",
        help="Process Absolute Relevance Layer (preserves original values with mass conservation)",
    )

    layer_group.add_argument(
        "--risk",
        action="store_true",
        help="Process Risk Layer (integrated risk assessment)",
    )

    layer_group.add_argument(
        "--population",
        action="store_true",
        help="Process Population Risk Layer (population-based risk assessment)",
    )

    layer_group.add_argument(
        "--population-relevance",
        action="store_true",
        help="Generate Population Relevance Layer (2025 GHS population data with corrected resolution handling)",
    )

    layer_group.add_argument(
        "--clusters",
        action="store_true",
        help="Process Cluster Layer (extract risk cluster polygons from existing results)",
    )

    layer_group.add_argument(
        "--economic-impact",
        action="store_true",
        help="Process Economic Impact Analysis (extract absolute economic values from risk clusters)",
    )

    layer_group.add_argument(
        "--web-conversion",
        action="store_true",
        help="Convert existing .tif files to .cog and .gpkg files to .mbtiles for web delivery",
    )

    layer_group.add_argument(
        "--all",
        action="store_true",
        help="Process all layers (hazard, exposition, relevance, risk, population, clusters, economic-impact)",
    )

    # Configuration arguments
    config_group = parser.add_argument_group(
        "Configuration Options", "Control execution behavior and output"
    )

    config_group.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging output"
    )

    config_group.add_argument(
        "--no-cache", action="store_true", help="Disable caching system"
    )

    config_group.add_argument(
        "--no-upload", action="store_true", help="Skip data upload to Hugging Face"
    )

    config_group.add_argument(
        "--upload",
        action="store_true",
        help="Only execute data upload to Hugging Face (skip all risk analysis)",
    )

    config_group.add_argument(
        "--download",
        action="store_true",
        help="Only execute data download from Hugging Face (skip all risk analysis)",
    )

    config_group.add_argument(
        "--no-visualize", action="store_true", help="Skip visualization generation"
    )

    config_group.add_argument(
        "--output-dir", type=str, help="Custom output directory for results"
    )

    # Quality control arguments
    quality_group = parser.add_argument_group(
        "Quality Control", "Data validation and integrity checks"
    )

    quality_group.add_argument(
        "--skip-integrity-check",
        action="store_true",
        help="Skip data integrity validation",
    )

    quality_group.add_argument(
        "--force-regenerate",
        action="store_true",
        help="Force regeneration of all outputs (ignore existing files)",
    )

    args = parser.parse_args()

    # Validate arguments
    if args.upload:
        # If --upload flag is set, disable all other processing and only run upload
        args.hazard = False
        args.exposition = False
        args.relevance = False
        args.relevance_absolute = False
        args.risk = False
        args.population = False
        args.clusters = False
        args.economic_impact = False
        args.all = False
        args.no_upload = False  # Ensure upload is enabled
    elif args.download:
        # If --download flag is set, disable all other processing and only run download
        args.hazard = False
        args.exposition = False
        args.relevance = False
        args.relevance_absolute = False
        args.risk = False
        args.population = False
        args.clusters = False
        args.economic_impact = False
        args.web_conversion = False
        args.all = False
        args.no_upload = True  # Disable upload when downloading
    elif not any(
        [
            args.hazard,
            args.exposition,
            args.relevance,
            args.relevance_absolute,
            args.risk,
            args.population,
            args.population_relevance,
            args.clusters,
            args.economic_impact,
            args.web_conversion,
            args.all,
            args.freight_only,
        ]
    ):
        # If no specific layers are chosen, default to --all
        logger.info("No specific layers selected, defaulting to --all")
        args.all = True

    # If --all is specified, enable all individual layers
    if args.all:
        args.hazard = True
        args.exposition = True
        args.relevance = True
        args.relevance_absolute = True
        args.risk = True
        args.population = True
        args.clusters = True
        args.economic_impact = True

    return args


class RiskAssessment:
    """
    Risk Assessment Implementation
    ============================

    Integrates Hazard and Exposition layers to produce comprehensive
    climate risk assessments. Implements the three-layer approach:
    1. Hazard (sea level rise, climate indicators)
    2. Exposition (building density, population, economic factors)
    3. Risk (combined assessment with weighted factors)


    """

    def __init__(self, config: ProjectConfig):
        """Initialize Risk Assessment with configuration."""
        self.config = config

        # Create layer instances
        self.hazard_layer = HazardLayer(config)
        self.exposition_layer = ExpositionLayer(config)
        self.relevance_layer = RelevanceLayer(config)
        self.risk_layer = RiskLayer(config)
        self.cluster_layer = ClusterLayer(config)

        self._apply_caching()

        # Results storage
        self.risk_indices = {}
        self.risk_classifications = {}

        logger.info("Initialized Risk Assessment System")

    def _apply_caching(self):
        """Apply caching to layer instances if enabled."""
        try:
            # Create cached versions of the layers
            cached_layers = create_cached_layers(
                hazard_layer=self.hazard_layer,
                exposition_layer=self.exposition_layer,
                relevance_layer=self.relevance_layer,
                risk_assessment=self,
                config=self.config,
            )

            # Replace instances with cached versions
            if "hazard" in cached_layers:
                self.hazard_layer = cached_layers["hazard"]
            if "exposition" in cached_layers:
                self.exposition_layer = cached_layers["exposition"]
            if "relevance" in cached_layers:
                self.relevance_layer = cached_layers["relevance"]

            logger.info("Caching applied to risk assessment layers")

        except Exception as e:
            logger.warning(f"Could not apply caching: {e}")
            logger.info("Continuing without caching...")

    def run_exposition(self, config: ProjectConfig) -> None:
        logger.info("=" * 40)
        logger.info("EXPOSITION LAYER ANALYSIS")
        logger.info("=" * 40)
        exposition_layer = ExpositionLayer(config)
        exposition_layer.run_exposition_with_all_economic_layers(
            visualize=False, create_png=True, show_ports=True, show_port_buffers=False
        )

    def run_risk_assessment(
        self,
        config: ProjectConfig,
        run_hazard: bool = True,
        run_exposition: bool = True,
        run_relevance: bool = True,
        create_png_outputs: bool = True,
        visualize: bool = False,
    ) -> Dict[str, Any]:
        """
        Run the complete risk assessment process.
        This includes preparing data, calculating risk indices,
        visualizing results, and exporting to files.
        """
        logger.info("\n" + "=" * 40)
        logger.info("RISK ASSESSMENT INTEGRATION")
        logger.info("=" * 40)

        risk_layer = RiskLayer(config)

        # Run complete risk assessment with all scenario combinations
        risk_scenarios = risk_layer.run_risk_assessment(
            visualize=visualize, export_results=True
        )

        logger.info("\n" + "=" * 60)
        logger.info("ANALYSIS COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Results saved to: {config.output_dir}")

        return risk_scenarios

    def run_hazard_layer_analysis(self, config: ProjectConfig) -> None:
        """
        Run the Hazard Layer analysis for the EU Climate Risk Assessment System.

        Args:
            config: Project configuration object containing paths and settings.
        """
        logger.info("\n" + "=" * 40)
        logger.info("HAZARD LAYER ANALYSIS")
        logger.info("=" * 40)

        # Create hazard layer instance
        hazard_layer = HazardLayer(config)

        # Apply caching if enabled
        try:
            cached_layers = create_cached_layers(
                hazard_layer=hazard_layer, config=config
            )
            if "hazard" in cached_layers:
                hazard_layer = cached_layers["hazard"]
        except Exception as e:
            logger.warning(f"Could not apply caching to hazard layer: {e}")

        slr_scenarios = [
            SeaLevelScenario(
                "Current", 0.0, "Current sea level - todays scenario (2025)"
            ),
            SeaLevelScenario(
                "Conservative", 1.0, "1m sea level rise - conservative scenario (2100)"
            ),
            SeaLevelScenario(
                "Moderate", 2.0, "2m sea level rise - moderate scenario (2100)"
            ),
            SeaLevelScenario(
                "Severe", 3.0, "3m sea level rise - severe scenario (2100)"
            ),
            SeaLevelScenario(
                "Very Severe", 10.0, "10m sea level rise - very severe scenario (2300)"
            ),
            SeaLevelScenario(
                "Extreme", 15.0, "15m sea level rise - extreme scenario (2300)"
            ),
        ]

        flood_extents = hazard_layer.process_scenarios(slr_scenarios)

        # hazard_layer.visualize_hazard_assessment(flood_extents, save_plots=True)

        hazard_layer.export_results(flood_extents)

    def run_freight_relevance_only(self, config: ProjectConfig) -> None:
        """
        Run only freight relevance layer analysis with enhanced Zeevart maritime data.

        Args:
            config: Project configuration
        """
        logger.info(
            "🚛 Starting FREIGHT-ONLY relevance layer analysis with enhanced Zeevart data"
        )

        try:
            relevance_layer = RelevanceLayer(config)
            relevance_layers = relevance_layer.run_freight_relevance_only(
                visualize=True, export_tif=True
            )

            # Log freight-specific results
            if "freight" in relevance_layers:
                freight_data = relevance_layers["freight"]
                logger.info("✅ Freight relevance layer completed:")
                logger.info(f"   - Shape: {freight_data.shape}")
                logger.info(
                    f"   - Value range: {np.nanmin(freight_data):.3f} to {np.nanmax(freight_data):.3f}"
                )
                logger.info(f"   - Non-zero pixels: {np.sum(freight_data > 0):,}")
                logger.info("   - Enhanced with Zeevart maritime port data")
            else:
                logger.warning("!  Freight layer not found in results")

        except Exception as e:
            logger.error(f"❌ Error in freight relevance analysis: {str(e)}")
            raise

    def run_relevance_layer_analysis(self, config: ProjectConfig) -> None:
        """
        Run the Relevance Layer analysis for the EU Climate Risk Assessment System.

        Args:
            config: Project configuration object containing paths and settings.
        """
        logger.info("\n" + "=" * 40)
        logger.info("RELEVANCE LAYER ANALYSIS")
        logger.info("=" * 40)

        try:
            cached_relevance_layer = cache_relevance_layer(self.relevance_layer)
            self.relevance_layer = cached_relevance_layer
        except Exception as e:
            logger.warning(f"Could not apply caching to relevance layer: {e}")

        # Process relevance layer analysis
        relevance_layers = self.relevance_layer.run_relevance_analysis(
            visualize=True, export_individual_tifs=True
        )

        logger.info(
            f"Relevance layer analysis completed - Generated {len(relevance_layers)} layers"
        )

    def run_absolute_relevance_layer_analysis(self, config: ProjectConfig) -> None:
        """
        Run the Absolute Relevance Layer analysis preserving absolute values with mass conservation.

        This analysis processes GDP, Freight, HRST, and Population indicators while maintaining
        their original absolute values and ensuring total value conservation through
        spatial distribution using exposition layer weights.
        """
        logger.info("=" * 40)
        logger.info("ABSOLUTE RELEVANCE LAYER ANALYSIS")
        logger.info("=" * 40)

        try:
            absolute_relevance_layer = RelevanceAbsoluteLayer(config)

            absolute_relevance_layers = (
                absolute_relevance_layer.run_absolute_relevance_analysis(
                    visualize=True, export_individual_tifs=True
                )
            )

            logger.info(
                f"Absolute relevance layer analysis completed - Generated {len(absolute_relevance_layers)} layers"
            )

        except Exception as e:
            logger.error(f"Error in absolute relevance layer analysis: {str(e)}")
            raise

    def run_risk_layer_analysis(
        self, config: ProjectConfig
    ) -> Dict[str, Dict[str, np.ndarray]]:
        """
        Run the Risk Layer analysis for the EU Climate Risk Assessment System.

        Args:
            config: Project configuration object containing paths and settings.

        Returns:
            Dictionary of risk scenarios
        """
        logger.info("\n" + "=" * 40)
        logger.info("RISK LAYER ANALYSIS")
        logger.info("=" * 40)

        try:
            risk_layer = RiskLayer(config)

            # Run complete risk assessment
            risk_scenarios = risk_layer.run_risk_assessment(
                visualize=True, export_results=True
            )

            logger.info("Risk layer analysis completed successfully")
            logger.info(f"Processed {len(risk_scenarios)} sea level scenarios")

            return risk_scenarios

        except Exception as e:
            logger.error(f"Could not execute risk layer analysis: {e}")
            raise e

    def run_population_relevance_layer_analysis(self, config: ProjectConfig) -> Path:
        """
        Run the Population Relevance Layer generation using 2025 GHS population data.

        Args:
            config: Project configuration object containing paths and settings.

        Returns:
            Path to the generated population relevance layer TIF file
        """
        logger.info("\n" + "=" * 40)
        logger.info("POPULATION RELEVANCE LAYER GENERATION")
        logger.info("=" * 40)

        try:
            # Import the population relevance layer generator
            from eu_climate.scripts.population_relevance_layer import (
                PopulationRelevanceLayer,
            )

            # Create and run the population relevance layer generator
            population_relevance = PopulationRelevanceLayer(config)
            output_path = population_relevance.generate_population_relevance_layer()

            logger.info(
                f"Population relevance layer generation completed: {output_path}"
            )
            return output_path

        except Exception as e:
            logger.error(f"Error in population relevance layer generation: {str(e)}")
            raise e

    def run_population_risk_layer_analysis(
        self, config: ProjectConfig
    ) -> Dict[str, np.ndarray]:
        """
        Run the Population Risk Layer analysis for the EU Climate Risk Assessment System.

        Args:
            config: Project configuration object containing paths and settings.

        Returns:
            Dictionary of population risk scenarios
        """
        logger.info("\n" + "=" * 40)
        logger.info("POPULATION RISK LAYER ANALYSIS")
        logger.info("=" * 40)

        try:
            risk_layer = RiskLayer(config)

            # Run complete population risk assessment
            population_risk_scenarios = risk_layer.run_population_risk_assessment(
                visualize=True, export_results=True
            )

            logger.info("Population risk layer analysis completed successfully")
            logger.info(
                f"Processed {len(population_risk_scenarios)} sea level scenarios"
            )

            return population_risk_scenarios

        except Exception as e:
            logger.error(f"Could not execute population risk layer analysis: {e}")
            raise e

    def run_cluster_layer_analysis(self, config: ProjectConfig) -> Dict[str, Any]:
        """
        Run the Cluster Layer analysis for the EU Climate Risk Assessment System.

        Args:
            config: Project configuration object containing paths and settings.

        Returns:
            Dictionary of cluster results for all scenarios
        """
        logger.info("\n" + "=" * 40)
        logger.info("CLUSTER LAYER ANALYSIS")
        logger.info("=" * 40)

        try:
            cluster_layer = ClusterLayer(config)

            cluster_results = cluster_layer.run_cluster_analysis(
                visualize=True, export_results=True
            )

            logger.info("Cluster layer analysis completed successfully")
            logger.info(
                f"Processed {len(cluster_results)} risk scenarios for clustering"
            )

            if cluster_results:
                summary_statistics = cluster_layer.get_cluster_summary_statistics(
                    cluster_results
                )
                logger.info("Cluster summary statistics:")
                for scenario_name, stats in summary_statistics.items():
                    logger.info(
                        f"  {scenario_name}: {stats['cluster_count']} clusters, {stats.get('total_area_square_kilometers', 0):.2f} km²"
                    )

            return cluster_results

        except Exception as e:
            logger.error(f"Could not execute cluster layer analysis: {e}")
            raise e

    def run_economic_impact_analysis(self, config: ProjectConfig) -> List[Any]:
        """
        Run Economic Impact Analysis for extracting absolute economic values from risk clusters.

        Args:
            config: Project configuration object containing paths and settings.

        Returns:
            List of economic impact metrics for all scenarios
        """
        logger.info("\n" + "=" * 40)
        logger.info("ECONOMIC IMPACT ANALYSIS")
        logger.info("=" * 40)

        try:
            impact_analyzer = EconomicImpactAnalyzer(config)

            impact_metrics = impact_analyzer.run_economic_impact_analysis(
                create_visualizations=True, export_results=True
            )

            logger.info("Economic impact analysis completed successfully")
            logger.info(f"Generated impact metrics for {len(impact_metrics)} scenarios")

            if impact_metrics:
                logger.info("Economic impact summary:")
                for metrics in impact_metrics:
                    gdp_risk_pct = (
                        (
                            metrics.at_risk_gdp_millions_eur
                            / metrics.total_gdp_millions_eur
                            * 100
                        )
                        if metrics.total_gdp_millions_eur > 0
                        else 0
                    )
                    freight_risk_pct = (
                        (
                            metrics.at_risk_freight_tonnes
                            / metrics.total_freight_tonnes
                            * 100
                        )
                        if metrics.total_freight_tonnes > 0
                        else 0
                    )
                    logger.info(
                        f"  {metrics.scenario_name}: GDP at risk {gdp_risk_pct:.1f}%, Freight at risk {freight_risk_pct:.1f}%"
                    )

            return impact_metrics

        except Exception as e:
            logger.error(f"Could not execute economic impact analysis: {e}")
            raise e

    def run_web_conversion(self, config: ProjectConfig) -> Dict[str, Any]:
        """
        Convert existing files to web-optimized formats:
        - .tif files to .cog (raster data)
        - .gpkg files to .mbtiles (vector data from output)
        - .shp files to .mbtiles (vector data from source)

        This scans both output and source directories for convertible files and creates
        web-optimized versions without running any analysis.

        Args:
            config: Project configuration containing output and data paths

        Returns:
            Dict with conversion results and statistics
        """
        from eu_climate.utils.web_exports import WebOptimizedExporter
        from pathlib import Path

        logger.info("Starting web conversion of existing files")

        web_exporter = WebOptimizedExporter(config=config.__dict__)

        # Check dependencies
        deps = web_exporter.check_dependencies()
        missing_deps = [name for name, available in deps.items() if not available]
        if missing_deps:
            logger.warning(f"Missing dependencies: {missing_deps}")
            logger.info("Some conversions may fail or use fallback methods")

        results = {
            "tif_to_cog": {"success": [], "failed": []},
            "gpkg_to_mbtiles": {"success": [], "failed": []},
            "shp_to_mbtiles": {"success": [], "failed": []},
            "summary": {},
        }

        output_dir = Path(config.output_dir)
        source_dir = Path(config.data_dir)

        # Find all .tif files recursively in output directory
        tif_files = list(output_dir.rglob("*.tif"))
        logger.info(f"Found {len(tif_files)} .tif files for COG conversion")

        # Convert .tif files to .cog
        for tif_file in tif_files:
            # Skip files that are already in web/cog directory
            if "web" in tif_file.parts and "cog" in tif_file.parts:
                logger.debug(f"Skipping already converted COG: {tif_file}")
                continue

            try:
                # Determine output directory structure
                # Files are typically in: output_dir/scenario/tif/filename.tif
                # We want to create: output_dir/scenario/web/cog/filename.tif

                # Get the scenario directory (parent of tif directory)
                if tif_file.parent.name == "tif":
                    base_output_dir = tif_file.parent.parent
                else:
                    # If not in tif subdirectory, use parent directory
                    base_output_dir = tif_file.parent

                # Create web directory structure
                cog_dir = base_output_dir / "web" / "cog"
                cog_dir.mkdir(parents=True, exist_ok=True)

                # Set output path
                cog_path = cog_dir / tif_file.name

                # Skip if COG already exists and is newer than source
                if (
                    cog_path.exists()
                    and cog_path.stat().st_mtime > tif_file.stat().st_mtime
                ):
                    logger.debug(f"COG already up-to-date: {cog_path}")
                    results["tif_to_cog"]["success"].append(str(tif_file))
                    continue

                logger.info(f"Converting {tif_file.name} to COG...")

                success = web_exporter.export_raster_as_cog(
                    input_path=tif_file,
                    output_path=cog_path,
                    overwrite=True,
                    add_overviews=True,
                )

                if success:
                    results["tif_to_cog"]["success"].append(str(tif_file))
                    logger.info(f"✓ Successfully converted: {tif_file.name}")
                else:
                    results["tif_to_cog"]["failed"].append(str(tif_file))
                    logger.error(f"✗ Failed to convert: {tif_file.name}")

            except Exception as e:
                results["tif_to_cog"]["failed"].append(str(tif_file))
                logger.error(f"✗ Error converting {tif_file.name}: {e}")

        # Find all .gpkg files recursively in output directory
        gpkg_files = list(output_dir.rglob("*.gpkg"))
        logger.info(f"Found {len(gpkg_files)} .gpkg files for MBTiles conversion")

        # Convert .gpkg files to .mbtiles
        for gpkg_file in gpkg_files:
            # Skip files that are already converted or in web directory
            if "web" in gpkg_file.parts:
                logger.debug(f"Skipping file in web directory: {gpkg_file}")
                continue

            try:
                # Determine output directory structure
                # Files are typically in: output_dir/scenario/gpkg/filename.gpkg
                # We want to create: output_dir/scenario/web/mvt/filename.mbtiles

                # Get the scenario directory (parent of gpkg directory)
                if gpkg_file.parent.name == "gpkg":
                    base_output_dir = gpkg_file.parent.parent
                else:
                    # If not in gpkg subdirectory, use parent directory
                    base_output_dir = gpkg_file.parent

                # Create web directory structure
                mvt_dir = base_output_dir / "web" / "mvt"
                mvt_dir.mkdir(parents=True, exist_ok=True)

                # Set output path
                mbtiles_path = mvt_dir / f"{gpkg_file.stem}.mbtiles"

                # Skip if MBTiles already exists and is newer than source
                if (
                    mbtiles_path.exists()
                    and mbtiles_path.stat().st_mtime > gpkg_file.stat().st_mtime
                ):
                    logger.debug(f"MBTiles already up-to-date: {mbtiles_path}")
                    results["gpkg_to_mbtiles"]["success"].append(str(gpkg_file))
                    continue

                logger.info(f"Converting {gpkg_file.name} to MBTiles...")

                success = web_exporter.export_vector_as_mvt(
                    input_path=gpkg_file,
                    output_path=mbtiles_path,
                    layer_name=gpkg_file.stem,
                    min_zoom=0,
                    max_zoom=12,  # Reduced max zoom for better performance
                    overwrite=True,
                )

                if success:
                    results["gpkg_to_mbtiles"]["success"].append(str(gpkg_file))
                    logger.info(f"✓ Successfully converted: {gpkg_file.name}")
                else:
                    results["gpkg_to_mbtiles"]["failed"].append(str(gpkg_file))
                    logger.error(f"✗ Failed to convert: {gpkg_file.name}")

            except Exception as e:
                results["gpkg_to_mbtiles"]["failed"].append(str(gpkg_file))
                logger.error(f"✗ Error converting {gpkg_file.name}: {e}")

        # Find all .shp files recursively in source directory
        shp_files = list(source_dir.rglob("*.shp"))
        logger.info(f"Found {len(shp_files)} .shp files for MBTiles conversion")

        # Convert .shp files to .mbtiles
        for shp_file in shp_files:
            try:
                # Create appropriate output directory structure
                # Source files go to: output_dir/source/web/mvt/filename.mbtiles
                source_web_dir = output_dir / "source" / "web" / "mvt"
                source_web_dir.mkdir(parents=True, exist_ok=True)

                # Set output path
                mbtiles_path = source_web_dir / f"{shp_file.stem}.mbtiles"

                # Skip if MBTiles already exists and is newer than source
                if (
                    mbtiles_path.exists()
                    and mbtiles_path.stat().st_mtime > shp_file.stat().st_mtime
                ):
                    logger.debug(f"MBTiles already up-to-date: {mbtiles_path}")
                    results["shp_to_mbtiles"]["success"].append(str(shp_file))
                    continue

                logger.info(f"Converting {shp_file.name} to MBTiles...")

                success = web_exporter.export_vector_as_mvt(
                    input_path=shp_file,
                    output_path=mbtiles_path,
                    layer_name=shp_file.stem,
                    min_zoom=0,
                    max_zoom=12,  # Reduced max zoom for better performance
                    overwrite=True,
                )

                if success:
                    results["shp_to_mbtiles"]["success"].append(str(shp_file))
                    logger.info(f"✓ Successfully converted: {shp_file.name}")
                else:
                    results["shp_to_mbtiles"]["failed"].append(str(shp_file))
                    logger.error(f"✗ Failed to convert: {shp_file.name}")

            except Exception as e:
                results["shp_to_mbtiles"]["failed"].append(str(shp_file))
                logger.error(f"✗ Error converting {shp_file.name}: {e}")

        # Generate summary
        results["summary"] = {
            "total_tif_files": len(tif_files),
            "successful_cog_conversions": len(results["tif_to_cog"]["success"]),
            "failed_cog_conversions": len(results["tif_to_cog"]["failed"]),
            "total_gpkg_files": len(gpkg_files),
            "successful_gpkg_mbtiles_conversions": len(
                results["gpkg_to_mbtiles"]["success"]
            ),
            "failed_gpkg_mbtiles_conversions": len(
                results["gpkg_to_mbtiles"]["failed"]
            ),
            "total_shp_files": len(shp_files),
            "successful_shp_mbtiles_conversions": len(
                results["shp_to_mbtiles"]["success"]
            ),
            "failed_shp_mbtiles_conversions": len(results["shp_to_mbtiles"]["failed"]),
        }

        # Log summary
        summary = results["summary"]
        logger.info(f"\n{'=' * 60}")
        logger.info("WEB CONVERSION SUMMARY")
        logger.info(f"{'=' * 60}")
        logger.info(
            f"TIF to COG conversions: {summary['successful_cog_conversions']}/{summary['total_tif_files']} successful"
        )
        logger.info(
            f"GPKG to MBTiles conversions: {summary['successful_gpkg_mbtiles_conversions']}/{summary['total_gpkg_files']} successful"
        )
        logger.info(
            f"SHP to MBTiles conversions: {summary['successful_shp_mbtiles_conversions']}/{summary['total_shp_files']} successful"
        )

        total_failed = (
            summary["failed_cog_conversions"]
            + summary["failed_gpkg_mbtiles_conversions"]
            + summary["failed_shp_mbtiles_conversions"]
        )
        if total_failed > 0:
            logger.warning("Some conversions failed. Check logs for details.")
        else:
            logger.info("All conversions completed successfully!")

        return results


def run_web_conversion_standalone(config: ProjectConfig) -> Dict[str, Any]:
    """
    Standalone web conversion function that doesn't require RiskAssessment initialization.

    This scans both output and source directories for existing files and creates web-optimized versions
    without running any analysis. Useful for converting legacy outputs to modern web formats.

    Args:
        config: Project configuration containing output and data paths

    Returns:
        Dict with conversion results and statistics
    """
    from eu_climate.utils.web_exports import WebOptimizedExporter
    from pathlib import Path

    logger.info("Starting web conversion of existing files")

    web_exporter = WebOptimizedExporter(config=config.__dict__)

    # Check dependencies
    deps = web_exporter.check_dependencies()
    missing_deps = [name for name, available in deps.items() if not available]
    if missing_deps:
        logger.warning(f"Missing dependencies: {missing_deps}")
        logger.info("Some conversions may fail or use fallback methods")

    results = {
        "tif_to_cog": {"success": [], "failed": []},
        "gpkg_to_mbtiles": {"success": [], "failed": []},
        "shp_to_mbtiles": {"success": [], "failed": []},
        "summary": {},
    }

    output_dir = Path(config.output_dir)
    logger.error(output_dir)
    source_dir = Path(config.data_dir)

    # Find all .tif files recursively in output directory
    tif_files = list(output_dir.rglob("*.tif")) + list(output_dir.rglob("*.tiff"))
    logger.info(f"Found {len(tif_files)} .tif and .tiff files for COG conversion")

    # Convert .tif files to .cog
    for tif_file in tif_files:
        # Skip files that are already in web/cog directory
        if "web" in tif_file.parts and "cog" in tif_file.parts:
            logger.debug(f"Skipping already converted COG: {tif_file}")
            continue

        try:
            # Determine output directory structure
            # Files are typically in: output_dir/scenario/tif/filename.tif
            # We want to create: output_dir/scenario/web/cog/filename.tif

            # Get the scenario directory (parent of tif directory)
            if tif_file.parent.name == "tif":
                base_output_dir = tif_file.parent.parent
            else:
                # If not in tif subdirectory, use parent directory
                base_output_dir = tif_file.parent

            # Create web directory structure
            cog_dir = base_output_dir / "web" / "cog"
            cog_dir.mkdir(parents=True, exist_ok=True)

            # Set output path
            cog_path = cog_dir / tif_file.name

            # Skip if COG already exists and is newer than source
            if (
                cog_path.exists()
                and cog_path.stat().st_mtime > tif_file.stat().st_mtime
            ):
                logger.debug(f"COG already up-to-date: {cog_path}")
                results["tif_to_cog"]["success"].append(str(tif_file))
                continue

            logger.info(f"Converting {tif_file.name} to COG...")

            success = web_exporter.export_raster_as_cog(
                input_path=tif_file,
                output_path=cog_path,
                overwrite=True,
                add_overviews=True,
            )

            if success:
                results["tif_to_cog"]["success"].append(str(tif_file))
                logger.info(f"✓ Successfully converted: {tif_file.name}")
            else:
                results["tif_to_cog"]["failed"].append(str(tif_file))
                logger.error(f"✗ Failed to convert: {tif_file.name}")

        except Exception as e:
            results["tif_to_cog"]["failed"].append(str(tif_file))
            logger.error(f"✗ Error converting {tif_file.name}: {e}")

    # Find all .gpkg files recursively in output directory
    gpkg_files = list(output_dir.rglob("*.gpkg"))
    logger.info(f"Found {len(gpkg_files)} .gpkg files for MBTiles conversion")

    # Convert .gpkg files to .mbtiles
    for gpkg_file in gpkg_files:
        # Skip files that are already converted or in web directory
        if "web" in gpkg_file.parts:
            logger.debug(f"Skipping file in web directory: {gpkg_file}")
            continue

        try:
            # Determine output directory structure
            # Files are typically in: output_dir/scenario/gpkg/filename.gpkg
            # We want to create: output_dir/scenario/web/mvt/filename.mbtiles

            # Get the scenario directory (parent of gpkg directory)
            if gpkg_file.parent.name == "gpkg":
                base_output_dir = gpkg_file.parent.parent
            else:
                # If not in gpkg subdirectory, use parent directory
                base_output_dir = gpkg_file.parent

            # Create web directory structure
            mvt_dir = base_output_dir / "web" / "mvt"
            mvt_dir.mkdir(parents=True, exist_ok=True)

            # Set output path
            mbtiles_path = mvt_dir / f"{gpkg_file.stem}.mbtiles"

            # Skip if MBTiles already exists and is newer than source
            if (
                mbtiles_path.exists()
                and mbtiles_path.stat().st_mtime > gpkg_file.stat().st_mtime
            ):
                logger.debug(f"MBTiles already up-to-date: {mbtiles_path}")
                results["gpkg_to_mbtiles"]["success"].append(str(gpkg_file))
                continue

            logger.info(f"Converting {gpkg_file.name} to MBTiles...")

            success = web_exporter.export_vector_as_mvt(
                input_path=gpkg_file,
                output_path=mbtiles_path,
                layer_name=gpkg_file.stem,
                min_zoom=0,
                max_zoom=12,  # Reduced max zoom for better performance
                overwrite=True,
            )

            if success:
                results["gpkg_to_mbtiles"]["success"].append(str(gpkg_file))
                logger.info(f"✓ Successfully converted: {gpkg_file.name}")
            else:
                results["gpkg_to_mbtiles"]["failed"].append(str(gpkg_file))
                logger.error(f"✗ Failed to convert: {gpkg_file.name}")

        except Exception as e:
            results["gpkg_to_mbtiles"]["failed"].append(str(gpkg_file))
            logger.error(f"✗ Error converting {gpkg_file.name}: {e}")

    # Find all .shp files recursively in source directory
    shp_files = list(source_dir.rglob("*.shp"))
    logger.info(f"Found {len(shp_files)} .shp files for MBTiles conversion")

    # Convert .shp files to .mbtiles
    for shp_file in shp_files:
        try:
            # Create appropriate output directory structure
            # Source files go to: output_dir/source/web/mvt/filename.mbtiles
            source_web_dir = output_dir / "source" / "web" / "mvt"
            source_web_dir.mkdir(parents=True, exist_ok=True)

            # Set output path
            mbtiles_path = source_web_dir / f"{shp_file.stem}.mbtiles"

            # Skip if MBTiles already exists and is newer than source
            if (
                mbtiles_path.exists()
                and mbtiles_path.stat().st_mtime > shp_file.stat().st_mtime
            ):
                logger.debug(f"MBTiles already up-to-date: {mbtiles_path}")
                results["shp_to_mbtiles"]["success"].append(str(shp_file))
                continue

            logger.info(f"Converting {shp_file.name} to MBTiles...")

            success = web_exporter.export_vector_as_mvt(
                input_path=shp_file,
                output_path=mbtiles_path,
                layer_name=shp_file.stem,
                min_zoom=0,
                max_zoom=12,  # Reduced max zoom for better performance
                overwrite=True,
            )

            if success:
                results["shp_to_mbtiles"]["success"].append(str(shp_file))
                logger.info(f"✓ Successfully converted: {shp_file.name}")
            else:
                results["shp_to_mbtiles"]["failed"].append(str(shp_file))
                logger.error(f"✗ Failed to convert: {shp_file.name}")

        except Exception as e:
            results["shp_to_mbtiles"]["failed"].append(str(shp_file))
            logger.error(f"✗ Error converting {shp_file.name}: {e}")

    # Generate summary
    results["summary"] = {
        "total_tif_files": len(tif_files),
        "successful_cog_conversions": len(results["tif_to_cog"]["success"]),
        "failed_cog_conversions": len(results["tif_to_cog"]["failed"]),
        "total_gpkg_files": len(gpkg_files),
        "successful_gpkg_mbtiles_conversions": len(
            results["gpkg_to_mbtiles"]["success"]
        ),
        "failed_gpkg_mbtiles_conversions": len(results["gpkg_to_mbtiles"]["failed"]),
        "total_shp_files": len(shp_files),
        "successful_shp_mbtiles_conversions": len(results["shp_to_mbtiles"]["success"]),
        "failed_shp_mbtiles_conversions": len(results["shp_to_mbtiles"]["failed"]),
    }

    # Log summary
    summary = results["summary"]
    logger.info(f"\n{'=' * 60}")
    logger.info("WEB CONVERSION SUMMARY")
    logger.info(f"{'=' * 60}")
    logger.info(
        f"TIF to COG conversions: {summary['successful_cog_conversions']}/{summary['total_tif_files']} successful"
    )
    logger.info(
        f"GPKG to MBTiles conversions: {summary['successful_gpkg_mbtiles_conversions']}/{summary['total_gpkg_files']} successful"
    )
    logger.info(
        f"SHP to MBTiles conversions: {summary['successful_shp_mbtiles_conversions']}/{summary['total_shp_files']} successful"
    )

    total_failed = (
        summary["failed_cog_conversions"]
        + summary["failed_gpkg_mbtiles_conversions"]
        + summary["failed_shp_mbtiles_conversions"]
    )
    if total_failed > 0:
        logger.warning("Some conversions failed. Check logs for details.")
    else:
        logger.info("All conversions completed successfully!")

    return results


def main():
    """
    Main execution function for the EU Climate Risk Assessment System.
    """
    # Parse command line arguments
    args = parse_arguments()

    # Configure logging level based on verbose flag
    if args.verbose:
        import logging

        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("Verbose logging enabled")

    suppress_warnings()
    logger.info("=" * 60)
    logger.info("EU CLIMATE RISK ASSESSMENT SYSTEM")
    logger.info("=" * 60)

    # Log selected layers or upload-only/download-only mode
    if args.upload:
        logger.info("UPLOAD-ONLY MODE: Skipping all risk analysis layers")
    elif args.download:
        logger.info("DOWNLOAD-ONLY MODE: Skipping all risk analysis layers")
    else:
        selected_layers = []
        if args.hazard:
            selected_layers.append("Hazard")
        if args.exposition:
            selected_layers.append("Exposition")
        if args.relevance:
            selected_layers.append("Relevance")
        if args.freight_only:
            selected_layers.append("Freight-Only Relevance")
        if args.relevance_absolute:
            selected_layers.append("Absolute Relevance")
        if args.risk:
            selected_layers.append("Risk")
        if args.population:
            selected_layers.append("Population Risk")
        if args.population_relevance:
            selected_layers.append("Population Relevance")
        if args.clusters:
            selected_layers.append("Clusters")
        if args.economic_impact:
            selected_layers.append("Economic Impact")
        if args.web_conversion:
            selected_layers.append("Web Conversion")

        logger.info(f"Selected layers: {', '.join(selected_layers)}")

    if args.no_cache:
        logger.info("Caching disabled")
    if args.no_upload:
        logger.info("Data upload disabled")
    if args.no_visualize:
        logger.info("Visualization disabled")

    # Initialize project configuration
    config = ProjectConfig()

    # Override output directory if specified
    if args.output_dir:
        config.output_dir = Path(args.output_dir)
        config.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using custom output directory: {config.output_dir}")

    logger.info(f"Project initialized with data directory: {config.data_dir}")

    # Handle upload-only mode
    if args.upload:
        logger.info("\n" + "=" * 50)
        logger.info("UPLOAD-ONLY MODE: EXECUTING DATA UPLOAD")
        logger.info("=" * 50)
        try:
            upload_result = upload_data()
            if upload_result:
                logger.info(f"\n{'=' * 60}")
                logger.info("UPLOAD COMPLETED SUCCESSFULLY")
                logger.info(f"{'=' * 60}")
            else:
                logger.error("Upload failed")
                sys.exit(1)
        except Exception as e:
            logger.error(f"Error during upload: {str(e)}")
            if args.verbose:
                import traceback

                logger.error(f"Full traceback:\n{traceback.format_exc()}")
            sys.exit(1)
        return

    # Handle download-only mode
    if args.download:
        logger.info("\n" + "=" * 50)
        logger.info("DOWNLOAD-ONLY MODE: EXECUTING DATA DOWNLOAD")
        logger.info("=" * 50)
        try:
            from eu_climate.utils.data_loading import download_data

            download_result = download_data()
            if download_result:
                logger.info(f"\n{'=' * 60}")
                logger.info("DOWNLOAD COMPLETED SUCCESSFULLY")
                logger.info(f"{'=' * 60}")
            else:
                logger.error("Download failed")
                sys.exit(1)
        except Exception as e:
            logger.error(f"Error during download: {str(e)}")
            if args.verbose:
                import traceback

                logger.error(f"Full traceback:\n{traceback.format_exc()}")
            sys.exit(1)
        return

    # Handle web-conversion-only mode
    if args.web_conversion:
        logger.info("\n" + "=" * 50)
        logger.info("WEB-CONVERSION MODE: CONVERTING EXISTING FILES")
        logger.info("=" * 50)
        try:
            # Initialize project configuration
            config = ProjectConfig()

            # Override output directory if specified
            if args.output_dir:
                config.output_dir = Path(args.output_dir)
                config.output_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Using custom output directory: {config.output_dir}")

            # Run web conversion directly without initializing full RiskAssessment
            run_web_conversion_standalone(config)

            logger.info(f"\n{'=' * 60}")
            logger.info("WEB CONVERSION COMPLETED SUCCESSFULLY")
            logger.info(f"{'=' * 60}")

        except Exception as e:
            logger.error(f"Error during web conversion: {str(e)}")
            if args.verbose:
                import traceback

                logger.error(f"Full traceback:\n{traceback.format_exc()}")
            sys.exit(1)
        return

    # Normal processing mode - perform data integrity check (unless skipped)
    if not args.skip_integrity_check:
        logger.info("\n" + "=" * 40)
        logger.info("DATA INTEGRITY CHECK")
        logger.info("=" * 40)
        check_data_integrity(config)
    else:
        logger.info("Skipping data integrity check")

    # Create RiskAssessment instance
    risk_assessment = RiskAssessment(config)

    # Initialize caching system (unless disabled)
    if not args.no_cache:
        try:
            initialize_caching(config)
            logger.info("Caching system initialized")
        except Exception as e:
            logger.warning(f"Could not initialize caching: {e}")
            logger.info("Continuing without caching...")
    else:
        logger.info("Caching system disabled")

    try:
        # Execute selected layers in logical dependency order
        if args.hazard:
            logger.info(f"\n{'=' * 50}")
            logger.info("EXECUTING HAZARD LAYER ANALYSIS")
            logger.info(f"{'=' * 50}")
            risk_assessment.run_hazard_layer_analysis(config)

        if args.exposition:
            logger.info(f"\n{'=' * 50}")
            logger.info("EXECUTING EXPOSITION LAYER ANALYSIS")
            logger.info(f"{'=' * 50}")
            risk_assessment.run_exposition(config)

        if args.relevance:
            logger.info(f"\n{'=' * 50}")
            logger.info("EXECUTING RELEVANCE LAYER ANALYSIS")
            logger.info(f"{'=' * 50}")
            risk_assessment.run_relevance_layer_analysis(config)

        if args.freight_only:
            logger.info(f"\n{'=' * 50}")
            logger.info("EXECUTING FREIGHT-ONLY RELEVANCE LAYER ANALYSIS")
            logger.info(f"{'=' * 50}")
            risk_assessment.run_freight_relevance_only(config)

        if args.relevance_absolute:
            logger.info(f"\n{'=' * 50}")
            logger.info("EXECUTING ABSOLUTE RELEVANCE LAYER ANALYSIS")
            logger.info(f"{'=' * 50}")
            risk_assessment.run_absolute_relevance_layer_analysis(config)

        if args.risk:
            logger.info(f"\n{'=' * 50}")
            logger.info("EXECUTING RISK LAYER ANALYSIS")
            logger.info(f"{'=' * 50}")
            risk_scenarios = risk_assessment.run_risk_layer_analysis(config)
            logger.info(f"Risk analysis completed with {len(risk_scenarios)} scenarios")

        if args.population_relevance:
            logger.info(f"\n{'=' * 50}")
            logger.info("EXECUTING POPULATION RELEVANCE LAYER GENERATION")
            logger.info(f"{'=' * 50}")
            population_relevance_output = (
                risk_assessment.run_population_relevance_layer_analysis(config)
            )
            logger.info(
                f"Population relevance layer generation completed: {population_relevance_output}"
            )

        if args.population:
            logger.info(f"\n{'=' * 50}")
            logger.info("EXECUTING POPULATION RISK LAYER ANALYSIS")
            logger.info(f"{'=' * 50}")
            population_risk_scenarios = (
                risk_assessment.run_population_risk_layer_analysis(config)
            )
            logger.info(
                f"Population risk analysis completed with {len(population_risk_scenarios)} scenarios"
            )

        if args.clusters:
            logger.info(f"\n{'=' * 50}")
            logger.info("EXECUTING CLUSTER LAYER ANALYSIS")
            logger.info(f"{'=' * 50}")
            cluster_results = risk_assessment.run_cluster_layer_analysis(config)
            logger.info(
                f"Cluster analysis completed with results for {len(cluster_results)} scenarios"
            )

        if args.economic_impact:
            logger.info(f"\n{'=' * 50}")
            logger.info("EXECUTING ECONOMIC IMPACT ANALYSIS")
            logger.info(f"{'=' * 50}")
            impact_metrics = risk_assessment.run_economic_impact_analysis(config)
            logger.info(
                f"Economic impact analysis completed with metrics for {len(impact_metrics)} scenarios"
            )

        # Data upload (unless disabled)
        if not args.no_upload:
            logger.info("\n" + "=" * 40)
            logger.info("DATA UPLOAD CHECK")
            logger.info("=" * 40)
            upload_data()
        else:
            logger.info("Skipping data upload")

        # Print cache statistics (unless caching is disabled)
        if not args.no_cache:
            try:
                print_cache_status(config)
            except Exception as e:
                logger.debug(f"Could not print cache statistics: {e}")

        logger.info(f"\n{'=' * 60}")
        logger.info("EXECUTION COMPLETED SUCCESSFULLY")
        logger.info(f"{'=' * 60}")
        logger.info(f"Results saved to: {config.output_dir}")

    except Exception as e:
        logger.error(f"Error during analysis: {str(e)}")
        if args.verbose:
            import traceback

            logger.error(f"Full traceback:\n{traceback.format_exc()}")
        raise


if __name__ == "__main__":
    main()
