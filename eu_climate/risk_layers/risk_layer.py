from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np
import rasterio
import rasterio.features
import rasterio.warp
import geopandas as gpd
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import os
import re

from eu_climate.config.config import ProjectConfig
from eu_climate.utils.utils import setup_logging
from eu_climate.utils.conversion import RasterTransformer
from eu_climate.utils.visualization import LayerVisualizer
from eu_climate.utils.caching_wrappers import CacheAwareMethod
from eu_climate.utils.normalise_data import (
    AdvancedDataNormalizer,
    NormalizationStrategy,
)
from eu_climate.risk_layers.hazard_layer import HazardLayer, SeaLevelScenario
from eu_climate.risk_layers.relevance_layer import RelevanceLayer

logger = setup_logging(__name__)


class RiskLayer:
    """
    Climate Risk Layer Implementation for Comprehensive Risk Assessment
    ================================================================

    The RiskLayer class provides the final integration layer that combines hazard
    scenarios with economic relevance data to produce comprehensive climate risk
    assessments. This class represents the culmination of the risk assessment
    pipeline, integrating multiple data sources and analytical approaches.

    Key Features:
    - Multi-hazard scenario integration (sea level rise projections)
    - Economic relevance layer integration (GDP, freight, HRST, population)
    - Comprehensive risk calculation methodologies
    - Flexible scenario analysis with custom parameters
    - Advanced caching for computational efficiency
    - Comprehensive export and visualization capabilities
    - Population-based risk assessment alternatives

    Risk Assessment Methodology:
    The risk assessment follows the established framework:
    Risk = Hazard × Exposure × Vulnerability

    Where:
    - Hazard: Flood risk from sea level rise scenarios (from HazardLayer)
    - Exposure: Economic activities and population at risk locations
    - Vulnerability: Economic relevance and population density (from RelevanceLayer)

    Supported Analysis Types:
    1. Economic Risk Assessment: Combines flood hazard with economic relevance
    2. Population Risk Assessment: Combines flood hazard with population data
    3. Scenario Analysis: Multiple sea level rise projections
    4. Comparative Analysis: Different economic indicators and combinations

    Processing Pipeline:
    1. Load or generate hazard layers for different sea level rise scenarios
    2. Load or generate economic relevance layers for different indicators
    3. Integrate hazard and relevance data using risk calculation methods
    4. Apply advanced normalization and quality assurance
    5. Export risk assessments for each scenario and indicator combination
    6. Generate comprehensive visualizations and summary statistics

    Integration Capabilities:
    - Seamless integration with HazardLayer for flood risk scenarios
    - Integration with RelevanceLayer for economic importance assessment
    - Support for both absolute and relative economic analysis approaches
    - Flexible weighting schemes for different risk factors
    - Comprehensive caching to avoid redundant calculations

    The RiskLayer provides the foundation for climate risk decision-making by
    combining physical hazard projections with economic and social vulnerability
    assessments in a spatially explicit and quantitative framework.
    """

    def __init__(self, config: ProjectConfig):
        """
        Initialize the Risk Layer with comprehensive analytical capabilities.

        Sets up all required components for climate risk assessment including
        hazard analysis, relevance analysis, spatial processing, and visualization.

        Args:
            config: Project configuration containing all processing parameters
        """
        self.config = config

        # Initialize core analysis components
        self.hazard_layer = HazardLayer(config)
        self.relevance_layer = RelevanceLayer(config)

        # Initialize sea level rise scenarios
        self.sea_level_scenarios = SeaLevelScenario.get_default_scenarios()

        # Initialize spatial processing components
        self.transformer = RasterTransformer(
            target_crs=self.config.target_crs, config=self.config
        )

        # Initialize visualization component
        self.visualizer = LayerVisualizer(self.config)

        # Initialize advanced normalizer optimized for risk data
        self.normalizer = AdvancedDataNormalizer(
            NormalizationStrategy.EXPOSITION_OPTIMIZED
        )

        logger.info("Initialized Risk Layer with comprehensive analytical capabilities")

    def load_existing_hazard_outputs(
        self, sea_level_scenarios: List[SeaLevelScenario]
    ) -> Optional[Dict[str, np.ndarray]]:
        """
        Load existing hazard outputs if they exist to avoid redundant computation.

        This method checks for previously computed hazard scenarios and loads them
        if available, significantly improving computational efficiency for repeated
        analyses or when only updating economic components.

        Args:
            sea_level_scenarios: List of sea level rise scenarios to check for

        Returns:
            Dictionary mapping scenario names to hazard arrays, or None if incomplete
        """
        output_dir = Path(self.config.output_dir)

        hazard_results = {}
        all_files_exist = True

        for scenario in sea_level_scenarios:
            hazard_file = (
                output_dir
                / "hazard"
                / "tif"
                / f"flood_risk_{scenario.name.lower()}.tif"
            )

            if hazard_file.exists():
                logger.info(
                    f"Loading existing hazard data for {scenario.name} from {hazard_file}"
                )
                try:
                    with rasterio.open(hazard_file) as src:
                        hazard_results[scenario.name] = src.read(1)
                except Exception as e:
                    logger.warning(
                        f"Failed to load existing hazard file {hazard_file}: {e}"
                    )
                    all_files_exist = False
                    break
            else:
                logger.info(f"Hazard file not found for {scenario.name}: {hazard_file}")
                all_files_exist = False
                break

        if all_files_exist:
            logger.info("Successfully loaded all existing hazard outputs")
            return hazard_results
        else:
            logger.info("Not all hazard outputs exist, will regenerate")
            return None

    def load_existing_relevance_outputs(self) -> Optional[Dict[str, np.ndarray]]:
        """
        Load existing relevance outputs if they exist to avoid redundant computation.

        This method checks for previously computed relevance layers and loads them
        if available, improving computational efficiency when only updating hazard
        scenarios or performing sensitivity analysis.

        Returns:
            Dictionary mapping layer names to relevance arrays, or None if incomplete
        """
        output_dir = Path(self.config.output_dir)

        # Get expected economic variables from configuration
        economic_variables = self.config.config["relevance"]["economic_variables"]
        relevance_files = {}

        # Map expected files for each variable
        for variable in economic_variables:
            relevance_files[variable] = (
                output_dir / "relevance" / "tif" / f"relevance_{variable}.tif"
            )

        # Also check for combined relevance layer
        relevance_files["combined"] = (
            output_dir / "relevance" / "tif" / "relevance_combined.tif"
        )

        relevance_results = {}
        all_files_exist = True

        # Attempt to load each relevance file
        for layer_name, file_path in relevance_files.items():
            if file_path.exists():
                logger.info(
                    f"Loading existing relevance data for {layer_name} from {file_path}"
                )
                try:
                    with rasterio.open(file_path) as src:
                        relevance_results[layer_name] = src.read(1)
                except Exception as e:
                    logger.warning(
                        f"Failed to load existing relevance file {file_path}: {e}"
                    )
                    all_files_exist = False
                    break
            else:
                logger.info(f"Relevance file not found: {file_path}")
                all_files_exist = False
                break

        if all_files_exist:
            logger.info("Successfully loaded all existing relevance outputs")
            return relevance_results
        else:
            logger.info("Not all relevance outputs exist, will regenerate")
            return None

    @CacheAwareMethod(
        cache_type="raster_data",
        input_files=["land_mass_path"],
        config_attrs=["target_crs", "target_resolution"],
    )
    def load_land_mask(self) -> Tuple[np.ndarray, rasterio.Affine, rasterio.crs.CRS]:
        """
        Load and prepare land mass mask for valid study area definition.

        This method loads the land mass raster and creates a binary mask that
        defines the valid study area for risk assessment, ensuring that risk
        calculations are only performed on land areas.

        Returns:
            Tuple containing:
            - Binary land mask array (1=land, 0=water)
            - Affine transformation matrix for spatial reference
            - Coordinate reference system for spatial operations
        """
        logger.info("Loading land mass mask...")

        # Use NUTS-L3 boundaries to define reference area
        nuts_l3_path = self.config.data_dir / "NUTS-L3-NL.shp"
        reference_bounds = self.transformer.get_reference_bounds(nuts_l3_path)

        # Load and transform land mass data
        land_mass_data, transform, crs = self.transformer.transform_raster(
            self.config.land_mass_path,
            reference_bounds=reference_bounds,
            resampling_method=self.config.resampling_method.name.lower()
            if hasattr(self.config.resampling_method, "name")
            else str(self.config.resampling_method).lower(),
        )

        # Create binary land mask
        land_mask = (land_mass_data > 0).astype(np.uint8)

        # Log mask statistics
        logger.info(f"Land mask shape: {land_mask.shape}")
        logger.info(f"Land coverage: {np.sum(land_mask) / land_mask.size * 100:.1f}%")

        return land_mask, transform, crs

    @CacheAwareMethod(
        cache_type="final_results",
        input_files=["dem_path", "land_mass_path"],
        config_attrs=["target_crs", "target_resolution", "risk_weights"],
    )
    def process_risk_scenarios(
        self, custom_sea_level_scenarios: Optional[List[SeaLevelScenario]] = None
    ) -> Dict[str, np.ndarray]:
        """
        Process comprehensive risk scenarios combining sea level rise and economic data.

        This is the main method for climate risk assessment that integrates hazard
        scenarios with economic relevance data to produce spatially explicit risk
        assessments for different climate projections.

        Args:
            custom_sea_level_scenarios: Optional custom scenarios, uses defaults if None

        Returns:
            Dictionary mapping scenario names to risk assessment arrays
        """
        logger.info("=== STARTING process_risk_scenarios ===")
        logger.info("Processing comprehensive risk scenarios...")

        # Use provided scenarios or default set
        sea_level_scenarios = custom_sea_level_scenarios or self.sea_level_scenarios

        # Load spatial reference data
        land_mask, transform, crs = self.load_land_mask()

        # Load or generate hazard data
        logger.info("Checking for existing hazard outputs...")
        hazard_results = self.load_existing_hazard_outputs(sea_level_scenarios)

        if hazard_results is None:
            logger.info("Regenerating hazard scenarios...")
            hazard_results = self.hazard_layer.process_scenarios(sea_level_scenarios)

        # Load or generate relevance data
        logger.info("Checking for existing relevance outputs...")
        economic_results = self.load_existing_relevance_outputs()

        if economic_results is None:
            logger.info("Regenerating economic layers...")
            economic_results = self.relevance_layer.run_relevance_analysis(
                visualize=False, export_individual_tifs=True
            )

        # Validate economic data availability
        logger.info(f"Available economic variables: {list(economic_results.keys())}")

        # Define economic variables for processing
        economic_variables = [
            var for var in economic_results.keys() if var != "combined"
        ]

        # Always include combined layer if available
        if "combined" in economic_results:
            economic_variables.append("combined")

        # Validate data availability
        if not economic_variables:
            logger.error("No economic variables found for risk assessment!")
            return {}

        logger.info(f"Economic variables to process: {economic_variables}")

        # Process risk scenarios for each combination
        risk_scenarios = {}

        for slr_scenario in sea_level_scenarios:
            # Create descriptive scenario name with SLR level
            scenario_name = f"SLR-{int(slr_scenario.rise_meters)}-{slr_scenario.name}"

            # Get hazard data for this scenario
            hazard_data = hazard_results[slr_scenario.name]

            logger.info(
                f"Calculating risk for {scenario_name} with {len(economic_variables)} economic variables"
            )

            # Process each economic variable
            for economic_variable in economic_variables:
                if economic_variable == "combined":
                    combined_scenario_name = f"{scenario_name}_COMBINED"
                    logger.info(
                        f"Processing combined economic scenario: {combined_scenario_name}"
                    )

                    # Use combined economic data
                    economic_data = economic_results[economic_variable]

                    # Calculate integrated risk
                    risk_data = self.calculate_integrated_risk(
                        hazard_data, economic_data, land_mask
                    )

                    risk_scenarios[combined_scenario_name] = risk_data
                else:
                    # Process individual economic variable
                    individual_scenario_name = (
                        f"{scenario_name}_{economic_variable.upper()}"
                    )
                    logger.info(
                        f"Processing individual economic scenario: {individual_scenario_name}"
                    )

                    # Use specific economic data
                    economic_data = economic_results[economic_variable]

                    # Calculate integrated risk
                    risk_data = self.calculate_integrated_risk(
                        hazard_data, economic_data, land_mask
                    )

                    risk_scenarios[individual_scenario_name] = risk_data

        logger.info(f"Completed processing {len(risk_scenarios)} risk scenarios")
        return risk_scenarios

    def calculate_integrated_risk(
        self,
        hazard_data: np.ndarray,
        economic_data: Union[Dict[str, np.ndarray], np.ndarray],
        land_mask: np.ndarray,
    ) -> np.ndarray:
        """
        Calculate integrated risk from hazard and economic data using current GDP levels.
        Uses filtered calculation that only applies economic risk where flood risk exists.

        Args:
            hazard_data: Hazard layer data (0-1 normalized)
            economic_data: Either a dictionary of economic layer data or a single combined numpy array
            land_mask: Valid study area mask

        Returns:
            Integrated risk data (0-1 normalized)
        """
        weights = self.config.risk_weights
        hazard_weight = weights["hazard"]
        economic_weight = weights["economic"]

        # Get thresholds from config
        max_safe_flood_risk = self.config.max_safe_flood_risk
        min_economic_value = self.config.min_economic_value
        logger.info(f"Using flood risk threshold: {max_safe_flood_risk}")
        logger.info(f"Using minimum economic value threshold: {min_economic_value}")

        # Clip hazard data: set values below threshold to 0
        clipped_hazard_data = np.where(
            hazard_data > max_safe_flood_risk, hazard_data, 0.0
        )
        logger.info(f"Clipped hazard values below {max_safe_flood_risk} to 0")
        logger.info(
            f"Hazard cells above threshold: {np.sum(clipped_hazard_data > 0)} / {clipped_hazard_data.size}"
        )

        # Use current GDP levels (multiplier = 1.0)
        economic_multiplier = 1.0

        # Handle different economic data formats
        if isinstance(economic_data, np.ndarray):
            # Pre-combined economic data (e.g., from relevance_combined.tif)
            combined_economic = economic_data * economic_multiplier
        elif isinstance(economic_data, dict) and len(economic_data) == 1:
            # Single economic variable passed as dictionary
            combined_economic = list(economic_data.values())[0] * economic_multiplier
        else:
            logger.error(
                f"Unexpected economic data format: {type(economic_data)} with length {len(economic_data) if isinstance(economic_data, dict) else 'N/A'}"
            )
            logger.error(
                "Economic data should be either a numpy array or a dictionary with exactly one variable"
            )
            combined_economic = (
                np.zeros_like(land_mask, dtype=np.float32)
                if isinstance(land_mask, np.ndarray)
                else np.zeros((100, 100))
            )

        if clipped_hazard_data.shape != combined_economic.shape:
            logger.info("Aligning economic data to hazard grid...")
            from scipy.ndimage import zoom

            zoom_factors = (
                clipped_hazard_data.shape[0] / combined_economic.shape[0],
                clipped_hazard_data.shape[1] / combined_economic.shape[1],
            )
            combined_economic = zoom(combined_economic, zoom_factors, order=1)

        # Initialize risk data with zeros
        risk_data = np.zeros_like(clipped_hazard_data, dtype=np.float32)

        # Create masks for filtered calculation
        flood_risk_mask = clipped_hazard_data > 0
        economic_relevance_mask = combined_economic > min_economic_value
        land_valid_mask = land_mask > 0

        # Combined mask: only calculate risk where there is both flood risk AND economic relevance
        calculation_mask = flood_risk_mask & economic_relevance_mask & land_valid_mask

        # Apply weighted calculation only where both conditions are met
        if np.any(calculation_mask):
            risk_data[calculation_mask] = (
                hazard_weight * clipped_hazard_data[calculation_mask]
                + economic_weight * combined_economic[calculation_mask]
            )

            # Normalize risk data ensuring full range utilization
            risk_data = self.normalizer.normalize_risk_data(risk_data, calculation_mask)

            logger.info(
                f"Economic risk calculated for {np.sum(calculation_mask)} cells"
            )
            logger.info(
                f"Flood risk cells: {np.sum(flood_risk_mask & land_valid_mask)}"
            )
            logger.info(
                f"Economic relevance cells: {np.sum(economic_relevance_mask & land_valid_mask)}"
            )
            logger.info(f"Combined risk cells: {np.sum(calculation_mask)}")
        else:
            logger.warning(
                "No cells meet both flood risk and economic relevance criteria"
            )

        return risk_data

    def export_risk_scenarios(
        self,
        risk_scenarios: Dict[str, np.ndarray],
        transform: rasterio.Affine,
        crs: rasterio.crs.CRS,
        land_mask: Optional[np.ndarray] = None,
    ) -> None:
        """Export risk scenarios to the specified directory structure."""
        logger.info("Exporting risk scenarios...")
        logger.info(f"Received scenario names: {list(risk_scenarios.keys())}")

        # Create metadata dict for visualization
        meta = {"transform": transform, "crs": crs}

        for scenario_name, risk_data in risk_scenarios.items():
            # Parse scenario name to extract SLR scenario part
            # Expected formats: "SLR-0-Current_GDP", "SLR-1-Conservative_FREIGHT", etc.
            # We need to extract just the SLR part: "SLR-0-Current", "SLR-1-Conservative", etc.

            # Use regex to match SLR pattern: SLR-{number}-{name}
            # This will work with any custom scenarios
            slr_pattern = r"^(SLR-\d+-[^_]+)"
            match = re.match(slr_pattern, scenario_name)

            if match:
                slr_part = match.group(1)
                # Extract economic part (everything after SLR scenario + "_")
                if (
                    len(scenario_name) > len(slr_part)
                    and scenario_name[len(slr_part)] == "_"
                ):
                    economic_part = scenario_name[len(slr_part) + 1 :]
                else:
                    economic_part = None
            else:
                # Fallback if parsing fails
                logger.warning(f"Could not parse scenario name: {scenario_name}")
                slr_part = scenario_name
                economic_part = "UNKNOWN"

            # Create clean title for visualization
            if economic_part:
                clean_scenario_title = (
                    f"{slr_part} - {economic_part.replace('_', ' ').title()}"
                )
            else:
                clean_scenario_title = slr_part

            # Create simplified directory structure: risk/SLR-scenario/
            output_dir = self.config.output_dir / "risk" / slr_part
            output_dir.mkdir(parents=True, exist_ok=True)

            # TIFs go in tif subdirectory
            tif_path = output_dir / "tif" / f"risk_{scenario_name}.tif"
            tif_path.parent.mkdir(parents=True, exist_ok=True)

            self.save_risk_raster(risk_data, transform, crs, tif_path)

            # PNGs go directly in the scenario directory
            png_path = output_dir / f"risk_{scenario_name}.png"

            self.visualizer.visualize_risk_layer(
                risk_data=risk_data,
                meta=meta,
                scenario_title=f"{clean_scenario_title}",
                output_path=png_path,
                land_mask=land_mask,
            )

            logger.info(f"Exported risk scenario: {scenario_name} -> {output_dir}")

        logger.info("Risk scenario export complete")

    def save_risk_raster(
        self,
        risk_data: np.ndarray,
        transform: rasterio.Affine,
        crs: rasterio.crs.CRS,
        output_path: Path,
    ) -> None:
        """Save risk data as GeoTIFF."""
        with rasterio.open(
            output_path,
            "w",
            driver="GTiff",
            height=risk_data.shape[0],
            width=risk_data.shape[1],
            count=1,
            dtype=risk_data.dtype,
            crs=crs,
            transform=transform,
            compress="lzw",
        ) as dst:
            dst.write(risk_data, 1)

        logger.info(f"Saved risk raster: {output_path}")

    def run_risk_assessment(
        self,
        visualize: bool = True,
        export_results: bool = True,
        custom_sea_level_scenarios: Optional[List[SeaLevelScenario]] = None,
    ) -> Dict[str, np.ndarray]:
        """
        Run complete risk assessment process using current GDP levels.

        Args:
            visualize: Whether to create visualizations
            export_results: Whether to export results to files
            custom_sea_level_scenarios: Custom sea level scenarios

        Returns:
            Risk scenario results
        """
        logger.info("Starting risk assessment with current GDP levels...")

        risk_scenarios = self.process_risk_scenarios(custom_sea_level_scenarios)

        if export_results or visualize:
            land_mask, transform, crs = self.load_land_mask()

            if export_results:
                self.export_risk_scenarios(risk_scenarios, transform, crs, land_mask)

        logger.info("Risk assessment complete")
        return risk_scenarios

    @CacheAwareMethod(
        cache_type="raster_data",
        input_files=["population_2025_path"],
        config_attrs=["target_crs", "target_resolution"],
    )
    def load_population_data(self) -> np.ndarray:
        """Load 2025 population data with corrected resolution handling."""
        logger.info(
            "Loading 2025 population data with corrected resolution handling..."
        )

        from ..utils.data_loading import load_population_2025_with_validation

        # Use the corrected 2025 population loading function
        population_data, metadata, validation_passed = (
            load_population_2025_with_validation(
                config=self.config, apply_study_area_mask=True
            )
        )

        logger.info(f"2025 population validation passed: {validation_passed}")

        # Normalize population data ensuring full range utilization
        valid_mask = ~np.isnan(population_data) & (population_data >= 0)
        normalized_population = self.normalizer.normalize_risk_data(
            population_data, valid_mask
        )

        logger.info(f"Population data shape: {normalized_population.shape}")
        logger.info(
            f"Population coverage: {np.sum(normalized_population > 0) / normalized_population.size * 100:.1f}%"
        )

        return normalized_population

    def calculate_population_risk(
        self,
        hazard_data: np.ndarray,
        population_data: np.ndarray,
        land_mask: np.ndarray,
    ) -> np.ndarray:
        """
        Calculate integrated risk from hazard and population data.
        Uses filtered calculation that only applies population risk where flood risk exists.

        Args:
            hazard_data: Hazard layer data (0-1 normalized)
            population_data: Population density data (0-1 normalized)
            land_mask: Valid study area mask

        Returns:
            Integrated population risk data (0-1 normalized)
        """
        weights = self.config.risk_weights
        hazard_weight = weights["hazard"]
        population_weight = weights.get(
            "population", weights["economic"]
        )  # Use economic weight as fallback

        # Get thresholds from config
        max_safe_flood_risk = self.config.max_safe_flood_risk
        min_population_threshold = (
            0.01  # Minimum population density threshold (1% of max)
        )

        logger.info(f"Using flood risk threshold: {max_safe_flood_risk}")
        logger.info(f"Using minimum population threshold: {min_population_threshold}")

        # Clip hazard data: set values below threshold to 0
        clipped_hazard_data = np.where(
            hazard_data > max_safe_flood_risk, hazard_data, 0.0
        )
        logger.info(f"Clipped hazard values below {max_safe_flood_risk} to 0")
        logger.info(
            f"Hazard cells above threshold: {np.sum(clipped_hazard_data > 0)} / {clipped_hazard_data.size}"
        )

        # Align population data to hazard grid if needed
        if clipped_hazard_data.shape != population_data.shape:
            logger.info("Aligning population data to hazard grid...")
            from scipy.ndimage import zoom

            zoom_factors = (
                clipped_hazard_data.shape[0] / population_data.shape[0],
                clipped_hazard_data.shape[1] / population_data.shape[1],
            )
            population_data = zoom(population_data, zoom_factors, order=1)

        # Initialize risk data with zeros
        risk_data = np.zeros_like(clipped_hazard_data, dtype=np.float32)

        # Create masks for filtered calculation
        flood_risk_mask = clipped_hazard_data > 0
        population_relevance_mask = population_data > min_population_threshold
        land_valid_mask = land_mask > 0

        # Combined mask: only calculate risk where there is both flood risk AND population presence
        calculation_mask = flood_risk_mask & population_relevance_mask & land_valid_mask

        # Apply weighted calculation only where both conditions are met
        if np.any(calculation_mask):
            risk_data[calculation_mask] = (
                hazard_weight * clipped_hazard_data[calculation_mask]
                + population_weight * population_data[calculation_mask]
            )

            # Normalize risk data ensuring full range utilization
            risk_data = self.normalizer.normalize_risk_data(risk_data, calculation_mask)

            logger.info(
                f"Population risk calculated for {np.sum(calculation_mask)} cells"
            )
            logger.info(
                f"Flood risk cells: {np.sum(flood_risk_mask & land_valid_mask)}"
            )
            logger.info(
                f"Population relevance cells: {np.sum(population_relevance_mask & land_valid_mask)}"
            )
            logger.info(f"Combined risk cells: {np.sum(calculation_mask)}")
        else:
            logger.warning(
                "No cells meet both flood risk and population relevance criteria"
            )

        return risk_data

    @CacheAwareMethod(
        cache_type="final_results",
        input_files=["dem_path", "land_mass_path", "population_2025_path"],
        config_attrs=["target_crs", "target_resolution", "risk_weights"],
    )
    def process_population_risk_scenarios(
        self, custom_sea_level_scenarios: Optional[List[SeaLevelScenario]] = None
    ) -> Dict[str, np.ndarray]:
        """
        Process sea level rise scenarios with population risk assessment.

        Returns:
            Dictionary with structure: {sea_level_scenario: population_risk_data}
        """
        logger.info("Processing population risk scenarios...")

        sea_level_scenarios = custom_sea_level_scenarios or self.sea_level_scenarios

        land_mask, transform, crs = self.load_land_mask()

        # Load population data
        logger.info("Loading population data for risk assessment...")
        population_data = self.load_population_data()

        # Try to load existing hazard outputs first
        logger.info("Checking for existing hazard outputs...")
        hazard_results = self.load_existing_hazard_outputs(sea_level_scenarios)

        if hazard_results is None:
            logger.info("Regenerating hazard scenarios...")
            hazard_results = self.hazard_layer.process_scenarios(sea_level_scenarios)

        population_risk_scenarios = {}

        for slr_scenario in sea_level_scenarios:
            scenario_name = f"SLR-{int(slr_scenario.rise_meters)}-{slr_scenario.name}"

            hazard_data = hazard_results[slr_scenario.name]

            logger.info(f"Calculating population risk for {scenario_name}")

            population_risk_data = self.calculate_population_risk(
                hazard_data=hazard_data,
                population_data=population_data,
                land_mask=land_mask,
            )

            population_risk_scenarios[scenario_name] = population_risk_data

        logger.info(
            f"Processed {len(population_risk_scenarios)} population risk scenarios"
        )
        return population_risk_scenarios

    def export_population_risk_scenarios(
        self,
        population_risk_scenarios: Dict[str, np.ndarray],
        transform: rasterio.Affine,
        crs: rasterio.crs.CRS,
        land_mask: Optional[np.ndarray] = None,
    ) -> None:
        """Export population risk scenarios to the specified directory structure."""
        logger.info("Exporting population risk scenarios...")

        # Create metadata dict for visualization
        meta = {"transform": transform, "crs": crs}

        for scenario_name, population_risk_data in population_risk_scenarios.items():
            # Create simplified directory structure: risk/SLR-scenario/
            output_dir = self.config.output_dir / "risk" / scenario_name
            output_dir.mkdir(parents=True, exist_ok=True)

            # TIFs go in tif subdirectory
            tif_path = output_dir / "tif" / f"risk_{scenario_name}_POPULATION.tif"
            tif_path.parent.mkdir(parents=True, exist_ok=True)

            self.save_risk_raster(population_risk_data, transform, crs, tif_path)

            # PNGs go directly in the scenario directory
            png_path = output_dir / f"risk_{scenario_name}_POPULATION.png"

            self.visualizer.visualize_risk_layer(
                risk_data=population_risk_data,
                meta=meta,
                scenario_title=f"Population - {scenario_name}",
                output_path=png_path,
                land_mask=land_mask,
            )

            logger.info(
                f"Exported population risk scenario: {scenario_name} -> {output_dir}"
            )

        logger.info("Population risk scenario export complete")

    def run_population_risk_assessment(
        self,
        visualize: bool = True,
        export_results: bool = True,
        custom_sea_level_scenarios: Optional[List[SeaLevelScenario]] = None,
    ) -> Dict[str, np.ndarray]:
        """
        Run complete population risk assessment process.

        Args:
            visualize: Whether to create visualizations
            export_results: Whether to export results to files
            custom_sea_level_scenarios: Custom sea level scenarios

        Returns:
            Population risk scenario results
        """
        logger.info("Starting population risk assessment...")

        population_risk_scenarios = self.process_population_risk_scenarios(
            custom_sea_level_scenarios
        )

        if export_results or visualize:
            land_mask, transform, crs = self.load_land_mask()

            if export_results:
                self.export_population_risk_scenarios(
                    population_risk_scenarios, transform, crs, land_mask
                )

        logger.info("Population risk assessment complete")
        return population_risk_scenarios
