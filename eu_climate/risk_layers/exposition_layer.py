import rasterio
import rasterio.features
import rasterio.warp
import geopandas as gpd
from scipy import ndimage
from typing import Optional, Tuple, Dict
import numpy as np
from rasterio.enums import Resampling
from pathlib import Path
import logging
import matplotlib.pyplot as plt
import os
import pandas as pd

from eu_climate.config.config import ProjectConfig
from eu_climate.utils.utils import setup_logging, suppress_warnings
from eu_climate.utils.conversion import RasterTransformer
from eu_climate.utils.visualization import LayerVisualizer
from eu_climate.utils.normalise_data import DataNormalizer, AdvancedDataNormalizer, NormalizationStrategy, ensure_full_range_utilization
from eu_climate.utils.vierkant_processor import VierkantStatsProcessor
from eu_climate.utils.web_export_mixin import WebExportMixin


# Set up logging for the exposition layer
logger = setup_logging(__name__)


class ExpositionLayer(WebExportMixin):
    """
    Exposition Layer Implementation
    =============================
    
    Processes and analyzes exposure factors including:
    - Building Morphological Settlement Zone (MSZ) Delineation (GHS Built C) 
        - https://human-settlement.emergency.copernicus.eu/download.php?ds=builtC
        - Range: 0-25 | Explanation https://human-settlement.emergency.copernicus.eu/documents/GHSL_Data_Package_2023.pdf?t=1727170839
        - 2018, 10m Res, Cord System Mollweide, ESRI54009
    - Population density (GHS POP)
        - https://human-settlement.emergency.copernicus.eu/download.php?ds=pop
        - 2025, 100m Res, Cord System WGS84, EPSG:4326 
    - Building volume (GHS Built V) 
        - https://human-settlement.emergency.copernicus.eu/download.php?ds=builtV
        - 2025, 100m Res, Cord System Mollweide, ESRI54009
    - Degree of Urbanisation (GHS DUC) - Applied as Multiplier
        - Integrates Urban_share and SUrb_share from GHS_DUC_NL_Extract.xlsx
        - Uses GADM Level 2 administrative boundaries (gadm41_NLD_2.shp)
        - Formula: Urbanisation_Factor = 0.7 * Urban_share + 0.3 * SUrb_share
        - Applied as multiplier to boost exposition in urban areas:
          * Urban areas (≥0.6): 1.2x multiplier
          * Semi-urban areas (≥0.4, <0.6): 1.1x multiplier  
          * Rural areas (<0.4): 1.0x multiplier (no boost)
        - Rasterized to 30m resolution matching other layers
    - Port Infrastructure (PORT_RG_2009) - Applied as Multiplier
        - Loads port shapefile data and creates two zone types:
          * Port polygons (direct port areas): 1.8x multiplier
          * Port buffer zones (250m radius): 1.3x multiplier
        - Port polygons override buffer zones for higher multiplier effect
        - Combined with urbanisation multipliers for cumulative effect in overlapping areas
        - Rasterized to 30m resolution matching other layers
    """
    
    def __init__(self, config: ProjectConfig):
        """Initialize the Exposition Layer with project configuration."""
        super().__init__()
        self.config = config
        
        # Data paths
        self.ghs_built_c_path = self.config.ghs_built_c_path
        self.ghs_built_v_path = self.config.ghs_built_v_path
        self.population_path = self.config.population_2025_path
        self.electricity_consumption_path = self.config.electricity_consumption_path
        self.vierkant_stats_path = self.config.vierkant_stats_path
        self.nuts_paths = self.config.nuts_paths
        self.ghs_duc_path = self.config.ghs_duc_path
        self.gadm_l2_path = self.config.gadm_l2_path
        self.port_path = self.config.port_path
        
        # Initialize raster transformer
        self.transformer = RasterTransformer(
            target_crs=self.config.target_crs,
            config=self.config
        )
        
        # Initialize visualizer
        self.visualizer = LayerVisualizer(self.config)
        
        # Initialize vierkant stats processor
        self.vierkant_processor = VierkantStatsProcessor(self.config)
        
        # Initialize sophisticated normalizer optimized for exposition data
        self.normalizer = AdvancedDataNormalizer(NormalizationStrategy.EXPOSITION_OPTIMIZED)
        
        logger.info(f"Initialized Exposition Layer with urbanisation and port integration")
        


    def load_ghs_built_c(self):
        """Load the GHS Built C data.Transform to the target CRS from the config file."""""
        # The GHS BUILT C uses the 
        return self.ghs_built_c_path
    
    def load_ghs_built_v(self):
        """Load the GHS Built V data. Transform to the target CRS from the config file."""
        return self.ghs_built_v_path
    
    def load_population(self):
        """Load the population data.Transform to the target CRS from the config file."""
        return self.population_path
    
    def load_electricity_consumption(self):
        """Load the electricity consumption data. Transform to the target CRS from the config file."""
        return self.electricity_consumption_path
    
    def load_vierkant_stats(self):
        """Load the vierkant stats data. Transform to the target CRS from the config file."""
        return self.vierkant_stats_path
    
    def load_urbanisation_data(self) -> pd.DataFrame:
        """Load and process urbanisation data from Excel and GADM shapefiles.
        
        Calculates urbanisation multipliers based on thresholds:
        - Urban areas (≥ urban_threshold): get urban_multiplier boost (1.2)
        - Semi-urban areas (≥ semi_urban_threshold): get semi_urban_multiplier boost (1.1) 
        - Rural areas (< semi_urban_threshold): get rural_multiplier (1.0, no boost)
        """
        logger.info("Loading urbanisation data from Excel and GADM files")
        
        # Load Excel data
        excel_data = pd.read_excel(self.config.ghs_duc_path)
        logger.info(f"Loaded Excel data with {len(excel_data)} records")
        logger.info(f"Excel columns: {list(excel_data.columns)}")
        
        # Load GADM Level 2 shapefile
        gadm_gdf = gpd.read_file(self.config.gadm_l2_path)
        logger.info(f"Loaded GADM data with {len(gadm_gdf)} records")
        logger.info(f"GADM columns: {list(gadm_gdf.columns)}")
        
        # Merge data on GID_2
        merged_data = gadm_gdf.merge(excel_data, on='GID_2', how='inner')
        logger.info(f"Merged data has {len(merged_data)} records")
        
        if len(merged_data) == 0:
            raise ValueError("No matching GID_2 values found between Excel and GADM data")
        
        # Calculate urbanisation factor using the provided formula
        urbanisation_config = self.config.exposition_weights['urbanisation_multipliers']
        merged_data['urbanisation_factor'] = (
            urbanisation_config['urban_weight'] * merged_data['Urban_share'] +
            urbanisation_config['semi_urban_weight'] * merged_data['SUrb_share']
        )
        
        logger.info(f"Calculated urbanisation factor - Min: {merged_data['urbanisation_factor'].min():.4f}, "
                   f"Max: {merged_data['urbanisation_factor'].max():.4f}, "
                   f"Mean: {merged_data['urbanisation_factor'].mean():.4f}")
        
        # Apply threshold-based multipliers
        urban_threshold = urbanisation_config['urban_threshold']
        semi_urban_threshold = urbanisation_config['semi_urban_threshold']
        urban_multiplier = urbanisation_config['urban_multiplier']
        semi_urban_multiplier = urbanisation_config['semi_urban_multiplier']
        rural_multiplier = urbanisation_config['rural_multiplier']
        
        # Classify areas and assign multipliers
        conditions = [
            merged_data['urbanisation_factor'] >= urban_threshold,
            merged_data['urbanisation_factor'] >= semi_urban_threshold,
            merged_data['urbanisation_factor'] < semi_urban_threshold
        ]
        choices = [urban_multiplier, semi_urban_multiplier, rural_multiplier]
        
        merged_data['urbanisation_multiplier'] = np.select(conditions, choices, default=rural_multiplier)
        
        # Log classification results
        urban_count = (merged_data['urbanisation_factor'] >= urban_threshold).sum()
        semi_urban_count = ((merged_data['urbanisation_factor'] >= semi_urban_threshold) & 
                           (merged_data['urbanisation_factor'] < urban_threshold)).sum()
        rural_count = (merged_data['urbanisation_factor'] < semi_urban_threshold).sum()
        
        logger.info(f"Area classification:")
        logger.info(f"  Urban areas (>={urban_threshold}): {urban_count} ({urban_count/len(merged_data)*100:.1f}%) - Multiplier: {urban_multiplier}")
        logger.info(f"  Semi-urban areas (>={semi_urban_threshold}, <{urban_threshold}): {semi_urban_count} ({semi_urban_count/len(merged_data)*100:.1f}%) - Multiplier: {semi_urban_multiplier}")
        logger.info(f"  Rural areas (<{semi_urban_threshold}): {rural_count} ({rural_count/len(merged_data)*100:.1f}%) - Multiplier: {rural_multiplier}")
        
        logger.info(f"Urbanisation multipliers - Min: {merged_data['urbanisation_multiplier'].min():.1f}, "
                   f"Max: {merged_data['urbanisation_multiplier'].max():.1f}, "
                   f"Mean: {merged_data['urbanisation_multiplier'].mean():.2f}")
        
        return merged_data
    
    def rasterize_urbanisation_multiplier(self, urbanisation_gdf: pd.DataFrame) -> Tuple[np.ndarray, dict]:
        """Rasterize the urbanisation multiplier to target resolution using NUTS-L3 bounds."""
        logger.info("Rasterizing urbanisation multiplier to target resolution")
        
        # Get reference bounds from NUTS-L3 for consistency
        nuts_l3_path = self.config.data_dir / "NUTS-L3-NL.shp"
        reference_bounds = self.transformer.get_reference_bounds(nuts_l3_path)
        
        # Ensure GDF is in target CRS
        target_crs = rasterio.crs.CRS.from_string(self.config.target_crs)
        if urbanisation_gdf.crs != target_crs:
            urbanisation_gdf = urbanisation_gdf.to_crs(target_crs)
        
        # Calculate raster dimensions
        # reference_bounds is a tuple: (left, bottom, right, top)
        left, bottom, right, top = reference_bounds
        resolution = self.config.target_resolution
        width = int((right - left) / resolution)
        height = int((top - bottom) / resolution)
        
        # Create transform
        transform = rasterio.transform.from_bounds(
            left, bottom, right, top,
            width, height
        )
        
        # Rasterize urbanisation multiplier (default to 1.0 for areas without data)
        urbanisation_raster = rasterio.features.rasterize(
            [(geom, value) for geom, value in zip(urbanisation_gdf.geometry, urbanisation_gdf['urbanisation_multiplier'])],
            out_shape=(height, width),
            transform=transform,
            dtype=np.float32,
            fill=1.0  # Default multiplier of 1.0 (no boost) for areas without data
        )
        
        logger.info(f"Rasterized urbanisation multiplier - Min: {np.nanmin(urbanisation_raster):.2f}, "
                   f"Max: {np.nanmax(urbanisation_raster):.2f}, "
                   f"Mean: {np.nanmean(urbanisation_raster):.2f}")
        
        # Create metadata
        meta = {
            'crs': target_crs,
            'transform': transform,
            'height': height,
            'width': width,
            'dtype': 'float32'
        }
        
        return urbanisation_raster, meta
    
    def load_port_data(self) -> gpd.GeoDataFrame:
        """Load and process port data from shapefile, clipped to study area.
        
        Creates two zone types:
        - Port polygons (direct port areas): get port_polygon_multiplier boost (1.8)
        - Port buffer zones (250m radius): get port_buffer_multiplier boost (1.3)
        """
        logger.info("Loading port data from shapefile")
        
        # Load port shapefile
        port_gdf = gpd.read_file(self.config.port_path)
        logger.info(f"Loaded port data with {len(port_gdf)} records")
        logger.info(f"Port columns: {list(port_gdf.columns)}")
        
        # Ensure port data is in target CRS
        target_crs = rasterio.crs.CRS.from_string(self.config.target_crs)
        if port_gdf.crs != target_crs:
            port_gdf = port_gdf.to_crs(target_crs)
            logger.info(f"Transformed port data to {target_crs}")
        
        # Load NUTS-L3 boundaries to define study area
        nuts_l3_path = self.config.data_dir / "NUTS-L3-NL.shp"
        try:
            nuts_gdf = gpd.read_file(nuts_l3_path)
            logger.info(f"Loaded NUTS-L3 boundaries with {len(nuts_gdf)} regions")
            
            # Ensure NUTS is in target CRS
            if nuts_gdf.crs != target_crs:
                nuts_gdf = nuts_gdf.to_crs(target_crs)
                logger.info(f"Transformed NUTS boundaries to {target_crs}")
            
            # Create study area boundary (union of all NUTS regions)
            study_area = nuts_gdf.geometry.unary_union
            
            # Clip ports to study area (keep ports that intersect with study area)
            ports_in_study_area = port_gdf[port_gdf.geometry.intersects(study_area)]
            logger.info(f"Clipped to study area: {len(ports_in_study_area)} ports within Netherlands boundaries (from {len(port_gdf)} total)")
            
            if len(ports_in_study_area) == 0:
                logger.warning("No ports found within the study area boundaries")
                # Return empty GeoDataFrame with required columns
                empty_gdf = gpd.GeoDataFrame(columns=['geometry', 'multiplier', 'zone_type'], crs=target_crs)
                return empty_gdf
            
            port_gdf = ports_in_study_area
            
        except Exception as e:
            logger.warning(f"Could not load NUTS boundaries for port clipping: {e}")
            logger.warning("Proceeding with all ports (no clipping)")
        
        # Get port configuration
        port_config = self.config.exposition_weights['port_multipliers']
        buffer_distance = port_config['port_buffer_distance_m']
        port_polygon_multiplier = port_config['port_polygon_multiplier']
        port_buffer_multiplier = port_config['port_buffer_multiplier']
        
        # Create buffer zones around ports
        port_buffers = port_gdf.copy()
        port_buffers['geometry'] = port_gdf.geometry.buffer(buffer_distance)
        port_buffers['multiplier'] = port_buffer_multiplier
        port_buffers['zone_type'] = 'buffer'
        
        # Original port polygons (these will override buffer zones)
        port_polygons = port_gdf.copy()
        port_polygons['multiplier'] = port_polygon_multiplier
        port_polygons['zone_type'] = 'polygon'
        
        logger.info(f"Created {len(port_buffers)} port buffer zones ({buffer_distance}m radius) - Multiplier: {port_buffer_multiplier}")
        logger.info(f"Created {len(port_polygons)} port polygon zones - Multiplier: {port_polygon_multiplier}")
        
        # Combine both zone types (polygons will be processed after buffers to override)
        combined_port_zones = pd.concat([port_buffers, port_polygons], ignore_index=True)
        
        logger.info(f"Total port zones created: {len(combined_port_zones)} (within study area)")
        
        return combined_port_zones
    
    def rasterize_port_multiplier(self, port_gdf: gpd.GeoDataFrame) -> Tuple[np.ndarray, dict]:
        """Rasterize the port multiplier to target resolution using NUTS-L3 bounds."""
        logger.info("Rasterizing port multiplier to target resolution")
        
        # Get reference bounds from NUTS-L3 for consistency
        nuts_l3_path = self.config.data_dir / "NUTS-L3-NL.shp"
        reference_bounds = self.transformer.get_reference_bounds(nuts_l3_path)
        
        # Ensure GDF is in target CRS
        target_crs = rasterio.crs.CRS.from_string(self.config.target_crs)
        if len(port_gdf) > 0 and port_gdf.crs != target_crs:
            port_gdf = port_gdf.to_crs(target_crs)
        
        # Calculate raster dimensions
        left, bottom, right, top = reference_bounds
        resolution = self.config.target_resolution
        width = int((right - left) / resolution)
        height = int((top - bottom) / resolution)
        
        # Create transform
        transform = rasterio.transform.from_bounds(
            left, bottom, right, top,
            width, height
        )
        
        # Handle case where no ports are in study area
        if len(port_gdf) == 0:
            logger.info("No ports in study area - creating default multiplier raster (all 1.0)")
            port_raster = np.ones((height, width), dtype=np.float32)
        else:
            # Initialize with default multiplier
            port_raster = np.ones((height, width), dtype=np.float32)
            
            # First rasterize buffer zones with proper overlap handling
            buffer_zones = port_gdf[port_gdf['zone_type'] == 'buffer']
            if len(buffer_zones) > 0:
                # For overlapping buffers, use merge_alg='replace' to handle overlaps
                # This will use the last (highest) value where buffers overlap
                buffer_raster = rasterio.features.rasterize(
                    [(geom, value) for geom, value in zip(buffer_zones.geometry, buffer_zones['multiplier'])],
                    out_shape=(height, width),
                    transform=transform,
                    dtype=np.float32,
                    fill=0.0,  # Use 0 to identify areas without buffers
                    merge_alg=rasterio.enums.MergeAlg.replace
                )
                
                # Apply buffer multipliers where they exist, keeping max value for overlaps
                port_raster = np.maximum(port_raster, buffer_raster)
                
                # Log buffer overlap statistics
                buffer_pixels = np.sum(buffer_raster > 1.0)
                logger.info(f"Buffer zones applied to {buffer_pixels} pixels")
            
            # Then rasterize port polygons (these will override everything)
            port_polygons = port_gdf[port_gdf['zone_type'] == 'polygon']
            if len(port_polygons) > 0:
                polygon_raster = rasterio.features.rasterize(
                    [(geom, value) for geom, value in zip(port_polygons.geometry, port_polygons['multiplier'])],
                    out_shape=(height, width),
                    transform=transform,
                    dtype=np.float32,
                    fill=0.0,  # Use 0 to identify areas without port polygons
                    merge_alg=rasterio.enums.MergeAlg.replace
                )
                
                # Apply polygon multipliers where they exist (override buffer and default values)
                port_raster = np.where(polygon_raster > 0, polygon_raster, port_raster)
                
                # Log polygon statistics
                polygon_pixels = np.sum(polygon_raster > 0)
                logger.info(f"Port polygons applied to {polygon_pixels} pixels (override buffers)")
            
            # Log final precedence application
            final_buffer_pixels = np.sum((port_raster > 1.0) & (port_raster < port_gdf[port_gdf['zone_type'] == 'polygon']['multiplier'].iloc[0] if len(port_polygons) > 0 else 2.0))
            final_polygon_pixels = np.sum(port_raster >= port_gdf[port_gdf['zone_type'] == 'polygon']['multiplier'].iloc[0]) if len(port_polygons) > 0 else 0
            
            logger.info(f"Final port precedence - Buffer pixels: {final_buffer_pixels}, Polygon pixels: {final_polygon_pixels}")
        
        logger.info(f"Rasterized port multiplier - Min: {np.nanmin(port_raster):.2f}, "
                   f"Max: {np.nanmax(port_raster):.2f}, "
                   f"Mean: {np.nanmean(port_raster):.2f}")
        
        # Overall coverage summary
        if len(port_gdf) == 0:
            logger.info("Port coverage - No ports in study area, using default multiplier everywhere")
        else:
            total_affected_pixels = np.sum(port_raster > 1.0)
            total_pixels = port_raster.size
            coverage_percentage = (total_affected_pixels / total_pixels) * 100
            logger.info(f"Port coverage - {total_affected_pixels} pixels affected ({coverage_percentage:.2f}% of study area)")
            logger.info("Port precedence system applied: Port polygons > Buffer zones > Default (1.0)")
        
        # Create metadata
        meta = {
            'crs': target_crs,
            'transform': transform,
            'height': height,
            'width': width,
            'dtype': 'float32'
        }
        
        return port_raster, meta
    

    def load_and_preprocess_raster(self, path: str) -> Tuple[np.ndarray, dict]:
        """Load and preprocess a single raster to target resolution and CRS using NUTS-L3 bounds."""
        logger.info(f"Loading raster: {path}")
        
        # Get reference bounds from NUTS-L3 instead of NUTS-L0 for consistency with relevance layer
        nuts_l3_path = self.config.data_dir / "NUTS-L3-NL.shp"
        reference_bounds = self.transformer.get_reference_bounds(nuts_l3_path)
        
        # Transform raster
        resampling_method_str = (self.config.resampling_method.name.lower() 
                               if hasattr(self.config.resampling_method, 'name') 
                               else str(self.config.resampling_method).lower())
        
        data, transform, crs = self.transformer.transform_raster(
            path,
            reference_bounds=reference_bounds,
            resampling_method=resampling_method_str
        )
        
        # Create metadata
        meta = {
            'crs': crs,
            'transform': transform,
            'height': data.shape[0],
            'width': data.shape[1],
            'dtype': 'float32'
        }
        
        return data, meta

    def normalize_ghs_built_c(self, data: np.ndarray) -> np.ndarray:
        """Normalize GHS Built-C using config-driven class weights."""
        class_weights = self.config.ghs_built_c_class_weights
        max_class = int(np.nanmax(data))
        lookup = np.zeros(max_class + 1)
        for k, v in class_weights.items():
            lookup[int(k)] = v
        normalized = lookup[data.astype(int)]
        logger.info(f"GHS Built-C normalization - Min: {np.nanmin(normalized)}, Max: {np.nanmax(normalized)}, Mean: {np.nanmean(normalized)}")
        return normalized

    def normalize_raster(self, data: np.ndarray) -> np.ndarray:
        """Normalize a raster ensuring sophisticated exposition optimization."""
        valid_mask = ~np.isnan(data)
        return self.normalizer.normalize_exposition_data(data, valid_mask)

    def calculate_exposition(self) -> Tuple[np.ndarray, dict]:
        """Calculate the final exposition layer using weighted combination."""
        return self.calculate_exposition_with_weights(self.config.exposition_weights)

    def calculate_exposition_with_weights(self, weights: Dict[str, float]) -> Tuple[np.ndarray, dict]:
        """Calculate exposition layer using custom weights."""
        ghs_built_c, meta = self.load_and_preprocess_raster(self.ghs_built_c_path)
        logger.info(f"GHS Built-C after preprocessing - Min: {np.nanmin(ghs_built_c)}, Max: {np.nanmax(ghs_built_c)}, Mean: {np.nanmean(ghs_built_c)}")
        
        reference_transform = meta['transform']
        reference_crs = meta['crs']
        reference_shape = ghs_built_c.shape
        
        ghs_built_v, _ = self.load_and_preprocess_raster(self.ghs_built_v_path)
        logger.info(f"GHS Built-V after preprocessing - Min: {np.nanmin(ghs_built_v)}, Max: {np.nanmax(ghs_built_v)}, Mean: {np.nanmean(ghs_built_v)}")
        
        # Use corrected 2025 population loading with proper resolution handling
        from ..utils.data_loading import load_population_2025_with_validation
        population, _, validation_passed = load_population_2025_with_validation(
            config=self.config,
            apply_study_area_mask=True
        )
        logger.info(f"Loaded 2025 population data with validation: {validation_passed}")
        logger.info(f"Population after preprocessing - Min: {np.nanmin(population)}, Max: {np.nanmax(population)}, Mean: {np.nanmean(population)}")
        
        electricity_consumption, _ = self.load_and_preprocess_raster(self.electricity_consumption_path)
        logger.info(f"Electricity consumption after preprocessing - Min: {np.nanmin(electricity_consumption)}, Max: {np.nanmax(electricity_consumption)}, Mean: {np.nanmean(electricity_consumption)}")
        
        vierkant_stats, vierkant_meta = self.load_and_preprocess_vierkant_stats()
        logger.info(f"Vierkant stats after preprocessing - Min: {np.nanmin(vierkant_stats)}, Max: {np.nanmax(vierkant_stats)}, Mean: {np.nanmean(vierkant_stats)}")
        
        urbanisation_gdf = self.load_urbanisation_data()
        urbanisation_multiplier, urbanisation_meta = self.rasterize_urbanisation_multiplier(urbanisation_gdf)
        logger.info(f"Urbanisation multiplier after rasterization - Min: {np.nanmin(urbanisation_multiplier):.2f}, Max: {np.nanmax(urbanisation_multiplier):.2f}, Mean: {np.nanmean(urbanisation_multiplier):.2f}")
        
        port_gdf = self.load_port_data()
        port_multiplier, port_meta = self.rasterize_port_multiplier(port_gdf)
        logger.info(f"Port multiplier after rasterization - Min: {np.nanmin(port_multiplier):.2f}, Max: {np.nanmax(port_multiplier):.2f}, Mean: {np.nanmean(port_multiplier):.2f}")
        
        resampling_method_str = (self.config.resampling_method.name.lower() 
                               if hasattr(self.config.resampling_method, 'name') 
                               else str(self.config.resampling_method).lower())
        
        if not self.transformer.validate_alignment(ghs_built_v, meta['transform'], ghs_built_c, reference_transform):
            ghs_built_v = self.transformer.ensure_alignment(
                ghs_built_v,
                meta['transform'],
                reference_transform,
                reference_shape,
                resampling_method_str
            )
            logger.info(f"GHS Built-V after reprojection - Min: {np.nanmin(ghs_built_v)}, Max: {np.nanmax(ghs_built_v)}, Mean: {np.nanmean(ghs_built_v)}")
            
        if not self.transformer.validate_alignment(population, meta['transform'], ghs_built_c, reference_transform):
            population = self.transformer.ensure_alignment(
                population,
                meta['transform'],
                reference_transform,
                reference_shape,
                resampling_method_str
            )
            logger.info(f"Population after reprojection - Min: {np.nanmin(population)}, Max: {np.nanmax(population)}, Mean: {np.nanmean(population)}")
        
        if not self.transformer.validate_alignment(electricity_consumption, meta['transform'], ghs_built_c, reference_transform):
            electricity_consumption = self.transformer.ensure_alignment(
                electricity_consumption,
                meta['transform'],
                reference_transform,
                reference_shape,
                resampling_method_str
            )
            logger.info(f"Electricity consumption after reprojection - Min: {np.nanmin(electricity_consumption)}, Max: {np.nanmax(electricity_consumption)}, Mean: {np.nanmean(electricity_consumption)}")
        
        # Ensure vierkant stats alignment with reference
        if not self.transformer.validate_alignment(vierkant_stats, vierkant_meta['transform'], ghs_built_c, reference_transform):
            vierkant_stats = self.transformer.ensure_alignment(
                vierkant_stats,
                vierkant_meta['transform'],
                reference_transform,
                reference_shape,
                resampling_method_str
            )
            logger.info(f"Vierkant stats after reprojection - Min: {np.nanmin(vierkant_stats)}, Max: {np.nanmax(vierkant_stats)}, Mean: {np.nanmean(vierkant_stats)}")
        
        # Ensure urbanisation multiplier has the same shape and transform
        if not self.transformer.validate_alignment(urbanisation_multiplier, urbanisation_meta['transform'], ghs_built_c, reference_transform):
            urbanisation_multiplier = self.transformer.ensure_alignment(
                urbanisation_multiplier,
                urbanisation_meta['transform'],
                reference_transform,
                reference_shape,
                resampling_method_str
            )
            logger.info(f"Urbanisation multiplier after reprojection - Min: {np.nanmin(urbanisation_multiplier):.2f}, Max: {np.nanmax(urbanisation_multiplier):.2f}, Mean: {np.nanmean(urbanisation_multiplier):.2f}")
        
        # Ensure port multiplier has the same shape and transform
        if not self.transformer.validate_alignment(port_multiplier, port_meta['transform'], ghs_built_c, reference_transform):
            port_multiplier = self.transformer.ensure_alignment(
                port_multiplier,
                port_meta['transform'],
                reference_transform,
                reference_shape,
                resampling_method_str
            )
            logger.info(f"Port multiplier after reprojection - Min: {np.nanmin(port_multiplier):.2f}, Max: {np.nanmax(port_multiplier):.2f}, Mean: {np.nanmean(port_multiplier):.2f}")
        
        # Check for valid data
        if np.all(ghs_built_c == 0) or np.all(ghs_built_v == 0) or np.all(population == 0) or np.all(electricity_consumption == 0) or np.all(vierkant_stats == 0):
            logger.error("One or more input layers contain only zeros!")
            raise ValueError("Invalid input data: one or more layers contain only zeros")
        
        # Normalize base layers
        norm_built_c = self.normalize_ghs_built_c(ghs_built_c)
        norm_built_v = self.normalize_raster(ghs_built_v)
        norm_population = self.normalize_raster(population)
        norm_electricity_consumption = self.normalize_raster(electricity_consumption)
        norm_vierkant_stats = self.normalize_raster(vierkant_stats)
        
        # Check normalized data
        if np.all(norm_built_c == 0) or np.all(norm_built_v == 0) or np.all(norm_population == 0) or np.all(norm_electricity_consumption == 0) or np.all(norm_vierkant_stats == 0):
            logger.error("One or more normalized layers contain only zeros!")
            raise ValueError("Invalid normalized data: one or more layers contain only zeros")
        
        # Weighted sum using provided weights
        exposition = (
            weights['ghs_built_c_weight'] * norm_built_c +
            weights['ghs_built_v_weight'] * norm_built_v +
            weights['population_weight'] * norm_population +
            weights['electricity_consumption_weight'] * norm_electricity_consumption +
            weights['vierkant_stats_weight'] * norm_vierkant_stats
        )
        logger.info(f"Base exposition - Min: {np.nanmin(exposition):.4f}, Max: {np.nanmax(exposition):.4f}, Mean: {np.nanmean(exposition):.4f}")
        
        # Apply urbanisation and port multipliers
        # Combine multipliers: areas with both get cumulative effect, others get individual effect
        combined_multiplier = urbanisation_multiplier * port_multiplier
        exposition = exposition * combined_multiplier
        logger.info(f"Final exposition with urbanisation and port multipliers - Min: {np.nanmin(exposition):.4f}, Max: {np.nanmax(exposition):.4f}, Mean: {np.nanmean(exposition):.4f}")
        
        # Log multiplier effect breakdown
        urban_only_pixels = np.sum((urbanisation_multiplier > 1.0) & (port_multiplier == 1.0))
        port_only_pixels = np.sum((urbanisation_multiplier == 1.0) & (port_multiplier > 1.0))
        both_pixels = np.sum((urbanisation_multiplier > 1.0) & (port_multiplier > 1.0))
        logger.info(f"Multiplier coverage - Urban only: {urban_only_pixels} pixels, Port only: {port_only_pixels} pixels, Both: {both_pixels} pixels")
        
        # Check final exposition
        if np.all(exposition == 0):
            logger.error("Final exposition layer contains only zeros!")
            raise ValueError("Invalid exposition layer: contains only zeros")
        
        # Optional smoothing
        if self.config.smoothing_sigma > 0:
            exposition = ndimage.gaussian_filter(exposition, sigma=self.config.smoothing_sigma)
            logger.info(f"Exposition after smoothing - Min: {np.nanmin(exposition)}, Max: {np.nanmax(exposition)}, Mean: {np.nanmean(exposition)}")
            
            # Check smoothed exposition
            if np.all(exposition == 0):
                logger.error("Smoothed exposition layer contains only zeros!")
                raise ValueError("Invalid smoothed exposition layer: contains only zeros")
        
        # Apply study area mask to limit data to relevant landmass
        exposition = self._apply_study_area_mask(exposition, reference_transform, reference_shape)
        logger.info(f"Exposition after study area masking - Min: {np.nanmin(exposition)}, Max: {np.nanmax(exposition)}, Mean: {np.nanmean(exposition)}")
        
        # Apply final normalization to ensure full 0-1 range utilization after multipliers
        study_area_mask = exposition > 0
        exposition = ensure_full_range_utilization(exposition, study_area_mask)
        logger.info(f"Final exposition after full range normalization - Min: {np.nanmin(exposition)}, Max: {np.nanmax(exposition)}, Mean: {np.nanmean(exposition)}")
            
        return exposition, meta

    def save_exposition_layer(self, data: np.ndarray, meta: dict, out_path: str, create_web_formats: bool = True):
        """Save the final exposition layer as GeoTIFF and web-optimized formats."""
        if os.path.exists(out_path):
            logger.info(f"Removing existing file at {out_path} before writing new output.")
            os.remove(out_path)
        vrt_path = os.path.splitext(out_path)[0] + '.vrt'
        if os.path.exists(vrt_path):
            logger.info(f"Removing existing VRT file at {vrt_path} before writing new output.")
            os.remove(vrt_path)
            
        # Ensure data is in valid range and not all zeros
        if np.all(data == 0):
            logger.warning("All values in the exposition layer are zero!")
            return
            
        # Log original statistics before any clipping
        original_min, original_max, original_mean = np.nanmin(data), np.nanmax(data), np.nanmean(data)
        logger.info(f"Original data statistics - Min: {original_min:.4f}, Max: {original_max:.4f}, Mean: {original_mean:.4f}")
        
        # Only clip negative values, preserve multiplier effects by allowing values > 1
        data = np.clip(data, 0, None)
        final_min, final_max, final_mean = np.nanmin(data), np.nanmax(data), np.nanmean(data)
        logger.info(f"Data before saving (after clipping negatives) - Min: {final_min:.4f}, Max: {final_max:.4f}, Mean: {final_mean:.4f}")
        
        # Extract layer name from file path
        layer_name = Path(out_path).stem
        
        # Use the web export mixin to save both legacy and web formats
        results = self.save_raster_with_web_exports(
            data=data,
            meta=meta,
            output_path=out_path,
            layer_name=layer_name,
            create_web_formats=create_web_formats
        )
        
        if results.get('geotiff', False):
            logger.info(f"Successfully wrote exposition layer to {out_path}")
        if results.get('cog', False):
            logger.info(f"Created web-optimized COG for exposition layer")
        
        return results

    def visualize_exposition(self, exposition: np.ndarray, meta: dict, title: str = "Exposition Layer", show_ports: bool = False, show_port_buffers: bool = False):
        """Visualize the exposition index for each cell using unified styling."""
        output_path = Path(self.config.output_dir) / "exposition" / "exposition_layer.png"
        
        # Load land mask for proper water/land separation  
        land_mask = None
        try:
            with rasterio.open(self.config.land_mass_path) as src:
                # Transform land mask to match exposition layer resolution and extent
                if meta and 'transform' in meta:
                    land_mask, _ = rasterio.warp.reproject(
                        source=src.read(1),
                        destination=np.zeros((meta['height'], meta['width']), dtype=np.uint8),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=meta['transform'],
                        dst_crs=meta['crs'],
                        resampling=rasterio.enums.Resampling.nearest
                    )
                    # Ensure proper data type (1=land, 0=water)
                    land_mask = (land_mask > 0).astype(np.uint8)
                    logger.info("Loaded and transformed land mask for exposition visualization")
                else:
                    logger.warning("No metadata available for land mask transformation")
        except Exception as e:
            logger.warning(f"Could not load land mask for exposition visualization: {e}")
        
        self.visualizer.visualize_exposition_layer(
            data=exposition,
            meta=meta,
            output_path=output_path,
            title=title,
            land_mask=land_mask,
            show_ports=show_ports,
            show_port_buffers=show_port_buffers
        )

    def export_exposition(self, data: np.ndarray, meta: dict, out_path: str):
        """Export the exposition index for each cell to a specified GeoTIFF path."""
        meta.update({'dtype': 'float32', 'count': 1})
        with rasterio.open(out_path, 'w', **meta) as dst:
            dst.write(data.astype(np.float32), 1)
        logger.info(f"Exposition layer exported to {out_path}")

    def create_economic_exposition_layer(self, economic_identifier: str, weights: Dict[str, float]) -> Tuple[np.ndarray, dict]:
        """Create an exposition layer for a specific economic dataset using custom weights."""
        logger.info(f"Creating exposition layer for {economic_identifier} with weights: {weights}")
        return self.calculate_exposition_with_weights(weights)

    def save_economic_exposition_layers(self):
        """Create and save all economic-specific exposition layers based on config."""
        logger.info("Creating economic-specific exposition layers")
        
        # Get economic exposition weights from config
        economic_weights = self.config.economic_exposition_weights
        
        for economic_identifier, weights in economic_weights.items():
            logger.info(f"Processing exposition layer for {economic_identifier}")
            
            # Create exposition layer with custom weights
            exposition_data, meta = self.create_economic_exposition_layer(economic_identifier, weights)
            
            # Define output paths
            tif_output_dir = Path(self.config.output_dir) / "exposition" / "tif"
            png_output_dir = Path(self.config.output_dir) / "exposition"
            tif_output_dir.mkdir(parents=True, exist_ok=True)
            png_output_dir.mkdir(parents=True, exist_ok=True)
            
            # Save TIF file
            tif_path = tif_output_dir / f"exposition_{economic_identifier}.tif"
            self.save_exposition_layer(exposition_data, meta, str(tif_path))
            logger.info(f"Saved {economic_identifier} exposition layer TIF to {tif_path}")
            
            # Create PNG visualization
            png_path = png_output_dir / f"exposition_{economic_identifier}.png"
            
            # Load land mask for proper water/land separation  
            land_mask = None
            try:
                with rasterio.open(self.config.land_mass_path) as src:
                    # Transform land mask to match exposition layer resolution and extent
                    if meta and 'transform' in meta:
                        land_mask, _ = rasterio.warp.reproject(
                            source=src.read(1),
                            destination=np.zeros((meta['height'], meta['width']), dtype=np.uint8),
                            src_transform=src.transform,
                            src_crs=src.crs,
                            dst_transform=meta['transform'],
                            dst_crs=meta['crs'],
                            resampling=rasterio.enums.Resampling.nearest
                        )
                        # Ensure proper data type (1=land, 0=water)
                        land_mask = (land_mask > 0).astype(np.uint8)
                        logger.info(f"Loaded and transformed land mask for {economic_identifier} exposition visualization")
                    else:
                        logger.warning("No metadata available for land mask transformation")
            except Exception as e:
                logger.warning(f"Could not load land mask for {economic_identifier} exposition visualization: {e}")
            
            # Create visualization with economic identifier in title
            self.visualizer.visualize_exposition_layer(
                data=exposition_data,
                meta=meta,
                output_path=png_path,
                title=f"Exposition Layer - {economic_identifier.upper()}",
                land_mask=land_mask
            )
            
            logger.info(f"Saved {economic_identifier} exposition layer PNG to {png_path}")

    def run_exposition(self, visualize: bool = False, create_png: bool = True, show_ports: bool = False, show_port_buffers: bool = False):
        """Main execution flow for the exposition layer."""
        # Create default exposition layer
        exposition, meta = self.calculate_exposition()
        out_path = Path(self.config.output_dir) /"exposition" / "tif" / 'exposition_layer.tif'
        out_path.parent.mkdir(parents=True, exist_ok=True)

        self.save_exposition_layer(exposition, meta, out_path)
        logger.info(f"Default exposition layer saved to {out_path}")
        
        # Create PNG visualization for default layer
        if create_png or visualize:
            png_path = Path(self.config.output_dir) / "exposition" / 'exposition_layer.png'
            
            # Load land mask for proper water/land separation  
            land_mask = None
            try:
                with rasterio.open(self.config.land_mass_path) as src:
                    # Transform land mask to match exposition layer resolution and extent
                    if meta and 'transform' in meta:
                        land_mask, _ = rasterio.warp.reproject(
                            source=src.read(1),
                            destination=np.zeros((meta['height'], meta['width']), dtype=np.uint8),
                            src_transform=src.transform,
                            src_crs=src.crs,
                            dst_transform=meta['transform'],
                            dst_crs=meta['crs'],
                            resampling=rasterio.enums.Resampling.nearest
                        )
                        # Ensure proper data type (1=land, 0=water)
                        land_mask = (land_mask > 0).astype(np.uint8)
                        logger.info("Loaded and transformed land mask for default exposition PNG")
                    else:
                        logger.warning("No metadata available for land mask transformation")
            except Exception as e:
                logger.warning(f"Could not load land mask for default exposition PNG: {e}")
            
            self.visualizer.visualize_exposition_layer(
                data=exposition,
                meta=meta,
                output_path=png_path,
                title="Exposition Layer",
                land_mask=land_mask,
                show_ports=show_ports,
                show_port_buffers=show_port_buffers
            )
            logger.info(f"Default exposition layer PNG saved to {png_path}")
        
        # Create all economic-specific exposition layers
        self.save_economic_exposition_layers()

    def run_exposition_with_all_economic_layers(self, visualize: bool = False, create_png: bool = True, show_ports: bool = False, show_port_buffers: bool = False):
        """Run exposition layer creation including all economic-specific layers."""
        logger.info("Creating default exposition layer and all economic-specific exposition layers")
        self.run_exposition(visualize=visualize, create_png=create_png, show_ports=show_ports, show_port_buffers= show_port_buffers)

    def _apply_study_area_mask(self, exposition: np.ndarray, transform: rasterio.Affine, shape: Tuple[int, int]) -> np.ndarray:
        """Apply study area mask using NUTS boundaries and land mass data."""
        logger.info("Applying study area mask to exposition layer...")
        
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
                dtype=np.uint8
            )
            logger.info(f"Created NUTS mask: {np.sum(nuts_mask)} pixels within NUTS boundaries")
            
            # Load and align land mass data
            resampling_method_str = (self.config.resampling_method.name.lower() 
                                   if hasattr(self.config.resampling_method, 'name') 
                                   else str(self.config.resampling_method).lower())
            
            land_mass_data, land_transform, _ = self.transformer.transform_raster(
                self.config.land_mass_path,
                reference_bounds=self.transformer.get_reference_bounds(nuts_l3_path),
                resampling_method=resampling_method_str
            )
            
            # Ensure land mass data is aligned with exposition layer
            if not self.transformer.validate_alignment(land_mass_data, land_transform, exposition, transform):
                land_mass_data = self.transformer.ensure_alignment(
                    land_mass_data, land_transform, transform, shape,
                    resampling_method_str
                )
            
            # Create land mask (1=land, 0=water/no data)
            land_mask = (land_mass_data > 0).astype(np.uint8)
            logger.info(f"Created land mask: {np.sum(land_mask)} pixels identified as land")
            
            # Combine masks: only areas that are both within NUTS and on land
            combined_mask = (nuts_mask == 1) & (land_mask == 1)
            logger.info(f"Combined study area mask: {np.sum(combined_mask)} pixels in relevant study area")
            
            # Apply mask to exposition layer
            masked_exposition = exposition.copy()
            masked_exposition[~combined_mask] = 0.0
            
            # Log masking statistics
            original_nonzero = np.sum(exposition > 0)
            masked_nonzero = np.sum(masked_exposition > 0)
            logger.info(f"Masking removed {original_nonzero - masked_nonzero} non-zero pixels "
                       f"({(original_nonzero - masked_nonzero) / original_nonzero * 100:.1f}% reduction)")
            
            # Log final study area values (no renormalization to preserve multiplier effects)
            study_area_values = masked_exposition[combined_mask]
            valid_values = study_area_values[study_area_values > 0]
            
            if len(valid_values) > 0:
                min_val = np.min(valid_values)
                max_val = np.max(valid_values)
                mean_val = np.mean(valid_values)
                logger.info(f"Final study area values - Min: {min_val:.4f}, Max: {max_val:.4f}, Mean: {mean_val:.4f}")
                logger.info(f"Urbanisation multipliers preserved - no renormalization applied")
                return masked_exposition
            else:
                logger.warning("No valid values found in study area")
                return masked_exposition
            
        except Exception as e:
            logger.warning(f"Could not apply study area mask: {str(e)}")
            logger.warning("Proceeding with unmasked exposition layer")
            return exposition

    def ensure_economic_exposition_layer_exists(self, economic_identifier: str) -> Path:
        """
        Ensure that the economic exposition layer exists for the given identifier.
        If it doesn't exist, create it using the weights from config.
        
        Returns:
            Path to the exposition layer TIF file
        """
        tif_path = Path(self.config.output_dir) / "exposition" / "tif" / f"exposition_{economic_identifier}.tif"
        
        if tif_path.exists():
            logger.info(f"Economic exposition layer for {economic_identifier} already exists at {tif_path}")
            return tif_path
        
        logger.info(f"Economic exposition layer for {economic_identifier} does not exist, creating it...")
        
        # Get weights for this economic dataset
        economic_weights = self.config.economic_exposition_weights
        if economic_identifier not in economic_weights:
            raise ValueError(f"No exposition weights found for economic identifier: {economic_identifier}")
        
        weights = economic_weights[economic_identifier]
        
        # Create the exposition layer
        exposition_data, meta = self.create_economic_exposition_layer(economic_identifier, weights)
        
        # Ensure output directory exists
        tif_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save the TIF file
        self.save_exposition_layer(exposition_data, meta, str(tif_path))
        logger.info(f"Created and saved economic exposition layer for {economic_identifier} at {tif_path}")
        
        return tif_path

    def load_and_preprocess_vierkant_stats(self) -> Tuple[np.ndarray, dict]:
        """Load and preprocess vierkant stats socioeconomic data."""
        logger.info("Loading and preprocessing Vierkantstatistieken socioeconomic data")
        
        vierkant_data, vierkant_meta = self.vierkant_processor.process_vierkant_stats()
        
        logger.info(f"Vierkant stats socioeconomic data - Shape: {vierkant_data.shape}, "
                   f"Min: {np.nanmin(vierkant_data):.4f}, "
                   f"Max: {np.nanmax(vierkant_data):.4f}, "
                   f"Mean: {np.nanmean(vierkant_data):.4f}")
        
        return vierkant_data, vierkant_meta