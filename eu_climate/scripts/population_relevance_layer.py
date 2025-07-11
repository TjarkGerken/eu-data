import sys
from pathlib import Path
import numpy as np
import rasterio

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from eu_climate.config.config import ProjectConfig
from eu_climate.utils.utils import setup_logging
from eu_climate.utils.data_loading import load_population_2025_with_validation
from eu_climate.utils.visualization import LayerVisualizer
from eu_climate.utils.normalise_data import (
    AdvancedDataNormalizer,
    NormalizationStrategy,
)
from eu_climate.utils.conversion import RasterTransformer

logger = setup_logging(__name__)


class PopulationRelevanceLayer:
    """Creates population relevance layer with consistent formatting and styling."""

    def __init__(self, config: ProjectConfig):
        self.config = config
        self.visualizer = LayerVisualizer(config)
        self.normalizer = AdvancedDataNormalizer(
            NormalizationStrategy.ECONOMIC_OPTIMIZED
        )
        self.transformer = RasterTransformer(
            target_crs=config.target_crs, config=config
        )

    def load_population_data(self):
        """Load 2025 population data with corrected resolution handling."""
        logger.info("Loading 2025 population data for relevance layer...")

        # Load using the corrected 2025 population loading function
        population_data, metadata, validation_passed = (
            load_population_2025_with_validation(
                self.config, apply_study_area_mask=True
            )
        )

        # Log processing details
        logger.info("Population Data Processing Results:")
        logger.info(f"  Data shape: {population_data.shape}")
        logger.info(f"  Source file: {metadata['source_file']}")
        logger.info(f"  Resampling method: {metadata['resampling_method']}")
        logger.info(f"  Target CRS: {metadata['crs']}")
        logger.info(
            f"  Area scaling applied: {metadata.get('area_scaling_applied', False)}"
        )

        # Calculate statistics
        valid_data = population_data[~np.isnan(population_data) & (population_data > 0)]
        total_population = int(valid_data.sum()) if len(valid_data) > 0 else 0

        logger.info(f"  Total population: {total_population:,} persons")
        logger.info(f"  Valid pixels: {len(valid_data):,}")
        logger.info(
            f"  Population density range: {valid_data.min():.2f} - {valid_data.max():.2f} persons/pixel"
        )

        return population_data, metadata

    def normalize_population_data(self, population_data: np.ndarray) -> np.ndarray:
        """Normalize population data using economic optimization strategy."""
        logger.info("Normalizing population data for relevance layer...")

        # Create validity mask
        valid_mask = (population_data > 0) & ~np.isnan(population_data)

        # Apply economic optimization normalization
        normalized_data = self.normalizer.normalize_economic_data(
            population_data, valid_mask
        )

        # Log normalization results
        normalized_valid = normalized_data[valid_mask]
        logger.info(f"Normalized population data:")
        logger.info(f"  Min: {np.min(normalized_valid):.6f}")
        logger.info(f"  Max: {np.max(normalized_valid):.6f}")
        logger.info(f"  Mean: {np.mean(normalized_valid):.6f}")
        logger.info(f"  Std: {np.std(normalized_valid):.6f}")

        return normalized_data

    def save_relevance_layer(
        self, relevance_data: np.ndarray, metadata: dict, layer_name: str = "population"
    ):
        """Save population relevance layer to standard relevance directory structure."""

        # Create output directory structure
        output_dir = self.config.output_dir / "relevance"
        tif_dir = output_dir / "tif"
        tif_dir.mkdir(parents=True, exist_ok=True)

        # Prepare output metadata
        output_meta = {
            "driver": "GTiff",
            "dtype": "float32",
            "width": metadata["width"],
            "height": metadata["height"],
            "count": 1,
            "crs": metadata["crs"],
            "transform": metadata["transform"],
            "nodata": None,
        }

        # Save TIF file
        tif_path = tif_dir / f"relevance_{layer_name}.tif"
        if tif_path.exists():
            tif_path.unlink()

        with rasterio.open(tif_path, "w", **output_meta) as dst:
            dst.write(relevance_data.astype(np.float32), 1)

        logger.info(f"Saved {layer_name} relevance layer to {tif_path}")

        return tif_path

    def visualize_relevance_layer(
        self, relevance_data: np.ndarray, metadata: dict, layer_name: str = "population"
    ):
        """Create visualization using standard relevance layer styling."""

        output_dir = self.config.output_dir / "relevance"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Load land mask for proper visualization
        land_mask = None
        try:
            with rasterio.open(self.config.land_mass_path) as src:
                land_mask, _ = rasterio.warp.reproject(
                    source=src.read(1),
                    destination=np.zeros(
                        (metadata["height"], metadata["width"]), dtype=np.uint8
                    ),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=metadata["transform"],
                    dst_crs=metadata["crs"],
                    resampling=rasterio.enums.Resampling.nearest,
                )
                land_mask = (land_mask > 0).astype(np.uint8)
                logger.info("Loaded and transformed land mask for visualization")
        except Exception as e:
            logger.warning(f"Could not load land mask for visualization: {e}")

        # Create visualization using standard relevance layer styling
        plot_path = output_dir / f"relevance_{layer_name}_plot.png"

        self.visualizer.visualize_relevance_layer(
            data=relevance_data,
            meta=metadata,
            layer_name=layer_name,
            output_path=plot_path,
            land_mask=land_mask,
        )

        logger.info(f"Saved {layer_name} relevance visualization to {plot_path}")

        return plot_path

    def generate_population_relevance_layer(self) -> Path:
        """Main execution flow to generate population relevance layer."""
        logger.info("Starting population relevance layer generation")

        # Load population data
        population_data, metadata = self.load_population_data()

        # Normalize for relevance layer
        relevance_data = self.normalize_population_data(population_data)

        # Save TIF file
        tif_path = self.save_relevance_layer(relevance_data, metadata)

        # Create visualization
        plot_path = self.visualize_relevance_layer(relevance_data, metadata)

        logger.info("Population relevance layer generation completed successfully")
        logger.info(f"  TIF output: {tif_path}")
        logger.info(f"  PNG output: {plot_path}")

        return tif_path


def main():
    """Main execution function."""
    logger.info("Starting Population Relevance Layer Generation")

    # Initialize configuration
    config = ProjectConfig()

    # Create population relevance layer generator
    population_relevance = PopulationRelevanceLayer(config)

    try:
        # Generate the population relevance layer
        output_path = population_relevance.generate_population_relevance_layer()

        # Final summary
        logger.info("=" * 70)
        logger.info("POPULATION RELEVANCE LAYER SUMMARY")
        logger.info("=" * 70)
        logger.info(f"✓ Population relevance layer generated successfully")
        logger.info(
            f"✓ Used 2025 GHS population data with corrected resolution handling"
        )
        logger.info(f"✓ Applied economic optimization normalization")
        logger.info(f"✓ Netherlands study area masking applied")
        logger.info(f"✓ Consistent relevance layer styling and formatting")
        logger.info(f"Output: {output_path}")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"Error in population relevance layer generation: {e}")
        import traceback

        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise


if __name__ == "__main__":
    main()
