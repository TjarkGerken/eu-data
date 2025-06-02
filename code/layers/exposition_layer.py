import rasterio
import rasterio.features
import rasterio.warp
import geopandas as gpd
from scipy import ndimage
from typing import Optional, Tuple
import numpy as np
from code.main import ProjectConfig
from code.utils import setup_logging

# Set up logging for the exposition layer
logger = setup_logging(__name__)


class ExpositionLayer:
    """
    Exposition Layer Implementation
    =============================
    
    Processes and analyzes exposure factors including:
    - Building density and volume (GHS Built C)
    - Population density (GHS POP)
    - Economic indicators (NUTS data)
    - Building structure (GHS Built S)
    
    Features:
    - Multi-source building data integration
    - Downsampling of aggregated data
    - Spatial normalization
    - Integration of multiple exposure factors
    """
    
    def __init__(self, config: ProjectConfig):
        """Initialize the Exposition Layer with project configuration."""
        self.config = config
        
        # Data paths
        self.ghs_built_path = self.config.ghs_built_path
        self.ghs_built_s_path = self.config.ghs_built_s_path
        self.population_path = self.config.population_path
        self.nuts_paths = self.config.nuts_paths
        
        # Data holders
        self.ghs_built_data = None
        self.ghs_built_s_data = None
        self.population_data = None
        self.transform = None
        self.crs = None
        self.nuts_data = {}
        
        logger.info(f"Initialized Exposition Layer")
        
    def _resample_to_match(self, data: np.ndarray, src_transform: rasterio.Affine,
                          src_crs: rasterio.crs.CRS) -> np.ndarray:
        """
        Resample data to match the reference (GHS Built C) resolution and projection.
        
        Args:
            data: Source data array
            src_transform: Source data transform
            src_crs: Source data CRS
            
        Returns:
            Resampled data array matching reference dimensions
        """
        # Create destination profile
        dst_shape = self.ghs_built_data.shape
        dst_transform = self.transform
        dst_crs = self.crs
        
        # Calculate resampling parameters
        reproject_params = {
            'src_transform': src_transform,
            'src_crs': src_crs,
            'dst_transform': dst_transform,
            'dst_crs': dst_crs,
            'resampling': self.config.resampling_method
        }
        
        # Perform resampling
        resampled_data, _ = rasterio.warp.reproject(
            source=data,
            destination=np.zeros(dst_shape, dtype=data.dtype),
            **reproject_params
        )
        
        return resampled_data
    
    def load_building_data(self) -> Tuple[np.ndarray, rasterio.Affine, rasterio.crs.CRS]:
        """
        Load and prepare building data from both GHS Built C and Built S.
        
        Returns:
            Tuple containing the combined building data array, transform, and CRS information.
        """
        logger.info("Loading building data...")
        
        try:
            # Load GHS Built C (comprehensive building characteristics)
            with rasterio.open(self.ghs_built_path) as src:
                self.ghs_built_data = src.read(1)
                self.transform = src.transform
                self.crs = src.crs
                
                # Handle nodata values
                nodata = src.nodata
                if nodata is not None:
                    self.ghs_built_data = np.where(self.ghs_built_data == nodata, np.nan, self.ghs_built_data)
        except Exception as e:
            logger.warning(f"Could not load GHS Built C data: {str(e)}")
            logger.warning("Proceeding with default building density values")
            self.ghs_built_data = np.ones((1000, 1000))  # Default size
            
        try:
            # Load GHS Built S (building structure information)
            with rasterio.open(self.ghs_built_s_path) as src:
                self.ghs_built_s_data = src.read(1)
                
                # Ensure same projection and resolution
                if (src.crs != self.crs or 
                    src.transform != self.transform or 
                    self.ghs_built_s_data.shape != self.ghs_built_data.shape):
                    logger.info("Resampling GHS Built S data to match GHS Built C...")
                    self.ghs_built_s_data = self._resample_to_match(
                        self.ghs_built_s_data,
                        src.transform,
                        src.crs
                    )
                
                # Handle nodata values
                nodata = src.nodata
                if nodata is not None:
                    self.ghs_built_s_data = np.where(self.ghs_built_s_data == nodata, np.nan, self.ghs_built_s_data)
        except Exception as e:
            logger.warning(f"Could not load GHS Built S data: {str(e)}")
            logger.warning("Proceeding without building structure information")
            self.ghs_built_s_data = np.ones_like(self.ghs_built_data)
        
        # Log statistics
        self._log_building_statistics()
        
        return self.ghs_built_data, self.transform, self.crs
    
    def _log_building_statistics(self) -> None:
        """Log statistics about building data."""
        for name, data in [("GHS Built C", self.ghs_built_data),
                         ("GHS Built S", self.ghs_built_s_data)]:
            valid_data = data[~np.isnan(data)]
            logger.info(f"{name} Statistics:")
            logger.info(f"  Shape: {data.shape}")
            logger.info(f"  Min value: {np.min(valid_data):.2f}")
            logger.info(f"  Max value: {np.max(valid_data):.2f}")
            logger.info(f"  Mean value: {np.mean(valid_data):.2f}")
            logger.info(f"  Coverage: {len(valid_data) / data.size * 100:.1f}%")
    
    def calculate_building_volume(self) -> np.ndarray:
        """
        Calculate building volume using both GHS Built C and Built S data.
        
        Returns:
            Array of estimated building volumes in cubic meters.
        """
        if self.ghs_built_data is None or self.ghs_built_s_data is None:
            raise ValueError("Building data must be loaded first")
        
        # Use building structure data to estimate height
        structure_factor = np.clip(self.ghs_built_s_data / np.nanmax(self.ghs_built_s_data), 0, 1)
        
        # Calculate building height based on both density and structure
        base_height = self.config.base_floor_height
        max_floors = self.config.max_floors
        
        # Normalize built-up density
        normalized_density = (self.ghs_built_data - np.nanmin(self.ghs_built_data)) / (
            np.nanmax(self.ghs_built_data) - np.nanmin(self.ghs_built_data)
        )
        
        # Combine density and structure information for height estimation
        height_factor = 0.7 * normalized_density + 0.3 * structure_factor
        avg_floors = 1 + (height_factor * (max_floors - 1))
        
        # Calculate building height and volume
        building_height = avg_floors * base_height
        building_volume = self.ghs_built_data * building_height
        
        logger.info(f"Building volume calculation completed")
        logger.info(f"  Average building height: {np.nanmean(building_height):.2f}m")
        logger.info(f"  Max building height: {np.nanmax(building_height):.2f}m")
        logger.info(f"  Structure factor influence applied")
        
        return building_volume
    
    def load_nuts_data(self, level: str = 'L3') -> gpd.GeoDataFrame:
        """Load NUTS administrative boundaries and socio-economic data."""
        if level not in self.nuts_paths:
            raise ValueError(f"Invalid NUTS level: {level}")
            
        if level not in self.nuts_data:
            logger.info(f"Loading NUTS {level} data...")
            nuts_gdf = gpd.read_file(self.nuts_paths[level])
            
            # Ensure proper projection
            if nuts_gdf.crs != self.config.target_crs:
                nuts_gdf = nuts_gdf.to_crs(self.config.target_crs)
            
            self.nuts_data[level] = nuts_gdf
            logger.info(f"Loaded {len(nuts_gdf)} NUTS {level} regions")
        
        return self.nuts_data[level]
    
    def calculate_exposure_index(self, building_weight: float = 0.4,
                               population_weight: float = 0.4,
                               volume_weight: float = 0.2) -> np.ndarray:
        """
        Calculate combined exposure index from all factors.
        
        Args:
            building_weight: Weight for building density
            population_weight: Weight for population density
            volume_weight: Weight for building volume
            
        Returns:
            Combined exposure index array
        """
        if any(x is None for x in [self.ghs_built_data, self.population_data]):
            raise ValueError("Both building and population data must be loaded")
            
        # Ensure weights sum to 1
        total_weight = building_weight + population_weight + volume_weight
        if not np.isclose(total_weight, 1.0):
            raise ValueError("Weights must sum to 1")
        
        # Calculate building volume using enhanced method
        building_volume = self.calculate_building_volume()
        
        # Normalize all factors to 0-1 range
        norm_building = (self.ghs_built_data - np.nanmin(self.ghs_built_data)) / (
            np.nanmax(self.ghs_built_data) - np.nanmin(self.ghs_built_data)
        )
        
        norm_population = (self.population_data - np.nanmin(self.population_data)) / (
            np.nanmax(self.population_data) - np.nanmin(self.population_data)
        )
        
        norm_volume = (building_volume - np.nanmin(building_volume)) / (
            np.nanmax(building_volume) - np.nanmin(building_volume)
        )
        
        # Combine factors with weights
        exposure_index = (
            building_weight * norm_building +
            population_weight * norm_population +
            volume_weight * norm_volume
        )
        
        # Apply spatial smoothing to reduce noise
        exposure_index = ndimage.gaussian_filter(
            np.nan_to_num(exposure_index, nan=0),
            sigma=self.config.smoothing_sigma
        )
        
        logger.info("Exposure index calculation completed")
        logger.info(f"  Mean exposure: {np.nanmean(exposure_index):.3f}")
        logger.info(f"  Max exposure: {np.nanmax(exposure_index):.3f}")
        
        return exposure_index
    
    def process_economic_exposure(self, nuts_data: Optional[gpd.GeoDataFrame] = None) -> np.ndarray:
        """
        Process economic exposure using NUTS regional data.
        
        Args:
            nuts_data: Optional GeoDataFrame with NUTS regions and economic indicators
            
        Returns:
            Economic exposure index array
        """
        if nuts_data is None:
            nuts_data = gpd.read_file(self.nuts_paths['L3'])
        
        # Ensure NUTS data is in the same CRS
        if nuts_data.crs != self.crs:
            nuts_data = nuts_data.to_crs(self.crs)
        
        # Create empty raster with same dimensions as other layers
        economic_exposure = np.zeros_like(self.ghs_built_data)
        
        # Rasterize economic indicators
        # This is a simplified version - could be enhanced with more sophisticated
        # economic indicators and weighting
        shapes = ((geom, value) for geom, value in zip(nuts_data.geometry, nuts_data.gdp_per_capita))
        economic_exposure = rasterio.features.rasterize(
            shapes=shapes,
            out_shape=self.ghs_built_data.shape,
            transform=self.transform,
            dtype=np.float32
        )
        
        # Normalize economic exposure
        economic_exposure = (economic_exposure - np.nanmin(economic_exposure)) / (
            np.nanmax(economic_exposure) - np.nanmin(economic_exposure)
        )
        
        return economic_exposure
    
    def export_results(self, output_prefix: str = "exposition") -> None:
        """Export exposition layer results to GeoTIFF files."""
        if self.ghs_built_data is None:
            raise ValueError("No data to export")
            
        # Calculate indices
        exposure_index = self.calculate_exposure_index()
        building_volume = self.calculate_building_volume()
        
        # Prepare export paths
        exposure_path = self.config.output_dir / f"{output_prefix}_index.tif"
        volume_path = self.config.output_dir / f"{output_prefix}_building_volume.tif"
        
        # Export exposure index
        with rasterio.open(
            exposure_path,
            'w',
            driver='GTiff',
            height=exposure_index.shape[0],
            width=exposure_index.shape[1],
            count=1,
            dtype=exposure_index.dtype,
            crs=self.crs,
            transform=self.transform
        ) as dst:
            dst.write(exposure_index, 1)
            
        # Export building volume
        with rasterio.open(
            volume_path,
            'w',
            driver='GTiff',
            height=building_volume.shape[0],
            width=building_volume.shape[1],
            count=1,
            dtype=building_volume.dtype,
            crs=self.crs,
            transform=self.transform
        ) as dst:
            dst.write(building_volume, 1)
            
        logger.info(f"Exported exposition results to {self.config.output_dir}")