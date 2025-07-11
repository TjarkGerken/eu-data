# Configuration Documentation

This folder contains all configuration files and utilities for the EU Climate Risk Assessment project.

## Files Overview

### 📁 Configuration Files

| File            | Purpose               | Description                                            |
| --------------- | --------------------- | ------------------------------------------------------ |
| `config.yaml`   | Main configuration    | Contains all project parameters, weights, and settings |
| `config.py`     | Configuration manager | Python class that loads and validates configuration    |
| `.template.env` | Environment template  | Template for required environment variables            |

## Quick Start

### 1. Set up Environment Variables

Copy the template and fill in your credentials:

```bash
cp .template.env .env
# Edit .env with your actual tokens
```

### 2. Configure Project Settings

The main configuration is in `config.yaml`. Most default values should work out of the box, but you may want to adjust:

- **Data paths**: Where your input data is located
- **Processing parameters**: Resolution, resampling methods
- **Risk assessment weights**: How different factors are weighted
- **Output settings**: What formats to export

### 3. Use Configuration in Code

```python
from eu_climate.config.config import ProjectConfig

# Load configuration
config = ProjectConfig()

# Access data paths
data_dir = config.data_dir
dem_path = config.dem_path

# Access processing parameters
resolution = config.target_resolution
crs = config.target_crs
```

## Configuration Sections

### 🛠️ Processing Parameters

Controls how data is processed and transformed:

```yaml
processing:
  resampling_method: "bilinear" # How to resample raster data
  target_resolution: 30.0 # Target resolution in meters
  target_crs: "EPSG:3035" # Target coordinate reference system
  smoothing_sigma: 1.0 # Gaussian smoothing parameter
```

**Available resampling methods:**

- `nearest`: Nearest neighbor (fast, preserves original values)
- `bilinear`: Bilinear interpolation (smooth, good for continuous data)
- `cubic`: Cubic interpolation (smoother, computationally intensive)
- `average`: Average of source pixels (good for aggregation)

### 🗺️ Data Paths

Specifies where input data files are located:

```yaml
data_paths:
  local_data_dir: "data" # Root data directory
  source_data_dir: "source" # Source data subdirectory
  local_output_dir: "output" # Output directory
```

### 📊 Risk Assessment

Controls how risk is calculated and weighted:

```yaml
risk_assessment:
  n_risk_classes: 5 # Number of risk categories
  weights:
    hazard: 0.1 # Weight for hazard component
    economic: 0.9 # Weight for economic component
```

**Risk Components:**

- **Hazard**: Physical risk factors (flooding, elevation, proximity to water)
- **Economic**: Economic exposure and vulnerability factors

### 🏗️ Exposition Weights

How different exposure factors are weighted:

```yaml
exposition:
  ghs_built_c_weight: 0.30 # Built-up area coverage weight
  ghs_built_v_weight: 0.30 # Built-up volume weight
  population_weight: 0.13 # Population density weight
  electricity_consumption_weight: 0.12 # Electricity consumption weight
  vierkant_stats_weight: 0.15 # Census statistics weight
```

### 🌊 Hazard Configuration

Physical risk factors and their parameters:

```yaml
hazard:
  river_zones:
    high_risk_distance_m: 50 # High risk zone around rivers
    high_risk_weight: 1.15 # Risk multiplier for high risk zones
    moderate_risk_distance_m: 200 # Moderate risk zone
    moderate_risk_weight: 1.1 # Risk multiplier for moderate zones

  elevation_risk:
    max_safe_elevation_m: 25.0 # Elevation above which risk decreases
    risk_decay_factor: 1.4 # How quickly risk decreases with elevation

  coastline_risk:
    coastline_multiplier: 1.1 # Risk multiplier near coastlines
    coastline_distance_m: 5000 # Distance from coast for risk calculation
```

### 💰 Economic Relevance

How economic factors are incorporated:

```yaml
relevance:
  min_economic_value: 0.05 # Minimum economic value threshold
  economic_datasets:
    gdp:
      weight: 0.25 # GDP weight in economic assessment
      nuts_level: "l3" # NUTS administrative level
    freight:
      weight: 0.5 # Freight/transport weight
    hrst:
      weight: 0.25 # Human resources in science/technology weight
```

### 🌐 Web Export Settings

Configuration for web-ready outputs:

```yaml
web_exports:
  enabled: true
  create_cog: true # Create Cloud Optimized GeoTIFF
  create_mvt: true # Create Mapbox Vector Tiles

  cog_settings:
    compress: "LZW" # Compression method
    blocksize: 512 # Internal tile size
    auto_overviews: true # Generate overview pyramids

  mvt_settings:
    min_zoom: 0 # Minimum zoom level
    max_zoom: 12 # Maximum zoom level
    buffer_size: 64 # Tile buffer size
```

### 🎯 Clustering Parameters

Settings for risk cluster detection:

```yaml
clustering:
  risk_threshold: 0.35 # Minimum risk for clustering
  cell_size_meters: 30 # Grid cell size
  minimum_polygon_area_square_meters: 12000000 # Minimum cluster area
  smoothing_buffer_meters: 200 # Smoothing buffer
  polygon_simplification_tolerance: 50 # Polygon simplification
```

## Configuration Validation

The configuration system includes automatic validation:

### Weight Validation

All weight groups must sum to 1.0:

- Risk assessment weights (hazard + economic = 1.0)
- Exposition weights (all components = 1.0)
- Economic dataset weights (all datasets = 1.0)

### File Validation

The `validate_files()` method checks that all required input files exist:

```python
config = ProjectConfig()
config.validate_files()  # Raises FileNotFoundError if files missing
```

## Environment Variables

Required environment variables (set in `.env`):

```bash
# Hugging Face API token for data access
HF_API_TOKEN="your_huggingface_token_here"
```

## Configuration Properties

The `ProjectConfig` class provides convenient properties for accessing file paths:

### Data File Properties

- `config.dem_path` - Digital elevation model
- `config.population_path` - Population density data
- `config.ghs_built_c_path` - Built-up area coverage
- `config.ghs_built_v_path` - Built-up volume
- `config.nuts_paths` - NUTS administrative boundaries
- `config.river_polygons_path` - River/water bodies
- `config.coastline_path` - Coastline data

### Processing Properties

- `config.target_resolution` - Target resolution in meters
- `config.target_crs` - Target coordinate reference system
- `config.resampling_method` - Resampling method enum
- `config.smoothing_sigma` - Smoothing parameter

### Risk Assessment Properties

- `config.risk_weights` - Risk component weights
- `config.exposition_weights` - Exposure factor weights
- `config.economic_datasets` - Economic dataset configuration
