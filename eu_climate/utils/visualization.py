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
from matplotlib.colors import LinearSegmentedColormap, ListedColormap, BoundaryNorm
import numpy as np
import geopandas as gpd
import rasterio
from typing import Optional, Tuple, Dict
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap


from eu_climate.config.config import ProjectConfig
from eu_climate.utils.utils import setup_logging

logger = setup_logging(__name__)

exposition_colors = [ 
    (0.0, '#ffffff'),
    (0.05, '#d8f3dc'),    
    (0.125, '#b7e4c7'),    
    # (0.25, '#95d5b2'),    
    # (0.375, '#74c69d'),    
    # (0.5, '#52b788'),    
    # (0.625, '#40916c'),    
    (0.25, '#2d6a4f'),    
    (0.5, '#1b4332'),    
    (0.7, '#081c15'),
    (1.0, '#000000')
]

economic_risk_colors = [
    (0.0, '#ffffff'),    
        (0.1, '#b6ffb6'),   
    (0.5, '#ff0000'),   
    (1.0, '#000000')    
]

hazard_risk_colors = [ 
    (0.0, '#ffffff'),
    (0.25, '#ff9500'),
    (0.5, '#e95555'),
    (0.75, '#e30613'),      
    (1.0, '#9f040e'),  
]

# Neue Colormap erzeugen
exposition_cmap = LinearSegmentedColormap.from_list("exposition_colors", exposition_colors)
economic_cmap = LinearSegmentedColormap.from_list("economic_risk_colors", economic_risk_colors)
hazard_cmap = LinearSegmentedColormap.from_list("hazard_risk_colors", hazard_risk_colors)

class ScientificStyle:
    """Scientific publication styling configuration."""
    
    # Color schemes for different data types
    ELEVATION_CMAP = 'terrain'
    HAZARD_CMAP = hazard_cmap
    EXPOSITION_CMAP = exposition_cmap
    RELEVANCE_CMAP = exposition_cmap  
    ECONOMIC_RISK_CMAP = economic_cmap
    
    # Zone classification values
    WATER_VALUE = 0
    OUTSIDE_NL_VALUE = 1  
    LAND_BASE_VALUE = 2
    
    # Zone colors
    WATER_COLOR = '#1f78b4'         # Blue for water bodies
    LAND_OUTSIDE_COLOR = '#bdbdbd'  # Light gray for areas outside Netherlands
    LAND_BASE_COLOR = '#ffffff'     # White base for Netherlands land
    
    # Standard figure parameters
    FIGURE_SIZE = (12, 8)
    DPI = 300
    
    # Font specifications
    FONT_FAMILY = 'sans-serif'
    TITLE_SIZE = 14
    LABEL_SIZE = 12
    TICK_SIZE = 10
    LEGEND_SIZE = 10
    
    # Color definitions (legacy - maintained for backward compatibility)
    NUTS_BOUNDARY_COLOR = '#2c3e50'  # Dark blue-gray
    NUTS_BOUNDARY_WIDTH = 0.5
    NUTS_BOUNDARY_ALPHA = 0.9
    
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
    
    @classmethod
    def get_zone_colors(cls):
        """Get standardized zone colors as a list for matplotlib colormaps."""
        return [cls.WATER_COLOR, cls.LAND_OUTSIDE_COLOR, cls.LAND_BASE_COLOR]
    
    @classmethod
    def create_zone_colormap(cls):
        """Create standardized zone colormap for all layer visualizations."""
        from matplotlib.colors import ListedColormap
        return ListedColormap(cls.get_zone_colors())


def setup_scientific_style():
    """Configure matplotlib for scientific publications."""
    plt.style.use('default')  
    

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
                                 title: str = "Exposition Layer",
                                 land_mask: Optional[np.ndarray] = None) -> None:
        """Create standardized exposition layer visualization with proper zone separation."""
        fig, ax = plt.subplots(figsize=ScientificStyle.FIGURE_SIZE, dpi=ScientificStyle.DPI)
        
        extent = self.get_raster_extent(data, meta)
        
        # Create zone classification for background
        zones = self.create_zone_classification(data.shape, meta['transform'], land_mask)
        
        # Display base zones first
        zone_cmap = ScientificStyle.create_zone_colormap()
        ax.imshow(zones, cmap=zone_cmap, aspect='equal', extent=extent, 
                 vmin=ScientificStyle.WATER_VALUE, vmax=ScientificStyle.LAND_BASE_VALUE, alpha=1.0)
        
        # Create data overlay only for Netherlands land areas
        netherlands_mask = (zones == ScientificStyle.LAND_BASE_VALUE) & (~np.isnan(data))
        data_overlay = np.full_like(data, np.nan, dtype=np.float32)
        data_overlay[netherlands_mask] = data[netherlands_mask]
        
        # Overlay exposition data
        im = ax.imshow(
            data_overlay,
            cmap=ScientificStyle.EXPOSITION_CMAP,
            aspect='equal',
            extent=extent,
            vmin=0, vmax=1,
            alpha=0.85
        )
        
        # Add NUTS overlay
        nuts_gdf = self.get_nuts_boundaries("L3")
        if nuts_gdf is not None:
            self.add_nuts_overlay(ax, nuts_gdf)
        
        # Styling
        ax.set_title(title, fontsize=ScientificStyle.TITLE_SIZE, fontweight='bold', pad=20)
        ax.set_xlabel('Easting (m)', fontsize=ScientificStyle.LABEL_SIZE)
        ax.set_ylabel('Northing (m)', fontsize=ScientificStyle.LABEL_SIZE)
        
        # Add colorbar for exposition data
        self.create_standard_colorbar(im, ax, 'Exposition Index (0-1)')
        
        # Add zone legend
        import matplotlib.patches as mpatches
        legend_patches = [
            mpatches.Patch(color=ScientificStyle.WATER_COLOR, label='Water Bodies'),
            mpatches.Patch(color=ScientificStyle.LAND_OUTSIDE_COLOR, label='Outside Netherlands')
        ]
        ax.legend(handles=legend_patches, loc='lower left', fontsize=8, frameon=True)
        
        # Add statistics for Netherlands areas only
        if np.any(netherlands_mask):
            netherlands_data = data[netherlands_mask]
            self.add_statistics_box(ax, netherlands_data, 'upper left')
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=ScientificStyle.DPI, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            logger.info(f"Saved exposition visualization to {output_path}")
        
        plt.close()
    
    def visualize_hazard_scenario(self, flood_mask: np.ndarray, dem_data: np.ndarray, 
                                meta: dict, scenario, output_path: Optional[Path] = None,
                                land_mask: Optional[np.ndarray] = None) -> None:
        """Create standardized hazard scenario visualization with centralized zone handling."""
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
        
        # Create zone classification for background
        zones = self.create_zone_classification(dem_data.shape, meta['transform'], land_mask)
        
        # Display base zones first
        zone_cmap = ScientificStyle.create_zone_colormap()
        ax.imshow(zones, cmap=zone_cmap, aspect='equal', extent=extent, 
                 vmin=ScientificStyle.WATER_VALUE, vmax=ScientificStyle.LAND_BASE_VALUE, alpha=1.0)
        
        # Create elevation overlay for Netherlands land areas only
        netherlands_mask = (zones == ScientificStyle.LAND_BASE_VALUE) & (~np.isnan(dem_data))
        
        # Create masked elevation data for proper visualization
        dem_for_vis = np.full_like(dem_data, np.nan, dtype=np.float32)
        dem_for_vis[netherlands_mask] = dem_data[netherlands_mask]
        
        # Overlay elevation data with transparency
        # im_dem = ax.imshow(
        #     dem_for_vis,
        #     cmap=ScientificStyle.ELEVATION_CMAP,
        #     aspect='equal',
        #     extent=extent,
        #     alpha=0.7,
        #     vmin=elevation_min, vmax=elevation_max
        # )
        
        # Overlay flood risk areas on Netherlands land only
        flood_overlay = np.full_like(flood_mask, np.nan, dtype=np.float32)
        flood_overlay[netherlands_mask & (flood_mask > 0)] = flood_mask[netherlands_mask & (flood_mask > 0)]
        
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
        # cbar_dem = self.create_standard_colorbar(im_dem, ax, 'Elevation (m)', shrink=0.6)
        # cbar_dem.ax.set_position([0.92, 0.15, 0.02, 0.3])
        
        # Flood risk colorbar (only if there are flooded areas)
        if np.any(flood_mask > 0):
            cbar_flood = self.create_standard_colorbar(im_flood, ax, 'Flood Risk', shrink=0.6)
            cbar_flood.ax.set_position([0.92, 0.55, 0.02, 0.3])
        
        # Add zone legend
        import matplotlib.patches as mpatches
        legend_patches = [
            mpatches.Patch(color=ScientificStyle.WATER_COLOR, label='Water Bodies'),
            mpatches.Patch(color=ScientificStyle.LAND_OUTSIDE_COLOR, label='Outside Netherlands')
        ]
        ax.legend(handles=legend_patches, loc='lower left', fontsize=8, frameon=True)
        
        # Add statistics for flood extent in Netherlands only
        if np.any(netherlands_mask):
            netherlands_flood_mask = flood_mask[netherlands_mask]
            flooded_pixels = np.sum(netherlands_flood_mask > 0.3)
            total_netherlands_pixels = np.sum(netherlands_mask)
            flood_percentage = (flooded_pixels / total_netherlands_pixels) * 100 if total_netherlands_pixels > 0 else 0
            
            stats_text = (
                f'Scenario: {scenario.name}\n'
                f'Sea Level Rise: {scenario.rise_meters}m\n'
                f'Flood Coverage (NL): {flood_percentage:.1f}%\n'
                f'Flooded Area (NL): {(flooded_pixels * 30 * 30) / 1000000:.2f} km^2'
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
                                layer_name: str, output_path: Optional[Path] = None,
                                land_mask: Optional[np.ndarray] = None) -> None:
        """Create standardized relevance layer visualization with proper zone separation."""
        fig, ax = plt.subplots(figsize=ScientificStyle.FIGURE_SIZE, dpi=ScientificStyle.DPI)
        
        extent = self.get_raster_extent(data, meta)
        
        # Create zone classification for background
        zones = self.create_zone_classification(data.shape, meta['transform'], land_mask)
        
        # Display base zones first
        zone_cmap = ScientificStyle.create_zone_colormap()
        ax.imshow(zones, cmap=zone_cmap, aspect='equal', extent=extent, 
                 vmin=ScientificStyle.WATER_VALUE, vmax=ScientificStyle.LAND_BASE_VALUE, alpha=1.0)
        
        # Create data overlay only for Netherlands land areas
        netherlands_mask = (zones == ScientificStyle.LAND_BASE_VALUE) & (~np.isnan(data))
        data_overlay = np.full_like(data, np.nan, dtype=np.float32)
        data_overlay[netherlands_mask] = data[netherlands_mask]
        
        # Overlay relevance data
        im = ax.imshow(
            data_overlay,
            cmap=ScientificStyle.RELEVANCE_CMAP,
            aspect='equal',
            extent=extent,
            vmin=0, vmax=1,
            alpha=0.85
        )
        
        # Add NUTS overlay
        nuts_gdf = self.get_nuts_boundaries("L3")
        if nuts_gdf is not None:
            self.add_nuts_overlay(ax, nuts_gdf)
        
        # Get proper layer title
        layer_titles = {
            'gdp': 'GDP Economic Relevance',
            'freight_loading': 'Freight Loading Economic Relevance',
            'freight_unloading': 'Freight Unloading Economic Relevance',
            'combined': 'Combined Economic Relevance'
        }
        
        title = layer_titles.get(layer_name, f'{layer_name.title()} Relevance Layer')
        
        # Styling
        ax.set_title(title, fontsize=ScientificStyle.TITLE_SIZE, fontweight='bold', pad=20)
        ax.set_xlabel('Easting (m)', fontsize=ScientificStyle.LABEL_SIZE)
        ax.set_ylabel('Northing (m)', fontsize=ScientificStyle.LABEL_SIZE)
        
        # Add colorbar for relevance data
        self.create_standard_colorbar(im, ax, 'Relevance Index (0-1)')
        
        # Add zone legend
        import matplotlib.patches as mpatches
        legend_patches = [
            mpatches.Patch(color=ScientificStyle.WATER_COLOR, label='Water Bodies'),
            mpatches.Patch(color=ScientificStyle.LAND_OUTSIDE_COLOR, label='Outside Netherlands')
        ]
        ax.legend(handles=legend_patches, loc='lower left', fontsize=8, frameon=True)
        
        # Add statistics for Netherlands areas only
        if np.any(netherlands_mask):
            netherlands_data = data[netherlands_mask]
            self.add_statistics_box(ax, netherlands_data, 'upper left')
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=ScientificStyle.DPI, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            logger.info(f"Saved {layer_name} relevance visualization to {output_path}")
        
        plt.close()

    def visualize_risk_layer(self, risk_data: np.ndarray, meta: dict,
                           scenario_title: str, output_path: Optional[Path] = None,
                           land_mask: Optional[np.ndarray] = None) -> None:
        """Create standardized risk layer visualization with proper zone separation and color mapping."""
        fig, ax = plt.subplots(figsize=ScientificStyle.FIGURE_SIZE, dpi=ScientificStyle.DPI)
        
        extent = self.get_raster_extent(risk_data, meta)
        
        # Create zone classification for background
        zones = self.create_zone_classification(risk_data.shape, meta['transform'], land_mask)
        
        # Display base zones first
        zone_cmap = ScientificStyle.create_zone_colormap()
        ax.imshow(zones, cmap=zone_cmap, aspect='equal', extent=extent, 
                 vmin=ScientificStyle.WATER_VALUE, vmax=ScientificStyle.LAND_BASE_VALUE, alpha=1.0)
        
        # Create data overlay only for Netherlands land areas
        netherlands_mask = (zones == ScientificStyle.LAND_BASE_VALUE) & (~np.isnan(risk_data)) & (risk_data > 0)
        data_overlay = np.full_like(risk_data, np.nan, dtype=np.float32)
        data_overlay[netherlands_mask] = risk_data[netherlands_mask]
        
        # Use a custom risk colormap that shows gradual risk 
        
        # Overlay risk data with proper visibility
        im = ax.imshow(
            data_overlay,
            cmap=ScientificStyle.HAZARD_CMAP,
            aspect='equal',
            extent=extent,
            vmin=0, vmax=1,
            alpha=0.9
        )
        
        # Add NUTS overlay
        nuts_gdf = self.get_nuts_boundaries("L3")
        if nuts_gdf is not None:
            self.add_nuts_overlay(ax, nuts_gdf)
        
        # Styling
        ax.set_title(f"Risk Assessment: {scenario_title}", 
                    fontsize=ScientificStyle.TITLE_SIZE, fontweight='bold', pad=20)
        ax.set_xlabel('Easting (m)', fontsize=ScientificStyle.LABEL_SIZE)
        ax.set_ylabel('Northing (m)', fontsize=ScientificStyle.LABEL_SIZE)
        
        # Add colorbar for risk data
        self.create_standard_colorbar(im, ax, 'Risk Index (0-1)')
        
        # Add zone legend
        import matplotlib.patches as mpatches
        legend_patches = [
            mpatches.Patch(color=ScientificStyle.WATER_COLOR, label='Water Bodies'),
            mpatches.Patch(color=ScientificStyle.LAND_OUTSIDE_COLOR, label='Outside Netherlands')
        ]
        ax.legend(handles=legend_patches, loc='lower left', fontsize=8, frameon=True)
        
        # Add statistics for Netherlands areas only
        if np.any(netherlands_mask):
            netherlands_data = data_overlay[netherlands_mask]
            self.add_statistics_box(ax, netherlands_data, 'upper left')
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=ScientificStyle.DPI, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            logger.info(f"Saved risk visualization to {output_path}")
        
        plt.close()

    def create_risk_summary_visualizations(self, risk_scenarios: Dict[str, np.ndarray], 
                                         meta: dict, land_mask: Optional[np.ndarray] = None,
                                         output_dir: Optional[Path] = None) -> None:
        """Create summary visualizations for all risk scenarios using current GDP levels."""
        logger.info("Creating risk summary visualizations...")
        
        if output_dir is None:
            output_dir = Path(".")
        
        # Create individual scenario plots
        for scenario_name, risk_data in risk_scenarios.items():
            scenario_title = f"{scenario_name} (Current GDP)"
            output_path = output_dir / f"risk_summary_{scenario_name}.png"
            
            self.visualize_risk_layer(
                risk_data=risk_data,
                meta=meta,
                scenario_title=scenario_title,
                output_path=output_path,
                land_mask=land_mask
            )
        
        logger.info("Risk summary visualizations complete")

    def create_zone_classification(self, data_shape: Tuple[int, int], transform: dict, 
                                  land_mask: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Create standardized zone classification for all layer visualizations.
        
        Args:
            data_shape: Shape of the data array (height, width)
            transform: Raster transform
            land_mask: Optional land mask array (1=land, 0=water)
            
        Returns:
            Zone classification array with values:
            - WATER_VALUE (0): Water bodies
            - OUTSIDE_NL_VALUE (1): Land outside Netherlands  
            - LAND_BASE_VALUE (2): Netherlands land
        """
        # Initialize zone classification
        zones = np.full(data_shape, ScientificStyle.LAND_BASE_VALUE, dtype=np.uint8)
        
        # Get NUTS boundaries for Netherlands
        nuts_gdf = self.get_nuts_boundaries("L3")
        
        if nuts_gdf is not None:
            import rasterio.features
            # Create NUTS mask
            nuts_mask = rasterio.features.rasterize(
                [(geom, 1) for geom in nuts_gdf.geometry],
                out_shape=data_shape,
                transform=transform,
                dtype=np.uint8
            )
            
            # Set areas outside Netherlands
            zones[nuts_mask == 0] = ScientificStyle.OUTSIDE_NL_VALUE
        
        # Set water areas if land mask is provided
        if land_mask is not None:
            zones[land_mask == 0] = ScientificStyle.WATER_VALUE
            
        return zones


def create_flood_composite_colormap():
    """Create standardized colormap for flood risk visualization."""
    colors = [
        ScientificStyle.WATER_COLOR,           # Water
        ScientificStyle.LAND_OUTSIDE_COLOR,    # Land outside study area
        ScientificStyle.SAFE_LAND_COLOR,       # Safe land
        ScientificStyle.FLOOD_RISK_COLOR       # Flood risk
    ]
    return ListedColormap(colors), BoundaryNorm([0, 1, 2, 3, 4], len(colors)) 