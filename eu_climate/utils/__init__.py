"""
EU Climate Risk Assessment Utils package.
"""

# Core utilities
from .utils import setup_logging, suppress_warnings
from .data_loading import get_config
from .conversion import RasterTransformer

# Caching system
from .cache_manager import CacheManager, get_cache_manager, cached_method, cached_function
from .caching_wrappers import (
    CachingLayerWrapper, 
    apply_caching_to_layer,
    cache_hazard_layer,
    cache_exposition_layer, 
    cache_risk_assessment,
    CacheAwareMethod,
    cache_raster_method,
    cache_calculation_method,
    cache_result_method
)
from .cache_utils import (
    CacheIntegrator,
    get_cache_integrator,
    initialize_caching,
    create_cached_layers,
    print_cache_status,
    is_caching_enabled,
    get_cache_directory,
    invalidate_cache_for_files
)

__all__ = [
    # Core utilities
    'setup_logging',
    'suppress_warnings', 
    'get_config',
    'RasterTransformer',
    
    # Caching system
    'CacheManager',
    'get_cache_manager',
    'cached_method',
    'cached_function',
    'CachingLayerWrapper',
    'apply_caching_to_layer',
    'cache_hazard_layer',
    'cache_exposition_layer',
    'cache_risk_assessment',
    'CacheAwareMethod',
    'cache_raster_method',
    'cache_calculation_method',
    'cache_result_method',
    'CacheIntegrator',
    'get_cache_integrator',
    'initialize_caching', 
    'create_cached_layers',
    'print_cache_status',
    'is_caching_enabled',
    'get_cache_directory',
    'invalidate_cache_for_files'
] 