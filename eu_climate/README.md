# EU Climate Risk Assessment System

A comprehensive geospatial analysis tool for assessing climate risks in European regions using a three-layer approach: **Hazard**, **Exposition**, and **Risk**.

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
