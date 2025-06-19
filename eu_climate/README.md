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
| **Dutch Hydrography**  | Dutch river networks and water bodies         | Vector polygons  | Hazard         | `Hydrographie-Watercourse/`          | [PDOK](https://service.pdok.nl/kadaster/hy/atom/v1_0/hydrographie.xml)                                               |

---

## 🌊 Flood Risk

| Dataset                    | Description                                       | Scope/Resolution | Used in Layers | Files          | Source                                                                |
| -------------------------- | ------------------------------------------------- | ---------------- | -------------- | -------------- | --------------------------------------------------------------------- |
| **Dutch Flood Risk Zones** | Zones under flood risk as per EU Floods Directive | Vector polygons  | Hazard         | `NL_Riskzone/` | [PDOK](https://service.pdok.nl/rws/overstromingen-risicogebied/atom/) |

---

## 💶 Socioeconomic Data

| Dataset                          | Description                                         | Scope/Resolution | Used in Layers        | Files                                | Source                                                                                         |
| -------------------------------- | --------------------------------------------------- | ---------------- | --------------------- | ------------------------------------ | ---------------------------------------------------------------------------------------------- |
| **GDP Statistics (NUTS-3)**      | Regional GDP by administrative region               | NUTS L3          | Relevance             | `L3-estat_gdp.csv/`                  | —                                                                                              |
| **Electricity Consumption Grid** | 1 km² global grid electricity estimates (1992–2019) | 1 km             | Exposition, Relevance | `Electricity/Electricity.0.tif`      | [Figshare](https://figshare.com/articles/dataset/17004523)                                     |
| **Vierkantstatistieken (100m)**  | Dutch socio-demographic grid at 100m                | 100m             | Exposition            | `Vierkantstatistieken/`              | [PDOK](https://service.pdok.nl/cbs/vierkantstatistieken100m/atom/vierkantstatistieken100m.xml) |
| **HRST Statistics**              | Human capital in science and tech sectors           | NUTS L2          | Relevance             | `L2_estat_hrst_st_rcat_filtered_en/` | [Eurostat](https://ec.europa.eu/eurostat/databrowser/view/hrst_st_rcat/default/table)          |
