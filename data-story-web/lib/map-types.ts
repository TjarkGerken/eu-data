/**
 * Enhanced Map Layer Types for Customizable Styling
 * Based on EU Climate Risk Assessment color schemes
 */

export interface ColorStop {
  position: number; // 0-1
  color: string; // hex color
}

export interface RasterColorScheme {
  id: string;
  name: string;
  displayName: string;
  description: string;
  colors: ColorStop[];
  category: 'risk' | 'relevance' | 'exposition' | 'economic' | 'hazard' | 'custom';
}

export interface VectorStyle {
  fillColor: string;
  fillOpacity: number;
  borderColor: string;
  borderWidth: number;
  borderOpacity: number;
  borderDashArray?: string; // for dashed lines: "5,5" for dashed, undefined for solid
}

export interface LayerStyleConfig {
  id: string;
  type: 'raster' | 'vector';
  rasterScheme?: RasterColorScheme;
  vectorStyle?: VectorStyle;
  customRasterColors?: ColorStop[]; // for fully custom schemes
  lastModified?: string;
}

// Enhanced layer state with styling
export interface StyledLayerState {
  id: string;
  visible: boolean;
  opacity: number;
  metadata: {
    name: string;
    dataType: string;
    format: string;
    [key: string]: unknown;
  }; // Simplified metadata to avoid circular imports
  styleConfig?: LayerStyleConfig;
}

// Color scheme categories for UI organization
export type ColorSchemeCategory = 'risk' | 'relevance' | 'exposition' | 'economic' | 'hazard' | 'custom';

// Predefined color scheme IDs
export const SCHEME_IDS = {
  RISK_DEFAULT: 'risk-white-yellow-orange-red',
  RELEVANCE_DEFAULT: 'relevance-white-green-darkgreen',
  EXPOSITION_DEFAULT: 'exposition-white-green-darkgreen',
  ECONOMIC_DEFAULT: 'economic-white-green-red-black',
  HAZARD_DEFAULT: 'hazard-white-orange-red-darkred',
} as const;

// Default vector styles by layer type
export const DEFAULT_VECTOR_STYLES = {
  clusters: {
    fillColor: '#4fc3f7',
    fillOpacity: 0.6,
    borderColor: '#ffffff',
    borderWidth: 2,
    borderOpacity: 0.9,
  },
  ports: {
    fillColor: '#9c27b0', // violet
    fillOpacity: 0.7,
    borderColor: '#000000',
    borderWidth: 1,
    borderOpacity: 1.0,
  },
  nuts: {
    fillColor: 'transparent',
    fillOpacity: 0,
    borderColor: '#2c3e50',
    borderWidth: 1,
    borderOpacity: 0.9,
  },
  default: {
    fillColor: '#ff6b6b',
    fillOpacity: 0.6,
    borderColor: '#ffffff',
    borderWidth: 2,
    borderOpacity: 0.9,
  }
} as const; 