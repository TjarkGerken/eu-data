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

# Datasets

What data is used:

Degree of Urbanisation https://human-settlement.emergency.copernicus.eu/download.php?ds=DUC
GADM Shapefiles: https://gadm.org/download_world.html
HRSThttps://ec.europa.eu/eurostat/databrowser/view/hrst_st_rcat/default/table?lang=en

Freight Loading: https://ec.europa.eu/eurostat/databrowser/view/road_go_na_rl3g/default/table?lang=en&category=reg.reg_tran.reg_road
Freight Unloading: https://ec.europa.eu/eurostat/databrowser/view/road_go_na_ru3g/default/table?lang=en&category=reg.reg_tran.reg_road
GHS built-up volume (R2023): https://human-settlement.emergency.copernicus.eu/download.php?ds=builtV
Land fraction per pixel as derived from Sentinel2 data composite and OpenStreetMap (OSM) data. (R2022): https://human-settlement.emergency.copernicus.eu/download.php?ds=land
GHS built-up characteristics (R2023) https://human-settlement.emergency.copernicus.eu/download.php?ds=builtC
GHS Popuation: https://human-settlement.emergency.copernicus.eu/download.php?ds=pop
NUTS L0-L3: https://ec.europa.eu/eurostat/web/gisco/geodata/statistical-units/territorial-units-statistics
Copernicus DEM: https://ec.europa.eu/eurostat/web/gisco/geodata/digital-elevation-model/copernicus
Ports: https://ec.europa.eu/eurostat/web/gisco/geodata/transport-networks und selberweiterverarbeitet
European Coastline: https://www.eea.europa.eu/data-and-maps/data/eea-coastline-for-analysis-1/gis-data/europe-coastline-shapefile

Gebieden met Natuurrisico's - Overstromingen - Risicogebied - Richtlijn Overstromingsrisico's (ROR) (INSPIRE geharmoniseerd): https://service.pdok.nl/rws/overstromingen-risicogebied/atom/gebieden_met_natuurrisicos_overstromingen_risicogebied_richtlijn_overstromingsrisicos_ror_inspire_geharmoniseerd.xml

Data Feed - Hydrografie EPSG:4258 (GML): https://service.pdok.nl/kadaster/hy/atom/v1_0/hydrografie.xml
Vierkantstatistieken 100m 2023: https://service.pdok.nl/cbs/vierkantstatistieken100m/atom/vierkantstatistieken100m.xml (cbs_vk100_2023.gpkg)

Electricity Consumption: https://figshare.com/articles/dataset/Global_1_km_1_km_gridded_revised_real_gross_domestic_product_and_electricity_consumption_during_1992-2019_based_on_calibrated_nighttime_light_data/17004523/1