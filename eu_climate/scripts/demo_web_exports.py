import os
import sys
import platform
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Test imports with fallback handling
print("=== EU Climate Web Export Demo ===")
print(f"Platform: {platform.system()}")
print(f"Python: {platform.python_version()}")

try:
    from eu_climate.config.config import ProjectConfig
    print("✓ ProjectConfig imported successfully")
    CONFIG_AVAILABLE = True
except ImportError as e:
    print(f"✗ ProjectConfig import failed: {e}")
    CONFIG_AVAILABLE = False

try:
    from eu_climate.utils.web_exports import WebOptimizedExporter
    print("✓ WebOptimizedExporter imported successfully")
    WEB_EXPORT_AVAILABLE = True
except ImportError as e:
    print(f"✗ WebOptimizedExporter import failed: {e}")
    WEB_EXPORT_AVAILABLE = False

try:
    import rasterio
    print("✓ Rasterio available")
    RASTERIO_AVAILABLE = True
except ImportError as e:
    print(f"✗ Rasterio not available: {e}")
    RASTERIO_AVAILABLE = False

try:
    import geopandas as gpd
    print("✓ GeoPandas available")
    GEOPANDAS_AVAILABLE = True
except ImportError as e:
    print(f"✗ GeoPandas not available: {e}")
    GEOPANDAS_AVAILABLE = False

print("\n=== Dependency Check ===")

if WEB_EXPORT_AVAILABLE:
    try:
        exporter = WebOptimizedExporter()
        deps = exporter.check_dependencies()
        
        for dep, available in deps.items():
            status = "✓" if available else "✗"
            print(f"{status} {dep}: {available}")
    except Exception as e:
        print(f"Error checking dependencies: {e}")

print("\n=== Test Web Export System ===")

if CONFIG_AVAILABLE and WEB_EXPORT_AVAILABLE:
    try:
        config = ProjectConfig()
        print("✓ Configuration loaded")
        
        # Test basic functionality
        exporter = WebOptimizedExporter(config.config)
        print("✓ Web exporter initialized")
        
        # Show available formats
        print("\nAvailable export formats:")
        if RASTERIO_AVAILABLE:
            print("  - Cloud-Optimized GeoTIFF (COG) for raster data")
        else:
            print("  - COG export disabled (rasterio not available)")
            
        try:
            if exporter._check_tippecanoe():
                print("  - Mapbox Vector Tiles (MVT) via tippecanoe")
            else:
                print("  - MVT export via Python fallback")
        except:
            print("  - MVT export status unknown")
            
        print("\n=== Windows Specific Information ===")
        if platform.system() == 'Windows':
            print("For optimal performance on Windows:")
            print("1. Use WSL for tippecanoe (vector tiles)")
            print("2. Use conda for GDAL/rasterio installation")
            print("3. COG export works natively on Windows")
            print("4. MVT Python fallback available")
        
    except Exception as e:
        print(f"✗ Error during demo: {e}")
        if "DLL load failed" in str(e):
            print("\n💡 Windows DLL Issue Detected!")
            print("This is a common Windows GDAL issue. Solutions:")
            print("1. Try: conda install -c conda-forge gdal")
            print("2. Install Visual C++ Redistributable")
            print("3. Use WSL for full geospatial stack")
            print("4. Use OSGeo4W distribution")

else:
    print("Demo cannot run - missing core dependencies")

print("\n=== Summary ===")
print("This demo checks what's available and provides fallback options.")
print("The web export system is designed to work with partial functionality.")

if platform.system() == 'Windows' and not RASTERIO_AVAILABLE:
    print("\n🚨 Windows GDAL/Rasterio Issue Detected")
    print("Recommended solutions:")
    print("1. Fresh conda environment with GDAL from conda-forge")
    print("2. Install Microsoft Visual C++ Redistributable 2019")
    print("3. Use WSL (Windows Subsystem for Linux)")
    print("4. Use OSGeo4W distribution")

print("\nDemo complete!")

def main():
    """Main function for running the demo"""
    pass  # All the demo code above runs when the script is imported

if __name__ == "__main__":
    main() 