# Interactive Maps Implementation

## Overview

The data-story-web application now supports interactive maps that efficiently handle large climate risk data files (up to 200MB) using a tile-based architecture. This implementation provides smooth user experience while maintaining data integrity and performance.

## Architecture

### 1. Tile-Based Raster Serving

- **Problem**: Large .tif files (200MB+) cannot be loaded directly in browsers
- **Solution**: On-demand tile generation from source raster files
- **Benefits**:
  - Only loads visible tiles
  - Progressive loading based on zoom level
  - Browser caching of individual tiles
  - Reduced memory footprint

### 2. Vector Overlay System

- **Purpose**: Display cluster polygons from geopackage files
- **Format**: GeoJSON conversion from .gpkg files
- **Features**: Interactive popups with cluster statistics

### 3. Layer Management

- **Multiple scenarios**: Current, Severe, Conservative, Moderate
- **Layer types**: Risk, Hazard, Exposition, Relevance
- **Controls**: Opacity, visibility, scenario switching

## Implementation Details

### Tile Service (`/api/map-tiles/[...params]`)

```typescript
// URL Pattern: /api/map-tiles/{layerName}/{zoom}/{x}/{y}.png
// Example: /api/map-tiles/risk_slr_current/10/512/342.png
```

**Features:**

- Dynamic tile generation from source .tif files
- Color mapping based on layer type
- Caching with Vercel Blob storage
- Fallback to local files
- Error handling for missing data

### Interactive Map Component

```typescript
<InteractiveMap
  title="Climate Risk Assessment"
  description="Interactive exploration of climate scenarios"
  initialLayers={["risk_current", "hazard_severe"]}
  showClusterOverlay={true}
  height="700px"
  enableLayerControls={true}
  scenarioFilter={["current", "severe"]}
/>
```

### Integration with Content Management

Maps can be configured through the admin interface with:

- Interactive mode toggle
- Layer configuration
- Cluster overlay settings
- Scenario filtering
- Custom dimensions

## Performance Optimizations

### 1. Tile Caching Strategy

- **Browser Cache**: Individual tiles cached with 24h TTL
- **Server Cache**: Generated tiles stored in blob storage
- **Memory Management**: Tiles generated on-demand, not pre-computed

### 2. Data Loading Optimization

- **Lazy Loading**: Map components load only when visible
- **Progressive Enhancement**: Fallback to static images if interactive fails
- **Chunk Splitting**: Map libraries loaded separately using Next.js dynamic imports

### 3. File Size Management

- **Tile Size**: 256x256 pixels (standard web map tiles)
- **Compression**: PNG with optimized compression
- **Selective Loading**: Only visible zoom levels and extents loaded

## Data Flow

### 1. Raster Data (.tif → Tiles)

```
Source .tif files → Tile API → Sharp processing → Color mapping → PNG tiles → Browser
```

### 2. Vector Data (.gpkg → GeoJSON)

```
Cluster .gpkg files → Cluster API → ogr2ogr conversion → GeoJSON → Leaflet rendering
```

### 3. Metadata Management

```
Layer configuration → Map service → Client state → UI controls
```

## Usage Examples

### Basic Interactive Map

```typescript
// In content.json
{
  "type": "visualization",
  "data": {
    "title": "Risk Assessment Map",
    "description": "Interactive climate risk visualization",
    "type": "map",
    "interactive": true,
    "initialLayers": ["risk_current"],
    "showClusterOverlay": true,
    "height": "600px"
  }
}
```

### Advanced Configuration

```typescript
{
  "type": "visualization",
  "data": {
    "title": "Multi-Scenario Analysis",
    "type": "map",
    "interactive": true,
    "initialLayers": ["risk_current", "hazard_severe"],
    "scenarioFilter": ["current", "severe"],
    "enableLayerControls": true,
    "showClusterOverlay": true,
    "height": "800px"
  }
}
```

## File Structure

```
data-story-web/
├── components/
│   ├── interactive-map.tsx           # Main map component
│   └── map/
│       └── leaflet-map.tsx          # Leaflet implementation
├── app/api/
│   ├── map-tiles/[...params]/       # Tile serving API
│   └── map-data/
│       └── clusters/[scenario]/     # Cluster data API
├── lib/
│   └── map-tile-service.ts         # Map service utilities
└── public/
    ├── risk/                        # Source .tif files
    └── clusters/                    # Cluster .gpkg files
```

## Dependencies

### New Packages Added

```json
{
  "leaflet": "^1.9.4", // Map library
  "sharp": "^0.33.2", // Image processing
  "@types/leaflet": "^1.9.8" // TypeScript definitions
}
```

### System Requirements

- **Sharp**: For basic image processing
- **Modern Web Formats**: COG and MBTiles files pre-optimized by Python pipeline

## Best Practices

### 1. Performance

- Use scenario filtering to limit loaded layers
- Implement proper error boundaries
- Monitor tile cache hit rates
- Consider tile pregeneration for popular layers

### 2. User Experience

- Provide loading states for tile loading
- Include fallback to static images
- Add layer legends and metadata
- Implement responsive design for mobile

### 3. Data Management

- Keep source files organized by scenario
- Use consistent naming conventions
- Implement proper cache invalidation
- Monitor storage usage

## Troubleshooting

### Common Issues

1. **Tiles not loading**

   - Check source file paths
   - Verify API route accessibility
   - Confirm Sharp dependency installation

2. **Cluster overlays missing**

   - Ensure .gpkg files are accessible
   - Check GDAL installation
   - Verify GeoJSON conversion

3. **Performance issues**
   - Monitor tile generation times
   - Check cache effectiveness
   - Consider reducing initial layer count

### Debug Tools

- Browser Network tab for tile loading
- Console logs for API errors
- Map bounds inspector for coordinate issues

## Future Enhancements

### Planned Features

1. **Vector Tiles**: Convert large vector datasets to MVT format
2. **WebGL Rendering**: Use Deck.gl for high-performance visualization
3. **Real-time Updates**: Live data streaming for dynamic scenarios
4. **Advanced Analytics**: Click-through statistics and heatmaps

### Scalability Considerations

- CDN integration for global tile delivery
- Database optimization for metadata queries
- Serverless function scaling for tile generation
- Progressive Web App features for offline access
