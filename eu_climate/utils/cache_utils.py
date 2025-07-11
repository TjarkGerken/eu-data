import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
import argparse

from eu_climate.utils.cache_manager import get_cache_manager, CacheManager
from eu_climate.utils.caching_wrappers import (
    cache_hazard_layer, 
    cache_exposition_layer, 
    cache_risk_assessment,
    cache_relevance_layer
)
from eu_climate.utils.utils import setup_logging

logger = setup_logging(__name__)


class CacheIntegrator:
    """
    High-level cache integration for the EU Climate Risk Assessment system.
    
    Provides simple methods to enable caching for different components
    and manage cache operations.
    
    This class serves as the main interface for integrating caching into
    the risk assessment workflow. It handles:
    - Automatic wrapping of layer instances with caching capabilities
    - Cache performance monitoring and statistics
    - Cache lifecycle management and cleanup
    - Integration with the broader risk assessment pipeline
    
    The integrator maintains references to cached layer instances to ensure
    consistent caching behavior across the system.
    """
    
    def __init__(self, config=None):
        """
        Initialize the cache integrator.
        
        Args:
            config: ProjectConfig instance containing cache configuration
        """
        self.config = config
        self.cache_manager = get_cache_manager(config)
        self._cached_layers = {}  # Store references to cached layer instances
        
    def enable_caching_for_hazard_layer(self, hazard_layer):
        """
        Enable caching for a HazardLayer instance.
        
        Wraps the hazard layer with caching capabilities, intercepting method calls
        to provide transparent caching for expensive operations like:
        - DEM processing and flood extent calculations
        - Scenario processing and risk assessments
        - Visualization and output generation
        
        Args:
            hazard_layer: HazardLayer instance to wrap with caching
            
        Returns:
            Cached version of the hazard layer with transparent caching
        """
        if id(hazard_layer) not in self._cached_layers:
            cached_layer = cache_hazard_layer(hazard_layer)
            self._cached_layers[id(hazard_layer)] = cached_layer
            logger.info("Enabled caching for HazardLayer")
            return cached_layer
        return self._cached_layers[id(hazard_layer)]
        
    def enable_caching_for_exposition_layer(self, exposition_layer):
        """
        Enable caching for an ExpositionLayer instance.
        
        Wraps the exposition layer with caching capabilities for operations like:
        - Population and built environment data loading
        - Raster preprocessing and normalization
        - Exposition index calculations
        - Port and infrastructure processing
        
        Args:
            exposition_layer: ExpositionLayer instance to wrap with caching
            
        Returns:
            Cached version of the exposition layer with transparent caching
        """
        if id(exposition_layer) not in self._cached_layers:
            cached_layer = cache_exposition_layer(exposition_layer)
            self._cached_layers[id(exposition_layer)] = cached_layer
            logger.info("Enabled caching for ExpositionLayer")
            return cached_layer
        return self._cached_layers[id(exposition_layer)]
        
    def enable_caching_for_risk_assessment(self, risk_assessment):
        """
        Enable caching for a RiskAssessment instance.
        
        Wraps the risk assessment with caching capabilities for operations like:
        - Data preparation and integration
        - Integrated risk calculations
        - Risk classification and analysis
        - Final result generation
        
        Args:
            risk_assessment: RiskAssessment instance to wrap with caching
            
        Returns:
            Cached version of the risk assessment with transparent caching
        """
        if id(risk_assessment) not in self._cached_layers:
            cached_layer = cache_risk_assessment(risk_assessment)
            self._cached_layers[id(risk_assessment)] = cached_layer
            logger.info("Enabled caching for RiskAssessment")
            return cached_layer
        return self._cached_layers[id(risk_assessment)]
        
    def enable_caching_for_relevance_layer(self, relevance_layer):
        """
        Enable caching for a RelevanceLayer instance.
        
        Wraps the relevance layer with caching capabilities for operations like:
        - Economic dataset loading and processing
        - NUTS region processing and rasterization
        - Relevance index calculations
        - Freight and population data integration
        
        Args:
            relevance_layer: RelevanceLayer instance to wrap with caching
            
        Returns:
            Cached version of the relevance layer with transparent caching
        """
        if id(relevance_layer) not in self._cached_layers:
            cached_layer = cache_relevance_layer(relevance_layer)
            self._cached_layers[id(relevance_layer)] = cached_layer
            logger.info("Enabled caching for RelevanceLayer")
            return cached_layer
        return self._cached_layers[id(relevance_layer)]
        
    def print_cache_statistics(self):
        """
        Print comprehensive cache statistics.
        
        Outputs detailed information about cache performance including:
        - Cache hit/miss rates and performance metrics
        - Cache size and storage utilization
        - Cache breakdown by data type
        - Directory structure and file counts
        
        This information is useful for:
        - Monitoring cache effectiveness
        - Identifying performance bottlenecks
        - Optimizing cache configuration
        - Debugging cache-related issues
        """
        stats = self.cache_manager.get_stats()
        
        print("\n" + "="*50)
        print("CACHE STATISTICS")
        print("="*50)
        print(f"Cache Status: {'Enabled' if self.cache_manager.enabled else 'Disabled'}")
        print(f"Cache Directory: {self.cache_manager.cache_dir}")
        print(f"Cache Size: {stats['cache_size_gb']:.2f} GB")
        print(f"Max Cache Size: {self.cache_manager.max_cache_size_gb} GB")
        print()
        print("Performance Metrics:")
        print(f"  Cache Hits: {stats['hits']}")
        print(f"  Cache Misses: {stats['misses']}")
        print(f"  Hit Rate: {stats['hit_rate']:.1%}")
        print(f"  Invalidations: {stats['invalidations']}")
        print()
        
        # Show cache breakdown by type
        for cache_type, cache_dir in self.cache_manager.cache_dirs.items():
            if cache_dir.exists():
                file_count = len(list(cache_dir.glob('*')))
                dir_size = sum(f.stat().st_size for f in cache_dir.rglob('*') if f.is_file())
                dir_size_mb = dir_size / (1024 * 1024)
                print(f"  {cache_type.title()}: {file_count} files, {dir_size_mb:.1f} MB")
                
        print("="*50)
        
    def cleanup_cache(self, max_age_days: int = 7):
        """
        Clean up old cache files.
        
        Removes cache files older than the specified number of days to prevent
        unlimited cache growth and maintain system performance.
        
        Args:
            max_age_days: Remove files older than this many days
        """
        removed = self.cache_manager.cleanup_old_cache(max_age_days)
        logger.info(f"Cache cleanup completed: removed {removed} old files")
        
    def clear_cache(self, cache_type: Optional[str] = None):
        """
        Clear cache data.
        
        Removes cached data either for a specific cache type or all cache data.
        Useful for:
        - Forcing re-computation of results
        - Clearing cache after configuration changes
        - Freeing up disk space
        
        Args:
            cache_type: Specific cache type to clear ('raster_data', 'calculations', 
                       'final_results'), or None for all cache types
        """
        if cache_type:
            removed = self.cache_manager.invalidate(cache_type=cache_type)
            logger.info(f"Cleared {cache_type} cache: removed {removed} files")
        else:
            removed = self.cache_manager.clear_all()
            logger.info(f"Cleared all cache data: removed {removed} files")
            
    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get detailed cache information.
        
        Returns comprehensive information about the cache system including:
        - Configuration and status
        - Performance statistics
        - Storage breakdown by cache type
        - Directory structure and file counts
        
        Returns:
            Dictionary containing detailed cache information
        """
        stats = self.cache_manager.get_stats()
        
        cache_info = {
            'enabled': self.cache_manager.enabled,
            'cache_dir': str(self.cache_manager.cache_dir),
            'total_size_gb': stats['cache_size_gb'],
            'max_size_gb': self.cache_manager.max_cache_size_gb,
            'statistics': stats,
            'breakdown': {}
        }
        
        # Add breakdown by cache type
        for cache_type, cache_dir in self.cache_manager.cache_dirs.items():
            if cache_dir.exists():
                files = list(cache_dir.glob('*'))
                total_size = sum(f.stat().st_size for f in cache_dir.rglob('*') if f.is_file())
                
                cache_info['breakdown'][cache_type] = {
                    'file_count': len(files),
                    'size_mb': total_size / (1024 * 1024),
                    'directory': str(cache_dir)
                }
                
        return cache_info


# Global cache integrator instance for system-wide consistency
_cache_integrator = None


def get_cache_integrator(config=None) -> CacheIntegrator:
    """
    Get or create the global cache integrator instance.
    
    Implements singleton pattern to ensure consistent cache integration
    across the entire system.
    
    Args:
        config: ProjectConfig instance (only used for first initialization)
        
    Returns:
        CacheIntegrator: Global cache integrator instance
    """
    global _cache_integrator
    if _cache_integrator is None:
        _cache_integrator = CacheIntegrator(config)
    return _cache_integrator


def initialize_caching(config=None) -> CacheIntegrator:
    """
    Initialize the caching system for the project.
    
    Sets up the caching infrastructure and performs initial configuration.
    This function should be called early in the application lifecycle to
    ensure caching is available for all components.
    
    Features:
    - Initializes cache directory structure
    - Loads configuration from project config
    - Performs automatic cleanup if configured
    - Provides comprehensive logging of cache status
    
    Args:
        config: ProjectConfig instance containing cache configuration
        
    Returns:
        CacheIntegrator: Initialized cache integrator instance
    """
    integrator = get_cache_integrator(config)
    
    if integrator.cache_manager.enabled:
        logger.info("Caching system initialized and enabled")
        
        # Log cache configuration details
        cache_config = {}
        if config and hasattr(config, 'config'):
            cache_config = config.config.get('caching', {})
            
        logger.info(f"Cache directory: {integrator.cache_manager.cache_dir}")
        logger.info(f"Max cache size: {integrator.cache_manager.max_cache_size_gb} GB")
        
        # Perform automatic cleanup if enabled
        if integrator.cache_manager.auto_cleanup:
            max_age = cache_config.get('max_age_days', 7)
            integrator.cleanup_cache(max_age)
            
    else:
        logger.info("Caching system initialized but disabled")
        
    return integrator


def create_cached_layers(hazard_layer=None, exposition_layer=None, relevance_layer=None, risk_assessment=None, config=None):
    """
    Create cached versions of layer instances.
    
    Provides a convenient way to wrap multiple layer instances with caching
    capabilities in a single function call.
    
    Args:
        hazard_layer: Optional HazardLayer instance to wrap with caching
        exposition_layer: Optional ExpositionLayer instance to wrap with caching
        relevance_layer: Optional RelevanceLayer instance to wrap with caching
        risk_assessment: Optional RiskAssessment instance to wrap with caching
        config: ProjectConfig instance for cache configuration
        
    Returns:
        Dictionary with cached layer instances:
        - 'hazard': Cached hazard layer (if provided)
        - 'exposition': Cached exposition layer (if provided)
        - 'relevance': Cached relevance layer (if provided)
        - 'risk': Cached risk assessment (if provided)
    """
    integrator = get_cache_integrator(config)
    cached_layers = {}
    
    if hazard_layer:
        cached_layers['hazard'] = integrator.enable_caching_for_hazard_layer(hazard_layer)
        
    if exposition_layer:
        cached_layers['exposition'] = integrator.enable_caching_for_exposition_layer(exposition_layer)
        
    if relevance_layer:
        cached_layers['relevance'] = integrator.enable_caching_for_relevance_layer(relevance_layer)
        
    if risk_assessment:
        cached_layers['risk'] = integrator.enable_caching_for_risk_assessment(risk_assessment)
        
    return cached_layers


def print_cache_status(config=None):
    """
    Print current cache status and statistics.
    
    Convenience function to quickly display cache information without
    creating a cache integrator instance explicitly.
    
    Args:
        config: ProjectConfig instance for cache configuration
    """
    integrator = get_cache_integrator(config)
    integrator.print_cache_statistics()


def manage_cache_cli():
    """
    Command-line interface for cache management.
    
    Provides a CLI tool for managing cache operations including:
    - Viewing cache statistics and status
    - Clearing cache data by type or completely
    - Cleaning up old cache files
    - Displaying cache size breakdown
    
    Usage:
        python -m eu_climate.utils.cache_utils --stats
        python -m eu_climate.utils.cache_utils --clear all
        python -m eu_climate.utils.cache_utils --cleanup 7
        python -m eu_climate.utils.cache_utils --size
    """
    parser = argparse.ArgumentParser(description='EU Climate Cache Management')
    parser.add_argument('--stats', action='store_true', help='Show cache statistics')
    parser.add_argument('--clear', choices=['all', 'raster_data', 'calculations', 'final_results'],
                       help='Clear cache data')
    parser.add_argument('--cleanup', type=int, metavar='DAYS', 
                       help='Remove cache files older than N days')
    parser.add_argument('--size', action='store_true', help='Show cache size breakdown')
    
    args = parser.parse_args()
    
    # Initialize cache manager
    integrator = get_cache_integrator()
    
    if args.stats:
        integrator.print_cache_statistics()
        
    if args.clear:
        if args.clear == 'all':
            integrator.clear_cache()
        else:
            integrator.clear_cache(args.clear)
            
    if args.cleanup:
        integrator.cleanup_cache(args.cleanup)
        
    if args.size:
        cache_info = integrator.get_cache_info()
        print(f"\nCache Size Breakdown:")
        for cache_type, info in cache_info['breakdown'].items():
            print(f"  {cache_type}: {info['file_count']} files, {info['size_mb']:.1f} MB")


def is_caching_enabled(config=None) -> bool:
    """
    Check if caching is enabled.
    
    Convenience function to check cache status without creating
    full cache integrator instance.
    
    Args:
        config: ProjectConfig instance for cache configuration
        
    Returns:
        bool: True if caching is enabled, False otherwise
    """
    cache_manager = get_cache_manager(config)
    return cache_manager.enabled


def get_cache_directory(config=None) -> Path:
    """
    Get the cache directory path.
    
    Returns the path to the cache directory used by the system.
    
    Args:
        config: ProjectConfig instance for cache configuration
        
    Returns:
        Path: Path to cache directory
    """
    cache_manager = get_cache_manager(config)
    return cache_manager.cache_dir


def invalidate_cache_for_files(file_paths: List[str], config=None):
    """
    Invalidate cache entries that depend on specific files.
    
    Useful for invalidating cache when input files are modified externally.
    This function provides a simplified interface for cache invalidation based
    on file dependencies.
    
    Args:
        file_paths: List of file paths that have been modified
        config: ProjectConfig instance for cache configuration
        
    Note:
        This is a simplified invalidation approach. In a more sophisticated system,
        we could track file dependencies more precisely to only invalidate
        cache entries that actually depend on the modified files.
    """
    cache_manager = get_cache_manager(config)
    
    # This is a simplified invalidation - in a more sophisticated system,
    # we could track file dependencies more precisely
    total_invalidated = 0
    
    for file_path in file_paths:
        file_name = Path(file_path).name
        # Remove cache entries that might depend on this file
        invalidated = cache_manager.invalidate(pattern=file_name)
        total_invalidated += invalidated
        
    if total_invalidated > 0:
        logger.info(f"Invalidated {total_invalidated} cache entries due to file changes")


# Export key functions for easy importing
__all__ = [
    'CacheIntegrator',
    'get_cache_integrator', 
    'initialize_caching',
    'create_cached_layers',
    'print_cache_status',
    'is_caching_enabled',
    'get_cache_directory',
    'invalidate_cache_for_files'
] 