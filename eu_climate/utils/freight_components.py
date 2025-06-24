import pandas as pd
import geopandas as gpd
import numpy as np
import rasterio
import rasterio.features
from typing import Dict, Tuple, Optional
from pathlib import Path

from eu_climate.config.config import ProjectConfig
from eu_climate.utils.utils import setup_logging
from eu_climate.utils.conversion import RasterTransformer
from eu_climate.utils.normalise_data import AdvancedDataNormalizer, NormalizationStrategy

logger = setup_logging(__name__)


class ZeevartDataLoader:
    """Handles loading and preprocessing of Zeevart maritime freight data."""
    
    def __init__(self, config: ProjectConfig):
        self.config = config
        self.data_dir = config.data_dir
        self.transformer = RasterTransformer(
            target_crs=config.target_crs,
            config=config
        )
        
    def load_zeevart_freight_data(self) -> pd.DataFrame:
        """Load and process Zeevart maritime freight data."""
        zeevart_path = self.config.zeevart_freight_path
        
        if not zeevart_path.exists():
            logger.warning(f"Zeevart data not found: {zeevart_path}")
            return pd.DataFrame()
            
        logger.info(f"Loading Zeevart freight data from {zeevart_path}")
        
        try:
            zeevart_df = pd.read_excel(zeevart_path)
            logger.info(f"Loaded Zeevart data with shape: {zeevart_df.shape}")
            logger.info(f"Columns: {zeevart_df.columns.tolist()}")
            
            processed_data = self._process_zeevart_data(zeevart_df)
            return processed_data
            
        except Exception as e:
            logger.error(f"Error loading Zeevart data: {e}")
            return pd.DataFrame()
    
    def _process_zeevart_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process Zeevart data to extract relevant freight values."""
        # Filter for "Aan- en afvoer" (combined import/export) data
        combined_flow_data = df[df['Vervoerstromen'] == 'Aan- en afvoer']
        
        # Get most recent full year (2022*)
        latest_year = '2022*'
        if latest_year not in combined_flow_data['Perioden'].values:
            available_years = combined_flow_data['Perioden'].unique()
            latest_year = sorted([year for year in available_years if '*' in year and 'kwartaal' not in year])[-1]
            logger.info(f"Using latest available year: {latest_year}")
        
        latest_data = combined_flow_data[combined_flow_data['Perioden'] == latest_year]
        
        # Group by port category and sum freight volumes
        aggregated = latest_data.groupby('Nederlandse zeehavens').agg({
            'Overgeslagen brutogewicht (1 000 ton)': 'sum'
        }).reset_index()
        
        # Clean and standardize column names
        aggregated.columns = ['port_category', 'freight_volume_1000_tons']
        
        # Convert to tonnes (multiply by 1000)
        aggregated['freight_value'] = aggregated['freight_volume_1000_tons'] * 1000
        
        # Remove 'Totaal' category to avoid double counting
        aggregated = aggregated[aggregated['port_category'] != 'Totaal']
        
        # Ensure numeric values
        aggregated['freight_value'] = pd.to_numeric(aggregated['freight_value'], errors='coerce')
        aggregated = aggregated.dropna()
        
        logger.info(f"Processed Zeevart data: {len(aggregated)} port categories for year {latest_year}")
        logger.info(f"Total maritime freight volume: {aggregated['freight_value'].sum():,.0f} tonnes")
        
        return aggregated


class PortFreightMapper:
    """Maps freight data to individual port geometries using centralized transformation utilities."""
    
    def __init__(self, config: ProjectConfig):
        self.config = config
        self.transformer = RasterTransformer(
            target_crs=config.target_crs,
            config=config
        )
        
    def load_port_mapping(self) -> pd.DataFrame:
        """Load port ID to category mapping file."""
        mapping_path = self.config.port_mapping_path
        
        if not mapping_path.exists():
            logger.error(f"Port mapping file not found: {mapping_path}")
            return pd.DataFrame()
            
        try:
            mapping_df = pd.read_excel(mapping_path)
            logger.info(f"Loaded port mapping with shape: {mapping_df.shape}")
            return mapping_df
            
        except Exception as e:
            logger.error(f"Error loading port mapping: {e}")
            return pd.DataFrame()
    
    def load_port_shapefile(self) -> gpd.GeoDataFrame:
        """Load port shapefile using consistent coordinate transformation."""
        if not self.config.port_path.exists():
            logger.error(f"Port shapefile not found: {self.config.port_path}")
            return gpd.GeoDataFrame()
            
        try:
            port_gdf = gpd.read_file(self.config.port_path)
            logger.info(f"Loaded port shapefile with {len(port_gdf)} ports")
            logger.info(f"Port shapefile columns: {port_gdf.columns.tolist()}")
            
            # Transform to target CRS using consistent approach
            target_crs = rasterio.crs.CRS.from_string(self.config.target_crs)
            if port_gdf.crs != target_crs:
                port_gdf = port_gdf.to_crs(target_crs)
                logger.info(f"Transformed port data to {target_crs}")
                
            return port_gdf
            
        except Exception as e:
            logger.error(f"Error loading port shapefile: {e}")
            return gpd.GeoDataFrame()
    
    def map_freight_to_ports(self, zeevart_data: pd.DataFrame) -> gpd.GeoDataFrame:
        """Map Zeevart freight data to individual port geometries using area-based allocation."""
        # Load port shapefile and mapping
        port_gdf = self.load_port_shapefile()
        mapping_df = self.load_port_mapping()
        
        if port_gdf.empty or mapping_df.empty or zeevart_data.empty:
            logger.warning("Missing required data for port freight mapping")
            return gpd.GeoDataFrame()
        
        # Merge port geometries with categories
        port_with_categories = port_gdf.merge(
            mapping_df, 
            left_on='PORT_ID', 
            right_on='PORT_ID', 
            how='left'
        )
        
        # Merge with freight data
        port_with_freight = port_with_categories.merge(
            zeevart_data,
            left_on='Category',
            right_on='port_category',
            how='left'
        )
        
        # Fill missing freight values with 0 and ensure proper float type
        port_with_freight['freight_value'] = port_with_freight['freight_value'].fillna(0).astype(float)
        
        # Calculate port areas for proportional allocation
        port_with_freight['port_area'] = port_with_freight.geometry.area
        
        # Apply area-based freight distribution within each category
        if not port_with_freight.empty:
            logger.info("Distributing freight among ports by area-weighted allocation:")
            
            for category in port_with_freight['port_category'].dropna().unique():
                if category in zeevart_data['port_category'].values:
                    # Get total freight for this category
                    total_freight = zeevart_data[zeevart_data['port_category'] == category]['freight_value'].iloc[0]
                    
                    # Filter ports in this category
                    category_mask = port_with_freight['port_category'] == category
                    category_ports = port_with_freight[category_mask]
                    
                    if len(category_ports) > 0:
                        # Calculate area-based allocation
                        total_area = category_ports['port_area'].sum()
                        
                        if total_area > 0:
                            # Distribute freight proportionally to port area
                            area_ratios = category_ports['port_area'] / total_area
                            freight_allocations = area_ratios * total_freight
                            
                            # Update freight values for this category
                            port_with_freight.loc[category_mask, 'freight_value'] = freight_allocations.values
                            
                            # Log allocation details
                            num_ports = len(category_ports)
                            min_allocation = freight_allocations.min()
                            max_allocation = freight_allocations.max()
                            avg_allocation = freight_allocations.mean()
                            
                            logger.info(f"  {category}: {total_freight:,.0f} tonnes allocated across {num_ports} ports")
                            logger.info(f"    Area-based allocation range: {min_allocation:,.0f} - {max_allocation:,.0f} tonnes (avg: {avg_allocation:,.0f})")
                            logger.info(f"    Total area: {total_area:,.0f} m²")
                        else:
                            logger.warning(f"  {category}: Zero total area, using equal distribution fallback")
                            freight_per_port = total_freight / len(category_ports)
                            port_with_freight.loc[category_mask, 'freight_value'] = freight_per_port
        
        # Include all ports - those with categories get freight, those without get 0 freight
        valid_ports = port_with_freight.copy()
        
        # Ensure all ports have a freight value (NaN categories get 0 freight)  
        valid_ports['freight_value'] = valid_ports['freight_value'].fillna(0)
        
        # Filter out any ports with invalid geometries
        valid_ports = valid_ports[valid_ports['geometry'].notna()].copy()
        
        # Clip to study area using existing NUTS boundaries
        nuts_l3_path = self.config.data_dir / "NUTS-L3-NL.shp"
        if nuts_l3_path.exists():
            try:
                nuts_gdf = gpd.read_file(nuts_l3_path)
                target_crs = rasterio.crs.CRS.from_string(self.config.target_crs)
                if nuts_gdf.crs != target_crs:
                    nuts_gdf = nuts_gdf.to_crs(target_crs)
                
                study_area = nuts_gdf.geometry.unary_union
                ports_in_study_area = valid_ports[valid_ports.geometry.intersects(study_area)]
                
                logger.info(f"Clipped to study area: {len(ports_in_study_area)} ports with freight data "
                           f"(from {len(valid_ports)} total valid ports)")
                valid_ports = ports_in_study_area
                
            except Exception as e:
                logger.warning(f"Could not clip ports to study area: {e}")
        
        logger.info(f"Mapped freight to {len(valid_ports)} ports using area-based allocation")
        if len(valid_ports) > 0:
            total_mapped_freight = valid_ports['freight_value'].sum()
            logger.info(f"Total mapped maritime freight: {total_mapped_freight:,.0f} tonnes")
            
            # Log freight distribution by category with area statistics
            freight_by_category = valid_ports.groupby('port_category').agg({
                'freight_value': 'sum',
                'port_area': 'sum'
            }).sort_values('freight_value', ascending=False)
            
            logger.info("Area-weighted freight distribution by port category:")
            for category, row in freight_by_category.iterrows():
                freight = row['freight_value']
                area = row['port_area']
                logger.info(f"  {category}: {freight:,.0f} tonnes (total area: {area:,.0f} m²)")
        
        return valid_ports


class CombinedFreightProcessor:
    """Combines NUTS-based and port-based freight data using centralized normalization."""
    
    def __init__(self, config: ProjectConfig):
        self.config = config
        self.transformer = RasterTransformer(
            target_crs=config.target_crs,
            config=config
        )
        self.normalizer = AdvancedDataNormalizer(NormalizationStrategy.ECONOMIC_OPTIMIZED)
        
    def combine_freight_datasets(self, nuts_freight_data: pd.DataFrame, 
                                port_freight_gdf: gpd.GeoDataFrame) -> Dict[str, pd.DataFrame]:
        """Combine NUTS and port freight data ensuring no double counting."""
        combined_datasets = {}
        
        if not nuts_freight_data.empty:
            combined_datasets['nuts_freight'] = nuts_freight_data.copy()
            nuts_total = nuts_freight_data['freight_value'].sum()
            logger.info(f"NUTS freight total: {nuts_total:,.0f} tonnes")
        
        if not port_freight_gdf.empty:
            port_data = pd.DataFrame({
                'port_id': port_freight_gdf['PORT_ID'],
                'freight_value': port_freight_gdf['freight_value'],
                'geometry': port_freight_gdf['geometry'],
                'port_category': port_freight_gdf['port_category']
            })
            combined_datasets['port_freight'] = port_data
            port_total = port_data['freight_value'].sum()
            logger.info(f"Port freight total: {port_total:,.0f} tonnes")
        
        if 'nuts_freight' in combined_datasets and 'port_freight' in combined_datasets:
            logger.info("Created combined freight dataset with both NUTS and port components")
            
            combined_total = nuts_total + port_total
            logger.info(f"Combined freight total: {combined_total:,.0f} tonnes")
            logger.info(f"NUTS share: {(nuts_total/combined_total)*100:.1f}%, Port share: {(port_total/combined_total)*100:.1f}%")
            
        return combined_datasets
    
    def normalize_combined_freight_data(self, combined_datasets: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Apply sophisticated normalization across all freight datasets."""
        normalized_datasets = {}
        
        for dataset_name, dataset in combined_datasets.items():
            if 'freight_value' in dataset.columns:
                valid_mask = (dataset['freight_value'] > 0) & dataset['freight_value'].notna()
                
                if valid_mask.sum() > 0:
                    freight_values = dataset['freight_value'].values
                    normalized_values = self.normalizer.normalize_economic_data(
                        data=freight_values,
                        economic_mask=valid_mask.values
                    )
                    
                    normalized_dataset = dataset.copy()
                    normalized_dataset['freight_value_normalized'] = normalized_values
                    normalized_datasets[dataset_name] = normalized_dataset
                    
                    logger.info(f"Normalized {dataset_name}: {valid_mask.sum()} valid freight entries")
                else:
                    logger.warning(f"No valid freight data found in {dataset_name}")
                    normalized_datasets[dataset_name] = dataset.copy()
            else:
                normalized_datasets[dataset_name] = dataset.copy()
        
        return normalized_datasets 