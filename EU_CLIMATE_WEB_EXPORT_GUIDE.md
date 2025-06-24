# EU Climate Risk Assessment Framework - Complete Guide

A comprehensive framework for climate risk analysis with modern web-compatible data exports.

## 📋 Table of Contents

1. [🚀 Quick Start](#-quick-start)
2. [💻 Environment Setup](#-environment-setup)
3. [🌐 Web Export System](#-web-export-system)
4. [🔧 Running the Analysis](#-running-the-analysis)
5. [📊 Output Formats](#-output-formats)
6. [🛠️ Advanced Usage](#️-advanced-usage)
7. [📁 Project Structure](#-project-structure)
8. [🌍 Web Deployment](#-web-deployment)

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
- **File Extension**: `.tif` (in `/web/cog/` directories)

#### Mapbox Vector Tiles (MVT)
- **Purpose**: Efficient web delivery of vector data
- **Features**:
  - MBTiles format (SQLite database)
  - Multiple zoom levels (0-12)
  - Binary compression
  - Optimized for web rendering
- **Use Cases**: Interactive maps, clustering visualization, responsive design
- **File Extension**: `.mbtiles`

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

### Example Output Files

**After running the complete analysis, you'll have:**

**COG Files (32 files total):**
```
eu_climate/data/.output/risk/SLR-0-Current/web/cog/
├── risk_SLR-0-Current_COMBINED_cog.tif    (31MB)
├── risk_SLR-0-Current_FREIGHT_cog.tif     (35MB)
├── risk_SLR-0-Current_GDP_cog.tif         (18MB)
├── risk_SLR-0-Current_HRST_cog.tif        (32MB)
└── risk_SLR-0-Current_POPULATION_cog.tif  (38MB)
```

**MVT Files (12 files total):**
```
eu_climate/data/.output/clusters/SLR-0-Current/web/mvt/
├── clusters_SLR-0-Current_FREIGHT.mbtiles     (32KB)
├── clusters_SLR-0-Current_GDP.mbtiles         (32KB)
└── clusters_SLR-0-Current_POPULATION.mbtiles  (32KB)
```

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

Available COG profiles: `lzw`, `deflate`, `zstd`, `jpeg`, `webp`

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

5. **Web export warnings:**
   - COG warnings about OVERVIEW_LEVELS are normal and don't affect functionality

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
│   ├── web_exports.py        # Web export functionality ⭐
│   ├── web_export_mixin.py   # Mixin for easy integration
│   ├── cache_manager.py      # Data caching
│   ├── data_loader.py        # Data loading utilities
│   └── visualization.py     # Visualization tools
├── scripts/                  # Utility scripts
│   ├── demo_web_exports.py   # Web export demonstration ⭐
│   └── cache_manager_cli.py  # Cache management CLI
├── data/                     # Data directory (synced with HuggingFace)
│   ├── source/               # Input data
│   └── .output/              # Generated outputs
│       ├── */tif/            # Traditional raster outputs
│       ├── */web/cog/        # Web-optimized raster outputs ⭐
│       ├── */gpkg/           # Traditional vector outputs
│       └── */web/mvt/        # Web-optimized vector outputs ⭐
├── debug/                    # Log files
├── main.py                   # Main execution script
├── run_eu_climate.py         # WSL-compatible runner ⭐
├── run_in_wsl.ps1           # PowerShell WSL runner ⭐
└── README.md                 # Documentation
```

### Key Components

- **WebOptimizedExporter**: Handles COG and MVT generation
- **WebExportMixin**: Easy integration into existing layer classes
- **ProjectConfig**: Centralized configuration management
- **Cache Manager**: Intelligent data caching system
- **Risk Layers**: Modular risk assessment components

## 🌍 Web Deployment

### Using COG Files in Web Applications

**Leaflet Example:**
```javascript
// Add COG layer using georaster-layer-for-leaflet
fetch('path/to/risk_SLR-0-Current_COMBINED_cog.tif')
  .then(response => response.arrayBuffer())
  .then(arrayBuffer => {
    parseGeoraster(arrayBuffer).then(georaster => {
      const layer = new GeoRasterLayer({
        georaster: georaster,
        opacity: 0.7
      });
      layer.addTo(map);
    });
  });
```

**OpenLayers Example:**
```javascript
// Add COG layer using ol-source-raster
import GeoTIFF from 'ol/source/GeoTIFF';

const source = new GeoTIFF({
  sources: [{
    url: 'path/to/risk_SLR-0-Current_COMBINED_cog.tif'
  }]
});

const layer = new TileLayer({ source });
map.addLayer(layer);
```

### Using MVT Files in Web Applications

**Mapbox GL JS Example:**
```javascript
map.addSource('clusters', {
  'type': 'vector',
  'url': 'mbtiles://path/to/clusters_SLR-0-Current_POPULATION.mbtiles'
});

map.addLayer({
  'id': 'cluster-layer',
  'type': 'circle',
  'source': 'clusters',
  'paint': {
    'circle-radius': 6,
    'circle-color': '#ff0000'
  }
});
```

**Leaflet with Mapbox Vector Tiles:**
```javascript
// Using leaflet-vector-tile-layer
const vectorTileLayer = L.vectorTileLayer(
  'path/to/clusters_SLR-0-Current_POPULATION.mbtiles/{z}/{x}/{y}.pbf'
).addTo(map);
```

### Performance Benefits

**COG Benefits:**
- **HTTP Range Requests**: Only download needed portions
- **Progressive Loading**: Show low-res first, enhance with detail
- **Caching**: Efficient browser and CDN caching
- **Mobile Optimized**: Reduced bandwidth usage

**MVT Benefits:**
- **Vector Rendering**: Smooth zooming and styling
- **Interactive Features**: Click events and popups
- **Small File Sizes**: 32-40KB vs 324KB+ for GPKG
- **Responsive Design**: Adapts to different screen sizes

### Deployment Options

1. **Static File Server**: Host files directly (Apache, Nginx, S3)
2. **CDN Deployment**: Use CloudFront, CloudFlare for global delivery
3. **Tile Server**: Use TileServer GL for dynamic serving
4. **Database Integration**: Import MVT into PostGIS for complex queries

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

**File Counts After Complete Analysis:**
- COG files: 20 (4 scenarios × 5 risk types)
- MVT files: 12 (4 scenarios × 3 cluster types)
- Total web files: 32

**Performance Stats:**
- COG creation: ~4-6 seconds per file
- MVT creation: ~0.2-0.4 seconds per file
- Total web export time: ~2-3 minutes for all files

For detailed technical documentation, see individual module docstrings and the configuration files. 