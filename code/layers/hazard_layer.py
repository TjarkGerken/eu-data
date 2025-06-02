from typing import Dict, List, Optional, Tuple
import numpy as np
import rasterio
import rasterio.features
import rasterio.warp
import geopandas as gpd
from scipy import ndimage
from dataclasses import dataclass
from code.main import ProjectConfig
from code.utils import setup_logging


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
        
        # Data holders
        self.dem_data = None
        self.transform = None
        self.crs = None
        self.river_network = None
        self.river_nodes = None
        
        # Validate files exist
        for path in [self.dem_path, self.river_segments_path, self.river_nodes_path]:
            if not path.exists():
                raise FileNotFoundError(f"Required file not found: {path}")
        
        logger.info(f"Initialized Hazard Layer with DEM and river data")
        
    def load_and_prepare_dem(self) -> Tuple[np.ndarray, rasterio.Affine, rasterio.crs.CRS]:
        """
        Load and prepare Digital Elevation Model (DEM) data.
        
        Returns:
            Tuple containing:
            - DEM data array
            - Affine transform
            - Coordinate Reference System
        """
        logger.info("Loading DEM data...")
        
        with rasterio.open(self.dem_path) as src:
            dem_data = src.read(1)
            transform = src.transform
            src_crs = src.crs
            
            # Transform DEM to ETRS89 Lambert Azimuthal Equal Area if needed
            target_crs = rasterio.crs.CRS.from_string(
                'PROJCS["ETRS89_Lambert_Azimutal_Equal_Area",'
                'GEOGCS["GCS_ETRS89_geographiques_dms",'
                'DATUM["D_ETRS_1989",'
                'SPHEROID["GRS_1980",6378137.0,298.257222101]],'
                'PRIMEM["Greenwich",0.0],'
                'UNIT["Degree",0.0174532925199433]],'
                'PROJECTION["Lambert_Azimuthal_Equal_Area"],'
                'PARAMETER["False_Easting",4321000.0],'
                'PARAMETER["False_Northing",3210000.0],'
                'PARAMETER["Central_Meridian",10.0],'
                'PARAMETER["Latitude_Of_Origin",52.0],'
                'UNIT["Meter",1.0]]'
            )
            
            if src_crs != target_crs:
                logger.info(f"Transforming DEM from {src_crs} to ETRS89 Lambert Azimuthal Equal Area")
                # Calculate output dimensions and transform
                transform, width, height = rasterio.warp.calculate_default_transform(
                    src_crs, target_crs, src.width, src.height, *src.bounds
                )
                
                # Initialize output array
                dem_transformed = np.zeros((height, width), dtype=dem_data.dtype)
                
                # Perform the reprojection
                rasterio.warp.reproject(
                    source=dem_data,
                    destination=dem_transformed,
                    src_transform=src.transform,
                    src_crs=src_crs,
                    dst_transform=transform,
                    dst_crs=target_crs,
                    resampling=self.config.resampling_method
                )
                
                dem_data = dem_transformed
                logger.info("DEM transformed to ETRS89 Lambert Azimuthal Equal Area")
            
            # Handle nodata values
            nodata = src.nodata
            if nodata is not None:
                dem_data = np.where(dem_data == nodata, np.nan, dem_data)
            
            # Store data for later use
            self.dem_data = dem_data
            self.transform = transform
            self.crs = target_crs
            
            # Calculate resolution in meters (always in meters since target CRS is projected)
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
            
            return dem_data, transform, target_crs
    
    def load_river_data(self) -> Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
        """Load and prepare river network data."""
        logger.info("Loading river network data...")
        
        try:
            # Define the target CRS (ETRS89 Lambert Azimuthal Equal Area)
            target_crs = rasterio.crs.CRS.from_string(
                'PROJCS["ETRS89_Lambert_Azimutal_Equal_Area",'
                'GEOGCS["GCS_ETRS89_geographiques_dms",'
                'DATUM["D_ETRS_1989",'
                'SPHEROID["GRS_1980",6378137.0,298.257222101]],'
                'PRIMEM["Greenwich",0.0],'
                'UNIT["Degree",0.0174532925199433]],'
                'PROJECTION["Lambert_Azimuthal_Equal_Area"],'
                'PARAMETER["False_Easting",4321000.0],'
                'PARAMETER["False_Northing",3210000.0],'
                'PARAMETER["Central_Meridian",10.0],'
                'PARAMETER["Latitude_Of_Origin",52.0],'
                'UNIT["Meter",1.0]]'
            )
            
            # Load river segments with explicit CRS
            river_network = gpd.read_file(self.river_segments_path)
            river_nodes = gpd.read_file(self.river_nodes_path)
            
            # Set CRS if not already set
            if river_network.crs is None:
                river_network.set_crs(target_crs, inplace=True)
                logger.info("Set river network CRS to ETRS89 Lambert Azimuthal Equal Area")
            if river_nodes.crs is None:
                river_nodes.set_crs(target_crs, inplace=True)
                logger.info("Set river nodes CRS to ETRS89 Lambert Azimuthal Equal Area")
            
            # Get DEM CRS
            with rasterio.open(self.dem_path) as src:
                dem_crs = src.crs
                dem_bounds = src.bounds
                logger.info(f"DEM CRS: {dem_crs}")
                logger.info(f"DEM bounds: [{dem_bounds.left:.2f}, {dem_bounds.right:.2f}] x [{dem_bounds.bottom:.2f}, {dem_bounds.top:.2f}]")
            
            # Transform to DEM CRS if different
            if river_network.crs != target_crs:
                river_network = river_network.to_crs(target_crs)
                logger.info("Transformed river network to ETRS89 Lambert Azimuthal Equal Area")
            if river_nodes.crs != target_crs:
                river_nodes = river_nodes.to_crs(target_crs)
                logger.info("Transformed river nodes to ETRS89 Lambert Azimuthal Equal Area")
            
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
    
    def calculate_flood_extent(self, dem_data: np.ndarray, sea_level_rise: float) -> np.ndarray:
        """
        Calculate flood extent based on DEM, river network, and sea level rise scenario.
        
        Args:
            dem_data: Digital elevation model data array
            sea_level_rise: Sea level rise in meters
            
        Returns:
            Binary array where 1 indicates flooded areas, 0 indicates safe areas
        """
        logger.info(f"Calculating flood extent for {sea_level_rise}m sea level rise...")
        
        # Basic flood model: areas below sea level rise are considered flooded
        flood_mask = dem_data <= sea_level_rise
        
        try:
            if self.river_network is None:
                self.load_river_data()
                
            # Create a raster representation of the river network
            river_raster = self._rasterize_river_network(dem_data.shape)
            
            # Enhance flood risk near rivers based on elevation and distance
            river_buffer = ndimage.distance_transform_edt(~river_raster)
            river_influence = np.exp(-river_buffer / 1000)  # Decay factor for river influence
            
            # Calculate elevation-based flood risk
            elevation_risk = np.clip((sea_level_rise - dem_data) / sea_level_rise, 0, 1)
            
            # Combine flood risks
            combined_risk = np.maximum(
                flood_mask,
                (elevation_risk * river_influence) > 0.5
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
        
        # Calculate statistics
        pixel_area_m2 = np.int64(30) * np.int64(30)  # 30m resolution
        flooded_pixels = np.int64(np.sum(binary_risk))
        valid_pixels = np.int64(np.sum(~np.isnan(dem_data)))
        
        flooded_area_km2 = (flooded_pixels * pixel_area_m2) / 1_000_000.0
        flood_percentage = (flooded_pixels / valid_pixels) * 100.0 if valid_pixels > 0 else 0.0
        
        logger.info(f"  Flooded area: {flooded_area_km2:.2f} km²")
        logger.info(f"  Flood percentage: {flood_percentage:.2f}%")
        
        return binary_risk.astype(np.uint8)
    
    def _rasterize_river_network(self, shape: Tuple[int, int]) -> np.ndarray:
        """Convert river network to raster format."""
        river_raster = rasterio.features.rasterize(
            [(geom, 1) for geom in self.river_network.geometry],
            out_shape=shape,
            transform=self.transform,
            dtype=np.uint8
        )
        return river_raster
    
    def calculate_river_distance(self, shape: Tuple[int, int]) -> np.ndarray:
        """Calculate distance to nearest river for each pixel."""
        river_raster = self._rasterize_river_network(shape)
        return ndimage.distance_transform_edt(~river_raster) * self.transform[0]
    
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
        
        # Load DEM data once
        dem_data, transform, crs = self.load_and_prepare_dem()
        
        flood_extents = {}
        
        for scenario in scenarios:
            logger.info(f"Processing scenario: {scenario.name} ({scenario.rise_meters}m)")
            
            flood_extent = self.calculate_flood_extent(dem_data, scenario.rise_meters)
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
        Create comprehensive visualizations of the hazard assessment results.
        
        Args:
            flood_extents: Dictionary of flood extent results
            save_plots: Whether to save plots to disk
        """
        logger.info("Creating hazard assessment visualizations...")
        
        # Load NUTS administrative boundaries for overlay
        nuts_gdf = self._load_nuts_boundaries()
        
        # Create a comprehensive multi-panel figure
        fig = plt.figure(figsize=(20, 15))
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
        
        # Color schemes
        dem_cmap = plt.cm.terrain
        flood_cmap = mcolors.ListedColormap(['green', 'red'])
        
        # Set terrain colormap to focus on relevant elevation range
        dem_cmap.set_bad('lightgray')  # Color for NaN values
        norm = mcolors.Normalize(vmin=-25, vmax=50)
        
        scenarios = list(flood_extents.keys())
        
        # Get spatial extent and transform for proper overlay
        dem_data = flood_extents[scenarios[0]]['dem_data']
        transform = flood_extents[scenarios[0]]['transform']
        crs = flood_extents[scenarios[0]]['crs']
        
        # Calculate extent for matplotlib in the correct CRS
        with rasterio.open(self.dem_path) as src:
            bounds = src.bounds
            extent = [bounds.left, bounds.right, bounds.bottom, bounds.top]
        
        # Load river data if not already loaded
        if self.river_network is None:
            self.load_river_data()
        
        # Ensure river network is in the correct CRS
        if self.river_network is not None:
            if self.river_network.crs is None:
                self.river_network.set_crs("IGNF:ETRS89LAEA", inplace=True)
            if self.river_nodes.crs is None:
                self.river_nodes.set_crs("IGNF:ETRS89LAEA", inplace=True)
            
            # Transform to DEM's CRS if different
            if self.river_network.crs != crs:
                self.river_network = self.river_network.to_crs(crs)
            if self.river_nodes.crs != crs:
                self.river_nodes = self.river_nodes.to_crs(crs)
        
        # Panel 1: Original DEM with rivers
        ax1 = fig.add_subplot(gs[0, 0])
        im1 = ax1.imshow(dem_data, cmap=dem_cmap, norm=norm, aspect='equal', extent=extent)
        self._add_nuts_overlay(ax1, nuts_gdf, crs)
        if self.river_network is not None:
            self.river_network.plot(ax=ax1, color='blue', linewidth=0.8, alpha=0.7, zorder=5)
            self.river_nodes.plot(ax=ax1, color='darkblue', markersize=1, alpha=0.5, zorder=6)
        ax1.set_title('Original DEM with River Network\n(Copernicus Height Profile, Clipped -25m to 50m)', 
                     fontsize=12, fontweight='bold')
        ax1.set_xlabel('X Coordinate (m)')
        ax1.set_ylabel('Y Coordinate (m)')
        plt.colorbar(im1, ax=ax1, label='Elevation (m)', shrink=0.8)
        
        # Set the extent to match the DEM bounds
        ax1.set_xlim(bounds.left, bounds.right)
        ax1.set_ylim(bounds.bottom, bounds.top)
        
        # Panels 2-4: Flood extent for each scenario with rivers
        for i, scenario_name in enumerate(scenarios):
            ax = fig.add_subplot(gs[0, i+1]) if i < 2 else fig.add_subplot(gs[1, i-2])
            
            flood_data = flood_extents[scenario_name]
            flood_mask = flood_data['flood_mask']
            scenario = flood_data['scenario']
            
            # Show flood extent
            im = ax.imshow(flood_mask, cmap=flood_cmap, aspect='equal', extent=extent)
            self._add_nuts_overlay(ax, nuts_gdf, crs)
            
            # Add river network
            if self.river_network is not None:
                self.river_network.plot(ax=ax, color='blue', linewidth=0.8, alpha=0.7, zorder=5)
                self.river_nodes.plot(ax=ax, color='darkblue', markersize=1, alpha=0.5, zorder=6)
            
            ax.set_title(f'{scenario.name} Scenario with River Network\n({scenario.rise_meters}m SLR)', 
                        fontsize=12, fontweight='bold')
            ax.set_xlabel('X Coordinate (m)')
            ax.set_ylabel('Y Coordinate (m)')
            
            # Set the extent to match the DEM bounds
            ax.set_xlim(bounds.left, bounds.right)
            ax.set_ylim(bounds.bottom, bounds.top)
            
            # Add colorbar
            cbar = plt.colorbar(im, ax=ax, shrink=0.8)
            cbar.set_ticks([0.25, 0.75])
            cbar.set_ticklabels(['Safe', 'Flooded'])
        
        # Panel 5: Flood risk progression
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
        
        bars = ax5.bar(scenario_names, flood_areas, color=['green', 'orange', 'red'], alpha=0.7)
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
            # Plot elevation histogram
            valid_elevations = dem_data[~np.isnan(dem_data)]
            ax6.hist(valid_elevations, bins=100, range=(-25, 50), alpha=0.7, 
                    color='skyblue', edgecolor='black', zorder=1)
            
            # Add vertical lines for each scenario
            colors = ['green', 'orange', 'red']
            for i, scenario_name in enumerate(scenarios):
                scenario = flood_extents[scenario_name]['scenario']
                ax6.axvline(scenario.rise_meters, color=colors[i], linestyle='--', 
                           linewidth=2, label=f'{scenario.name} ({scenario.rise_meters}m)', zorder=2)
            
            # Add river statistics
            river_stats = "River Network Statistics:\n"
            river_stats += f"Total Segments: {len(self.river_network)}\n"
            river_stats += f"Total Nodes: {len(self.river_nodes)}"
            ax6.text(0.98, 0.98, river_stats, transform=ax6.transAxes,
                    verticalalignment='top', horizontalalignment='right',
                    bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))
            
        ax6.set_xlabel('Elevation (m)')
        ax6.set_ylabel('Frequency')
        ax6.set_title('Elevation Distribution with Sea Level Rise Thresholds\n' +
                     '(Clipped to -25m to 50m range)', fontsize=12, fontweight='bold')
        ax6.legend()
        ax6.grid(True, alpha=0.3)
        ax6.set_xlim(-25, 50)
        
        # Add main title
        fig.suptitle('EU Climate Risk Assessment - Hazard Layer Analysis\n' + 
                    'Sea Level Rise and River Network Impact Assessment', 
                    fontsize=16, fontweight='bold', y=0.98)
        
        if save_plots:
            output_path = self.config.output_dir / "hazard_layer_assessment.png"
            plt.savefig(output_path, dpi=self.config.dpi, bbox_inches='tight')
            logger.info(f"Saved hazard assessment visualization to: {output_path}")
        
        plt.show()
    
    def _load_nuts_boundaries(self) -> gpd.GeoDataFrame:
        """
        Load NUTS administrative boundaries for overlay visualization.
        
        Returns:
            GeoDataFrame with NUTS boundaries
        """
        try:
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
            # Reproject NUTS boundaries to match the DEM CRS
            if nuts_gdf.crs != target_crs:
                nuts_reproj = nuts_gdf.to_crs(target_crs)
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
    
    def export_results(self, flood_extents: Dict[str, np.ndarray]) -> None:
        """
        Export hazard assessment results to files for further analysis.
        
        Args:
            flood_extents: Dictionary of flood extent results
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



