import numpy as np
from typing import Optional, Tuple, Dict, Union
from enum import Enum
from dataclasses import dataclass
from eu_climate.utils.utils import setup_logging

logger = setup_logging(__name__)


class NormalizationStrategy(Enum):
    """
    Enumeration of available normalization strategies.

    Each strategy is optimized for different types of data and use cases:
    - HAZARD_SOPHISTICATED: Advanced preservation of risk distributions
    - EXPOSITION_OPTIMIZED: Full range utilization for exposition visualization
    - ECONOMIC_OPTIMIZED: Optimized for economic data analysis
    - ROBUST_PERCENTILE: Robust to outliers using percentile bounds
    - FULL_RANGE: Simple but effective min-max normalization
    """

    HAZARD_SOPHISTICATED = "hazard_sophisticated"
    EXPOSITION_OPTIMIZED = "exposition_optimized"
    ECONOMIC_OPTIMIZED = "economic_optimized"
    FULL_RANGE = "full_range"
    ROBUST_PERCENTILE = "robust_percentile"


@dataclass
class NormalizationParams:
    """
    Configuration parameters for normalization strategies.

    This dataclass encapsulates all the parameters that control the normalization
    behavior, allowing for fine-tuning of the normalization process based on
    data characteristics and visualization requirements.

    Attributes:
        target_max: Maximum value for normalized output (typically 1.0)
        target_min: Minimum value for normalized output (typically 0.0)
        conservative_max: Conservative maximum to avoid over-saturation
        meaningful_min: Minimum meaningful value for visualization
        significant_threshold: Threshold for determining significant values
        outlier_threshold_percentile: Percentile for outlier detection
        normalization_percentile: Percentile for normalization bounds
        expected_significant_coverage_min: Expected minimum percentage of significant values
        expected_significant_coverage_max: Expected maximum percentage of significant values
        gentle_saturation_factor: Factor for gentle outlier saturation
        tanh_scaling_factor: Scaling factor for tanh saturation function
        preserve_distribution: Whether to preserve original data distribution
        enable_boost_factor: Whether to apply boost factors for range utilization
        enable_outlier_saturation: Whether to apply outlier saturation
    """

    target_max: float = 1.0
    target_min: float = 0.0
    conservative_max: float = 1.0
    meaningful_min: float = 0.001
    significant_threshold: float = 0.3
    outlier_threshold_percentile: float = 99.0
    normalization_percentile: float = 95.0
    expected_significant_coverage_min: float = 30.0
    expected_significant_coverage_max: float = 50.0
    gentle_saturation_factor: float = 0.02
    tanh_scaling_factor: float = 0.1
    preserve_distribution: bool = True
    enable_boost_factor: bool = True
    enable_outlier_saturation: bool = True


class AdvancedDataNormalizer:
    """
    Advanced data normalization utility based on sophisticated hazard layer logic.

    Provides consistent, sophisticated normalization across all risk assessment layers
    while preserving relative relationships and ensuring optimal visualization.
    Incorporates the advanced statistical analysis and distribution preservation
    from the hazard layer as the foundation for all normalization approaches.

    The normalizer uses different strategies optimized for different types of data:
    - Hazard data: Preserves risk distributions with sophisticated analysis
    - Exposition data: Optimizes for full range utilization and visualization
    - Economic data: Balances distribution preservation with range optimization
    - General data: Applies robust normalization techniques

    Key features:
    - Comprehensive statistical analysis of input data
    - Intelligent parameter adjustment based on data characteristics
    - Sophisticated outlier handling with gentle saturation
    - Distribution-aware normalization that preserves important patterns
    - Scale-adaptive processing for different data sizes
    """

    def __init__(
        self,
        strategy: NormalizationStrategy = NormalizationStrategy.HAZARD_SOPHISTICATED,
    ):
        """
        Initialize the advanced data normalizer.

        Args:
            strategy: Normalization strategy to use for processing
        """
        self.strategy = strategy
        self._params = self._get_strategy_params(strategy)

    def _get_strategy_params(
        self, strategy: NormalizationStrategy
    ) -> NormalizationParams:
        """
        Get normalization parameters optimized for each layer type.

        This method returns carefully tuned parameters for each normalization strategy,
        based on extensive testing and analysis of different data types in the
        EU Climate Risk Assessment system.

        Args:
            strategy: Normalization strategy to get parameters for

        Returns:
            NormalizationParams instance with optimized parameters
        """
        if strategy == NormalizationStrategy.HAZARD_SOPHISTICATED:
            return NormalizationParams(
                target_max=1.0,
                meaningful_min=0.05,
                significant_threshold=0.3,
                conservative_max=0.95,
                expected_significant_coverage_min=30.0,
                expected_significant_coverage_max=50.0,
                preserve_distribution=True,
                enable_boost_factor=False,  # Hazard preserves original distribution
            )
        elif strategy == NormalizationStrategy.EXPOSITION_OPTIMIZED:
            return NormalizationParams(
                target_max=1.0,
                meaningful_min=0.01,
                significant_threshold=0.1,
                conservative_max=1.0,
                expected_significant_coverage_min=20.0,
                expected_significant_coverage_max=80.0,
                preserve_distribution=False,
                enable_boost_factor=True,  # Exposition needs full range utilization
            )
        elif strategy == NormalizationStrategy.ECONOMIC_OPTIMIZED:
            return NormalizationParams(
                target_max=1.0,
                meaningful_min=0.01,
                significant_threshold=0.05,
                conservative_max=1.0,
                expected_significant_coverage_min=10.0,
                expected_significant_coverage_max=90.0,
                preserve_distribution=True,
                enable_boost_factor=True,  # Economic data needs full range utilization
            )
        elif strategy == NormalizationStrategy.ROBUST_PERCENTILE:
            return NormalizationParams(
                target_max=1.0,
                meaningful_min=0.01,
                normalization_percentile=1.0,
                enable_boost_factor=True,
            )
        else:  # FULL_RANGE
            return NormalizationParams(
                target_max=1.0, meaningful_min=0.01, enable_boost_factor=True
            )

    def normalize_hazard_data(
        self, risk_data: np.ndarray, valid_study_area: np.ndarray
    ) -> np.ndarray:
        """
        Apply sophisticated hazard normalization preserving risk distributions.

        This is the foundational method based on the advanced logic from hazard_layer.py,
        with detailed statistical analysis and distribution preservation.

        The method performs:
        1. Comprehensive statistical analysis of the input data
        2. Distribution-aware normalization parameter selection
        3. Sophisticated outlier handling with gentle saturation
        4. Preservation of important risk patterns and relationships
        5. Detailed logging of normalization results and guidance

        Args:
            risk_data: Input risk data array to normalize
            valid_study_area: Boolean mask indicating valid study area

        Returns:
            Normalized risk data with preserved distributions
        """
        return self._apply_sophisticated_normalization(
            data=risk_data,
            valid_mask=valid_study_area,
            params=self._get_strategy_params(
                NormalizationStrategy.HAZARD_SOPHISTICATED
            ),
            layer_name="hazard",
        )

    def normalize_exposition_data(
        self, data: np.ndarray, study_area_mask: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Normalize exposition layer data ensuring full range utilization.

        Uses sophisticated normalization with parameters optimized for exposition data.
        This strategy emphasizes full range utilization for optimal visualization
        while maintaining data integrity.

        Args:
            data: Input exposition data array
            study_area_mask: Optional mask for valid study area

        Returns:
            Normalized exposition data with optimized range utilization
        """
        if study_area_mask is None:
            study_area_mask = ~np.isnan(data) & (data > 0)

        return self._apply_sophisticated_normalization(
            data=data,
            valid_mask=study_area_mask,
            params=self._get_strategy_params(
                NormalizationStrategy.EXPOSITION_OPTIMIZED
            ),
            layer_name="exposition",
        )

    def normalize_economic_data(
        self, data: np.ndarray, economic_mask: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Normalize economic relevance data with full range optimization.

        Uses sophisticated normalization with parameters optimized for economic data.
        Balances distribution preservation with range optimization for economic analysis.

        Args:
            data: Input economic data array
            economic_mask: Optional mask for valid economic data

        Returns:
            Normalized economic data with balanced optimization
        """
        if economic_mask is None:
            economic_mask = (data > 0) & ~np.isnan(data)

        return self._apply_sophisticated_normalization(
            data=data,
            valid_mask=economic_mask,
            params=self._get_strategy_params(NormalizationStrategy.ECONOMIC_OPTIMIZED),
            layer_name="economic",
        )

    def normalize_risk_data(
        self,
        data: np.ndarray,
        valid_mask: Optional[np.ndarray] = None,
        preserve_zeros: bool = True,
    ) -> np.ndarray:
        """
        Normalize integrated risk data using sophisticated approach.

        Applies sophisticated normalization optimized for final risk assessment data,
        with options for preserving zero values and handling integrated risk patterns.

        Args:
            data: Input risk data array to normalize
            valid_mask: Optional mask for valid data points
            preserve_zeros: Whether to preserve zero values in the output

        Returns:
            Normalized risk data with sophisticated statistical handling
        """
        if valid_mask is None:
            valid_mask = ~np.isnan(data)

        if preserve_zeros:
            valid_mask = valid_mask & (data > 0)

        return self._apply_sophisticated_normalization(
            data=data,
            valid_mask=valid_mask,
            params=self._get_strategy_params(
                NormalizationStrategy.EXPOSITION_OPTIMIZED
            ),
            layer_name="risk",
        )

    def _apply_sophisticated_normalization(
        self,
        data: np.ndarray,
        valid_mask: np.ndarray,
        params: NormalizationParams,
        layer_name: str,
    ) -> np.ndarray:
        """
        Apply sophisticated normalization based on advanced hazard layer logic.

        This is the core normalization method that incorporates all the sophisticated
        statistical analysis and distribution preservation from the hazard layer.

        The method performs:
        1. Comprehensive statistical analysis of input data
        2. Intelligent normalization strategy selection
        3. Advanced outlier handling with configurable saturation
        4. Distribution-aware processing
        5. Detailed result analysis and guidance

        Args:
            data: Input data array to normalize
            valid_mask: Boolean mask indicating valid data points
            params: Normalization parameters for this strategy
            layer_name: Name of the layer being processed (for logging)

        Returns:
            Sophisticated normalized data array
        """
        # Apply study area mask first
        masked_data = data * valid_mask

        # Get valid data values for normalization analysis
        valid_data_values = masked_data[valid_mask]

        if len(valid_data_values) == 0:
            logger.warning(f"No valid {layer_name} values for normalization")
            return masked_data.astype(np.float32)

        # Calculate comprehensive distribution statistics (like hazard layer)
        data_mean = np.mean(valid_data_values)
        data_median = np.median(valid_data_values)
        data_std = np.std(valid_data_values)
        data_min = np.min(valid_data_values)
        data_max = np.max(valid_data_values)
        data_95th = np.percentile(valid_data_values, 95)
        data_99th = np.percentile(
            valid_data_values, params.outlier_threshold_percentile
        )

        # Calculate current significant value coverage
        current_significant_pct = (
            np.sum(valid_data_values > params.significant_threshold)
            / len(valid_data_values)
            * 100
        )

        # Log comprehensive pre-normalization statistics
        logger.info(f"Pre-normalization statistics for {layer_name}:")
        logger.info(
            f"  Mean: {data_mean:.4f}, Median: {data_median:.4f}, Std: {data_std:.4f}"
        )
        logger.info(f"  Range: {data_min:.4f} to {data_max:.4f}")
        logger.info(
            f"  95th percentile: {data_95th:.4f}, 99th percentile: {data_99th:.4f}"
        )
        logger.info(
            f"  Current significant value coverage (>{params.significant_threshold}): {current_significant_pct:.1f}%"
        )

        # Apply sophisticated normalization logic (adapted from hazard layer)
        normalized_data = masked_data.copy()

        # Determine normalization approach based on data characteristics
        if params.preserve_distribution and data_max <= params.target_max:
            logger.info(
                f"{layer_name}: Data already in optimal range, minimal normalization applied"
            )
            # Apply gentle adjustment only if needed
            if data_max < params.target_max * 0.8 and params.enable_boost_factor:
                boost_factor = params.target_max * 0.9 / data_max
                normalized_data = masked_data * boost_factor
                logger.info(
                    f"{layer_name}: Applied gentle boost factor: {boost_factor:.3f}"
                )
        elif data_max > params.target_max:
            # Apply sophisticated normalization based on percentiles
            if data_99th > params.conservative_max:
                normalization_factor = params.conservative_max / data_99th
                normalized_data = masked_data * normalization_factor
                logger.info(
                    f"{layer_name}: Applied conservative normalization with factor: {normalization_factor:.3f}"
                )
            else:
                # Just ensure no values exceed target max
                normalized_data = np.minimum(masked_data, params.target_max)
                logger.info(f"{layer_name}: Applied gentle clipping to target max")
        else:
            # Apply full range utilization for visualization optimization
            if not params.preserve_distribution and params.enable_boost_factor:
                if data_max < params.target_max * 0.95:
                    boost_factor = params.target_max / data_max
                    normalized_data = masked_data * boost_factor
                    logger.info(
                        f"{layer_name}: Applied full range boost factor: {boost_factor:.3f}"
                    )

        # Apply sophisticated outlier handling (like hazard layer)
        if params.enable_outlier_saturation:
            reasonable_max = params.conservative_max
            outlier_mask = normalized_data > reasonable_max
            if np.any(outlier_mask):
                # Apply gentle saturation using tanh function (from hazard layer)
                normalized_data[outlier_mask] = (
                    reasonable_max
                    + params.gentle_saturation_factor
                    * np.tanh(
                        (normalized_data[outlier_mask] - reasonable_max)
                        / params.tanh_scaling_factor
                    )
                )
                outlier_count = np.sum(outlier_mask & valid_mask)
                logger.info(
                    f"{layer_name}: Applied gentle saturation to {outlier_count} extreme outlier pixels"
                )

        # Ensure meaningful minimum values (from hazard layer logic)
        if params.meaningful_min > 0:
            normalized_data = np.where(
                valid_mask,
                np.maximum(normalized_data, params.meaningful_min),
                normalized_data,
            )

        # Calculate final distribution statistics and provide analysis
        final_valid_values = normalized_data[valid_mask]
        if len(final_valid_values) > 0:
            final_mean = np.mean(final_valid_values)
            final_median = np.median(final_valid_values)
            final_max = np.max(final_valid_values)
            final_min = np.min(final_valid_values)
            final_95th = np.percentile(final_valid_values, 95)

            # Calculate distribution categories (adapted from hazard layer)
            very_high_count = np.sum(final_valid_values > 0.8)
            high_count = np.sum(
                (final_valid_values > 0.6) & (final_valid_values <= 0.8)
            )
            moderate_count = np.sum(
                (final_valid_values > params.significant_threshold)
                & (final_valid_values <= 0.6)
            )
            low_count = np.sum(
                (final_valid_values > 0.1)
                & (final_valid_values <= params.significant_threshold)
            )
            minimal_count = np.sum(final_valid_values <= 0.1)

            total_count = len(final_valid_values)
            significant_count = very_high_count + high_count + moderate_count
            final_significant_pct = significant_count / total_count * 100

            # Log comprehensive post-normalization statistics
            logger.info(f"Post-normalization statistics for {layer_name}:")
            logger.info(f"  Mean: {final_mean:.4f}, Median: {final_median:.4f}")
            logger.info(
                f"  Range: {final_min:.4f} to {final_max:.4f}, 95th percentile: {final_95th:.4f}"
            )

            logger.info(f"Final {layer_name} distribution:")
            logger.info(
                f"  Very High (>0.8): {very_high_count / total_count * 100:.1f}% ({very_high_count} pixels)"
            )
            logger.info(
                f"  High (0.6-0.8): {high_count / total_count * 100:.1f}% ({high_count} pixels)"
            )
            logger.info(
                f"  Moderate (>{params.significant_threshold:.1f}-0.6): {moderate_count / total_count * 100:.1f}% ({moderate_count} pixels)"
            )
            logger.info(
                f"  Low (0.1-{params.significant_threshold:.1f}): {low_count / total_count * 100:.1f}% ({low_count} pixels)"
            )
            logger.info(
                f"  Minimal (<=0.1): {minimal_count / total_count * 100:.1f}% ({minimal_count} pixels)"
            )
            logger.info(
                f"  **Total significant values (>{params.significant_threshold:.1f}): {final_significant_pct:.1f}%**"
            )

            # Provide intelligent guidance (adapted from hazard layer)
            if final_significant_pct > params.expected_significant_coverage_max:
                logger.warning(
                    f"{layer_name}: Significant value coverage ({final_significant_pct:.1f}%) is higher than expected "
                    f"(~{params.expected_significant_coverage_max:.0f}%). Consider adjusting thresholds."
                )
            elif final_significant_pct < params.expected_significant_coverage_min:
                logger.warning(
                    f"{layer_name}: Significant value coverage ({final_significant_pct:.1f}%) is lower than expected "
                    f"(~{params.expected_significant_coverage_min:.0f}%). Consider increasing sensitivity."
                )
            else:
                logger.info(
                    f"{layer_name}: Significant value coverage ({final_significant_pct:.1f}%) is within expected range "
                    f"({params.expected_significant_coverage_min:.0f}-{params.expected_significant_coverage_max:.0f}%)."
                )

            # Calculate range utilization for visualization optimization
            range_utilization = (
                (final_max - final_min) / (params.target_max - params.target_min) * 100
            )
            logger.info(f"{layer_name}: Range utilization: {range_utilization:.1f}%")

            if range_utilization < 90 and not params.preserve_distribution:
                logger.info(
                    f"{layer_name}: Range utilization could be improved for better visualization"
                )

        return normalized_data.astype(np.float32)


# Convenience functions for backward compatibility and easy usage
def normalize_layer_data(
    data: np.ndarray,
    layer_type: str,
    valid_mask: Optional[np.ndarray] = None,
    strategy: Optional[NormalizationStrategy] = None,
) -> np.ndarray:
    """
    Convenience function for normalizing layer data with appropriate sophisticated defaults.

    This function provides a simple interface for normalizing different types of layer data
    using the most appropriate normalization strategy for each data type.

    Args:
        data: Input data array to normalize
        layer_type: Type of layer ('hazard', 'exposition', 'relevance', 'risk')
        valid_mask: Optional validity mask for the data
        strategy: Optional strategy override for custom normalization

    Returns:
        Normalized data array using sophisticated normalization appropriate for the layer type
    """
    # Determine optimal strategy for layer type
    if strategy is None:
        if layer_type == "hazard":
            strategy = NormalizationStrategy.HAZARD_SOPHISTICATED
        elif layer_type == "exposition":
            strategy = NormalizationStrategy.EXPOSITION_OPTIMIZED
        elif layer_type in ["relevance", "economic"]:
            strategy = NormalizationStrategy.ECONOMIC_OPTIMIZED
        else:  # risk and others
            strategy = NormalizationStrategy.EXPOSITION_OPTIMIZED

    # Create normalizer and apply appropriate method
    normalizer = AdvancedDataNormalizer(strategy)

    if layer_type == "hazard":
        if valid_mask is None:
            valid_mask = ~np.isnan(data) & (data > 0)
        return normalizer.normalize_hazard_data(data, valid_mask)
    elif layer_type == "exposition":
        return normalizer.normalize_exposition_data(data, valid_mask)
    elif layer_type in ["relevance", "economic"]:
        return normalizer.normalize_economic_data(data, valid_mask)
    elif layer_type == "risk":
        return normalizer.normalize_risk_data(data, valid_mask)
    else:
        raise ValueError(f"Unknown layer type: {layer_type}")


def ensure_full_range_utilization(
    data: np.ndarray,
    valid_mask: Optional[np.ndarray] = None,
    target_max: float = 1.0,
    target_min: float = 0.0,
) -> np.ndarray:
    """
    Ensure data fully utilizes the target range using sophisticated normalization.

    This function applies sophisticated normalization to maximize the utilization
    of the target range while preserving data relationships and handling outliers
    appropriately.

    Args:
        data: Input data array to normalize
        valid_mask: Optional validity mask for the data
        target_max: Target maximum value for the output
        target_min: Target minimum value for the output

    Returns:
        Data array with sophisticated full range utilization
    """
    # Create custom parameters for full range utilization
    params = NormalizationParams(
        target_max=target_max,
        target_min=target_min,
        enable_boost_factor=True,
        preserve_distribution=False,
    )

    # Create normalizer with full range strategy
    normalizer = AdvancedDataNormalizer(NormalizationStrategy.FULL_RANGE)

    if valid_mask is None:
        valid_mask = ~np.isnan(data)

    return normalizer._apply_sophisticated_normalization(
        data, valid_mask, params, "full_range"
    )


# Legacy compatibility - will be removed in future versions
class DataNormalizer(AdvancedDataNormalizer):
    """
    Legacy compatibility wrapper - use AdvancedDataNormalizer instead.

    This class is maintained for backward compatibility but will be deprecated
    in future versions. Please use AdvancedDataNormalizer directly.
    """

    pass
