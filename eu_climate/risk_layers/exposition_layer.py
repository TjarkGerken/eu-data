import rasterio
import rasterio.features
import rasterio.warp
import geopandas as gpd
from scipy import ndimage
from typing import Optional, Tuple
import numpy as np
from rasterio.enums import Resampling
from pathlib import Path
import logging
import matplotlib.pyplot as plt
import os

from eu_climate.config.config import ProjectConfig
from eu_climate.utils.utils import setup_logging, suppress_warnings
from eu_climate.utils.conversion import RasterTransformer
from eu_climate.utils.visualization import LayerVisualizer


# Set up logging for the exposition layer
logger = setup_logging(__name__)


class ExpositionLayer:
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
    """
    
    def __init__(self, config: ProjectConfig):
        """Initialize the Exposition Layer with project configuration."""
        self.config = config
        
        # Data paths
        self.ghs_built_c_path = self.config.ghs_built_c_path
        self.ghs_built_v_path = self.config.ghs_built_v_path
        self.population_path = self.config.population_path
        self.nuts_paths = self.config.nuts_paths
        
        # Initialize raster transformer
        self.transformer = RasterTransformer(
            target_crs=self.config.target_crs,
            target_resolution=30.0,  # 30m resolution
            config=self.config
        )
        
        # Initialize visualizer
        self.visualizer = LayerVisualizer(self.config)
        
        logger.info(f"Initialized Exposition Layer")
        


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
    
    def normalize_data(self):
        """Normalize the data to a unified scale of 0-1."""
        pass
    
    def load_and_preprocess_raster(self, path: str) -> Tuple[np.ndarray, dict]:
        """Load and preprocess a single raster to target resolution and CRS using NUTS-L3 bounds."""
        logger.info(f"Loading raster: {path}")
        
        # Get reference bounds from NUTS-L3 instead of NUTS-L0 for consistency with relevance layer
        nuts_l3_path = self.config.data_dir / "NUTS-L3-NL.shp"
        reference_bounds = self.transformer.get_reference_bounds(nuts_l3_path)
        
        # Transform raster
        data, transform, crs = self.transformer.transform_raster(
            path,
            reference_bounds=reference_bounds,
            resampling_method=self.config.resampling_method
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
        """Normalize a raster to 0-1 based on min/max values, ignoring NaNs."""
        valid = ~np.isnan(data)
        min_val = np.nanmin(data)
        max_val = np.nanmax(data)
        logger.info(f"Raster normalization - Original Min: {min_val}, Max: {max_val}, Mean: {np.nanmean(data)}")
        norm = np.zeros_like(data, dtype=np.float32)
        if max_val > min_val:
            norm[valid] = (data[valid] - min_val) / (max_val - min_val)
        logger.info(f"Raster normalization - Normalized Min: {np.nanmin(norm)}, Max: {np.nanmax(norm)}, Mean: {np.nanmean(norm)}")
        return norm

    def calculate_exposition(self) -> Tuple[np.ndarray, dict]:
        """Calculate the final exposition layer using weighted combination."""
        # Load and preprocess rasters
        ghs_built_c, meta = self.load_and_preprocess_raster(self.ghs_built_c_path)
        logger.info(f"GHS Built-C after preprocessing - Min: {np.nanmin(ghs_built_c)}, Max: {np.nanmax(ghs_built_c)}, Mean: {np.nanmean(ghs_built_c)}")
        
        # Use the first layer's transform as reference for all other layers
        reference_transform = meta['transform']
        reference_crs = meta['crs']
        reference_shape = ghs_built_c.shape
        
        # Load other layers with the same transform
        ghs_built_v, _ = self.load_and_preprocess_raster(self.ghs_built_v_path)
        logger.info(f"GHS Built-V after preprocessing - Min: {np.nanmin(ghs_built_v)}, Max: {np.nanmax(ghs_built_v)}, Mean: {np.nanmean(ghs_built_v)}")
        
        # Load population data last to ensure proper alignment
        population, _ = self.load_and_preprocess_raster(self.population_path)
        logger.info(f"Population after preprocessing - Min: {np.nanmin(population)}, Max: {np.nanmax(population)}, Mean: {np.nanmean(population)}")
        
        # Ensure all layers have the same shape and transform
        if not self.transformer.validate_alignment(ghs_built_v, meta['transform'], ghs_built_c, reference_transform):
            ghs_built_v = self.transformer.ensure_alignment(
                ghs_built_v,
                meta['transform'],
                reference_transform,
                reference_shape,
                self.config.resampling_method
            )
            logger.info(f"GHS Built-V after reprojection - Min: {np.nanmin(ghs_built_v)}, Max: {np.nanmax(ghs_built_v)}, Mean: {np.nanmean(ghs_built_v)}")
            
        if not self.transformer.validate_alignment(population, meta['transform'], ghs_built_c, reference_transform):
            population = self.transformer.ensure_alignment(
                population,
                meta['transform'],
                reference_transform,
                reference_shape,
                self.config.resampling_method
            )
            logger.info(f"Population after reprojection - Min: {np.nanmin(population)}, Max: {np.nanmax(population)}, Mean: {np.nanmean(population)}")
        
        # Check for valid data
        if np.all(ghs_built_c == 0) or np.all(ghs_built_v == 0) or np.all(population == 0):
            logger.error("One or more input layers contain only zeros!")
            raise ValueError("Invalid input data: one or more layers contain only zeros")
        
        # Normalize
        norm_built_c = self.normalize_ghs_built_c(ghs_built_c)
        norm_built_v = self.normalize_raster(ghs_built_v)
        norm_population = self.normalize_raster(population)
        
        # Check normalized data
        if np.all(norm_built_c == 0) or np.all(norm_built_v == 0) or np.all(norm_population == 0):
            logger.error("One or more normalized layers contain only zeros!")
            raise ValueError("Invalid normalized data: one or more layers contain only zeros")
        
        # Weighted sum
        w = self.config.exposition_weights
        exposition = (
            w['ghs_built_c_weight'] * norm_built_c +
            w['ghs_built_v_weight'] * norm_built_v +
            w['population_weight'] * norm_population
        )
        logger.info(f"Final exposition - Min: {np.nanmin(exposition)}, Max: {np.nanmax(exposition)}, Mean: {np.nanmean(exposition)}")
        
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
            
        return exposition, meta

    def save_exposition_layer(self, data: np.ndarray, meta: dict, out_path: str):
        """Save the final exposition layer as GeoTIFF."""
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
            
        data = np.clip(data, 0, 1)
        logger.info(f"Data before saving - Min: {np.nanmin(data)}, Max: {np.nanmax(data)}, Mean: {np.nanmean(data)}")
        
        meta.update({
            'driver': 'GTiff',
            'dtype': 'float32',
            'count': 1,
            'nodata': None  # Ensure no nodata value is set
        })
        
        with rasterio.open(out_path, 'w', **meta) as dst:
            dst.write(data.astype(np.float32), 1)
            logger.info(f"Successfully wrote data to {out_path}")

    def visualize_exposition(self, exposition: np.ndarray, meta: dict, title: str = "Exposition Layer"):
        """Visualize the exposition index for each cell using unified styling."""
        output_path = Path(self.config.output_dir) / 'exposition_layer.png'
        self.visualizer.visualize_exposition_layer(
            data=exposition,
            meta=meta,
            output_path=output_path,
            title=title
        )

    def export_exposition(self, data: np.ndarray, meta: dict, out_path: str):
        """Export the exposition index for each cell to a specified GeoTIFF path."""
        meta.update({'dtype': 'float32', 'count': 1})
        with rasterio.open(out_path, 'w', **meta) as dst:
            dst.write(data.astype(np.float32), 1)
        logger.info(f"Exposition layer exported to {out_path}")

    def run_exposition(self, visualize: bool = False, export_path: str = None, create_png: bool = True):
        """Main execution flow for the exposition layer."""
        exposition, meta = self.calculate_exposition()
        out_path = export_path or str(Path(self.config.output_dir) / 'exposition_layer.tif')
        self.save_exposition_layer(exposition, meta, out_path)
        logger.info(f"Exposition layer saved to {out_path}")
        
        # Create PNG visualization
        if create_png:
            png_path = Path(self.config.output_dir) / 'exposition_layer.png'
            self.visualizer.visualize_exposition_layer(
                data=exposition,
                meta=meta,
                output_path=png_path,
                title="Exposition Layer"
            )
            logger.info(f"Exposition layer PNG saved to {png_path}")
        
        if visualize:
            self.visualize_exposition(exposition, meta)
        if export_path:
            self.export_exposition(exposition, meta, export_path)

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
            land_mass_data, land_transform, _ = self.transformer.transform_raster(
                self.config.land_mass_path,
                reference_bounds=self.transformer.get_reference_bounds(nuts_l3_path),
                resampling_method=self.config.resampling_method
            )
            
            # Ensure land mass data is aligned with exposition layer
            if not self.transformer.validate_alignment(land_mass_data, land_transform, exposition, transform):
                land_mass_data = self.transformer.ensure_alignment(
                    land_mass_data, land_transform, transform, shape,
                    self.config.resampling_method
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
            
            # Renormalize values within study area to full 0-1 range
            study_area_values = masked_exposition[combined_mask]
            valid_values = study_area_values[study_area_values > 0]
            
            if len(valid_values) > 0:
                min_val = np.min(valid_values)
                max_val = np.max(valid_values)
                logger.info(f"Study area values before renormalization - Min: {min_val:.4f}, Max: {max_val:.4f}")
                
                if max_val > min_val:
                    # Renormalize only the valid values within study area to 0-1 range
                    renormalized_exposition = masked_exposition.copy()
                    valid_mask = combined_mask & (masked_exposition > 0)
                    renormalized_exposition[valid_mask] = (masked_exposition[valid_mask] - min_val) / (max_val - min_val)
                    
                    # Verify renormalization
                    final_values = renormalized_exposition[valid_mask]
                    logger.info(f"Study area values after renormalization - Min: {np.min(final_values):.4f}, Max: {np.max(final_values):.4f}")
                    
                    return renormalized_exposition
                else:
                    logger.warning("No variation in study area values - cannot renormalize")
                    return masked_exposition
            else:
                logger.warning("No valid values found in study area")
                return masked_exposition
            
        except Exception as e:
            logger.warning(f"Could not apply study area mask: {str(e)}")
            logger.warning("Proceeding with unmasked exposition layer")
            return exposition