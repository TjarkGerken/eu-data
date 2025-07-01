import rasterio
import numpy as np

path = 'eu_climate/data/source/Pop/POP_GHS_2025.tif'
print("=== NEW 2025 POPULATION FILE ANALYSIS ===")

with rasterio.open(path) as src:
    print(f"File: {path}")
    print(f"Shape: {src.shape}")
    print(f"Bounds: {src.bounds}")
    print(f"Resolution: {src.res}")
    print(f"CRS: {src.crs}")
    
    data = src.read(1)
    print(f"Data type: {data.dtype}")
    print(f"NoData: {src.nodata}")
    
    # Analyze population values
    valid = data[data > 0]
    print(f"\nPopulation Statistics:")
    print(f"Total population in file: {valid.sum():,.0f}")
    print(f"Valid pixels: {len(valid):,}")
    print(f"Min value: {valid.min():.6f}")
    print(f"Max value: {valid.max():.6f}")
    print(f"Mean: {valid.mean():.6f}")
    print(f"Median: {np.median(valid):.6f}")
    
    print(f"\nGeographic Coverage:")
    print(f"Longitude: {src.bounds.left:.3f} to {src.bounds.right:.3f}")
    print(f"Latitude: {src.bounds.bottom:.3f} to {src.bounds.top:.3f}")
    
    print(f"\nResolution in 3 arcseconds:")
    lon_res, lat_res = src.res
    print(f"Longitude: {lon_res} degrees = {lon_res * 3600:.1f} arcseconds")
    print(f"Latitude: {lat_res} degrees = {abs(lat_res) * 3600:.1f} arcseconds")
    
    # Check if this might be different admin level data
    unique_vals = np.unique(valid)
    print(f"\nData Characteristics:")
    print(f"Unique values: {len(unique_vals):,}")
    print(f"Integer-like values: {len([v for v in unique_vals if abs(v - round(v)) < 0.001])}")
    
    # Sample some values
    print(f"\nFirst 20 unique values:")
    for i, val in enumerate(unique_vals[:20]):
        print(f"  {val:.6f}")

print("\n=== COMPARED TO EXPECTED ===")
expected = 16655799
actual = valid.sum()
ratio = actual / expected
print(f"Expected Netherlands 2025: {expected:,}")
print(f"Actual file total: {actual:,.0f}")
print(f"Ratio: {ratio:.1f}x")
print(f"Excess population: {actual - expected:,.0f}")

print("\n=== GEOGRAPHIC ASSESSMENT ===")
print("Netherlands bounds: ~3.3-7.2°E, 50.7-53.6°N")
print("File bounds: 3.360-7.221°E, 50.751-53.554°N")
print("Assessment: File covers Netherlands + small border areas")
print("=> The file has correct geographic scope but population is ~6x too high")
print("=> This suggests either:")
print("   1. Different population units/scaling")
print("   2. Different temporal baseline")
print("   3. Includes border area populations that need masking") 