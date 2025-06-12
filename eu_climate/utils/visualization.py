"""
Unified Visualization Utilities for EU Climate Risk Assessment
============================================================

This module provides standardized visualization functions and styling
that ensure consistency across all risk layers (Hazard, Exposition, Relevance).

Key Features:
- Scientific publication-ready styling
- Consistent color schemes and layouts
- Standardized NUTS boundary overlays
- Unified coordinate reference handling
- Minimalistic, professional design
"""

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.colors import ListedColormap, BoundaryNorm
import numpy as np
import geopandas as gpd
import rasterio
from typing import Optional, Tuple, Dict, Any
from pathlib import Path
import logging

from eu_climate.config.config import ProjectConfig
from eu_climate.utils.utils import setup_logging

logger = setup_logging(__name__)


class ScientificStyle:
    """Scientific publication styling configuration."""
    
    # Color schemes for different data types
    ELEVATION_CMAP = 'terrain'
    HAZARD_CMAP = 'Reds'
    EXPOSITION_CMAP = 'PiYG'
    RELEVANCE_CMAP = 'PiYG'
    
    # Standard figure parameters
    FIGURE_SIZE = (12, 8)
    DPI = 300
    
    # Font specifications
    FONT_FAMILY = 'sans-serif'
    TITLE_SIZE = 14
    LABEL_SIZE = 12
    TICK_SIZE = 10
    LEGEND_SIZE = 10
    
    # Color definitions
    NUTS_BOUNDARY_COLOR = '#2c3e50'  # Dark blue-gray
    NUTS_BOUNDARY_WIDTH = 0.8
    NUTS_BOUNDARY_ALPHA = 0.9
    
    WATER_COLOR = '#3498db'  # Light blue
    LAND_OUTSIDE_COLOR = '#ecf0f1'  # Light gray
    SAFE_LAND_COLOR = '#27ae60'  # Green
    FLOOD_RISK_COLOR = '#e74c3c'  # Red
    
    # Statistics box styling
    STATS_BOX_PROPS = {
        'boxstyle': 'round,pad=0.5',
        'facecolor': 'white',
        'alpha': 0.9,
        'edgecolor': '#34495e',
        'linewidth': 1
    }


def setup_scientific_style():
    """Configure matplotlib for scientific publications."""
    plt.style.use('default')  # Start with clean default
    
    # Set font properties
    plt.rcParams.update({
        'font.family': ScientificStyle.FONT_FAMILY,
        'font.size': ScientificStyle.LABEL_SIZE,
        'axes.titlesize': ScientificStyle.TITLE_SIZE,
        'axes.labelsize': ScientificStyle.LABEL_SIZE,
        'xtick.labelsize': ScientificStyle.TICK_SIZE,
        'ytick.labelsize': ScientificStyle.TICK_SIZE,
        'legend.fontsize': ScientificStyle.LEGEND_SIZE,
        
        # Figure properties
        'figure.figsize': ScientificStyle.FIGURE_SIZE,
        'figure.dpi': ScientificStyle.DPI,
        'savefig.dpi': ScientificStyle.DPI,
        'savefig.bbox': 'tight',
        'savefig.facecolor': 'white',
        
        # Axes properties
        'axes.grid': False,
        'axes.spines.top': False,
        'axes.spines.right': False,
        'axes.linewidth': 0.8,
        'axes.edgecolor': '#2c3e50',
        
        # Tick properties
        'xtick.direction': 'out',
        'ytick.direction': 'out',
        'xtick.major.size': 4,
        'ytick.major.size': 4,
        'xtick.color': '#2c3e50',
        'ytick.color': '#2c3e50',
        
        # Remove tick marks for cleaner look
        'xtick.major.size': 0,
        'ytick.major.size': 0,
        'xtick.minor.size': 0,
        'ytick.minor.size': 0
    })


class LayerVisualizer:
    """Unified visualizer for all risk assessment layers."""
    
    def __init__(self, config: ProjectConfig):
        self.config = config
        setup_scientific_style()
        
    def get_nuts_boundaries(self, level: str = "L3") -> Optional[gpd.GeoDataFrame]:
        """Load NUTS boundaries for overlay visualization."""
        nuts_file = f"NUTS-{level}-NL.shp"
        nuts_path = self.config.data_dir / nuts_file
        
        if not nuts_path.exists():
            logger.warning(f"NUTS {level} boundaries not found: {nuts_path}")
            return None
            
        try:
            target_crs = rasterio.crs.CRS.from_string(self.config.target_crs)
            nuts_gdf = gpd.read_file(nuts_path)
            
            if nuts_gdf.crs != target_crs:
                nuts_gdf = nuts_gdf.to_crs(target_crs)
                
            logger.info(f"Loaded NUTS {level} boundaries: {len(nuts_gdf)} regions")
            return nuts_gdf
            
        except Exception as e:
            logger.warning(f"Could not load NUTS {level} boundaries: {e}")
            return None
    
    def get_raster_extent(self, data: np.ndarray, meta: dict) -> Tuple[float, float, float, float]:
        """Calculate raster extent for proper coordinate alignment."""
        if 'transform' in meta:
            transform = meta['transform']
            height, width = data.shape
            
            left = transform.c
            right = left + width * transform.a
            top = transform.f
            bottom = top + height * transform.e
            
            return (left, right, bottom, top)
        else:
            height, width = data.shape
            return (0, width, 0, height)
    
    def add_nuts_overlay(self, ax, nuts_gdf: Optional[gpd.GeoDataFrame]):
        """Add NUTS boundaries as overlay with consistent styling."""
        if nuts_gdf is not None:
            nuts_gdf.boundary.plot(
                ax=ax,
                color=ScientificStyle.NUTS_BOUNDARY_COLOR,
                linewidth=ScientificStyle.NUTS_BOUNDARY_WIDTH,
                alpha=ScientificStyle.NUTS_BOUNDARY_ALPHA,
                zorder=10
            )
    
    def add_statistics_box(self, ax, data: np.ndarray, position: str = 'upper right'):
        """Add statistics box with consistent styling."""
        valid_data = data[~np.isnan(data) & (data > 0)]
        
        if len(valid_data) == 0:
            return
            
        stats_text = (
            f'Min: {np.min(valid_data):.3f}\n'
            f'Max: {np.max(valid_data):.3f}\n'
            f'Mean: {np.mean(valid_data):.3f}\n'
            f'Std: {np.std(valid_data):.3f}'
        )
        
        # Position mapping
        position_coords = {
            'upper right': (0.98, 0.98),
            'upper left': (0.02, 0.98),
            'lower right': (0.98, 0.02),
            'lower left': (0.02, 0.02)
        }
        
        coords = position_coords.get(position, (0.98, 0.98))
        
        ax.text(
            coords[0], coords[1], stats_text,
            transform=ax.transAxes,
            verticalalignment='top' if 'upper' in position else 'bottom',
            horizontalalignment='right' if 'right' in position else 'left',
            bbox=ScientificStyle.STATS_BOX_PROPS,
            fontsize=ScientificStyle.TICK_SIZE
        )
    
    def create_standard_colorbar(self, im, ax, label: str, shrink: float = 0.8):
        """Create standardized colorbar with consistent styling."""
        cbar = plt.colorbar(im, ax=ax, shrink=shrink)
        cbar.set_label(label, rotation=270, labelpad=15, fontsize=ScientificStyle.LABEL_SIZE)
        cbar.ax.tick_params(labelsize=ScientificStyle.TICK_SIZE)
        return cbar
    
    def visualize_exposition_layer(self, data: np.ndarray, meta: dict, 
                                 output_path: Optional[Path] = None,
                                 title: str = "Exposition Layer") -> None:
        """Create standardized exposition layer visualization."""
        fig, ax = plt.subplots(figsize=ScientificStyle.FIGURE_SIZE, dpi=ScientificStyle.DPI)
        
        extent = self.get_raster_extent(data, meta)
        
        # Create main visualization
        im = ax.imshow(
            data, 
            cmap=ScientificStyle.EXPOSITION_CMAP,
            aspect='equal', 
            extent=extent,
            vmin=0, vmax=1
        )
        
        # Add NUTS overlay
        nuts_gdf = self.get_nuts_boundaries("L3")
        self.add_nuts_overlay(ax, nuts_gdf)
        
        # Styling
        ax.set_title(title, fontsize=ScientificStyle.TITLE_SIZE, fontweight='bold', pad=20)
        ax.set_xlabel('Easting (m)', fontsize=ScientificStyle.LABEL_SIZE)
        ax.set_ylabel('Northing (m)', fontsize=ScientificStyle.LABEL_SIZE)
        
        # Add colorbar
        self.create_standard_colorbar(im, ax, 'Exposition Index (0-1)')
        
        # Add statistics
        self.add_statistics_box(ax, data, 'upper left')
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=ScientificStyle.DPI, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            logger.info(f"Saved exposition visualization to {output_path}")
        
        plt.close()
    
    def visualize_hazard_scenario(self, flood_mask: np.ndarray, dem_data: np.ndarray, 
                                meta: dict, scenario, output_path: Optional[Path] = None,
                                land_mask: Optional[np.ndarray] = None) -> None:
        """Create standardized hazard scenario visualization."""
        fig, ax = plt.subplots(figsize=ScientificStyle.FIGURE_SIZE, dpi=ScientificStyle.DPI)
        
        extent = self.get_raster_extent(flood_mask, meta)
        
        # Calculate dynamic elevation range based on NUTS region if available
        nuts_gdf = self.get_nuts_boundaries("L3")
        
        if nuts_gdf is not None and land_mask is not None:
            # Create NUTS mask
            import rasterio.features
            nuts_mask = rasterio.features.rasterize(
                [(geom, 1) for geom in nuts_gdf.geometry],
                out_shape=dem_data.shape,
                transform=meta['transform'],
                dtype=np.uint8
            )
            
            # Get elevation data within NUTS and land areas only
            nuts_land_mask = (nuts_mask == 1) & (land_mask == 1) & (~np.isnan(dem_data))
            if np.any(nuts_land_mask):
                nuts_elevations = dem_data[nuts_land_mask]
                elevation_min = np.percentile(nuts_elevations, 2) - 30 # Use 2nd percentile to avoid outliers and add 30m buffer to ensure that only water is blue
                elevation_max = np.percentile(nuts_elevations, 98) + 100  # Use 98th percentile to avoid outliers and add 100m buffer to ensure that the entire landscape is visible (not all white)
            else:
                # Fallback to global range if no valid data
                valid_elevations = dem_data[~np.isnan(dem_data)]
                elevation_min = np.percentile(valid_elevations, 2) - 30
                elevation_max = np.percentile(valid_elevations, 98) + 100
        else:
            # Fallback to global range if no NUTS data or land mask
            valid_elevations = dem_data[~np.isnan(dem_data)]
            elevation_min = np.percentile(valid_elevations, 2) - 30
            elevation_max = np.percentile(valid_elevations, 98) + 100
        
        # Create masked elevation data for proper visualization
        dem_for_vis = dem_data.copy()
        
        # Set water areas to below minimum land elevation if land mask is available
        if land_mask is not None:
            water_elevation = elevation_min - 10
            dem_for_vis[land_mask == 0] = water_elevation
            vmin_vis = water_elevation
        else:
            vmin_vis = elevation_min
        
        # Create composite visualization showing elevation and flood risk
        # Use DEM as background with flood overlay
        im_dem = ax.imshow(
            dem_for_vis,
            cmap=ScientificStyle.ELEVATION_CMAP,
            aspect='equal',
            extent=extent,
            alpha=0.7,
            vmin=vmin_vis, vmax=elevation_max
        )
        
        # Overlay flood risk areas
        flood_overlay = np.ma.masked_where(flood_mask == 0, flood_mask)
        im_flood = ax.imshow(
            flood_overlay,
            cmap=ScientificStyle.HAZARD_CMAP,
            aspect='equal',
            extent=extent,
            alpha=0.8,
            vmin=0, vmax=1
        )
        
        # Add NUTS overlay
        if nuts_gdf is not None:
            self.add_nuts_overlay(ax, nuts_gdf)
        
        # Styling
        title = f'Hazard Assessment - {scenario.name} Scenario\n({scenario.rise_meters}m Sea Level Rise)'
        ax.set_title(title, fontsize=ScientificStyle.TITLE_SIZE, fontweight='bold', pad=20)
        ax.set_xlabel('Easting (m)', fontsize=ScientificStyle.LABEL_SIZE)
        ax.set_ylabel('Northing (m)', fontsize=ScientificStyle.LABEL_SIZE)
        
        # Add dual colorbars
        # Elevation colorbar
        cbar_dem = self.create_standard_colorbar(im_dem, ax, 'Elevation (m)', shrink=0.6)
        cbar_dem.ax.set_position([0.92, 0.15, 0.02, 0.3])
        
        # Flood risk colorbar (only if there are flooded areas)
        if np.any(flood_mask > 0):
            cbar_flood = self.create_standard_colorbar(im_flood, ax, 'Flood Risk', shrink=0.6)
            cbar_flood.ax.set_position([0.92, 0.55, 0.02, 0.3])
        
        # Add statistics for flood extent
        flooded_pixels = np.sum(flood_mask)
        total_pixels = flood_mask.size
        flood_percentage = (flooded_pixels / total_pixels) * 100
        
        stats_text = (
            f'Scenario: {scenario.name}\n'
            f'Sea Level Rise: {scenario.rise_meters}m\n'
            f'Elevation Range: {elevation_min:.1f}m to {elevation_max:.1f}m\n'
            f'Flood Coverage: {flood_percentage:.1f}%\n'
            f'Flooded Area: {flooded_pixels:,} pixels'
        )
        
        ax.text(
            0.02, 0.98, stats_text,
            transform=ax.transAxes,
            verticalalignment='top',
            horizontalalignment='left',
            bbox=ScientificStyle.STATS_BOX_PROPS,
            fontsize=ScientificStyle.TICK_SIZE
        )
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=ScientificStyle.DPI, bbox_inches='tight',
                       facecolor='white', edgecolor='none')
            logger.info(f"Saved hazard scenario visualization to {output_path}")
        
        plt.close()
    
    def visualize_hazard_layer(self, flood_data: Dict[str, np.ndarray], meta: dict,
                              output_path: Optional[Path] = None) -> None:
        """Create standardized hazard layer visualization."""
        # Implementation will be added in hazard layer modification
        pass
    
    def visualize_relevance_layer(self, data: np.ndarray, meta: dict,
                                layer_name: str, output_path: Optional[Path] = None) -> None:
        """Create standardized relevance layer visualization."""
        fig, ax = plt.subplots(figsize=ScientificStyle.FIGURE_SIZE, dpi=ScientificStyle.DPI)
        
        extent = self.get_raster_extent(data, meta)
        
        # Create main visualization
        im = ax.imshow(
            data,
            cmap=ScientificStyle.RELEVANCE_CMAP,
            aspect='equal',
            extent=extent,
            vmin=0, vmax=1
        )
        
        # Add NUTS overlay
        nuts_gdf = self.get_nuts_boundaries("L3")
        self.add_nuts_overlay(ax, nuts_gdf)
        
        # Styling
        title_map = {
            'gdp': 'GDP Economic Relevance',
            'freight_loading': 'Freight Loading Economic Relevance', 
            'freight_unloading': 'Freight Unloading Economic Relevance',
            'combined': 'Combined Economic Relevance'
        }
        
        title = title_map.get(layer_name, f'{layer_name.title()} Economic Relevance')
        ax.set_title(title, fontsize=ScientificStyle.TITLE_SIZE, fontweight='bold', pad=20)
        ax.set_xlabel('Easting (m)', fontsize=ScientificStyle.LABEL_SIZE)
        ax.set_ylabel('Northing (m)', fontsize=ScientificStyle.LABEL_SIZE)
        
        # Add colorbar
        self.create_standard_colorbar(im, ax, 'Economic Relevance Index (0-1)')
        
        # Add statistics
        self.add_statistics_box(ax, data, 'upper left')
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=ScientificStyle.DPI, bbox_inches='tight',
                       facecolor='white', edgecolor='none')
            logger.info(f"Saved {layer_name} relevance visualization to {output_path}")
        
        plt.close()


def create_flood_composite_colormap():
    """Create standardized colormap for flood risk visualization."""
    colors = [
        ScientificStyle.WATER_COLOR,           # Water
        ScientificStyle.LAND_OUTSIDE_COLOR,    # Land outside study area
        ScientificStyle.SAFE_LAND_COLOR,       # Safe land
        ScientificStyle.FLOOD_RISK_COLOR       # Flood risk
    ]
    return ListedColormap(colors), BoundaryNorm([0, 1, 2, 3, 4], len(colors)) 