# Economic Impact Analysis Guide

## Overview

The Economic Impact Analysis module calculates the absolute values of economic indicators (GDP, Freight, Population/HRST) that are at risk from flooding under different sea level rise scenarios. It combines results from the absolute relevance layers with hazard assessments to provide quantitative risk analysis.

## Key Features

- **Sequential Processing**: Processes scenarios one at a time (compute → plot → save → next) for memory efficiency
- **Flood Risk Threshold**: Uses configurable `max_safe_flood_risk` threshold from config.yaml (currently 0.3)
- **Stacked Bar Visualizations**: Creates charts showing total vs at-risk amounts with:
  - Light grey: Safe portion (100% - risk%)
  - Red: At-risk portion 
  - Value annotations within bars
  - Shared percentage scale (0-100%)
- **Multiple Output Formats**: Generates both PNG visualizations and CSV data files

## Prerequisites

Before running the economic impact analysis, ensure you have:

1. **Absolute Relevance Layers** generated in `data/output/relevance_absolute/tif/`:
   - `absolute_relevance_gdp.tif`
   - `absolute_relevance_freight.tif`
   - `absolute_relevance_hrst.tif`

2. **Hazard Scenario Layers** generated in `data/output/hazard/tif/`:
   - `flood_risk_current.tif`
   - `flood_risk_conservative.tif`
   - `flood_risk_moderate.tif`
   - `flood_risk_severe.tif`

## Usage

### Option 1: Using the Demo Script (Recommended)

```bash
cd eu_climate/scripts
python demo_economic_impact.py
```

### Option 2: Programmatic Usage

```python
from eu_climate.config.config import ProjectConfig
from eu_climate.risk_layers.economic_impact_analyzer import EconomicImpactAnalyzer

# Initialize configuration
config = ProjectConfig()

# Create analyzer
analyzer = EconomicImpactAnalyzer(config)

# Run analysis for all scenarios
results = analyzer.run_economic_impact_analysis()

# Results structure:
# results[scenario_name][indicator][metric]
# Where:
# - scenario_name: 'Current', 'Conservative', 'Moderate', 'Severe'
# - indicator: 'gdp', 'freight', 'hrst'
# - metric: 'total_value', 'at_risk_value', 'safe_value', 'risk_percentage', 'safe_percentage'
```

### Option 3: Custom Scenarios

```python
# Define custom scenarios
custom_scenarios = [
    ('Custom_Low', 0.5),    # 0.5m sea level rise
    ('Custom_High', 4.0),   # 4.0m sea level rise
]

# Run with custom scenarios
results = analyzer.run_economic_impact_analysis(scenarios=custom_scenarios)
```

## Output Structure

The analysis creates the following output structure:

```
data/output/economic_impact/
├── current/
│   ├── economic_impact_current.png      # Visualization
│   └── impact_data_current.csv          # Data
├── conservative/
│   ├── economic_impact_conservative.png
│   └── impact_data_conservative.csv
├── moderate/
│   ├── economic_impact_moderate.png
│   └── impact_data_moderate.csv
├── severe/
│   ├── economic_impact_severe.png
│   └── impact_data_severe.csv
└── summary/
    └── economic_impact_summary.csv      # Combined results
```

## Visualization Details

Each scenario generates a horizontal stacked bar chart with:

- **3 bars**: One for each indicator (GDP, Freight, Population/HRST)
- **2 colors per bar**:
  - Light grey: Safe from flooding (percentage + absolute value)
  - Red: At risk from flooding (percentage + absolute value)
- **Value formatting**:
  - GDP: Billions of Euros (e.g., "145.2B €")
  - Freight: Million tonnes (e.g., "23.5M t")
  - Population (HRST): Thousands of persons (e.g., "89K persons")

## Configuration

Key configuration parameters in `config.yaml`:

```yaml
hazard:
  flood_risk:
    max_safe_flood_risk: 0.3  # Threshold for defining "at risk" areas
```

## Data Processing Method

1. **Load Data**: Absolute relevance layers and hazard scenario data
2. **Create Risk Mask**: Binary mask where `hazard_risk > max_safe_flood_risk`
3. **Calculate Totals**: Sum all valid pixels in Netherlands for each indicator
4. **Calculate At-Risk**: Sum pixels that meet both valid + risk mask criteria
5. **Compute Percentages**: Calculate risk/safe percentages for visualization
6. **Generate Outputs**: Create visualizations and save data files

## Indicators Explanation

- **GDP**: Gross Domestic Product distributed spatially based on economic exposition
- **Freight**: Combined freight volumes (loading, unloading, maritime) with port enhancements
- **Population (HRST)**: Human Resources in Science and Technology as population proxy

## Technical Notes

- **Memory Efficiency**: Processes scenarios sequentially to avoid memory issues
- **Data Alignment**: Ensures hazard and relevance rasters have matching spatial dimensions
- **Mass Conservation**: Absolute relevance layers preserve total economic values
- **Spatial Resolution**: Uses 30m pixel resolution for analysis

## Troubleshooting

### Common Issues

1. **Missing Input Files**:
   ```
   FileNotFoundError: Required absolute relevance layer missing: gdp
   ```
   **Solution**: Generate absolute relevance layers first using `RelevanceAbsoluteLayer`

2. **Shape Mismatch**:
   ```
   Shape mismatch for gdp: (2000, 1500) vs (2000, 1600)
   ```
   **Solution**: Ensure all input rasters use the same spatial grid and bounds

3. **No Valid Data**:
   ```
   No valid data found in freight layer
   ```
   **Solution**: Check that absolute relevance layers contain non-zero values

### Performance Optimization

- Run on systems with sufficient RAM (>8GB recommended)
- Process scenarios individually if memory is limited
- Use SSD storage for faster I/O operations

## Integration with Other Modules

This module integrates with:

- **Hazard Layer**: Uses flood risk scenarios as input
- **Absolute Relevance Layer**: Uses absolute economic values as input
- **Visualization Module**: Uses standardized plotting functions
- **Configuration Module**: Reads flood risk thresholds and paths

## Example Output Interpretation

For a "Moderate" scenario result:
- GDP: 15.2B € / 142.8B € at risk (10.6%)
- Freight: 3.4M t / 28.9M t at risk (11.8%)
- Population: 125K / 1,450K persons at risk (8.6%)

This means under a 2m sea level rise scenario, approximately 10-12% of economic value and 8.6% of the skilled population would be at flood risk (risk > 0.3 threshold). 