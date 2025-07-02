/*
 * Enhanced Map Layer Types for Customizable Styling
 * Based on EU Climate Risk Assessment color schemes
 */

// ---- Core Color Types ----
export interface ColorStop {
  /** Position within gradient (0-1) */
  position: number;
  /** Hex color code */
  color: string;
}

// ---- Raster Layer Color Scheme ----
export interface RasterColorScheme {
  /** Unique ID */
  id: string;
  /** Internal name */
  name: string;
  /** Display name for UI */
  displayName: string;
  /** Description for UI */
  description: string;
  /** Array of color stops */
  colors: ColorStop[];
  /** Category for filtering */
  category: 'risk' | 'relevance' | 'exposition' | 'economic' | 'hazard' | 'custom';
}

// ---- Vector Layer Style ----
export interface VectorStyle {
  fillColor: string;
  fillOpacity: number;
  borderColor: string;
  borderWidth: number;
  borderOpacity: number;
  /** Leaflet dash array string, e.g. "5,5" */
  borderDashArray?: string;
}

// ---- Layer Style Configuration ----
export interface LayerStyleConfig {
  id: string;
  type: 'raster' | 'vector';
  rasterScheme?: RasterColorScheme;
  vectorStyle?: VectorStyle;
  /** For user-defined gradients */
  customRasterColors?: ColorStop[];
  lastModified?: string;
}

/* ------------------------------------
 * Constants / Defaults
 * ----------------------------------*/

// Color scheme IDs for easy reference in code & UI
export const SCHEME_IDS = {
  RISK_DEFAULT: 'risk-white-yellow-orange-red',
  RELEVANCE_DEFAULT: 'relevance-white-green-darkgreen',
  EXPOSITION_DEFAULT: 'exposition-white-green-darkgreen',
  ECONOMIC_DEFAULT: 'economic-white-green-red-black',
  HAZARD_DEFAULT: 'hazard-white-orange-red-darkred',
} as const;

export type SchemeId = typeof SCHEME_IDS[keyof typeof SCHEME_IDS];

// Default vector styles by semantic layer type (used when no custom style provided)
export const DEFAULT_VECTOR_STYLES: Record<string, VectorStyle> = {
  clusters: {
    fillColor: '#4fc3f7',
    fillOpacity: 0.6,
    borderColor: '#ffffff',
    borderWidth: 2,
    borderOpacity: 0.9,
  },
  ports: {
    fillColor: '#9c27b0',
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
  },
};

export type ColorSchemeCategory = RasterColorScheme['category'];

// Ensure file recognized as a module
export {}; 