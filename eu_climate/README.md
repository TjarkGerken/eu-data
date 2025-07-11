# EU Climate Risk Assessment Framework

A comprehensive geospatial analysis framework for climate risk assessment in European regions, implementing a four-layer approach: **Hazard**, **Exposition**, **Relevance**, and **Risk**. This system provides robust data processing pipelines, multi-scenario analysis capabilities, and web-optimized outputs for modern climate risk visualization.

## 🎯 Project Overview

### Key Features

- **Multi-Layer Risk Assessment**: Implements a scientifically-grounded four-layer approach for comprehensive climate risk analysis
- **Sea Level Rise Scenarios**: Supports multiple scenarios from current levels to extreme 15m rise projections (2025-2300)
- **Advanced Data Processing**: Robust ETL pipelines with standardized cartographic projections and normalization
- **Web-Ready Outputs**: Automatic generation of Cloud-Optimized GeoTIFF (COG) and Mapbox Vector Tiles (MVT) for web applications
- **Economic Impact Analysis**: Quantitative assessment of GDP, freight, and human resources at risk
- **Cluster Analysis**: Spatial clustering of high-risk areas with polygon extraction and smoothing
- **Interactive Visualization**: Comprehensive plotting and mapping capabilities with standardized color schemes

### Technical Architecture

- **Language**: Python 3.11+
- **Key Libraries**: GeoPandas, Rasterio, Scikit-learn, Matplotlib, Folium
- **Data Storage**: Cloud-integrated with Hugging Face Hub for dataset management
- **Output Formats**: GeoTIFF, GeoPackage, COG, MVT, PNG, CSV
- **Coordinate System**: EPSG:3035 (European standard)
- **Resolution**: 30m standardized grid

## 📋 Table of Contents

1. [🚀 Quick Start](#-quick-start)
2. [💻 Environment Setup](#-environment-setup)
3. [🌐 Data Management](#-data-management)
4. [🔧 Running the Analysis](#-running-the-analysis)
5. [📊 Output Formats](#-output-formats)
6. [🛠️ Advanced Usage](#️-advanced-usage)
7. [📁 Project Structure](#-project-structure)
8. [📦 Datasets Overview](#-datasets-overview)
9. [🔬 Technical Details](#-technical-details)
10. [🤝 Contributing](#-contributing)

## 🚀 Quick Start

### Prerequisites

- **Python**: 3.11+ (Python 3.11 recommended for optimal geospatial library compatibility)
- **Storage**: At least 20 GB of free disk space
- **Memory**: Minimum 16 GB RAM (32 GB recommended for large-scale analysis)
- **Platform**: Windows (WSL), Linux, or macOS

### Fastest Setup (Recommended)

```bash
# Clone the repository
git clone https://github.com/TjarkGerken/eu-data
cd eu-data/eu_climate

# Create virtual environment
python3 -m venv ./.venv
source ./.venv/bin/activate  # On Windows: .\.venv\Scripts\activate

# Install dependencies
pip install -r ../requirements.txt

# Configure Hugging Face token (required for data access)
cd config
cp .template.env .env
# Edit .env file and add: HF_API_TOKEN=hf_YOUR_TOKEN_HERE

# Run complete analysis
python -m eu_climate.main
```

## 💻 Environment Setup

### Option 1: Linux/macOS (Full Feature Support)

**Advantages**: Complete web export support, native performance, all features available

```bash
# Create virtual environment
python3 -m venv ./.venv
source ./.venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Install system dependencies for web exports
# Ubuntu/Debian:
sudo apt update
sudo apt install gdal-bin libgdal-dev tippecanoe

# macOS:
brew install gdal tippecanoe

# Verify installation
python -c "import rasterio, geopandas; print('✅ All dependencies working!')"
```

### Option 2: Windows with WSL (Recommended)

**Advantages**: Full feature support, Docker-like isolation, consistent behavior

```powershell
# Install WSL2 if not already installed
wsl --install

# Use the provided PowerShell runner
.\run_in_wsl.ps1 main
```

### Option 3: Native Windows (Limited Features)

**Advantages**: Simpler setup, no WSL required  
**Limitations**: Limited web export support (COG only, no tippecanoe), potential GDAL issues

```powershell
# Install Anaconda/Miniconda
# Download from: https://www.anaconda.com/download

# Create conda environment
conda create -n eu-climate python=3.11 gdal rasterio geopandas numpy pandas matplotlib scipy pyyaml -c conda-forge -y
conda activate eu-climate
pip install -r requirements.txt

# Run analysis
python eu_climate/main.py
```

## 🌐 Data Management

### Automatic Data Download (Recommended)

The system automatically downloads required datasets from Hugging Face Hub:

1. **Configure Hugging Face Token**:

   ```bash
   cd eu_climate/config
   cp .template.env .env
   ```

2. **Get Token**: Visit [Hugging Face Settings](https://huggingface.co/settings/tokens) and create a token with **write access**

3. **Add Token to .env**:
   ```env
   HF_API_TOKEN=hf_YOUR_TOKEN_HERE
   ```

### Manual Data Download

If automatic download fails or you prefer manual setup:

1. Visit: [EU Climate Data Repository](https://huggingface.co/datasets/TjarkGerken/eu-data)
2. Download and extract the repository contents
3. Place contents in: `eu_climate/data/source/`
4. Verify paths in `eu_climate/config/config.yaml`

### Data Upload

Upload analysis results back to Hugging Face:

```bash
# Upload only (skip analysis)
python -m eu_climate.main --upload

# Regular analysis with upload
python -m eu_climate.main  # Upload happens automatically at the end
```

## 🔧 Running the Analysis

### Basic Execution

```bash
# Complete analysis (all layers)
python -m eu_climate.main

# With verbose logging
python -m eu_climate.main --verbose
```

### Layer-Specific Analysis

```bash
# Individual layers
python -m eu_climate.main --hazard                # Sea level rise scenarios
python -m eu_climate.main --exposition            # Building density, population
python -m eu_climate.main --relevance             # Economic factors (GDP, freight, HRST)
python -m eu_climate.main --risk                  # Integrated risk assessment
python -m eu_climate.main --clusters              # Risk cluster extraction
python -m eu_climate.main --economic-impact       # Economic impact quantification

# Multiple layers
python -m eu_climate.main --hazard --exposition --relevance
```

### Specialized Analysis

```bash
# Freight-only analysis with enhanced maritime data
python -m eu_climate.main --freight-only

# Absolute relevance (preserves original values)
python -m eu_climate.main --relevance-absolute

# Population-specific analysis
python -m eu_climate.main --population

# Population relevance layer generation
python -m eu_climate.main --population-relevance
```

### Web Optimization

```bash
# Convert existing outputs to web formats
python -m eu_climate.main --web-conversion

# Analysis with automatic web export
python -m eu_climate.main --all  # Web exports created automatically
```

### Advanced Options

```bash
# Disable caching (force regeneration)
python -m eu_climate.main --no-cache

# Skip data upload
python -m eu_climate.main --no-upload

# Custom output directory
python -m eu_climate.main --output-dir /path/to/custom/output

# Download data only
python -m eu_climate.main --download
```

### WSL-Specific Commands

```powershell
# Complete analysis
.\run_in_wsl.ps1 main

# Specific layers
.\run_in_wsl.ps1 main --risk --clusters

# Web conversion demo
.\run_in_wsl.ps1 demo
```

## 📊 Output Formats

### Directory Structure

```
eu_climate/data/output/
├── hazard/                           # Sea level rise hazard analysis
│   ├── tif/                          # Standard GeoTIFF files
│   │   ├── flood_risk_current.tif
│   │   ├── flood_risk_conservative.tif
│   │   └── flood_risk_severe.tif
│   └── web/cog/                      # Cloud-Optimized GeoTIFF
│       └── flood_risk_*.tif
├── exposition/                       # Building and population exposure
│   ├── tif/
│   │   ├── exposition_layer.tif
│   │   ├── exposition_freight.tif
│   │   ├── exposition_gdp.tif
│   │   └── exposition_hrst.tif
│   └── web/cog/
├── relevance/                        # Economic relevance factors
│   ├── tif/
│   │   ├── relevance_combined.tif
│   │   ├── relevance_freight.tif
│   │   ├── relevance_gdp.tif
│   │   └── relevance_hrst.tif
│   └── web/cog/
├── risk/                             # Integrated risk assessment
│   └── SLR-{scenario}/
│       ├── tif/                      # Standard risk outputs
│       │   ├── risk_SLR-0-Current_COMBINED.tif
│       │   ├── risk_SLR-0-Current_GDP.tif
│       │   ├── risk_SLR-0-Current_FREIGHT.tif
│       │   └── risk_SLR-0-Current_POPULATION.tif
│       └── web/cog/                  # Web-optimized risk outputs
├── clusters/                         # Risk cluster polygons
│   └── SLR-{scenario}/
│       ├── gpkg/                     # Standard vector files
│       │   ├── clusters_SLR-0-Current_GDP.gpkg
│       │   └── clusters_SLR-0-Current_FREIGHT.gpkg
│       └── web/mvt/                  # Mapbox Vector Tiles
│           ├── clusters_SLR-0-Current_GDP.mbtiles
│           └── clusters_SLR-0-Current_FREIGHT.mbtiles
├── economic_impact/                  # Economic impact metrics
│   ├── current/
│   │   ├── economic_impact_current.csv
│   │   └── economic_impact_current.png
│   └── summary/
│       └── economic_impact_summary.csv
└── source/web/mvt/                   # Web-optimized source data
    ├── NUTS-L3-NL.mbtiles
    ├── PORT_RG_2025_Updated.mbtiles
    └── Europe_coastline_raw_rev2017.mbtiles
```

### File Naming Conventions

**Raster Data**:

- `{layer}_{scenario}_{type}.tif` - Standard GeoTIFF files
- `{layer}_{scenario}_{type}_cog.tif` - Cloud-Optimized GeoTIFF

**Vector Data**:

- `clusters_{scenario}_{type}.gpkg` - Standard GeoPackage files
- `clusters_{scenario}_{type}.mbtiles` - Mapbox Vector Tiles

**Scenarios**:

- `SLR-0-Current` - Current sea level conditions (2025)
- `SLR-1-Conservative` - 1m sea level rise (2100)
- `SLR-2-Moderate` - 2m sea level rise (2100)
- `SLR-3-Severe` - 3m sea level rise (2100)
- `SLR-10-Very-Severe` - 10m sea level rise (2300)
- `SLR-15-Extreme` - 15m sea level rise (2300)

**Risk Types**:

- `COMBINED` - Overall integrated risk assessment
- `POPULATION` - Population-based risk analysis
- `GDP` - Economic (GDP) risk assessment
- `FREIGHT` - Freight transport risk analysis
- `HRST` - Human resources in science & technology risk

### Web-Ready Formats

**Cloud-Optimized GeoTIFF (COG)**:

- Tiled structure for efficient web streaming
- Multiple resolution overviews
- LZW compression for optimal file size
- Compatible with modern web mapping libraries

**Mapbox Vector Tiles (MVT)**:

- Zoom levels 0-12 for multi-scale visualization
- Topology-preserving simplification
- Optimized for web rendering performance
- Direct integration with mapping frameworks

## 🛠️ Advanced Usage

### Configuration Customization

Edit `eu_climate/config/config.yaml` to modify:

```yaml
data:
  processing:
    target_resolution: 30.0 # Output resolution in meters
    resampling_method: "bilinear" # Resampling algorithm
    target_crs: "EPSG:3035" # Coordinate reference system

  risk_assessment:
    n_risk_classes: 5 # Number of risk classification levels
    weights:
      hazard: 0.1 # Hazard layer weight
      economic: 0.9 # Economic relevance weight

  clustering:
    risk_threshold: 0.35 # Minimum risk for cluster inclusion
    minimum_polygon_area_square_meters: 12000000 # Min cluster size
```

### Caching System

The framework includes an intelligent caching system:

```bash
# Enable caching (default)
python -m eu_climate.main

# Disable caching
python -m eu_climate.main --no-cache

# Clear cache
python -m eu_climate.scripts.cache_manager_cli --clear
```

### Custom Sea Level Scenarios

Modify `eu_climate/risk_layers/hazard_layer.py` to add custom scenarios:

```python
custom_scenarios = [
    SeaLevelScenario("Custom", 5.0, "5m sea level rise - custom scenario"),
    SeaLevelScenario("Extreme", 20.0, "20m sea level rise - extreme scenario")
]
```

### Performance Optimization

**Memory Management**:

- Use `--no-cache` for memory-constrained environments
- Process individual layers separately for large datasets
- Consider chunked processing for very high-resolution data

**Parallel Processing**:

- Multiple CPU cores utilized automatically for raster operations
- Vector operations parallelized where possible
- Web export conversions run in parallel

## 📁 Project Structure

```
eu_climate/
├── config/                          # Configuration management
│   ├── config.py                    # Configuration class
│   ├── config.yaml                  # Main configuration file
│   └── .template.env                # Environment template
├── risk_layers/                     # Core analysis modules
│   ├── hazard_layer.py              # Sea level rise hazard assessment
│   ├── exposition_layer.py          # Building and population exposure
│   ├── relevance_layer.py           # Economic relevance analysis
│   ├── relevance_absolute_layer.py  # Absolute value relevance
│   ├── risk_layer.py                # Integrated risk assessment
│   ├── cluster_layer.py             # Spatial clustering analysis
│   └── economic_impact_analyzer.py  # Economic impact quantification
├── utils/                           # Utility modules
│   ├── web_exports.py               # Web format conversion utilities
│   ├── cache_manager.py             # Data caching system
│   ├── data_loading.py              # Data loading and validation
│   ├── visualization.py             # Plotting and mapping utilities
│   ├── conversion.py                # Coordinate and format conversion
│   ├── normalise_data.py            # Data normalization algorithms
│   └── clustering_utils.py          # Clustering helper functions
├── scripts/                         # Utility scripts
│   ├── demo_web_exports.py          # Web export demonstration
│   ├── cache_manager_cli.py         # Cache management CLI
│   ├── upload_data.py               # Data upload utilities
│   └── validate_web_conversion.py   # Web format validation
├── data/                            # Data directory (auto-managed)
│   ├── source/                      # Input datasets
│   └── output/                      # Generated analysis results
├── debug/                           # Log files and debugging output
└── main.py                          # Main execution script
```

### Key Components

**Core Classes**:

- `ProjectConfig`: Centralized configuration management
- `HazardLayer`: Sea level rise and flood risk assessment
- `ExpositionLayer`: Building density and population exposure
- `RelevanceLayer`: Economic factor analysis and distribution
- `RiskLayer`: Integrated multi-scenario risk assessment
- `ClusterLayer`: High-risk area clustering and polygon extraction
- `EconomicImpactAnalyzer`: Quantitative economic impact assessment

**Utility Systems**:

- `WebOptimizedExporter`: COG and MVT generation
- `CacheManager`: Intelligent data caching with automatic cleanup
- `LayerVisualizer`: Standardized visualization and plotting
- `RasterTransformer`: Coordinate system and resolution management

## 📦 Datasets Overview

This section outlines all geospatial and statistical datasets used for the case study on climate risk in the Netherlands. Each dataset is grouped by thematic domain and includes source links and file structure.

---

## 🗺️ Administrative Boundaries

| Dataset                           | Description                                              | Scope/Resolution | Used in Layers  | Files                                   | Source                                                                                                           |
| --------------------------------- | -------------------------------------------------------- | ---------------- | --------------- | --------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| **NUTS Levels 0–3 (Netherlands)** | European statistical units for regional analysis (L0–L3) | NUTS L0-L3       | Relevance, Risk | `NUTS-L0-NL.shp`, ..., `NUTS-L3-NL.shp` | [Eurostat GISCO](https://ec.europa.eu/eurostat/web/gisco/geodata/statistical-units/territorial-units-statistics) |
| **GADM Shapefiles (NL, L2)**      | Administrative boundary fallback dataset                 | GADM L2          | Relevance       | `NL-GADM-L2/gadm41_NLD_2.shp`           | [GADM](https://gadm.org/download_world.html)                                                                     |

---

## 👥 Population & Urban Development

| Dataset                                  | Description                                               | Scope/Resolution | Used in Layers | Files                        | Source                                                                                    |
| ---------------------------------------- | --------------------------------------------------------- | ---------------- | -------------- | ---------------------------- | ----------------------------------------------------------------------------------------- |
| **GHS Population Grid (R2023)**          | Gridded population at 3 arcsecond resolution              | 3 arcsec (~100m) | Exposition     | `ClippedGHS_POP_3ss.tif`     | [Copernicus EMS](https://human-settlement.emergency.copernicus.eu/download.php?ds=pop)    |
| **GHS Built-up Characteristics (R2023)** | Structural type and height of buildings                   | Variable         | Exposition     | `GHS_BUILT_C/`               | [Copernicus EMS](https://human-settlement.emergency.copernicus.eu/download.php?ds=builtC) |
| **GHS Built-up Volume (R2023)**          | Estimated 3D volume of built structures (100m resolution) | 100m             | Exposition     | `Clipped_GHS_Built-V-100m/`  | [Copernicus EMS](https://human-settlement.emergency.copernicus.eu/download.php?ds=builtV) |
| **Degree of Urbanisation (DUC)**         | Urban/rural classification by grid cell on GADM basis     | GADM L2          | Exposition     | `degree_of_urbanisation/`    | [Copernicus EMS](https://human-settlement.emergency.copernicus.eu/download.php?ds=DUC)    |
| **GHS Land Fraction (R2022)**            | Land cover based on Sentinel-2 + OSM (10m)                | 10m              | Hazard         | `Clipped_GHS_LAND-10m_Moll/` | [Copernicus EMS](https://human-settlement.emergency.copernicus.eu/download.php?ds=land)   |

---

## 🚛 Transportation & Infrastructure

| Dataset                          | Description                              | Scope/Resolution | Used in Layers         | Files                                                              | Source                                                                                   |
| -------------------------------- | ---------------------------------------- | ---------------- | ---------------------- | ------------------------------------------------------------------ | ---------------------------------------------------------------------------------------- |
| **Freight Loading Statistics**   | Road freight loading by NUTS-3 region    | NUTS L3          | Relevance              | `road_go_loading/`, `unified_freight_data.csv`                     | [Eurostat](https://ec.europa.eu/eurostat/databrowser/view/road_go_na_rl3g/default/table) |
| **Freight Unloading Statistics** | Road freight unloading by NUTS-3 region  | NUTS L3          | Relevance              | `L3-estat_road_go_unloading/`                                      | [Eurostat](https://ec.europa.eu/eurostat/databrowser/view/road_go_na_ru3g/default/table) |
| **European Ports**               | Location and attributes of major ports   | Point data       | Exposition & Relevance | `Port/PORT_RG_2025_Updated.shp`                                    | [Eurostat GISCO](https://ec.europa.eu/eurostat/web/gisco/geodata/transport-networks)     |
| **Zeevaart Maritime Data**       | Dutch port freight statistics (enhanced) | Per Port         | Relevance              | `Port/Zeevaart__gewicht__haven__soort_lading_19062025_160850.xlsx` | [CBS](https://opendata.cbs.nl/#/CBS/nl/dataset/82850NED/table)                           |

---

## 🌍 Physical Geography & Environment

| Dataset                | Description                                   | Scope/Resolution | Used in Layers | Files                                | Source                                                                                                               |
| ---------------------- | --------------------------------------------- | ---------------- | -------------- | ------------------------------------ | -------------------------------------------------------------------------------------------------------------------- |
| **Copernicus DEM**     | High-resolution elevation model               | ~30m             | Hazard         | `ClippedCopernicusHeightProfile.tif` | [Eurostat GISCO](https://ec.europa.eu/eurostat/web/gisco/geodata/digital-elevation-model/copernicus)                 |
| **European Coastline** | Coastal geometry for flood exposure modelling | Vector polylines | Hazard         | `EEA_Coastline_Polyline_Shape/`      | [EEA](https://www.eea.europa.eu/data-and-maps/data/eea-coastline-for-analysis-1/gis-data/europe-coastline-shapefile) |
| **Dutch Hydrography**  | Dutch river networks and water bodies         | Vector polygons  | Hazard         | `Hydrographie-Watercourse/`          | [PDOK](https://www.pdok.nl/introductie/-/article/hydrografie-inspire-geharmoniseerd-)                                |

---

## 🌊 Flood Risk

| Dataset                    | Description                                       | Scope/Resolution | Used in Layers | Files          | Source                                                                                                                                                                |
| -------------------------- | ------------------------------------------------- | ---------------- | -------------- | -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Dutch Flood Risk Zones** | Zones under flood risk as per EU Floods Directive | Vector polygons  | Hazard         | `NL_Riskzone/` | [PDOK](https://www.pdok.nl/introductie/-/article/gebieden-met-natuurrisico-s-overstromingen-risicogebied-richtlijn-overstromingsrisico-s-ror-inspire-geharmoniseerd-) |

---

## 💼 Socioeconomic Data

| Dataset                          | Description                                         | Scope/Resolution | Used in Layers | Files                                      | Source                                                                                         |
| -------------------------------- | --------------------------------------------------- | ---------------- | -------------- | ------------------------------------------ | ---------------------------------------------------------------------------------------------- |
| **GDP Statistics (NUTS-3)**      | Regional GDP by administrative region               | NUTS L3          | Relevance      | `L3-estat_gdp.csv`                         | [Eurostat](https://ec.europa.eu/eurostat/databrowser/view/nama_10r_3gdp/default/table)         |
| **Electricity Consumption Grid** | Global 1 km² grid electricity estimates (1992–2019) | 1 km             | Relevance      | `Electricity/Electricity.vrt`              | [Figshare](https://figshare.com/articles/dataset/17004523)                                     |
| **Vierkantstatistieken (100m)**  | Dutch socio-demographic grid at 100m resolution     | 100m             | Relevance      | `Vierkantstatistieken/cbs_vk100_2023.gpkg` | [PDOK](https://service.pdok.nl/cbs/vierkantstatistieken100m/atom/vierkantstatistieken100m.xml) |
| **HRST Statistics**              | Human capital in science and technology sectors     | NUTS L2          | Relevance      | `L2_estat_hrst_st_rcat_filtered_en/`       | [Eurostat](https://ec.europa.eu/eurostat/databrowser/view/hrst_st_rcat/default/table)          |

## 🔬 Technical Details

### Risk Assessment Methodology

The framework implements a four-layer approach following established climate risk assessment principles:

1. **Hazard Layer**: Quantifies physical climate hazards (sea level rise, coastal proximity, elevation)
2. **Exposition Layer**: Measures assets and population exposed to hazards (buildings, infrastructure, people)
3. **Relevance Layer**: Assesses economic and social importance of exposed assets (GDP, freight, human capital)
4. **Risk Layer**: Integrates all factors using weighted algorithms to produce final risk scores

### Data Processing Pipeline

**Coordinate System Standardization**:

- All data reprojected to EPSG:3035 (ETRS89-extended / LAEA Europe)
- Consistent 30m resolution grid for all raster outputs
- Bilinear resampling for continuous data, nearest neighbor for categorical

**Normalization Strategy**:

- Min-max normalization for individual indicators
- Quantile-based normalization for heavy-tailed distributions
- Mass-conserving normalization for economic indicators
- Weighted aggregation using configurable importance weights

**Quality Assurance**:

- Automated data integrity checks
- Consistent coordinate reference systems
- Standardized no-data handling
- Comprehensive logging and error reporting

### Web Export Optimization

**Cloud-Optimized GeoTIFF (COG)**:

- Internal tiling (512x512 pixel tiles)
- Multiple overview levels for efficient zooming
- LZW compression with horizontal predictor
- Optimized for HTTP range requests

**Mapbox Vector Tiles (MVT)**:

- Zoom-dependent simplification using Douglas-Peucker algorithm
- Topology preservation for accurate boundaries
- Attribute filtering to reduce file size
- Optimized for modern web mapping libraries

### Performance Characteristics

**Processing Speed**:

- Full Netherlands analysis: ~60-120 minutes (depending on hardware)
- Individual layers: ~5-15 minutes each
- Web conversion: ~10-20 minutes for complete dataset
- Clustering analysis: ~15-30 minutes per scenario

**Memory Usage**:

- Peak memory: ~16-32 GB RAM for full analysis
- Streaming I/O for large rasters to minimize memory footprint
- Automatic garbage collection and memory optimization

## 🎯 Quick Reference

**Most Common Commands**:

```bash
# Complete analysis with web exports
python -m eu_climate.main

# Risk assessment only
python -m eu_climate.main --risk

# Freight analysis with enhanced maritime data
python -m eu_climate.main --freight-only

# Convert existing outputs to web formats
python -m eu_climate.main --web-conversion
```

**Output Locations**:

- Standard formats: `eu_climate/data/output/*/tif/` and `*/gpkg/`
- Web formats: `eu_climate/data/output/*/web/cog/` and `*/web/mvt/`

**Web Export Support**:

- **Full support**: WSL (Windows), Linux, macOS
- **Limited support**: Native Windows (COG only, no tippecanoe)

**Configuration**: `eu_climate/config/config.yaml`  
**Logs**: `eu_climate/debug/risk_assessment.log`  
**Data Repository**: [Hugging Face Dataset](https://huggingface.co/datasets/TjarkGerken/eu-data)

For technical support and detailed implementation information, refer to individual module docstrings and the configuration files.
