from typing import Dict, List, Optional, Tuple, Any
import rasterio
import geopandas as gpd
from pathlib import Path
from dataclasses import dataclass
import re

from eu_climate.config.config import ProjectConfig
from eu_climate.utils.utils import setup_logging
from eu_climate.utils.visualization import LayerVisualizer
from eu_climate.utils.caching_wrappers import CacheAwareMethod
from eu_climate.utils.clustering_utils import RiskClusterExtractor, RiskClusterAnalyzer
from eu_climate.utils.web_export_mixin import WebExportMixin

logger = setup_logging(__name__)


@dataclass
class ClusterConfiguration:
    """
    Configuration parameters for risk clustering analysis.

    This dataclass contains all the tunable parameters used in the clustering
    process, from initial risk thresholding to final polygon smoothing.

    Attributes:
        risk_threshold: Minimum risk value to consider for clustering (0-1 scale)
        cell_size_meters: Size of raster cells in meters for spatial analysis
        morphological_closing_disk_size: Size of morphological closing operation disk
        cluster_epsilon_multiplier: Multiplier for DBSCAN epsilon parameter
        minimum_samples: Minimum samples required for DBSCAN clustering
        alpha_parameter_divisor: Divisor for alpha-shape parameter calculation
        hole_area_threshold: Threshold for removing holes in polygons (as fraction of total area)
        minimum_polygon_area_square_meters: Minimum area for polygon retention
        smoothing_buffer_meters: Buffer distance for polygon smoothing
        polygon_simplification_tolerance: Tolerance for polygon simplification
        natural_smoothing_iterations: Number of natural smoothing iterations
        corner_rounding_radius: Radius for corner rounding in polygon smoothing
        use_contour_method: Whether to use contour-based polygon extraction
        export_formats: List of output formats to generate
    """

    risk_threshold: float = 0.25
    cell_size_meters: float = 30
    morphological_closing_disk_size: int = 3
    cluster_epsilon_multiplier: float = 1.5
    minimum_samples: int = 4
    alpha_parameter_divisor: float = 1.0
    hole_area_threshold: float = 0.10
    minimum_polygon_area_square_meters: float = 5000
    smoothing_buffer_meters: float = 45
    polygon_simplification_tolerance: float = 15
    natural_smoothing_iterations: int = 2
    corner_rounding_radius: float = 30
    use_contour_method: bool = False
    export_formats: List[str] = None

    def __post_init__(self):
        """Set default export formats if none provided."""
        if self.export_formats is None:
            self.export_formats = ["gpkg", "png"]


class ClusterLayer(WebExportMixin):
    """
    Cluster Layer Implementation for Risk Assessment
    ===============================================

    The ClusterLayer class processes risk assessment results to identify and extract
    clean polygons representing high-risk economic areas. It uses advanced clustering
    algorithms (DBSCAN) combined with alpha-shape polygon generation to create
    meaningful spatial boundaries around risk hotspots.

    The class integrates with the broader risk assessment pipeline by:
    1. Loading existing risk layer outputs from the file system
    2. Applying configurable clustering parameters
    3. Extracting risk clusters using spatial analysis
    4. Generating both vector and raster outputs
    5. Creating web-optimized formats for visualization

    Key Features:
    - Configurable risk thresholds and clustering parameters
    - Integration with existing risk layer directory structure
    - Statistical analysis of extracted clusters
    - Multiple export formats (GeoPackage, PNG, MVT)
    - Web-ready output formats for online mapping
    - Comprehensive logging and error handling

    Processing Pipeline:
    1. Load risk raster data from previous analysis steps
    2. Apply risk threshold to identify high-risk areas
    3. Use DBSCAN clustering to group spatially connected risk cells
    4. Generate alpha-shape polygons around clusters
    5. Apply morphological operations and smoothing
    6. Export results in multiple formats
    """

    def __init__(self, config: ProjectConfig):
        """
        Initialize the Cluster Layer with project configuration.

        Args:
            config: Project configuration containing paths and settings
        """
        super().__init__()
        self.config = config

        # Load clustering-specific configuration parameters
        self.cluster_config = self._load_cluster_configuration()

        # Initialize visualization and analysis components
        self.visualizer = LayerVisualizer(self.config)

        # Initialize cluster extraction engine with configuration parameters
        self.cluster_extractor = RiskClusterExtractor(
            risk_threshold=self.cluster_config.risk_threshold,
            cell_size_meters=self.cluster_config.cell_size_meters,
            morphological_closing_disk_size=self.cluster_config.morphological_closing_disk_size,
            cluster_epsilon_multiplier=self.cluster_config.cluster_epsilon_multiplier,
            minimum_samples=self.cluster_config.minimum_samples,
            alpha_parameter_divisor=self.cluster_config.alpha_parameter_divisor,
            hole_area_threshold=self.cluster_config.hole_area_threshold,
            minimum_polygon_area_square_meters=self.cluster_config.minimum_polygon_area_square_meters,
            smoothing_buffer_meters=self.cluster_config.smoothing_buffer_meters,
            polygon_simplification_tolerance=self.cluster_config.polygon_simplification_tolerance,
            natural_smoothing_iterations=self.cluster_config.natural_smoothing_iterations,
            corner_rounding_radius=self.cluster_config.corner_rounding_radius,
            use_contour_method=getattr(
                self.cluster_config, "use_contour_method", False
            ),
        )

        # Initialize statistical analysis component
        self.cluster_analyzer = RiskClusterAnalyzer()

        logger.info("Initialized Cluster Layer with configurable smoothing parameters")

    def _load_cluster_configuration(self) -> ClusterConfiguration:
        """
        Load cluster configuration from project config file.

        Extracts clustering-specific parameters from the main configuration
        and creates a ClusterConfiguration object with appropriate defaults.

        Returns:
            ClusterConfiguration: Configuration object with clustering parameters
        """
        # Extract clustering section from main config, default to empty dict
        clustering_config = getattr(self.config, "clustering", {})

        logger.info(f"Loading clustering configuration: {clustering_config}")

        # Create configuration object with values from config file or defaults
        config = ClusterConfiguration(
            risk_threshold=clustering_config.get("risk_threshold", 0.25),
            cell_size_meters=clustering_config.get("cell_size_meters", 30),
            morphological_closing_disk_size=clustering_config.get(
                "morphological_closing_disk_size", 3
            ),
            cluster_epsilon_multiplier=clustering_config.get(
                "cluster_epsilon_multiplier", 1.5
            ),
            minimum_samples=clustering_config.get("minimum_samples", 4),
            alpha_parameter_divisor=clustering_config.get(
                "alpha_parameter_divisor", 1.0
            ),
            hole_area_threshold=clustering_config.get("hole_area_threshold", 0.10),
            minimum_polygon_area_square_meters=clustering_config.get(
                "minimum_polygon_area_square_meters", 5000
            ),
            smoothing_buffer_meters=clustering_config.get(
                "smoothing_buffer_meters", 45
            ),
            polygon_simplification_tolerance=clustering_config.get(
                "polygon_simplification_tolerance", 15
            ),
            natural_smoothing_iterations=clustering_config.get(
                "natural_smoothing_iterations", 2
            ),
            corner_rounding_radius=clustering_config.get("corner_rounding_radius", 30),
            use_contour_method=clustering_config.get("use_contour_method", False),
            export_formats=clustering_config.get("export_formats", ["gpkg", "png"]),
        )

        # Log key parameters for debugging and verification
        logger.info("Applied clustering parameters:")
        logger.info(f"  - risk_threshold: {config.risk_threshold}")
        logger.info(
            f"  - cluster_epsilon_multiplier: {config.cluster_epsilon_multiplier}"
        )
        logger.info(f"  - minimum_samples: {config.minimum_samples}")
        logger.info(
            f"  - minimum_polygon_area_square_meters: {config.minimum_polygon_area_square_meters}"
        )
        logger.info(f"  - smoothing_buffer_meters: {config.smoothing_buffer_meters}")

        return config

    def load_existing_risk_outputs(self) -> Dict[str, Dict[str, str]]:
        """
        Load paths to existing risk output files from the file system.

        Scans the risk output directory for processed risk assessment files
        and filters them to include only relevant economic indicators.

        Returns:
            Dict[str, Dict[str, str]]: Nested dictionary with structure:
                {scenario_name: {file_key: file_path}}

        Note:
            Only processes GDP, Population, and Freight (combined) indicators
            to focus on economic impact analysis.
        """
        risk_output_dir = Path(self.config.output_dir) / "risk"

        # Check if risk output directory exists
        if not risk_output_dir.exists():
            logger.warning(f"Risk output directory not found: {risk_output_dir}")
            return {}

        risk_file_paths = {}

        # Iterate through scenario directories
        for scenario_dir in risk_output_dir.iterdir():
            if not scenario_dir.is_dir():
                continue

            scenario_name = scenario_dir.name
            tif_dir = scenario_dir / "tif"

            if not tif_dir.exists():
                continue

            # Collect valid risk files for this scenario
            scenario_files = {}
            for tif_file in tif_dir.glob("risk_*.tif"):
                file_stem = tif_file.stem

                # Apply filtering logic to focus on economic indicators
                if self._should_skip_file(file_stem):
                    logger.info(f"Skipping file: {file_stem}")
                    continue

                scenario_files[file_stem] = str(tif_file)

            if scenario_files:
                risk_file_paths[scenario_name] = scenario_files

        logger.info(f"Found risk outputs for {len(risk_file_paths)} scenarios")
        return risk_file_paths

    def _should_skip_file(self, file_stem: str) -> bool:
        """
        Determine whether a risk file should be skipped based on economic indicators.

        This method implements filtering logic to focus cluster analysis on
        the most relevant economic indicators for impact assessment.

        Args:
            file_stem: Filename stem (without extension) to evaluate

        Returns:
            bool: True if file should be skipped, False if it should be processed

        Note:
            Currently processes only GDP, Population, and Freight (combined)
            indicators while excluding freight loading/unloading variants.
        """
        filename_lower = file_stem.lower()

        # Define the economic indicators we want to process
        allowed_indicators = [
            "_gdp",  # Gross Domestic Product
            "_population",  # Population density/count
            "_freight",  # Combined freight activity (not loading/unloading)
        ]

        # Check if file contains any allowed indicator
        for indicator in allowed_indicators:
            if indicator in filename_lower:
                # Special handling for freight - exclude loading/unloading variants
                if indicator == "_freight":
                    if "_loading" in filename_lower or "_unloading" in filename_lower:
                        return True  # Skip freight loading/unloading
                return False  # Keep this file

        # Skip all other files (COMBINED, HRST, etc.)
        return True

    def parse_risk_filename(self, filename: str) -> Tuple[str, str, Optional[str]]:
        """
        Parse risk filename to extract scenario and economic component information.

        Extracts structured information from risk assessment filenames following
        the naming convention: risk_SLR-X-SCENARIO_ECONOMIC_INDICATOR.tif

        Args:
            filename: Risk assessment filename to parse

        Returns:
            Tuple containing:
                - slr_scenario: Sea level rise scenario identifier
                - economic_indicator: Economic indicator name
                - full_scenario_name: Complete scenario name for output naming

        Example:
            Input: "risk_SLR-1-2050_gdp.tif"
            Output: ("SLR-1-2050", "gdp", "SLR-1-2050_gdp")
        """
        # Remove file extension and risk prefix
        filename_without_extension = filename.replace(".tif", "").replace("risk_", "")

        # Extract SLR scenario using regex pattern
        slr_pattern = r"^(SLR-\d+-[^_]+)"
        match = re.match(slr_pattern, filename_without_extension)

        if not match:
            logger.warning(f"Could not parse filename: {filename}")
            return filename_without_extension, "", None

        slr_scenario = match.group(1)

        # Extract economic indicator if present
        if (
            len(filename_without_extension) > len(slr_scenario)
            and filename_without_extension[len(slr_scenario)] == "_"
        ):
            economic_indicator = filename_without_extension[len(slr_scenario) + 1 :]
        else:
            economic_indicator = None

        return slr_scenario, economic_indicator or "", filename_without_extension

    @CacheAwareMethod(
        cache_type="cluster_results",
        input_files=["output_dir"],
        config_attrs=["target_crs", "clustering"],
    )
    def process_risk_clusters_sequential(
        self, custom_risk_files: Optional[Dict[str, str]] = None, visualize: bool = True
    ) -> Dict[str, gpd.GeoDataFrame]:
        """
        Process risk outputs to extract clusters using sequential processing pattern.

        This method implements a sequential workflow: calculate -> visualize -> write
        for each scenario, providing immediate feedback and allowing for process
        monitoring during long-running operations.

        Args:
            custom_risk_files: Optional dictionary of custom risk files to process
                              instead of scanning the file system
            visualize: Whether to create visualization plots during processing

        Returns:
            Dict[str, gpd.GeoDataFrame]: Dictionary mapping file keys to cluster results

        Note:
            This method is cached based on output directory, CRS, and clustering
            configuration to avoid redundant processing.
        """
        logger.info(
            "Starting sequential cluster processing: calculate -> visualize -> write per scenario"
        )

        # Determine input files - either custom or from file system scan
        if custom_risk_files:
            risk_file_paths = {"custom": custom_risk_files}
        else:
            risk_file_paths = self.load_existing_risk_outputs()

        if not risk_file_paths:
            logger.warning("No risk outputs found for cluster processing")
            return {}

        all_cluster_results = {}

        # Process each scenario sequentially
        for scenario_name, scenario_files in risk_file_paths.items():
            logger.info(f"\n-> Processing scenario: {scenario_name}")

            # Process each file in the scenario
            for file_key, file_path in scenario_files.items():
                logger.info(f"  -> Calculate clusters for: {file_key}")

                # Extract clusters from single risk file
                cluster_result = self._process_single_risk_file(file_path, file_key)

                if not cluster_result.empty:
                    all_cluster_results[file_key] = cluster_result
                    logger.info(f"  + Calculated: {len(cluster_result)} clusters")

                    # Immediately visualize and export results
                    logger.info(f"  -> Visualize & Write: {file_key}")
                    self._export_single_cluster_result(
                        file_key, cluster_result, visualize
                    )
                    logger.info(f"  + Completed processing for: {file_key}")
                else:
                    logger.info(f"  ! No clusters found in: {file_key}")

            logger.info(f"+ Scenario {scenario_name} complete")

        logger.info(
            f"\n+ Sequential cluster processing complete: {len(all_cluster_results)} scenarios processed"
        )
        return all_cluster_results

    def process_risk_clusters(
        self, custom_risk_files: Optional[Dict[str, str]] = None
    ) -> Dict[str, gpd.GeoDataFrame]:
        """
        Legacy batch processing method for risk clusters.

        Processes all clusters in batch mode without creating visualizations.
        This method is maintained for backward compatibility but sequential
        processing is recommended for better monitoring and feedback.

        Args:
            custom_risk_files: Optional dictionary of custom risk files to process

        Returns:
            Dict[str, gpd.GeoDataFrame]: Dictionary mapping file keys to cluster results
        """
        logger.info("Processing risk clusters from existing outputs (batch mode)...")

        # Determine input files
        if custom_risk_files:
            risk_file_paths = {"custom": custom_risk_files}
        else:
            risk_file_paths = self.load_existing_risk_outputs()

        if not risk_file_paths:
            logger.warning("No risk outputs found for cluster processing")
            return {}

        all_cluster_results = {}

        # Process all scenarios in batch
        for scenario_name, scenario_files in risk_file_paths.items():
            logger.info(f"Processing clusters for scenario: {scenario_name}")

            for file_key, file_path in scenario_files.items():
                cluster_result = self._process_single_risk_file(file_path, file_key)

                if not cluster_result.empty:
                    all_cluster_results[file_key] = cluster_result
                    logger.info(
                        f"Extracted {len(cluster_result)} clusters from {file_key}"
                    )
                else:
                    logger.info(f"No clusters found in {file_key}")

        logger.info(f"Processed clusters for {len(all_cluster_results)} risk scenarios")
        return all_cluster_results

    def _process_single_risk_file(
        self, file_path: str, file_key: str
    ) -> gpd.GeoDataFrame:
        """
        Process a single risk file to extract cluster polygons.

        This method handles the core cluster extraction workflow for a single
        risk assessment file, including data loading, cluster extraction,
        and statistical enhancement.

        Args:
            file_path: Path to the risk assessment GeoTIFF file
            file_key: Identifier key for the risk file

        Returns:
            gpd.GeoDataFrame: GeoDataFrame containing extracted cluster polygons
                             with enhanced statistical attributes
        """
        try:
            # Load risk raster data
            with rasterio.open(file_path) as risk_source:
                risk_data = risk_source.read(1)  # Read first band
                transform = risk_source.transform
                crs = risk_source.crs

            # Extract clusters using configured parameters
            clusters = self.cluster_extractor.extract_risk_clusters(
                risk_data=risk_data, transform=transform, target_crs=str(crs)
            )

            # Enhance clusters with statistical information if any were found
            if not clusters.empty:
                enhanced_clusters = (
                    self.cluster_analyzer.enhance_clusters_with_statistics(
                        cluster_geodataframe=clusters,
                        risk_data=risk_data,
                        transform=transform,
                    )
                )
                return enhanced_clusters

        except Exception as e:
            logger.error(f"Failed to process risk file {file_path}: {e}")

        # Return empty GeoDataFrame if processing failed
        return gpd.GeoDataFrame(
            {"geometry": [], "risk_cluster_id": []}, crs=self.config.target_crs
        )

    def export_cluster_results(
        self,
        cluster_results: Dict[str, gpd.GeoDataFrame],
        create_visualizations: bool = True,
    ) -> None:
        """
        Legacy batch export method for cluster results.

        Exports all cluster results at once without individual progress tracking.
        This method is maintained for backward compatibility.

        Args:
            cluster_results: Dictionary of cluster results to export
            create_visualizations: Whether to create PNG visualizations
        """
        logger.info("Exporting cluster results (batch mode)...")

        # Export each cluster result
        for file_key, cluster_geodataframe in cluster_results.items():
            if cluster_geodataframe.empty:
                logger.info(f"Skipping empty cluster result: {file_key}")
                continue

            self._export_single_cluster_result(
                file_key, cluster_geodataframe, create_visualizations
            )

        logger.info("Batch cluster export complete")

    def _export_single_cluster_result(
        self,
        file_key: str,
        cluster_geodataframe: gpd.GeoDataFrame,
        create_visualizations: bool,
        create_web_formats: bool = True,
    ) -> None:
        """
        Export a single cluster result in multiple formats.

        Handles the export of cluster results to various formats including
        GeoPackage, PNG visualizations, and web-optimized formats (MVT).

        Args:
            file_key: Identifier key for the cluster result
            cluster_geodataframe: GeoDataFrame containing cluster polygons
            create_visualizations: Whether to create PNG visualizations
            create_web_formats: Whether to create web-optimized formats
        """
        # Parse filename to determine output structure
        slr_scenario, economic_indicator, full_scenario_name = self.parse_risk_filename(
            file_key
        )

        # Create output directory following risk layer structure
        output_dir = self._create_cluster_output_directory(slr_scenario)

        cluster_filename = f"clusters_{full_scenario_name}"

        # Export GeoPackage format if requested
        if "gpkg" in self.cluster_config.export_formats:
            gpkg_path = output_dir / "gpkg" / f"{cluster_filename}.gpkg"
            gpkg_path.parent.mkdir(parents=True, exist_ok=True)

            # Use the web export mixin to save both legacy and web formats
            results = self.save_vector_with_web_exports(
                gdf=cluster_geodataframe,
                output_path=gpkg_path,
                layer_name=cluster_filename,
                create_web_formats=create_web_formats,
            )

            if results.get("gpkg", False):
                logger.info(f"Saved cluster GeoPackage: {gpkg_path}")
            if results.get("mvt", False):
                logger.info(
                    f"Created web-optimized MVT for cluster: {cluster_filename}"
                )

        # Create PNG visualization if requested
        if create_visualizations and "png" in self.cluster_config.export_formats:
            png_path = output_dir / f"{cluster_filename}.png"
            self._create_cluster_visualization(
                cluster_geodataframe, png_path, full_scenario_name
            )

    def _create_cluster_output_directory(self, slr_scenario: str) -> Path:
        """
        Create output directory following the established risk layer structure.

        Args:
            slr_scenario: Sea level rise scenario identifier

        Returns:
            Path: Path to the created output directory
        """
        cluster_output_dir = self.config.output_dir / "clusters" / slr_scenario
        cluster_output_dir.mkdir(parents=True, exist_ok=True)
        return cluster_output_dir

    def _create_cluster_visualization(
        self,
        cluster_geodataframe: gpd.GeoDataFrame,
        output_path: Path,
        scenario_title: str,
    ) -> None:
        """
        Create a scientific-style visualization of cluster polygons.

        Generates a publication-quality plot showing cluster polygons overlaid
        on administrative boundaries with statistical information.

        Args:
            cluster_geodataframe: GeoDataFrame containing cluster polygons
            output_path: Path where the visualization should be saved
            scenario_title: Title for the visualization
        """
        import matplotlib.pyplot as plt
        from eu_climate.utils.visualization import ScientificStyle

        # Create figure with scientific styling
        fig, ax = plt.subplots(
            figsize=ScientificStyle.FIGURE_SIZE, dpi=ScientificStyle.DPI
        )

        # Add administrative boundaries as context
        nuts_geodataframe = self.visualizer.get_nuts_boundaries("L3")
        if nuts_geodataframe is not None:
            nuts_geodataframe.boundary.plot(
                ax=ax,
                color=ScientificStyle.NUTS_BOUNDARY_COLOR,
                linewidth=ScientificStyle.NUTS_BOUNDARY_WIDTH,
                alpha=ScientificStyle.NUTS_BOUNDARY_ALPHA,
                zorder=1,
            )

        # Plot cluster polygons with distinctive styling
        cluster_geodataframe.plot(
            ax=ax,
            facecolor="red",
            edgecolor="darkred",
            alpha=0.7,
            linewidth=1,
            zorder=10,
        )

        # Calculate summary statistics for display
        cluster_count = len(cluster_geodataframe)
        total_area = (
            cluster_geodataframe["cluster_area_square_meters"].sum() / 1_000_000
        )  # Convert to km²

        # Set plot title and labels
        title = f"Risk Clusters: {scenario_title.replace('_', ' ').title()}"
        ax.set_title(
            title, fontsize=ScientificStyle.TITLE_SIZE, fontweight="bold", pad=20
        )
        ax.set_xlabel("Easting (m)", fontsize=ScientificStyle.LABEL_SIZE)
        ax.set_ylabel("Northing (m)", fontsize=ScientificStyle.LABEL_SIZE)

        # Create statistics text box
        statistics_text = f"Clusters: {cluster_count}\nTotal Area: {total_area:.2f} km²"

        # Add risk statistics if clusters exist
        if cluster_count > 0:
            mean_risk = cluster_geodataframe["mean_risk_value"].mean()
            max_risk = cluster_geodataframe["max_risk_value"].max()
            statistics_text += f"\nMean Risk: {mean_risk:.3f}\nMax Risk: {max_risk:.3f}"

        # Add statistics text box to plot
        ax.text(
            0.02,
            0.98,
            statistics_text,
            transform=ax.transAxes,
            verticalalignment="top",
            horizontalalignment="left",
            bbox=ScientificStyle.STATS_BOX_PROPS,
            fontsize=ScientificStyle.TICK_SIZE,
        )

        # Apply final styling
        ax.grid(False)
        ax.set_aspect("equal")

        # Save the visualization
        plt.tight_layout()
        plt.savefig(
            output_path,
            dpi=ScientificStyle.DPI,
            bbox_inches="tight",
            facecolor="white",
            edgecolor="none",
        )
        plt.close()

        logger.info(f"Saved cluster visualization: {output_path}")

    def run_cluster_analysis(
        self,
        visualize: bool = True,
        export_results: bool = True,
        custom_risk_files: Optional[Dict[str, str]] = None,
    ) -> Dict[str, gpd.GeoDataFrame]:
        """
        Run the complete cluster analysis process with sequential processing.

        This is the main entry point for cluster analysis, providing a complete
        workflow from risk data loading to final output generation.

        Args:
            visualize: Whether to create visualization plots
            export_results: Whether to export results to files
            custom_risk_files: Optional custom risk files to process

        Returns:
            Dict[str, gpd.GeoDataFrame]: Dictionary of cluster analysis results

        Note:
            Sequential processing is used to provide better progress tracking
            and immediate feedback during long-running operations.
        """
        logger.info("Starting sequential cluster analysis...")

        # Run sequential processing with appropriate visualization settings
        if export_results:
            cluster_results = self.process_risk_clusters_sequential(
                custom_risk_files, visualize
            )
        else:
            cluster_results = self.process_risk_clusters_sequential(
                custom_risk_files, False
            )

        if not cluster_results:
            logger.warning("No cluster results generated")

        logger.info("Sequential cluster analysis complete")
        return cluster_results

    def get_cluster_summary_statistics(
        self, cluster_results: Dict[str, gpd.GeoDataFrame]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Generate comprehensive summary statistics for all cluster results.

        Calculates aggregate statistics across all scenarios to provide
        insights into the overall clustering analysis results.

        Args:
            cluster_results: Dictionary of cluster results to analyze

        Returns:
            Dict[str, Dict[str, Any]]: Nested dictionary with statistics for each scenario
        """
        summary_statistics = {}

        # Calculate statistics for each scenario
        for file_key, cluster_geodataframe in cluster_results.items():
            if cluster_geodataframe.empty:
                continue

            statistics = self._calculate_scenario_statistics(cluster_geodataframe)
            summary_statistics[file_key] = statistics

        return summary_statistics

    def _calculate_scenario_statistics(
        self, cluster_geodataframe: gpd.GeoDataFrame
    ) -> Dict[str, Any]:
        """
        Calculate detailed summary statistics for a single scenario.

        Computes various metrics including spatial, statistical, and risk-related
        measures for the cluster analysis results.

        Args:
            cluster_geodataframe: GeoDataFrame containing cluster polygons

        Returns:
            Dict[str, Any]: Dictionary containing calculated statistics
        """
        total_clusters = len(cluster_geodataframe)

        # Handle empty results
        if total_clusters == 0:
            return {"cluster_count": 0}

        # Calculate comprehensive statistics
        return {
            "cluster_count": total_clusters,
            "total_area_square_kilometers": cluster_geodataframe[
                "cluster_area_square_meters"
            ].sum()
            / 1_000_000,
            "mean_cluster_area_square_meters": cluster_geodataframe[
                "cluster_area_square_meters"
            ].mean(),
            "largest_cluster_area_square_meters": cluster_geodataframe[
                "cluster_area_square_meters"
            ].max(),
            "average_risk_value": cluster_geodataframe["mean_risk_value"].mean(),
            "maximum_risk_value": cluster_geodataframe["max_risk_value"].max(),
            "total_affected_pixels": cluster_geodataframe["pixel_count"].sum(),
        }
