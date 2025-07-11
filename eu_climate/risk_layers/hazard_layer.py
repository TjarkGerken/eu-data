from typing import Dict, List, Optional, Tuple
from matplotlib import pyplot as plt
import numpy as np
import rasterio
import rasterio.features
import rasterio.warp
import geopandas as gpd
from scipy import ndimage
from dataclasses import dataclass
import pandas as pd
from eu_climate.config.config import ProjectConfig
from eu_climate.utils.utils import setup_logging
from eu_climate.utils.conversion import RasterTransformer
from eu_climate.utils.visualization import LayerVisualizer
from eu_climate.utils.normalise_data import (
    AdvancedDataNormalizer,
    NormalizationStrategy,
)


logger = setup_logging(__name__)


@dataclass
class SeaLevelScenario:
    """
    Configuration for sea level rise scenarios used in flood risk assessment.

    This dataclass defines the parameters for different sea level rise scenarios,
    providing a standardized way to represent and process various climate projections.

    Attributes:
        name: Human-readable name for the scenario (e.g., "Current", "Conservative")
        rise_meters: Sea level rise amount in meters above current levels
        description: Detailed description of the scenario and its timeframe
    """

    name: str
    rise_meters: float
    description: str

    @classmethod
    def get_default_scenarios(cls) -> List["SeaLevelScenario"]:
        """
        Returns the default set of sea level rise scenarios for analysis.

        Provides a comprehensive range of scenarios from current conditions
        to extreme projections, covering different timeframes and confidence levels.

        Returns:
            List of SeaLevelScenario objects representing standard assessment scenarios
        """
        return [
            cls("Current", 0.0, "Current sea level - todays scenario (2025)"),
            cls(
                "Conservative", 1.0, "1m sea level rise - conservative scenario (2100)"
            ),
            cls("Moderate", 2.0, "2m sea level rise - moderate scenario (2100)"),
            cls("Severe", 3.0, "3m sea level rise - severe scenario (2100)"),
            cls(
                "Very Severe", 10.0, "10m sea level rise - very severe scenario (2300)"
            ),
            cls("Extreme", 15.0, "15m sea level rise - extreme scenario (2300)"),
        ]


class HazardLayer:
    """
    Hazard Layer Implementation for Flood Risk Assessment
    ===================================================

    The HazardLayer class processes Digital Elevation Model (DEM) data and hydrological
    information to assess flood risks under different sea level rise scenarios. It
    integrates multiple data sources to create comprehensive flood risk assessments.

    Key Features:
    - Configurable sea level rise scenarios (current to extreme projections)
    - River polygon network integration for enhanced flood modeling
    - Advanced elevation-based risk calculation with decay functions
    - Coastline proximity enhancement for coastal flood risks
    - Proper cartographic projection handling and spatial analysis
    - Standardized data harmonization and normalization
    - Comprehensive visualization and export capabilities

    Data Sources Processed:
    1. Digital Elevation Model (DEM):
       - High-resolution topographic data
       - Basis for elevation-based flood risk calculation

    2. River Polygon Network:
       - Detailed hydrological features
       - Enhanced flood risk modeling near waterways
       - Size filtering for computational efficiency

    3. Coastline Data:
       - Coastal boundaries for proximity analysis
       - Enhanced flood risk in coastal zones

    4. Land Mass Data:
       - Land/water distinction
       - Study area masking and validation

    Processing Pipeline:
    1. Load and prepare DEM and auxiliary datasets
    2. Apply sea level rise scenarios to elevation data
    3. Calculate base elevation flood risk with decay functions
    4. Apply river proximity enhancements
    5. Apply coastline proximity enhancements
    6. Combine and normalize risk factors
    7. Export results and create visualizations

    The layer supports both individual scenario processing and batch processing
    with immediate export capabilities for memory-efficient handling of large datasets.
    """

    def __init__(self, config: ProjectConfig):
        """
        Initialize the Hazard Layer with project configuration.

        Sets up all required components including data paths, transformation tools,
        normalizers, and loads auxiliary datasets for flood risk processing.

        Args:
            config: Project configuration containing paths and processing parameters
        """
        self.config = config
        self.dem_path = self.config.dem_path
        self.river_polygons_path = self.config.river_polygons_path
        self.scenarios = SeaLevelScenario.get_default_scenarios()

        # Initialize river polygon network (loaded later)
        self.river_polygon_network = None

        # Initialize raster transformer for coordinate system handling
        self.transformer = RasterTransformer(
            target_crs=self.config.target_crs, config=self.config
        )

        # Initialize visualization component
        self.visualizer = LayerVisualizer(self.config)

        # Initialize sophisticated normalizer for hazard data
        self.normalizer = AdvancedDataNormalizer(
            NormalizationStrategy.HAZARD_SOPHISTICATED
        )

        # Validate required input files
        for path in [self.dem_path, self.river_polygons_path]:
            if not path.exists():
                raise FileNotFoundError(f"Required file not found: {path}")

        # Load river polygon data during initialization
        self.load_river_polygon_data()

        logger.info("Initialized Hazard Layer with DEM and river polygon data")

    def load_and_prepare_dem(
        self,
    ) -> Tuple[np.ndarray, rasterio.Affine, rasterio.crs.CRS, np.ndarray]:
        """
        Load and prepare Digital Elevation Model (DEM) data and land mass mask.

        Processes DEM data by transforming to target coordinate system, aligning
        with study area boundaries, and creating associated land mass masks for
        proper water/land distinction in flood analysis.

        Returns:
            Tuple containing:
            - DEM data array: Elevation values in target CRS and resolution
            - Affine transform: Spatial reference transformation matrix
            - Coordinate Reference System: CRS object for spatial operations
            - Land mass mask: Binary array (1=land, 0=water)
        """
        logger.info("Loading DEM data...")

        # Get reference bounds from NUTS-L3 for consistency with other layers
        nuts_l3_path = self.config.data_dir / "NUTS-L3-NL.shp"
        reference_bounds = self.transformer.get_reference_bounds(nuts_l3_path)

        # Load and transform DEM using NUTS-L3 bounds for consistent study area
        dem_data, transform, crs = self.transformer.transform_raster(
            self.dem_path,
            reference_bounds=reference_bounds,
            resampling_method=self.config.resampling_method.name.lower()
            if hasattr(self.config.resampling_method, "name")
            else str(self.config.resampling_method).lower(),
        )

        # Load and align land mass raster to DEM grid using same bounds
        land_mass_data, land_transform, _ = self.transformer.transform_raster(
            self.config.land_mass_path,
            reference_bounds=reference_bounds,
            resampling_method=self.config.resampling_method.name.lower()
            if hasattr(self.config.resampling_method, "name")
            else str(self.config.resampling_method).lower(),
        )

        # Ensure land mass data is aligned with DEM
        if not self.transformer.validate_alignment(
            land_mass_data, land_transform, dem_data, transform
        ):
            land_mass_data = self.transformer.ensure_alignment(
                land_mass_data,
                land_transform,
                transform,
                dem_data.shape,
                self.config.resampling_method.name.lower()
                if hasattr(self.config.resampling_method, "name")
                else str(self.config.resampling_method).lower(),
            )

        # Create binary land mask (1=land, 0=water)
        land_mask = (land_mass_data > 0).astype(np.uint8)

        # Calculate spatial resolution in meters for reporting
        res_x = abs(transform[0])  # Width of a pixel in meters
        res_y = abs(transform[4])  # Height of a pixel in meters

        # Log DEM statistics for validation
        valid_data = dem_data[~np.isnan(dem_data)]
        logger.info("DEM Statistics:")
        logger.info(f"  Shape: {dem_data.shape}")
        logger.info(f"  Resolution: {res_x:.2f} x {res_y:.2f} meters")
        logger.info(f"  Min elevation: {np.min(valid_data):.2f}m")
        logger.info(f"  Max elevation: {np.max(valid_data):.2f}m")
        logger.info(f"  Mean elevation: {np.mean(valid_data):.2f}m")
        logger.info(f"  Coverage: {len(valid_data) / dem_data.size * 100:.1f}%")

        # Calculate and log the actual spatial bounds of the DEM
        corners = [
            (0, 0),  # top-left
            (dem_data.shape[1], 0),  # top-right
            (dem_data.shape[1], dem_data.shape[0]),  # bottom-right
            (0, dem_data.shape[0]),  # bottom-left
        ]

        # Transform corners to geographic coordinates
        dem_bounds = []
        for x, y in corners:
            x_geo, y_geo = transform * (x, y)
            dem_bounds.extend([float(x_geo), float(y_geo)])

        # Extract min/max coordinates for bounds reporting
        dem_bounds = [
            min(dem_bounds[::2]),  # left
            max(dem_bounds[::2]),  # right
            min(dem_bounds[1::2]),  # bottom
            max(dem_bounds[1::2]),  # top
        ]
        logger.info(f"DEM bounds: {dem_bounds}")

        return dem_data, transform, crs, land_mask

    def load_river_polygon_data(self) -> gpd.GeoDataFrame:
        """
        Load and prepare river polygon network data for enhanced flood modeling.

        Processes river polygon data by transforming to target coordinate system
        and clipping to study area boundaries for computational efficiency.

        Returns:
            GeoDataFrame containing processed river polygon network
        """
        logger.info("Loading river polygon network data...")

        try:
            # Get target CRS from configuration
            target_crs = rasterio.crs.CRS.from_string(self.config.target_crs)

            # Load river polygons with explicit CRS handling
            river_polygon_network = gpd.read_file(self.river_polygons_path)

            # Set CRS if not already defined
            if river_polygon_network.crs is None:
                river_polygon_network.set_crs(target_crs, inplace=True)
                logger.info(f"Set river polygon network CRS to {target_crs}")

            # Transform to target CRS if different
            if river_polygon_network.crs != target_crs:
                river_polygon_network = river_polygon_network.to_crs(target_crs)
                logger.info(f"Transformed river polygon network to {target_crs}")

            self.river_polygon_network = river_polygon_network

            # Log coordinate ranges to verify correct transformation
            bounds = river_polygon_network.total_bounds
            logger.info(
                f"River polygon network bounds: [{bounds[0]:.2f}, {bounds[2]:.2f}] x [{bounds[1]:.2f}, {bounds[3]:.2f}]"
            )

            logger.info(f"Loaded {len(river_polygon_network)} river polygons")
            return river_polygon_network

        except Exception as e:
            logger.warning(f"Could not process river polygon data: {str(e)}")
            logger.warning(
                "Proceeding with basic flood model without river polygon influence"
            )
            return None

    def calculate_flood_extent(
        self,
        dem_data: np.ndarray,
        sea_level_rise: float,
        transform: rasterio.Affine,
        land_mask: np.ndarray,
    ) -> np.ndarray:
        """
        Calculate normalized flood risk based on elevation, river networks, and sea level rise.

        This is the core method for flood risk assessment that combines multiple risk factors
        to produce a comprehensive normalized flood risk map. The method applies a sophisticated
        multi-step process to account for elevation, river proximity, and coastline effects.

        Args:
            dem_data: Digital elevation model data array
            sea_level_rise: Sea level rise in meters for the scenario
            transform: Affine transform matrix for spatial reference
            land_mask: Binary land mask (1=land, 0=water)

        Returns:
            Normalized array where values range from 0 (no risk) to 1 (maximum risk)
        """
        logger.info(
            f"Calculating normalized flood risk for {sea_level_rise}m sea level rise..."
        )

        # Load NUTS boundaries for study area definition
        nuts_gdf = self._load_nuts_boundaries()
        if nuts_gdf is None:
            raise ValueError(
                "Could not load NUTS boundaries - required for flood extent calculation"
            )

        # Create mask for valid land areas (non-NaN DEM values)
        valid_land_mask = ~np.isnan(dem_data)

        # Always rasterize NUTS to DEM grid for study area definition
        nuts_mask = rasterio.features.rasterize(
            [(geom, 1) for geom in nuts_gdf.geometry],
            out_shape=dem_data.shape,
            transform=transform,
            dtype=np.uint8,
        )

        # Define valid study area combining land, NUTS, and data availability
        valid_study_area = valid_land_mask & (nuts_mask == 1) & (land_mask == 1)

        # Step 1: Calculate base elevation-based flood risk
        elevation_risk = self._calculate_elevation_flood_risk(
            dem_data, sea_level_rise, valid_study_area
        )

        # Step 2: Apply river proximity decay enhancement
        river_decay_enhanced_risk = self._apply_river_proximity_decay(
            dem_data, elevation_risk, sea_level_rise, valid_study_area, transform
        )

        # Calculate elevation statistics for context adjustment
        study_elevations = dem_data[valid_study_area]
        elevation_stats = self._calculate_elevation_statistics(
            study_elevations, sea_level_rise
        )

        # Step 3: Apply study area context adjustment
        context_adjusted_risk = self._apply_study_area_context_adjustment(
            river_decay_enhanced_risk, dem_data, elevation_stats, valid_study_area
        )

        # Step 4: Calculate river risk enhancement zones
        river_risk_enhancement = self._calculate_river_risk_enhancement(
            dem_data.shape, transform
        )

        # Step 5: Calculate coastline risk enhancement zones
        coastline_risk_enhancement, coastline_zone_mask = (
            self._calculate_coastline_risk_enhancement(
                dem_data.shape, transform, land_mask
            )
        )

        # Step 6: Combine all risk factors
        combined_risk = self._combine_flood_risks(
            context_adjusted_risk,
            river_risk_enhancement,
            coastline_risk_enhancement,
            valid_study_area,
        )

        # Step 7: Apply smoothing to reduce noise
        smoothed_risk = ndimage.gaussian_filter(
            np.nan_to_num(combined_risk, nan=0), sigma=self.config.smoothing_sigma
        )

        # Step 8: Final normalization using sophisticated approach
        final_risk = self.normalizer.normalize_hazard_data(
            smoothed_risk, valid_study_area
        )

        # Log comprehensive risk statistics
        self._log_final_risk_statistics(final_risk, valid_study_area)

        # Calculate area statistics for reporting
        pixel_width = abs(transform[0])
        pixel_height_top = abs(transform[4])
        pixel_height_bottom = abs(transform[4] + transform[5] * dem_data.shape[0])
        pixel_height_avg = (pixel_height_top + pixel_height_bottom) / 2
        pixel_area_m2 = pixel_width * pixel_height_avg

        # Calculate risk area statistics
        valid_pixels = np.int64(np.sum(valid_study_area))
        high_risk_pixels = np.int64(np.sum((final_risk > 0.7) & valid_study_area))
        moderate_risk_pixels = np.int64(
            np.sum((final_risk > 0.3) & (final_risk <= 0.7) & valid_study_area)
        )
        low_risk_pixels = np.int64(
            np.sum((final_risk > 0.1) & (final_risk <= 0.3) & valid_study_area)
        )

        total_area_km2 = (valid_pixels * pixel_area_m2) / 1_000_000.0
        high_risk_area_km2 = (high_risk_pixels * pixel_area_m2) / 1_000_000.0
        moderate_risk_area_km2 = (moderate_risk_pixels * pixel_area_m2) / 1_000_000.0
        low_risk_area_km2 = (low_risk_pixels * pixel_area_m2) / 1_000_000.0

        valid_risk_values = final_risk[valid_study_area]
        mean_risk = np.mean(valid_risk_values) if len(valid_risk_values) > 0 else 0.0
        max_risk = np.max(valid_risk_values) if len(valid_risk_values) > 0 else 0.0

        logger.info(f"  Total study area: {total_area_km2:.2f} km²")
        logger.info(
            f"  High risk area (>0.7): {high_risk_area_km2:.2f} km² ({high_risk_area_km2 / total_area_km2 * 100:.1f}%)"
        )
        logger.info(
            f"  Moderate risk area (0.3-0.7): {moderate_risk_area_km2:.2f} km² ({moderate_risk_area_km2 / total_area_km2 * 100:.1f}%)"
        )
        logger.info(
            f"  Low risk area (0.1-0.3): {low_risk_area_km2:.2f} km² ({low_risk_area_km2 / total_area_km2 * 100:.1f}%)"
        )
        logger.info(f"  Mean risk: {mean_risk:.3f}, Max risk: {max_risk:.3f}")

        return final_risk.astype(np.float32)

    def _create_single_buffer_zone(
        self, river_polygons: gpd.GeoDataFrame, buffer_distance: float
    ) -> gpd.GeoDataFrame:
        """
        Create a single buffer zone around river polygons at specified distance.

        Efficiently combines river geometries and creates uniform buffer zones
        for enhanced flood risk modeling near hydrological features.

        Args:
            river_polygons: GeoDataFrame with river polygon geometries
            buffer_distance: Buffer distance in meters

        Returns:
            GeoDataFrame with the buffer polygon geometry
        """
        from shapely.ops import unary_union

        # Combine all river polygons into a single geometry for efficient buffering
        river_polygons_combined = unary_union(river_polygons.geometry.tolist())

        # Create buffer at specified distance
        buffer_geom = river_polygons_combined.buffer(buffer_distance)

        # Create GeoDataFrame for this buffer zone
        buffer_gdf = gpd.GeoDataFrame(
            {"buffer_distance_m": [buffer_distance]},
            geometry=[buffer_geom],
            crs=river_polygons.crs,
        )

        return buffer_gdf

    def _calculate_elevation_flood_risk(
        self, dem_data: np.ndarray, sea_level_rise: float, valid_study_area: np.ndarray
    ) -> np.ndarray:
        """
        Calculate selective flood risk based on elevation within study area context.

        Uses a sophisticated approach that concentrates high risk in truly vulnerable areas,
        applying scientifically-based elevation thresholds and decay functions to avoid
        over-broad risk distribution.

        Args:
            dem_data: Digital elevation model data
            sea_level_rise: Sea level rise scenario in meters
            valid_study_area: Boolean mask defining the valid study area for normalization

        Returns:
            Selective flood risk with realistic distribution
        """
        study_elevations = dem_data[valid_study_area]

        if len(study_elevations) == 0:
            logger.warning("No valid elevations in study area, returning zero risk")
            return np.zeros_like(dem_data, dtype=np.float32)

        # Calculate elevation statistics for risk assessment
        elevation_stats = self._calculate_elevation_statistics(
            study_elevations, sea_level_rise
        )

        # Calculate base risk using elevation and sea level rise
        base_risk = self._calculate_base_elevation_risk(
            dem_data, sea_level_rise, elevation_stats
        )

        return base_risk

    def _calculate_elevation_statistics(
        self, study_elevations: np.ndarray, sea_level_rise: float
    ) -> Dict:
        """
        Calculate comprehensive elevation statistics for risk assessment.

        Analyzes elevation distribution within the study area to inform
        risk calculation parameters and thresholds.

        Args:
            study_elevations: Array of elevation values within study area
            sea_level_rise: Sea level rise scenario in meters

        Returns:
            Dictionary containing elevation statistics and derived parameters
        """
        min_study_elevation = np.min(study_elevations)
        max_study_elevation = np.max(study_elevations)
        elevation_range = max_study_elevation - min_study_elevation
        mean_study_elevation = np.mean(study_elevations)

        # Get safe elevation threshold from configuration
        max_safe_elevation = self.config.elevation_risk["max_safe_elevation_m"]
        safe_threshold = max_safe_elevation

        logger.info(
            f"Study area elevation range: {min_study_elevation:.2f}m to {max_study_elevation:.2f}m"
        )
        logger.info(f"Study area mean elevation: {mean_study_elevation:.2f}m")
        logger.info(f"Sea level rise scenario: {sea_level_rise:.2f}m")
        logger.info(f"Safe elevation threshold: {safe_threshold:.2f}m")

        return {
            "min_elevation": min_study_elevation,
            "max_elevation": max_study_elevation,
            "elevation_range": elevation_range,
            "mean_elevation": mean_study_elevation,
            "safe_threshold": safe_threshold,
            "vulnerability_range": max(10.0, elevation_range * 0.3),
        }

    def _calculate_base_elevation_risk(
        self, dem_data: np.ndarray, sea_level_rise: float, elevation_stats: Dict
    ) -> np.ndarray:
        """
        Calculate base elevation risk using standard decay parameters.

        Applies the primary elevation-based risk calculation using configured
        decay factors and thresholds.

        Args:
            dem_data: Digital elevation model data
            sea_level_rise: Sea level rise scenario in meters
            elevation_stats: Dictionary of elevation statistics

        Returns:
            Base elevation risk array
        """
        return self._calculate_elevation_risk_with_decay(
            dem_data,
            sea_level_rise,
            elevation_stats,
            self.config.elevation_risk["risk_decay_factor"],
        )

    def _calculate_elevation_risk_with_decay(
        self,
        dem_data: np.ndarray,
        sea_level_rise: float,
        elevation_stats: Dict,
        decay_factor: float,
    ) -> np.ndarray:
        """
        Calculate elevation risk with specified decay factor.

        Implements the core elevation-based risk calculation with configurable
        decay parameters for different risk zones based on elevation relative
        to sea level rise scenarios.

        Args:
            dem_data: Digital elevation model data
            sea_level_rise: Sea level rise scenario in meters
            elevation_stats: Dictionary of elevation statistics
            decay_factor: Exponential decay factor for risk calculation

        Returns:
            Elevation-based risk array with applied decay
        """
        elevation_range = elevation_stats["elevation_range"]
        safe_threshold = elevation_stats["safe_threshold"]
        vulnerability_range = elevation_stats["vulnerability_range"]

        # Handle edge case of uniform elevation
        if elevation_range == 0:
            logger.warning(
                "All elevations in study area are identical, using uniform risk"
            )
            uniform_risk = (
                0.3 if elevation_stats["min_elevation"] <= safe_threshold else 0.05
            )
            return np.full_like(dem_data, uniform_risk, dtype=np.float32)

        # Calculate elevation above sea level rise
        elevation_above_slr = dem_data - sea_level_rise
        risk = np.zeros_like(dem_data, dtype=np.float32)

        # Zone 1: Areas below sea level rise (highest risk)
        below_slr_mask = elevation_above_slr <= 0
        if np.any(below_slr_mask):
            depth_below_slr = np.abs(elevation_above_slr[below_slr_mask])
            risk[below_slr_mask] = 0.8 + 0.19 * (1 - np.exp(-depth_below_slr / 2.0))

        # Zone 2: Vulnerable areas above sea level rise but within vulnerability range
        vulnerable_mask = (elevation_above_slr > 0) & (
            elevation_above_slr <= vulnerability_range
        )
        if np.any(vulnerable_mask):
            height_above_slr = elevation_above_slr[vulnerable_mask]
            risk[vulnerable_mask] = 0.6 * np.exp(-height_above_slr / decay_factor)

        # Zone 3: Moderate risk areas between vulnerability range and safe threshold
        moderate_mask = (elevation_above_slr > vulnerability_range) & (
            dem_data <= safe_threshold
        )
        if np.any(moderate_mask):
            risk[moderate_mask] = 0.05 + 0.1 * np.exp(
                -(elevation_above_slr[moderate_mask] - vulnerability_range) / 5.0
            )

        # Zone 4: Low risk areas above safe threshold
        safe_mask = dem_data > safe_threshold
        if np.any(safe_mask):
            risk[safe_mask] = 0.001 + 0.009 * np.exp(
                -(dem_data[safe_mask] - safe_threshold) / 10.0
            )

        return risk

    def _apply_river_proximity_decay(
        self,
        dem_data: np.ndarray,
        base_risk: np.ndarray,
        sea_level_rise: float,
        valid_study_area: np.ndarray,
        transform: rasterio.Affine,
    ) -> np.ndarray:
        """Apply enhanced risk decay near rivers where higher decay takes precedence."""
        if not self.config.river_risk_decay:
            return base_risk

        if self.river_polygon_network is None:
            self.load_river_polygon_data()

        if self.river_polygon_network is None:
            logger.warning(
                "No river polygon network available, skipping river proximity decay"
            )
            return base_risk

        river_proximity_mask = self._create_river_proximity_mask(
            dem_data.shape, transform
        )

        if not np.any(river_proximity_mask):
            logger.info("No areas within river proximity distance, using base risk")
            return base_risk

        elevation_stats = {
            "min_elevation": np.min(dem_data[valid_study_area]),
            "max_elevation": np.max(dem_data[valid_study_area]),
            "elevation_range": np.max(dem_data[valid_study_area])
            - np.min(dem_data[valid_study_area]),
            "safe_threshold": self.config.elevation_risk["max_safe_elevation_m"],
            "vulnerability_range": max(
                10.0,
                (
                    np.max(dem_data[valid_study_area])
                    - np.min(dem_data[valid_study_area])
                )
                * 0.3,
            ),
        }

        enhanced_decay_factor = self.config.river_risk_decay["enhanced_decay_factor"]
        river_enhanced_risk = self._calculate_elevation_risk_with_decay(
            dem_data, sea_level_rise, elevation_stats, enhanced_decay_factor
        )

        combined_risk = base_risk.copy()

        precedence_mask = river_proximity_mask & (river_enhanced_risk > base_risk)
        combined_risk[precedence_mask] = river_enhanced_risk[precedence_mask]

        affected_pixels = np.sum(precedence_mask)
        total_pixels = np.sum(valid_study_area)
        logger.info(
            f"River proximity decay applied to {affected_pixels} pixels ({affected_pixels / total_pixels * 100:.2f}% of study area)"
        )
        logger.info(
            f"Enhanced decay factor: {enhanced_decay_factor} (vs base: {self.config.elevation_risk['risk_decay_factor']})"
        )

        return combined_risk

    def _create_river_proximity_mask(
        self, data_shape: Tuple[int, int], transform: rasterio.Affine
    ) -> np.ndarray:
        """Create mask for areas within river proximity distance."""
        decay_distance = self.config.river_risk_decay["decay_distance_m"]
        min_river_area = self.config.river_risk_decay["min_river_area_m2"]

        filtered_rivers = self._filter_rivers_by_area(
            self.river_polygon_network, min_river_area
        )

        if len(filtered_rivers) == 0:
            logger.warning(
                f"No rivers meet minimum area requirement ({min_river_area} m²)"
            )
            return np.zeros(data_shape, dtype=bool)

        from shapely.ops import unary_union

        combined_rivers = unary_union(filtered_rivers.geometry.tolist())
        buffer_geom = combined_rivers.buffer(decay_distance)

        if hasattr(buffer_geom, "geoms"):
            buffer_geometries = [
                (geom, 1) for geom in buffer_geom.geoms if geom.is_valid
            ]
        else:
            buffer_geometries = [(buffer_geom, 1)] if buffer_geom.is_valid else []

        if not buffer_geometries:
            logger.warning("No valid buffer geometries created for river proximity")
            return np.zeros(data_shape, dtype=bool)

        buffer_raster = rasterio.features.rasterize(
            buffer_geometries,
            out_shape=data_shape,
            transform=transform,
            dtype=np.uint8,
            all_touched=True,
        )

        logger.info(
            f"Created river proximity mask within {decay_distance}m of {len(filtered_rivers)} rivers"
        )
        return buffer_raster == 1

    def _filter_rivers_by_area(
        self, rivers_gdf: gpd.GeoDataFrame, min_area_m2: float
    ) -> gpd.GeoDataFrame:
        """Filter rivers by minimum area requirement."""
        rivers_with_area = rivers_gdf.copy()
        rivers_with_area["area_m2"] = rivers_with_area.geometry.area

        filtered_rivers = rivers_with_area[rivers_with_area["area_m2"] >= min_area_m2]

        logger.info(
            f"River area filtering: {len(filtered_rivers)} rivers remain (from {len(rivers_gdf)}) with minimum area {min_area_m2} m²"
        )

        return filtered_rivers.drop(columns=["area_m2"])

    def _apply_study_area_context_adjustment(
        self,
        risk_data: np.ndarray,
        dem_data: np.ndarray,
        elevation_stats: Dict,
        valid_study_area: np.ndarray,
    ) -> np.ndarray:
        """Apply study area context adjustment to risk values."""
        elevation_range = elevation_stats["elevation_range"]
        min_elevation = elevation_stats["min_elevation"]

        study_percentile = np.zeros_like(dem_data, dtype=np.float32)
        if elevation_range > 0:
            study_percentile[valid_study_area] = (
                dem_data[valid_study_area] - min_elevation
            ) / elevation_range

        context_adjustment = (
            1.0 + 0.2 * (1.0 - study_percentile) - 0.1 * study_percentile
        )

        final_risk = risk_data * context_adjustment
        final_risk = final_risk * valid_study_area

        return final_risk

    def _log_final_risk_statistics(
        self, final_risk: np.ndarray, valid_study_area: np.ndarray
    ) -> None:
        """Log comprehensive risk statistics for analysis."""
        final_valid_risks = final_risk[valid_study_area]
        if len(final_valid_risks) == 0:
            return

        logger.info("Risk calculation statistics:")
        logger.info(
            f"  Range: {np.min(final_valid_risks):.4f} to {np.max(final_valid_risks):.4f}"
        )
        logger.info(f"  Mean: {np.mean(final_valid_risks):.4f}")
        logger.info(f"  Median: {np.median(final_valid_risks):.4f}")

        very_high_count = np.sum(final_valid_risks > 0.8)
        high_risk_count = np.sum((final_valid_risks > 0.6) & (final_valid_risks <= 0.8))
        moderate_risk_count = np.sum(
            (final_valid_risks > 0.3) & (final_valid_risks <= 0.6)
        )
        low_risk_count = np.sum((final_valid_risks > 0.1) & (final_valid_risks <= 0.3))
        minimal_risk_count = np.sum(final_valid_risks <= 0.1)

        total_pixels = len(final_valid_risks)
        logger.info("Risk distribution:")
        logger.info(
            f"  Very High (>0.8): {very_high_count / total_pixels * 100:.1f}% ({very_high_count} pixels)"
        )
        logger.info(
            f"  High (0.6-0.8): {high_risk_count / total_pixels * 100:.1f}% ({high_risk_count} pixels)"
        )
        logger.info(
            f"  Moderate (0.3-0.6): {moderate_risk_count / total_pixels * 100:.1f}% ({moderate_risk_count} pixels)"
        )
        logger.info(
            f"  Low (0.1-0.3): {low_risk_count / total_pixels * 100:.1f}% ({low_risk_count} pixels)"
        )
        logger.info(
            f"  Minimal (<=0.1): {minimal_risk_count / total_pixels * 100:.1f}% ({minimal_risk_count} pixels)"
        )

        significant_risk_count = very_high_count + high_risk_count + moderate_risk_count
        logger.info(
            f"  Total significant risk (>0.3): {significant_risk_count / total_pixels * 100:.1f}%"
        )

    def _filter_rivers_by_size(self, rivers_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Filter river polygons by area to focus on significant rivers and improve performance.

        Args:
            rivers_gdf: GeoDataFrame with river polygon geometries

        Returns:
            Filtered GeoDataFrame with only significant rivers
        """
        # Calculate area for each river polygon
        rivers_with_area = rivers_gdf.copy()
        rivers_with_area["area_m2"] = rivers_with_area.geometry.area

        # Define size thresholds
        min_area_m2 = 50_000  # 500 m² minimum (removes tiny streams)
        max_area_m2 = (
            50_000_000  # 50 km² maximum (removes huge water bodies like lakes)
        )

        # Filter by area
        filtered_rivers = rivers_with_area[(rivers_with_area["area_m2"] >= min_area_m2)]

        logger.info("River filtering results:")
        logger.info(f"  Original rivers: {len(rivers_gdf):,}")
        logger.info(f"  After size filtering: {len(filtered_rivers):,}")
        logger.info(f"  Removed: {len(rivers_gdf) - len(filtered_rivers):,} rivers")
        logger.info(
            f"  Area range: {min_area_m2 / 1000:.1f}-{max_area_m2 / 1_000_000:.0f}km² ({min_area_m2}-{max_area_m2:,} m²)"
        )

        if len(filtered_rivers) > 0:
            area_stats = filtered_rivers["area_m2"]
            logger.info(
                f"  Remaining river areas - Min: {area_stats.min():,.0f} m², Max: {area_stats.max():,.0f} m², Mean: {area_stats.mean():,.0f} m²"
            )

        return filtered_rivers.drop(columns=["area_m2"])

    def _calculate_river_risk_enhancement(
        self, shape: Tuple[int, int], transform: rasterio.Affine
    ) -> np.ndarray:
        """
        Calculate flood risk enhancement using buffer zones around filtered significant river polygons.
        Filters rivers by size to focus on important waterways and uses efficient buffer creation.

        Args:
            shape: Shape of the raster grid
            transform: Affine transform matrix

        Returns:
            Risk enhancement multiplier (1.0 = no enhancement, >1.0 = increased risk)
        """
        try:
            if self.river_polygon_network is None:
                self.load_river_polygon_data()

            if self.river_polygon_network is None:
                logger.warning(
                    "No river polygon network available, skipping river risk enhancement"
                )
                return np.ones(shape, dtype=np.float32)

            zones = self.config.river_zones
            logger.info("Processing river polygon enhancement with size filtering")
            logger.info(
                f"Original river polygon count: {len(self.river_polygon_network)}"
            )
            logger.info(
                f"River polygon bounds: {self.river_polygon_network.total_bounds}"
            )
            logger.info(f"Raster shape: {shape}, pixel size: {abs(transform[0]):.1f}m")

            # Step 1: Filter rivers by size to focus on significant waterways
            filtered_rivers = self._filter_rivers_by_size(self.river_polygon_network)

            if len(filtered_rivers) == 0:
                logger.warning("No rivers remaining after filtering!")
                return np.ones(shape, dtype=np.float32)

            # Step 2: Create buffer zones efficiently for filtered rivers
            from shapely.ops import unary_union

            logger.info(
                f"Creating optimized buffer zones for {len(filtered_rivers)} filtered rivers:"
            )
            logger.info(
                f"  High risk: {zones['high_risk_distance_m']}m (weight: {zones['high_risk_weight']})"
            )
            logger.info(
                f"  Moderate risk: {zones['moderate_risk_distance_m']}m (weight: {zones['moderate_risk_weight']})"
            )
            logger.info(
                f"  Low risk: {zones['low_risk_distance_m']}m (weight: {zones['low_risk_weight']})"
            )

            # Combine all filtered rivers into a single geometry for efficient buffering
            logger.info("Combining filtered river geometries...")
            combined_rivers = unary_union(filtered_rivers.geometry.tolist())

            # Initialize enhancement array
            enhancement = np.ones(shape, dtype=np.float32)
            total_pixels = shape[0] * shape[1]

            # Step 3: Create and apply buffer zones (largest to smallest for proper overlap)
            buffer_configs = [
                ("low_risk", zones["low_risk_distance_m"], zones["low_risk_weight"]),
                (
                    "moderate_risk",
                    zones["moderate_risk_distance_m"],
                    zones["moderate_risk_weight"],
                ),
                ("high_risk", zones["high_risk_distance_m"], zones["high_risk_weight"]),
            ]

            for zone_name, buffer_distance, risk_weight in buffer_configs:
                logger.info(
                    f"Processing {zone_name} buffer zone ({buffer_distance}m)..."
                )

                # Create buffer
                buffer_geom = combined_rivers.buffer(buffer_distance)

                # Rasterize buffer
                if hasattr(buffer_geom, "geoms"):
                    buffer_geometries = [
                        (geom, 1) for geom in buffer_geom.geoms if geom.is_valid
                    ]
                else:
                    buffer_geometries = (
                        [(buffer_geom, 1)] if buffer_geom.is_valid else []
                    )

                if not buffer_geometries:
                    logger.warning(f"No valid {zone_name} buffer geometries!")
                    continue

                buffer_raster = rasterio.features.rasterize(
                    buffer_geometries,
                    out_shape=shape,
                    transform=transform,
                    dtype=np.uint8,
                    all_touched=True,
                )

                # Apply enhancement (overwrites previous zones)
                buffer_mask = buffer_raster == 1
                enhancement[buffer_mask] = risk_weight

                enhanced_pixels = np.sum(buffer_mask)
                logger.info(
                    f"  Applied to {enhanced_pixels:,} pixels ({enhanced_pixels / total_pixels * 100:.2f}%)"
                )

            # Log final statistics
            total_enhanced = np.sum(enhancement != 1.0)
            high_risk_pixels = np.sum(enhancement == zones["high_risk_weight"])
            moderate_risk_pixels = np.sum(enhancement == zones["moderate_risk_weight"])
            low_risk_pixels = np.sum(enhancement == zones["low_risk_weight"])

            logger.info("Final filtered river enhancement results:")
            logger.info(
                f"  High risk pixels: {high_risk_pixels:,} ({high_risk_pixels / total_pixels * 100:.2f}%)"
            )
            logger.info(
                f"  Moderate risk pixels: {moderate_risk_pixels:,} ({moderate_risk_pixels / total_pixels * 100:.2f}%)"
            )
            logger.info(
                f"  Low risk pixels: {low_risk_pixels:,} ({low_risk_pixels / total_pixels * 100:.2f}%)"
            )
            logger.info(
                f"  Total enhanced pixels: {total_enhanced:,} ({total_enhanced / total_pixels * 100:.2f}%)"
            )

            return enhancement

        except Exception as e:
            logger.warning(f"Could not calculate river polygon enhancement: {str(e)}")
            import traceback

            logger.warning(f"Full traceback: {traceback.format_exc()}")
            return np.ones(shape, dtype=np.float32)

    def _combine_flood_risks(
        self,
        elevation_risk: np.ndarray,
        river_enhancement: np.ndarray,
        coastline_enhancement: np.ndarray,
        valid_study_area: np.ndarray,
    ) -> np.ndarray:
        """
        Combine elevation-based flood risk with river and coastline proximity enhancements using unified normalization.

        Args:
            elevation_risk: Base flood risk from elevation (normalized within study area)
            river_enhancement: Risk enhancement multiplier from rivers (≥1.0)
            coastline_enhancement: Risk enhancement multiplier from coastline proximity (≥1.0)
            valid_study_area: Mask for valid areas to consider

        Returns:
            Combined flood risk with preserved gradients and unified normalization
        """
        # Apply both river and coastline enhancements to elevation risk
        enhanced_risk = elevation_risk * river_enhancement * coastline_enhancement

        # Get valid enhanced risk values for normalization
        valid_enhanced_risk = enhanced_risk[valid_study_area]

        if len(valid_enhanced_risk) == 0:
            logger.warning(
                "No valid enhanced risk values, returning original elevation risk"
            )
            return elevation_risk * valid_study_area

        # Calculate statistics for enhanced risk
        mean_enhanced_risk = np.mean(valid_enhanced_risk)
        max_enhanced_risk = np.max(valid_enhanced_risk)
        percentile_99 = np.percentile(valid_enhanced_risk, 99)

        logger.info(
            f"Enhanced risk statistics - Mean: {mean_enhanced_risk:.4f}, Max: {max_enhanced_risk:.4f}, "
            f"99th percentile: {percentile_99:.4f}"
        )

        # Apply soft normalization to preserve gradients while keeping values reasonable
        if percentile_99 > 1.0:
            # Use 99th percentile instead of max to avoid outliers dominating normalization
            normalization_factor = 1.0 / percentile_99
            enhanced_risk = enhanced_risk * normalization_factor
            logger.info(
                f"Applied soft normalization using 99th percentile factor: {normalization_factor:.3f}"
            )

        # Ensure only valid study areas have risk values
        combined_risk = enhanced_risk * valid_study_area

        # Final statistics
        final_valid_risk = combined_risk[valid_study_area]
        if len(final_valid_risk) > 0:
            logger.info(
                f"Final combined risk - Mean: {np.mean(final_valid_risk):.4f}, "
                f"Max: {np.max(final_valid_risk):.4f}, Min: {np.min(final_valid_risk):.4f}"
            )

            # Risk distribution after combination
            high_risk_pct = np.sum(final_valid_risk > 0.7) / len(final_valid_risk) * 100
            moderate_risk_pct = (
                np.sum((final_valid_risk > 0.3) & (final_valid_risk <= 0.7))
                / len(final_valid_risk)
                * 100
            )
            low_risk_pct = (
                np.sum((final_valid_risk > 0.1) & (final_valid_risk <= 0.3))
                / len(final_valid_risk)
                * 100
            )

            logger.info(
                f"Combined risk distribution - High (>0.7): {high_risk_pct:.1f}%, "
                f"Moderate (0.3-0.7): {moderate_risk_pct:.1f}%, Low (0.1-0.3): {low_risk_pct:.1f}%"
            )

        return combined_risk

    def process_scenarios(
        self, custom_scenarios: Optional[List[SeaLevelScenario]] = None
    ) -> Dict[str, np.ndarray]:
        """
        Process sea level rise scenarios with immediate TIF and PNG export per scenario.
        Args:
            custom_scenarios: Optional custom scenarios, uses defaults if None
        Returns:
            Dictionary mapping scenario names to flood extent arrays
        """
        scenarios = custom_scenarios or self.scenarios
        logger.info(
            f"Processing {len(scenarios)} sea level rise scenarios with immediate export..."
        )

        dem_data, transform, crs, land_mask = self.load_and_prepare_dem()

        _, coastline_zone_mask = self._calculate_coastline_risk_enhancement(
            dem_data.shape, transform, land_mask
        )

        flood_extents = {}
        for scenario in scenarios:
            logger.info(
                f"Processing scenario: {scenario.name} ({scenario.rise_meters}m)"
            )
            flood_risk = self.calculate_flood_extent(
                dem_data, scenario.rise_meters, transform, land_mask
            )

            flood_data = {
                "flood_risk": flood_risk,
                "scenario": scenario,
                "transform": transform,
                "crs": crs,
                "dem_data": dem_data,
                "coastline_zone_mask": coastline_zone_mask,
            }
            flood_extents[scenario.name] = flood_data

            self._export_individual_scenario(scenario.name, flood_data, land_mask)

        logger.info("Completed processing all scenarios with immediate export")
        return flood_extents

    def _export_individual_scenario(
        self, scenario_name: str, flood_data: Dict, land_mask: np.ndarray
    ) -> None:
        """
        Export TIF and PNG for individual scenario immediately after processing.

        Args:
            scenario_name: Name of the scenario
            flood_data: Dictionary containing flood risk and metadata
            land_mask: Binary land mask for visualization
        """
        flood_risk = flood_data["flood_risk"]
        transform = flood_data["transform"]
        crs = flood_data["crs"]
        scenario = flood_data["scenario"]
        dem_data = flood_data["dem_data"]

        logger.info(f"Exporting {scenario_name} scenario...")

        risk_output_path = (
            self.config.output_dir
            / "hazard"
            / "tif"
            / f"flood_risk_{scenario_name.lower()}.tif"
        )
        risk_output_path.parent.mkdir(parents=True, exist_ok=True)

        with rasterio.open(
            risk_output_path,
            "w",
            driver="GTiff",
            height=flood_risk.shape[0],
            width=flood_risk.shape[1],
            count=1,
            dtype=np.float32,
            crs=crs,
            transform=transform,
            nodata=-9999.0,
            compress="lzw",
        ) as dst:
            dst.write(flood_risk, 1)
            dst.set_band_description(
                1, f"Normalized flood risk for {scenario.rise_meters}m SLR"
            )
            dst.update_tags(
                description="Normalized flood risk values (0=no risk, 1=maximum risk)",
                scenario=scenario.name,
                sea_level_rise_m=str(scenario.rise_meters),
                method="elevation_profile_with_river_enhancement",
            )

        logger.info(f"  Exported TIF: {risk_output_path}")

        meta = {
            "crs": crs,
            "transform": transform,
            "height": flood_risk.shape[0],
            "width": flood_risk.shape[1],
            "dtype": "float32",
        }

        risk_png_path = (
            self.config.output_dir
            / "hazard"
            / f"hazard_risk_{scenario_name.lower()}_scenario.png"
        )

        self.visualizer.visualize_hazard_scenario(
            flood_mask=flood_risk,
            dem_data=dem_data,
            meta=meta,
            scenario=scenario,
            output_path=risk_png_path,
            show_nl_forecast=False,
            land_mask=land_mask,
            show_coastline_overlay=False,
            coastline_zone_mask=flood_data["coastline_zone_mask"],
            river_polygon_network=self.river_polygon_network,
        )

        logger.info(f"  Exported PNG: {risk_png_path}")

    def visualize_hazard_assessment(
        self, flood_extents: Dict[str, np.ndarray], save_plots: bool = True
    ) -> None:
        """
        Create comprehensive visualization of hazard assessment results.

        Args:
            flood_extents: Dictionary of flood extent data for each scenario
            save_plots: Whether to save visualization to file
        """
        # Set up the plotting parameters
        plt.style.use("default")

        # Create figure with proper grid layout
        fig = plt.figure(figsize=(20, 15))
        gs = plt.GridSpec(
            3, 3, figure=fig, height_ratios=[1, 1, 0.8], width_ratios=[1, 1, 1]
        )

        # Get scenario names from flood extents
        scenarios = list(flood_extents.keys())

        # Get DEM bounds for consistent visualization extent
        first_scenario = list(flood_extents.values())[0]
        dem_bounds = [
            first_scenario["transform"].xoff,
            first_scenario["transform"].xoff
            + first_scenario["transform"].a * first_scenario["dem_data"].shape[1],
            first_scenario["transform"].yoff
            + first_scenario["transform"].e * first_scenario["dem_data"].shape[0],
            first_scenario["transform"].yoff,
        ]

        logger.info(f"DEM bounds in visualization: {dem_bounds}")

        # Try to load NUTS for extent calculation
        nuts_gdf = self._load_nuts_boundaries()

        if nuts_gdf is not None:
            # Get NUTS bounds in the target CRS for extent calculation
            nuts_bounds = nuts_gdf.total_bounds  # [minx, miny, maxx, maxy]
            logger.info(f"Using NUTS-L0 bounds for visualization extent: {nuts_bounds}")
        else:
            # Fall back to DEM bounds
            nuts_bounds = dem_bounds
            logger.info(
                "No NUTS boundaries available, using DEM bounds for visualization extent"
            )

        # Clip river polygon network to visualization extent for performance
        if self.river_polygon_network is not None:
            # Get NUTS-L0 bounds for clipping
            river_polygon_bounds = self.river_polygon_network.total_bounds
            logger.info(
                f"River polygon network bounds after clipping: {river_polygon_bounds}"
            )

        # Get reference DEM data and transform for land mass alignment
        reference_flood_data = list(flood_extents.values())[0]
        reference_dem_data = reference_flood_data["dem_data"]
        reference_transform = reference_flood_data["transform"]

        # Transform land mass data once outside the loop (optimization)
        land_mass_data, land_transform, _ = self.transformer.transform_raster(
            self.config.land_mass_path,
            reference_bounds=None,
            resampling_method=self.config.resampling_method.name.lower()
            if hasattr(self.config.resampling_method, "name")
            else str(self.config.resampling_method).lower(),
        )
        if not self.transformer.validate_alignment(
            land_mass_data, land_transform, reference_dem_data, reference_transform
        ):
            land_mask_aligned = self.transformer.ensure_alignment(
                land_mass_data,
                land_transform,
                reference_transform,
                reference_dem_data.shape,
                self.config.resampling_method.name.lower()
                if hasattr(self.config.resampling_method, "name")
                else str(self.config.resampling_method).lower(),
            )
        else:
            land_mask_aligned = land_mass_data

        land_mask = (land_mask_aligned > 0).astype(np.uint8)

        # Calculate dynamic elevation range for NUTS region
        if nuts_gdf is not None:
            nuts_mask = rasterio.features.rasterize(
                [(geom, 1) for geom in nuts_gdf.geometry],
                out_shape=reference_dem_data.shape,
                transform=reference_transform,
                dtype=np.uint8,
            )
            # Get elevation data within NUTS and land areas only
            nuts_land_mask = (
                (nuts_mask == 1) & (land_mask == 1) & (~np.isnan(reference_dem_data))
            )
            if np.any(nuts_land_mask):
                nuts_elevations = reference_dem_data[nuts_land_mask]
                elevation_min = (
                    np.percentile(nuts_elevations, 2) - 30
                )  # Use 2nd percentile to avoid outliers and add 30m buffer to ensure that only water is blue
                elevation_max = (
                    np.percentile(nuts_elevations, 98) + 100
                )  # Use 98th percentile to avoid outliers and add 100m buffer to ensure that the entire landscape is visible (not all white)
                logger.info(
                    f"Dynamic elevation range for NUTS region: {elevation_min:.1f}m to {elevation_max:.1f}m"
                )
            else:
                # Fallback to global range if no valid data
                valid_elevations = reference_dem_data[~np.isnan(reference_dem_data)]
                elevation_min = (
                    np.percentile(valid_elevations, 2) - 30
                )  # Use 2nd percentile to avoid outliers and add 30m buffer to ensure that only water is blue
                elevation_max = (
                    np.percentile(valid_elevations, 98) + 100
                )  # Use 98th percentile to avoid outliers and add 100m buffer to ensure that the entire landscape is visible (not all white)
                logger.info(
                    f"Fallback elevation range: {elevation_min:.1f}m to {elevation_max:.1f}m"
                )
        else:
            # Fallback to global range if no NUTS data
            valid_elevations = reference_dem_data[~np.isnan(reference_dem_data)]
            elevation_min = (
                np.percentile(valid_elevations, 2) - 30
            )  # Use 2nd percentile to avoid outliers and add 30m buffer to ensure that only water is blue
            elevation_max = (
                np.percentile(valid_elevations, 98) + 100
            )  # Use 98th percentile to avoid outliers and add 100m buffer to ensure that the entire landscape is visible (not all white)
            logger.info(
                f"Global elevation range: {elevation_min:.1f}m to {elevation_max:.1f}m"
            )

        # Panel 1: Overview/composite map with NUTS overlay and rivers
        ax = fig.add_subplot(gs[0, 0])

        # Use reference DEM for the overview
        dem_data = reference_dem_data
        transform = reference_transform

        logger.info(
            f"DEM extent (target CRS): left={nuts_bounds[0]}, right={nuts_bounds[2]}, bottom={nuts_bounds[1]}, top={nuts_bounds[3]}"
        )

        # Create masked elevation data for proper visualization
        # Create a copy of DEM data for visualization
        dem_for_vis = dem_data.copy()

        # Set water areas (where land_mask == 0) to a specific value for proper visualization
        water_elevation = (
            elevation_min - 10
        )  # Set water to below minimum land elevation
        dem_for_vis[land_mask == 0] = water_elevation

        # Create a base elevation visualization with proper water/land distinction
        im1 = ax.imshow(
            dem_for_vis,
            cmap="terrain",
            aspect="equal",
            extent=dem_bounds,
            vmin=water_elevation,
            vmax=elevation_max,
            alpha=0.8,
        )

        # River polygon network overlay
        if self.river_polygon_network is not None:
            logger.info(
                f"River polygon network bounds: {self.river_polygon_network.total_bounds}"
            )
            self.river_polygon_network.plot(
                ax=ax,
                facecolor="darkblue",
                edgecolor="navy",
                linewidth=0.2,
                alpha=0.7,
                zorder=10,
            )

        # NUTS overlay
        if nuts_gdf is not None:
            logger.info(f"NUTS bounds: {nuts_gdf.total_bounds}")
            nuts_gdf.plot(
                ax=ax,
                facecolor="none",
                edgecolor="black",
                linewidth=1.0,
                alpha=1.0,
                zorder=11,
            )

        ax.autoscale(False)

        ax.set_title(
            "Study Area Overview\nElevation with River Polygons and Administrative Boundaries",
            fontsize=12,
            fontweight="bold",
        )
        ax.set_xlabel("X Coordinate (m)")
        ax.set_ylabel("Y Coordinate (m)")

        # Add colorbar for elevation with proper range
        cbar1 = plt.colorbar(im1, ax=ax, shrink=0.8)
        cbar1.set_label("Elevation (m)", rotation=270, labelpad=15)

        # Panels 2-5: Normalized flood risk for each scenario with rivers
        for i, scenario_name in enumerate(scenarios):
            if i >= 4:  # Only show first 4 scenarios
                break

            ax = (
                fig.add_subplot(gs[0, i + 1])
                if i < 2
                else fig.add_subplot(gs[1, i - 2])
            )
            flood_data = flood_extents[scenario_name]
            flood_risk = flood_data["flood_risk"]  # Use normalized risk values
            scenario = flood_data["scenario"]
            dem_data = flood_data["dem_data"]
            transform = flood_data["transform"]

            # Always rasterize NUTS to DEM grid
            nuts_mask = rasterio.features.rasterize(
                [(geom, 1) for geom in nuts_gdf.geometry],
                out_shape=dem_data.shape,
                transform=transform,
                dtype=np.uint8,
            )

            # Create visualization showing normalized flood risk with proper background zones
            valid_study_area = (
                (land_mask == 1) & (nuts_mask == 1) & (~np.isnan(dem_data))
            )

            # Create composite visualization array
            # Start with a base array for all zones
            composite_display = np.zeros_like(dem_data, dtype=np.uint8)

            # Define zone values
            WATER_VALUE = 0  # Existing water bodies (blue)
            OUTSIDE_NL_VALUE = 1  # Land outside Netherlands (gray)
            LAND_BASE_VALUE = 2  # Base value for Netherlands land

            # Set base zones
            composite_display[land_mask == 0] = (
                WATER_VALUE  # Water areas from land mass file
            )
            composite_display[(land_mask == 1) & (nuts_mask == 0)] = (
                OUTSIDE_NL_VALUE  # Outside Netherlands
            )
            composite_display[valid_study_area] = (
                LAND_BASE_VALUE  # Netherlands land areas
            )

            # Create risk overlay only for valid study areas
            risk_overlay = np.full_like(dem_data, np.nan, dtype=np.float32)
            risk_overlay[valid_study_area] = flood_risk[valid_study_area]

            # Display base zones first
            from matplotlib.colors import ListedColormap, LinearSegmentedColormap

            base_colors = [
                "#1f78b4",
                "#bdbdbd",
                "#ffffff",
            ]  # Blue (water), Gray (outside NL), White (NL land base)
            base_cmap = ListedColormap(base_colors)

            # Show base zones
            ax.imshow(
                composite_display,
                cmap=base_cmap,
                aspect="equal",
                extent=dem_bounds,
                vmin=0,
                vmax=2,
                alpha=1.0,
            )

            # Create flood risk colormap (warm colors for risk)
            risk_colors = [
                "#ffffcc",
                "#feb24c",
                "#fd8d3c",
                "#fc4e2a",
                "#e31a1c",
                "#b10026",
            ]
            risk_cmap = LinearSegmentedColormap.from_list(
                "flood_risk", risk_colors, N=256
            )

            # Overlay flood risk only on Netherlands land areas
            im = ax.imshow(
                risk_overlay,
                cmap=risk_cmap,
                aspect="equal",
                extent=dem_bounds,
                vmin=0,
                vmax=1,
                alpha=0.85,
            )

            # NUTS overlay
            if nuts_gdf is not None:
                nuts_gdf.plot(
                    ax=ax,
                    facecolor="none",
                    edgecolor="black",
                    linewidth=0.5,
                    alpha=1.0,
                    zorder=10,
                )

            # River polygon network overlay - filled polygons with subtle outline
            if self.river_polygon_network is not None:
                self.river_polygon_network.plot(
                    ax=ax,
                    facecolor="darkblue",
                    edgecolor="navy",
                    linewidth=0.1,
                    alpha=0.6,
                    zorder=11,
                )

            ax.set_title(
                f"{scenario.name} Scenario\n({scenario.rise_meters}m SLR) - Normalized Risk",
                fontsize=12,
                fontweight="bold",
            )
            ax.set_xlabel("X Coordinate (m)")
            ax.set_ylabel("Y Coordinate (m)")
            ax.set_xlim(dem_bounds[0], dem_bounds[1])
            ax.set_ylim(dem_bounds[2], dem_bounds[3])
            ax.autoscale(False)

            # Add colorbar for flood risk
            cbar = plt.colorbar(im, ax=ax, shrink=0.8)
            cbar.set_label("Flood Risk (0=safe, 1=maximum)", rotation=270, labelpad=15)

            # Add legend for zones and risk levels
            import matplotlib.patches as mpatches

            legend_patches = [
                mpatches.Patch(color="#1f78b4", label="Existing Water Bodies"),
                mpatches.Patch(color="#bdbdbd", label="Outside Netherlands"),
                mpatches.Patch(color="#ffffcc", label="Low Flood Risk (0-0.3)"),
                mpatches.Patch(color="#fd8d3c", label="Moderate Risk (0.3-0.7)"),
                mpatches.Patch(color="#e31a1c", label="High Risk (0.7-1.0)"),
            ]
            ax.legend(
                handles=legend_patches, loc="lower left", fontsize=8, frameon=True
            )

        # Panel 5: Flood risk progression (if we have less than 4 scenarios, place it in remaining slot)
        if len(scenarios) < 4:
            ax5 = fig.add_subplot(gs[1, len(scenarios) - 2])
        else:
            ax5 = fig.add_subplot(gs[1, 2])

        flood_areas = []
        scenario_names = []
        rise_values = []

        for scenario_name in scenarios:
            flood_data = flood_extents[scenario_name]
            flood_risk = flood_data["flood_risk"]
            dem_data = flood_data["dem_data"]

            # Calculate area with significant flood risk (>0.3)
            high_risk_area_km2 = np.sum(flood_risk > 0.3) * (30 * 30) / 1_000_000
            flood_areas.append(high_risk_area_km2)
            scenario_names.append(flood_data["scenario"].name)
            rise_values.append(flood_data["scenario"].rise_meters)

        colors = ["#2e8b57", "#ff8c00", "#dc143c", "#8a2be2"][
            : len(scenarios)
        ]  # SeaGreen, DarkOrange, Crimson, BlueViolet
        bars = ax5.bar(scenario_names, flood_areas, color=colors, alpha=0.7)
        ax5.set_title(
            "High Flood Risk Area by Scenario\n(Risk > 0.3)",
            fontsize=12,
            fontweight="bold",
        )
        ax5.set_ylabel("High Risk Area (km²)")
        ax5.set_xlabel("Sea Level Rise Scenario")

        # Add value labels on bars
        for bar, area in zip(bars, flood_areas):
            height = bar.get_height()
            ax5.text(
                bar.get_x() + bar.get_width() / 2.0,
                height + height * 0.01,
                f"{area:.1f} km²",
                ha="center",
                va="bottom",
                fontweight="bold",
            )

        # Panel 6: River polygon network with elevation profile
        ax6 = fig.add_subplot(gs[2, :])
        if self.river_polygon_network is not None:
            # Plot elevation histogram using dynamic range
            if nuts_gdf is not None and np.any(nuts_land_mask):
                valid_elevations = nuts_elevations
                hist_range = (elevation_min, elevation_max)
                range_label = "NUTS Region"
            else:
                valid_elevations = reference_dem_data[~np.isnan(reference_dem_data)]
                hist_range = (elevation_min, elevation_max)
                range_label = "Study Area"

            ax6.hist(
                valid_elevations,
                bins=100,
                range=hist_range,
                alpha=0.7,
                color="skyblue",
                edgecolor="black",
                zorder=1,
            )

            # Add vertical lines for each scenario
            colors = ["green", "orange", "red", "purple"]
            for i, scenario_name in enumerate(scenarios):
                scenario = flood_extents[scenario_name]["scenario"]
                ax6.axvline(
                    scenario.rise_meters,
                    color=colors[i],
                    linestyle="--",
                    linewidth=2,
                    label=f"{scenario.name} ({scenario.rise_meters}m)",
                    zorder=2,
                )

            # Add statistics
            stats_text = f"Elevation Statistics ({range_label}):\n"
            stats_text += f"Min: {elevation_min:.1f}m\n"
            stats_text += f"Max: {elevation_max:.1f}m\n"
            stats_text += f"Mean: {np.mean(valid_elevations):.1f}m\n"
            if self.river_polygon_network is not None:
                stats_text += "\nRiver Polygon Network:\n"
                stats_text += f"Polygons: {len(self.river_polygon_network)}"

            ax6.text(
                0.98,
                0.98,
                stats_text,
                transform=ax6.transAxes,
                verticalalignment="top",
                horizontalalignment="right",
                bbox=dict(facecolor="white", alpha=0.8, edgecolor="none"),
            )

        ax6.set_xlabel("Elevation (m)")
        ax6.set_ylabel("Frequency")
        ax6.set_title(
            "Elevation Distribution with Sea Level Rise Thresholds\n"
            + f"(Range: {elevation_min:.1f}m to {elevation_max:.1f}m)",
            fontsize=12,
            fontweight="bold",
        )
        ax6.legend()
        ax6.grid(True, alpha=0.3)
        ax6.set_xlim(
            elevation_min - (elevation_max - elevation_min) * 0.1,
            elevation_max + (elevation_max - elevation_min) * 0.1,
        )

        # Add main title
        fig.suptitle(
            "EU Climate Risk Assessment - Enhanced Hazard Layer Analysis\n"
            + "Normalized Flood Risk with River Zone Enhancement and Elevation Profiles",
            fontsize=16,
            fontweight="bold",
            y=0.98,
        )

        if save_plots:
            output_path = (
                self.config.output_dir / "hazard" / "hazard_layer_assessment.png"
            )
            plt.savefig(output_path, dpi=self.config.dpi, bbox_inches="tight")
            logger.info(f"Saved hazard assessment visualization to: {output_path}")
        # TODO: Remove this before pushing
        # plt.show()

    def _load_nuts_boundaries(self) -> gpd.GeoDataFrame:
        """
        Load NUTS administrative boundaries for overlay visualization.

        Returns:
            GeoDataFrame with NUTS boundaries
        """
        try:
            # Get target CRS from config
            target_crs = rasterio.crs.CRS.from_string(self.config.target_crs)

            # Try to load NUTS boundaries, starting with the most detailed level
            nuts_files = [
                "NUTS-L3-NL.shp",  # Most detailed (municipalities/counties)
                "NUTS-L2-NL.shp",  # Provinces
                "NUTS-L1-NL.shp",  # Regions
                "NUTS-L0-NL.shp",  # Countries
            ]

            for nuts_file in nuts_files:
                nuts_path = self.config.data_dir / nuts_file
                if nuts_path.exists():
                    logger.info(f"Loading NUTS boundaries from: {nuts_file}")
                    nuts_gdf = gpd.read_file(nuts_path)

                    # Log information about the loaded boundaries
                    logger.info(f"  Loaded {len(nuts_gdf)} administrative units")
                    logger.info(f"  Original CRS: {nuts_gdf.crs}")

                    # Transform to target CRS if different
                    if nuts_gdf.crs != target_crs:
                        nuts_gdf = nuts_gdf.to_crs(target_crs)
                        logger.info(f"  Transformed to target CRS: {target_crs}")

                    return nuts_gdf

            logger.warning(
                "No NUTS boundary files found. Visualizations will not include administrative boundaries."
            )
            return None

        except Exception as e:
            logger.warning(f"Could not load NUTS boundaries: {str(e)}")
            return None

    def _add_nuts_overlay(
        self, ax, nuts_gdf: gpd.GeoDataFrame, target_crs: rasterio.crs.CRS
    ) -> None:
        """
        Add NUTS administrative boundaries as overlay to a plot.

        Args:
            ax: Matplotlib axis to add overlay to
            nuts_gdf: GeoDataFrame with NUTS boundaries
            target_crs: Target coordinate reference system for reprojection
        """
        if nuts_gdf is None:
            return

        try:
            # Get target CRS from config
            config_target_crs = rasterio.crs.CRS.from_string(self.config.target_crs)

            # Ensure NUTS boundaries are in the target CRS
            if nuts_gdf.crs != config_target_crs:
                nuts_reproj = nuts_gdf.to_crs(config_target_crs)
                logger.info(
                    f"Reprojected NUTS boundaries from {nuts_gdf.crs} to {config_target_crs}"
                )
            else:
                nuts_reproj = nuts_gdf

            # Add the boundaries as overlay
            nuts_reproj.plot(
                ax=ax,
                facecolor="cyan",  # Green fill
                alpha=0.1,  # 20% transparency
                edgecolor="black",  # Bold dark green outlines
                linewidth=2,  # Bold outline width
                zorder=10,  # Ensure it's on top of the raster data
            )

            logger.debug(
                f"Added NUTS overlay with {len(nuts_reproj)} administrative units"
            )

        except Exception as e:
            logger.warning(f"Could not add NUTS overlay: {str(e)}")
            return

    def create_png_visualizations(self, flood_extents: Dict[str, np.ndarray]) -> None:
        """Create PNG visualizations for each hazard scenario using unified styling."""
        logger.info("Creating PNG visualizations for hazard scenarios...")

        # Get reference data for land mask calculation
        reference_flood_data = list(flood_extents.values())[0]
        reference_dem_data = reference_flood_data["dem_data"]
        reference_transform = reference_flood_data["transform"]

        # Transform land mass data once for all scenarios
        land_mass_data, land_transform, _ = self.transformer.transform_raster(
            self.config.land_mass_path,
            reference_bounds=None,
            resampling_method=self.config.resampling_method.name.lower()
            if hasattr(self.config.resampling_method, "name")
            else str(self.config.resampling_method).lower(),
        )
        if not self.transformer.validate_alignment(
            land_mass_data, land_transform, reference_dem_data, reference_transform
        ):
            land_mask_aligned = self.transformer.ensure_alignment(
                land_mass_data,
                land_transform,
                reference_transform,
                reference_dem_data.shape,
                self.config.resampling_method.name.lower()
                if hasattr(self.config.resampling_method, "name")
                else str(self.config.resampling_method).lower(),
            )
        else:
            land_mask_aligned = land_mass_data

        land_mask = (land_mask_aligned > 0).astype(np.uint8)

        for scenario_name, flood_data in flood_extents.items():
            flood_risk = flood_data["flood_risk"]
            transform = flood_data["transform"]
            crs = flood_data["crs"]
            scenario = flood_data["scenario"]
            dem_data = flood_data["dem_data"]

            # Create metadata for visualization
            meta = {
                "crs": crs,
                "transform": transform,
                "height": flood_risk.shape[0],
                "width": flood_risk.shape[1],
                "dtype": "float32",
            }

            # Create output path for normalized risk
            risk_png_path = (
                self.config.output_dir
                / "hazard"
                / f"hazard_risk_{scenario_name.lower()}_scenario.png"
            )

            # Use unified visualizer for normalized risk visualization
            self.visualizer.visualize_hazard_scenario(
                flood_mask=flood_risk,  # Pass normalized risk values
                dem_data=dem_data,
                meta=meta,
                show_nl_forecast=False,
                scenario=scenario,
                output_path=risk_png_path,
                land_mask=land_mask,
                show_coastline_overlay=False,
                coastline_zone_mask=flood_extents[scenario_name]["coastline_zone_mask"],
                river_polygon_network=self.river_polygon_network,
            )

    def create_flood_risk_bar_charts(
        self, flood_extents: Dict[str, np.ndarray]
    ) -> None:
        """
        Create standalone bar charts for flood risk analysis.

        Args:
            flood_extents: Dictionary of flood extent results
        """
        logger.info("Creating standalone flood risk bar charts...")

        # Calculate data for both charts
        flood_areas = []
        scenario_names = []
        rise_values = []
        total_study_area_km2 = None

        for scenario_name in flood_extents.keys():
            flood_data = flood_extents[scenario_name]
            flood_risk = flood_data["flood_risk"]
            dem_data = flood_data["dem_data"]
            scenario = flood_data["scenario"]

            # Calculate pixel area in km²
            pixel_area_km2 = (30 * 30) / 1_000_000

            # Calculate total study area from first scenario (should be same for all)
            if total_study_area_km2 is None:
                # Load NUTS boundaries to calculate study area
                nuts_gdf = self._load_nuts_boundaries()
                if nuts_gdf is not None:
                    # Get reference data for land mask calculation
                    reference_transform = flood_data["transform"]

                    # Transform land mass data
                    land_mass_data, land_transform, _ = (
                        self.transformer.transform_raster(
                            self.config.land_mass_path,
                            reference_bounds=None,
                            resampling_method=self.config.resampling_method.name.lower()
                            if hasattr(self.config.resampling_method, "name")
                            else str(self.config.resampling_method).lower(),
                        )
                    )
                    if not self.transformer.validate_alignment(
                        land_mass_data, land_transform, dem_data, reference_transform
                    ):
                        land_mask_aligned = self.transformer.ensure_alignment(
                            land_mass_data,
                            land_transform,
                            reference_transform,
                            dem_data.shape,
                            self.config.resampling_method.name.lower()
                            if hasattr(self.config.resampling_method, "name")
                            else str(self.config.resampling_method).lower(),
                        )
                    else:
                        land_mask_aligned = land_mass_data

                    land_mask = (land_mask_aligned > 0).astype(np.uint8)

                    # Rasterize NUTS to DEM grid
                    nuts_mask = rasterio.features.rasterize(
                        [(geom, 1) for geom in nuts_gdf.geometry],
                        out_shape=dem_data.shape,
                        transform=reference_transform,
                        dtype=np.uint8,
                    )

                    # Calculate valid study area
                    valid_study_area = (
                        (~np.isnan(dem_data)) & (nuts_mask == 1) & (land_mask == 1)
                    )
                    total_study_area_km2 = np.sum(valid_study_area) * pixel_area_km2
                else:
                    # Fallback: use all non-NaN DEM areas
                    total_study_area_km2 = np.sum(~np.isnan(dem_data)) * pixel_area_km2

            # Calculate area with significant flood risk (>0.3)
            high_risk_area_km2 = np.sum(flood_risk > 0.3) * pixel_area_km2
            flood_areas.append(high_risk_area_km2)
            scenario_names.append(scenario.name)
            rise_values.append(scenario.rise_meters)

        # Define consistent colors for all charts
        scenario_colors = ["#2e8b57", "#ff8c00", "#dc143c", "#8a2be2"][
            : len(scenario_names)
        ]  # SeaGreen, DarkOrange, Crimson, BlueViolet

        # Create absolute bar chart
        self._create_absolute_flood_risk_chart(
            scenario_names, flood_areas, scenario_colors
        )

        # Create relative stacked bar chart
        self._create_relative_flood_risk_chart(
            scenario_names, flood_areas, total_study_area_km2, scenario_colors
        )

        logger.info("Completed creation of standalone flood risk bar charts")

    def _create_absolute_flood_risk_chart(
        self, scenario_names: List[str], flood_areas: List[float], colors: List[str]
    ) -> None:
        """
        Create standalone absolute flood risk bar chart.

        Args:
            scenario_names: List of scenario names
            flood_areas: List of high risk areas in km²
            colors: List of colors for consistent styling
        """
        plt.figure(figsize=(12, 8))

        bars = plt.bar(
            scenario_names,
            flood_areas,
            color=colors,
            alpha=0.8,
            edgecolor="black",
            linewidth=1,
        )

        plt.title(
            "High Flood Risk Area by Sea Level Rise Scenario\n(Risk > 0.3)",
            fontsize=16,
            fontweight="bold",
            pad=20,
        )
        plt.ylabel("High Risk Area (km²)", fontsize=14, fontweight="bold")
        plt.xlabel("Sea Level Rise Scenario", fontsize=14, fontweight="bold")

        # Add value labels on bars
        for bar, area in zip(bars, flood_areas):
            height = bar.get_height()
            plt.text(
                bar.get_x() + bar.get_width() / 2.0,
                height + height * 0.01,
                f"{area:.1f} km²",
                ha="center",
                va="bottom",
                fontweight="bold",
                fontsize=12,
            )

        # Add grid for better readability
        plt.grid(True, alpha=0.3, axis="y")
        plt.gca().set_axisbelow(True)

        # Improve styling
        plt.xticks(fontsize=12, fontweight="bold")
        plt.yticks(fontsize=12)

        # Add subtitle with methodology positioned in bottom right corner
        plt.figtext(
            0.98,
            0.02,
            "Based on DEM analysis with river polygon enhancement and 30m resolution",
            ha="right",
            va="bottom",
            fontsize=10,
            style="italic",
        )

        plt.tight_layout()

        # Save the chart
        output_path = (
            self.config.output_dir / "hazard" / "flood_risk_absolute_by_scenario.png"
        )
        plt.savefig(
            output_path, dpi=self.config.dpi, bbox_inches="tight", facecolor="white"
        )
        plt.close()

        logger.info(f"Saved absolute flood risk bar chart to: {output_path}")

    def _create_relative_flood_risk_chart(
        self,
        scenario_names: List[str],
        flood_areas: List[float],
        total_area_km2: float,
        colors: List[str],
    ) -> None:
        """
        Create standalone relative flood risk stacked bar chart.

        Args:
            scenario_names: List of scenario names
            flood_areas: List of high risk areas in km²
            total_area_km2: Total study area in km²
            colors: List of colors for consistent styling
        """
        plt.figure(figsize=(12, 8))

        # Calculate percentages
        risk_percentages = [(area / total_area_km2) * 100 for area in flood_areas]
        safe_percentages = [100 - risk_pct for risk_pct in risk_percentages]

        # Create stacked bar chart
        x_positions = range(len(scenario_names))

        plt.title(
            "Relative Flood Risk Distribution by Sea Level Rise Scenario\n(Percentage of Total Study Area)",
            fontsize=16,
            fontweight="bold",
            pad=20,
        )
        plt.ylabel("Percentage of Study Area (%)", fontsize=14, fontweight="bold")
        plt.xlabel("Sea Level Rise Scenario", fontsize=14, fontweight="bold")

        # Set x-axis labels
        plt.xticks(x_positions, scenario_names, fontsize=12, fontweight="bold")
        plt.yticks(fontsize=12)

        # Add percentage labels on risk areas
        for i, (risk_pct, area_km2) in enumerate(zip(risk_percentages, flood_areas)):
            if risk_pct > 2:  # Only show label if percentage is significant enough
                plt.text(
                    i,
                    safe_percentages[i] + risk_pct / 2,
                    f"{risk_pct:.1f}%\n({area_km2:.1f} km²)",
                    ha="center",
                    va="center",
                    fontweight="bold",
                    fontsize=10,
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8),
                )

        # Add total area information on safe areas
        for i, safe_pct in enumerate(safe_percentages):
            if safe_pct > 10:  # Only show if there's enough space
                plt.text(
                    i,
                    safe_pct / 2,
                    f"{safe_pct:.1f}%",
                    ha="center",
                    va="center",
                    fontweight="bold",
                    fontsize=10,
                    color="darkgray",
                )

        # Add grid for better readability
        plt.grid(True, alpha=0.3, axis="y")
        plt.gca().set_axisbelow(True)

        # Add legend
        plt.legend(
            loc="upper right", fontsize=12, frameon=True, fancybox=True, shadow=True
        )

        # Set y-axis to 0-100%
        plt.ylim(0, 100)

        # Add subtitle with total area information positioned in bottom right corner
        plt.figtext(
            0.98,
            0.02,
            f"Total Study Area: {total_area_km2:.1f} km² (NUTS regions on land)",
            ha="right",
            va="bottom",
            fontsize=10,
            style="italic",
        )

        plt.tight_layout()

        # Save the chart
        output_path = (
            self.config.output_dir / "hazard" / "flood_risk_relative_by_scenario.png"
        )
        plt.savefig(
            output_path, dpi=self.config.dpi, bbox_inches="tight", facecolor="white"
        )
        plt.close()

        logger.info(f"Saved relative flood risk stacked bar chart to: {output_path}")

    def export_results(self, flood_extents: Dict[str, np.ndarray]) -> None:
        """
        Export comprehensive analysis results (individual scenario exports handled during processing).

        Args:
            flood_extents: Dictionary of flood extent results
        """
        logger.info("Exporting comprehensive analysis results...")

        # Export summary statistics
        summary_stats = []
        for scenario_name, flood_data in flood_extents.items():
            flood_risk = flood_data["flood_risk"]
            dem_data = flood_data["dem_data"]
            scenario = flood_data["scenario"]

            # Calculate areas for different risk levels
            pixel_area_km2 = (30 * 30) / 1_000_000
            total_valid_area_km2 = np.sum(~np.isnan(dem_data)) * pixel_area_km2

            # Risk level statistics
            high_risk_area_km2 = np.sum(flood_risk > 0.7) * pixel_area_km2
            moderate_risk_area_km2 = (
                np.sum((flood_risk > 0.3) & (flood_risk <= 0.7)) * pixel_area_km2
            )
            low_risk_area_km2 = (
                np.sum((flood_risk > 0.1) & (flood_risk <= 0.3)) * pixel_area_km2
            )

            # Mean and maximum risk
            valid_risk = flood_risk[~np.isnan(dem_data)]
            mean_risk = np.mean(valid_risk) if len(valid_risk) > 0 else 0.0
            max_risk = np.max(valid_risk) if len(valid_risk) > 0 else 0.0

            summary_stats.append(
                {
                    "scenario": scenario_name,
                    "sea_level_rise_m": scenario.rise_meters,
                    "total_area_km2": total_valid_area_km2,
                    "high_risk_area_km2": high_risk_area_km2,
                    "moderate_risk_area_km2": moderate_risk_area_km2,
                    "low_risk_area_km2": low_risk_area_km2,
                    "high_risk_percentage": (high_risk_area_km2 / total_valid_area_km2)
                    * 100,
                    "moderate_risk_percentage": (
                        moderate_risk_area_km2 / total_valid_area_km2
                    )
                    * 100,
                    "low_risk_percentage": (low_risk_area_km2 / total_valid_area_km2)
                    * 100,
                    "mean_risk": mean_risk,
                    "max_risk": max_risk,
                    "description": scenario.description,
                }
            )

        # Save summary as CSV
        summary_df = pd.DataFrame(summary_stats)
        summary_path = (
            self.config.output_dir / "hazard" / "hazard_assessment_summary.csv"
        )
        summary_df.to_csv(summary_path, index=False)
        logger.info(f"Exported summary statistics to: {summary_path}")

        self.create_flood_risk_bar_charts(flood_extents)

    def _calculate_coastline_risk_enhancement(
        self, shape: Tuple[int, int], transform: rasterio.Affine, land_mask: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate flood risk enhancement based on distance to coastline.

        Args:
            shape: Shape of the raster grid
            transform: Affine transform matrix
            land_mask: Binary land mask (1=land, 0=water)

        Returns:
            Tuple of (risk enhancement multiplier, coastline zone mask)
            - enhancement: 1.0 = no enhancement, >1.0 = increased risk
            - zone_mask: Binary mask showing areas within coastline influence zone
        """
        try:
            if not self.config.coastline_path.exists():
                logger.warning(
                    f"Coastline file not found: {self.config.coastline_path}"
                )
                return np.ones(shape, dtype=np.float32), np.zeros(shape, dtype=np.uint8)

            # Get coastline configuration
            coastline_distance_m = self.config.config["hazard"]["coastline_risk"][
                "coastline_distance_m"
            ]
            coastline_multiplier = self.config.config["hazard"]["coastline_risk"][
                "coastline_multiplier"
            ]

            logger.info("Calculating coastline risk enhancement:")
            logger.info(f"  Distance threshold: {coastline_distance_m}m")
            logger.info(f"  Risk multiplier: {coastline_multiplier}")
            logger.info(f"  Coastline file: {self.config.coastline_path}")

            # Load coastline data
            target_crs = rasterio.crs.CRS.from_string(self.config.target_crs)
            coastline_gdf = gpd.read_file(self.config.coastline_path)

            logger.info("Loaded coastline data:")
            logger.info(f"  Features: {len(coastline_gdf)}")
            logger.info(f"  Original CRS: {coastline_gdf.crs}")
            logger.info(f"  Original bounds: {coastline_gdf.total_bounds}")

            if coastline_gdf.crs != target_crs:
                coastline_gdf = coastline_gdf.to_crs(target_crs)
                logger.info(f"Transformed coastline to {target_crs}")
                logger.info(f"  Transformed bounds: {coastline_gdf.total_bounds}")

            # Get NUTS boundaries extent to clip coastline data
            nuts_gdf = self._load_nuts_boundaries()
            if nuts_gdf is None:
                logger.warning("No NUTS boundaries available for coastline clipping")
                return np.ones(shape, dtype=np.float32), np.zeros(shape, dtype=np.uint8)

            # Get NUTS extent (bounding box) to avoid overlap issues
            nuts_bounds = nuts_gdf.total_bounds  # [minx, miny, maxx, maxy]

            logger.info("NUTS boundaries:")
            logger.info(f"  Features: {len(nuts_gdf)}")
            logger.info(f"  Bounds: {nuts_bounds}")

            # Add buffer to NUTS bounds to capture nearby coastline features
            buffer_distance = (
                coastline_distance_m * 1.2
            )  # 20% buffer beyond influence zone
            nuts_extent_buffered = [
                nuts_bounds[0] - buffer_distance,  # minx
                nuts_bounds[1] - buffer_distance,  # miny
                nuts_bounds[2] + buffer_distance,  # maxx
                nuts_bounds[3] + buffer_distance,  # maxy
            ]

            logger.info("Buffered clipping extent:")
            logger.info(f"  Buffer distance: {buffer_distance}m")
            logger.info(f"  Buffered bounds: {nuts_extent_buffered}")

            # Check if coastline and NUTS bounds overlap at all
            coastline_bounds = coastline_gdf.total_bounds
            logger.info("Bounds overlap check:")
            logger.info(f"  Coastline bounds: {coastline_bounds}")
            logger.info(f"  NUTS bounds: {nuts_bounds}")
            logger.info(f"  Buffered bounds: {nuts_extent_buffered}")

            # Clip coastline to buffered NUTS extent
            from shapely.geometry import box

            clipping_box = box(*nuts_extent_buffered)
            coastline_clipped = coastline_gdf[
                coastline_gdf.geometry.intersects(clipping_box)
            ]

            logger.info("Clipping results:")
            logger.info(f"  Original coastline features: {len(coastline_gdf)}")
            logger.info(f"  Clipped coastline features: {len(coastline_clipped)}")

            if len(coastline_clipped) == 0:
                logger.warning("No coastline features found within study area extent!")
                logger.warning(
                    "This suggests the coastline data doesn't overlap with the Netherlands study area"
                )
                return np.ones(shape, dtype=np.float32), np.zeros(shape, dtype=np.uint8)

            # Create buffer polygon around coastline (extends into both land and sea)
            logger.info(f"Creating {coastline_distance_m}m buffer around coastline...")

            # Combine all coastline geometries and create buffer
            from shapely.ops import unary_union

            coastline_combined = unary_union(coastline_clipped.geometry.tolist())
            coastline_buffer = coastline_combined.buffer(coastline_distance_m)

            logger.info("Buffer creation:")
            logger.info(f"  Original coastline geometries: {len(coastline_clipped)}")
            logger.info(f"  Combined coastline type: {type(coastline_combined)}")
            logger.info(f"  Buffer distance: {coastline_distance_m}m")
            logger.info(f"  Buffer area: {coastline_buffer.area / 1e6:.2f} km²")

            # Rasterize the buffer polygon
            logger.info("Rasterizing coastline buffer...")
            logger.info(f"  Raster shape: {shape}")
            logger.info(f"  Transform: {transform}")

            # Handle both single geometry and geometry collection
            if hasattr(coastline_buffer, "geoms"):
                # MultiPolygon or GeometryCollection
                buffer_geometries = [
                    (geom, 1) for geom in coastline_buffer.geoms if geom.is_valid
                ]
            else:
                # Single Polygon
                buffer_geometries = (
                    [(coastline_buffer, 1)] if coastline_buffer.is_valid else []
                )

            if not buffer_geometries:
                logger.warning("No valid buffer geometries created!")
                return np.ones(shape, dtype=np.float32), np.zeros(shape, dtype=np.uint8)

            logger.info(f"  Rasterizing {len(buffer_geometries)} buffer geometries...")

            coastline_buffer_raster = rasterio.features.rasterize(
                buffer_geometries,
                out_shape=shape,
                transform=transform,
                dtype=np.uint8,
                all_touched=True,  # Include pixels touched by geometry
            )

            buffer_pixels = np.sum(coastline_buffer_raster == 1)
            logger.info(f"  Buffer pixels in raster: {buffer_pixels}")

            if buffer_pixels == 0:
                logger.warning(
                    "No buffer pixels found in raster! Buffer may be outside raster bounds"
                )
                return np.ones(shape, dtype=np.float32), np.zeros(shape, dtype=np.uint8)

            # Create coastline influence zone by intersecting buffer with land mask
            logger.info("Creating coastline influence zone...")

            # The buffer extends into both land and sea - we only want the land portion
            coastline_zone_mask = (coastline_buffer_raster == 1) & (land_mask == 1)

            # Calculate statistics
            land_pixels = np.sum(land_mask == 1)
            buffer_pixels_total = np.sum(coastline_buffer_raster == 1)
            affected_land_pixels = np.sum(coastline_zone_mask)

            logger.info("Zone calculation:")
            logger.info(f"  Total land pixels: {land_pixels}")
            logger.info(f"  Total buffer pixels (land + sea): {buffer_pixels_total}")
            logger.info(
                f"  Land pixels within {coastline_distance_m}m of coastline: {affected_land_pixels}"
            )

            # Initialize enhancement array with base value (no enhancement)
            enhancement = np.ones(shape, dtype=np.float32)

            # Apply enhancement multiplier to areas within coastline influence zone
            # Use boolean mask directly for indexing
            enhancement[coastline_zone_mask] = coastline_multiplier

            # Convert to uint8 for return (after applying enhancement)
            coastline_zone_mask = coastline_zone_mask.astype(np.uint8)

            affected_pixels = np.sum(coastline_zone_mask)
            total_land_pixels = np.sum(land_mask == 1)
            affected_percentage = (
                (affected_pixels / total_land_pixels * 100)
                if total_land_pixels > 0
                else 0
            )

            logger.info("Applied coastline risk enhancement:")
            logger.info(
                f"  Affected land pixels: {affected_pixels} ({affected_percentage:.1f}% of land)"
            )
            logger.info(
                f"  Enhancement factor: {coastline_multiplier}x within {coastline_distance_m}m"
            )

            return enhancement, coastline_zone_mask

        except Exception as e:
            logger.warning(f"Could not calculate coastline risk enhancement: {str(e)}")
            return np.ones(shape, dtype=np.float32), np.zeros(shape, dtype=np.uint8)
