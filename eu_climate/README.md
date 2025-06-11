# EU Climate Risk Assessment System

A comprehensive geospatial analysis tool for assessing climate risks in European regions using a four-layer approach: Hazard, Exposition, Relevance, and Risk.

## System Architecture

### Risk Assessment Layers

1. **Hazard Layer** - Sea level rise and flood risk assessment
2. **Exposition Layer** - Building density, population, and infrastructure exposure
3. **Relevance Layer** - Economic importance and vulnerability factors
4. **Risk Layer** - Integrated risk assessment combining all factors

### Unified Visualization Framework

The system implements a **unified visualization approach** ensuring consistency across all layers:

#### Key Features
- **Consistent Study Area Definition**: All layers use NUTS-L3 boundaries for spatial reference
- **Scientific Publication Standards**: Minimalistic, professional styling suitable for academic publications
- **Standardized Color Schemes**: 
  - Elevation: `terrain` colormap
  - Hazard: `Reds` colormap
  - Exposition: `viridis` colormap
  - Relevance: `inferno` colormap
- **Unified Coordinate Handling**: Proper alignment and extent calculation across all layers
- **Automated PNG Generation**: All layers automatically generate publication-ready PNG visualizations

#### Implementation Details

**LayerVisualizer Class** (`eu_climate/utils/visualization.py`):
- Centralized visualization utilities
- Consistent NUTS boundary overlays
- Standardized statistics boxes and colorbars
- Scientific styling configuration

**ScientificStyle Configuration**:
- Figure size: 12x8 inches at 300 DPI
- Font family: sans-serif with consistent sizing
- NUTS boundaries: Dark blue-gray (#2c3e50) with 0.8 width
- Statistics boxes: White background with rounded corners

### Spatial Consistency

All layers now use **NUTS-L3 boundaries** as the primary spatial reference:

1. **Hazard Layer**: Updated to use NUTS-L3 bounds instead of full DEM extent
2. **Exposition Layer**: Already using NUTS-L3 bounds for consistency
3. **Relevance Layer**: Uses exposition layer metadata for perfect spatial alignment

This ensures:
- Consistent study area coverage across all analyses
- Proper spatial alignment for risk integration
- Clean visualization boundaries matching administrative regions

### Automated Output Generation

Each layer automatically generates:
- **GeoTIFF files**: For spatial analysis and further processing
- **PNG visualizations**: Publication-ready figures with consistent styling
- **Summary statistics**: Quantitative analysis results

#### Usage Examples

```python
# Exposition Layer with PNG generation
exposition_layer = ExpositionLayer(config)
exposition_layer.run_exposition(create_png=True)

# Hazard Layer with PNG generation
hazard_layer = HazardLayer(config)
flood_extents = hazard_layer.process_scenarios()
hazard_layer.export_results(flood_extents, create_png=True)

# Relevance Layer with unified visualization
relevance_layer = RelevanceLayer(config)
relevance_layers = relevance_layer.run_relevance_analysis(visualize=True)
```

### Best Practices

#### Visualization Standards
- Use unified LayerVisualizer for all new visualizations
- Follow ScientificStyle configuration for consistency
- Include NUTS boundary overlays for geographic context
- Add statistics boxes for quantitative information

#### Spatial Reference
- Always use NUTS-L3 boundaries for study area definition
- Ensure proper coordinate alignment using transformer utilities
- Validate spatial consistency across layers before integration

#### Code Quality
- Follow naming conventions (no abbreviations, descriptive names)
- Use type hints and docstrings for all public functions
- Implement early returns to reduce nesting
- Extract complex logic into well-named helper functions

## Technical Implementation

### Data Processing Pipeline
- Robust ETL processes for harmonizing diverse datasets
- Standardized cartographic projections (EPSG:3035)
- Risk approximation based on climate data and normalization factors
- Downsampling techniques for fine-grained spatial analysis (30m resolution)

### Caching System
- Intelligent caching for expensive computations
- Cache-aware method decorators
- Configurable cache invalidation strategies

### Quality Assurance
- Comprehensive data validation
- Automated integrity checks
- Error handling and logging throughout the pipeline

## File Structure

```
eu_climate/
├── config/           # Configuration management
├── risk_layers/      # Core analysis layers
│   ├── hazard_layer.py
│   ├── exposition_layer.py
│   ├── relevance_layer.py
│   └── risk_layer.py
├── utils/            # Shared utilities
│   ├── visualization.py  # Unified visualization framework
│   ├── conversion.py     # Spatial transformations
│   └── utils.py         # General utilities
├── data/             # Data directory (synced with HuggingFace)
│   ├── source/       # Input datasets
│   └── output/       # Generated results
├── debug/            # Log files
├── scripts/          # Data management scripts
└── main.py          # Main execution entry point
```

## Getting Started

1. **Initialize Configuration**:
   ```python
   from eu_climate.config.config import ProjectConfig
   config = ProjectConfig()
   ```

2. **Run Complete Analysis**:
   ```python
   from eu_climate.main import RiskAssessment
   risk_assessment = RiskAssessment(config)
   # Individual layers with PNG generation
   risk_assessment.run_hazard_layer_analysis(config)
   risk_assessment.run_exposition(config)
   risk_assessment.run_relevance_layer_analysis(config)
   ```

3. **Access Results**:
   - GeoTIFF files: `data/output/*.tif`
   - PNG visualizations: `data/output/*.png`
   - Summary statistics: `data/output/*_summary.csv`

## Dependencies

- **Geospatial**: rasterio, geopandas, shapely
- **Scientific Computing**: numpy, scipy, scikit-learn
- **Visualization**: matplotlib
- **Data Management**: pandas, huggingface_hub
- **Configuration**: pydantic, python-dotenv

## Contributing

When adding new features:
1. Use the unified LayerVisualizer for all visualizations
2. Ensure NUTS-L3 spatial consistency
3. Follow the established naming conventions
4. Add comprehensive docstrings and type hints
5. Update this README with any architectural changes

## Authors

EU Geolytics Team - Climate Risk Assessment Specialists

## 🎯 Project Overview

This system implements a robust and reproducible data processing pipeline that systematically processes climate data, economic indicators, and social metrics to provide precise risk assessments at multiple spatial scales.

### Technical Implementation Framework

- **Robust ETL Pipeline**: Extract, Transform, Load processes for harmonizing diverse datasets
- **Standardized Cartographic Projections**: Unified spatial representation using EPSG:3035 (ETRS89-extended / LAEA Europe)
- **Risk Approximation**: Combination of climate data, sea level projections, and normalization factors
- **Downsampling Techniques**: Complex aggregated information brought to fine spatial resolution
- **Code-based Visualizations**: Python and QGIS-compatible outputs

## 🏗️ System Architecture

### Three-Layer Risk Assessment Model

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   HAZARD LAYER  │    │ EXPOSITION LAYER│    │   RISK LAYER    │
│                 │    │                 │    │                 │
│ • Sea Level Rise│    │ • Population    │    │ • Integrated    │
│ • DEM Analysis  │    │ • Economics     │    │   Risk Metrics  │
│ • Flood Extents │────│ • Infrastructure│────│ • Multi-criteria│
│ • Climate Data  │    │ • Building      │    │   Assessment    │
│                 │    │   Density       │    │ • Scenarios     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- GDAL/OGR libraries (for geospatial processing)
- Required data files in the `data/` directory

### Installation

1. **Clone or download the project**
2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Ensure data files are in place:**
   - `data/ClippedCopernicusHeightProfile.tif` (European DEM)
   - Additional datasets as needed

### Running the Analysis

```bash
# Navigate to the code directory
cd code

# Run the complete risk assessment
python main.py
```

## 📊 Hazard Layer Implementation

The **Hazard Layer** is the foundation of our risk assessment system, processing Digital Elevation Model (DEM) data to assess sea level rise impacts.

### Key Features

- **Configurable Sea Level Rise Scenarios**: Default scenarios include 1m, 2m, and 3m rises
- **DEM Processing**: Handles Copernicus Height Profile data with proper nodata handling
- **Flood Extent Calculation**: Identifies areas vulnerable to flooding based on elevation
- **Comprehensive Visualization**: Multi-panel plots showing original DEM, flood extents, and statistics

### Sea Level Rise Scenarios

| Scenario     | Rise (m) | Description                 | Risk Level |
| ------------ | -------- | --------------------------- | ---------- |
| Conservative | 1.0      | Conservative sea level rise | Low        |
| Moderate     | 2.0      | Moderate sea level rise     | Medium     |
| Severe       | 3.0      | Severe sea level rise       | High       |

### Customizing Scenarios

You can define custom scenarios by modifying the `SeaLevelScenario` class:

```python
from main import SeaLevelScenario, HazardLayer, ProjectConfig

# Define custom scenarios
custom_scenarios = [
    SeaLevelScenario("Optimistic", 0.5, "0.5m rise - optimistic scenario"),
    SeaLevelScenario("Extreme", 5.0, "5m rise - extreme scenario")
]

# Initialize and run with custom scenarios
config = ProjectConfig()
hazard_layer = HazardLayer(config)
flood_extents = hazard_layer.process_scenarios(custom_scenarios)
```

## 📈 Output Files

The system generates several output files in the `output/` directory:

### Geospatial Data

- `flood_extent_conservative.tif` - Conservative scenario flood extent (GeoTIFF)
- `flood_extent_moderate.tif` - Moderate scenario flood extent (GeoTIFF)
- `flood_extent_severe.tif` - Severe scenario flood extent (GeoTIFF)

### Visualizations

- `hazard_layer_assessment.png` - Comprehensive hazard assessment visualization

### Statistics

- `hazard_assessment_summary.csv` - Summary statistics for all scenarios

### Log Files

- `risk_assessment.log` - Detailed processing log

## 🔧 Configuration

### Project Configuration

The `ProjectConfig` class allows customization of key parameters:

```python
@dataclass
class ProjectConfig:
    data_dir: Path = Path("data")              # Data directory
    output_dir: Path = Path("output")          # Output directory
    dem_file: str = "ClippedCopernicusHeightProfile.tif"  # DEM filename
    target_crs: str = "EPSG:3035"             # Target projection
    figure_size: Tuple[int, int] = (15, 10)   # Plot dimensions
    dpi: int = 300                            # Output resolution
```

### Coordinate Reference System

The system uses **EPSG:3035** (ETRS89-extended / LAEA Europe) as the standard projection, ensuring:

- Accurate area calculations across Europe
- Minimal distortion for the study region
- Compatibility with EU statistical frameworks

## 📊 Data Requirements

### Primary Data Sources

1. **Digital Elevation Model (DEM)**

   - Source: Copernicus Land Monitoring Service
   - File: `ClippedCopernicusHeightProfile.tif`
   - Resolution: 30m (typical)
   - Coverage: European study area

2. **Administrative Boundaries** (Available)

   - NUTS Level 0-3 boundaries for Netherlands
   - Relevant area shapefiles

3. **Population Data** (Available for future implementation)

   - GHS Population data (`ClippedGHS_POP_3ss.tif`)

4. **Built Environment Data** (Available for future implementation)
   - GHS Built-up Surface data (`ClippedGHS_Built-S_3ss.tif`)

## 🎨 Visualization Features

The system produces comprehensive visualizations including:

1. **Original DEM Display** - Terrain visualization with elevation coloring
2. **Flood Extent Maps** - Binary maps showing flooded vs. safe areas for each scenario
3. **Risk Progression Chart** - Bar chart comparing flooded areas across scenarios
4. **Elevation Histogram** - Distribution of elevations with flood thresholds marked

## 🚧 Future Development

### Exposition Layer (Planned)

- Population density exposure analysis
- Economic activity mapping
- Infrastructure exposure assessment
- Building density integration

### Risk Assessment Integration (Planned)

- Multi-criteria risk calculation
- Vulnerability assessment
- Risk aggregation and normalization
- Scenario comparison and ranking

## 📋 System Requirements

### Minimum Requirements

- Python 3.8+
- 8GB RAM (for processing large raster datasets)
- 2GB free disk space
- GDAL libraries

### Recommended Requirements

- Python 3.10+
- 16GB RAM
- SSD storage
- Multi-core processor for faster processing

## 🤝 Contributing

This system follows scientific software development best practices:

1. **Reproducible Research**: All analyses are scripted and version-controlled
2. **Modular Design**: Clear separation between Hazard, Exposition, and Risk layers
3. **Documentation**: Comprehensive inline documentation and logging
4. **Standardization**: Consistent coordinate systems and data formats

## 📝 License

This project is developed for academic research purposes as part of the EU Geolytics initiative.

## 📞 Support

For questions or technical support, please refer to the project documentation or contact the EU Geolytics team.

---

**EU Geolytics Team** | Version 1.0.0 | 2025

# Data Management

## Configuration

The project uses a combination of environment variables and YAML configuration to manage data handling settings. Configuration can be set in two ways:

1. **Environment Variables** (Recommended for sensitive data)

   ```bash
   # Create a .env file in the code directory
   cp .env.template .env
   # Edit the .env file with your settings
   ```

   Available environment variables:

   - `HF_API_TOKEN`: Your Hugging Face API token (required for upload)
   - `HF_REPO`: Hugging Face repository name (default: "TjarkGerken/eu-data")
   - `AUTO_DOWNLOAD`: Enable/disable automatic downloads (default: true)
   - `ENABLE_UPLOAD`: Enable/disable data upload (default: false)

2. **YAML Configuration** (`code/config/data_config.yaml`)
   ```yaml
   data:
     huggingface_repo: "TjarkGerken/eu-data"
     auto_download: true
     data_paths:
       local_data_dir: "code/data"
       local_output_dir: "code/output"
   ```

Environment variables take precedence over YAML configuration. This ensures sensitive data like API tokens can be kept secure and not committed to version control.

## Data Download

There are two ways to get the required data:

### 1. Automatic Download (Recommended)

The data will be automatically downloaded when running the project if auto-download is enabled. To enable this:

1. Ensure either:
   - `AUTO_DOWNLOAD=true` in your `.env` file, or
   - `auto_download: true` in `code/config/data_config.yaml`
2. The data will be downloaded automatically when needed

### 2. Manual Download

If automatic download is disabled or fails:

1. Visit https://huggingface.co/datasets/TjarkGerken/eu-data
2. Download the following directories:
   - `code/data`
   - `code/output`
3. Place them in their respective locations in your project directory

## Uploading Data

To upload data to the Hugging Face repository:

1. Get your Hugging Face API token from https://huggingface.co/settings/tokens

2. Set up your environment:

   ```bash
   # In your .env file
   HF_API_TOKEN="your_api_token_here"
   ```

3. Upload the data using one of these methods:

   a. Using the upload script:

   ```bash
   # Navigate to the code directory
   cd code

   # Run the upload script
   ./scripts/upload_data.py
   ```

   b. Using Python:

   ```python
   from utils.data_loading import upload_data

   # Upload both data and output directories
   success = upload_data()
   ```

   The script will:

   - Validate your API token and configuration
   - Upload the contents of `code/data` and `code/output` directories
   - Provide detailed logging of the upload process
   - Exit with a non-zero status if any uploads fail

## Directory Structure

The project expects the following data directory structure:

```
code/
├── data/          # Input data directory
└── output/        # Output data directory
```
