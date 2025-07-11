from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
import rasterio.mask
from pathlib import Path
import matplotlib.pyplot as plt
from dataclasses import dataclass

from eu_climate.config.config import ProjectConfig
from eu_climate.utils.utils import setup_logging
from eu_climate.utils.visualization import (
    ScientificStyle,
    setup_scientific_style,
)
from eu_climate.utils.conversion import RasterTransformer
from eu_climate.risk_layers.relevance_layer import RelevanceLayer

logger = setup_logging(__name__)


@dataclass
class EconomicImpactMetrics:
    """
    Comprehensive economic impact metrics for a single flood scenario.

    This dataclass encapsulates all key economic indicators and their risk exposure
    for a specific flood scenario, providing a standardized way to store and
    compare economic impacts across different scenarios.

    Attributes:
        scenario_name: Name of the flood scenario (e.g., 'current', 'severe')
        total_gdp_millions_eur: Total GDP in millions EUR for the region
        at_risk_gdp_millions_eur: GDP at risk from flooding in millions EUR
        total_freight_tonnes: Total freight activity in tonnes
        at_risk_freight_tonnes: Freight activity at risk from flooding in tonnes
        total_population_persons: Total population in persons
        at_risk_population_persons: Population at risk from flooding in persons
        total_hrst_persons: Total HRST (Human Resources in Science & Technology) in persons
        at_risk_hrst_persons: HRST at risk from flooding in persons
        total_population_ghs_persons: Total population from GHS data in persons
        at_risk_population_ghs_persons: GHS population at risk from flooding in persons
        cluster_count: Number of risk clusters identified
        total_risk_area_square_kilometers: Total area at risk in square kilometers
    """

    scenario_name: str
    total_gdp_millions_eur: float
    at_risk_gdp_millions_eur: float
    total_freight_tonnes: float
    at_risk_freight_tonnes: float
    total_population_persons: float
    at_risk_population_persons: float
    total_hrst_persons: float
    at_risk_hrst_persons: float
    total_population_ghs_persons: float
    at_risk_population_ghs_persons: float
    cluster_count: int
    total_risk_area_square_kilometers: float


class ZonalStatisticsExtractor:
    """
    Extracts absolute economic values from raster layers within polygon boundaries.

    This class provides functionality to extract quantitative economic values
    from raster datasets using polygon geometries as extraction boundaries.
    It supports multiple economic indicators and handles coordinate transformations
    and spatial operations.
    """

    def __init__(self, config: ProjectConfig):
        """
        Initialize the zonal statistics extractor.

        Args:
            config: Project configuration containing paths and settings
        """
        self.config = config

    def extract_values_from_clusters(
        self,
        cluster_geodataframe: gpd.GeoDataFrame,
        relevance_layers: Dict[str, np.ndarray],
        relevance_metadata: dict,
    ) -> pd.DataFrame:
        """
        Extract absolute economic values within each cluster polygon.

        Performs zonal statistics extraction for all clusters across multiple
        economic indicators, returning a comprehensive DataFrame with extracted values.

        Args:
            cluster_geodataframe: GeoDataFrame containing cluster polygons
            relevance_layers: Dictionary mapping indicator names to raster arrays
            relevance_metadata: Metadata for raster alignment and transforms

        Returns:
            DataFrame with extracted values for each cluster and indicator
        """
        if cluster_geodataframe.empty:
            return pd.DataFrame()

        results = []

        # Extract values for each cluster polygon
        for _, cluster_row in cluster_geodataframe.iterrows():
            cluster_values = self._extract_single_cluster_values(
                cluster_row, relevance_layers, relevance_metadata
            )
            results.append(cluster_values)

        return pd.DataFrame(results)

    def _extract_single_cluster_values(
        self,
        cluster_row: pd.Series,
        relevance_layers: Dict[str, np.ndarray],
        relevance_metadata: dict,
    ) -> Dict[str, Any]:
        """
        Extract economic values for a single cluster polygon.

        Processes a single cluster polygon to extract values from all available
        economic indicator rasters, handling spatial operations and data validation.

        Args:
            cluster_row: Series containing cluster geometry and attributes
            relevance_layers: Dictionary of economic indicator rasters
            relevance_metadata: Raster metadata for spatial operations

        Returns:
            Dictionary containing extracted values for all indicators
        """
        cluster_geometry = cluster_row["geometry"]
        cluster_id = cluster_row.get("risk_cluster_id", "unknown")

        # Initialize results dictionary with cluster metadata
        extracted_values = {
            "cluster_id": cluster_id,
            "cluster_area_square_meters": cluster_row.get(
                "cluster_area_square_meters", 0
            ),
        }

        # Extract values from relevance layers
        for layer_name, layer_data in relevance_layers.items():
            if layer_name == "combined":
                continue  # Skip combined layer

            extracted_value = self._perform_zonal_extraction(
                cluster_geometry, layer_data, relevance_metadata
            )
            extracted_values[f"{layer_name}_absolute"] = extracted_value

        # Extract population data separately using dedicated method
        population_value = self._extract_population_from_cluster(cluster_geometry)
        extracted_values["population_absolute"] = population_value

        return extracted_values

    def _extract_population_from_cluster(self, cluster_geometry: any) -> float:
        """
        Extract population values from cluster using 2025 population raster.

        Specialized method for extracting population data with proper handling
        of the 2025 population raster resolution and coordinate systems.

        Args:
            cluster_geometry: Cluster polygon geometry

        Returns:
            Total population within the cluster polygon
        """
        try:
            # Open population raster and extract values within cluster
            with rasterio.open(self.config.population_2025_path) as src:
                population_data = src.read(1).astype(np.float32)

                from rasterio.features import rasterize

                # Create mask for cluster polygon
                polygon_mask = rasterize(
                    [cluster_geometry],
                    out_shape=population_data.shape,
                    transform=src.transform,
                    fill=0,
                    default_value=1,
                    dtype=np.uint8,
                )

                # Apply mask and sum values
                masked_values = population_data * polygon_mask
                valid_values = masked_values[masked_values > 0]

                total_population = (
                    float(valid_values.sum()) if len(valid_values) > 0 else 0.0
                )
                return total_population

        except Exception as e:
            logger.warning(f"Population extraction failed for cluster: {e}")
            return 0.0

    def _perform_zonal_extraction(
        self, geometry: any, raster_data: np.ndarray, metadata: dict
    ) -> float:
        """
        Perform zonal statistics extraction for a single geometry.

        Core method that handles the rasterization of polygon geometries
        and extraction of values from raster data arrays.

        Args:
            geometry: Polygon geometry for extraction
            raster_data: Raster array containing values to extract
            metadata: Raster metadata including transform information

        Returns:
            Sum of raster values within the polygon geometry
        """
        try:
            from rasterio.features import rasterize

            # Get raster parameters
            transform = metadata["transform"]
            height, width = raster_data.shape

            # Rasterize polygon to create mask
            polygon_mask = rasterize(
                [geometry],
                out_shape=(height, width),
                transform=transform,
                fill=0,
                default_value=1,
                dtype=np.uint8,
            )

            # Extract values using mask
            masked_values = raster_data * polygon_mask
            valid_values = masked_values[masked_values > 0]

            return float(valid_values.sum()) if len(valid_values) > 0 else 0.0

        except Exception as e:
            logger.warning(f"Zonal extraction failed: {e}")
            return 0.0


class NutsDataAggregator:
    """
    Aggregates total economic values from NUTS regional data.

    This class provides functionality to calculate total economic values
    across all NUTS regions for comparison with at-risk values. It handles
    multiple data sources and ensures consistent unit conversions.
    """

    def __init__(self, config: ProjectConfig):
        """
        Initialize the NUTS data aggregator.

        Args:
            config: Project configuration containing paths and settings
        """
        self.config = config
        self.relevance_layer = RelevanceLayer(config)

    def get_total_regional_values(self) -> Dict[str, float]:
        """
        Get total absolute values for all economic indicators across the region.

        Calculates comprehensive totals for each economic indicator by aggregating
        values from NUTS regional data and population rasters.

        Returns:
            Dictionary mapping indicator names to total regional values
        """
        # Load economic data from NUTS regions
        economic_gdfs = self.relevance_layer.load_and_process_economic_data()

        totals = {}

        # Process each economic dataset
        for dataset_name, nuts_gdf in economic_gdfs.items():
            value_column = f"{dataset_name}_value"

            if value_column not in nuts_gdf.columns:
                continue

            # Sum values across all NUTS regions
            total_value = nuts_gdf[value_column].sum()
            totals[dataset_name] = self._convert_to_standard_units(
                total_value, dataset_name
            )

        # Add population data from raster
        totals["population"] = self._get_total_population_from_raster()

        return totals

    def _get_total_population_from_raster(self) -> float:
        """
        Extract total population from the 2025 GHS population raster.

        Processes the Global Human Settlement population raster to calculate
        total population within the study area with proper handling of
        resolution and coordinate systems.

        Returns:
            Total population from raster data
        """
        try:
            # Open population raster and extract all valid values
            with rasterio.open(self.config.population_2025_path) as src:
                population_data = src.read(1)

                # Create mask for valid population values
                valid_mask = ~np.isnan(population_data) & (population_data > 0)
                total_population = float(population_data[valid_mask].sum())

                logger.info(
                    f"Total population from raster: {total_population:,.0f} persons"
                )
                return total_population

        except Exception as e:
            logger.error(f"Failed to extract total population: {e}")
            return 0.0

    def _convert_to_standard_units(self, value: float, dataset_name: str) -> float:
        """
        Convert values to standard units for comparison.

        Ensures consistent units across different economic indicators
        for meaningful comparison and visualization.

        Args:
            value: Raw value to convert
            dataset_name: Name of the dataset for unit determination

        Returns:
            Value converted to standard units
        """
        # Currently using values as-is, but method allows for future unit conversions
        if dataset_name == "gdp":
            return value
        if dataset_name == "freight":
            return value
        if dataset_name in ["population", "hrst"]:
            return value

        return value


class EconomicImpactVisualizer:
    """
    Creates visualizations comparing total vs at-risk economic values.

    This class generates publication-quality visualizations showing the
    economic impact of flood scenarios through various chart types including
    stacked bar charts, comparison plots, and multi-scenario analyses.
    """

    def __init__(self, config: ProjectConfig):
        """
        Initialize the economic impact visualizer.

        Args:
            config: Project configuration containing paths and settings
        """
        self.config = config
        self.output_dir = Path(config.output_dir) / "economic_impact"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_impact_comparison_plots(
        self, impact_metrics: List[EconomicImpactMetrics]
    ) -> None:
        """
        Create comparison plots for all scenarios and indicators.

        Generates comprehensive visualizations showing economic impact
        across multiple scenarios and indicators with both individual
        and comparative views.

        Args:
            impact_metrics: List of impact metrics for each scenario
        """
        if not impact_metrics:
            logger.warning("No impact metrics available for visualization")
            return

        scenarios = [metrics.scenario_name for metrics in impact_metrics]

        # Create individual scenario plots
        for scenario in scenarios:
            scenario_metrics = next(
                m for m in impact_metrics if m.scenario_name == scenario
            )
            self._create_single_scenario_plot(scenario_metrics)

        # Create multi-scenario comparison
        self._create_multi_scenario_comparison(impact_metrics)

    def _create_single_scenario_plot(self, metrics: EconomicImpactMetrics) -> None:
        """
        Create impact comparison plot for a single scenario with percentage scaling.

        Generates a stacked bar chart showing total vs at-risk values
        for each economic indicator as percentages with absolute value annotations.

        Args:
            metrics: Economic impact metrics for the scenario
        """
        # Define indicators and extract values
        indicators = ["GDP", "Freight", "Population"]

        total_values = [
            metrics.total_gdp_millions_eur,
            metrics.total_freight_tonnes,
            metrics.total_population_persons,
        ]
        at_risk_values = [
            metrics.at_risk_gdp_millions_eur,
            metrics.at_risk_freight_tonnes,
            metrics.at_risk_population_persons,
        ]

        # Create figure with scientific styling
        fig, ax = plt.subplots(figsize=(12, 8), dpi=ScientificStyle.DPI)

        x_positions = np.arange(len(indicators))

        # Configure plot appearance
        ax.set_xlabel("Economic Indicators", fontsize=ScientificStyle.LABEL_SIZE)
        ax.set_ylabel("Percentage (%)", fontsize=ScientificStyle.LABEL_SIZE)
        ax.set_title(
            f"Economic Impact Analysis: {metrics.scenario_name}",
            fontsize=ScientificStyle.TITLE_SIZE,
            fontweight="bold",
        )
        ax.set_xticks(x_positions)
        ax.set_xticklabels(indicators)
        ax.set_ylim(0, 100)
        ax.legend()

        # Add absolute value annotations
        self._add_absolute_value_labels(
            ax, x_positions, total_values, at_risk_values, indicators
        )

        ax.grid(axis="y", alpha=0.3)

        # Save the plot
        plt.tight_layout()
        plot_path = self.output_dir / f"economic_impact_{metrics.scenario_name}.png"
        plt.savefig(
            plot_path,
            dpi=ScientificStyle.DPI,
            bbox_inches="tight",
            facecolor="white",
            edgecolor="none",
        )
        plt.close()

        logger.info(f"Saved economic impact plot: {plot_path}")

    def _add_absolute_value_labels(
        self,
        ax: plt.Axes,
        x_positions: np.ndarray,
        total_values: List[float],
        at_risk_values: List[float],
        indicators: List[str],
    ) -> None:
        """
        Add absolute value annotations to bars.

        Adds properly formatted absolute value labels to bar charts
        with appropriate units and scaling for readability.

        Args:
            ax: Matplotlib axes object
            x_positions: X-axis positions for bars
            total_values: List of total values for each indicator
            at_risk_values: List of at-risk values for each indicator
            indicators: List of indicator names
        """
        # Define units for each indicator
        units = {"GDP": "€M", "Freight": "t", "Population": "persons"}

        # Add annotations for each bar
        for i, (x_pos, total, at_risk, indicator) in enumerate(
            zip(x_positions, total_values, at_risk_values, indicators)
        ):
            unit = units.get(indicator, "")

            # Format values with appropriate units
            total_text = self._format_value_with_unit(total, unit)
            at_risk_text = self._format_value_with_unit(at_risk, unit)

            # Add total value annotation above bar
            ax.text(
                x_pos,
                95,
                f"Total: {total_text}",
                ha="center",
                va="top",
                fontsize=10,
                fontweight="bold",
            )

            # Add at-risk value annotation in red section
            risk_percentage = (at_risk / total * 100) if total > 0 else 0
            ax.text(
                x_pos,
                risk_percentage / 2,
                f"At Risk: {at_risk_text}",
                ha="center",
                va="center",
                fontsize=9,
                color="white",
                fontweight="bold",
            )

    def _format_value_with_unit(self, value: float, unit: str) -> str:
        """
        Format values with appropriate scaling and units.

        Provides intelligent formatting with K/M suffixes for large numbers
        and appropriate precision for different value ranges.

        Args:
            value: Numeric value to format
            unit: Unit string to append

        Returns:
            Formatted string with value and unit
        """
        if unit == "€M":
            return f"{value:,.0f} {unit}"
        elif unit == "t":
            if value >= 1_000_000:
                return f"{value / 1_000_000:.1f}M {unit}"
            elif value >= 1_000:
                return f"{value / 1_000:.0f}K {unit}"
            else:
                return f"{value:,.0f} {unit}"
        elif unit == "persons":
            if value >= 1_000_000:
                return f"{value / 1_000_000:.1f}M {unit}"
            elif value >= 1_000:
                return f"{value / 1_000:.0f}K {unit}"
            else:
                return f"{value:,.0f} {unit}"
        else:
            return f"{value:,.0f}"

    def _create_multi_scenario_comparison(
        self, impact_metrics: List[EconomicImpactMetrics]
    ) -> None:
        """
        Create comparison plot across multiple scenarios.

        Generates a comparative visualization showing risk exposure
        percentages across different flood scenarios for key indicators.

        Args:
            impact_metrics: List of impact metrics for all scenarios
        """
        if len(impact_metrics) < 2:
            return

        # Extract scenario data
        scenarios = [m.scenario_name for m in impact_metrics]
        gdp_percentages = [
            (m.at_risk_gdp_millions_eur / m.total_gdp_millions_eur * 100)
            if m.total_gdp_millions_eur > 0
            else 0
            for m in impact_metrics
        ]
        freight_percentages = [
            (m.at_risk_freight_tonnes / m.total_freight_tonnes * 100)
            if m.total_freight_tonnes > 0
            else 0
            for m in impact_metrics
        ]

        # Create comparison plot
        fig, ax = plt.subplots(
            figsize=ScientificStyle.FIGURE_SIZE, dpi=ScientificStyle.DPI
        )

        x_positions = np.arange(len(scenarios))
        bar_width = 0.35

        # Create grouped bars for GDP and Freight
        ax.bar(
            x_positions - bar_width / 2,
            gdp_percentages,
            bar_width,
            label="GDP at Risk (%)",
            color="navy",
            alpha=0.7,
        )
        ax.bar(
            x_positions + bar_width / 2,
            freight_percentages,
            bar_width,
            label="Freight at Risk (%)",
            color="darkred",
            alpha=0.7,
        )

        # Configure plot appearance
        ax.set_xlabel("Scenarios", fontsize=ScientificStyle.LABEL_SIZE)
        ax.set_ylabel("Percentage at Risk (%)", fontsize=ScientificStyle.LABEL_SIZE)
        ax.set_title(
            "Risk Exposure Comparison Across Scenarios",
            fontsize=ScientificStyle.TITLE_SIZE,
            fontweight="bold",
        )
        ax.set_xticks(x_positions)
        ax.set_xticklabels(scenarios, rotation=45, ha="right")
        ax.legend()

        # Save the plot
        plt.tight_layout()
        plot_path = self.output_dir / "multi_scenario_risk_comparison.png"
        plt.savefig(
            plot_path,
            dpi=ScientificStyle.DPI,
            bbox_inches="tight",
            facecolor="white",
            edgecolor="none",
        )
        plt.close()

        logger.info(f"Saved multi-scenario comparison plot: {plot_path}")

    def _add_value_labels_to_bars(
        self, ax: plt.Axes, bars: any, values: List[float]
    ) -> None:
        """
        Add value labels on top of bars.

        Utility method to add numeric labels above bar charts
        for improved readability of exact values.

        Args:
            ax: Matplotlib axes object
            bars: Bar objects from matplotlib
            values: List of values to display
        """
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height + height * 0.01,
                f"{value:.1f}",
                ha="center",
                va="bottom",
                fontsize=ScientificStyle.TICK_SIZE - 2,
            )


class EconomicImpactExporter:
    """
    Exports economic impact results to various file formats.

    This class handles the export of economic impact analysis results
    to standard formats including CSV summaries and enhanced GeoPackage
    files with spatial and economic data integration.
    """

    def __init__(self, config: ProjectConfig):
        """
        Initialize the economic impact exporter.

        Args:
            config: Project configuration containing paths and settings
        """
        self.config = config
        self.output_dir = Path(config.output_dir) / "economic_impact"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_impact_metrics(
        self,
        impact_metrics: List[EconomicImpactMetrics],
        cluster_details: Dict[str, pd.DataFrame],
    ) -> None:
        """
        Export impact metrics to CSV and enhanced GeoPackage formats.

        Creates comprehensive exports including summary statistics
        and detailed cluster-level economic data.

        Args:
            impact_metrics: List of impact metrics for all scenarios
            cluster_details: Dictionary of detailed cluster data by scenario
        """
        if not impact_metrics:
            return

        # Export summary statistics
        self._export_summary_csv(impact_metrics)

        # Export detailed cluster data
        self._export_detailed_cluster_data(cluster_details)

    def _export_summary_csv(self, impact_metrics: List[EconomicImpactMetrics]) -> None:
        """
        Export summary metrics to CSV format.

        Creates a comprehensive CSV file with all economic impact metrics
        and calculated risk percentages for each scenario.

        Args:
            impact_metrics: List of impact metrics to export
        """
        summary_data = []

        # Process each scenario's metrics
        for metrics in impact_metrics:
            summary_data.append(
                {
                    "scenario": metrics.scenario_name,
                    "total_gdp_millions_eur": metrics.total_gdp_millions_eur,
                    "at_risk_gdp_millions_eur": metrics.at_risk_gdp_millions_eur,
                    "gdp_risk_percentage": self._calculate_risk_percentage(
                        metrics.at_risk_gdp_millions_eur, metrics.total_gdp_millions_eur
                    ),
                    "total_freight_tonnes": metrics.total_freight_tonnes,
                    "at_risk_freight_tonnes": metrics.at_risk_freight_tonnes,
                    "freight_risk_percentage": self._calculate_risk_percentage(
                        metrics.at_risk_freight_tonnes, metrics.total_freight_tonnes
                    ),
                    "cluster_count": metrics.cluster_count,
                    "total_risk_area_square_kilometers": metrics.total_risk_area_square_kilometers,
                }
            )

        # Export to CSV
        summary_df = pd.DataFrame(summary_data)
        csv_path = self.output_dir / "economic_impact_summary.csv"
        summary_df.to_csv(csv_path, index=False)

        logger.info(f"Exported impact summary to: {csv_path}")

    def _export_detailed_cluster_data(
        self, cluster_details: Dict[str, pd.DataFrame]
    ) -> None:
        """
        Export detailed cluster data with economic values.

        Creates GeoPackage files containing cluster geometries with
        associated economic data for detailed spatial analysis.

        Args:
            cluster_details: Dictionary mapping scenarios to cluster DataFrames
        """
        # Export each scenario's cluster data
        for scenario, cluster_data in cluster_details.items():
            if cluster_data.empty:
                continue

            gpkg_path = self.output_dir / f"clusters_with_economics_{scenario}.gpkg"

            # Handle both GeoDataFrame and regular DataFrame
            if hasattr(cluster_data, "to_file"):
                cluster_data.to_file(gpkg_path, driver="GPKG")
            else:
                cluster_gdf = gpd.GeoDataFrame(cluster_data)
                cluster_gdf.to_file(gpkg_path, driver="GPKG")

            logger.info(f"Exported detailed cluster data to: {gpkg_path}")

    def _calculate_risk_percentage(
        self, at_risk_value: float, total_value: float
    ) -> float:
        """
        Calculate risk percentage with division by zero protection.

        Safely calculates the percentage of total value that is at risk
        with proper handling of edge cases.

        Args:
            at_risk_value: Value at risk from flooding
            total_value: Total value for comparison

        Returns:
            Risk percentage (0-100)
        """
        if total_value <= 0:
            return 0.0
        return (at_risk_value / total_value) * 100


class EconomicImpactAnalyzer:
    """
    Economic Impact Analyzer for Flood Risk Assessment
    ================================================

    The EconomicImpactAnalyzer class provides comprehensive analysis of economic
    impacts from flood scenarios by combining hazard assessments with economic
    relevance data. It quantifies the economic value at risk across multiple
    indicators and scenarios.

    Key Features:
    - Sequential scenario processing for memory efficiency
    - Integration of hazard and economic relevance data
    - Configurable flood risk thresholds
    - Multiple economic indicators (GDP, Freight, Population, HRST)
    - Comprehensive visualization and reporting
    - Stacked bar charts showing total vs at-risk amounts
    - Multi-scenario comparison capabilities
    - Export functionality for results and visualizations

    Processing Pipeline:
    1. Load absolute relevance layers for economic indicators
    2. Load hazard scenarios (current, conservative, moderate, severe)
    3. Apply flood risk thresholds to identify at-risk areas
    4. Calculate economic impacts by overlaying hazard and relevance data
    5. Generate comprehensive visualizations and reports
    6. Export results in multiple formats

    The analyzer supports both individual scenario analysis and comparative
    analysis across multiple flood scenarios with consistent methodology.
    """

    def __init__(self, config: ProjectConfig):
        """
        Initialize the Economic Impact Analyzer.

        Sets up the analyzer with configuration parameters and initializes
        all required components for economic impact analysis.

        Args:
            config: Project configuration containing paths and analysis settings
        """
        self.config = config
        self.max_safe_flood_risk = config.max_safe_flood_risk
        self.indicators = config.config["relevance"]["economic_variables"] + [
            "population"
        ]  # Add population

        # Define hazard scenarios to process
        self.hazard_scenarios = ["current", "conservative", "moderate", "severe"]

        # Setup visualization styling
        setup_scientific_style()

        logger.info("Initialized Economic Impact Analyzer")
        logger.info(f"Flood risk threshold: {self.max_safe_flood_risk}")
        logger.info(f"Target indicators: {self.indicators}")
        logger.info(
            "Note: Using HRST (Human Resources in Science & Technology) as population indicator"
        )
        logger.info(
            "Note: Added total population from GHS_POP raster as additional indicator"
        )

    def load_absolute_relevance_layers(self) -> Dict[str, np.ndarray]:
        """
        Load absolute relevance layers for all economic indicators.

        Loads pre-processed absolute relevance layers that contain quantitative
        economic values (not normalized) for use in impact calculations.

        Returns:
            Dictionary mapping indicator names to absolute value raster arrays
        """
        logger.info("Loading absolute relevance layers...")

        relevance_layers = {}

        # Load each economic indicator
        for indicator in self.indicators:
            if indicator == "population":
                # Load population data directly from raster file
                population_data = self.load_population_data()
                relevance_layers[indicator] = population_data
                continue

            # Load pre-processed absolute relevance layer
            tif_path = (
                self.config.output_dir
                / "relevance_absolute"
                / "tif"
                / f"absolute_relevance_{indicator}.tif"
            )

            if not tif_path.exists():
                logger.error(f"Required absolute relevance layer missing: {tif_path}")
                raise FileNotFoundError(
                    f"Required absolute relevance layer missing: {indicator}"
                )

            # Load raster data
            with rasterio.open(tif_path) as src:
                data = src.read(1).astype(np.float32)
                relevance_layers[indicator] = data

                # Log loading statistics
                valid_data = data[~np.isnan(data) & (data > 0)]
                total_value = valid_data.sum() if len(valid_data) > 0 else 0
                logger.info(
                    f"Loaded {indicator}: {len(valid_data)} pixels, total value: {total_value:,.0f}"
                )

        return relevance_layers

    def load_population_data(self) -> np.ndarray:
        """
        Load 2025 population data with corrected resolution handling.

        Loads population data from the Global Human Settlement Layer with
        proper validation and study area masking.

        Returns:
            Population raster array with corrected resolution
        """
        logger.info(
            "Loading 2025 population data with corrected resolution handling..."
        )

        try:
            # Use the validated population loading function
            from ..utils.data_loading import load_population_2025_with_validation

            # Load population data with validation
            population_data, metadata, validation_passed = (
                load_population_2025_with_validation(
                    config=self.config, apply_study_area_mask=True
                )
            )

            # Log loading statistics
            valid_data = population_data[
                ~np.isnan(population_data) & (population_data > 0)
            ]
            total_population = valid_data.sum() if len(valid_data) > 0 else 0

            logger.info(f"Loaded 2025 population data: {population_data.shape} shape")
            logger.info(
                f"Population pixels: {len(valid_data)}, total population: {total_population:,.0f}"
            )
            logger.info(f"Validation passed: {validation_passed}")

            return population_data

        except Exception as e:
            logger.error(f"Failed to load population data: {e}")
            import traceback

            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise

    def _apply_study_area_mask(
        self, data: np.ndarray, transform: rasterio.Affine, shape: Tuple[int, int]
    ) -> np.ndarray:
        """
        Apply study area mask using NUTS boundaries and land mass data.

        Restricts analysis to relevant study areas by masking out regions
        outside NUTS boundaries and water bodies.

        Args:
            data: Input raster data to mask
            transform: Raster coordinate transform
            shape: Raster dimensions (height, width)

        Returns:
            Masked raster data limited to study area
        """
        logger.info("Applying study area mask to population data...")

        try:
            # Load NUTS-L3 boundaries for study area definition
            nuts_l3_path = self.config.data_dir / "NUTS-L3-NL.shp"
            nuts_gdf = gpd.read_file(nuts_l3_path)

            # Ensure NUTS is in target CRS
            target_crs = rasterio.crs.CRS.from_string(self.config.target_crs)
            if nuts_gdf.crs != target_crs:
                nuts_gdf = nuts_gdf.to_crs(target_crs)

            # Create NUTS mask
            nuts_mask = rasterio.features.rasterize(
                [(geom, 1) for geom in nuts_gdf.geometry],
                out_shape=shape,
                transform=transform,
                dtype=np.uint8,
            )
            logger.info(
                f"Created NUTS mask: {np.sum(nuts_mask)} pixels within NUTS boundaries"
            )

            # Load and align land mass data
            transformer = RasterTransformer(
                target_crs=self.config.target_crs, config=self.config
            )
            resampling_method_str = (
                self.config.resampling_method.name.lower()
                if hasattr(self.config.resampling_method, "name")
                else str(self.config.resampling_method).lower()
            )

            land_mass_data, land_transform, _ = transformer.transform_raster(
                self.config.land_mass_path,
                reference_bounds=transformer.get_reference_bounds(nuts_l3_path),
                resampling_method=resampling_method_str,
            )

            # Ensure land mass data is aligned with population data
            if not transformer.validate_alignment(
                land_mass_data, land_transform, data, transform
            ):
                land_mass_data = transformer.ensure_alignment(
                    land_mass_data,
                    land_transform,
                    transform,
                    shape,
                    resampling_method_str,
                )

            # Create land mask (1=land, 0=water/no data)
            land_mask = (land_mass_data > 0).astype(np.uint8)
            logger.info(
                f"Created land mask: {np.sum(land_mask)} pixels identified as land"
            )

            # Combine masks: only areas that are both within NUTS and on land
            combined_mask = (nuts_mask == 1) & (land_mask == 1)
            logger.info(
                f"Combined study area mask: {np.sum(combined_mask)} pixels in relevant study area"
            )

            # Apply mask to population data
            masked_data = data.copy()
            masked_data[~combined_mask] = 0.0

            # Log masking statistics
            original_nonzero = np.sum(data > 0)
            masked_nonzero = np.sum(masked_data > 0)
            original_total = np.sum(data[data > 0]) if original_nonzero > 0 else 0
            masked_total = (
                np.sum(masked_data[masked_data > 0]) if masked_nonzero > 0 else 0
            )

            logger.info(
                f"Population masking removed {original_nonzero - masked_nonzero} non-zero pixels "
                f"({(original_nonzero - masked_nonzero) / original_nonzero * 100:.1f}% reduction)"
            )
            logger.info(
                f"Population total reduced from {original_total:,.0f} to {masked_total:,.0f} "
                f"({(original_total - masked_total) / original_total * 100:.1f}% reduction)"
            )

            return masked_data

        except Exception as e:
            logger.warning(
                f"Could not apply study area mask to population data: {str(e)}"
            )
            logger.warning("Proceeding with unmasked population data")
            return data

    def load_hazard_scenario(self, scenario_name: str) -> Tuple[np.ndarray, dict]:
        """
        Load hazard data for a specific flood scenario.

        Loads processed hazard raster data for a given scenario and extracts
        relevant metadata for subsequent analysis.

        Args:
            scenario_name: Name of the flood scenario to load

        Returns:
            Tuple of (hazard_data, metadata) for the scenario
        """
        hazard_path = (
            self.config.output_dir
            / "hazard"
            / "tif"
            / f"flood_risk_{scenario_name.lower()}.tif"
        )

        if not hazard_path.exists():
            raise FileNotFoundError(f"Hazard scenario not found: {hazard_path}")

        # Load hazard data
        with rasterio.open(hazard_path) as src:
            hazard_data = src.read(1).astype(np.float32)
            meta = src.meta

        # Log hazard statistics
        valid_hazard = hazard_data[~np.isnan(hazard_data)]
        at_risk_pixels = np.sum(valid_hazard > self.max_safe_flood_risk)
        total_pixels = len(valid_hazard)
        risk_percentage = (
            (at_risk_pixels / total_pixels * 100) if total_pixels > 0 else 0
        )

        logger.info(
            f"Loaded {scenario_name} hazard: {at_risk_pixels}/{total_pixels} pixels at risk ({risk_percentage:.1f}%)"
        )

        return hazard_data, meta

    def calculate_scenario_impact(
        self,
        hazard_data: np.ndarray,
        relevance_layers: Dict[str, np.ndarray],
        scenario_name: str,
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate economic impact for a specific scenario using flood risk threshold.

        Performs the core economic impact calculation by overlaying hazard data
        with economic relevance layers and applying the configured risk threshold.

        Args:
            hazard_data: Hazard raster array for the scenario
            relevance_layers: Dictionary of economic indicator raster arrays
            scenario_name: Name of the scenario for logging

        Returns:
            Dictionary containing impact results for each economic indicator
        """
        logger.info(f"Calculating economic impact for {scenario_name} scenario...")
        logger.info(f"Using flood risk threshold: {self.max_safe_flood_risk}")

        # Create risk mask where hazard exceeds threshold
        risk_mask = hazard_data > self.max_safe_flood_risk
        risk_pixel_count = np.sum(risk_mask)
        total_pixels = np.sum(~np.isnan(hazard_data))

        logger.info(
            f"Risk pixels: {risk_pixel_count}/{total_pixels} ({risk_pixel_count / total_pixels * 100:.1f}%)"
        )

        impact_results = {}

        # Calculate impact for each indicator
        for indicator in self.indicators:
            relevance_data = relevance_layers[indicator]

            # Ensure data alignment
            if relevance_data.shape != hazard_data.shape:
                logger.warning(
                    f"Shape mismatch for {indicator}: {relevance_data.shape} vs {hazard_data.shape}"
                )
                continue

            # Calculate total and at-risk values
            valid_mask = ~np.isnan(relevance_data) & (relevance_data > 0)

            total_value = np.sum(relevance_data[valid_mask])
            at_risk_value = np.sum(relevance_data[valid_mask & risk_mask])

            # Calculate percentages
            risk_percentage = (
                (at_risk_value / total_value * 100) if total_value > 0 else 0
            )
            safe_percentage = 100 - risk_percentage

            # Store results
            impact_results[indicator] = {
                "total_value": total_value,
                "at_risk_value": at_risk_value,
                "safe_value": total_value - at_risk_value,
                "risk_percentage": risk_percentage,
                "safe_percentage": safe_percentage,
            }

            logger.info(
                f"{indicator.upper()} impact - Total: {total_value:,.0f}, At Risk: {at_risk_value:,.0f} ({risk_percentage:.1f}%)"
            )

        return impact_results

    def create_impact_visualization(
        self, impact_results: Dict[str, Dict[str, float]], scenario_name: str
    ) -> None:
        """
        Create stacked vertical bar chart visualization for economic impact.

        Generates a publication-quality visualization showing the economic
        impact of flooding with stacked bars representing safe vs at-risk portions.

        Args:
            impact_results: Dictionary with impact results for each indicator
            scenario_name: Name of the scenario for titling and file naming
        """
        logger.info(f"Creating impact visualization for scenario: {scenario_name}")

        # Create scenario output directory
        scenario_dir = (
            self.config.output_dir / "economic_impact" / scenario_name.lower()
        )
        scenario_dir.mkdir(parents=True, exist_ok=True)

        # Prepare data for visualization
        indicators = []
        total_values = []
        at_risk_values = []
        percentages_at_risk = []

        # Define indicator display names and units
        indicator_info = {
            "gdp": {
                "name": "GDP",
                "unit": "trillion €",
                "scale": 1_000_000,
            },  # Data already in trillion
            "freight": {
                "name": "Freight",
                "unit": "million tonnes",
                "scale": 1_000_000,
            },
            "hrst": {
                "name": "Population (HRST)",
                "unit": "millions persons",
                "scale": 1_000_000,
            },
            "population": {
                "name": "Population (GHS)",
                "unit": "millions persons",
                "scale": 1_000_000,
            },
        }

        # Process each indicator for visualization
        for indicator_key, results in impact_results.items():
            if indicator_key in indicator_info:
                info = indicator_info[indicator_key]
                indicators.append(info["name"])

                # Apply appropriate scaling based on indicator type
                if indicator_key == "gdp":
                    # GDP data is already in EUR, convert to millions
                    total_val = results["total_value"] / info["scale"]
                    at_risk_val = results["at_risk_value"] / info["scale"]
                else:
                    # Other indicators need scaling
                    total_val = results["total_value"] / info["scale"]
                    at_risk_val = results["at_risk_value"] / info["scale"]

                total_values.append(total_val)
                at_risk_values.append(at_risk_val)

                # Calculate percentage at risk
                if total_val > 0:
                    percentage = (at_risk_val / total_val) * 100
                else:
                    percentage = 0
                percentages_at_risk.append(percentage)

        if not indicators:
            logger.warning("No valid indicators found for visualization")
            return

        # Create vertical stacked bar chart with 0-100% scale
        fig, ax = plt.subplots(figsize=(12, 8), dpi=ScientificStyle.DPI)

        x_positions = np.arange(len(indicators))
        
        # Safe portion (grey) starts from at-risk percentage
        safe_percentages = [100 - pct for pct in percentages_at_risk]

        # Customize the plot
        ax.set_ylabel("Percentage (%)", fontsize=ScientificStyle.LABEL_SIZE)
        ax.set_xlabel("Economic Indicators", fontsize=ScientificStyle.LABEL_SIZE)
        ax.set_title(
            f"Economic Impact Analysis: {scenario_name.title()}",
            fontsize=ScientificStyle.TITLE_SIZE,
            fontweight="bold",
        )
        ax.set_xticks(x_positions)
        ax.set_xticklabels(indicators, rotation=45, ha="right")
        ax.set_ylim(0, 100)
        ax.legend()

        # Add value annotations inside bars
        for i, (at_risk_pct, safe_pct, total_val, at_risk_val, indicator) in enumerate(
            zip(
                percentages_at_risk,
                safe_percentages,
                total_values,
                at_risk_values,
                indicators,
            )
        ):
            # Get unit info for this indicator
            info = next(
                info
                for key, info in indicator_info.items()
                if info["name"] == indicator
            )

            # Add total value annotation above the bar
            ax.text(
                i,
                105,
                f"Total: {total_val:.1f} {info['unit']}",
                ha="center",
                va="bottom",
                fontsize=9,
                fontweight="bold",
            )

            # Add at-risk value annotation in the red section (if visible)
            if at_risk_pct > 10:  # Only show if section is big enough
                red_section_center = at_risk_pct / 2
                ax.text(
                    i,
                    red_section_center,
                    f"{at_risk_val:.1f}\n{info['unit']}",
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="white",
                    fontweight="bold",
                )

            # Add percentage annotation in the red section
            if at_risk_pct > 5:  # Only show if section is visible
                ax.text(
                    i,
                    at_risk_pct - 2,
                    f"{at_risk_pct:.1f}%",
                    ha="center",
                    va="top",
                    fontsize=8,
                    color="white",
                    fontweight="bold",
                )

        ax.grid(axis="y", alpha=0.3)
        ax.set_axisbelow(True)

        # Save the visualization
        plt.tight_layout()
        output_path = scenario_dir / f"economic_impact_{scenario_name.lower()}.png"
        plt.savefig(
            output_path,
            dpi=ScientificStyle.DPI,
            bbox_inches="tight",
            facecolor="white",
            edgecolor="none",
        )
        plt.close()

        logger.info(f"Saved impact visualization to {output_path}")

        # Log the actual values for debugging
        logger.info(f"Visualization data for {scenario_name}:")
        for i, indicator in enumerate(indicators):
            logger.info(
                f"  {indicator}: {at_risk_values[i]:.2f} / {total_values[i]:.2f} ({percentages_at_risk[i]:.1f}%)"
            )

    def process_scenario(
        self,
        scenario_name: str,
        create_visualizations: bool = True,
        export_results: bool = True,
    ) -> Optional[EconomicImpactMetrics]:
        """
        Process a single flood risk scenario and calculate economic impacts.

        Performs complete economic impact analysis for a single scenario including
        data loading, impact calculation, visualization, and export.

        Args:
            scenario_name: Name of the scenario to process
            create_visualizations: Whether to create visualization plots
            export_results: Whether to export results to files

        Returns:
            Economic impact metrics for the scenario, or None if processing failed
        """
        try:
            # Load hazard data for the scenario
            logger.info(f"Loading hazard data for scenario: {scenario_name}")
            hazard_data, hazard_meta = self.load_hazard_scenario(scenario_name)

            if hazard_data is None:
                logger.error(
                    f"Could not load hazard data for scenario: {scenario_name}"
                )
                return None

            # Load economic relevance layers
            logger.info("Loading absolute relevance layers...")
            relevance_layers = self.load_absolute_relevance_layers()

            if not relevance_layers:
                logger.error(
                    f"Could not load relevance layers for scenario: {scenario_name}"
                )
                return None

            # Calculate economic impacts
            logger.info("Calculating economic impacts...")
            impact_results = self.calculate_scenario_impact(
                hazard_data, relevance_layers, scenario_name
            )

            # Create metrics object
            metrics = EconomicImpactMetrics(
                scenario_name=scenario_name,
                total_gdp_millions_eur=impact_results["gdp"]["total_value"] / 1_000_000,
                at_risk_gdp_millions_eur=impact_results["gdp"]["at_risk_value"]
                / 1_000_000,
                total_freight_tonnes=impact_results["freight"]["total_value"],
                at_risk_freight_tonnes=impact_results["freight"]["at_risk_value"],
                total_population_persons=impact_results["hrst"]["total_value"],
                at_risk_population_persons=impact_results["hrst"]["at_risk_value"],
                total_hrst_persons=impact_results["hrst"]["total_value"],
                at_risk_hrst_persons=impact_results["hrst"]["at_risk_value"],
                total_population_ghs_persons=impact_results["population"][
                    "total_value"
                ],
                at_risk_population_ghs_persons=impact_results["population"][
                    "at_risk_value"
                ],
                cluster_count=0,  # Will be updated if cluster analysis is available
                total_risk_area_square_kilometers=0.0,  # Will be calculated from risk mask
            )

            # Calculate risk area from hazard data
            risk_mask = hazard_data > self.max_safe_flood_risk
            risk_pixels = np.sum(risk_mask)
            pixel_area_square_meters = self.config.target_resolution**2
            metrics.total_risk_area_square_kilometers = (
                risk_pixels * pixel_area_square_meters
            ) / 1_000_000

            # Create visualizations if requested
            if create_visualizations:
                logger.info(f"Creating visualization for scenario: {scenario_name}")
                self.create_impact_visualization(impact_results, scenario_name)

            # Export results if requested
            if export_results:
                logger.info(f"Exporting results for scenario: {scenario_name}")
                self.export_scenario_data(impact_results, scenario_name)

            # Log summary statistics
            logger.info(f"Scenario {scenario_name} summary:")
            logger.info(
                f"  GDP at risk: {metrics.at_risk_gdp_millions_eur:.1f}M EUR ({metrics.at_risk_gdp_millions_eur / metrics.total_gdp_millions_eur * 100:.1f}%)"
            )
            logger.info(
                f"  Freight at risk: {metrics.at_risk_freight_tonnes:.0f} tonnes ({metrics.at_risk_freight_tonnes / metrics.total_freight_tonnes * 100:.1f}%)"
            )
            logger.info(
                f"  Population at risk: {metrics.at_risk_population_persons:.0f} persons ({metrics.at_risk_population_persons / metrics.total_population_persons * 100:.1f}%)"
            )
            logger.info(
                f"  Risk area: {metrics.total_risk_area_square_kilometers:.1f} km²"
            )

            return metrics

        except Exception as e:
            logger.error(f"Error processing scenario {scenario_name}: {e}")
            import traceback

            logger.error(f"Full traceback: {traceback.format_exc()}")
            return None

    def run_economic_impact_analysis(
        self, create_visualizations: bool = True, export_results: bool = True
    ) -> List[EconomicImpactMetrics]:
        """
        Run complete economic impact analysis for all flood risk scenarios.

        Executes the full economic impact analysis pipeline including
        processing all scenarios, creating visualizations, and generating
        comprehensive reports.

        Args:
            create_visualizations: Whether to create visualization plots
            export_results: Whether to export results to files

        Returns:
            List of economic impact metrics for each scenario
        """
        logger.info("Starting comprehensive economic impact analysis...")
        logger.info(f"Processing {len(self.hazard_scenarios)} flood risk scenarios")
        logger.info(f"Target flood risk threshold: {self.max_safe_flood_risk}")

        all_metrics = []

        # Process each scenario
        for scenario_name in self.hazard_scenarios:
            logger.info(f"\n{'=' * 50}")
            logger.info(f"Processing scenario: {scenario_name}")
            logger.info(f"{'=' * 50}")

            metrics = self.process_scenario(
                scenario_name, create_visualizations, export_results
            )
            if metrics:
                all_metrics.append(metrics)
                logger.info(f"[SUCCESS] Completed scenario: {scenario_name}")
            else:
                logger.warning(f"[FAILED] Failed to process scenario: {scenario_name}")

        # Create summary report if exporting results
        if export_results:
            self.create_summary_report(all_metrics)

        # Log final summary
        logger.info(f"\n{'=' * 60}")
        logger.info("ECONOMIC IMPACT ANALYSIS COMPLETE")
        logger.info(f"{'=' * 60}")
        logger.info(
            f"Successfully processed {len(all_metrics)}/{len(self.hazard_scenarios)} scenarios"
        )

        return all_metrics

    def create_summary_report(self, all_metrics: List[EconomicImpactMetrics]) -> None:
        """
        Create comprehensive summary report with all scenario metrics.

        Generates a detailed CSV report containing all economic impact metrics
        across all processed scenarios for comparative analysis.

        Args:
            all_metrics: List of economic impact metrics for all scenarios
        """
        logger.info("Creating summary report...")

        # Prepare summary data
        summary_data = []
        for metrics in all_metrics:
            summary_data.append(
                {
                    "scenario": metrics.scenario_name,
                    "total_gdp_millions_eur": metrics.total_gdp_millions_eur,
                    "at_risk_gdp_millions_eur": metrics.at_risk_gdp_millions_eur,
                    "total_freight_tonnes": metrics.total_freight_tonnes,
                    "at_risk_freight_tonnes": metrics.at_risk_freight_tonnes,
                    "total_population_persons": metrics.total_population_persons,
                    "at_risk_population_persons": metrics.at_risk_population_persons,
                    "total_hrst_persons": metrics.total_hrst_persons,
                    "at_risk_hrst_persons": metrics.at_risk_hrst_persons,
                    "total_population_ghs_persons": metrics.total_population_ghs_persons,
                    "at_risk_population_ghs_persons": metrics.at_risk_population_ghs_persons,
                    "cluster_count": metrics.cluster_count,
                    "total_risk_area_square_kilometers": metrics.total_risk_area_square_kilometers,
                }
            )

        # Create summary directory and export CSV
        summary_dir = self.config.output_dir / "economic_impact" / "summary"
        summary_dir.mkdir(parents=True, exist_ok=True)

        summary_df = pd.DataFrame(summary_data)
        csv_path = summary_dir / "economic_impact_summary.csv"
        summary_df.to_csv(csv_path, index=False)

        logger.info(f"Saved summary report to {csv_path}")
        logger.info("Summary report completed")

    def export_scenario_data(
        self, impact_results: Dict[str, Dict[str, float]], scenario_name: str
    ) -> None:
        """
        Export individual scenario data to CSV file.

        Creates detailed CSV exports for each scenario containing all
        calculated impact metrics and analysis parameters.

        Args:
            impact_results: Dictionary containing impact results for all indicators
            scenario_name: Name of the scenario for file naming
        """
        logger.info(f"Exporting data for scenario: {scenario_name}")

        # Create scenario output directory
        scenario_dir = (
            self.config.output_dir / "economic_impact" / scenario_name.lower()
        )
        scenario_dir.mkdir(parents=True, exist_ok=True)

        # Prepare data for CSV export
        csv_data = []
        for indicator, results in impact_results.items():
            csv_data.append(
                {
                    "scenario": scenario_name,
                    "indicator": indicator.upper(),
                    "total_value": results["total_value"],
                    "at_risk_value": results["at_risk_value"],
                    "safe_value": results["safe_value"],
                    "risk_percentage": results["risk_percentage"],
                    "safe_percentage": results["safe_percentage"],
                    "flood_risk_threshold": self.max_safe_flood_risk,
                }
            )

        # Export to CSV
        df = pd.DataFrame(csv_data)
        csv_path = scenario_dir / f"economic_impact_{scenario_name.lower()}.csv"
        df.to_csv(csv_path, index=False)

        logger.info(f"Saved impact data to {csv_path}")


def run_economic_impact_analysis_from_config(
    config: ProjectConfig,
) -> Dict[str, Dict[str, Dict[str, float]]]:
    """
    Convenience function to run the complete economic impact analysis.

    Provides a simple interface to execute the full economic impact analysis
    pipeline with a single function call using project configuration.

    Args:
        config: Project configuration containing all necessary parameters

    Returns:
        Dictionary containing results for all scenarios and indicators
    """
    analyzer = EconomicImpactAnalyzer(config)
    return analyzer.run_economic_impact_analysis()
