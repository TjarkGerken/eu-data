# Layer Color Customization Implementation Guide

## Overview

This implementation provides comprehensive color customization for both raster and vector map layers, inspired by the scientific color schemes from the EU Climate Risk Assessment visualization system.

## Features

### 🎨 Raster Layer Customization
- **Predefined Color Schemes**: Based on scientific visualization standards
  - Risk assessment (white → yellow → orange → red)
  - Hazard assessment (white → orange → red)
  - Exposition (white → light green → dark green)
  - Relevance (white → green variants)
  - Economic risk (white → green → red → black)
  - Additional custom gradients

- **Color Scheme Categories**: Organized by purpose
  - `risk` - Risk assessment color schemes
  - `relevance` - Relevance layer color schemes  
  - `exposition` - Exposition layer color schemes
  - `economic` - Economic impact color schemes
  - `hazard` - Hazard assessment color schemes
  - `custom` - Additional custom gradients

### 🔷 Vector Layer Customization
- **Fill Color**: Full color picker with predefined colors and custom hex input
- **Fill Opacity**: 0-100% transparency control
- **Border Color**: Customizable outline colors
- **Border Width**: 0-10px adjustable border thickness
- **Border Opacity**: Independent border transparency
- **Border Style**: Multiple line styles (solid, dashed, dotted, dash-dot)

## Implementation Structure

### Core Files

#### Type Definitions (`lib/map-types.ts`)
```typescript
interface RasterColorScheme {
  id: string;
  name: string;
  displayName: string;
  description: string;
  colors: ColorStop[];
  category: 'risk' | 'relevance' | 'exposition' | 'economic' | 'hazard' | 'custom';
}

interface VectorStyle {
  fillColor: string;
  fillOpacity: number;
  borderColor: string;
  borderWidth: number;
  borderOpacity: number;
  borderDashArray?: string;
}

interface LayerStyleConfig {
  id: string;
  type: 'raster' | 'vector';
  rasterScheme?: RasterColorScheme;
  vectorStyle?: VectorStyle;
  customRasterColors?: ColorStop[];
  lastModified?: string;
}
```

#### Color Schemes Library (`lib/color-schemes.ts`)
- Scientific color definitions from `visualization.py`
- Color interpolation utilities
- Leaflet color function generators
- Predefined scheme management

#### Style Editor Components
- `RasterStyleEditor`: Color scheme selection with live preview
- `VectorStyleEditor`: Comprehensive vector styling controls

### Enhanced Components

#### Layer Manager (`components/admin/layer-manager.tsx`)
- Added "Style" button to each layer card
- Style configuration dialog with appropriate editor
- API integration for persisting style changes
- Real-time style preview

#### Interactive Map (`components/interactive-map.tsx`)
- Updated legend to show custom color schemes
- Maintains backward compatibility with existing layers

#### Base Leaflet Map (`components/map/base-leaflet-map.tsx`)
- Enhanced vector layer styling with custom configurations
- Custom raster color function support
- Fallback to original styling for layers without custom config

### API Endpoints

#### Style Management (`/api/map-layers/[layerId]/style`)
- `GET`: Retrieve layer style configuration
- `PUT`: Update layer style configuration
- `DELETE`: Remove layer style configuration

#### Style Service Utilities (`lib/map-style-service.ts`)
- `loadLayerStyleConfig(layerId)`: Load single layer style configuration
- `saveLayerStyleConfig(layerId, config)`: Save layer style configuration
- `loadLayersWithStyleConfigs(layers)`: Bulk load styles for multiple layers
- `deleteLayerStyleConfig(layerId)`: Remove layer style configuration

**Automatic Loading**: All map components automatically load style configurations when layers are loaded, ensuring styles are always current and persistent across page reloads.

## Usage Guide

### For Administrators

1. **Access Layer Manager**: Navigate to the admin layer management interface
2. **Configure Layer Style**: Click the "Style" button on any layer card
3. **Customize Appearance**:
   - **Raster Layers**: Select from predefined color schemes or create custom gradients
   - **Vector Layers**: Adjust fill color, border properties, and opacity settings
4. **Preview Changes**: See real-time preview of style changes
5. **Apply Changes**: Styles are automatically saved and applied

### For Content Creators

- Styled layers automatically appear with custom colors in interactive maps
- Legend shows proper color gradients for raster layers
- Vector layers display with configured styling
- All changes are persistent across page reloads

### For End Users

- Maps display with consistently styled layers
- Legend accurately represents layer colors
- No additional interaction required

## Color Scheme Categories

### Risk Assessment (`risk`)
- **Default Risk Scheme**: White → Yellow → Orange → Red → Dark Red
- Suitable for showing increasing risk levels

### Hazard Assessment (`hazard`) 
- **Hazard Scheme**: White → Orange → Red → Dark Red
- Focused on immediate threat visualization

### Exposition (`exposition`)
- **Exposition Scheme**: White → Light Green → Dark Green → Black
- Shows exposure levels with green gradient

### Relevance (`relevance`)
- **Relevance Scheme**: White → Light Green → Green → Dark Green
- Clean green gradient for relevance data

### Economic Impact (`economic`)
- **Economic Scheme**: White → Green → Red → Black
- Shows transition from positive to negative economic impact

### Custom Schemes (`custom`)
- **Water Blues**: Blue gradient for water-related data
- **Purple Gradient**: General purpose purple gradient

## Technical Integration

### Backward Compatibility
- Existing layers without style configs use original styling
- Legacy `colorScale` arrays still supported
- No breaking changes to existing functionality

### Performance Considerations
- Color functions are optimized for real-time rendering
- Style configurations cached in component state
- Minimal API calls through efficient change detection

### Browser Support
- Works with all modern browsers supporting CSS gradients
- Graceful fallback for older browsers
- No external dependencies required

## Future Enhancements

### Planned Features
- Custom gradient builder interface
- Import/export of color schemes
- Bulk style operations
- Advanced color interpolation options

### Database Integration
- Current implementation uses in-memory storage
- Ready for database persistence layer
- Supports user-specific style preferences

## Examples

### Applying Risk Color Scheme
```typescript
const riskScheme = getSchemeById('risk-white-yellow-orange-red');
handleRasterSchemeChange(riskScheme);
```

### Configuring Vector Style
```typescript
const vectorStyle = {
  fillColor: '#3b82f6',
  fillOpacity: 0.6,
  borderColor: '#ffffff',
  borderWidth: 2,
  borderOpacity: 1.0,
  borderDashArray: '5,5' // dashed border
};
handleVectorStyleChange(vectorStyle);
```

This implementation provides a comprehensive, user-friendly color customization system that maintains scientific accuracy while offering flexibility for different visualization needs. 