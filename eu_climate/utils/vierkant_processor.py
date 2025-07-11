import geopandas as gpd
import numpy as np
import rasterio
import rasterio.features
import rasterio.transform
from pathlib import Path
from typing import Tuple, Dict
import tempfile

from .conversion import RasterTransformer
from .normalise_data import AdvancedDataNormalizer, NormalizationStrategy
from .utils import setup_logging

logger = setup_logging(__name__)

class VierkantStatsProcessor:
    
    def __init__(self, config):
        self.config = config
        self.transformer = RasterTransformer(
            target_crs=config.target_crs,
            config=config
        )
        self.normalizer = AdvancedDataNormalizer(NormalizationStrategy.EXPOSITION_OPTIMIZED)
    
    def load_vierkant_vector_data(self) -> gpd.GeoDataFrame:
        """Load Vierkantstatistieken GPKG vector file and validate required columns."""
        vierkant_path = self.config.vierkant_stats_path
        logger.info(f"Loading Vierkantstatistieken vector data from {vierkant_path}")
        
        if not vierkant_path.exists():
            raise FileNotFoundError(f"Vierkant stats file not found: {vierkant_path}")
        
        vierkant_gdf = gpd.read_file(vierkant_path)
        logger.info(f"Loaded {len(vierkant_gdf)} grid polygons from Vierkantstatistieken")
        logger.info(f"Available columns: {list(vierkant_gdf.columns)}")
        
        required_columns = ['aantal_inwoners', 'gemiddelde_huishoudensgrootte', 'gemiddelde_woz_waarde_woning']
        for column in required_columns:
            if column not in vierkant_gdf.columns:
                raise ValueError(f"Required column '{column}' not found in Vierkantstatistieken data")
        
        logger.info(f"All required columns found: {required_columns}")
        return vierkant_gdf
    
    def create_socioeconomic_index_from_vector(self, vierkant_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Create weighted socioeconomic index from vector attribute columns."""
        logger.info("Creating socioeconomic index from vector attributes")
        
        multipliers = self.config.vierkant_stats_multipliers
        inhabitants_multiplier = multipliers['number_of_occupants_multiplier']
        household_size_multiplier = multipliers['mean_household_size_multiplier']
        house_price_multiplier = multipliers['mean_houseprice_multiplier']
        
        logger.info(f"Using multipliers - Inhabitants: {inhabitants_multiplier}, "
                   f"Household size: {household_size_multiplier}, House price: {house_price_multiplier}")
        
        vierkant_processed = vierkant_gdf.copy()
        
        inhabitants = self.handle_vector_nodata_values(vierkant_processed['aantal_inwoners'])
        household_size = self.handle_vector_nodata_values(vierkant_processed['gemiddelde_huishoudensgrootte'])
        house_price = self.handle_vector_nodata_values(vierkant_processed['gemiddelde_woz_waarde_woning'])
        
        if inhabitants.max() == 0 and household_size.max() == 0 and house_price.max() == 0:
            raise ValueError("All Vierkantstatistieken components contain only zeros")
        
        normalized_inhabitants = self.normalize_vector_component_data(inhabitants)
        normalized_household_size = self.normalize_vector_component_data(household_size)
        normalized_house_price = self.normalize_vector_component_data(house_price)
        
        vierkant_processed['socioeconomic_index'] = (
            inhabitants_multiplier * normalized_inhabitants +
            household_size_multiplier * normalized_household_size +
            house_price_multiplier * normalized_house_price
        )
        
        logger.info(f"Socioeconomic index statistics - "
                   f"Min: {vierkant_processed['socioeconomic_index'].min():.4f}, "
                   f"Max: {vierkant_processed['socioeconomic_index'].max():.4f}, "
                   f"Mean: {vierkant_processed['socioeconomic_index'].mean():.4f}")
        
        return vierkant_processed
    
    def handle_vector_nodata_values(self, series_data):
        """Handle nodata values in pandas series by converting to zeros."""
        return series_data.fillna(0)
    
    def normalize_vector_component_data(self, component_data) -> np.ndarray:
        """Normalize component using central normalization utility."""
        component_array = component_data.values
        
        if np.max(component_array) == np.min(component_array):
            return np.zeros_like(component_array)
        
        valid_mask = component_array > 0
        return self.normalizer.normalize_exposition_data(component_array, valid_mask)
    
    def convert_vector_to_raster_using_central_transformer(self, vierkant_gdf: gpd.GeoDataFrame) -> Tuple[np.ndarray, Dict]:
        """Convert vector socioeconomic index to raster using central transformer."""
        logger.info("Converting vector socioeconomic index to raster using central approach")
        
        nuts_l3_path = self.config.data_dir / "NUTS-L3-NL.shp"
        reference_bounds = self.transformer.get_reference_bounds(nuts_l3_path)
        target_crs = rasterio.crs.CRS.from_string(self.config.target_crs)
        
        transformed_gdf = self.ensure_correct_coordinate_system(vierkant_gdf, target_crs)
        temp_raster_path = self.create_temporary_raster_file()
        
        try:
            raster_100m = self.create_100m_raster_from_vector(transformed_gdf, reference_bounds, target_crs)
            self.save_raster_to_temporary_file(raster_100m, reference_bounds, target_crs, temp_raster_path)
            return self.transform_using_central_transformer(temp_raster_path, reference_bounds)
        finally:
            self.cleanup_temporary_file(temp_raster_path)
    
    def ensure_correct_coordinate_system(self, vierkant_gdf: gpd.GeoDataFrame, target_crs: rasterio.crs.CRS) -> gpd.GeoDataFrame:
        """Ensure GeoDataFrame is in correct coordinate system."""
        if vierkant_gdf.crs == target_crs:
            return vierkant_gdf
            
        transformed_gdf = vierkant_gdf.to_crs(target_crs)
        logger.info(f"Transformed Vierkantstatistieken to {target_crs}")
        return transformed_gdf
    
    def create_temporary_raster_file(self) -> Path:
        """Create temporary raster file for processing."""
        temp_file = tempfile.NamedTemporaryFile(suffix='.tif', delete=False)
        return Path(temp_file.name)
    
    def cleanup_temporary_file(self, file_path: Path) -> None:
        """Clean up temporary file."""
        if file_path.exists():
            file_path.unlink()
    
    def create_100m_raster_from_vector(self, vierkant_gdf: gpd.GeoDataFrame, reference_bounds: Tuple, target_crs: rasterio.crs.CRS) -> np.ndarray:
        """Create 100m resolution raster from vector polygons."""
        RESOLUTION_100M = 100.0
        left, bottom, right, top = reference_bounds
        width = int((right - left) / RESOLUTION_100M)
        height = int((top - bottom) / RESOLUTION_100M)
        
        transform_100m = rasterio.transform.from_bounds(
            left, bottom, right, top, width, height
        )
        
        return rasterio.features.rasterize(
            [(geom, value) for geom, value in zip(vierkant_gdf.geometry, vierkant_gdf['socioeconomic_index'])],
            out_shape=(height, width),
            transform=transform_100m,
            dtype=np.float32,
            fill=0.0
        )
    
    def save_raster_to_temporary_file(self, raster_data: np.ndarray, reference_bounds: Tuple, target_crs: rasterio.crs.CRS, temp_path: Path) -> None:
        """Save raster data to temporary file."""
        RESOLUTION_100M = 100.0
        left, bottom, right, top = reference_bounds
        width = int((right - left) / RESOLUTION_100M)
        height = int((top - bottom) / RESOLUTION_100M)
        
        transform_100m = rasterio.transform.from_bounds(
            left, bottom, right, top, width, height
        )
        
        with rasterio.open(
            temp_path, 'w',
            driver='GTiff',
            height=height,
            width=width,
            count=1,
            dtype='float32',
            crs=target_crs,
            transform=transform_100m
        ) as temp_raster:
            temp_raster.write(raster_data, 1)
    
    def transform_using_central_transformer(self, temp_raster_path: Path, reference_bounds: Tuple) -> Tuple[np.ndarray, Dict]:
        """Transform raster to target resolution using central transformer."""
        final_raster, final_transform, final_crs = self.transformer.transform_raster(
            temp_raster_path,
            reference_bounds,
            self.config.resampling_method.name.lower()
        )
        
        final_meta = {
            'crs': final_crs,
            'transform': final_transform,
            'height': final_raster.shape[0],
            'width': final_raster.shape[1],
            'dtype': 'float32'
        }
        
        logger.info(f"Final raster - Shape: {final_raster.shape}, "
                   f"Min: {np.nanmin(final_raster):.4f}, "
                   f"Max: {np.nanmax(final_raster):.4f}")
        
        return final_raster, final_meta
    
    def process_vierkant_stats(self) -> Tuple[np.ndarray, Dict]:
        """Complete processing pipeline for Vierkantstatistieken vector data."""
        logger.info("Starting Vierkantstatistieken vector processing pipeline")
        
        vierkant_gdf = self.load_vierkant_vector_data()
        
        vierkant_with_index = self.create_socioeconomic_index_from_vector(vierkant_gdf)
        
        final_raster, final_meta = self.convert_vector_to_raster_using_central_transformer(vierkant_with_index)
        
        logger.info("Vierkantstatistieken vector processing pipeline completed successfully")
        return final_raster, final_meta 