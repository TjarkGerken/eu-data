"""
Cache Utilities for EU Climate Risk Assessment
=============================================

High-level utilities for cache management, integration, and monitoring.
Provides easy-to-use functions for integrating caching into the main workflow.
"""

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
    """
    
    def __init__(self, config=None):
        """Initialize the cache integrator."""
        self.config = config
        self.cache_manager = get_cache_manager(config)
        self._cached_layers = {}
        
    def enable_caching_for_hazard_layer(self, hazard_layer):
        """
        Enable caching for a HazardLayer instance.
        
        Args:
            hazard_layer: HazardLayer instance to wrap with caching
            
        Returns:
            Cached version of the hazard layer
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
        
        Args:
            exposition_layer: ExpositionLayer instance to wrap with caching
            
        Returns:
            Cached version of the exposition layer
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
        
        Args:
            risk_assessment: RiskAssessment instance to wrap with caching
            
        Returns:
            Cached version of the risk assessment
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
        
        Args:
            relevance_layer: RelevanceLayer instance to wrap with caching
            
        Returns:
            Cached version of the relevance layer
        """
        if id(relevance_layer) not in self._cached_layers:
            cached_layer = cache_relevance_layer(relevance_layer)
            self._cached_layers[id(relevance_layer)] = cached_layer
            logger.info("Enabled caching for RelevanceLayer")
            return cached_layer
        return self._cached_layers[id(relevance_layer)]
        
    def print_cache_statistics(self):
        """Print comprehensive cache statistics."""
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
        
        Args:
            max_age_days: Remove files older than this many days
        """
        removed = self.cache_manager.cleanup_old_cache(max_age_days)
        logger.info(f"Cache cleanup completed: removed {removed} old files")
        
    def clear_cache(self, cache_type: Optional[str] = None):
        """
        Clear cache data.
        
        Args:
            cache_type: Specific cache type to clear, or None for all
        """
        if cache_type:
            removed = self.cache_manager.invalidate(cache_type=cache_type)
            logger.info(f"Cleared {cache_type} cache: removed {removed} files")
        else:
            removed = self.cache_manager.clear_all()
            logger.info(f"Cleared all cache data: removed {removed} files")
            
    def get_cache_info(self) -> Dict[str, Any]:
        """Get detailed cache information."""
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


# Global cache integrator instance
_cache_integrator = None


def get_cache_integrator(config=None) -> CacheIntegrator:
    """Get or create the global cache integrator instance."""
    global _cache_integrator
    if _cache_integrator is None:
        _cache_integrator = CacheIntegrator(config)
    return _cache_integrator


def initialize_caching(config=None) -> CacheIntegrator:
    """
    Initialize the caching system for the project.
    
    Args:
        config: Project configuration
        
    Returns:
        CacheIntegrator instance
    """
    integrator = get_cache_integrator(config)
    
    if integrator.cache_manager.enabled:
        logger.info("Caching system initialized and enabled")
        
        # Log cache configuration
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
    
    Args:
        hazard_layer: Optional HazardLayer instance
        exposition_layer: Optional ExpositionLayer instance
        relevance_layer: Optional RelevanceLayer instance
        risk_assessment: Optional RiskAssessment instance
        config: Project configuration
        
    Returns:
        Dictionary with cached layer instances
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
    """Print current cache status and statistics."""
    integrator = get_cache_integrator(config)
    integrator.print_cache_statistics()


def manage_cache_cli():
    """Command-line interface for cache management."""
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
    """Check if caching is enabled."""
    cache_manager = get_cache_manager(config)
    return cache_manager.enabled


def get_cache_directory(config=None) -> Path:
    """Get the cache directory path."""
    cache_manager = get_cache_manager(config)
    return cache_manager.cache_dir


def invalidate_cache_for_files(file_paths: List[str], config=None):
    """
    Invalidate cache entries that depend on specific files.
    
    Args:
        file_paths: List of file paths that have been modified
        config: Project configuration
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