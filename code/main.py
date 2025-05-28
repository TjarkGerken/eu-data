#!/usr/bin/env python3
"""
EU Climate Risk Assessment System
=================================

A comprehensive geospatial analysis tool for assessing climate risks in European regions.
This system implements a three-layer approach: Hazard, Exposition, and Risk.

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
import logging
import numpy as np
import rasterio
import rasterio.mask
import rasterio.features
import rasterio.warp
from rasterio.enums import Resampling
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Rectangle
import seaborn as sns
from pathlib import Path
from typing import Tuple, List, Dict, Optional, Union
import warnings
from dataclasses import dataclass
from enum import Enum

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore', category=rasterio.errors.NotGeoreferencedWarning)
warnings.filterwarnings('ignore', category=UserWarning)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('risk_assessment.log')
    ]
)
logger = logging.getLogger(__name__)

class RiskLayer(Enum):
    """Enumeration for the three risk assessment layers."""
    HAZARD = "hazard"
    EXPOSITION = "exposition"  
    RISK = "risk"

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

@dataclass
class ProjectConfig:
    """Configuration class for the risk assessment project."""
    data_dir: Path = Path("data")
    output_dir: Path = Path("output")
    dem_file: str = "ClippedCopernicusHeightProfile.tif"
    
    # Projection settings (using EPSG:3035 - ETRS89-extended / LAEA Europe)
    target_crs: str = "EPSG:3035"
    
    # Visualization settings
    figure_size: Tuple[int, int] = (15, 10)
    dpi: int = 300
    
    def __post_init__(self):
        """Ensure output directory exists."""
        self.output_dir.mkdir(exist_ok=True)

class HazardLayer:
    """
    Hazard Layer Implementation
    ==========================
    
    The Hazard Layer processes Digital Elevation Model (DEM) data to assess
    sea level rise impacts under different scenarios. It provides the foundation
    for risk assessment by identifying areas vulnerable to flooding.
    
    Key Features:
    - Configurable sea level rise scenarios
    - Proper cartographic projection handling
    - Flood extent calculation based on DEM analysis
    - Standardized data harmonization
    """
    
    def __init__(self, config: ProjectConfig):
        """Initialize the Hazard Layer with project configuration."""
        self.config = config
        self.dem_path = self.config.data_dir / self.config.dem_file
        self.scenarios = SeaLevelScenario.get_default_scenarios()
        
        # Validate DEM file exists
        if not self.dem_path.exists():
            raise FileNotFoundError(f"DEM file not found: {self.dem_path}")
        
        logger.info(f"Initialized Hazard Layer with DEM: {self.dem_path}")
        
    def load_and_prepare_dem(self) -> Tuple[np.ndarray, rasterio.Affine, rasterio.crs.CRS]:
        """
        Load and prepare the DEM data for analysis.
        
        Returns:
            Tuple containing the DEM array, transform, and CRS information.
        """
        logger.info("Loading and preparing DEM data...")
        
        with rasterio.open(self.dem_path) as src:
            # Read the DEM data
            dem_data = src.read(1)
            transform = src.transform
            original_crs = src.crs
            
            # Handle nodata values
            nodata = src.nodata
            if nodata is not None:
                dem_data = np.where(dem_data == nodata, np.nan, dem_data)
            
            # Clip elevation values to relevant range for Netherlands
            dem_data = np.clip(dem_data, -25, 50)
            
            # Log basic statistics
            valid_data = dem_data[~np.isnan(dem_data)]
            logger.info(f"DEM Statistics:")
            logger.info(f"  Shape: {dem_data.shape}")
            logger.info(f"  Min elevation (clipped): {np.min(valid_data):.2f}m")
            logger.info(f"  Max elevation (clipped): {np.max(valid_data):.2f}m")
            logger.info(f"  Mean elevation: {np.mean(valid_data):.2f}m")
            logger.info(f"  Original CRS: {original_crs}")
            
            return dem_data, transform, original_crs
    
    def calculate_flood_extent(self, dem_data: np.ndarray, sea_level_rise: float) -> np.ndarray:
        """
        Calculate flood extent based on DEM and sea level rise scenario.
        
        Args:
            dem_data: Digital elevation model data array
            sea_level_rise: Sea level rise in meters
            
        Returns:
            Binary array where 1 indicates flooded areas, 0 indicates safe areas
        """
        logger.info(f"Calculating flood extent for {sea_level_rise}m sea level rise...")
        
        # Simple flood model: areas below sea level rise are considered flooded
        # In a more sophisticated model, you might consider:
        # - Connectivity to the sea
        # - Flood propagation algorithms
        # - Coastal protection infrastructure
        # - Tidal effects
        
        flood_mask = dem_data <= sea_level_rise
        
        # Handle NaN values
        flood_mask = np.where(np.isnan(dem_data), False, flood_mask)
        
        # Calculate areas using 64-bit integers to avoid overflow
        pixel_area_m2 = np.int64(30) * np.int64(30)  # 30m resolution
        flooded_pixels = np.int64(np.sum(flood_mask))
        valid_pixels = np.int64(np.sum(~np.isnan(dem_data)))
        
        flooded_area_km2 = (flooded_pixels * pixel_area_m2) / 1_000_000.0
        total_valid_area_km2 = (valid_pixels * pixel_area_m2) / 1_000_000.0
        flood_percentage = (flooded_pixels / valid_pixels) * 100.0 if valid_pixels > 0 else 0.0
        
        logger.info(f"  Flooded area: {flooded_area_km2:.2f} km²")
        logger.info(f"  Flood percentage: {flood_percentage:.2f}%")
        
        return flood_mask.astype(np.uint8)
    
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
        
        # Calculate extent for matplotlib
        height, width = dem_data.shape
        left, top = rasterio.transform.xy(transform, 0, 0, offset='ul')
        right, bottom = rasterio.transform.xy(transform, height-1, width-1, offset='lr')
        extent = [left, right, bottom, top]
        
        # Panel 1: Original DEM
        ax1 = fig.add_subplot(gs[0, 0])
        im1 = ax1.imshow(dem_data, cmap=dem_cmap, norm=norm, aspect='equal', extent=extent)
        self._add_nuts_overlay(ax1, nuts_gdf, crs)
        ax1.set_title('Original DEM\n(Copernicus Height Profile, Clipped -25m to 50m)', 
                     fontsize=12, fontweight='bold')
        ax1.set_xlabel('X Coordinate (m)')
        ax1.set_ylabel('Y Coordinate (m)')
        plt.colorbar(im1, ax=ax1, label='Elevation (m)', shrink=0.8)
        
        # Panels 2-4: Flood extent for each scenario
        for i, scenario_name in enumerate(scenarios):
            ax = fig.add_subplot(gs[0, i+1]) if i < 2 else fig.add_subplot(gs[1, i-2])
            
            flood_data = flood_extents[scenario_name]
            flood_mask = flood_data['flood_mask']
            scenario = flood_data['scenario']
            
            # Show flood extent
            im = ax.imshow(flood_mask, cmap=flood_cmap, aspect='equal', extent=extent)
            self._add_nuts_overlay(ax, nuts_gdf, crs)
            ax.set_title(f'{scenario.name} Scenario\n({scenario.rise_meters}m SLR)', 
                        fontsize=12, fontweight='bold')
            ax.set_xlabel('X Coordinate (m)')
            ax.set_ylabel('Y Coordinate (m)')
            
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
        
        # Panel 6: Elevation histogram with flood thresholds
        ax6 = fig.add_subplot(gs[2, :])
        dem_data = flood_extents[scenarios[0]]['dem_data']
        valid_elevations = dem_data[~np.isnan(dem_data)]
        
        # Create histogram with clipped data
        ax6.hist(valid_elevations, bins=100, range=(-25, 50), alpha=0.7, 
                color='skyblue', edgecolor='black')
        ax6.set_xlabel('Elevation (m)')
        ax6.set_ylabel('Frequency')
        ax6.set_title('Elevation Distribution with Sea Level Rise Thresholds\n' +
                     '(Clipped to -25m to 50m range)', fontsize=12, fontweight='bold')
        
        # Add vertical lines for each scenario
        colors = ['green', 'orange', 'red']
        for i, scenario_name in enumerate(scenarios):
            scenario = flood_extents[scenario_name]['scenario']
            ax6.axvline(scenario.rise_meters, color=colors[i], linestyle='--', 
                       linewidth=2, label=f'{scenario.name} ({scenario.rise_meters}m)')
        
        ax6.legend()
        ax6.grid(True, alpha=0.3)
        ax6.set_xlim(-25, 50)  # Set x-axis limits to match clipped range
        
        # Add main title
        fig.suptitle('EU Climate Risk Assessment - Hazard Layer Analysis\n' + 
                    'Sea Level Rise Impact Assessment using Copernicus DEM (Clipped -25m to 50m)', 
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

class ExpositionLayer:
    """
    Exposition Layer Implementation (Placeholder)
    ============================================
    
    The Exposition Layer will assess what assets, populations, and economic
    activities are exposed to the hazards identified in the Hazard Layer.
    
    Future implementation will include:
    - Population density analysis
    - Economic activity mapping
    - Infrastructure exposure assessment
    - Building density integration
    """
    
    def __init__(self, config: ProjectConfig):
        self.config = config
        logger.info("Exposition Layer initialized (placeholder)")
    
    def process_population_exposure(self):
        """Placeholder for population exposure analysis."""
        logger.info("Population exposure analysis - To be implemented")
        pass
    
    def process_economic_exposure(self):
        """Placeholder for economic exposure analysis."""
        logger.info("Economic exposure analysis - To be implemented")
        pass

class RiskAssessment:
    """
    Risk Assessment Integration Layer (Placeholder)
    ==============================================
    
    The Risk Layer combines Hazard and Exposition layers to calculate
    comprehensive risk metrics for different scenarios.
    
    Future implementation will include:
    - Multi-criteria risk calculation
    - Vulnerability assessment
    - Risk aggregation and normalization
    - Scenario comparison and ranking
    """
    
    def __init__(self, config: ProjectConfig):
        self.config = config
        self.hazard_layer = HazardLayer(config)
        self.exposition_layer = ExpositionLayer(config)
        logger.info("Risk Assessment layer initialized")
    
    def calculate_integrated_risk(self):
        """Placeholder for integrated risk calculation."""
        logger.info("Integrated risk calculation - To be implemented")
        pass

def main():
    """
    Main execution function for the EU Climate Risk Assessment System.
    """
    logger.info("=" * 60)
    logger.info("EU CLIMATE RISK ASSESSMENT SYSTEM")
    logger.info("=" * 60)
    
    # Initialize project configuration
    config = ProjectConfig()
    logger.info(f"Project initialized with data directory: {config.data_dir}")
    
    try:
        # Initialize and run Hazard Layer analysis
        logger.info("\n" + "="*40)
        logger.info("HAZARD LAYER ANALYSIS")
        logger.info("="*40)
        
        hazard_layer = HazardLayer(config)
        
        # Process default scenarios (1m, 2m, 3m sea level rise)
        flood_extents = hazard_layer.process_scenarios()
        
        # Create visualizations
        hazard_layer.visualize_hazard_assessment(flood_extents, save_plots=True)
        
        # Export results
        hazard_layer.export_results(flood_extents)
        
        # Future layers (placeholders)
        logger.info("\n" + "="*40)
        logger.info("EXPOSITION LAYER ANALYSIS")
        logger.info("="*40)
        exposition_layer = ExpositionLayer(config)
        
        logger.info("\n" + "="*40)
        logger.info("RISK ASSESSMENT INTEGRATION")
        logger.info("="*40)
        risk_assessment = RiskAssessment(config)
        
        logger.info("\n" + "="*60)
        logger.info("ANALYSIS COMPLETE")
        logger.info("="*60)
        logger.info(f"Results saved to: {config.output_dir}")
        
    except Exception as e:
        logger.error(f"Error during analysis: {str(e)}")
        raise

if __name__ == "__main__":
    main()
