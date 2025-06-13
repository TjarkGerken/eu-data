# EU Climate Risk Assessment System

A comprehensive geospatial analysis tool for assessing climate risks in European regions using a four-layer approach: Hazard, Exposition, Relevance, and Risk.

## System Architecture

### Risk Assessment Layers

1. **Hazard Layer** - Sea level rise and flood risk assessment
2. **Exposition Layer** - Building density, population, and infrastructure exposure
3. **Relevance Layer** - Economic importance and vulnerability factors
4. **Risk Layer** - Integrated risk assessment combining all factors

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

## 📊 Hazard Layer Implementation

### Sea Level Rise Scenarios

| Scenario     | Rise (m) | Description                 | Risk Level |
| ------------ | -------- | --------------------------- | ---------- |
| Conservative | 1.0      | Conservative sea level rise | Low        |
| Moderate     | 2.0      | Moderate sea level rise     | Medium     |
| Severe       | 3.0      | Severe sea level rise       | High       |

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

1. Ensure `auto_download: true` in `code/config/data_config.yaml`
2. The data will be downloaded automatically when needed

### 2. Manual Download

If automatic download is disabled or fails:

1. Visit https://huggingface.co/datasets/TjarkGerken/eu-data
2. Download the following directories:
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
