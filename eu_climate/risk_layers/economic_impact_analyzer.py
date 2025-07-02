from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
import rasterio.mask
from pathlib import Path
import matplotlib.pyplot as plt
from dataclasses import dataclass

from eu_climate.config.config import ProjectConfig
from eu_climate.utils.utils import setup_logging
from eu_climate.utils.visualization import LayerVisualizer, ScientificStyle, setup_scientific_style
from eu_climate.utils.conversion import RasterTransformer
from eu_climate.risk_layers.cluster_layer import ClusterLayer
from eu_climate.risk_layers.relevance_layer import RelevanceLayer
from eu_climate.risk_layers.relevance_absolute_layer import RelevanceAbsoluteLayer
from eu_climate.risk_layers.hazard_layer import HazardLayer

logger = setup_logging(__name__)


@dataclass
class EconomicImpactMetrics:
    """Economic impact metrics for a single scenario."""
    scenario_name: str
    total_gdp_millions_eur: float
    at_risk_gdp_millions_eur: float
    total_freight_tonnes: float
    at_risk_freight_tonnes: float
    total_population_persons: float
    at_risk_population_persons: float
    total_hrst_persons: float
    at_risk_hrst_persons: float
    total_population_ghs_persons: float
    at_risk_population_ghs_persons: float
    cluster_count: int
    total_risk_area_square_kilometers: float


class ZonalStatisticsExtractor:
    """Extracts absolute values from raster layers within polygon boundaries."""
    
    def __init__(self, config: ProjectConfig):
        self.config = config
        
    def extract_values_from_clusters(self, 
                                   cluster_geodataframe: gpd.GeoDataFrame,
                                   relevance_layers: Dict[str, np.ndarray],
                                   relevance_metadata: dict) -> pd.DataFrame:
        """Extract absolute economic values within each cluster polygon."""
        if cluster_geodataframe.empty:
            return pd.DataFrame()
            
        results = []
        
        for _, cluster_row in cluster_geodataframe.iterrows():
            cluster_values = self._extract_single_cluster_values(
                cluster_row, relevance_layers, relevance_metadata
            )
            results.append(cluster_values)
            
        return pd.DataFrame(results)
    
    def _extract_single_cluster_values(self, 
                                     cluster_row: pd.Series,
                                     relevance_layers: Dict[str, np.ndarray],
                                     relevance_metadata: dict) -> Dict[str, Any]:
        """Extract values for a single cluster polygon."""
        cluster_geometry = cluster_row['geometry']
        cluster_id = cluster_row.get('risk_cluster_id', 'unknown')
        
        extracted_values = {
            'cluster_id': cluster_id,
            'cluster_area_square_meters': cluster_row.get('cluster_area_square_meters', 0)
        }
        
        for layer_name, layer_data in relevance_layers.items():
            if layer_name == 'combined':
                continue
                
            extracted_value = self._perform_zonal_extraction(
                cluster_geometry, layer_data, relevance_metadata
            )
            extracted_values[f'{layer_name}_absolute'] = extracted_value
        
        population_value = self._extract_population_from_cluster(cluster_geometry)
        extracted_values['population_absolute'] = population_value
            
        return extracted_values
    
    def _extract_population_from_cluster(self, cluster_geometry: any) -> float:
        """Extract population values from cluster using 2025 population raster with corrected resolution."""
        try:
            with rasterio.open(self.config.population_2025_path) as src:
                population_data = src.read(1).astype(np.float32)
                
                from rasterio.features import rasterize
                
                polygon_mask = rasterize(
                    [cluster_geometry],
                    out_shape=population_data.shape,
                    transform=src.transform,
                    fill=0,
                    default_value=1,
                    dtype=np.uint8
                )
                
                masked_values = population_data * polygon_mask
                valid_values = masked_values[masked_values > 0]
                
                total_population = float(valid_values.sum()) if len(valid_values) > 0 else 0.0
                return total_population
                
        except Exception as e:
            logger.warning(f"Population extraction failed for cluster: {e}")
            return 0.0
    
    def _perform_zonal_extraction(self, 
                                geometry: any,
                                raster_data: np.ndarray,
                                metadata: dict) -> float:
        """Perform zonal statistics extraction for a single geometry."""
        try:
            from rasterio.features import rasterize
            from rasterio.transform import from_bounds
            
            transform = metadata['transform']
            height, width = raster_data.shape
            
            polygon_mask = rasterize(
                [geometry],
                out_shape=(height, width),
                transform=transform,
                fill=0,
                default_value=1,
                dtype=np.uint8
            )
            
            masked_values = raster_data * polygon_mask
            valid_values = masked_values[masked_values > 0]
            
            return float(valid_values.sum()) if len(valid_values) > 0 else 0.0
            
        except Exception as e:
            logger.warning(f"Zonal extraction failed: {e}")
            return 0.0


class NutsDataAggregator:
    """Aggregates total economic values from NUTS regional data."""
    
    def __init__(self, config: ProjectConfig):
        self.config = config
        self.relevance_layer = RelevanceLayer(config)
        
    def get_total_regional_values(self) -> Dict[str, float]:
        """Get total absolute values for all economic indicators."""
        economic_gdfs = self.relevance_layer.load_and_process_economic_data()
        
        totals = {}
        
        for dataset_name, nuts_gdf in economic_gdfs.items():
            value_column = f"{dataset_name}_value"
            
            if value_column not in nuts_gdf.columns:
                continue
                
            total_value = nuts_gdf[value_column].sum()
            totals[dataset_name] = self._convert_to_standard_units(
                total_value, dataset_name
            )
        
        totals['population'] = self._get_total_population_from_raster()
            
        return totals
    
    def _get_total_population_from_raster(self) -> float:
        """Extract total population from the 2025 GHS population raster with corrected resolution."""
        try:
            with rasterio.open(self.config.population_2025_path) as src:
                population_data = src.read(1)
                
                valid_mask = ~np.isnan(population_data) & (population_data > 0)
                total_population = float(population_data[valid_mask].sum())
                
                logger.info(f"Total population from raster: {total_population:,.0f} persons")
                return total_population
                
        except Exception as e:
            logger.error(f"Failed to extract total population: {e}")
            return 0.0
    
    def _convert_to_standard_units(self, value: float, dataset_name: str) -> float:
        """Convert values to standard units for comparison."""
        if dataset_name == 'gdp':
            return value
        if dataset_name == 'freight':
            return value
        if dataset_name in ['population', 'hrst']:
            return value
            
        return value


class EconomicImpactVisualizer:
    """Creates visualizations comparing total vs at-risk economic values."""
    
    def __init__(self, config: ProjectConfig):
        self.config = config
        self.output_dir = Path(config.output_dir) / "economic_impact"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def create_impact_comparison_plots(self, 
                                     impact_metrics: List[EconomicImpactMetrics]) -> None:
        """Create comparison plots for all scenarios and indicators."""
        if not impact_metrics:
            logger.warning("No impact metrics available for visualization")
            return
            
        scenarios = [metrics.scenario_name for metrics in impact_metrics]
        
        for scenario in scenarios:
            scenario_metrics = next(m for m in impact_metrics if m.scenario_name == scenario)
            self._create_single_scenario_plot(scenario_metrics)
            
        self._create_multi_scenario_comparison(impact_metrics)
        
    def _create_single_scenario_plot(self, metrics: EconomicImpactMetrics) -> None:
        """Create impact comparison plot for a single scenario with percentage scaling."""
        indicators = ['GDP', 'Freight', 'Population']
        
        total_values = [
            metrics.total_gdp_millions_eur,
            metrics.total_freight_tonnes,
            metrics.total_population_persons
        ]
        at_risk_values = [
            metrics.at_risk_gdp_millions_eur,
            metrics.at_risk_freight_tonnes,
            metrics.at_risk_population_persons
        ]
        
        risk_percentages = [
            (at_risk / total * 100) if total > 0 else 0 
            for at_risk, total in zip(at_risk_values, total_values)
        ]
        
        fig, ax = plt.subplots(figsize=(12, 8), dpi=ScientificStyle.DPI)
        
        x_positions = np.arange(len(indicators))
        bar_width = 0.4
        
        bars_total = ax.bar(x_positions, [100] * len(indicators),
                          bar_width, label='Total Regional', 
                          color='lightgrey', alpha=0.8)
        
        bars_risk = ax.bar(x_positions, risk_percentages,
                         bar_width, label='At Risk in Clusters',
                         color='red', alpha=0.8)
        
        ax.set_xlabel('Economic Indicators', fontsize=ScientificStyle.LABEL_SIZE)
        ax.set_ylabel('Percentage (%)', fontsize=ScientificStyle.LABEL_SIZE)
        ax.set_title(f'Economic Impact Analysis: {metrics.scenario_name}', 
                    fontsize=ScientificStyle.TITLE_SIZE, fontweight='bold')
        ax.set_xticks(x_positions)
        ax.set_xticklabels(indicators)
        ax.set_ylim(0, 100)
        ax.legend()
        
        self._add_absolute_value_labels(ax, x_positions, total_values, at_risk_values, indicators)
        
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        plot_path = self.output_dir / f"economic_impact_{metrics.scenario_name}.png"
        plt.savefig(plot_path, dpi=ScientificStyle.DPI, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        plt.close()
        
        logger.info(f"Saved economic impact plot: {plot_path}")
    
    def _add_absolute_value_labels(self, ax: plt.Axes, x_positions: np.ndarray,
                                 total_values: List[float], at_risk_values: List[float],
                                 indicators: List[str]) -> None:
        """Add absolute value annotations to bars."""
        units = {
            'GDP': '€M',
            'Freight': 't',
            'Population': 'persons'
        }
        
        for i, (x_pos, total, at_risk, indicator) in enumerate(zip(x_positions, total_values, at_risk_values, indicators)):
            unit = units.get(indicator, '')
            
            total_text = self._format_value_with_unit(total, unit)
            at_risk_text = self._format_value_with_unit(at_risk, unit)
            
            ax.text(x_pos, 95, f'Total: {total_text}', 
                   ha='center', va='top', fontsize=10, fontweight='bold')
            
            risk_percentage = (at_risk / total * 100) if total > 0 else 0
            ax.text(x_pos, risk_percentage/2, f'At Risk: {at_risk_text}', 
                   ha='center', va='center', fontsize=9, color='white', fontweight='bold')
    
    def _format_value_with_unit(self, value: float, unit: str) -> str:
        """Format values with appropriate scaling and units."""
        if unit == '€M':
            return f"{value:,.0f} {unit}"
        elif unit == 't':
            if value >= 1_000_000:
                return f"{value/1_000_000:.1f}M {unit}"
            elif value >= 1_000:
                return f"{value/1_000:.0f}K {unit}"
            else:
                return f"{value:,.0f} {unit}"
        elif unit == 'persons':
            if value >= 1_000_000:
                return f"{value/1_000_000:.1f}M {unit}"
            elif value >= 1_000:
                return f"{value/1_000:.0f}K {unit}"
            else:
                return f"{value:,.0f} {unit}"
        else:
            return f"{value:,.0f}"
        
    def _create_multi_scenario_comparison(self, 
                                        impact_metrics: List[EconomicImpactMetrics]) -> None:
        """Create comparison plot across multiple scenarios."""
        if len(impact_metrics) < 2:
            return
            
        scenarios = [m.scenario_name for m in impact_metrics]
        gdp_percentages = [
            (m.at_risk_gdp_millions_eur / m.total_gdp_millions_eur * 100) 
            if m.total_gdp_millions_eur > 0 else 0 
            for m in impact_metrics
        ]
        freight_percentages = [
            (m.at_risk_freight_tonnes / m.total_freight_tonnes * 100)
            if m.total_freight_tonnes > 0 else 0
            for m in impact_metrics
        ]
        
        fig, ax = plt.subplots(figsize=ScientificStyle.FIGURE_SIZE, dpi=ScientificStyle.DPI)
        
        x_positions = np.arange(len(scenarios))
        bar_width = 0.35
        
        ax.bar(x_positions - bar_width/2, gdp_percentages, 
               bar_width, label='GDP at Risk (%)', color='navy', alpha=0.7)
        ax.bar(x_positions + bar_width/2, freight_percentages, 
               bar_width, label='Freight at Risk (%)', color='darkred', alpha=0.7)
        
        ax.set_xlabel('Scenarios', fontsize=ScientificStyle.LABEL_SIZE)
        ax.set_ylabel('Percentage at Risk (%)', fontsize=ScientificStyle.LABEL_SIZE)
        ax.set_title('Risk Exposure Comparison Across Scenarios', 
                    fontsize=ScientificStyle.TITLE_SIZE, fontweight='bold')
        ax.set_xticks(x_positions)
        ax.set_xticklabels(scenarios, rotation=45, ha='right')
        ax.legend()
        
        plt.tight_layout()
        plot_path = self.output_dir / "multi_scenario_risk_comparison.png"
        plt.savefig(plot_path, dpi=ScientificStyle.DPI, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        plt.close()
        
        logger.info(f"Saved multi-scenario comparison plot: {plot_path}")
        
    def _add_value_labels_to_bars(self, ax: plt.Axes, bars: any, values: List[float]) -> None:
        """Add value labels on top of bars."""
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                   f'{value:.1f}', ha='center', va='bottom', 
                   fontsize=ScientificStyle.TICK_SIZE-2)


class EconomicImpactExporter:
    """Exports economic impact results to various file formats."""
    
    def __init__(self, config: ProjectConfig):
        self.config = config
        self.output_dir = Path(config.output_dir) / "economic_impact"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def export_impact_metrics(self, 
                            impact_metrics: List[EconomicImpactMetrics],
                            cluster_details: Dict[str, pd.DataFrame]) -> None:
        """Export impact metrics to CSV and enhanced GeoPackage formats."""
        if not impact_metrics:
            return
            
        self._export_summary_csv(impact_metrics)
        self._export_detailed_cluster_data(cluster_details)
        
    def _export_summary_csv(self, impact_metrics: List[EconomicImpactMetrics]) -> None:
        """Export summary metrics to CSV."""
        summary_data = []
        
        for metrics in impact_metrics:
            summary_data.append({
                'scenario': metrics.scenario_name,
                'total_gdp_millions_eur': metrics.total_gdp_millions_eur,
                'at_risk_gdp_millions_eur': metrics.at_risk_gdp_millions_eur,
                'gdp_risk_percentage': self._calculate_risk_percentage(
                    metrics.at_risk_gdp_millions_eur, metrics.total_gdp_millions_eur
                ),
                'total_freight_tonnes': metrics.total_freight_tonnes,
                'at_risk_freight_tonnes': metrics.at_risk_freight_tonnes,
                'freight_risk_percentage': self._calculate_risk_percentage(
                    metrics.at_risk_freight_tonnes, metrics.total_freight_tonnes
                ),
                'cluster_count': metrics.cluster_count,
                'total_risk_area_square_kilometers': metrics.total_risk_area_square_kilometers
            })
            
        summary_df = pd.DataFrame(summary_data)
        csv_path = self.output_dir / "economic_impact_summary.csv"
        summary_df.to_csv(csv_path, index=False)
        
        logger.info(f"Exported impact summary to: {csv_path}")
        
    def _export_detailed_cluster_data(self, 
                                    cluster_details: Dict[str, pd.DataFrame]) -> None:
        """Export detailed cluster data with economic values."""
        for scenario, cluster_data in cluster_details.items():
            if cluster_data.empty:
                continue
                
            gpkg_path = self.output_dir / f"clusters_with_economics_{scenario}.gpkg"
            
            if hasattr(cluster_data, 'to_file'):
                cluster_data.to_file(gpkg_path, driver='GPKG')
            else:
                cluster_gdf = gpd.GeoDataFrame(cluster_data)
                cluster_gdf.to_file(gpkg_path, driver='GPKG')
                
            logger.info(f"Exported detailed cluster data to: {gpkg_path}")
            
    def _calculate_risk_percentage(self, at_risk_value: float, total_value: float) -> float:
        """Calculate risk percentage with division by zero protection."""
        if total_value <= 0:
            return 0.0
        return (at_risk_value / total_value) * 100


class EconomicImpactAnalyzer:
    """
    Economic Impact Analyzer
    =======================
    
    Analyzes economic impact of flood scenarios by combining absolute relevance 
    layers with hazard assessments to determine at-risk indicator values.
    
    Features:
    - Sequential scenario processing for memory efficiency
    - Integration of absolute relevance and hazard data
    - Stacked bar visualizations showing total vs at-risk amounts
    - Configurable flood risk threshold from config
    """
    
    def __init__(self, config: ProjectConfig):
        """Initialize the Economic Impact Analyzer."""
        self.config = config
        self.max_safe_flood_risk = config.max_safe_flood_risk
        self.indicators = config.config['relevance']['economic_variables'] + ['population']  # Add population
        
        # Define hazard scenarios to process
        self.hazard_scenarios = ['current', 'conservative', 'moderate', 'severe']
        
        # Setup visualization styling
        setup_scientific_style()
        
        logger.info("Initialized Economic Impact Analyzer")
        logger.info(f"Flood risk threshold: {self.max_safe_flood_risk}")
        logger.info(f"Target indicators: {self.indicators}")
        logger.info("Note: Using HRST (Human Resources in Science & Technology) as population indicator")
        logger.info("Note: Added total population from GHS_POP raster as additional indicator")
    
    def load_absolute_relevance_layers(self) -> Dict[str, np.ndarray]:
        """Load absolute relevance layers for all indicators."""
        logger.info("Loading absolute relevance layers...")
        
        relevance_layers = {}
        
        for indicator in self.indicators:
            if indicator == 'population':
                # Load population data directly from VRT file
                population_data = self.load_population_data()
                relevance_layers[indicator] = population_data
                continue
                
            tif_path = self.config.output_dir / "relevance_absolute" / "tif" / f"absolute_relevance_{indicator}.tif"
            
            if not tif_path.exists():
                logger.error(f"Required absolute relevance layer missing: {tif_path}")
                raise FileNotFoundError(f"Required absolute relevance layer missing: {indicator}")
            
            with rasterio.open(tif_path) as src:
                data = src.read(1).astype(np.float32)
                relevance_layers[indicator] = data
                
                # Log statistics
                valid_data = data[~np.isnan(data) & (data > 0)]
                total_value = valid_data.sum() if len(valid_data) > 0 else 0
                logger.info(f"Loaded {indicator}: {len(valid_data)} pixels, total value: {total_value:,.0f}")
        
        return relevance_layers
    
    def load_population_data(self) -> np.ndarray:
        """Load 2025 population data with corrected resolution handling."""
        logger.info("Loading 2025 population data with corrected resolution handling...")
        
        try:
            from ..utils.data_loading import load_population_2025_with_validation
            
            # Use the corrected 2025 population loading function
            population_data, metadata, validation_passed = load_population_2025_with_validation(
                config=self.config,
                apply_study_area_mask=True
            )
            
            # Log statistics
            valid_data = population_data[~np.isnan(population_data) & (population_data > 0)]
            total_population = valid_data.sum() if len(valid_data) > 0 else 0
            
            logger.info(f"Loaded 2025 population data: {population_data.shape} shape")
            logger.info(f"Population pixels: {len(valid_data)}, total population: {total_population:,.0f}")
            logger.info(f"Validation passed: {validation_passed}")
            
            return population_data
                
        except Exception as e:
            logger.error(f"Failed to load population data: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise
    
    def _apply_study_area_mask(self, data: np.ndarray, transform: rasterio.Affine, shape: Tuple[int, int]) -> np.ndarray:
        """Apply study area mask using NUTS boundaries and land mass data."""
        logger.info("Applying study area mask to population data...")
        
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
            transformer = RasterTransformer(target_crs=self.config.target_crs, config=self.config)
            resampling_method_str = (self.config.resampling_method.name.lower() 
                                   if hasattr(self.config.resampling_method, 'name') 
                                   else str(self.config.resampling_method).lower())
            
            land_mass_data, land_transform, _ = transformer.transform_raster(
                self.config.land_mass_path,
                reference_bounds=transformer.get_reference_bounds(nuts_l3_path),
                resampling_method=resampling_method_str
            )
            
            # Ensure land mass data is aligned with population data
            if not transformer.validate_alignment(land_mass_data, land_transform, data, transform):
                land_mass_data = transformer.ensure_alignment(
                    land_mass_data, land_transform, transform, shape,
                    resampling_method_str
                )
            
            # Create land mask (1=land, 0=water/no data)
            land_mask = (land_mass_data > 0).astype(np.uint8)
            logger.info(f"Created land mask: {np.sum(land_mask)} pixels identified as land")
            
            # Combine masks: only areas that are both within NUTS and on land
            combined_mask = (nuts_mask == 1) & (land_mask == 1)
            logger.info(f"Combined study area mask: {np.sum(combined_mask)} pixels in relevant study area")
            
            # Apply mask to population data
            masked_data = data.copy()
            masked_data[~combined_mask] = 0.0
            
            # Log masking statistics
            original_nonzero = np.sum(data > 0)
            masked_nonzero = np.sum(masked_data > 0)
            original_total = np.sum(data[data > 0]) if original_nonzero > 0 else 0
            masked_total = np.sum(masked_data[masked_data > 0]) if masked_nonzero > 0 else 0
            
            logger.info(f"Population masking removed {original_nonzero - masked_nonzero} non-zero pixels "
                       f"({(original_nonzero - masked_nonzero) / original_nonzero * 100:.1f}% reduction)")
            logger.info(f"Population total reduced from {original_total:,.0f} to {masked_total:,.0f} "
                       f"({(original_total - masked_total) / original_total * 100:.1f}% reduction)")
            
            return masked_data
            
        except Exception as e:
            logger.warning(f"Could not apply study area mask to population data: {str(e)}")
            logger.warning("Proceeding with unmasked population data")
            return data
    
    def load_hazard_scenario(self, scenario_name: str) -> Tuple[np.ndarray, dict]:
        """Load hazard data for a specific scenario."""
        hazard_path = self.config.output_dir / "hazard" / "tif" / f"flood_risk_{scenario_name.lower()}.tif"
        
        if not hazard_path.exists():
            raise FileNotFoundError(f"Hazard scenario not found: {hazard_path}")
        
        with rasterio.open(hazard_path) as src:
            hazard_data = src.read(1).astype(np.float32)
            meta = src.meta
        
        # Log hazard statistics
        valid_hazard = hazard_data[~np.isnan(hazard_data)]
        at_risk_pixels = np.sum(valid_hazard > self.max_safe_flood_risk)
        total_pixels = len(valid_hazard)
        risk_percentage = (at_risk_pixels / total_pixels * 100) if total_pixels > 0 else 0
        
        logger.info(f"Loaded {scenario_name} hazard: {at_risk_pixels}/{total_pixels} pixels at risk ({risk_percentage:.1f}%)")
        
        return hazard_data, meta
    
    def calculate_scenario_impact(self, hazard_data: np.ndarray, 
                                relevance_layers: Dict[str, np.ndarray], 
                                scenario_name: str) -> Dict[str, Dict[str, float]]:
        """Calculate economic impact for a specific scenario using flood risk threshold."""
        logger.info(f"Calculating economic impact for {scenario_name} scenario...")
        logger.info(f"Using flood risk threshold: {self.max_safe_flood_risk}")
        
        # Create risk mask where hazard exceeds threshold
        risk_mask = hazard_data > self.max_safe_flood_risk
        risk_pixel_count = np.sum(risk_mask)
        total_pixels = np.sum(~np.isnan(hazard_data))
        
        logger.info(f"Risk pixels: {risk_pixel_count}/{total_pixels} ({risk_pixel_count/total_pixels*100:.1f}%)")
        
        impact_results = {}
        
        for indicator in self.indicators:
            relevance_data = relevance_layers[indicator]
            
            # Ensure data alignment
            if relevance_data.shape != hazard_data.shape:
                logger.warning(f"Shape mismatch for {indicator}: {relevance_data.shape} vs {hazard_data.shape}")
                continue
                
            # Calculate total and at-risk values
            valid_mask = ~np.isnan(relevance_data) & (relevance_data > 0)
            
            total_value = np.sum(relevance_data[valid_mask])
            at_risk_value = np.sum(relevance_data[valid_mask & risk_mask])
            
            # Calculate percentages
            risk_percentage = (at_risk_value / total_value * 100) if total_value > 0 else 0
            safe_percentage = 100 - risk_percentage
            
            impact_results[indicator] = {
                'total_value': total_value,
                'at_risk_value': at_risk_value,
                'safe_value': total_value - at_risk_value,
                'risk_percentage': risk_percentage,
                'safe_percentage': safe_percentage
            }
            
            logger.info(f"{indicator.upper()} impact - Total: {total_value:,.0f}, At Risk: {at_risk_value:,.0f} ({risk_percentage:.1f}%)")
        
        return impact_results
    
    def create_impact_visualization(self, impact_results: Dict[str, Dict[str, float]], 
                                  scenario_name: str) -> None:
        """
        Create stacked vertical bar chart visualization for economic impact.
        
        Args:
            impact_results: Dictionary with impact results for each indicator
            scenario_name: Name of the scenario
        """
        logger.info(f"Creating impact visualization for scenario: {scenario_name}")
        
        # Create scenario output directory
        scenario_dir = self.config.output_dir / "economic_impact" / scenario_name.lower()
        scenario_dir.mkdir(parents=True, exist_ok=True)
        
        # Prepare data for visualization
        indicators = []
        total_values = []
        at_risk_values = []
        percentages_at_risk = []
        
        # Define indicator display names and units
        # Note: GDP data appears to already be in trillion EUR based on CSV values
        indicator_info = {
            'gdp': {'name': 'GDP', 'unit': 'trillion €', 'scale': 1_000_000},  # Data already in trillion
            'freight': {'name': 'Freight', 'unit': 'million tonnes', 'scale': 1_000_000},
            'hrst': {'name': 'Population (HRST)', 'unit': 'millions persons', 'scale': 1_000_000},  # Changed to millions
            'population': {'name': 'Population (GHS)', 'unit': 'millions persons', 'scale': 1_000_000}  # Added population
        }
        
        for indicator_key, results in impact_results.items():
            if indicator_key in indicator_info:
                info = indicator_info[indicator_key]
                indicators.append(info['name'])
                
                # For GDP, the data appears to already be in correct units (millions)
                # For freight and population, we still need to convert
                if indicator_key == 'gdp':
                    # GDP data is already in EUR, convert to millions
                    total_val = results['total_value'] / info['scale']
                    at_risk_val = results['at_risk_value'] / info['scale']
                else:
                    # Other indicators need scaling
                    total_val = results['total_value'] / info['scale']
                    at_risk_val = results['at_risk_value'] / info['scale']
                
                total_values.append(total_val)
                at_risk_values.append(at_risk_val)
                
                # Calculate percentage at risk
                if total_val > 0:
                    percentage = (at_risk_val / total_val) * 100
                else:
                    percentage = 0
                percentages_at_risk.append(percentage)
        
        if not indicators:
            logger.warning(f"No valid indicators found for visualization")
            return
        
        # Create vertical stacked bar chart with 0-100% scale
        # Red (at-risk) from bottom, grey (safe) on top
        fig, ax = plt.subplots(figsize=(12, 8), dpi=ScientificStyle.DPI)
        
        x_positions = np.arange(len(indicators))
        bar_width = 0.6
        
        # Create stacked bars with red from bottom
        # At-risk portion (red) starts from 0
        bars_risk = ax.bar(x_positions, percentages_at_risk, bar_width,
                          label='At Risk', color='red', alpha=0.8)
        
        # Safe portion (grey) starts from at-risk percentage
        safe_percentages = [100 - pct for pct in percentages_at_risk]
        bars_safe = ax.bar(x_positions, safe_percentages, bar_width,
                          bottom=percentages_at_risk, label='Safe', color='lightgrey', alpha=0.8)
        
        # Customize the plot
        ax.set_ylabel('Percentage (%)', fontsize=ScientificStyle.LABEL_SIZE)
        ax.set_xlabel('Economic Indicators', fontsize=ScientificStyle.LABEL_SIZE)
        ax.set_title(f'Economic Impact Analysis: {scenario_name.title()}', 
                    fontsize=ScientificStyle.TITLE_SIZE, fontweight='bold')
        ax.set_xticks(x_positions)
        ax.set_xticklabels(indicators, rotation=45, ha='right')
        ax.set_ylim(0, 100)
        ax.legend()
        
        # Add value annotations inside bars
        for i, (at_risk_pct, safe_pct, total_val, at_risk_val, indicator) in enumerate(
            zip(percentages_at_risk, safe_percentages, total_values, at_risk_values, indicators)):
            
            # Get unit info for this indicator
            info = next(info for key, info in indicator_info.items() 
                       if info['name'] == indicator)
            
            # Add total value annotation above the bar
            ax.text(i, 105, f'Total: {total_val:.1f} {info["unit"]}', 
                   ha='center', va='bottom', fontsize=9, fontweight='bold')
            
            # Add at-risk value annotation in the red section (if visible)
            if at_risk_pct > 10:  # Only show if section is big enough
                red_section_center = at_risk_pct / 2
                ax.text(i, red_section_center, f'{at_risk_val:.1f}\n{info["unit"]}', 
                       ha='center', va='center', fontsize=8, color='white', 
                       fontweight='bold')
            
            # Add percentage annotation in the red section
            if at_risk_pct > 5:  # Only show if section is visible
                ax.text(i, at_risk_pct - 2, f'{at_risk_pct:.1f}%', 
                       ha='center', va='top', fontsize=8, color='white',
                       fontweight='bold')
        
        ax.grid(axis='y', alpha=0.3)
        ax.set_axisbelow(True)
        
        plt.tight_layout()
        output_path = scenario_dir / f"economic_impact_{scenario_name.lower()}.png"
        plt.savefig(output_path, dpi=ScientificStyle.DPI, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        plt.close()
        
        logger.info(f"Saved impact visualization to {output_path}")
        
        # Log the actual values for debugging
        logger.info(f"Visualization data for {scenario_name}:")
        for i, indicator in enumerate(indicators):
            logger.info(f"  {indicator}: {at_risk_values[i]:.2f} / {total_values[i]:.2f} ({percentages_at_risk[i]:.1f}%)")
    
    def process_scenario(self, 
                        scenario_name: str,
                        create_visualizations: bool = True,
                        export_results: bool = True) -> Optional[EconomicImpactMetrics]:
        """
        Process a single flood risk scenario and calculate economic impacts.
        
        Args:
            scenario_name: Name of the scenario to process
            create_visualizations: Whether to create visualization plots
            export_results: Whether to export results to files
            
        Returns:
            Economic impact metrics for the scenario, or None if processing failed
        """
        try:
            logger.info(f"Loading hazard data for scenario: {scenario_name}")
            hazard_data, hazard_meta = self.load_hazard_scenario(scenario_name)
            
            if hazard_data is None:
                logger.error(f"Could not load hazard data for scenario: {scenario_name}")
                return None
            
            logger.info(f"Loading absolute relevance layers...")
            relevance_layers = self.load_absolute_relevance_layers()
            
            if not relevance_layers:
                logger.error(f"Could not load relevance layers for scenario: {scenario_name}")
                return None
            
            logger.info(f"Calculating economic impacts...")
            impact_results = self.calculate_scenario_impact(hazard_data, relevance_layers, scenario_name)
            
            # Create metrics object
            metrics = EconomicImpactMetrics(
                scenario_name=scenario_name,
                total_gdp_millions_eur=impact_results['gdp']['total_value'] / 1_000_000,
                at_risk_gdp_millions_eur=impact_results['gdp']['at_risk_value'] / 1_000_000,
                total_freight_tonnes=impact_results['freight']['total_value'],
                at_risk_freight_tonnes=impact_results['freight']['at_risk_value'],
                total_population_persons=impact_results['hrst']['total_value'],
                at_risk_population_persons=impact_results['hrst']['at_risk_value'],
                total_hrst_persons=impact_results['hrst']['total_value'],
                at_risk_hrst_persons=impact_results['hrst']['at_risk_value'],
                total_population_ghs_persons=impact_results['population']['total_value'],
                at_risk_population_ghs_persons=impact_results['population']['at_risk_value'],
                cluster_count=0,  # Will be updated if cluster analysis is available
                total_risk_area_square_kilometers=0.0  # Will be calculated from risk mask
            )
            
            # Calculate risk area
            risk_mask = hazard_data > self.max_safe_flood_risk
            risk_pixels = np.sum(risk_mask)
            pixel_area_square_meters = self.config.target_resolution ** 2
            metrics.total_risk_area_square_kilometers = (risk_pixels * pixel_area_square_meters) / 1_000_000
            
            if create_visualizations:
                logger.info(f"Creating visualization for scenario: {scenario_name}")
                self.create_impact_visualization(impact_results, scenario_name)
            
            if export_results:
                logger.info(f"Exporting results for scenario: {scenario_name}")
                self.export_scenario_data(impact_results, scenario_name)
            
            # Log summary statistics
            logger.info(f"Scenario {scenario_name} summary:")
            logger.info(f"  GDP at risk: {metrics.at_risk_gdp_millions_eur:.1f}M EUR ({metrics.at_risk_gdp_millions_eur/metrics.total_gdp_millions_eur*100:.1f}%)")
            logger.info(f"  Freight at risk: {metrics.at_risk_freight_tonnes:.0f} tonnes ({metrics.at_risk_freight_tonnes/metrics.total_freight_tonnes*100:.1f}%)")
            logger.info(f"  Population at risk: {metrics.at_risk_population_persons:.0f} persons ({metrics.at_risk_population_persons/metrics.total_population_persons*100:.1f}%)")
            logger.info(f"  Risk area: {metrics.total_risk_area_square_kilometers:.1f} km²")
            
            return metrics
                    
        except Exception as e:
            logger.error(f"Error processing scenario {scenario_name}: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return None
    
    def run_economic_impact_analysis(self, 
                                   create_visualizations: bool = True,
                                   export_results: bool = True) -> List[EconomicImpactMetrics]:
        """
        Run complete economic impact analysis for all flood risk scenarios.
        
        Args:
            create_visualizations: Whether to create visualization plots
            export_results: Whether to export results to files
            
        Returns:
            List of economic impact metrics for each scenario
        """
        logger.info("Starting comprehensive economic impact analysis...")
        logger.info(f"Processing {len(self.hazard_scenarios)} flood risk scenarios")
        logger.info(f"Target flood risk threshold: {self.max_safe_flood_risk}")
        
        all_metrics = []
        
        for scenario_name in self.hazard_scenarios:
            logger.info(f"\n{'='*50}")
            logger.info(f"Processing scenario: {scenario_name}")
            logger.info(f"{'='*50}")
            
            metrics = self.process_scenario(scenario_name, create_visualizations, export_results)
            if metrics:
                all_metrics.append(metrics)
                logger.info(f"[SUCCESS] Completed scenario: {scenario_name}")
            else:
                logger.warning(f"[FAILED] Failed to process scenario: {scenario_name}")
        
        if export_results:
            self.create_summary_report(all_metrics)
        
        logger.info(f"\n{'='*60}")
        logger.info("ECONOMIC IMPACT ANALYSIS COMPLETE")
        logger.info(f"{'='*60}")
        logger.info(f"Successfully processed {len(all_metrics)}/{len(self.hazard_scenarios)} scenarios")
        
        return all_metrics
    
    def create_summary_report(self, all_metrics: List[EconomicImpactMetrics]) -> None:
        """Create summary report with all scenario metrics."""
        logger.info("Creating summary report...")
        
        summary_data = []
        for metrics in all_metrics:
            summary_data.append({
                'scenario': metrics.scenario_name,
                'total_gdp_millions_eur': metrics.total_gdp_millions_eur,
                'at_risk_gdp_millions_eur': metrics.at_risk_gdp_millions_eur,
                'total_freight_tonnes': metrics.total_freight_tonnes,
                'at_risk_freight_tonnes': metrics.at_risk_freight_tonnes,
                'total_population_persons': metrics.total_population_persons,
                'at_risk_population_persons': metrics.at_risk_population_persons,
                'total_hrst_persons': metrics.total_hrst_persons,
                'at_risk_hrst_persons': metrics.at_risk_hrst_persons,
                'total_population_ghs_persons': metrics.total_population_ghs_persons,
                'at_risk_population_ghs_persons': metrics.at_risk_population_ghs_persons,
                'cluster_count': metrics.cluster_count,
                'total_risk_area_square_kilometers': metrics.total_risk_area_square_kilometers
            })
        
        # Create summary directory
        summary_dir = self.config.output_dir / "economic_impact" / "summary"
        summary_dir.mkdir(parents=True, exist_ok=True)
        
        # Export to CSV
        summary_df = pd.DataFrame(summary_data)
        csv_path = summary_dir / "economic_impact_summary.csv"
        summary_df.to_csv(csv_path, index=False)
        
        logger.info(f"Saved summary report to {csv_path}")
        logger.info("Summary report completed")

    def export_scenario_data(self, impact_results: Dict[str, Dict[str, float]], scenario_name: str) -> None:
        """Export scenario data to CSV file."""
        logger.info(f"Exporting data for scenario: {scenario_name}")
        
        # Create scenario output directory
        scenario_dir = self.config.output_dir / "economic_impact" / scenario_name.lower()
        scenario_dir.mkdir(parents=True, exist_ok=True)
        
        # Prepare data for CSV
        csv_data = []
        for indicator, results in impact_results.items():
            csv_data.append({
                'scenario': scenario_name,
                'indicator': indicator.upper(),
                'total_value': results['total_value'],
                'at_risk_value': results['at_risk_value'],
                'safe_value': results['safe_value'],
                'risk_percentage': results['risk_percentage'],
                'safe_percentage': results['safe_percentage'],
                'flood_risk_threshold': self.max_safe_flood_risk
            })
        
        # Save as CSV
        df = pd.DataFrame(csv_data)
        csv_path = scenario_dir / f"economic_impact_{scenario_name.lower()}.csv"
        df.to_csv(csv_path, index=False)
        
        logger.info(f"Saved impact data to {csv_path}")


def run_economic_impact_analysis_from_config(config: ProjectConfig) -> Dict[str, Dict[str, Dict[str, float]]]:
    """
    Convenience function to run the complete economic impact analysis.
    
    Args:
        config: Project configuration
        
    Returns:
        Results for all scenarios
    """
    analyzer = EconomicImpactAnalyzer(config)
    return analyzer.run_economic_impact_analysis() 