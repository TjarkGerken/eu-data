import os
import pickle
import hashlib
import json
import time
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Union, Callable, Tuple
from functools import wraps
import numpy as np
import rasterio
from rasterio.crs import CRS
import logging
from datetime import datetime, timedelta
import h5py
import gzip

from eu_climate.utils.utils import setup_logging

logger = setup_logging(__name__)


class CacheManager:
    """
    Central Caching Solution for EU Climate Risk Assessment
    =====================================================
    
    Provides intelligent caching for:
    - Large raster data (HDF5 format)
    - Intermediate calculations (compressed pickle)
    - Final results (GeoTIFF + metadata)
    - Configuration-dependent results
    
    Features:
    - Automatic cache invalidation based on input changes
    - Configurable storage strategies
    - Memory-efficient data handling
    - Thread-safe operations
    """
    
    def __init__(self, config=None):
        """Initialize the cache manager."""
        self.config = config
        

        self.cache_dir = config.huggingface_folder / ".cache" / "eu_climate"
        
            
        # Create cache subdirectories
        self.cache_dirs = {
            'raster_data': self.cache_dir / 'raster_data',
            'calculations': self.cache_dir / 'calculations', 
            'final_results': self.cache_dir / 'final_results',
            'metadata': self.cache_dir / 'metadata',
            'config_snapshots': self.cache_dir / 'config_snapshots'
        }
        
        # Create directories
        for cache_dir in self.cache_dirs.values():
            cache_dir.mkdir(parents=True, exist_ok=True)
            
        # Cache configuration
        self.enabled = self._get_cache_config('enabled', True)
        self.max_cache_size_gb = self._get_cache_config('max_cache_size_gb', 10)
        self.auto_cleanup = self._get_cache_config('auto_cleanup', True)
        
        # Cache statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'invalidations': 0
        }
        
        logger.info(f"Cache manager initialized: {self.cache_dir}")
        logger.info(f"Cache enabled: {self.enabled}")
        
    def _get_cache_config(self, key: str, default: Any) -> Any:
        """Get cache configuration value from YAML config."""
        
        if self.config is None:
            raise ValueError(f"No configuration provided to CacheManager, cannot get cache config for '{key}'")
        
        # Check if config is ProjectConfig instance
        if hasattr(self.config, 'config'):
            yaml_config = self.config.config
            if 'caching' not in yaml_config:
                raise ValueError(f"'caching' section not found in YAML config. Available keys: {list(yaml_config.keys())}")
            
            caching_config = yaml_config['caching']
            
            if key not in caching_config:
                raise ValueError(f"Cache config key '{key}' not found. Available keys: {list(caching_config.keys())}")
            
            value = caching_config[key]
            return value
        
        # Check if config is direct dict
        elif isinstance(self.config, dict):
            if 'caching' not in self.config:
                raise ValueError(f"'caching' section not found in config dict. Available keys: {list(self.config.keys())}")
            
            caching_config = self.config['caching']
            
            if key not in caching_config:
                raise ValueError(f"Cache config key '{key}' not found. Available keys: {list(caching_config.keys())}")
            
            value = caching_config[key]
            return value
        
        else:
            raise ValueError(f"Invalid config type: {type(self.config)}. Expected ProjectConfig instance or dict with 'caching' section.")
        
    def generate_cache_key(self, 
                          function_name: str,
                          input_files: Optional[list] = None,
                          parameters: Optional[dict] = None,
                          config_params: Optional[dict] = None) -> str:
        """
        Generate a unique cache key based on function name, inputs, and parameters.
        
        Args:
            function_name: Name of the function being cached
            input_files: List of input file paths
            parameters: Function parameters that affect output
            config_params: Configuration parameters that affect output
            
        Returns:
            Unique cache key string
        """
        key_components = [function_name]
        
        # Add file signatures
        if input_files:
            for file_path in input_files:
                if isinstance(file_path, (str, Path)) and Path(file_path).exists():
                    file_stat = Path(file_path).stat()
                    file_sig = f"{file_path}:{file_stat.st_mtime}:{file_stat.st_size}"
                    key_components.append(file_sig)
                    
        # Add parameter signatures
        if parameters:
            param_str = json.dumps(parameters, sort_keys=True, default=str)
            key_components.append(param_str)
            
        # Add config signatures
        if config_params:
            config_str = json.dumps(config_params, sort_keys=True, default=str)
            key_components.append(config_str)
            
        # Create hash
        combined_key = '|'.join(key_components)
        cache_key = hashlib.sha256(combined_key.encode()).hexdigest()
        
        return cache_key
        
    def _get_cache_path(self, cache_key: str, cache_type: str, extension: str = '') -> Path:
        """Get the cache file path for a given key and type."""
        cache_dir = self.cache_dirs.get(cache_type, self.cache_dirs['calculations'])
        if extension and not extension.startswith('.'):
            extension = '.' + extension
        return cache_dir / f"{cache_key}{extension}"
        
    def _save_raster_data(self, data: np.ndarray, cache_path: Path, 
                         metadata: Optional[dict] = None) -> None:
        """Save raster data in compressed HDF5 format."""
        with h5py.File(cache_path, 'w') as f:
            # Save data with compression
            f.create_dataset('data', data=data, compression='gzip', compression_opts=6)
            
            # Save metadata
            if metadata:
                meta_group = f.create_group('metadata')
                for key, value in metadata.items():
                    if isinstance(value, (str, int, float, bool)):
                        meta_group.attrs[key] = value
                    elif isinstance(value, (list, tuple)):
                        # Save lists and tuples as datasets, converting to numpy array
                        meta_group.create_dataset(key, data=np.array(value))
                    elif isinstance(value, np.ndarray):
                        meta_group.create_dataset(key, data=value)
                    else:
                        # Fallback to string for other types
                        meta_group.attrs[key] = str(value)
                        
    def _load_raster_data(self, cache_path: Path) -> Tuple[np.ndarray, dict]:
        """Load raster data from HDF5 format."""
        with h5py.File(cache_path, 'r') as f:
            data = f['data'][:]
            
            metadata = {}
            if 'metadata' in f:
                meta_group = f['metadata']
                for key in meta_group.attrs:
                    metadata[key] = meta_group.attrs[key]
                for key in meta_group.keys():
                    metadata[key] = meta_group[key][:]
                    
        return data, metadata
        
    def _save_calculation_data(self, data: Any, cache_path: Path) -> None:
        """Save calculation data in compressed pickle format."""
        with gzip.open(cache_path, 'wb') as f:
            pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
            
    def _load_calculation_data(self, cache_path: Path) -> Any:
        """Load calculation data from compressed pickle format."""
        with gzip.open(cache_path, 'rb') as f:
            return pickle.load(f)
            
    def get(self, cache_key: str, cache_type: str = 'calculations') -> Optional[Any]:
        """
        Retrieve data from cache.
        
        Args:
            cache_key: Unique cache key
            cache_type: Type of cache ('raster_data', 'calculations', 'final_results')
            
        Returns:
            Cached data or None if not found
        """
        if not self.enabled:
            return None
            
        try:
            if cache_type == 'raster_data':
                cache_path = self._get_cache_path(cache_key, cache_type, '.h5')
                if cache_path.exists():
                    self.stats['hits'] += 1
                    return self._load_raster_data(cache_path)
            else:
                cache_path = self._get_cache_path(cache_key, cache_type, '.pkl.gz')
                if cache_path.exists():
                    self.stats['hits'] += 1
                    return self._load_calculation_data(cache_path)
                    
            self.stats['misses'] += 1
            return None
            
        except Exception as e:
            logger.warning(f"Cache read error for key {cache_key}: {e}")
            self.stats['misses'] += 1
            return None
            
    def set(self, cache_key: str, data: Any, cache_type: str = 'calculations', 
           metadata: Optional[dict] = None) -> bool:
        """
        Store data in cache.
        
        Args:
            cache_key: Unique cache key
            data: Data to cache
            cache_type: Type of cache
            metadata: Additional metadata for raster data
            
        Returns:
            True if successfully cached, False otherwise
        """
        if not self.enabled:
            return False
            
        try:
            if cache_type == 'raster_data':
                cache_path = self._get_cache_path(cache_key, cache_type, '.h5')
                if isinstance(data, np.ndarray):
                    self._save_raster_data(data, cache_path, metadata)
                else:
                    # If data is tuple (array, metadata), handle appropriately
                    if isinstance(data, tuple) and len(data) == 2:
                        array_data, meta = data
                        if metadata:
                            meta.update(metadata)
                        self._save_raster_data(array_data, cache_path, meta)
                    else:
                        return False
            else:
                cache_path = self._get_cache_path(cache_key, cache_type, '.pkl.gz')
                self._save_calculation_data(data, cache_path)
                
            logger.info(f"Cached data with key: {cache_key}")
            return True
            
        except Exception as e:
            logger.warning(f"Cache write error for key {cache_key}: {e}")
            return False
            
    def invalidate(self, pattern: Optional[str] = None, cache_type: Optional[str] = None) -> int:
        """
        Invalidate cache entries.
        
        Args:
            pattern: Optional pattern to match cache keys
            cache_type: Optional specific cache type to invalidate
            
        Returns:
            Number of invalidated entries
        """
        invalidated = 0
        
        cache_dirs_to_check = [self.cache_dirs[cache_type]] if cache_type else self.cache_dirs.values()
        
        for cache_dir in cache_dirs_to_check:
            if not cache_dir.exists():
                continue
                
            for cache_file in cache_dir.iterdir():
                if cache_file.is_file():
                    if pattern is None or pattern in cache_file.stem:
                        try:
                            cache_file.unlink()
                            invalidated += 1
                        except Exception as e:
                            logger.warning(f"Could not remove cache file {cache_file}: {e}")
                            
        self.stats['invalidations'] += invalidated
        logger.info(f"Invalidated {invalidated} cache entries")
        return invalidated
        
    def clear_all(self) -> int:
        """Clear all cache data."""
        return self.invalidate()
        
    def get_cache_size(self) -> float:
        """Get total cache size in GB."""
        total_size = 0
        for cache_dir in self.cache_dirs.values():
            if cache_dir.exists():
                for file_path in cache_dir.rglob('*'):
                    if file_path.is_file():
                        total_size += file_path.stat().st_size
        return total_size / (1024 ** 3)  # Convert to GB
        
    def cleanup_old_cache(self, max_age_days: int = 7) -> int:
        """Remove cache files older than specified days."""
        cutoff_time = time.time() - (max_age_days * 24 * 3600)
        removed = 0
        
        for cache_dir in self.cache_dirs.values():
            if not cache_dir.exists():
                continue
                
            for cache_file in cache_dir.iterdir():
                if cache_file.is_file() and cache_file.stat().st_mtime < cutoff_time:
                    try:
                        cache_file.unlink()
                        removed += 1
                    except Exception as e:
                        logger.warning(f"Could not remove old cache file {cache_file}: {e}")
                        
        logger.info(f"Removed {removed} old cache files")
        return removed
        
    def get_stats(self) -> dict:
        """Get cache statistics."""
        stats = self.stats.copy()
        stats['cache_size_gb'] = self.get_cache_size()
        stats['hit_rate'] = stats['hits'] / max(stats['hits'] + stats['misses'], 1)
        return stats
        
    def print_stats(self) -> None:
        """Print cache statistics."""
        stats = self.get_stats()
        logger.info("Cache Statistics:")
        logger.info(f"  Hits: {stats['hits']}")
        logger.info(f"  Misses: {stats['misses']}")
        logger.info(f"  Hit Rate: {stats['hit_rate']:.2%}")
        logger.info(f"  Cache Size: {stats['cache_size_gb']:.2f} GB")
        logger.info(f"  Invalidations: {stats['invalidations']}")


# Global cache manager instance
_cache_manager = None


def get_cache_manager(config=None) -> CacheManager:
    """Get or create the global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager(config)
    return _cache_manager


def cached_method(cache_type: str = 'calculations', 
                 include_self: bool = True,
                 input_files_attr: Optional[str] = None,
                 config_attrs: Optional[list] = None):
    """
    Decorator to cache method results.
    
    Args:
        cache_type: Type of cache to use
        include_self: Include self object in cache key generation
        input_files_attr: Attribute name containing input file paths
        config_attrs: List of config attributes to include in cache key
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get config from self object if available
            config = None
            if args and hasattr(args[0], 'config'):
                config = args[0].config
                
            cache_manager = get_cache_manager(config)
            
            if not cache_manager.enabled:
                return func(*args, **kwargs)
                
            # Generate cache key
            function_name = f"{func.__module__}.{func.__qualname__}"
            
            # Extract input files if specified
            input_files = []
            if input_files_attr and args and hasattr(args[0], input_files_attr):
                files = getattr(args[0], input_files_attr)
                if isinstance(files, (list, tuple)):
                    input_files.extend(files)
                elif files:
                    input_files.append(files)
                    
            # Extract config parameters
            config_params = {}
            if config_attrs and args and hasattr(args[0], 'config'):
                config = args[0].config
                for attr in config_attrs:
                    if hasattr(config, attr):
                        config_params[attr] = getattr(config, attr)
                        
            # Include method parameters
            parameters = {
                'args': args[1:] if include_self else args,
                'kwargs': kwargs
            }
            
            cache_key = cache_manager.generate_cache_key(
                function_name, input_files, parameters, config_params
            )
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key, cache_type)
            if cached_result is not None:
                return cached_result
                
            # Execute function and cache result
            logger.debug(f"Cache miss for {function_name}, executing...")
            result = func(*args, **kwargs)
            
            # Cache the result
            cache_manager.set(cache_key, result, cache_type)
            
            return result
            
        return wrapper
    return decorator


def cached_function(cache_type: str = 'calculations',
                   input_files: Optional[list] = None,
                   config_params: Optional[dict] = None):
    """
    Decorator to cache function results.
    
    Args:
        cache_type: Type of cache to use
        input_files: List of input file paths
        config_params: Configuration parameters affecting the result
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_manager = get_cache_manager()
            
            if not cache_manager.enabled:
                return func(*args, **kwargs)
                
            # Generate cache key
            function_name = f"{func.__module__}.{func.__qualname__}"
            parameters = {'args': args, 'kwargs': kwargs}
            
            cache_key = cache_manager.generate_cache_key(
                function_name, input_files, parameters, config_params
            )
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key, cache_type)
            if cached_result is not None:
                logger.debug(f"Cache hit for {function_name}")
                return cached_result
                
            # Execute function and cache result
            logger.debug(f"Cache miss for {function_name}, executing...")
            result = func(*args, **kwargs)
            
            # Cache the result
            cache_manager.set(cache_key, result, cache_type)
            
            return result
            
        return wrapper
    return decorator 