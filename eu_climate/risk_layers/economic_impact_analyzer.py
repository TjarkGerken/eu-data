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
from eu_climate.utils.visualization import LayerVisualizer, ScientificStyle
from eu_climate.risk_layers.cluster_layer import ClusterLayer
from eu_climate.risk_layers.relevance_layer import RelevanceLayer

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
        """Extract population values from cluster using original population raster."""
        try:
            with rasterio.open(self.config.population_path) as src:
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
        """Extract total population from the GHS population raster."""
        try:
            with rasterio.open(self.config.population_path) as src:
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
    """Main analyzer that coordinates economic impact assessment."""
    
    def __init__(self, config: ProjectConfig):
        self.config = config
        self.cluster_layer = ClusterLayer(config)
        self.relevance_layer = RelevanceLayer(config)
        self.zonal_extractor = ZonalStatisticsExtractor(config)
        self.nuts_aggregator = NutsDataAggregator(config)
        self.visualizer = EconomicImpactVisualizer(config)
        self.exporter = EconomicImpactExporter(config)
        
    def run_complete_impact_analysis(self, 
                                   create_visualizations: bool = True,
                                   export_results: bool = True) -> List[EconomicImpactMetrics]:
        """Run economic impact analysis with true sequential processing: one scenario at a time."""
        logger.info("Starting sequential scenario-by-scenario economic impact analysis")
        logger.info("Processing only GDP, Population, and Freight (combined) indicators")
        
        # Get list of scenario directories
        risk_output_dir = Path(self.config.output_dir) / "risk"
        if not risk_output_dir.exists():
            logger.warning("No risk output directory found")
            return []
            
        scenario_dirs = [d for d in risk_output_dir.iterdir() if d.is_dir()]
        if not scenario_dirs:
            logger.warning("No scenario directories found")
            return []
            
        # Get total regional economic values once
        total_regional_values = self.nuts_aggregator.get_total_regional_values()
        impact_metrics = []
        
        # Process each scenario COMPLETELY before moving to next
        for scenario_dir in sorted(scenario_dirs):
            scenario_name = scenario_dir.name
            logger.info(f"\n{'='*80}")
            logger.info(f"PROCESSING SCENARIO: {scenario_name}")
            logger.info(f"{'='*80}")
            
            # Get valid risk files (only GDP, Population, Freight)
            scenario_cluster_files = self._get_scenario_risk_files(scenario_dir)
            if not scenario_cluster_files:
                logger.warning(f"⚠ No valid risk files found for {scenario_name}")
                continue
                
            logger.info(f"Found {len(scenario_cluster_files)} indicators: {list(scenario_cluster_files.keys())}")
            
            # STEP 1: CALCULATE CLUSTERS for this scenario
            logger.info(f"\n-> STEP 1: Calculate clusters for {scenario_name}")
            scenario_clusters = {}
            
            for file_key, file_path in scenario_cluster_files.items():
                logger.info(f"  -> Processing clusters from: {file_key}")
                cluster_result = self.cluster_layer._process_single_risk_file(file_path, file_key)
                
                if not cluster_result.empty:
                    indicator = self._extract_indicator_from_filename(file_key)
                    scenario_clusters[indicator] = cluster_result
                    logger.info(f"  * Extracted {len(cluster_result)} clusters for {indicator}")
                else:
                    logger.info(f"  ! No clusters found in {file_key}")
            
            if not scenario_clusters:
                logger.warning(f"! No clusters extracted for {scenario_name}")
                continue
                
            # STEP 2: CALCULATE ECONOMIC IMPACT for this scenario
            logger.info(f"\n-> STEP 2: Calculate economic impact for {scenario_name}")
            metrics = self._analyze_scenario_with_indicators(
                scenario_name, scenario_clusters, total_regional_values
            )
            
            if not metrics:
                logger.warning(f"! Failed to calculate metrics for {scenario_name}")
                continue
                
            impact_metrics.append(metrics)
            logger.info(f"* Economic impact calculated for {scenario_name}")
            
            # STEP 3: VISUALIZE for this scenario
            if create_visualizations:
                logger.info(f"\n-> STEP 3: Create visualization for {scenario_name}")
                self._create_single_scenario_visualization(metrics)
                logger.info(f"* Visualization created for {scenario_name}")
            
            # STEP 4: EXPORT for this scenario
            if export_results:
                logger.info(f"\n-> STEP 4: Export results for {scenario_name}")
                self._export_scenario_results(scenario_name, scenario_clusters)
                logger.info(f"* Results exported for {scenario_name}")
                
            logger.info(f"\n* SCENARIO {scenario_name} COMPLETE")
        
        # Final summary export
        if export_results and impact_metrics:
            logger.info(f"\n{'='*80}")
            logger.info("EXPORTING SUMMARY RESULTS")
            logger.info(f"{'='*80}")
            self._export_summary_results(impact_metrics)
            logger.info("✓ Summary results exported")
        
        logger.info(f"\n{'='*80}")
        logger.info(f"ECONOMIC IMPACT ANALYSIS COMPLETE")
        logger.info(f"Processed {len(impact_metrics)} scenarios successfully")
        logger.info(f"{'='*80}")
        return impact_metrics
        
    def _get_scenario_risk_files(self, scenario_dir: Path) -> Dict[str, str]:
        """Get valid risk files for a single scenario (GDP, Population, Freight only)."""
        tif_dir = scenario_dir / "tif"
        if not tif_dir.exists():
            return {}
            
        scenario_files = {}
        for tif_file in tif_dir.glob("risk_*.tif"):
            file_stem = tif_file.stem
            
            # Use same filtering logic as cluster layer
            if not self.cluster_layer._should_skip_file(file_stem):
                scenario_files[file_stem] = str(tif_file)
                
        return scenario_files
        
    def _extract_indicator_from_filename(self, filename: str) -> str:
        """Extract indicator name from risk filename."""
        filename_lower = filename.lower()
        if '_gdp' in filename_lower:
            return 'GDP'
        elif '_population' in filename_lower:
            return 'POPULATION'  
        elif '_freight' in filename_lower:
            return 'FREIGHT'
        else:
            return 'UNKNOWN'
    
    def _group_clusters_by_scenario(self, cluster_results: Dict[str, gpd.GeoDataFrame]) -> Dict[str, Dict[str, gpd.GeoDataFrame]]:
        """Group risk layer results by scenario (e.g., SLR-0-Current, SLR-1-Conservative)."""
        scenarios = {}
        
        for layer_name, cluster_gdf in cluster_results.items():
            scenario_parts = layer_name.split('_')
            if len(scenario_parts) >= 3:
                scenario_name = '_'.join(scenario_parts[1:3])
                indicator = '_'.join(scenario_parts[3:]) if len(scenario_parts) > 3 else 'COMBINED'
                
                if scenario_name not in scenarios:
                    scenarios[scenario_name] = {}
                    
                scenarios[scenario_name][indicator] = cluster_gdf
                
        logger.info(f"Grouped clusters into {len(scenarios)} scenarios: {list(scenarios.keys())}")
        return scenarios
    
    def _analyze_scenario_with_indicators(self,
                                         scenario_name: str,
                                         scenario_clusters: Dict[str, gpd.GeoDataFrame],
                                         total_regional_values: Dict[str, float]) -> Optional[EconomicImpactMetrics]:
        """Analyze economic impact for a scenario across all its indicators."""
        logger.info(f"Analyzing economic impact for scenario: {scenario_name}")
        
        at_risk_values = {
            'gdp': 0.0,
            'freight': 0.0,
            'population': 0.0,
            'hrst': 0.0
        }
        
        total_clusters = 0
        total_area = 0.0
        
        for indicator, cluster_gdf in scenario_clusters.items():
            if cluster_gdf.empty:
                logger.info(f"    → Skipping {indicator}: no clusters")
                continue
                
            indicator_key = self._map_indicator_to_key(indicator)
            if indicator_key not in at_risk_values:
                logger.info(f"    → Skipping {indicator}: unmapped indicator")
                continue
                
            logger.info(f"    -> Processing {len(cluster_gdf)} clusters for {indicator}")
            
            if indicator_key == 'population':
                at_risk_value = self._extract_population_from_clusters(cluster_gdf)
            else:
                at_risk_value = self._extract_indicator_values_from_clusters(
                    cluster_gdf, indicator_key
                )
            
            at_risk_values[indicator_key] = at_risk_value
            total_clusters += len(cluster_gdf)
            total_area += cluster_gdf['cluster_area_square_meters'].sum()
            
            logger.info(f"    * Extracted {at_risk_value:,.0f} at-risk {indicator_key} from {len(cluster_gdf)} clusters")
        
        return EconomicImpactMetrics(
            scenario_name=scenario_name,
            total_gdp_millions_eur=total_regional_values.get('gdp', 0),
            at_risk_gdp_millions_eur=at_risk_values['gdp'],
            total_freight_tonnes=total_regional_values.get('freight', 0),
            at_risk_freight_tonnes=at_risk_values['freight'],
            total_population_persons=total_regional_values.get('population', 0),
            at_risk_population_persons=at_risk_values['population'],
            total_hrst_persons=total_regional_values.get('hrst', 0),
            at_risk_hrst_persons=at_risk_values['hrst'],
            cluster_count=total_clusters,
            total_risk_area_square_kilometers=total_area / 1_000_000
        )
    
    def _map_indicator_to_key(self, indicator: str) -> str:
        """Map indicator names to standard keys."""
        indicator_lower = indicator.lower()
        if 'gdp' in indicator_lower:
            return 'gdp'
        elif 'freight' in indicator_lower:
            return 'freight'
        elif 'population' in indicator_lower:
            return 'population'
        elif 'hrst' in indicator_lower:
            return 'hrst'
        else:
            return 'unknown'
    
    def _extract_population_from_clusters(self, cluster_gdf: gpd.GeoDataFrame) -> float:
        """Extract population values from clusters using original population raster."""
        total_population = 0.0
        
        try:
            with rasterio.open(self.config.population_path) as src:
                population_data = src.read(1).astype(np.float32)
                logger.info(f"Population raster shape: {population_data.shape}, CRS: {src.crs}")
                logger.info(f"Population raster stats: min={np.nanmin(population_data):.2f}, max={np.nanmax(population_data):.2f}, nonzero={np.count_nonzero(population_data)}")
                
                # Ensure cluster geometries are in same CRS as raster
                cluster_gdf_reprojected = cluster_gdf.to_crs(src.crs)
                logger.info(f"Reprojected clusters from {cluster_gdf.crs} to {src.crs}")
                
                for idx, cluster_row in cluster_gdf_reprojected.iterrows():
                    cluster_geometry = cluster_row['geometry']
                    
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
                    
                    cluster_population = float(valid_values.sum()) if len(valid_values) > 0 else 0.0
                    total_population += cluster_population
                    
                    if idx < 3:  # Debug first few clusters
                        logger.info(f"Cluster {idx}: mask_pixels={np.count_nonzero(polygon_mask)}, valid_values={len(valid_values)}, population={cluster_population:.0f}")
                    
                logger.info(f"Total population extracted from {len(cluster_gdf_reprojected)} clusters: {total_population:.0f}")
                    
        except Exception as e:
            logger.error(f"Failed to extract population from clusters: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
        return total_population
    
    def _extract_indicator_values_from_clusters(self, 
                                              cluster_gdf: gpd.GeoDataFrame,
                                              indicator_key: str) -> float:
        """Extract indicator values from clusters using relevance layers."""
        try:
            relevance_layers, relevance_metadata = self.relevance_layer.calculate_relevance([indicator_key])
            
            if indicator_key not in relevance_layers:
                logger.warning(f"Indicator {indicator_key} not found in relevance layers")
                return 0.0
            
            layer_data = relevance_layers[indicator_key]
            total_value = 0.0
            
            for _, cluster_row in cluster_gdf.iterrows():
                cluster_geometry = cluster_row['geometry']
                
                extracted_value = self.zonal_extractor._perform_zonal_extraction(
                    cluster_geometry, layer_data, relevance_metadata
                )
                total_value += extracted_value
                
            return total_value
            
        except Exception as e:
            logger.error(f"Failed to extract {indicator_key} values: {e}")
            return 0.0
    
    def _calculate_at_risk_totals(self, extracted_values: pd.DataFrame) -> Dict[str, float]:
        """Calculate total at-risk values across all clusters."""
        at_risk_totals = {}
        
        for column in extracted_values.columns:
            if column.endswith('_absolute'):
                indicator = column.replace('_absolute', '')
                at_risk_totals[indicator] = extracted_values[column].sum()
                
        return at_risk_totals
    
    def _enhance_clusters_with_economics(self, 
                                       cluster_geodataframe: gpd.GeoDataFrame,
                                       relevance_layers: Dict[str, np.ndarray],
                                       relevance_metadata: dict) -> gpd.GeoDataFrame:
        """Enhance cluster polygons with extracted economic values."""
        extracted_values = self.zonal_extractor.extract_values_from_clusters(
            cluster_geodataframe, relevance_layers, relevance_metadata
        )
        
        if extracted_values.empty:
            return cluster_geodataframe
            
        enhanced_clusters = cluster_geodataframe.merge(
            extracted_values, 
            left_on='risk_cluster_id', 
            right_on='cluster_id',
            how='left'
        )
        
        return enhanced_clusters
    
    def _create_single_scenario_visualization(self, metrics: EconomicImpactMetrics) -> None:
        """Create visualization for a single scenario immediately after calculation."""
        self.visualizer._create_single_scenario_plot(metrics)
    
    def _export_scenario_results(self, 
                                scenario_name: str,
                                scenario_clusters: Dict[str, gpd.GeoDataFrame]) -> None:
        """Export results for a scenario with all its indicators."""
        for indicator, cluster_gdf in scenario_clusters.items():
            if cluster_gdf.empty:
                continue
                
            gpkg_path = self.exporter.output_dir / f"clusters_{scenario_name}_{indicator}.gpkg"
            cluster_gdf.to_file(gpkg_path, driver='GPKG')
            logger.info(f"Exported {indicator} clusters to: {gpkg_path}")
    
    def _export_summary_results(self, impact_metrics: List[EconomicImpactMetrics]) -> None:
        """Export summary results after all scenarios are processed."""
        self.exporter._export_summary_csv(impact_metrics) 