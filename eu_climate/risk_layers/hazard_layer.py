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



# Set up logging for the hazard layer
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
        
        # Initialize river network attributes
        self.river_network = None
        self.river_nodes = None
        
        # Initialize raster transformer
        self.transformer = RasterTransformer(
            target_crs=self.config.target_crs,
            target_resolution=30.0,  # 30m resolution
            config=self.config
        )
        
        # Initialize visualizer for unified styling
        self.visualizer = LayerVisualizer(self.config)
        
        # Validate files exist
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
        Calculate flood extent based on DEM, river network, sea level rise scenario, and land mass mask.
        Args:
            dem_data: Digital elevation model data array
            sea_level_rise: Sea level rise in meters
            transform: Affine transform matrix for the DEM data
            land_mask: Binary land mask (1=land, 0=water)
        Returns:
            Binary array where 1 indicates flooded areas, 0 indicates safe areas
        """
        logger.info(f"Calculating flood extent for {sea_level_rise}m sea level rise...")
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
        # Combine masks to get valid study area (now includes land mask)
        valid_study_area = (valid_land_mask & (nuts_mask == 1) & (land_mask == 1))
        
        # Basic flood model: areas below sea level rise are considered flooded
        # Only consider areas within valid study area
        flood_mask = (dem_data <= sea_level_rise) & valid_study_area
        
        try:
            if self.river_network is None:
                self.load_river_data()
                
            # Create a raster representation of the river network
            river_raster = self._rasterize_river_network(dem_data.shape, transform)
            
            # Enhance flood risk near rivers based on elevation and distance
            river_buffer = ndimage.distance_transform_edt(~river_raster)
            river_influence = np.exp(-river_buffer / 1000)  # Decay factor for river influence
            
            # Calculate elevation-based flood risk
            elevation_risk = np.clip((sea_level_rise - dem_data) / sea_level_rise, 0, 1)
            
            # Combine flood risks, but only within valid study area
            combined_risk = np.maximum(
                flood_mask,
                ((elevation_risk * river_influence) > 0.5) & valid_study_area
            )
            
        except Exception as e:
            logger.warning(f"Could not process river data: {str(e)}")
            logger.warning("Proceeding with basic flood model without river influence")
            combined_risk = flood_mask
        
        # Apply morphological operations to create more realistic flood extent
        # First smooth the data
        smoothed_risk = ndimage.gaussian_filter(
            np.nan_to_num(combined_risk, nan=0),
            sigma=self.config.smoothing_sigma
        )
        
        # Then apply binary operations
        binary_risk = smoothed_risk > 0.5
        binary_risk = ndimage.binary_closing(binary_risk)
        binary_risk = ndimage.binary_fill_holes(binary_risk)
        
        # Ensure we only consider areas within valid study area
        binary_risk = binary_risk & valid_study_area
        
        # Calculate statistics using actual pixel areas from transform
        # Calculate actual pixel area in square meters
        # In EPSG:3035, the pixel size varies with latitude
        # We use the average of the top and bottom pixel heights
        pixel_width = abs(transform[0])  # Width of a pixel in meters
        pixel_height_top = abs(transform[4])  # Height of a pixel at the top
        pixel_height_bottom = abs(transform[4] + transform[5] * dem_data.shape[0])  # Height at the bottom
        pixel_height_avg = (pixel_height_top + pixel_height_bottom) / 2
        pixel_area_m2 = pixel_width * pixel_height_avg
        
        # Calculate areas only for valid study area
        flooded_pixels = np.int64(np.sum(binary_risk))
        valid_pixels = np.int64(np.sum(valid_study_area))
        
        flooded_area_km2 = (flooded_pixels * pixel_area_m2) / 1_000_000.0
        total_area_km2 = (valid_pixels * pixel_area_m2) / 1_000_000.0
        flood_percentage = (flooded_area_km2 / total_area_km2) * 100.0 if total_area_km2 > 0 else 0.0
        
        logger.info(f"  Total study area: {total_area_km2:.2f} km²")
        logger.info(f"  Flooded area: {flooded_area_km2:.2f} km²")
        logger.info(f"  Flood percentage: {flood_percentage:.2f}%")
        
        return binary_risk.astype(np.uint8)
    
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
            flood_extent = self.calculate_flood_extent(dem_data, scenario.rise_meters, transform, land_mask)
            flood_extents[scenario.name] = {
                'flood_mask': flood_extent,
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
        
        # Panels 2-5: Flood extent for each scenario with rivers
        for i, scenario_name in enumerate(scenarios):
            if i >= 4:  # Only show first 4 scenarios
                break
                
            ax = fig.add_subplot(gs[0, i+1]) if i < 2 else fig.add_subplot(gs[1, i-2])
            flood_data = flood_extents[scenario_name]
            flood_mask = flood_data['flood_mask']
            scenario = flood_data['scenario']
            dem_data = flood_data['dem_data']
            transform = flood_data['transform']
            
            # Use the pre-computed land mask (optimization - no repeated transformations)
            # Always rasterize NUTS to DEM grid
            nuts_mask = rasterio.features.rasterize(
                [(geom, 1) for geom in nuts_gdf.geometry],
                out_shape=dem_data.shape,
                transform=transform,
                dtype=np.uint8
            )

            # Composite mask for visualization
            composite = np.zeros_like(dem_data, dtype=np.uint8)
            composite[(land_mask==0)] = 0  # water (from land mass file)
            composite[(land_mask==1) & (nuts_mask==0)] = 1  # land outside NUTS
            composite[(land_mask==1) & (nuts_mask==1) & (flood_mask==0)] = 2  # safe land
            composite[(land_mask==1) & (nuts_mask==1) & (flood_mask==1)] = 3  # flood risk

            from matplotlib.colors import ListedColormap, BoundaryNorm
            cmap = ListedColormap(['#1f78b4', '#bdbdbd', '#33a02c', '#e31a1c'])
            norm = BoundaryNorm([0,1,2,3,4], cmap.N)
            # Use the same extent as the DEM for all visualizations
            im = ax.imshow(composite, cmap=cmap, norm=norm, aspect='equal', extent=dem_bounds)
            
            # NUTS overlay
            if nuts_gdf is not None:
                nuts_gdf.plot(ax=ax, facecolor='none', edgecolor='black', linewidth=0.5, alpha=1.0, zorder=10)
            
            # River network overlay
            if self.river_network is not None:
                self.river_network.plot(ax=ax, color='darkblue', linewidth=0.3, alpha=1.0, zorder=11)
                
            ax.set_title(f'{scenario.name} Scenario\n({scenario.rise_meters}m SLR)', 
                        fontsize=12, fontweight='bold')
            ax.set_xlabel('X Coordinate (m)')
            ax.set_ylabel('Y Coordinate (m)')
            # Set the extent to match the DEM bounds
            ax.set_xlim(dem_bounds[0], dem_bounds[1])
            ax.set_ylim(dem_bounds[2], dem_bounds[3])
            ax.autoscale(False)
            # Add colorbar with custom ticks
            import matplotlib.patches as mpatches
            legend_patches = [
                mpatches.Patch(color='#1f78b4', label='Water'),
                mpatches.Patch(color='#bdbdbd', label='Outside Netherlands'),
                mpatches.Patch(color='#33a02c', label='Safe Land'),
                mpatches.Patch(color='#e31a1c', label='Flood Risk')
            ]
            ax.legend(handles=legend_patches, loc='lower left', fontsize=8, frameon=True)

            # Save the composite mask as GeoTIFF
            output_path = self.config.output_dir / f"composite_mask_{scenario.name.lower()}.tif"
            with rasterio.open(
                output_path,
                'w',
                driver='GTiff',
                height=composite.shape[0],
                width=composite.shape[1],
                count=1,
                dtype=composite.dtype,
                crs=crs,
                transform=transform,
                nodata=None,
                compress='lzw'
            ) as dst:
                dst.write(composite, 1)
                dst.set_band_description(1, f"Composite mask for {scenario.name} scenario ({scenario.rise_meters}m SLR)")
                # Add category descriptions as metadata
                dst.update_tags(
                    **{
                        '0': 'Water',
                        '1': 'Outside Netherlands',
                        '2': 'Safe Land',
                        '3': 'Flood Risk'
                    }
                )
            logger.info(f"Saved composite mask for {scenario.name} scenario to: {output_path}")
        
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
            flood_mask = flood_data['flood_mask']
            dem_data = flood_data['dem_data']
            
            flooded_area_km2 = np.sum(flood_mask) * (30 * 30) / 1_000_000
            flood_areas.append(flooded_area_km2)
            scenario_names.append(flood_data['scenario'].name)
            rise_values.append(flood_data['scenario'].rise_meters)
        
        colors = ['green', 'orange', 'red', 'purple'][:len(scenarios)]
        bars = ax5.bar(scenario_names, flood_areas, color=colors, alpha=0.7)
        ax5.set_title('Flooded Area by Scenario', fontsize=12, fontweight='bold')
        ax5.set_ylabel('Flooded Area (km²)')
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
        fig.suptitle('EU Climate Risk Assessment - Hazard Layer Analysis\n' + 
                    'Sea Level Rise and River Network Impact Assessment', 
                    fontsize=16, fontweight='bold', y=0.98)
        
        if save_plots:
            output_path = self.config.output_dir / "hazard_layer_assessment.png"
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
    
    def create_png_visualizations(self, flood_extents: Dict[str, np.ndarray], 
                                 output_dir: Optional[Path] = None) -> None:
        """Create PNG visualizations for each hazard scenario using unified styling."""
        if output_dir is None:
            output_dir = self.config.output_dir
            
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
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
            flood_mask = flood_data['flood_mask']
            transform = flood_data['transform']
            crs = flood_data['crs']
            scenario = flood_data['scenario']
            dem_data = flood_data['dem_data']
            
            # Create metadata for visualization
            meta = {
                'crs': crs,
                'transform': transform,
                'height': flood_mask.shape[0],
                'width': flood_mask.shape[1],
                'dtype': 'uint8'
            }
            
            # Create output path
            png_path = output_dir / f"hazard_{scenario_name.lower()}_scenario.png"
            
            # Use unified visualizer for consistent styling
            self.visualizer.visualize_hazard_scenario(
                flood_mask=flood_mask,
                dem_data=dem_data,
                meta=meta,
                scenario=scenario,
                output_path=png_path,
                land_mask=land_mask
            )
            
            logger.info(f"Saved {scenario_name} hazard scenario PNG to {png_path}")

    def export_results(self, flood_extents: Dict[str, np.ndarray], create_png: bool = True) -> None:
        """
        Export hazard assessment results to files for further analysis.
        
        Args:
            flood_extents: Dictionary of flood extent results
            create_png: Whether to create PNG visualizations for each scenario
        """
        logger.info("Exporting hazard assessment results...")
        
        for scenario_name, flood_data in flood_extents.items():
            flood_mask = flood_data['flood_mask']
            transform = flood_data['transform']
            crs = flood_data['crs']
            scenario = flood_data['scenario']
            
            # Export as GeoTIFF
            output_path = self.config.output_dir / f"flood_extent_{scenario_name.lower()}.tif"
            
            with rasterio.open(
                output_path,
                'w',
                driver='GTiff',
                height=flood_mask.shape[0],
                width=flood_mask.shape[1],
                count=1,
                dtype=flood_mask.dtype,
                crs=crs,
                transform=transform,
                compress='lzw'
            ) as dst:
                dst.write(flood_mask, 1)
                dst.set_band_description(1, f"Flood extent for {scenario.rise_meters}m SLR")
            
            logger.info(f"Exported {scenario_name} flood extent to: {output_path}")
        
        # Export summary statistics
        summary_stats = []
        for scenario_name, flood_data in flood_extents.items():
            flood_mask = flood_data['flood_mask']
            dem_data = flood_data['dem_data']
            scenario = flood_data['scenario']
            
            flooded_area_km2 = np.sum(flood_mask) * (30 * 30) / 1_000_000
            total_valid_area_km2 = np.sum(~np.isnan(dem_data)) * (30 * 30) / 1_000_000
            flood_percentage = (flooded_area_km2 / total_valid_area_km2) * 100
            
            summary_stats.append({
                'scenario': scenario_name,
                'sea_level_rise_m': scenario.rise_meters,
                'flooded_area_km2': flooded_area_km2,
                'total_area_km2': total_valid_area_km2,
                'flood_percentage': flood_percentage,
                'description': scenario.description
            })
        
        # Save summary as CSV
        summary_df = pd.DataFrame(summary_stats)
        summary_path = self.config.output_dir / "hazard_assessment_summary.csv"
        summary_df.to_csv(summary_path, index=False)
        logger.info(f"Exported summary statistics to: {summary_path}")

        if create_png:
            self.create_png_visualizations(flood_extents)



