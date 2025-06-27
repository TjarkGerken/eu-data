# EU Climate Risk Assessment Framework

A comprehensive framework for climate risk analysis with modern web-compatible data exports.

## 📋 Table of Contents

1. [🚀 Quick Start](#-quick-start)
2. [💻 Environment Setup](#-environment-setup)
3. [🌐 Web Export System](#-web-export-system)
4. [🔧 Running the Analysis](#-running-the-analysis)
5. [📊 Output Formats](#-output-formats)
6. [🛠️ Advanced Usage](#️-advanced-usage)
7. [📁 Project Structure](#-project-structure)

## 🚀 Quick Start

### For Windows Users (Recommended: WSL Setup)

**Best Performance with Full Web Export Support:**

1. **Install WSL and set up the environment:**
```powershell
# Install WSL (if not already installed)
wsl --install

# Run the setup (one-time only)
.\run_in_wsl.ps1 setup
```

2. **Run the analysis:**
```powershell
# Run complete analysis with web exports
.\run_in_wsl.ps1 main

# Run web export demo
.\run_in_wsl.ps1 demo

# Open WSL shell for development
.\run_in_wsl.ps1 shell
```

### For Windows Users (Alternative: Native Setup)

**Limited web export support but simpler setup:**

```powershell
# Create conda environment
conda create -n eu-climate python=3.11 gdal rasterio geopandas -c conda-forge -y
conda activate eu-climate
pip install -r requirements.txt

# Run analysis
python eu_climate/main.py
```

### For Linux/macOS Users

```bash
# Create virtual environment
python3 -m venv ./.venv
source ./.venv/bin/activate
pip install -r requirements.txt

# Install web export dependencies
sudo apt install tippecanoe  # Ubuntu/Debian
# or brew install tippecanoe  # macOS

# Run analysis
python -m eu_climate.main
```

## 💻 Environment Setup

### Prerequisites

- **Storage**: At least 20 GB of free disk space
- **Memory**: Minimum 16 GB RAM
- **Python**: 3.11+ (Python 3.11 recommended for geospatial dependencies)

### Option 1: WSL Setup (Windows - Recommended)

**Advantages:**
- ✅ Full web export support (COG + MVT)
- ✅ Best performance for geospatial processing
- ✅ Native Linux tooling (tippecanoe, GDAL)
- ✅ No Windows DLL issues

**Setup:**

1. **Install WSL:**
```powershell
wsl --install
```

2. **Use the provided runner script:**
```powershell
# The script handles everything automatically
.\run_in_wsl.ps1 demo  # Test the setup
```

**What the WSL setup includes:**
- Ubuntu environment with Python 3.12
- Complete geospatial stack (GDAL, Rasterio, GeoPandas)
- Tippecanoe for optimal MVT generation
- Rio-cogeo for professional COG creation

### Option 2: Native Windows Setup

**Advantages:**
- ✅ Simpler setup
- ✅ No WSL required

**Limitations:**
- ❌ Limited web export support (COG only, no tippecanoe)
- ❌ Potential GDAL DLL issues

**Setup:**

1. **Install Anaconda/Miniconda:**
   - Download from: https://www.anaconda.com/download
   - ✅ **IMPORTANT**: Check "Add to PATH environment variable"

2. **Create Environment:**
```powershell
conda create -n eu-climate python=3.11 gdal rasterio geopandas numpy pandas matplotlib scipy pyyaml -c conda-forge -y
conda activate eu-climate
pip install -r requirements.txt
```

3. **Run Analysis:**
```powershell
python eu_climate/main.py
```

### Option 3: Linux/macOS Setup

**Full feature support with native performance:**

```bash
# Create virtual environment
python3 -m venv ./.venv
source ./.venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Install system dependencies
# Ubuntu/Debian:
sudo apt update
sudo apt install gdal-bin libgdal-dev tippecanoe

# macOS:
brew install gdal tippecanoe

# Verify installation
python -c "import rasterio, geopandas; print('✅ All dependencies working!')"
```

### Data Setup

The system uses data hosted on Hugging Face with automatic download:

1. **Configure Hugging Face token:**
```bash
cd eu_climate/config
cp .template.env .env
# Edit .env and add your HF token: HF_API_TOKEN=hf_XXXX
```

2. **Get token:** https://huggingface.co/settings/tokens (write access required)

3. **Manual download alternative:** https://huggingface.co/datasets/TjarkGerken/eu-data

## 🌐 Web Export System

The framework automatically generates web-optimized formats alongside traditional analysis outputs.

### Supported Formats

#### Cloud-Optimized GeoTIFF (COG)
- **Purpose**: Efficient web delivery of raster data
- **Features**: 
  - HTTP range request support
  - LZW compression
  - Automatic overview pyramids
  - 512×512 pixel tiles
- **Use Cases**: Web mapping, progressive loading, mobile apps

#### Mapbox Vector Tiles (MVT)
- **Purpose**: Efficient web delivery of vector data
- **Features**:
  - MBTiles format (SQLite database)
  - Multiple zoom levels (0-12)
  - Binary compression
  - Optimized for web rendering
- **Use Cases**: Interactive maps, clustering visualization, responsive design

### Web Export Dependencies

| Platform | COG Support | MVT Support | Setup |
|----------|-------------|-------------|-------|
| **WSL (Windows)** | ✅ Full | ✅ Full | Automatic via `run_in_wsl.ps1` |
| **Native Windows** | ✅ Full | ⚠️ Python fallback | Conda setup |
| **Linux/macOS** | ✅ Full | ✅ Full | Install tippecanoe |

### Testing Web Exports

```bash
# WSL (Windows)
.\run_in_wsl.ps1 demo

# Native Windows
python eu_climate/scripts/demo_web_exports.py

# Linux/macOS
python -m eu_climate.scripts.demo_web_exports
```

## 🔧 Running the Analysis

### Basic Usage

```bash
# Complete analysis (all layers)
python -m eu_climate.main

# Or using WSL runner (Windows)
.\run_in_wsl.ps1 main
```

### Layer-Specific Analysis

```bash
# Individual layers
python -m eu_climate.main --hazard
python -m eu_climate.main --exposition  
python -m eu_climate.main --relevance
python -m eu_climate.main --risk

# Multiple layers
python -m eu_climate.main --hazard --exposition
```

### Advanced Options

```bash
# Verbose logging
python -m eu_climate.main --verbose

# Disable caching
python -m eu_climate.main --no-cache

# Skip data upload
python -m eu_climate.main --no-upload

# Combined options
python -m eu_climate.main --verbose --no-cache --risk
```

### WSL-Specific Commands

```powershell
# Run analysis in WSL
.\run_in_wsl.ps1 main

# Test setup
.\run_in_wsl.ps1 test

# Open development shell
.\run_in_wsl.ps1 shell

# Run demo
.\run_in_wsl.ps1 demo
```

## 📊 Output Formats

### Directory Structure

```
eu_climate/data/.output/
├── hazard/
│   ├── tif/                    # Traditional GeoTIFF files
│   └── web/cog/               # Cloud-Optimized GeoTIFF files
├── exposition/
│   ├── tif/                    # Traditional GeoTIFF files  
│   └── web/cog/               # Cloud-Optimized GeoTIFF files
├── relevance/
│   ├── tif/                    # Traditional GeoTIFF files
│   └── web/cog/               # Cloud-Optimized GeoTIFF files
├── risk/
│   └── SLR-{scenario}/
│       ├── tif/               # Traditional GeoTIFF files
│       └── web/cog/           # Cloud-Optimized GeoTIFF files
└── clusters/
    └── SLR-{scenario}/
        ├── gpkg/              # Traditional GeoPackage files
        └── web/mvt/           # Mapbox Vector Tiles
```

### File Naming Convention

**Traditional Formats:**
- `{layer}_{scenario}_{type}.tif` - Raster analysis files
- `clusters_{scenario}_{type}.gpkg` - Vector cluster files

**Web-Optimized Formats:**
- `{layer}_{scenario}_{type}_cog.tif` - Cloud-Optimized GeoTIFF
- `clusters_{scenario}_{type}.mbtiles` - Mapbox Vector Tiles

### Scenarios

- `SLR-0-Current` - Current sea level conditions
- `SLR-1-Conservative` - Conservative sea level rise scenario
- `SLR-2-Moderate` - Moderate sea level rise scenario  
- `SLR-3-Severe` - Severe sea level rise scenario

### Risk Types

- `COMBINED` - Overall combined risk assessment
- `POPULATION` - Population-based risk
- `GDP` - Economic (GDP) risk
- `FREIGHT` - Freight transport risk
- `HRST` - Human resources in science & technology risk

## 🛠️ Advanced Usage

### Custom Web Export

```python
from eu_climate.utils.web_exports import WebOptimizedExporter

# Initialize exporter
exporter = WebOptimizedExporter()

# Export raster to COG
exporter.export_raster_as_cog(
    input_path="data/input.tif",
    output_path="data/output_cog.tif",
    add_overviews=True
)

# Export vector to MVT
exporter.export_vector_as_mvt(
    input_path="data/input.gpkg", 
    output_path="data/output.mbtiles",
    min_zoom=0,
    max_zoom=12
)
```

### Configuration

Edit `eu_climate/config/config.yaml` to customize:

```yaml
web_export:
  cog_profile: "lzw"           # COG compression profile
  mvt_max_zoom: 12             # Maximum zoom level for MVT
  mvt_simplification: "drop-densest-as-needed"
```

### Development Setup

```bash
# WSL development environment
.\run_in_wsl.ps1 shell

# Install additional dev dependencies
pip install jupyter jupyterlab black flake8

# Launch Jupyter Lab
jupyter lab
```

### Troubleshooting

**Common Issues:**

1. **GDAL DLL errors (Windows):**
   - Solution: Use WSL setup instead of native Windows

2. **Tippecanoe not found:**
   - Linux: `sudo apt install tippecanoe`
   - macOS: `brew install tippecanoe`
   - Windows: Use WSL or accept Python fallback

3. **Memory issues:**
   - Increase system RAM or reduce processing area
   - Use `--no-cache` flag to reduce memory usage

4. **Permission errors (WSL):**
   - Ensure files are accessible from WSL: `/mnt/c/...`

## 📁 Project Structure

```
eu_climate/
├── config/                    # Configuration files
│   ├── config.py             # Main configuration class
│   ├── config.yaml           # YAML configuration
│   └── .env                  # Environment variables (create from template)
├── risk_layers/              # Risk analysis modules
│   ├── hazard_layer.py       # Hazard layer processing
│   ├── exposition_layer.py   # Exposition layer processing
│   ├── relevance_layer.py    # Relevance layer processing
│   ├── cluster_layer.py      # Clustering analysis
│   └── economic_impact_analyzer.py  # Economic impact analysis
├── utils/                    # Utility modules
│   ├── web_exports.py        # Web export functionality
│   ├── cache_manager.py      # Data caching
│   ├── data_loader.py        # Data loading utilities
│   └── visualization.py     # Visualization tools
├── scripts/                  # Utility scripts
│   ├── demo_web_exports.py   # Web export demonstration
│   └── cache_manager_cli.py  # Cache management CLI
├── data/                     # Data directory (synced with HuggingFace)
│   ├── source/               # Input data
│   └── .output/              # Generated outputs
├── debug/                    # Log files
├── main.py                   # Main execution script
└── README.md                 # This documentation
```

### Key Components

- **WebOptimizedExporter**: Handles COG and MVT generation
- **ProjectConfig**: Centralized configuration management
- **Cache Manager**: Intelligent data caching system
- **Risk Layers**: Modular risk assessment components

---

## 🎯 Quick Reference

**Most Common Commands:**

```bash
# Windows (WSL) - Recommended
.\run_in_wsl.ps1 main          # Run complete analysis
.\run_in_wsl.ps1 demo          # Test web exports

# Any platform
python -m eu_climate.main      # Run complete analysis
python -m eu_climate.main --risk  # Run only risk assessment
```

**Output Locations:**
- Traditional formats: `eu_climate/data/.output/*/tif/` and `*/gpkg/`
- Web formats: `eu_climate/data/.output/*/web/cog/` and `*/web/mvt/`

**Web Export Support:**
- **Full support**: WSL (Windows), Linux, macOS
- **Limited support**: Native Windows (COG only)

For detailed technical documentation, see individual module docstrings and the configuration files.


## Quick Start

### Requirements

- Python 3.12
- At least 20 GB of free disk space
- Minimum 16 GB RAM

The dataset required to run the case study for the Netherlands is hosted on Hugging Face. By default, the system automatically downloads the necessary data. Manual download is also supported.

### Auto-Download Setup

1. Copy the environment template and configure your Hugging Face token:

   ```bash
   cd eu_climate/config
   cp .template.env .env
   ```

2. Create a token with **at least write access** at:  
   https://huggingface.co/settings/tokens

3. Paste the token into your `.env` file:

   ```env
   HF_API_TOKEN=hf_XXXX
   ```

### Manual Download

1. Visit: https://huggingface.co/datasets/TjarkGerken/eu-data
2. Download and extract the repository
3. Ensure the contents are placed in: `eu_climate/data/source`
4. Update paths in `eu_climate/config/config.yaml` if needed:

   ```yaml
   data:
     data_paths:
       local_data_dir: "data"
       source_data_dir: "source"
       local_output_dir: ".output"
   ```

### Starting the Program

```bash
python3 -m venv ./.venv
source ./.venv/bin/activate
pip install -r requirements.txt
python -m eu_climate.main
```

### Execution Commands

```bash
  python -m main --hazard                    # Run only hazard layer analysis
  python -m main --exposition                # Run only exposition layer analysis
  python -m main --relevance                 # Run only relevance layer analysis
  python -m main --risk                      # Run only risk layer analysis
  python -m main --hazard --exposition       # Run hazard and exposition layers
  python -m main --all                       # Run all layers (default behavior)
  python -m main --verbose --risk            # Run risk layer with verbose logging
  python -m main --no-cache --hazard         # Run hazard layer without caching
  python -m main --no-upload --all           # Run all layers without data upload
```

# 📦 Datasets Overview

This section outlines all geospatial and statistical datasets used for the case study on climate risk in the Netherlands. Each dataset is grouped by thematic domain and includes source links and file structure.

---

## 🗺️ Administrative Boundaries

| Dataset                           | Description                                              | Scope/Resolution | Used in Layers  | Files                                   | Source                                                                                                     |
| --------------------------------- | -------------------------------------------------------- | ---------------- | --------------- | --------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| **NUTS Levels 0–3 (Netherlands)** | European statistical units for regional analysis (L0–L3) | NUTS L0-L3       | Relevance, Risk | `NUTS-L0-NL.shp`, ..., `NUTS-L3-NL.shp` | [Eurostat](https://ec.europa.eu/eurostat/web/gisco/geodata/statistical-units/territorial-units-statistics) |
| **GADM Shapefiles (NL, L2)**      | Administrative boundary fallback dataset                 | GADM L2          | Relevance       | `NL-GADM-L2/`                           | [GADM](https://gadm.org/download_world.html)                                                               |

---

## 👥 Population & Urban Development

| Dataset                                  | Description                                               | Scope/Resolution | Used in Layers | Files                        | Source                                                                                    |
| ---------------------------------------- | --------------------------------------------------------- | ---------------- | -------------- | ---------------------------- | ----------------------------------------------------------------------------------------- |
| **GHS Population Grid (R2023)**          | Gridded population at 3 arcsecond resolution              | 3 arcsec (~100m) | Exposition     | `ClippedGHS_POP_3ss.tif`     | [Copernicus EMS](https://human-settlement.emergency.copernicus.eu/download.php?ds=pop)    |
| **GHS Built-up Characteristics (R2023)** | Structural type and height of buildings                   | NaN              | Exposition     | `GHS_BUILT_C/`               | [Copernicus EMS](https://human-settlement.emergency.copernicus.eu/download.php?ds=builtC) |
| **GHS Built-up Volume (R2023)**          | Estimated 3D volume of built structures (100m resolution) | 100m             | Exposition     | `Clipped_GHS_Built-V-100m/`  | [Copernicus EMS](https://human-settlement.emergency.copernicus.eu/download.php?ds=builtV) |
| **Degree of Urbanisation (DUC)**         | Urban/rural classification by grid cell on GADM basis     | GADM L2          | Exposition     | `degree_of_urbanisation/`    | [Copernicus EMS](https://human-settlement.emergency.copernicus.eu/download.php?ds=DUC)    |
| **GHS Land Fraction (R2022)**            | Land cover based on Sentinel-2 + OSM (10m)                | 10m              | Hazard         | `Clipped_GHS_LAND-10m_Moll/` | [Copernicus EMS](https://human-settlement.emergency.copernicus.eu/download.php?ds=land)   |

---

## 🚛 Transportation & Infrastructure

| Dataset                          | Description                       | Scope/Resolution | Used in Layers         | Files                                          | Source                                                                                   |
| -------------------------------- | --------------------------------- | ---------------- | ---------------------- | ---------------------------------------------- | ---------------------------------------------------------------------------------------- |
| **Freight Loading Statistics**   | Road freight loading by NUTS-3    | NUTS L3          | Relevance              | `road_go_loading/`, `unified_freight_data.csv` | [Eurostat](https://ec.europa.eu/eurostat/databrowser/view/road_go_na_rl3g/default/table) |
| **Freight Unloading Statistics** | Road freight unloading by NUTS-3  | NUTS L3          | Relevance              | `L3-estat_road_go_unloading/`                  | [Eurostat](https://ec.europa.eu/eurostat/databrowser/view/road_go_na_ru3g/default/table) |
| **European Ports**               | Location and attributes of ports  | Point data       | Exposition & Relevance | `Port/PORT_RG_2009.shp`                        | [Eurostat GISCO](https://ec.europa.eu/eurostat/web/gisco/geodata/transport-networks)     |
| **Zeevaart**               | Gross weight handled (1,000 tons) | Per Port         | Relevance              | `Port/PORT_RG_2009.shp`                        | [CBS](https://opendata.cbs.nl/#/CBS/nl/dataset/82850NED/table)                |

---

## 🌍 Physical Geography & Environment

| Dataset                | Description                                   | Scope/Resolution | Used in Layers | Files                                | Source                                                                                                               |
| ---------------------- | --------------------------------------------- | ---------------- | -------------- | ------------------------------------ | -------------------------------------------------------------------------------------------------------------------- |
| **Copernicus DEM**     | High-resolution elevation model               | ~30m             | Hazard         | `ClippedCopernicusHeightProfile.tif` | [Eurostat GISCO](https://ec.europa.eu/eurostat/web/gisco/geodata/digital-elevation-model/copernicus)                 |
| **European Coastline** | Coastal geometry for flood exposure modelling | Vector polylines | Hazard         | `EEA_Coastline_Polyline_Shape/`      | [EEA](https://www.eea.europa.eu/data-and-maps/data/eea-coastline-for-analysis-1/gis-data/europe-coastline-shapefile) |
| **Dutch Hydrography**  | Dutch river networks and water bodies         | Vector polygons  | Hazard         | `Hydrographie-Watercourse/`          | [PDOK](https://www.pdok.nl/introductie/-/article/gebieden-met-natuurrisico-s-overstromingen-risicogebied-richtlijn-overstromingsrisico-s-ror-inspire-geharmoniseerd-)                                               |

---

## 🌊 Flood Risk

| Dataset                    | Description                                       | Scope/Resolution | Used in Layers | Files          | Source                                                                |
| -------------------------- | ------------------------------------------------- | ---------------- | -------------- | -------------- | --------------------------------------------------------------------- |
| **Dutch Flood Risk Zones** | Zones under flood risk as per EU Floods Directive | Vector polygons  | Hazard         | `NL_Riskzone/` | [PDOK](## Quick Start

### Requirements

- Python 3.12
- At least 20 GB of free disk space
- Minimum 16 GB RAM

The dataset required to run the case study for the Netherlands is hosted on Hugging Face. By default, the system automatically downloads the necessary data. Manual download is also supported.

### Auto-Download Setup

1. Copy the environment template and configure your Hugging Face token:

   ```bash
   cd eu_climate/config
   cp .template.env .env
   ```

2. Create a token with **at least write access** at:  
   https://huggingface.co/settings/tokens

3. Paste the token into your `.env` file:

   ```env
   HF_API_TOKEN=hf_XXXX
   ```

### Manual Download

1. Visit: https://huggingface.co/datasets/TjarkGerken/eu-data
2. Download and extract the repository
3. Ensure the contents are placed in: `eu_climate/data/source`
4. Update paths in `eu_climate/config/config.yaml` if needed:

   ```yaml
   data:
     data_paths:
       local_data_dir: "data"
       source_data_dir: "source"
       local_output_dir: ".output"
   ```

### Starting the Program

```bash
python3 -m venv ./.venv
source ./.venv/bin/activate
pip install -r requirements.txt
python -m eu_climate.main
```

### Execution Commands

```bash
  python -m main --hazard                    # Run only hazard layer analysis
  python -m main --exposition                # Run only exposition layer analysis
  python -m main --relevance                 # Run only relevance layer analysis
  python -m main --risk                      # Run only risk layer analysis
  python -m main --hazard --exposition       # Run hazard and exposition layers
  python -m main --all                       # Run all layers (default behavior)
  python -m main --verbose --risk            # Run risk layer with verbose logging
  python -m main --no-cache --hazard         # Run hazard layer without caching
  python -m main --no-upload --all           # Run all layers without data upload
```

# 📦 Datasets Overview

This section outlines all geospatial and statistical datasets used for the case study on climate risk in the Netherlands. Each dataset is grouped by thematic domain and includes source links and file structure.

---

## 🗺️ Administrative Boundaries

| Dataset                           | Description                                              | Scope/Resolution | Used in Layers  | Files                                   | Source                                                                                                     |
| --------------------------------- | -------------------------------------------------------- | ---------------- | --------------- | --------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| **NUTS Levels 0–3 (Netherlands)** | European statistical units for regional analysis (L0–L3) | NUTS L0-L3       | Relevance, Risk | `NUTS-L0-NL.shp`, ..., `NUTS-L3-NL.shp` | [Eurostat](https://ec.europa.eu/eurostat/web/gisco/geodata/statistical-units/territorial-units-statistics) |
| **GADM Shapefiles (NL, L2)**      | Administrative boundary fallback dataset                 | GADM L2          | Relevance       | `NL-GADM-L2/`                           | [GADM](https://gadm.org/download_world.html)                                                               |

---

## 👥 Population & Urban Development

| Dataset                                  | Description                                               | Scope/Resolution | Used in Layers | Files                        | Source                                                                                    |
| ---------------------------------------- | --------------------------------------------------------- | ---------------- | -------------- | ---------------------------- | ----------------------------------------------------------------------------------------- |
| **GHS Population Grid (R2023)**          | Gridded population at 3 arcsecond resolution              | 3 arcsec (~100m) | Exposition     | `ClippedGHS_POP_3ss.tif`     | [Copernicus EMS](https://human-settlement.emergency.copernicus.eu/download.php?ds=pop)    |
| **GHS Built-up Characteristics (R2023)** | Structural type and height of buildings                   | NaN              | Exposition     | `GHS_BUILT_C/`               | [Copernicus EMS](https://human-settlement.emergency.copernicus.eu/download.php?ds=builtC) |
| **GHS Built-up Volume (R2023)**          | Estimated 3D volume of built structures (100m resolution) | 100m             | Exposition     | `Clipped_GHS_Built-V-100m/`  | [Copernicus EMS](https://human-settlement.emergency.copernicus.eu/download.php?ds=builtV) |
| **Degree of Urbanisation (DUC)**         | Urban/rural classification by grid cell on GADM basis     | GADM L2          | Exposition     | `degree_of_urbanisation/`    | [Copernicus EMS](https://human-settlement.emergency.copernicus.eu/download.php?ds=DUC)    |
| **GHS Land Fraction (R2022)**            | Land cover based on Sentinel-2 + OSM (10m)                | 10m              | Hazard         | `Clipped_GHS_LAND-10m_Moll/` | [Copernicus EMS](https://human-settlement.emergency.copernicus.eu/download.php?ds=land)   |

---

## 🚛 Transportation & Infrastructure

| Dataset                          | Description                       | Scope/Resolution | Used in Layers         | Files                                          | Source                                                                                   |
| -------------------------------- | --------------------------------- | ---------------- | ---------------------- | ---------------------------------------------- | ---------------------------------------------------------------------------------------- |
| **Freight Loading Statistics**   | Road freight loading by NUTS-3    | NUTS L3          | Relevance              | `road_go_loading/`, `unified_freight_data.csv` | [Eurostat](https://ec.europa.eu/eurostat/databrowser/view/road_go_na_rl3g/default/table) |
| **Freight Unloading Statistics** | Road freight unloading by NUTS-3  | NUTS L3          | Relevance              | `L3-estat_road_go_unloading/`                  | [Eurostat](https://ec.europa.eu/eurostat/databrowser/view/road_go_na_ru3g/default/table) |
| **European Ports**               | Location and attributes of ports  | Point data       | Exposition & Relevance | `Port/PORT_RG_2009.shp`                        | [Eurostat GISCO](https://ec.europa.eu/eurostat/web/gisco/geodata/transport-networks)     |
| **Zeevaart**               | Gross weight handled (1,000 tons) | Per Port         | Relevance              | `Port/PORT_RG_2009.shp`                        | [CBS](https://opendata.cbs.nl/#/CBS/nl/dataset/82850NED/table)                |

---

## 🌍 Physical Geography & Environment

| Dataset                | Description                                   | Scope/Resolution | Used in Layers | Files                                | Source                                                                                                               |
| ---------------------- | --------------------------------------------- | ---------------- | -------------- | ------------------------------------ | -------------------------------------------------------------------------------------------------------------------- |
| **Copernicus DEM**     | High-resolution elevation model               | ~30m             | Hazard         | `ClippedCopernicusHeightProfile.tif` | [Eurostat GISCO](https://ec.europa.eu/eurostat/web/gisco/geodata/digital-elevation-model/copernicus)                 |
| **European Coastline** | Coastal geometry for flood exposure modelling | Vector polylines | Hazard         | `EEA_Coastline_Polyline_Shape/`      | [EEA](https://www.eea.europa.eu/data-and-maps/data/eea-coastline-for-analysis-1/gis-data/europe-coastline-shapefile) |
| **Dutch Hydrography**  | Dutch river networks and water bodies         | Vector polygons  | Hazard         | `Hydrographie-Watercourse/`          | [PDOK](https://www.pdok.nl/introductie/-/article/hydrografie-inspire-geharmoniseerd-)                                               |

---

## 🌊 Flood Risk

| Dataset                    | Description                                       | Scope/Resolution | Used in Layers | Files          | Source                                                                |
| -------------------------- | ------------------------------------------------- | ---------------- | -------------- | -------------- | --------------------------------------------------------------------- |
| **Dutch Flood Risk Zones** | Zones under flood risk as per EU Floods Directive | Vector polygons  | Hazard         | `NL_Riskzone/` | [PDOK](https://www.pdok.nl/introductie/-/article/gebieden-met-natuurrisico-s-overstromingen-risicogebied-richtlijn-overstromingsrisico-s-ror-inspire-geharmoniseerd-) |

---

## 💶 Socioeconomic Data

| Dataset                          | Description                                         | Scope/Resolution | Used in Layers        | Files                                | Source                                                                                         |
| -------------------------------- | --------------------------------------------------- | ---------------- | --------------------- | ------------------------------------ | ---------------------------------------------------------------------------------------------- |
| **GDP Statistics (NUTS-3)**      | Regional GDP by administrative region               | NUTS L3          | Relevance             | `L3-estat_gdp.csv/`                  | —                                                                                              |
| **Electricity Consumption Grid** | 1 km² global grid electricity estimates (1992–2019) | 1 km             | Exposition, Relevance | `Electricity/Electricity.0.tif`      | [Figshare](https://figshare.com/articles/dataset/17004523)                                     |
| **Vierkantstatistieken (100m)**  | Dutch socio-demographic grid at 100m                | 100m             | Exposition            | `Vierkantstatistieken/`              | [PDOK](https://service.pdok.nl/cbs/vierkantstatistieken100m/atom/vierkantstatistieken100m.xml) |
| **HRST Statistics**              | Human capital in science and tech sectors           | NUTS L2          | Relevance             | `L2_estat_hrst_st_rcat_filtered_en/` | [Eurostat](https://ec.europa.eu/eurostat/databrowser/view/hrst_st_rcat/default/table)          |
) |

---

## 💶 Socioeconomic Data

| Dataset                          | Description                                         | Scope/Resolution | Used in Layers        | Files                                | Source                                                                                         |
| -------------------------------- | --------------------------------------------------- | ---------------- | --------------------- | ------------------------------------ | ---------------------------------------------------------------------------------------------- |
| **GDP Statistics (NUTS-3)**      | Regional GDP by administrative region               | NUTS L3          | Relevance             | `L3-estat_gdp.csv/`                  | —                                                                                              |
| **Electricity Consumption Grid** | 1 km² global grid electricity estimates (1992–2019) | 1 km             | Exposition, Relevance | `Electricity/Electricity.0.tif`      | [Figshare](https://figshare.com/articles/dataset/17004523)                                     |
| **Vierkantstatistieken (100m)**  | Dutch socio-demographic grid at 100m                | 100m             | Exposition            | `Vierkantstatistieken/`              | [PDOK](https://service.pdok.nl/cbs/vierkantstatistieken100m/atom/vierkantstatistieken100m.xml) |
| **HRST Statistics**              | Human capital in science and tech sectors           | NUTS L2          | Relevance             | `L2_estat_hrst_st_rcat_filtered_en/` | [Eurostat](https://ec.europa.eu/eurostat/databrowser/view/hrst_st_rcat/default/table)          |
