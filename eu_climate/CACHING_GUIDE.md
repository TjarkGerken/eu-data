# EU Climate Risk Assessment - Caching System Guide

## Overview

The EU Climate Risk Assessment system now includes a comprehensive caching solution that significantly improves performance by storing intermediate and final results. This caching system is designed to be completely transparent to the existing layer logic while providing substantial speed improvements for repeated computations.

## Key Features

- **Non-intrusive**: Zero modifications to existing layer code
- **Transparent**: Automatically caches expensive operations
- **Configurable**: Enable/disable caching via configuration
- **Persistent**: Cache survives between application runs
- **Intelligent**: Automatic cache invalidation based on input changes
- **Multi-format**: Optimized storage for different data types

## Architecture

### Cache Storage Structure

```
.cache/eu_climate/
├── raster_data/          # Large raster transformations (HDF5 format)
├── calculations/         # Intermediate calculations (compressed pickle)
├── final_results/        # Final layer outputs (compressed pickle)
├── metadata/             # Cache metadata and indices
└── config_snapshots/     # Configuration states for invalidation
```

### Cache Types

1. **Raster Data Cache**: Large geospatial arrays stored in compressed HDF5 format
2. **Calculations Cache**: Intermediate results stored as compressed pickle files
3. **Final Results Cache**: Complete layer outputs and risk assessments

## Configuration

### Enabling/Disabling Caching

Edit `eu_climate/config/data_config.yaml`:

```yaml
caching:
  enabled: true                    # Enable/disable caching
  cache_dir: ".cache"             # Cache directory location
  max_cache_size_gb: 10           # Maximum cache size in GB
  auto_cleanup: true              # Automatic cleanup of old files
  max_age_days: 7                 # Remove files older than N days
  cache_strategies:
    raster_data: "persistent"     # Cache large raster transformations
    calculations: "persistent"    # Cache intermediate calculations  
    final_results: "persistent"   # Cache final layer outputs
  logging:
    cache_operations: false       # Log individual cache operations (debug)
    cache_statistics: true        # Log cache statistics
```

### Cache Configuration Options

- **enabled**: Turn caching on/off globally
- **max_cache_size_gb**: Prevent cache from growing too large
- **auto_cleanup**: Automatically remove old cache files
- **max_age_days**: Age threshold for automatic cleanup
- **cache_strategies**: Control caching behavior for different data types

## Usage

### Automatic Integration

The caching system is automatically integrated into `main.py`. No changes to your workflow are required:

```python
# This code automatically uses caching when enabled
from eu_climate.main import main

if __name__ == "__main__":
    main()  # Caching is applied transparently
```

### Manual Layer Caching

If you need to manually apply caching to individual layers:

```python
from eu_climate.utils.cache_utils import create_cached_layers
from eu_climate.risk_layers.hazard_layer import HazardLayer

# Create layer instance
hazard_layer = HazardLayer(config)

# Apply caching
cached_layers = create_cached_layers(hazard_layer=hazard_layer, config=config)
cached_hazard_layer = cached_layers['hazard']

# Use cached layer (same interface as original)
flood_extents = cached_hazard_layer.process_scenarios()
```

### Cached Methods

The following methods are automatically cached when the system is enabled:

#### HazardLayer
- `load_and_prepare_dem()` - DEM loading and transformation
- `load_river_data()` - River network data loading
- `calculate_flood_extent()` - Flood extent calculations
- `process_scenarios()` - Multi-scenario processing

#### ExpositionLayer
- `load_and_preprocess_raster()` - Raster loading and preprocessing
- `calculate_exposition()` - Final exposition calculation
- `normalize_ghs_built_c()` - GHS Built-C normalization
- `normalize_raster()` - General raster normalization

## Cache Management

### Command Line Interface

Use the cache management CLI for cache operations:

```bash
# Show cache statistics
python eu_climate/scripts/cache_manager_cli.py --stats

# Clear all cache data
python -m eu_climate.scripts.cache_manager_cli --clear all

# Clear specific cache type
python -m eu_climate.scripts.cache_manager_cli --clear raster_data

# Remove files older than 7 days
python eu_climate/scripts/cache_manager_cli.py --cleanup 7

# Show detailed size breakdown
python eu_climate/scripts/cache_manager_cli.py --size

# Show cache configuration
python eu_climate/scripts/cache_manager_cli.py --info
```

### Programmatic Cache Management

```python
from eu_climate.utils.cache_utils import get_cache_integrator

# Get cache integrator
integrator = get_cache_integrator(config)

# Print statistics
integrator.print_cache_statistics()

# Clear specific cache type
integrator.clear_cache('raster_data')

# Clean up old files
integrator.cleanup_cache(max_age_days=7)

# Get cache information
cache_info = integrator.get_cache_info()
```

## Cache Invalidation

The caching system automatically invalidates cache entries when:

1. **Input files change**: File modification time or size changes
2. **Configuration changes**: Processing parameters are modified
3. **Method parameters change**: Different function arguments
4. **Manual invalidation**: Explicit cache clearing

### Cache Key Generation

Cache keys are generated based on:
- Function/method name
- Input file paths and timestamps
- Method parameters
- Relevant configuration parameters

## Performance Benefits

### Expected Performance Improvements

- **First run**: Normal execution time (cache miss)
- **Subsequent runs**: 50-90% reduction in computation time
- **Parameter variations**: Cached intermediate results speed up analysis
- **Visualization iterations**: Near-instant visualization regeneration

### Memory Efficiency

- **Compressed storage**: HDF5 and gzip compression reduce storage requirements
- **Selective loading**: Only required cached data is loaded into memory
- **Automatic cleanup**: Old cache files are automatically removed

## Troubleshooting

### Common Issues

#### Cache Not Working
1. Check if caching is enabled in `data_config.yaml`
2. Verify cache directory permissions
3. Check available disk space

#### Cache Size Growing Too Large
1. Reduce `max_cache_size_gb` in configuration
2. Enable `auto_cleanup`
3. Manually clean old files: `--cleanup 3`

#### Cache Invalidation Issues
1. Clear specific cache type: `--clear calculations`
2. Clear all cache: `--clear all`
3. Check file timestamps if using network storage

### Debug Mode

Enable detailed cache logging:

```yaml
caching:
  logging:
    cache_operations: true  # Enable debug logging
```

### Performance Monitoring

```python
# Print cache statistics after analysis
from eu_climate.utils.cache_utils import print_cache_status

print_cache_status(config)
```

## Implementation Details

### Cache Key Algorithm

1. Combine function name, file paths, and parameters
2. Include file modification times and sizes
3. Generate SHA256 hash for unique identification
4. Store with appropriate file extension based on cache type

### Storage Formats

- **Raster data**: HDF5 with gzip compression (level 6)
- **Calculations**: Pickle with gzip compression
- **Final results**: Pickle with gzip compression
- **Metadata**: JSON format for configuration snapshots

### Thread Safety

The caching system is designed to be thread-safe for read operations. Write operations are protected by file system locks.

## Advanced Usage

### Custom Cache Decorators

For custom methods, you can apply caching decorators:

```python
from eu_climate.utils.caching_wrappers import cache_raster_method

class CustomLayer:
    @cache_raster_method(
        input_files=['input_file_path'],
        config_attrs=['target_crs', 'resolution']
    )
    def process_custom_data(self, parameters):
        # Your processing logic here
        return processed_data
```

### Cache-Aware Development

When developing new methods that should be cached:

1. Identify expensive operations
2. Determine appropriate cache type
3. Add method to cache configuration
4. Test cache invalidation behavior

## Best Practices

1. **Enable caching for development**: Speeds up testing and debugging
2. **Monitor cache size**: Set appropriate size limits
3. **Regular cleanup**: Use automatic cleanup or periodic manual cleanup
4. **Test without cache**: Occasionally disable cache to verify correctness
5. **Network storage**: Be aware of timestamp precision on network filesystems

## Migration and Compatibility

The caching system is fully backward compatible:
- Existing code works without modification
- Caching can be disabled without affecting functionality
- Cache can be safely cleared at any time
- No changes to layer interfaces or return values

## Support

For issues or questions about the caching system:
1. Check this guide for common solutions
2. Use the CLI tools for diagnostics
3. Enable debug logging for detailed information
4. Verify configuration settings 