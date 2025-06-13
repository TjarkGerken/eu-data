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
