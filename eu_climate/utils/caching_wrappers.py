import functools
from typing import Any, Dict, List, Optional, Callable

from eu_climate.utils.cache_manager import get_cache_manager
from eu_climate.utils.utils import setup_logging

logger = setup_logging(__name__)


class CachingLayerWrapper:
    """
    Wrapper class that adds caching capabilities to existing layer instances.
    
    This wrapper intercepts method calls and applies appropriate caching strategies
    based on the method type and data involved.
    
    The wrapper maintains a configuration mapping that defines:
    - Which methods should be cached
    - What type of cache storage to use (raster_data, calculations, final_results)
    - Which input files to monitor for cache invalidation
    - Which configuration parameters affect the cache key
    
    The wrapper is designed to be completely transparent - the wrapped layer
    behaves exactly like the original layer, but with automatic caching.
    """
    
    def __init__(self, layer_instance, layer_type: str):
        """
        Initialize the caching wrapper.
        
        Args:
            layer_instance: The original layer instance to wrap
            layer_type: Type of layer ('hazard', 'exposition', 'risk', 'relevance')
        """
        self._wrapped_layer = layer_instance
        self._layer_type = layer_type
        self._cache_manager = get_cache_manager(getattr(layer_instance, 'config', None))
        
        # Define caching strategies for different methods
        self._method_cache_config = self._get_method_cache_config()
        
        # Apply caching to specified methods
        self._apply_caching()
        
        logger.info(f"Applied caching wrapper to {layer_type} layer")
        
    def _get_method_cache_config(self) -> Dict[str, Dict[str, Any]]:
        """
        Define caching configuration for different layer methods.
        
        This configuration maps method names to their caching strategies:
        - cache_type: Type of cache storage ('raster_data', 'calculations', 'final_results')
        - input_files_attr: Attributes containing input file paths for invalidation
        - config_attrs: Configuration attributes that affect the cache key
        
        Returns:
            Dictionary mapping method names to caching configurations
        """
        
        # Base configuration attributes that affect most methods
        base_config_attrs = ['target_crs', 'resampling_method', 'smoothing_sigma']
        
        config = {
            # Hazard Layer Methods
            'load_and_prepare_dem': {
                'cache_type': 'raster_data',
                'input_files_attr': ['dem_path', 'land_mass_path'],
                'config_attrs': base_config_attrs
            },
            'load_river_data': {
                'cache_type': 'calculations',
                'input_files_attr': ['river_polygons_path'],
                'config_attrs': base_config_attrs
            },
            'calculate_flood_extent': {
                'cache_type': 'calculations', 
                'input_files_attr': ['land_mass_path'],
                'config_attrs': base_config_attrs
            },
            'process_scenarios': {
                'cache_type': 'final_results',
                'input_files_attr': ['dem_path', 'land_mass_path'],
                'config_attrs': base_config_attrs
            },
            'visualize_hazard_assessment': {
                'cache_type': 'calculations',
                'input_files_attr': ['land_mass_path'],
                'config_attrs': base_config_attrs
            },
            
            # Exposition Layer Methods
            'load_and_preprocess_raster': {
                'cache_type': 'raster_data',
                'config_attrs': base_config_attrs
            },
            'calculate_exposition': {
                'cache_type': 'final_results',
                'input_files_attr': ['ghs_built_c_path', 'ghs_built_v_path', 'population_2025_path'],
                'config_attrs': base_config_attrs + ['exposition_weights', 'ghs_built_c_class_weights']
            },
            'normalize_ghs_built_c': {
                'cache_type': 'calculations',
                'config_attrs': ['ghs_built_c_class_weights']
            },
            'normalize_raster': {
                'cache_type': 'calculations',
                'config_attrs': []
            },
            
            # Risk Assessment Methods
            'prepare_data': {
                'cache_type': 'calculations',
                'config_attrs': base_config_attrs
            },
            'calculate_integrated_risk': {
                'cache_type': 'final_results',
                'config_attrs': base_config_attrs + ['risk_weights', 'exposition_weights']
            },
            '_classify_risk_levels': {
                'cache_type': 'calculations',
                'config_attrs': ['n_risk_classes']
            },
            # Relevance Layer Methods
            'load_economic_datasets': {
                'cache_type': 'calculations',
                'input_files_attr': [],
                'config_attrs': base_config_attrs
            },
            'load_nuts_shapefile': {
                'cache_type': 'calculations',
                'input_files_attr': [],
                'config_attrs': base_config_attrs
            },
            'rasterize_nuts_regions': {
                'cache_type': 'raster_data',
                'config_attrs': base_config_attrs + ['target_resolution']
            },
            'load_and_process_economic_data': {
                'cache_type': 'calculations',
                'config_attrs': base_config_attrs
            },
            'calculate_relevance': {
                'cache_type': 'final_results',
                'input_files_attr': [],
                'config_attrs': base_config_attrs + ['exposition_weights', 'relevance_weights']
            }
        }
        
        return config
        
    def _apply_caching(self):
        """
        Apply caching decorators to specified methods.
        
        Iterates through the method cache configuration and replaces
        the original methods with cached versions. The cached methods
        maintain the same signature and behavior as the original methods.
        """
        for method_name, cache_config in self._method_cache_config.items():
            if hasattr(self._wrapped_layer, method_name):
                original_method = getattr(self._wrapped_layer, method_name)
                
                # Create cached version of the method
                cached_method_func = self._create_cached_method(
                    original_method, 
                    method_name,
                    cache_config
                )
                
                # Replace the original method with cached version
                setattr(self._wrapped_layer, method_name, cached_method_func)
                
                logger.debug(f"Applied caching to {self._layer_type}.{method_name}")
                
    def _create_cached_method(self, original_method: Callable, method_name: str, 
                            cache_config: Dict[str, Any]) -> Callable:
        """
        Create a cached version of a method.
        
        The cached method:
        1. Checks if caching is enabled
        2. Generates a unique cache key based on method signature and configuration
        3. Attempts to retrieve cached result
        4. If cache miss, executes original method and caches result
        5. Returns result (cached or freshly computed)
        
        Args:
            original_method: Original method to wrap with caching
            method_name: Name of the method for logging/debugging
            cache_config: Caching configuration for this method
            
        Returns:
            Cached version of the method
        """
        
        @functools.wraps(original_method)
        def cached_wrapper(*args, **kwargs):
            # Always check if caching is enabled first
            if not self._cache_manager.enabled:
                logger.info(f"Cache disabled for {self._layer_type}.{method_name}, executing...")
                return original_method(*args, **kwargs)
                
            # Generate cache key
            cache_key = self._generate_method_cache_key(
                method_name, cache_config, args, kwargs
            )
            
            # Try to get from cache
            cache_type = cache_config.get('cache_type', 'calculations')
            cached_result = self._cache_manager.get(cache_key, cache_type)
            
            if cached_result is not None:
                logger.info(f"Cache hit for {self._layer_type}.{method_name}")
                return cached_result
                
            # Execute original method and cache result
            logger.info(f"Cache miss for {self._layer_type}.{method_name}, executing...")
            result = original_method(*args, **kwargs)
            
            # Cache the result
            self._cache_manager.set(cache_key, result, cache_type)
            
            return result
            
        return cached_wrapper
        
    def _generate_method_cache_key(self, method_name: str, cache_config: Dict[str, Any],
                                 args: tuple, kwargs: dict) -> str:
        """
        Generate cache key for a specific method call.
        
        Creates a unique cache key based on:
        - Method name and layer type
        - Input file paths and their modification times
        - Configuration parameters that affect the result
        - Method arguments and keyword arguments
        
        Args:
            method_name: Name of the method being cached
            cache_config: Cache configuration for this method
            args: Method positional arguments
            kwargs: Method keyword arguments
            
        Returns:
            Unique cache key string
        """
        
        function_name = f"{self._layer_type}.{method_name}"
        
        # Extract input files from layer attributes
        input_files = []
        input_files_attr = cache_config.get('input_files_attr')
        
        if input_files_attr:
            if isinstance(input_files_attr, str):
                # Single attribute
                if hasattr(self._wrapped_layer, input_files_attr):
                    file_path = getattr(self._wrapped_layer, input_files_attr)
                    if file_path:
                        input_files.append(str(file_path))
            elif isinstance(input_files_attr, list):
                # Multiple attributes  
                for attr in input_files_attr:
                    # Try direct attribute first
                    if hasattr(self._wrapped_layer, attr):
                        file_path = getattr(self._wrapped_layer, attr)
                        if file_path:
                            input_files.append(str(file_path))
                    # For nested attributes like config.data_dir
                    elif '.' in attr and hasattr(self._wrapped_layer, 'config'):
                        try:
                            obj = self._wrapped_layer.config
                            for part in attr.split('.')[1:]:  # Skip 'config' part
                                obj = getattr(obj, part)
                            if obj:
                                input_files.append(str(obj))
                        except AttributeError:
                            pass
                            
        # Extract config parameters that affect the cache key
        config_params = {}
        config_attrs = cache_config.get('config_attrs', [])
        
        if config_attrs and hasattr(self._wrapped_layer, 'config'):
            config = self._wrapped_layer.config
            for attr in config_attrs:
                if hasattr(config, attr):
                    config_params[attr] = getattr(config, attr)
                    
        # Include method parameters
        parameters = {
            'args': args,
            'kwargs': kwargs
        }
        
        return self._cache_manager.generate_cache_key(
            function_name, input_files, parameters, config_params
        )
        
    def __getattr__(self, name):
        """
        Delegate attribute access to the wrapped layer.
        
        This ensures that the wrapper is completely transparent - any attribute
        or method not handled by the wrapper is delegated to the original layer.
        
        Args:
            name: Attribute name to access
            
        Returns:
            Attribute value from the wrapped layer
        """
        return getattr(self._wrapped_layer, name)
        

def apply_caching_to_layer(layer_instance, layer_type: str):
    """
    Apply caching to a layer instance.
    
    This is the main function for wrapping layer instances with caching capabilities.
    It creates a CachingLayerWrapper that intercepts method calls and applies
    appropriate caching strategies.
    
    Args:
        layer_instance: The layer instance to wrap with caching
        layer_type: Type of layer ('hazard', 'exposition', 'risk', 'relevance')
        
    Returns:
        The wrapped layer instance with caching capabilities
    """
    return CachingLayerWrapper(layer_instance, layer_type)


def cache_hazard_layer(hazard_layer):
    """
    Apply caching specifically to HazardLayer instance.
    
    Wraps the hazard layer with caching optimized for:
    - DEM loading and preprocessing
    - Flood extent calculations
    - Scenario processing
    - Visualization generation
    
    Args:
        hazard_layer: HazardLayer instance to wrap
        
    Returns:
        Cached HazardLayer instance
    """
    return apply_caching_to_layer(hazard_layer, 'hazard')


def cache_exposition_layer(exposition_layer):
    """
    Apply caching specifically to ExpositionLayer instance.
    
    Wraps the exposition layer with caching optimized for:
    - Population and built environment data loading
    - Raster preprocessing and normalization
    - Exposition calculations
    - Port and infrastructure processing
    
    Args:
        exposition_layer: ExpositionLayer instance to wrap
        
    Returns:
        Cached ExpositionLayer instance
    """
    return apply_caching_to_layer(exposition_layer, 'exposition')


def cache_risk_assessment(risk_assessment):
    """
    Apply caching specifically to RiskAssessment instance.
    
    Wraps the risk assessment with caching optimized for:
    - Data preparation and integration
    - Risk calculations
    - Risk classification
    - Final result generation
    
    Args:
        risk_assessment: RiskAssessment instance to wrap
        
    Returns:
        Cached RiskAssessment instance
    """
    return apply_caching_to_layer(risk_assessment, 'risk')


def cache_relevance_layer(relevance_layer):
    """
    Apply caching specifically to RelevanceLayer instance.
    
    Wraps the relevance layer with caching optimized for:
    - Economic dataset loading
    - NUTS region processing
    - Relevance calculations
    - Freight and population data integration
    
    Args:
        relevance_layer: RelevanceLayer instance to wrap
        
    Returns:
        Cached RelevanceLayer instance
    """
    return apply_caching_to_layer(relevance_layer, 'relevance')


class CacheAwareMethod:
    """
    Decorator class for making individual methods cache-aware.
    
    This can be used to add caching to specific methods without
    wrapping the entire class. Useful for:
    - Adding caching to individual utility functions
    - Retrofitting existing methods with caching
    - Fine-grained control over caching behavior
    
    The decorator provides the same caching functionality as the
    layer wrapper but can be applied to individual methods.
    """
    
    def __init__(self, cache_type: str = 'calculations',
                 input_files: Optional[List[str]] = None,
                 config_attrs: Optional[List[str]] = None):
        """
        Initialize the cache-aware method decorator.
        
        Args:
            cache_type: Type of cache to use ('raster_data', 'calculations', 'final_results')
            input_files: List of input file attribute names to monitor for invalidation
            config_attrs: List of config attribute names that affect the cache key
        """
        self.cache_type = cache_type
        self.input_files = input_files or []
        self.config_attrs = config_attrs or []
        
    def __call__(self, func):
        """
        Apply caching to the decorated method.
        
        Args:
            func: Function to decorate with caching
            
        Returns:
            Decorated function with caching capabilities
        """
        
        # Store decorator attributes in closure
        decorator_input_files = self.input_files
        decorator_config_attrs = self.config_attrs
        decorator_cache_type = self.cache_type
        
        @functools.wraps(func)
        def wrapper(instance, *args, **kwargs):
            cache_manager = get_cache_manager(getattr(instance, 'config', None))
            
            if not cache_manager.enabled:
                return func(instance, *args, **kwargs)
                
            # Generate cache key
            function_name = f"{func.__module__}.{func.__qualname__}"
            
            # Extract input files from instance attributes
            input_file_paths = []
            for attr in decorator_input_files:
                if hasattr(instance, attr):
                    file_path = getattr(instance, attr)
                    if file_path:
                        input_file_paths.append(str(file_path))
                        
            # Extract config parameters that affect the cache key
            config_params = {}
            if hasattr(instance, 'config'):
                config = instance.config
                for attr in decorator_config_attrs:
                    if hasattr(config, attr):
                        config_params[attr] = getattr(config, attr)
                        
            # Method parameters
            parameters = {'args': args, 'kwargs': kwargs}
            
            cache_key = cache_manager.generate_cache_key(
                function_name, input_file_paths, parameters, config_params
            )
            
            # Try cache first
            cached_result = cache_manager.get(cache_key, decorator_cache_type)
            if cached_result is not None:
                logger.debug(f"Cache hit for {function_name}")
                return cached_result
                
            # Execute and cache
            logger.debug(f"Cache miss for {function_name}, executing...")
            result = func(instance, *args, **kwargs)
            cache_manager.set(cache_key, result, decorator_cache_type)
            
            return result
            
        return wrapper


# Convenient aliases for the decorator with specific cache types
cache_raster_method = lambda **kwargs: CacheAwareMethod(cache_type='raster_data', **kwargs)
cache_calculation_method = lambda **kwargs: CacheAwareMethod(cache_type='calculations', **kwargs)
cache_result_method = lambda **kwargs: CacheAwareMethod(cache_type='final_results', **kwargs) 