from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import rasterio
import geopandas as gpd
from pathlib import Path
from dataclasses import dataclass
import re

from eu_climate.config.config import ProjectConfig
from eu_climate.utils.utils import setup_logging
from eu_climate.utils.visualization import LayerVisualizer
from eu_climate.utils.caching_wrappers import CacheAwareMethod
from eu_climate.utils.clustering_utils import RiskClusterExtractor, RiskClusterAnalyzer
from eu_climate.utils.web_export_mixin import WebExportMixin
from eu_climate.risk_layers.hazard_layer import SeaLevelScenario

logger = setup_logging(__name__)


@dataclass
class ClusterConfiguration:
    """Configuration parameters for risk clustering."""
    risk_threshold: float = 0.25
    cell_size_meters: float = 30
    morphological_closing_disk_size: int = 3
    cluster_epsilon_multiplier: float = 1.5
    minimum_samples: int = 4
    alpha_parameter_divisor: float = 1.0
    hole_area_threshold: float = 0.10
    minimum_polygon_area_square_meters: float = 5000
    smoothing_buffer_meters: float = 45
    polygon_simplification_tolerance: float = 15
    natural_smoothing_iterations: int = 2
    corner_rounding_radius: float = 30
    use_contour_method: bool = False
    export_formats: List[str] = None
    
    def __post_init__(self):
        if self.export_formats is None:
            self.export_formats = ['gpkg', 'png']


class ClusterLayer(WebExportMixin):
    """
    Cluster Layer Implementation
    ===========================
    
    The Cluster Layer processes risk assessment results to identify and extract
    clean polygons of high-risk economic areas using DBSCAN clustering and
    alpha-shape polygon generation.
    
    Key Features:
    - Risk cluster extraction from raster data
    - Integration with existing risk layer outputs
    - Statistical analysis of risk clusters
    - Visualization and export of cluster polygons
    - Consistent directory structure following risk layer patterns
    """
    
    def __init__(self, config: ProjectConfig):
        """Initialize the Cluster Layer with project configuration."""
        super().__init__()
        self.config = config
        self.cluster_config = self._load_cluster_configuration()
        
        self.visualizer = LayerVisualizer(self.config)
        self.cluster_extractor = RiskClusterExtractor(
            risk_threshold=self.cluster_config.risk_threshold,
            cell_size_meters=self.cluster_config.cell_size_meters,
            morphological_closing_disk_size=self.cluster_config.morphological_closing_disk_size,
            cluster_epsilon_multiplier=self.cluster_config.cluster_epsilon_multiplier,
            minimum_samples=self.cluster_config.minimum_samples,
            alpha_parameter_divisor=self.cluster_config.alpha_parameter_divisor,
            hole_area_threshold=self.cluster_config.hole_area_threshold,
            minimum_polygon_area_square_meters=self.cluster_config.minimum_polygon_area_square_meters,
            smoothing_buffer_meters=self.cluster_config.smoothing_buffer_meters,
            polygon_simplification_tolerance=self.cluster_config.polygon_simplification_tolerance,
            natural_smoothing_iterations=self.cluster_config.natural_smoothing_iterations,
            corner_rounding_radius=self.cluster_config.corner_rounding_radius,
            use_contour_method=getattr(self.cluster_config, 'use_contour_method', False)
        )
        self.cluster_analyzer = RiskClusterAnalyzer()
        
        logger.info("Initialized Cluster Layer with configurable smoothing parameters")
    
    def _load_cluster_configuration(self) -> ClusterConfiguration:
        """Load cluster configuration from project config."""
        clustering_config = getattr(self.config, 'clustering', {})
        
        logger.info(f"Loading clustering configuration: {clustering_config}")
        
        config = ClusterConfiguration(
            risk_threshold=clustering_config.get('risk_threshold', 0.25),
            cell_size_meters=clustering_config.get('cell_size_meters', 30),
            morphological_closing_disk_size=clustering_config.get('morphological_closing_disk_size', 3),
            cluster_epsilon_multiplier=clustering_config.get('cluster_epsilon_multiplier', 1.5),
            minimum_samples=clustering_config.get('minimum_samples', 4),
            alpha_parameter_divisor=clustering_config.get('alpha_parameter_divisor', 1.0),
            hole_area_threshold=clustering_config.get('hole_area_threshold', 0.10),
            minimum_polygon_area_square_meters=clustering_config.get('minimum_polygon_area_square_meters', 5000),
            smoothing_buffer_meters=clustering_config.get('smoothing_buffer_meters', 45),
            polygon_simplification_tolerance=clustering_config.get('polygon_simplification_tolerance', 15),
            natural_smoothing_iterations=clustering_config.get('natural_smoothing_iterations', 2),
            corner_rounding_radius=clustering_config.get('corner_rounding_radius', 30),
            use_contour_method=clustering_config.get('use_contour_method', False),
            export_formats=clustering_config.get('export_formats', ['gpkg', 'png'])
        )
        
        logger.info(f"Applied clustering parameters:")
        logger.info(f"  - risk_threshold: {config.risk_threshold}")
        logger.info(f"  - cluster_epsilon_multiplier: {config.cluster_epsilon_multiplier}")
        logger.info(f"  - minimum_samples: {config.minimum_samples}")
        logger.info(f"  - minimum_polygon_area_square_meters: {config.minimum_polygon_area_square_meters}")
        logger.info(f"  - smoothing_buffer_meters: {config.smoothing_buffer_meters}")
        
        return config
    
    def load_existing_risk_outputs(self) -> Dict[str, Dict[str, str]]:
        """Load paths to existing risk output files with freight filtering."""
        risk_output_dir = Path(self.config.output_dir) / "risk"
        
        if not risk_output_dir.exists():
            logger.warning(f"Risk output directory not found: {risk_output_dir}")
            return {}
        
        risk_file_paths = {}
        
        for scenario_dir in risk_output_dir.iterdir():
            if not scenario_dir.is_dir():
                continue
                
            scenario_name = scenario_dir.name
            tif_dir = scenario_dir / "tif"
            
            if not tif_dir.exists():
                continue
                
            scenario_files = {}
            for tif_file in tif_dir.glob("risk_*.tif"):
                file_stem = tif_file.stem
                
                if self._should_skip_file(file_stem):
                    logger.info(f"Skipping file: {file_stem}")
                    continue
                    
                scenario_files[file_stem] = str(tif_file)
            
            if scenario_files:
                risk_file_paths[scenario_name] = scenario_files
        
        logger.info(f"Found risk outputs for {len(risk_file_paths)} scenarios")
        return risk_file_paths
    
    def _should_skip_file(self, file_stem: str) -> bool:
        """Only process GDP, Population, and Freight (combined) for economic impact analysis."""
        filename_lower = file_stem.lower()
        
        # Only keep these three specific indicators
        allowed_indicators = [
            '_gdp',
            '_population', 
            '_freight'  # Only combined freight, not loading/unloading
        ]
        
        # Check if file contains any allowed indicator
        for indicator in allowed_indicators:
            if indicator in filename_lower:
                # Special check for freight - skip loading/unloading variants
                if indicator == '_freight':
                    if '_loading' in filename_lower or '_unloading' in filename_lower:
                        return True  # Skip freight loading/unloading
                return False  # Keep this file
                
        # Skip all other files (COMBINED, HRST, etc.)
        return True
    
    def parse_risk_filename(self, filename: str) -> Tuple[str, str, Optional[str]]:
        """Parse risk filename to extract scenario and economic components."""
        filename_without_extension = filename.replace('.tif', '').replace('risk_', '')
        
        slr_pattern = r'^(SLR-\d+-[^_]+)'
        match = re.match(slr_pattern, filename_without_extension)
        
        if not match:
            logger.warning(f"Could not parse filename: {filename}")
            return filename_without_extension, "", None
            
        slr_scenario = match.group(1)
        
        if len(filename_without_extension) > len(slr_scenario) and filename_without_extension[len(slr_scenario)] == '_':
            economic_indicator = filename_without_extension[len(slr_scenario) + 1:]
        else:
            economic_indicator = None
            
        return slr_scenario, economic_indicator or "", filename_without_extension
    
    @CacheAwareMethod(cache_type='cluster_results',
                     input_files=['output_dir'],
                     config_attrs=['target_crs', 'clustering'])
    def process_risk_clusters_sequential(self, 
                                       custom_risk_files: Optional[Dict[str, str]] = None,
                                       visualize: bool = True) -> Dict[str, gpd.GeoDataFrame]:
        """Process risk outputs to extract clusters using sequential pattern: calculate -> visualize -> write."""
        logger.info("Starting sequential cluster processing: calculate -> visualize -> write per scenario")
        
        if custom_risk_files:
            risk_file_paths = {"custom": custom_risk_files}
        else:
            risk_file_paths = self.load_existing_risk_outputs()
            
        if not risk_file_paths:
            logger.warning("No risk outputs found for cluster processing")
            return {}
        
        all_cluster_results = {}
        
        for scenario_name, scenario_files in risk_file_paths.items():
            logger.info(f"\n-> Processing scenario: {scenario_name}")
            
            for file_key, file_path in scenario_files.items():
                logger.info(f"  -> Calculate clusters for: {file_key}")
                
                cluster_result = self._process_single_risk_file(file_path, file_key)
                
                if not cluster_result.empty:
                    all_cluster_results[file_key] = cluster_result
                    logger.info(f"  + Calculated: {len(cluster_result)} clusters")
                    
                    logger.info(f"  -> Visualize & Write: {file_key}")
                    self._export_single_cluster_result(file_key, cluster_result, visualize)
                    logger.info(f"  + Completed processing for: {file_key}")
                else:
                    logger.info(f"  ! No clusters found in: {file_key}")
                    
            logger.info(f"+ Scenario {scenario_name} complete")
        
        logger.info(f"\n+ Sequential cluster processing complete: {len(all_cluster_results)} scenarios processed")
        return all_cluster_results
    
    def process_risk_clusters(self, 
                             custom_risk_files: Optional[Dict[str, str]] = None) -> Dict[str, gpd.GeoDataFrame]:
        """Legacy batch processing method - processes all clusters without plotting."""
        logger.info("Processing risk clusters from existing outputs (batch mode)...")
        
        if custom_risk_files:
            risk_file_paths = {"custom": custom_risk_files}
        else:
            risk_file_paths = self.load_existing_risk_outputs()
            
        if not risk_file_paths:
            logger.warning("No risk outputs found for cluster processing")
            return {}
        
        all_cluster_results = {}
        
        for scenario_name, scenario_files in risk_file_paths.items():
            logger.info(f"Processing clusters for scenario: {scenario_name}")
            
            for file_key, file_path in scenario_files.items():
                cluster_result = self._process_single_risk_file(file_path, file_key)
                
                if not cluster_result.empty:
                    all_cluster_results[file_key] = cluster_result
                    logger.info(f"Extracted {len(cluster_result)} clusters from {file_key}")
                else:
                    logger.info(f"No clusters found in {file_key}")
        
        logger.info(f"Processed clusters for {len(all_cluster_results)} risk scenarios")
        return all_cluster_results
    
    def _process_single_risk_file(self, file_path: str, file_key: str) -> gpd.GeoDataFrame:
        """Process a single risk file to extract clusters."""
        try:
            with rasterio.open(file_path) as risk_source:
                risk_data = risk_source.read(1)
                transform = risk_source.transform
                crs = risk_source.crs
                
            clusters = self.cluster_extractor.extract_risk_clusters(
                risk_data=risk_data,
                transform=transform,
                target_crs=str(crs)
            )
            
            if not clusters.empty:
                enhanced_clusters = self.cluster_analyzer.enhance_clusters_with_statistics(
                    cluster_geodataframe=clusters,
                    risk_data=risk_data,
                    transform=transform
                )
                return enhanced_clusters
                
        except Exception as e:
            logger.error(f"Failed to process risk file {file_path}: {e}")
            
        return gpd.GeoDataFrame({'geometry': [], 'risk_cluster_id': []}, crs=self.config.target_crs)
    
    def export_cluster_results(self, 
                              cluster_results: Dict[str, gpd.GeoDataFrame],
                              create_visualizations: bool = True) -> None:
        """Legacy batch export method - exports all cluster results at once."""
        logger.info("Exporting cluster results (batch mode)...")
        
        for file_key, cluster_geodataframe in cluster_results.items():
            if cluster_geodataframe.empty:
                logger.info(f"Skipping empty cluster result: {file_key}")
                continue
                
            self._export_single_cluster_result(file_key, cluster_geodataframe, create_visualizations)
        
        logger.info("Batch cluster export complete")
    
    def _export_single_cluster_result(self, 
                                    file_key: str, 
                                    cluster_geodataframe: gpd.GeoDataFrame,
                                    create_visualizations: bool,
                                    create_web_formats: bool = True) -> None:
        """Export single cluster result with proper directory structure and web formats."""
        slr_scenario, economic_indicator, full_scenario_name = self.parse_risk_filename(file_key)
        
        output_dir = self._create_cluster_output_directory(slr_scenario)
        
        cluster_filename = f"clusters_{full_scenario_name}"
        
        if 'gpkg' in self.cluster_config.export_formats:
            gpkg_path = output_dir / "gpkg" / f"{cluster_filename}.gpkg"
            gpkg_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Use the web export mixin to save both legacy and web formats
            results = self.save_vector_with_web_exports(
                gdf=cluster_geodataframe,
                output_path=gpkg_path,
                layer_name=cluster_filename,
                create_web_formats=create_web_formats
            )
            
            if results.get('gpkg', False):
                logger.info(f"Saved cluster GeoPackage: {gpkg_path}")
            if results.get('mvt', False):
                logger.info(f"Created web-optimized MVT for cluster: {cluster_filename}")
        
        if create_visualizations and 'png' in self.cluster_config.export_formats:
            png_path = output_dir / f"{cluster_filename}.png"
            self._create_cluster_visualization(cluster_geodataframe, png_path, full_scenario_name)
    
    def _create_cluster_output_directory(self, slr_scenario: str) -> Path:
        """Create output directory following risk layer structure."""
        cluster_output_dir = self.config.output_dir / "clusters" / slr_scenario
        cluster_output_dir.mkdir(parents=True, exist_ok=True)
        return cluster_output_dir
    
    def _create_cluster_visualization(self, 
                                    cluster_geodataframe: gpd.GeoDataFrame,
                                    output_path: Path,
                                    scenario_title: str) -> None:
        """Create visualization of cluster polygons."""
        import matplotlib.pyplot as plt
        from eu_climate.utils.visualization import ScientificStyle
        
        fig, ax = plt.subplots(figsize=ScientificStyle.FIGURE_SIZE, dpi=ScientificStyle.DPI)
        
        nuts_geodataframe = self.visualizer.get_nuts_boundaries("L3")
        if nuts_geodataframe is not None:
            nuts_geodataframe.boundary.plot(
                ax=ax,
                color=ScientificStyle.NUTS_BOUNDARY_COLOR,
                linewidth=ScientificStyle.NUTS_BOUNDARY_WIDTH,
                alpha=ScientificStyle.NUTS_BOUNDARY_ALPHA,
                zorder=1
            )
        
        cluster_geodataframe.plot(
            ax=ax,
            facecolor='red',
            edgecolor='darkred',
            alpha=0.7,
            linewidth=1,
            zorder=10
        )
        
        cluster_count = len(cluster_geodataframe)
        total_area = cluster_geodataframe['cluster_area_square_meters'].sum() / 1_000_000
        
        title = f"Risk Clusters: {scenario_title.replace('_', ' ').title()}"
        ax.set_title(title, fontsize=ScientificStyle.TITLE_SIZE, fontweight='bold', pad=20)
        ax.set_xlabel('Easting (m)', fontsize=ScientificStyle.LABEL_SIZE)
        ax.set_ylabel('Northing (m)', fontsize=ScientificStyle.LABEL_SIZE)
        
        statistics_text = (
            f'Clusters: {cluster_count}\n'
            f'Total Area: {total_area:.2f} km²'
        )
        
        if cluster_count > 0:
            mean_risk = cluster_geodataframe['mean_risk_value'].mean()
            max_risk = cluster_geodataframe['max_risk_value'].max()
            statistics_text += f'\nMean Risk: {mean_risk:.3f}\nMax Risk: {max_risk:.3f}'
        
        ax.text(
            0.02, 0.98, statistics_text,
            transform=ax.transAxes,
            verticalalignment='top',
            horizontalalignment='left',
            bbox=ScientificStyle.STATS_BOX_PROPS,
            fontsize=ScientificStyle.TICK_SIZE
        )
        
        ax.grid(False)
        ax.set_aspect('equal')
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=ScientificStyle.DPI, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        plt.close()
        
        logger.info(f"Saved cluster visualization: {output_path}")
    
    def run_cluster_analysis(self,
                           visualize: bool = True,
                           export_results: bool = True,
                           custom_risk_files: Optional[Dict[str, str]] = None) -> Dict[str, gpd.GeoDataFrame]:
        """
        Run complete cluster analysis process with sequential processing.
        
        Args:
            visualize: Whether to create visualizations
            export_results: Whether to export results to files
            custom_risk_files: Custom risk files to process
            
        Returns:
            Cluster analysis results
        """
        logger.info("Starting sequential cluster analysis...")
        
        if export_results:
            cluster_results = self.process_risk_clusters_sequential(custom_risk_files, visualize)
        else:
            cluster_results = self.process_risk_clusters_sequential(custom_risk_files, False)
        
        if not cluster_results:
            logger.warning("No cluster results generated")
        
        logger.info("Sequential cluster analysis complete")
        return cluster_results
    
    def get_cluster_summary_statistics(self, 
                                     cluster_results: Dict[str, gpd.GeoDataFrame]) -> Dict[str, Dict[str, Any]]:
        """Generate summary statistics for all cluster results."""
        summary_statistics = {}
        
        for file_key, cluster_geodataframe in cluster_results.items():
            if cluster_geodataframe.empty:
                continue
                
            statistics = self._calculate_scenario_statistics(cluster_geodataframe)
            summary_statistics[file_key] = statistics
        
        return summary_statistics
    
    def _calculate_scenario_statistics(self, cluster_geodataframe: gpd.GeoDataFrame) -> Dict[str, Any]:
        """Calculate summary statistics for a single scenario."""
        total_clusters = len(cluster_geodataframe)
        
        if total_clusters == 0:
            return {'cluster_count': 0}
            
        return {
            'cluster_count': total_clusters,
            'total_area_square_kilometers': cluster_geodataframe['cluster_area_square_meters'].sum() / 1_000_000,
            'mean_cluster_area_square_meters': cluster_geodataframe['cluster_area_square_meters'].mean(),
            'largest_cluster_area_square_meters': cluster_geodataframe['cluster_area_square_meters'].max(),
            'average_risk_value': cluster_geodataframe['mean_risk_value'].mean(),
            'maximum_risk_value': cluster_geodataframe['max_risk_value'].max(),
            'total_affected_pixels': cluster_geodataframe['pixel_count'].sum()
        } 