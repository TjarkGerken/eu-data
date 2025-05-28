#!/usr/bin/env python3
"""
EU Climate Risk Assessment System - Demonstration
=================================================

This script demonstrates how to use the EU Climate Risk Assessment System
with custom sea level rise scenarios and configuration options.
"""

from main import HazardLayer, ProjectConfig, SeaLevelScenario
import numpy as np

def demo_custom_scenarios():
    """Demonstrate custom sea level rise scenarios."""
    print("🌊 EU CLIMATE RISK ASSESSMENT - CUSTOM SCENARIO DEMO")
    print("=" * 60)
    
    # Initialize configuration
    config = ProjectConfig()
    print(f"📁 Data directory: {config.data_dir}")
    print(f"📁 Output directory: {config.output_dir}")
    print(f"🗺️  Target CRS: {config.target_crs}")
    
    # Define custom scenarios
    custom_scenarios = [
        SeaLevelScenario("Optimistic", 0.5, "0.5m rise - optimistic IPCC scenario"),
        SeaLevelScenario("Realistic", 1.5, "1.5m rise - realistic scenario for 2100"),
        SeaLevelScenario("Pessimistic", 4.0, "4m rise - pessimistic scenario"),
        SeaLevelScenario("Extreme", 6.0, "6m rise - extreme worst-case scenario")
    ]
    
    print(f"\n🎯 Custom Scenarios Defined:")
    for scenario in custom_scenarios:
        print(f"   • {scenario.name}: {scenario.rise_meters}m - {scenario.description}")
    
    # Initialize Hazard Layer
    print(f"\n⚙️  Initializing Hazard Layer...")
    hazard_layer = HazardLayer(config)
    
    # Process custom scenarios
    print(f"\n🔄 Processing custom scenarios...")
    flood_extents = hazard_layer.process_scenarios(custom_scenarios)
    
    # Create visualizations
    print(f"\n📊 Creating visualizations...")
    hazard_layer.visualize_hazard_assessment(flood_extents, save_plots=True)
    
    # Export results
    print(f"\n💾 Exporting results...")
    hazard_layer.export_results(flood_extents)
    
    print(f"\n✅ Demo completed! Check the output directory for results.")

def demo_configuration_options():
    """Demonstrate different configuration options."""
    print("\n" + "=" * 60)
    print("🛠️  CONFIGURATION OPTIONS DEMO")
    print("=" * 60)
    
    # Custom configuration with high-resolution output
    custom_config = ProjectConfig(
        data_dir="data",
        output_dir="output_high_res",
        dem_file="ClippedCopernicusHeightProfile.tif",
        target_crs="EPSG:3035",  # European LAEA projection
        figure_size=(25, 20),    # Larger figures
        dpi=600                  # High resolution
    )
    
    print(f"📐 Custom configuration:")
    print(f"   • Figure size: {custom_config.figure_size}")
    print(f"   • DPI: {custom_config.dpi}")
    print(f"   • Output dir: {custom_config.output_dir}")
    
    # You could run analysis with this configuration:
    # hazard_layer = HazardLayer(custom_config)
    # flood_extents = hazard_layer.process_scenarios()
    
    print(f"   ℹ️  Use this config to generate high-resolution outputs")

def demo_quick_analysis():
    """Demonstrate a quick analysis with minimal scenarios."""
    print("\n" + "=" * 60)
    print("⚡ QUICK ANALYSIS DEMO")
    print("=" * 60)
    
    # Quick scenarios for rapid prototyping
    quick_scenarios = [
        SeaLevelScenario("Low", 1.0, "1m rise"),
        SeaLevelScenario("High", 3.0, "3m rise")
    ]
    
    config = ProjectConfig()
    hazard_layer = HazardLayer(config)
    
    print(f"🚀 Running quick analysis with 2 scenarios...")
    
    # Load DEM to show statistics
    dem_data, transform, crs = hazard_layer.load_and_prepare_dem()
    
    print(f"\n📊 DEM Quick Stats:")
    valid_data = dem_data[~np.isnan(dem_data)]
    print(f"   • Total pixels: {dem_data.size:,}")
    print(f"   • Valid pixels: {len(valid_data):,}")
    print(f"   • Elevation range: {np.min(valid_data):.1f}m to {np.max(valid_data):.1f}m")
    print(f"   • Below sea level: {np.sum(valid_data < 0):,} pixels")
    print(f"   • 0-2m elevation: {np.sum((valid_data >= 0) & (valid_data <= 2)):,} pixels")
    print(f"   • 2-5m elevation: {np.sum((valid_data > 2) & (valid_data <= 5)):,} pixels")
    
    # Quick flood extent calculation
    for scenario in quick_scenarios:
        flood_mask = dem_data <= scenario.rise_meters
        flood_mask = np.where(np.isnan(dem_data), False, flood_mask)
        flooded_pixels = np.sum(flood_mask)
        percentage = (flooded_pixels / len(valid_data)) * 100
        print(f"   • {scenario.name} scenario ({scenario.rise_meters}m): {flooded_pixels:,} pixels ({percentage:.1f}%)")

if __name__ == "__main__":
    # Run all demonstrations
    demo_quick_analysis()
    
    print(f"\n" + "=" * 60)
    print("💡 USAGE TIPS")
    print("=" * 60)
    print("1. Modify sea level rise scenarios by creating SeaLevelScenario objects")
    print("2. Adjust output quality using ProjectConfig (figure_size, dpi)")
    print("3. Change coordinate systems via target_crs parameter")
    print("4. All outputs are saved as GeoTIFF files for GIS compatibility")
    print("5. The system handles nodata values and CRS transformations automatically")
    print("6. Logs are saved to 'risk_assessment.log' for debugging")
    
    print(f"\n🎯 To run the full analysis:")
    print("   python main.py")
    
    print(f"\n🔧 To run custom scenarios:")
    print("   Uncomment the demo functions below and run this script")
    
    # Uncomment these lines to run the demos:
    # demo_custom_scenarios()
    # demo_configuration_options() 