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
import matplotlib.colors as mcolors
from eu_climate.config.config import ProjectConfig
from eu_climate.utils.utils import setup_logging
from eu_climate.utils.conversion import RasterTransformer
from eu_climate.utils.visualization import LayerVisualizer
from pathlib import Path


logger = setup_logging(__name__)

@dataclass
class SeaLevelScenario:
    """Configuration for sea level rise scenarios."""
    name: str
    rise_meters: float
    description: str
    
    @classmethod
    def get_default_scenarios(cls) -> List['SeaLevelScenario']:
        """Returns the default set of sea level rise scenarios."""
        return [
            cls("Current", 0.0, "Current sea level - todays scenario"),
            cls("Conservative", 1.0, "1m sea level rise - conservative scenario"),
            cls("Moderate", 2.0, "2m sea level rise - moderate scenario"),
            cls("Severe", 3.0, "3m sea level rise - severe scenario")
        ]

class HazardLayer:
    """
    Hazard Layer Implementation
    ==========================
    
    The Hazard Layer processes Digital Elevation Model (DEM) data and hydrological data
    to assess sea level rise and flood impacts under different scenarios.
    
    Key Features:
    - Configurable sea level rise scenarios
    - River network integration
    - Proper cartographic projection handling
    - Flood extent calculation based on DEM and river analysis
    - Standardized data harmonization
    """
    
    def __init__(self, config: ProjectConfig):
        """Initialize the Hazard Layer with project configuration."""
        self.config = config
        self.dem_path = self.config.dem_path
        self.river_segments_path = self.config.river_segments_path
        self.river_nodes_path = self.config.river_nodes_path
        self.scenarios = SeaLevelScenario.get_default_scenarios()
        
        self.river_network = None
        self.river_nodes = None

        self.transformer = RasterTransformer(
            target_crs=self.config.target_crs,
            config=self.config
        )
        
        self.visualizer = LayerVisualizer(self.config)
        
        for path in [self.dem_path, self.river_segments_path, self.river_nodes_path]:
            if not path.exists():
                raise FileNotFoundError(f"Required file not found: {path}")
        
        # Load river data
        self.load_river_data()
        
        logger.info(f"Initialized Hazard Layer with DEM and river data")
        
    def load_and_prepare_dem(self) -> Tuple[np.ndarray, rasterio.Affine, rasterio.crs.CRS, np.ndarray]:
        """
        Load and prepare Digital Elevation Model (DEM) data and land mass mask.
        Returns:
            Tuple containing:
            - DEM data array
            - Affine transform
            - Coordinate Reference System
            - Land mass mask (1=land, 0=water)
        """
        logger.info("Loading DEM data...")
        
        # Get reference bounds from NUTS-L3 for consistency with other layers
        nuts_l3_path = self.config.data_dir / "NUTS-L3-NL.shp"
        reference_bounds = self.transformer.get_reference_bounds(nuts_l3_path)
        
        # Load DEM using NUTS-L3 bounds for consistent study area
        dem_data, transform, crs = self.transformer.transform_raster(
            self.dem_path,
            reference_bounds=reference_bounds,
            resampling_method=self.config.resampling_method.name.lower() if hasattr(self.config.resampling_method, 'name') else str(self.config.resampling_method).lower()
        )
        
        # Load and align land mass raster to DEM grid using same bounds
        land_mass_data, land_transform, _ = self.transformer.transform_raster(
            self.config.land_mass_path,
            reference_bounds=reference_bounds,
            resampling_method=self.config.resampling_method.name.lower() if hasattr(self.config.resampling_method, 'name') else str(self.config.resampling_method).lower()
        )
        
        if not self.transformer.validate_alignment(land_mass_data, land_transform, dem_data, transform):
            land_mass_data = self.transformer.ensure_alignment(
                land_mass_data, land_transform, transform, dem_data.shape,
                self.config.resampling_method.name.lower() if hasattr(self.config.resampling_method, 'name') else str(self.config.resampling_method).lower()
            )
        land_mask = (land_mass_data > 0).astype(np.uint8)
        
        # Calculate resolution in meters
        res_x = abs(transform[0])  # Width of a pixel in meters
        res_y = abs(transform[4])  # Height of a pixel in meters
        
        # Log statistics
        valid_data = dem_data[~np.isnan(dem_data)]
        logger.info(f"DEM Statistics:")
        logger.info(f"  Shape: {dem_data.shape}")
        logger.info(f"  Resolution: {res_x:.2f} x {res_y:.2f} meters")
        logger.info(f"  Min elevation: {np.min(valid_data):.2f}m")
        logger.info(f"  Max elevation: {np.max(valid_data):.2f}m")
        logger.info(f"  Mean elevation: {np.mean(valid_data):.2f}m")
        logger.info(f"  Coverage: {len(valid_data) / dem_data.size * 100:.1f}%")
        
        # Calculate and log the actual bounds of the DEM
        corners = [
            (0, 0),  # top-left
            (dem_data.shape[1], 0),  # top-right
            (dem_data.shape[1], dem_data.shape[0]),  # bottom-right
            (0, dem_data.shape[0])  # bottom-left
        ]
        
        # Transform corners to geographic coordinates
        dem_bounds = []
        for x, y in corners:
            x_geo, y_geo = transform * (x, y)
            dem_bounds.extend([float(x_geo), float(y_geo)])
        
        # Extract min/max coordinates
        dem_bounds = [
            min(dem_bounds[::2]),  # left
            max(dem_bounds[::2]),  # right
            min(dem_bounds[1::2]),  # bottom
            max(dem_bounds[1::2])   # top
        ]
        logger.info(f"DEM bounds: {dem_bounds}")
        
        return dem_data, transform, crs, land_mask
    
    def load_river_data(self) -> Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
        """Load and prepare river network data."""
        logger.info("Loading river network data...")
        
        try:
            # Get target CRS from config
            target_crs = rasterio.crs.CRS.from_string(self.config.target_crs)
            
            # Load river segments with explicit CRS
            river_network = gpd.read_file(self.river_segments_path)
            river_nodes = gpd.read_file(self.river_nodes_path)
            
            # Set CRS if not already set
            if river_network.crs is None:
                river_network.set_crs(target_crs, inplace=True)
                logger.info(f"Set river network CRS to {target_crs}")
            if river_nodes.crs is None:
                river_nodes.set_crs(target_crs, inplace=True)
                logger.info(f"Set river nodes CRS to {target_crs}")
            
            # Transform to target CRS if different
            if river_network.crs != target_crs:
                river_network = river_network.to_crs(target_crs)
                logger.info(f"Transformed river network to {target_crs}")
            if river_nodes.crs != target_crs:
                river_nodes = river_nodes.to_crs(target_crs)
                logger.info(f"Transformed river nodes to {target_crs}")
            
            self.river_network = river_network
            self.river_nodes = river_nodes
            
            # Log the coordinate ranges to verify correct transformation
            bounds = river_network.total_bounds
            logger.info(f"River network bounds: [{bounds[0]:.2f}, {bounds[2]:.2f}] x [{bounds[1]:.2f}, {bounds[3]:.2f}]")
            
            logger.info(f"Loaded {len(river_network)} river segments and {len(river_nodes)} nodes")
            return river_network, river_nodes
            
        except Exception as e:
            logger.warning(f"Could not process river data: {str(e)}")
            logger.warning("Proceeding with basic flood model without river influence")
            return None, None
    
    def calculate_flood_extent(self, dem_data: np.ndarray, sea_level_rise: float, transform: rasterio.Affine, land_mask: np.ndarray) -> np.ndarray:
        """
        Calculate normalized flood risk based on DEM, river network, sea level rise scenario, and land mass mask.
        Args:
            dem_data: Digital elevation model data array
            sea_level_rise: Sea level rise in meters
            transform: Affine transform matrix for the DEM data
            land_mask: Binary land mask (1=land, 0=water)
        Returns:
            Normalized array where values range from 0 (no risk) to 1 (maximum risk)
        """
        logger.info(f"Calculating normalized flood risk for {sea_level_rise}m sea level rise...")
        
        # Load NUTS boundaries
        nuts_gdf = self._load_nuts_boundaries()
        if nuts_gdf is None:
            raise ValueError("Could not load NUTS boundaries - required for flood extent calculation")
        
        # Create a mask for valid land areas (non-NaN DEM values)
        valid_land_mask = ~np.isnan(dem_data)
        
        # Always rasterize NUTS to DEM grid
        nuts_mask = rasterio.features.rasterize(
            [(geom, 1) for geom in nuts_gdf.geometry],
            out_shape=dem_data.shape,
            transform=transform,
            dtype=np.uint8
        )
        
        
        valid_study_area = (valid_land_mask & (nuts_mask == 1) & (land_mask == 1))
        
        elevation_risk = self._calculate_elevation_flood_risk(dem_data, sea_level_rise, valid_study_area)
        
        river_risk_enhancement = self._calculate_river_risk_enhancement(dem_data.shape, transform)
        
        combined_risk = self._combine_flood_risks(elevation_risk, river_risk_enhancement, valid_study_area)
        
        smoothed_risk = ndimage.gaussian_filter(
            np.nan_to_num(combined_risk, nan=0),
            sigma=self.config.smoothing_sigma
        )
        
        final_risk = self._apply_final_normalization(smoothed_risk, valid_study_area)
        
        pixel_width = abs(transform[0])
        pixel_height_top = abs(transform[4])
        pixel_height_bottom = abs(transform[4] + transform[5] * dem_data.shape[0])
        pixel_height_avg = (pixel_height_top + pixel_height_bottom) / 2
        pixel_area_m2 = pixel_width * pixel_height_avg
        
        valid_pixels = np.int64(np.sum(valid_study_area))
        high_risk_pixels = np.int64(np.sum((final_risk > 0.7) & valid_study_area))
        moderate_risk_pixels = np.int64(np.sum((final_risk > 0.3) & (final_risk <= 0.7) & valid_study_area))
        low_risk_pixels = np.int64(np.sum((final_risk > 0.1) & (final_risk <= 0.3) & valid_study_area))
        
        total_area_km2 = (valid_pixels * pixel_area_m2) / 1_000_000.0
        high_risk_area_km2 = (high_risk_pixels * pixel_area_m2) / 1_000_000.0
        moderate_risk_area_km2 = (moderate_risk_pixels * pixel_area_m2) / 1_000_000.0
        low_risk_area_km2 = (low_risk_pixels * pixel_area_m2) / 1_000_000.0
            
        valid_risk_values = final_risk[valid_study_area]
        mean_risk = np.mean(valid_risk_values) if len(valid_risk_values) > 0 else 0.0
        max_risk = np.max(valid_risk_values) if len(valid_risk_values) > 0 else 0.0
        
        logger.info(f"  Total study area: {total_area_km2:.2f} km²")
        logger.info(f"  High risk area (>0.7): {high_risk_area_km2:.2f} km² ({high_risk_area_km2/total_area_km2*100:.1f}%)")
        logger.info(f"  Moderate risk area (0.3-0.7): {moderate_risk_area_km2:.2f} km² ({moderate_risk_area_km2/total_area_km2*100:.1f}%)")
        logger.info(f"  Low risk area (0.1-0.3): {low_risk_area_km2:.2f} km² ({low_risk_area_km2/total_area_km2*100:.1f}%)")
        logger.info(f"  Mean risk: {mean_risk:.3f}, Max risk: {max_risk:.3f}")
        
        return final_risk.astype(np.float32)
    
    def _rasterize_river_network(self, shape: Tuple[int, int], transform: rasterio.Affine) -> np.ndarray:
        """Convert river network to raster format."""
        river_raster = rasterio.features.rasterize(
            [(geom, 1) for geom in self.river_network.geometry],
            out_shape=shape,
            transform=transform,
            dtype=np.uint8
        )
        return river_raster
    
    def calculate_river_distance(self, shape: Tuple[int, int], transform: rasterio.Affine) -> np.ndarray:
        """Calculate distance to nearest river for each pixel."""
        river_raster = self._rasterize_river_network(shape, transform)
        return ndimage.distance_transform_edt(~river_raster) * transform[0]
    
    def _calculate_elevation_flood_risk(self, dem_data: np.ndarray, sea_level_rise: float, 
                                        valid_study_area: np.ndarray) -> np.ndarray:
        """
        Calculate selective flood risk based on elevation within study area context.
        
        Uses a more selective approach that concentrates high risk in truly vulnerable areas,
        avoiding too many maximum values and overly broad risk distribution.
        
        Args:
            dem_data: Digital elevation model data
            sea_level_rise: Sea level rise scenario in meters
            valid_study_area: Boolean mask defining the valid study area for normalization
            
        Returns:
            Selective flood risk with realistic distribution
        """
        # Get study area elevation statistics for normalization
        study_elevations = dem_data[valid_study_area]
        
        if len(study_elevations) == 0:
            logger.warning("No valid elevations in study area, returning zero risk")
            return np.zeros_like(dem_data, dtype=np.float32)
        
        # Calculate elevation range within study area
        min_study_elevation = np.min(study_elevations)
        max_study_elevation = np.max(study_elevations)
        elevation_range = max_study_elevation - min_study_elevation
        mean_study_elevation = np.mean(study_elevations)
        
        # Calculate critical thresholds
        max_safe_elevation = self.config.elevation_risk['max_safe_elevation_m']
        safe_threshold = max_safe_elevation + sea_level_rise
        
        # Log study area elevation statistics
        logger.info(f"Study area elevation range: {min_study_elevation:.2f}m to {max_study_elevation:.2f}m")
        logger.info(f"Study area mean elevation: {mean_study_elevation:.2f}m")
        logger.info(f"Sea level rise scenario: {sea_level_rise:.2f}m")
        logger.info(f"Safe elevation threshold: {safe_threshold:.2f}m")
        
        # Handle edge case where all elevations are the same
        if elevation_range == 0:
            logger.warning("All elevations in study area are identical, using uniform risk")
            uniform_risk = 0.3 if min_study_elevation <= safe_threshold else 0.05
            return np.full_like(dem_data, uniform_risk, dtype=np.float32)
        
        # Calculate vulnerability based on position relative to sea level rise
        elevation_above_slr = dem_data - sea_level_rise
        
        # Create base risk using more selective approach
        # Only areas within a reasonable vulnerability range get significant risk
        vulnerability_range = max(10.0, elevation_range * 0.3)  # Focus on bottom 30% of elevation range or 10m, whichever is larger
        
        # Calculate selective risk - concentrate high risk in truly vulnerable areas
        risk = np.zeros_like(dem_data, dtype=np.float32)
        
        # Areas below sea level rise - use exponential decay from surface
        below_slr_mask = elevation_above_slr <= 0
        if np.any(below_slr_mask):
            # Higher risk for areas further below sea level rise, but not all = 1.0
            depth_below_slr = np.abs(elevation_above_slr[below_slr_mask])
            # Use exponential function that starts high but doesn't saturate immediately
            risk[below_slr_mask] = 0.8 + 0.19 * (1 - np.exp(-depth_below_slr / 2.0))  # Max ~0.99, not 1.0
        
        # Areas above sea level rise but within vulnerability range
        vulnerable_mask = (elevation_above_slr > 0) & (elevation_above_slr <= vulnerability_range)
        if np.any(vulnerable_mask):
            # Exponential decay based on height above sea level rise
            height_above_slr = elevation_above_slr[vulnerable_mask]
            decay_factor = self.config.elevation_risk['risk_decay_factor']
            # Scale the risk to avoid too many high values
            risk[vulnerable_mask] = 0.6 * np.exp(-height_above_slr / decay_factor)
        
        # Areas well above vulnerability range but below safe threshold - minimal risk
        moderate_mask = (elevation_above_slr > vulnerability_range) & (dem_data <= safe_threshold)
        if np.any(moderate_mask):
            risk[moderate_mask] = 0.05 + 0.1 * np.exp(-(elevation_above_slr[moderate_mask] - vulnerability_range) / 5.0)
        
        # Areas above safe threshold - very minimal risk
        safe_mask = dem_data > safe_threshold
        if np.any(safe_mask):
            risk[safe_mask] = 0.001 + 0.009 * np.exp(-(dem_data[safe_mask] - safe_threshold) / 10.0)
        
        # Apply study area context adjustment
        # Adjust risk based on relative position within study area
        study_percentile = np.zeros_like(dem_data, dtype=np.float32)
        study_percentile[valid_study_area] = (
            (dem_data[valid_study_area] - min_study_elevation) / elevation_range
        )
        
        # Lower elevations within study area get slight risk boost
        # Higher elevations get slight risk reduction
        context_adjustment = 1.0 + 0.2 * (1.0 - study_percentile) - 0.1 * study_percentile
        context_adjustment = np.clip(context_adjustment, 0.5, 1.5)
        
        # Apply context adjustment
        adjusted_risk = risk * context_adjustment
        
        # Ensure realistic value distribution - avoid too many high values
        final_risk = np.clip(adjusted_risk, 0.001, 0.95)  
        
        # Log final risk statistics
        final_valid_risks = final_risk[valid_study_area]
        if len(final_valid_risks) > 0:
            logger.info(f"Risk calculation statistics:")
            logger.info(f"  Range: {np.min(final_valid_risks):.4f} to {np.max(final_valid_risks):.4f}")
            logger.info(f"  Mean: {np.mean(final_valid_risks):.4f}")
            logger.info(f"  Median: {np.median(final_valid_risks):.4f}")
            
            # Count risk distribution
            very_high_count = np.sum(final_valid_risks > 0.8)
            high_risk_count = np.sum((final_valid_risks > 0.6) & (final_valid_risks <= 0.8))
            moderate_risk_count = np.sum((final_valid_risks > 0.3) & (final_valid_risks <= 0.6))
            low_risk_count = np.sum((final_valid_risks > 0.1) & (final_valid_risks <= 0.3))
            minimal_risk_count = np.sum(final_valid_risks <= 0.1)
            
            total_pixels = len(final_valid_risks)
            logger.info(f"Risk distribution:")
            logger.info(f"  Very High (>0.8): {very_high_count/total_pixels*100:.1f}% ({very_high_count} pixels)")
            logger.info(f"  High (0.6-0.8): {high_risk_count/total_pixels*100:.1f}% ({high_risk_count} pixels)")
            logger.info(f"  Moderate (0.3-0.6): {moderate_risk_count/total_pixels*100:.1f}% ({moderate_risk_count} pixels)")
            logger.info(f"  Low (0.1-0.3): {low_risk_count/total_pixels*100:.1f}% ({low_risk_count} pixels)")
            logger.info(f"  Minimal (≤0.1): {minimal_risk_count/total_pixels*100:.1f}% ({minimal_risk_count} pixels)")
            
            # Calculate total significant risk area (>0.3)
            significant_risk_count = very_high_count + high_risk_count + moderate_risk_count
            logger.info(f"  Total significant risk (>0.3): {significant_risk_count/total_pixels*100:.1f}%")
        
        return final_risk.astype(np.float32)
    
    def _calculate_river_risk_enhancement(self, shape: Tuple[int, int], transform: rasterio.Affine) -> np.ndarray:
        """
        Calculate flood risk enhancement based on distance to rivers using configurable zones.
        
        Args:
            shape: Shape of the raster grid
            transform: Affine transform matrix
            
        Returns:
            Risk enhancement multiplier (1.0 = no enhancement, >1.0 = increased risk)
        """
        try:
            if self.river_network is None:
                self.load_river_data()
            
            if self.river_network is None:
                logger.warning("No river network available, skipping river risk enhancement")
                return np.ones(shape, dtype=np.float32)
            
            # Create raster representation of rivers
            river_raster = self._rasterize_river_network(shape, transform)
            
            # Calculate distance to nearest river in meters
            river_distance_pixels = ndimage.distance_transform_edt(~river_raster)
            pixel_size = abs(transform[0])  # Pixel size in meters
            river_distance_meters = river_distance_pixels * pixel_size
            
            # Initialize enhancement array with base value (no enhancement)
            enhancement = np.ones(shape, dtype=np.float32)
            
            # Apply zone-based enhancements from config
            zones = self.config.river_zones
            
            # High risk zone (closest to rivers)
            high_risk_mask = river_distance_meters <= zones['high_risk_distance_m']
            enhancement[high_risk_mask] = zones['high_risk_weight']
            
            # Moderate risk zone
            moderate_risk_mask = (river_distance_meters > zones['high_risk_distance_m']) & \
                               (river_distance_meters <= zones['moderate_risk_distance_m'])
            enhancement[moderate_risk_mask] = zones['moderate_risk_weight']
            
            # Low risk zone (furthest from rivers but still influenced)
            low_risk_mask = (river_distance_meters > zones['moderate_risk_distance_m']) & \
                           (river_distance_meters <= zones['low_risk_distance_m'])
            enhancement[low_risk_mask] = zones['low_risk_weight']
            
            logger.info(f"Applied river risk enhancement: {np.sum(high_risk_mask)} high risk, "
                       f"{np.sum(moderate_risk_mask)} moderate risk, {np.sum(low_risk_mask)} low risk pixels")
            
            return enhancement
            
        except Exception as e:
            logger.warning(f"Could not calculate river risk enhancement: {str(e)}")
            return np.ones(shape, dtype=np.float32)
    
    def _combine_flood_risks(self, elevation_risk: np.ndarray, river_enhancement: np.ndarray, 
                           valid_study_area: np.ndarray) -> np.ndarray:
        """
        Combine elevation-based flood risk with river proximity enhancement using unified normalization.
        
        Args:
            elevation_risk: Base flood risk from elevation (normalized within study area)
            river_enhancement: Risk enhancement multiplier from rivers (≥1.0)
            valid_study_area: Mask for valid areas to consider
            
        Returns:
            Combined flood risk with preserved gradients and unified normalization
        """
        # Apply river enhancement to elevation risk
        enhanced_risk = elevation_risk * river_enhancement
        
        # Get valid enhanced risk values for normalization
        valid_enhanced_risk = enhanced_risk[valid_study_area]
        
        if len(valid_enhanced_risk) == 0:
            logger.warning("No valid enhanced risk values, returning original elevation risk")
            return elevation_risk * valid_study_area
        
        # Calculate statistics for enhanced risk
        mean_enhanced_risk = np.mean(valid_enhanced_risk)
        max_enhanced_risk = np.max(valid_enhanced_risk)
        percentile_99 = np.percentile(valid_enhanced_risk, 99)
        
        logger.info(f"Enhanced risk statistics - Mean: {mean_enhanced_risk:.4f}, Max: {max_enhanced_risk:.4f}, "
                   f"99th percentile: {percentile_99:.4f}")
        
        # Apply soft normalization to preserve gradients while keeping values reasonable
        if percentile_99 > 1.0:
            # Use 99th percentile instead of max to avoid outliers dominating normalization
            normalization_factor = 1.0 / percentile_99
            enhanced_risk = enhanced_risk * normalization_factor
            logger.info(f"Applied soft normalization using 99th percentile factor: {normalization_factor:.3f}")
        
        # Ensure only valid study areas have risk values
        combined_risk = enhanced_risk * valid_study_area
        
        # Apply very soft upper bound to prevent extreme outliers while preserving gradients
        # This replaces the hard np.clip(0, 1) with a more nuanced approach
        max_reasonable_risk = 1.2  # Allow some values above 1.0 for better gradient preservation
        combined_risk = np.where(
            combined_risk > max_reasonable_risk,
            max_reasonable_risk * (1 - np.exp(-(combined_risk - max_reasonable_risk) / 0.3)),
            combined_risk
        )
        
        # Final statistics
        final_valid_risk = combined_risk[valid_study_area]
        if len(final_valid_risk) > 0:
            logger.info(f"Final combined risk - Mean: {np.mean(final_valid_risk):.4f}, "
                       f"Max: {np.max(final_valid_risk):.4f}, Min: {np.min(final_valid_risk):.4f}")
            
            # Risk distribution after combination
            high_risk_pct = np.sum(final_valid_risk > 0.7) / len(final_valid_risk) * 100
            moderate_risk_pct = np.sum((final_valid_risk > 0.3) & (final_valid_risk <= 0.7)) / len(final_valid_risk) * 100
            low_risk_pct = np.sum((final_valid_risk > 0.1) & (final_valid_risk <= 0.3)) / len(final_valid_risk) * 100
            
            logger.info(f"Combined risk distribution - High (>0.7): {high_risk_pct:.1f}%, "
                       f"Moderate (0.3-0.7): {moderate_risk_pct:.1f}%, Low (0.1-0.3): {low_risk_pct:.1f}%")
        
        return combined_risk
    
    def _apply_final_normalization(self, risk_data: np.ndarray, valid_study_area: np.ndarray) -> np.ndarray:
        """
        Apply conservative final normalization to preserve realistic risk distributions.
        
        This method applies minimal normalization to preserve the selective risk calculation
        while ensuring interpretable values and targeting ~40% significant risk coverage.
        
        Args:
            risk_data: Risk data after smoothing
            valid_study_area: Boolean mask for valid study area
            
        Returns:
            Final normalized risk data with realistic distribution
        """
        # Apply study area mask first
        masked_risk = risk_data * valid_study_area
        
        # Get valid risk values for normalization
        valid_risk_values = masked_risk[valid_study_area]
        
        if len(valid_risk_values) == 0:
            logger.warning("No valid risk values for final normalization")
            return masked_risk.astype(np.float32)
        
        # Calculate current distribution statistics
        risk_mean = np.mean(valid_risk_values)
        risk_median = np.median(valid_risk_values)
        risk_std = np.std(valid_risk_values)
        risk_min = np.min(valid_risk_values)
        risk_max = np.max(valid_risk_values) 
        risk_95th = np.percentile(valid_risk_values, 95)
        risk_99th = np.percentile(valid_risk_values, 99)
        
        # Calculate current significant risk coverage
        current_significant_risk_pct = np.sum(valid_risk_values > 0.3) / len(valid_risk_values) * 100
        
        logger.info(f"Pre-normalization statistics:")
        logger.info(f"  Mean: {risk_mean:.4f}, Median: {risk_median:.4f}, Std: {risk_std:.4f}")
        logger.info(f"  Range: {risk_min:.4f} to {risk_max:.4f}")
        logger.info(f"  95th percentile: {risk_95th:.4f}, 99th percentile: {risk_99th:.4f}")
        logger.info(f"  Current significant risk coverage (>0.3): {current_significant_risk_pct:.1f}%")
        
        # Apply minimal normalization - preserve the careful risk calculation
        normalized_risk = masked_risk.copy()
        
        # Only apply normalization if values exceed reasonable bounds
        if risk_max > 1.0:
            # Use conservative normalization to preserve risk structure
            # Target keeping 99th percentile around 0.9-0.95
            if risk_99th > 0.95:
                normalization_factor = 0.90 / risk_99th  # More conservative
                normalized_risk = masked_risk * normalization_factor
                logger.info(f"Applied conservative normalization with factor: {normalization_factor:.3f}")
            else:
                logger.info("Risk values within acceptable range, minimal adjustment applied")
                # Just ensure no values exceed 1.0
                normalized_risk = np.minimum(masked_risk, 1.0)
        else:
            logger.info("Risk values already in optimal range, no normalization needed")
        
        # Apply very gentle smoothing of extreme outliers only
        # This prevents a few extreme values from dominating while preserving most of the distribution
        reasonable_max = 0.98  # Slightly below 1.0
        outlier_mask = normalized_risk > reasonable_max
        if np.any(outlier_mask):
            # Apply very gentle saturation only to extreme outliers
            normalized_risk[outlier_mask] = reasonable_max + 0.02 * np.tanh(
                (normalized_risk[outlier_mask] - reasonable_max) / 0.1
            )
            outlier_count = np.sum(outlier_mask & valid_study_area)
            logger.info(f"Applied gentle saturation to {outlier_count} extreme outlier pixels")
        
        # Ensure meaningful minimum values (avoid too many zeros)
        min_meaningful_risk = 0.001
        normalized_risk = np.where(
            valid_study_area,
            np.maximum(normalized_risk, min_meaningful_risk),
            normalized_risk
        )
        
        # Final distribution statistics
        final_valid_values = normalized_risk[valid_study_area]
        final_mean = np.mean(final_valid_values)
        final_median = np.median(final_valid_values)
        final_max = np.max(final_valid_values)
        final_min = np.min(final_valid_values)
        final_95th = np.percentile(final_valid_values, 95)
        
        # Calculate final risk distribution
        very_high_count = np.sum(final_valid_values > 0.8)
        high_risk_count = np.sum((final_valid_values > 0.6) & (final_valid_values <= 0.8))
        moderate_risk_count = np.sum((final_valid_values > 0.3) & (final_valid_values <= 0.6))
        low_risk_count = np.sum((final_valid_values > 0.1) & (final_valid_values <= 0.3))
        minimal_risk_count = np.sum(final_valid_values <= 0.1)
        
        total_count = len(final_valid_values)
        significant_risk_count = very_high_count + high_risk_count + moderate_risk_count
        final_significant_risk_pct = significant_risk_count / total_count * 100
        
        logger.info(f"Post-normalization statistics:")
        logger.info(f"  Mean: {final_mean:.4f}, Median: {final_median:.4f}")
        logger.info(f"  Range: {final_min:.4f} to {final_max:.4f}, 95th percentile: {final_95th:.4f}")
        
        logger.info(f"Final risk distribution:")
        logger.info(f"  Very High (>0.8): {very_high_count/total_count*100:.1f}% ({very_high_count} pixels)")
        logger.info(f"  High (0.6-0.8): {high_risk_count/total_count*100:.1f}% ({high_risk_count} pixels)")
        logger.info(f"  Moderate (0.3-0.6): {moderate_risk_count/total_count*100:.1f}% ({moderate_risk_count} pixels)")
        logger.info(f"  Low (0.1-0.3): {low_risk_count/total_count*100:.1f}% ({low_risk_count} pixels)")
        logger.info(f"  Minimal (≤0.1): {minimal_risk_count/total_count*100:.1f}% ({minimal_risk_count} pixels)")
        logger.info(f"  **Total significant risk (>0.3): {final_significant_risk_pct:.1f}%**")
        
        # Provide guidance on risk distribution
        if final_significant_risk_pct > 50:
            logger.warning(f"Significant risk coverage ({final_significant_risk_pct:.1f}%) is higher than expected (~40%). "
                          "Consider adjusting vulnerability_range or risk thresholds.")
        elif final_significant_risk_pct < 30:
            logger.warning(f"Significant risk coverage ({final_significant_risk_pct:.1f}%) is lower than expected (~40%). "
                          "Consider increasing vulnerability sensitivity.")
        else:
            logger.info(f"Significant risk coverage ({final_significant_risk_pct:.1f}%) is within expected range (30-50%).")
        
        return normalized_risk.astype(np.float32)
    
    def process_scenarios(self, custom_scenarios: Optional[List[SeaLevelScenario]] = None) -> Dict[str, np.ndarray]:
        """
        Process all sea level rise scenarios and generate flood extent maps.
        Args:
            custom_scenarios: Optional custom scenarios, uses defaults if None
        Returns:
            Dictionary mapping scenario names to flood extent arrays
        """
        scenarios = custom_scenarios or self.scenarios
        logger.info(f"Processing {len(scenarios)} sea level rise scenarios...")
        # Load DEM data and land mask once
        dem_data, transform, crs, land_mask = self.load_and_prepare_dem()
        flood_extents = {}
        for scenario in scenarios:
            logger.info(f"Processing scenario: {scenario.name} ({scenario.rise_meters}m)")
            flood_risk = self.calculate_flood_extent(dem_data, scenario.rise_meters, transform, land_mask)
            flood_extents[scenario.name] = {
                'flood_risk': flood_risk, 
                'scenario': scenario,
                'transform': transform,
                'crs': crs,
                'dem_data': dem_data
            }
        logger.info("Completed processing all scenarios")
        return flood_extents
    
    def visualize_hazard_assessment(self, flood_extents: Dict[str, np.ndarray], 
                                      save_plots: bool = True) -> None:
        """
        Create comprehensive visualization of hazard assessment results.
        
        Args:
            flood_extents: Dictionary of flood extent data for each scenario
            save_plots: Whether to save visualization to file
        """
        # Set up the plotting parameters
        plt.style.use('default')
        
        # Create figure with proper grid layout
        fig = plt.figure(figsize=(20, 15))
        gs = plt.GridSpec(3, 3, figure=fig, height_ratios=[1, 1, 0.8], width_ratios=[1, 1, 1])
        
        # Get scenario names from flood extents
        scenarios = list(flood_extents.keys())
        
        # Get DEM bounds for consistent visualization extent
        first_scenario = list(flood_extents.values())[0]
        dem_bounds = [
            first_scenario['transform'].xoff,
            first_scenario['transform'].xoff + first_scenario['transform'].a * first_scenario['dem_data'].shape[1],
            first_scenario['transform'].yoff + first_scenario['transform'].e * first_scenario['dem_data'].shape[0],
            first_scenario['transform'].yoff
        ]
        
        crs = first_scenario['crs']
        
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
            logger.info("No NUTS boundaries available, using DEM bounds for visualization extent")
        
        # Clip river network to visualization extent for performance
        if self.river_network is not None:
            # Get NUTS-L0 bounds for clipping
            river_bounds = self.river_network.total_bounds
            logger.info(f"River network bounds after clipping: {river_bounds}")
        
        # Get reference DEM data and transform for land mass alignment
        reference_flood_data = list(flood_extents.values())[0]
        reference_dem_data = reference_flood_data['dem_data']
        reference_transform = reference_flood_data['transform']
        
        # Transform land mass data once outside the loop (optimization)
        land_mass_data, land_transform, _ = self.transformer.transform_raster(
            self.config.land_mass_path,
            reference_bounds=None,
            resampling_method=self.config.resampling_method.name.lower() if hasattr(self.config.resampling_method, 'name') else str(self.config.resampling_method).lower()
        )
        if not self.transformer.validate_alignment(land_mass_data, land_transform, reference_dem_data, reference_transform):
            land_mask_aligned = self.transformer.ensure_alignment(
                land_mass_data, land_transform, reference_transform, reference_dem_data.shape,
                self.config.resampling_method.name.lower() if hasattr(self.config.resampling_method, 'name') else str(self.config.resampling_method).lower()
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
                dtype=np.uint8
            )
            # Get elevation data within NUTS and land areas only
            nuts_land_mask = (nuts_mask == 1) & (land_mask == 1) & (~np.isnan(reference_dem_data))
            if np.any(nuts_land_mask):
                nuts_elevations = reference_dem_data[nuts_land_mask]
                elevation_min = np.percentile(nuts_elevations, 2) - 30 # Use 2nd percentile to avoid outliers and add 30m buffer to ensure that only water is blue
                elevation_max = np.percentile(nuts_elevations, 98) + 100 # Use 98th percentile to avoid outliers and add 100m buffer to ensure that the entire landscape is visible (not all white)
                logger.info(f"Dynamic elevation range for NUTS region: {elevation_min:.1f}m to {elevation_max:.1f}m")
            else:
                # Fallback to global range if no valid data
                valid_elevations = reference_dem_data[~np.isnan(reference_dem_data)]
                elevation_min = np.percentile(valid_elevations, 2) - 30 # Use 2nd percentile to avoid outliers and add 30m buffer to ensure that only water is blue
                elevation_max = np.percentile(valid_elevations, 98) + 100 # Use 98th percentile to avoid outliers and add 100m buffer to ensure that the entire landscape is visible (not all white)
                logger.info(f"Fallback elevation range: {elevation_min:.1f}m to {elevation_max:.1f}m")
        else:
            # Fallback to global range if no NUTS data
            valid_elevations = reference_dem_data[~np.isnan(reference_dem_data)]
            elevation_min = np.percentile(valid_elevations, 2) - 30 # Use 2nd percentile to avoid outliers and add 30m buffer to ensure that only water is blue
            elevation_max = np.percentile(valid_elevations, 98) + 100 # Use 98th percentile to avoid outliers and add 100m buffer to ensure that the entire landscape is visible (not all white)
            logger.info(f"Global elevation range: {elevation_min:.1f}m to {elevation_max:.1f}m")
        
        # Panel 1: Overview/composite map with NUTS overlay and rivers
        ax = fig.add_subplot(gs[0, 0])
        
        # Use reference DEM for the overview
        dem_data = reference_dem_data
        transform = reference_transform
        
        logger.info(f"DEM extent (target CRS): left={nuts_bounds[0]}, right={nuts_bounds[2]}, bottom={nuts_bounds[1]}, top={nuts_bounds[3]}")
        
        # Create masked elevation data for proper visualization
        # Create a copy of DEM data for visualization
        dem_for_vis = dem_data.copy()
        
        # Set water areas (where land_mask == 0) to a specific value for proper visualization
        water_elevation = elevation_min - 10  # Set water to below minimum land elevation
        dem_for_vis[land_mask == 0] = water_elevation
        
        # Create a base elevation visualization with proper water/land distinction
        im1 = ax.imshow(dem_for_vis, cmap='terrain', aspect='equal', 
                       extent=dem_bounds, vmin=water_elevation, vmax=elevation_max, alpha=0.8)
        
        # River network overlay
        if self.river_network is not None:
            logger.info(f"River network bounds: {self.river_network.total_bounds}")
            self.river_network.plot(ax=ax, color='darkblue', linewidth=0.5, alpha=0.9, zorder=10)
        
        # NUTS overlay
        if nuts_gdf is not None:
            logger.info(f"NUTS bounds: {nuts_gdf.total_bounds}")
            nuts_gdf.plot(ax=ax, facecolor='none', edgecolor='black', linewidth=1.0, alpha=1.0, zorder=11)
        
        ax.autoscale(False)
        
        ax.set_title('Study Area Overview\nElevation with River Network and Administrative Boundaries', 
                    fontsize=12, fontweight='bold')
        ax.set_xlabel('X Coordinate (m)')
        ax.set_ylabel('Y Coordinate (m)')
        
        # Add colorbar for elevation with proper range
        cbar1 = plt.colorbar(im1, ax=ax, shrink=0.8)
        cbar1.set_label('Elevation (m)', rotation=270, labelpad=15)
        
        # Panels 2-5: Normalized flood risk for each scenario with rivers
        for i, scenario_name in enumerate(scenarios):
            if i >= 4:  # Only show first 4 scenarios
                break
                
            ax = fig.add_subplot(gs[0, i+1]) if i < 2 else fig.add_subplot(gs[1, i-2])
            flood_data = flood_extents[scenario_name]
            flood_risk = flood_data['flood_risk']  # Use normalized risk values
            scenario = flood_data['scenario']
            dem_data = flood_data['dem_data']
            transform = flood_data['transform']
            
            # Always rasterize NUTS to DEM grid
            nuts_mask = rasterio.features.rasterize(
                [(geom, 1) for geom in nuts_gdf.geometry],
                out_shape=dem_data.shape,
                transform=transform,
                dtype=np.uint8
            )

            # Create visualization showing normalized flood risk with proper background zones
            valid_study_area = (land_mask == 1) & (nuts_mask == 1) & (~np.isnan(dem_data))
            
            # Create composite visualization array
            # Start with a base array for all zones
            composite_display = np.zeros_like(dem_data, dtype=np.uint8)
            
            # Define zone values
            WATER_VALUE = 0      # Existing water bodies (blue)
            OUTSIDE_NL_VALUE = 1 # Land outside Netherlands (gray)  
            LAND_BASE_VALUE = 2  # Base value for Netherlands land
            
            # Set base zones
            composite_display[land_mask == 0] = WATER_VALUE  # Water areas from land mass file
            composite_display[(land_mask == 1) & (nuts_mask == 0)] = OUTSIDE_NL_VALUE  # Outside Netherlands
            composite_display[valid_study_area] = LAND_BASE_VALUE  # Netherlands land areas
            
            # Create risk overlay only for valid study areas
            risk_overlay = np.full_like(dem_data, np.nan, dtype=np.float32)
            risk_overlay[valid_study_area] = flood_risk[valid_study_area]
            
            # Display base zones first
            from matplotlib.colors import ListedColormap, LinearSegmentedColormap
            base_colors = ['#1f78b4', '#bdbdbd', '#ffffff']  # Blue (water), Gray (outside NL), White (NL land base)
            base_cmap = ListedColormap(base_colors)
            
            # Show base zones
            ax.imshow(composite_display, cmap=base_cmap, aspect='equal', extent=dem_bounds, 
                     vmin=0, vmax=2, alpha=1.0)
            
            # Create flood risk colormap (warm colors for risk)
            risk_colors = ['#ffffcc', '#feb24c', '#fd8d3c', '#fc4e2a', '#e31a1c', '#b10026']
            risk_cmap = LinearSegmentedColormap.from_list('flood_risk', risk_colors, N=256)
            
            # Overlay flood risk only on Netherlands land areas
            im = ax.imshow(risk_overlay, cmap=risk_cmap, aspect='equal', extent=dem_bounds, 
                          vmin=0, vmax=1, alpha=0.85)
            
            # NUTS overlay
            if nuts_gdf is not None:
                nuts_gdf.plot(ax=ax, facecolor='none', edgecolor='black', linewidth=0.5, alpha=1.0, zorder=10)
            
            # River network overlay
            if self.river_network is not None:
                self.river_network.plot(ax=ax, color='darkblue', linewidth=0.3, alpha=1.0, zorder=11)
                
            ax.set_title(f'{scenario.name} Scenario\n({scenario.rise_meters}m SLR) - Normalized Risk', 
                        fontsize=12, fontweight='bold')
            ax.set_xlabel('X Coordinate (m)')
            ax.set_ylabel('Y Coordinate (m)')
            ax.set_xlim(dem_bounds[0], dem_bounds[1])
            ax.set_ylim(dem_bounds[2], dem_bounds[3])
            ax.autoscale(False)
            
            # Add colorbar for flood risk
            cbar = plt.colorbar(im, ax=ax, shrink=0.8)
            cbar.set_label('Flood Risk (0=safe, 1=maximum)', rotation=270, labelpad=15)
            
            # Add legend for zones and risk levels
            import matplotlib.patches as mpatches
            legend_patches = [
                mpatches.Patch(color='#1f78b4', label='Existing Water Bodies'),
                mpatches.Patch(color='#bdbdbd', label='Outside Netherlands'),
                mpatches.Patch(color='#ffffcc', label='Low Flood Risk (0-0.3)'),
                mpatches.Patch(color='#fd8d3c', label='Moderate Risk (0.3-0.7)'),
                mpatches.Patch(color='#e31a1c', label='High Risk (0.7-1.0)')
            ]
            ax.legend(handles=legend_patches, loc='lower left', fontsize=8, frameon=True)

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
            flood_risk = flood_data['flood_risk']
            dem_data = flood_data['dem_data']
            
            # Calculate area with significant flood risk (>0.3)
            high_risk_area_km2 = np.sum(flood_risk > 0.3) * (30 * 30) / 1_000_000
            flood_areas.append(high_risk_area_km2)
            scenario_names.append(flood_data['scenario'].name)
            rise_values.append(flood_data['scenario'].rise_meters)
        
        colors = ['#2e8b57', '#ff8c00', '#dc143c', '#8a2be2'][:len(scenarios)]  # SeaGreen, DarkOrange, Crimson, BlueViolet
        bars = ax5.bar(scenario_names, flood_areas, color=colors, alpha=0.7)
        ax5.set_title('High Flood Risk Area by Scenario\n(Risk > 0.3)', fontsize=12, fontweight='bold')
        ax5.set_ylabel('High Risk Area (km²)')
        ax5.set_xlabel('Sea Level Rise Scenario')
        
        # Add value labels on bars
        for bar, area in zip(bars, flood_areas):
            height = bar.get_height()
            ax5.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                    f'{area:.1f} km²', ha='center', va='bottom', fontweight='bold')
        
        # Panel 6: River network with elevation profile
        ax6 = fig.add_subplot(gs[2, :])
        if self.river_network is not None:
            # Plot elevation histogram using dynamic range
            if nuts_gdf is not None and np.any(nuts_land_mask):
                valid_elevations = nuts_elevations
                hist_range = (elevation_min, elevation_max)
                range_label = "NUTS Region"
            else:
                valid_elevations = reference_dem_data[~np.isnan(reference_dem_data)]
                hist_range = (elevation_min, elevation_max)
                range_label = "Study Area"
                
            ax6.hist(valid_elevations, bins=100, range=hist_range, alpha=0.7, 
                    color='skyblue', edgecolor='black', zorder=1)
            
            # Add vertical lines for each scenario
            colors = ['green', 'orange', 'red', 'purple']
            for i, scenario_name in enumerate(scenarios):
                scenario = flood_extents[scenario_name]['scenario']
                ax6.axvline(scenario.rise_meters, color=colors[i], linestyle='--', 
                           linewidth=2, label=f'{scenario.name} ({scenario.rise_meters}m)', zorder=2)
            
            # Add statistics
            stats_text = f"Elevation Statistics ({range_label}):\n"
            stats_text += f"Min: {elevation_min:.1f}m\n"
            stats_text += f"Max: {elevation_max:.1f}m\n"
            stats_text += f"Mean: {np.mean(valid_elevations):.1f}m\n"
            if self.river_network is not None:
                stats_text += f"\nRiver Network:\n"
                stats_text += f"Segments: {len(self.river_network)}\n"
                stats_text += f"Nodes: {len(self.river_nodes)}"
            
            ax6.text(0.98, 0.98, stats_text, transform=ax6.transAxes,
                    verticalalignment='top', horizontalalignment='right',
                    bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))
            
        ax6.set_xlabel('Elevation (m)')
        ax6.set_ylabel('Frequency')
        ax6.set_title(f'Elevation Distribution with Sea Level Rise Thresholds\n' +
                     f'(Range: {elevation_min:.1f}m to {elevation_max:.1f}m)', fontsize=12, fontweight='bold')
        ax6.legend()
        ax6.grid(True, alpha=0.3)
        ax6.set_xlim(elevation_min - (elevation_max - elevation_min) * 0.1, 
                     elevation_max + (elevation_max - elevation_min) * 0.1)
        
        # Add main title
        fig.suptitle('EU Climate Risk Assessment - Enhanced Hazard Layer Analysis\n' + 
                    'Normalized Flood Risk with River Zone Enhancement and Elevation Profiles', 
                    fontsize=16, fontweight='bold', y=0.98)
        
        if save_plots:
            output_path = self.config.output_dir /"hazard"/"hazard_layer_assessment.png"
            plt.savefig(output_path, dpi=self.config.dpi, bbox_inches='tight')
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
                "NUTS-L0-NL.shp"   # Countries
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
            
            logger.warning("No NUTS boundary files found. Visualizations will not include administrative boundaries.")
            return None
            
        except Exception as e:
            logger.warning(f"Could not load NUTS boundaries: {str(e)}")
            return None
    
    def _add_nuts_overlay(self, ax, nuts_gdf: gpd.GeoDataFrame, target_crs: rasterio.crs.CRS) -> None:
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
                logger.info(f"Reprojected NUTS boundaries from {nuts_gdf.crs} to {config_target_crs}")
            else:
                nuts_reproj = nuts_gdf
            
            # Add the boundaries as overlay
            nuts_reproj.plot(
                ax=ax,
                facecolor='cyan',      # Green fill
                alpha=0.1,              # 20% transparency
                edgecolor='black',  # Bold dark green outlines
                linewidth=2,            # Bold outline width
                zorder=10               # Ensure it's on top of the raster data
            )
            
            logger.debug(f"Added NUTS overlay with {len(nuts_reproj)} administrative units")
            
        except Exception as e:
            logger.warning(f"Could not add NUTS overlay: {str(e)}")
            return
    
    def create_png_visualizations(self, flood_extents: Dict[str, np.ndarray]) -> None:
        """Create PNG visualizations for each hazard scenario using unified styling."""
        logger.info("Creating PNG visualizations for hazard scenarios...")
        
        # Get reference data for land mask calculation
        reference_flood_data = list(flood_extents.values())[0]
        reference_dem_data = reference_flood_data['dem_data']
        reference_transform = reference_flood_data['transform']
        
        # Transform land mass data once for all scenarios
        land_mass_data, land_transform, _ = self.transformer.transform_raster(
            self.config.land_mass_path,
            reference_bounds=None,
            resampling_method=self.config.resampling_method.name.lower() if hasattr(self.config.resampling_method, 'name') else str(self.config.resampling_method).lower()
        )
        if not self.transformer.validate_alignment(land_mass_data, land_transform, reference_dem_data, reference_transform):
            land_mask_aligned = self.transformer.ensure_alignment(
                land_mass_data, land_transform, reference_transform, reference_dem_data.shape,
                self.config.resampling_method.name.lower() if hasattr(self.config.resampling_method, 'name') else str(self.config.resampling_method).lower()
            )
        else:
            land_mask_aligned = land_mass_data
        
        land_mask = (land_mask_aligned > 0).astype(np.uint8)
        
        for scenario_name, flood_data in flood_extents.items():
            flood_risk = flood_data['flood_risk']
            transform = flood_data['transform']
            crs = flood_data['crs']
            scenario = flood_data['scenario']
            dem_data = flood_data['dem_data']
            
            # Create metadata for visualization
            meta = {
                'crs': crs,
                'transform': transform,
                'height': flood_risk.shape[0],
                'width': flood_risk.shape[1],
                'dtype': 'float32'
            }
            
            # Create output path for normalized risk
            risk_png_path = self.config.output_dir / "hazard" / f"hazard_risk_{scenario_name.lower()}_scenario.png"
            
            # Use unified visualizer for normalized risk visualization
            self.visualizer.visualize_hazard_scenario(
                flood_mask=flood_risk,  # Pass normalized risk values
                dem_data=dem_data,
                meta=meta,
                scenario=scenario,
                output_path=risk_png_path,
                land_mask=land_mask,
            )
            

    def create_flood_risk_bar_charts(self, flood_extents: Dict[str, np.ndarray]) -> None:
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
            flood_risk = flood_data['flood_risk']
            dem_data = flood_data['dem_data']
            scenario = flood_data['scenario']
            
            # Calculate pixel area in km²
            pixel_area_km2 = (30 * 30) / 1_000_000
            
            # Calculate total study area from first scenario (should be same for all)
            if total_study_area_km2 is None:
                # Load NUTS boundaries to calculate study area
                nuts_gdf = self._load_nuts_boundaries()
                if nuts_gdf is not None:
                    # Get reference data for land mask calculation
                    reference_transform = flood_data['transform']
                    
                    # Transform land mass data
                    land_mass_data, land_transform, _ = self.transformer.transform_raster(
                        self.config.land_mass_path,
                        reference_bounds=None,
                        resampling_method=self.config.resampling_method.name.lower() if hasattr(self.config.resampling_method, 'name') else str(self.config.resampling_method).lower()
                    )
                    if not self.transformer.validate_alignment(land_mass_data, land_transform, dem_data, reference_transform):
                        land_mask_aligned = self.transformer.ensure_alignment(
                            land_mass_data, land_transform, reference_transform, dem_data.shape,
                            self.config.resampling_method.name.lower() if hasattr(self.config.resampling_method, 'name') else str(self.config.resampling_method).lower()
                        )
                    else:
                        land_mask_aligned = land_mass_data
                    
                    land_mask = (land_mask_aligned > 0).astype(np.uint8)
                    
                    # Rasterize NUTS to DEM grid
                    nuts_mask = rasterio.features.rasterize(
                        [(geom, 1) for geom in nuts_gdf.geometry],
                        out_shape=dem_data.shape,
                        transform=reference_transform,
                        dtype=np.uint8
                    )
                    
                    # Calculate valid study area
                    valid_study_area = (~np.isnan(dem_data)) & (nuts_mask == 1) & (land_mask == 1)
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
        scenario_colors = ['#2e8b57', '#ff8c00', '#dc143c', '#8a2be2'][:len(scenario_names)]  # SeaGreen, DarkOrange, Crimson, BlueViolet
        
        # Create absolute bar chart
        self._create_absolute_flood_risk_chart(scenario_names, flood_areas, scenario_colors)
        
        # Create relative stacked bar chart
        self._create_relative_flood_risk_chart(scenario_names, flood_areas, total_study_area_km2, scenario_colors)
        
        logger.info("Completed creation of standalone flood risk bar charts")
    
    def _create_absolute_flood_risk_chart(self, scenario_names: List[str], flood_areas: List[float], colors: List[str]) -> None:
        """
        Create standalone absolute flood risk bar chart.
        
        Args:
            scenario_names: List of scenario names
            flood_areas: List of high risk areas in km²
            colors: List of colors for consistent styling
        """
        plt.figure(figsize=(12, 8))
        
        bars = plt.bar(scenario_names, flood_areas, color=colors, alpha=0.8, edgecolor='black', linewidth=1)
        
        plt.title('High Flood Risk Area by Sea Level Rise Scenario\n(Risk > 0.3)', 
                 fontsize=16, fontweight='bold', pad=20)
        plt.ylabel('High Risk Area (km²)', fontsize=14, fontweight='bold')
        plt.xlabel('Sea Level Rise Scenario', fontsize=14, fontweight='bold')
        
        # Add value labels on bars
        for bar, area in zip(bars, flood_areas):
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                    f'{area:.1f} km²', ha='center', va='bottom', fontweight='bold', fontsize=12)
        
        # Add grid for better readability
        plt.grid(True, alpha=0.3, axis='y')
        plt.gca().set_axisbelow(True)
        
        # Improve styling
        plt.xticks(fontsize=12, fontweight='bold')
        plt.yticks(fontsize=12)
        plt.tight_layout()
        
        # Add subtitle with methodology
        plt.figtext(0.5, 0.02, 'Based on DEM analysis with river network enhancement and 30m resolution', 
                   ha='center', fontsize=10, style='italic')
        
        # Save the chart
        output_path = self.config.output_dir / "hazard" / "flood_risk_absolute_by_scenario.png"
        plt.savefig(output_path, dpi=self.config.dpi, bbox_inches='tight', facecolor='white')
        plt.close()
        
        logger.info(f"Saved absolute flood risk bar chart to: {output_path}")
    
    def _create_relative_flood_risk_chart(self, scenario_names: List[str], flood_areas: List[float], 
                                        total_area_km2: float, colors: List[str]) -> None:
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
        bar_width = 0.6
        x_positions = range(len(scenario_names))
        
        # Bottom bars (safe areas) - use light gray
        safe_bars = plt.bar(x_positions, safe_percentages, bar_width, 
                           label='Safe Areas (Risk ≤ 0.3)', color='lightgray', 
                           alpha=0.8, edgecolor='black', linewidth=1)
        
        # Top bars (risk areas) - use scenario colors
        risk_bars = plt.bar(x_positions, risk_percentages, bar_width, 
                           bottom=safe_percentages, label='High Risk Areas (Risk > 0.3)', 
                           color="#e30613", alpha=0.8, edgecolor='black', linewidth=1)
        
        plt.title('Relative Flood Risk Distribution by Sea Level Rise Scenario\n(Percentage of Total Study Area)', 
                 fontsize=16, fontweight='bold', pad=20)
        plt.ylabel('Percentage of Study Area (%)', fontsize=14, fontweight='bold')
        plt.xlabel('Sea Level Rise Scenario', fontsize=14, fontweight='bold')
        
        # Set x-axis labels
        plt.xticks(x_positions, scenario_names, fontsize=12, fontweight='bold')
        plt.yticks(fontsize=12)
        
        # Add percentage labels on risk areas
        for i, (risk_pct, area_km2) in enumerate(zip(risk_percentages, flood_areas)):
            if risk_pct > 2:  # Only show label if percentage is significant enough
                plt.text(i, safe_percentages[i] + risk_pct/2, 
                        f'{risk_pct:.1f}%\n({area_km2:.1f} km²)', 
                        ha='center', va='center', fontweight='bold', fontsize=10,
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
        
        # Add total area information on safe areas
        for i, safe_pct in enumerate(safe_percentages):
            if safe_pct > 10:  # Only show if there's enough space
                safe_area_km2 = total_area_km2 - flood_areas[i]
                plt.text(i, safe_pct/2, f'{safe_pct:.1f}%', 
                        ha='center', va='center', fontweight='bold', fontsize=10,
                        color='darkgray')
        
        # Add grid for better readability
        plt.grid(True, alpha=0.3, axis='y')
        plt.gca().set_axisbelow(True)
        
        # Add legend
        plt.legend(loc='upper right', fontsize=12, frameon=True, fancybox=True, shadow=True)
        
        # Set y-axis to 0-100%
        plt.ylim(0, 100)
        
        plt.tight_layout()
        
        # Add subtitle with total area information
        plt.figtext(0.5, 0.02, f'Total Study Area: {total_area_km2:.1f} km² (NUTS regions on land)', 
                   ha='center', fontsize=10, style='italic')
        
        # Save the chart
        output_path = self.config.output_dir / "hazard" / "flood_risk_relative_by_scenario.png"
        plt.savefig(output_path, dpi=self.config.dpi, bbox_inches='tight', facecolor='white')
        plt.close()
        
        logger.info(f"Saved relative flood risk stacked bar chart to: {output_path}")

    def export_results(self, flood_extents: Dict[str, np.ndarray]) -> None:
        """
        Export hazard assessment results to files for further analysis.
        
        Args:
            flood_extents: Dictionary of flood extent results
        """
        logger.info("Exporting hazard assessment results...")
        
        for scenario_name, flood_data in flood_extents.items():
            flood_risk = flood_data['flood_risk']
            transform = flood_data['transform']
            crs = flood_data['crs']
            scenario = flood_data['scenario']
            
            risk_output_path = self.config.output_dir / "hazard" / "tif" / f"flood_risk_{scenario_name.lower()}.tif"
            risk_output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with rasterio.open(
                risk_output_path,
                'w',
                driver='GTiff',
                height=flood_risk.shape[0],
                width=flood_risk.shape[1],
                count=1,
                dtype=np.float32,
                crs=crs,
                transform=transform,
                nodata=-9999.0,
                compress='lzw'
            ) as dst:
                dst.write(flood_risk, 1)
                dst.set_band_description(1, f"Normalized flood risk for {scenario.rise_meters}m SLR")
                dst.update_tags(
                    description='Normalized flood risk values (0=no risk, 1=maximum risk)',
                    scenario=scenario.name,
                    sea_level_rise_m=str(scenario.rise_meters),
                    method='elevation_profile_with_river_enhancement'
                )
            
            logger.info(f"Exported {scenario_name} normalized flood risk to: {risk_output_path}")
            
         
        
        # Export summary statistics
        summary_stats = []
        for scenario_name, flood_data in flood_extents.items():
            flood_risk = flood_data['flood_risk']
            dem_data = flood_data['dem_data']
            scenario = flood_data['scenario']
            
            # Calculate areas for different risk levels
            pixel_area_km2 = (30 * 30) / 1_000_000
            total_valid_area_km2 = np.sum(~np.isnan(dem_data)) * pixel_area_km2
            
            # Risk level statistics
            high_risk_area_km2 = np.sum(flood_risk > 0.7) * pixel_area_km2
            moderate_risk_area_km2 = np.sum((flood_risk > 0.3) & (flood_risk <= 0.7)) * pixel_area_km2
            low_risk_area_km2 = np.sum((flood_risk > 0.1) & (flood_risk <= 0.3)) * pixel_area_km2
            
            # Mean and maximum risk
            valid_risk = flood_risk[~np.isnan(dem_data)]
            mean_risk = np.mean(valid_risk) if len(valid_risk) > 0 else 0.0
            max_risk = np.max(valid_risk) if len(valid_risk) > 0 else 0.0
            
            summary_stats.append({
                'scenario': scenario_name,
                'sea_level_rise_m': scenario.rise_meters,
                'total_area_km2': total_valid_area_km2,
                'high_risk_area_km2': high_risk_area_km2,
                'moderate_risk_area_km2': moderate_risk_area_km2,
                'low_risk_area_km2': low_risk_area_km2,
                'high_risk_percentage': (high_risk_area_km2 / total_valid_area_km2) * 100,
                'moderate_risk_percentage': (moderate_risk_area_km2 / total_valid_area_km2) * 100,
                'low_risk_percentage': (low_risk_area_km2 / total_valid_area_km2) * 100,
                'mean_risk': mean_risk,
                'max_risk': max_risk,
                'description': scenario.description
            })
        
        # Save summary as CSV
        summary_df = pd.DataFrame(summary_stats)
        summary_path = self.config.output_dir / "hazard" / "hazard_assessment_summary.csv"
        summary_df.to_csv(summary_path, index=False)
        logger.info(f"Exported summary statistics to: {summary_path}")

        # Create PNG visualizations for all scenarios
        self.create_png_visualizations(flood_extents)
        
        # Create standalone flood risk bar charts
        self.create_flood_risk_bar_charts(flood_extents)



