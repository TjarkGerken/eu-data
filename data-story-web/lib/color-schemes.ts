/**
 * Color Schemes Library for EU Climate Risk Assessment
 * Based on the visualization.py scientific color schemes
 */

import { RasterColorScheme, ColorStop, SCHEME_IDS } from './map-types';

// Color utility functions
export function createColorStops(colorArray: Array<[number, string]>): ColorStop[] {
  return colorArray.map(([position, color]) => ({ position, color }));
}

export function interpolateColor(stops: ColorStop[], position: number): string {
  // Clamp position to 0-1
  position = Math.max(0, Math.min(1, position));
  
  // Find the two stops to interpolate between
  for (let i = 0; i < stops.length - 1; i++) {
    const current = stops[i];
    const next = stops[i + 1];
    
    if (position >= current.position && position <= next.position) {
      // Calculate interpolation factor
      const factor = (position - current.position) / (next.position - current.position);
      
      // Parse colors
      const currentRgb = hexToRgb(current.color);
      const nextRgb = hexToRgb(next.color);
      
      if (!currentRgb || !nextRgb) return current.color;
      
      // Interpolate RGB values
      const r = Math.round(currentRgb.r + (nextRgb.r - currentRgb.r) * factor);
      const g = Math.round(currentRgb.g + (nextRgb.g - currentRgb.g) * factor);
      const b = Math.round(currentRgb.b + (nextRgb.b - currentRgb.b) * factor);
      
      return rgbToHex(r, g, b);
    }
  }
  
  // If position is outside range, return closest stop
  return position <= stops[0].position ? stops[0].color : stops[stops.length - 1].color;
}

export function createGradientFromStops(stops: ColorStop[]): string {
  const gradientStops = stops.map(stop => `${stop.color} ${stop.position * 100}%`);
  return `linear-gradient(to right, ${gradientStops.join(', ')})`;
}

export function createLeafletColorFunction(scheme: RasterColorScheme, valueRange: [number, number]) {
  return (pixelValue: number): string | null => {
    if (pixelValue === null || pixelValue === undefined || isNaN(pixelValue)) {
      return null;
    }
    
    // Normalize pixel value to 0-1 range
    const normalized = (pixelValue - valueRange[0]) / (valueRange[1] - valueRange[0]);
    const clampedNormalized = Math.max(0, Math.min(1, normalized));
    
    return interpolateColor(scheme.colors, clampedNormalized);
  };
}

// Utility functions for color conversion
function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? {
    r: parseInt(result[1], 16),
    g: parseInt(result[2], 16),
    b: parseInt(result[3], 16)
  } : null;
}

function rgbToHex(r: number, g: number, b: number): string {
  return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
}

// Color scheme definitions based on visualization.py
const EXPOSITION_COLORS: Array<[number, string]> = [
  [0.0, '#ffffff'],
  [0.05, '#d8f3dc'],    
  [0.125, '#b7e4c7'],    
  [0.25, '#2d6a4f'],    
  [0.5, '#1b4332'],    
  [0.7, '#081c15'],
  [1.0, '#000000']
];

const ECONOMIC_RISK_COLORS: Array<[number, string]> = [
  [0.0, '#ffffff'],    
  [0.1, '#b6ffb6'],   
  [0.5, '#ff0000'],   
  [1.0, '#000000']    
];

const HAZARD_RISK_COLORS: Array<[number, string]> = [
  [0.0, '#ffffff'],
  [0.25, '#ff9500'],
  [0.5, '#e95555'],
  [0.75, '#e30613'],      
  [1.0, '#9f040e']
];

const RISK_COLORS: Array<[number, string]> = [
  [0.0, '#ffffff'],
  [0.125, '#ffffcc'],
  [0.25, '#feb24c'],
  [0.375, '#fd8d3c'],
  [0.5, '#fc4e2a'],
  [0.625, '#e31a1c'],
  [0.75, '#b10026'],
  [1.0, '#800026']
];

// Additional color schemes for variety
const RELEVANCE_GREEN_COLORS: Array<[number, string]> = [
  [0.0, '#ffffff'],
  [0.2, '#f0fdf4'],
  [0.4, '#bbf7d0'],
  [0.6, '#4ade80'],
  [0.8, '#15803d'],
  [1.0, '#14532d']
];

const BLUE_WATER_COLORS: Array<[number, string]> = [
  [0.0, '#ffffff'],
  [0.2, '#dbeafe'],
  [0.4, '#93c5fd'],
  [0.6, '#3b82f6'],
  [0.8, '#1d4ed8'],
  [1.0, '#1e3a8a']
];

const PURPLE_GRADIENT_COLORS: Array<[number, string]> = [
  [0.0, '#ffffff'],
  [0.2, '#f3e8ff'],
  [0.4, '#c084fc'],
  [0.6, '#9333ea'],
  [0.8, '#7c3aed'],
  [1.0, '#581c87']
];

// Predefined color schemes
export const PREDEFINED_COLOR_SCHEMES: RasterColorScheme[] = [
  {
    id: SCHEME_IDS.RISK_DEFAULT,
    name: 'risk-default',
    displayName: 'Risk (White → Yellow → Orange → Red)',
    description: 'Standard risk assessment color scheme from white through yellow and orange to dark red',
    colors: createColorStops(RISK_COLORS),
    category: 'risk'
  },
  {
    id: SCHEME_IDS.HAZARD_DEFAULT,
    name: 'hazard-default',
    displayName: 'Hazard (White → Orange → Red)',
    description: 'Hazard assessment colors from white through orange to dark red',
    colors: createColorStops(HAZARD_RISK_COLORS),
    category: 'hazard'
  },
  {
    id: SCHEME_IDS.EXPOSITION_DEFAULT,
    name: 'exposition-default',
    displayName: 'Exposition (White → Light Green → Dark Green)',
    description: 'Exposition layer colors from white through light green to dark green and black',
    colors: createColorStops(EXPOSITION_COLORS),
    category: 'exposition'
  },
  {
    id: SCHEME_IDS.RELEVANCE_DEFAULT,
    name: 'relevance-default',
    displayName: 'Relevance (White → Green)',
    description: 'Relevance layer colors from white through various shades of green',
    colors: createColorStops(RELEVANCE_GREEN_COLORS),
    category: 'relevance'
  },
  {
    id: SCHEME_IDS.ECONOMIC_DEFAULT,
    name: 'economic-default',
    displayName: 'Economic Risk (White → Green → Red → Black)',
    description: 'Economic risk assessment from white through green to red and black',
    colors: createColorStops(ECONOMIC_RISK_COLORS),
    category: 'economic'
  },
  // Additional color schemes for variety
  {
    id: 'blue-water-scheme',
    name: 'blue-water',
    displayName: 'Water Blues (White → Light Blue → Dark Blue)',
    description: 'Blue gradient suitable for water-related data',
    colors: createColorStops(BLUE_WATER_COLORS),
    category: 'custom'
  },
  {
    id: 'purple-gradient-scheme',
    name: 'purple-gradient',
    displayName: 'Purple Gradient (White → Light Purple → Dark Purple)',
    description: 'Purple gradient for general data visualization',
    colors: createColorStops(PURPLE_GRADIENT_COLORS),
    category: 'custom'
  }
];

// Helper functions to get schemes by category
export function getSchemesByCategory(category: string): RasterColorScheme[] {
  return PREDEFINED_COLOR_SCHEMES.filter(scheme => scheme.category === category);
}

export function getSchemeById(id: string): RasterColorScheme | undefined {
  return PREDEFINED_COLOR_SCHEMES.find(scheme => scheme.id === id);
}

export function getDefaultSchemeForLayerType(layerType: string): RasterColorScheme {
  // Determine default scheme based on layer name/type
  if (layerType.includes('risk')) {
    return getSchemeById(SCHEME_IDS.RISK_DEFAULT)!;
  } else if (layerType.includes('hazard')) {
    return getSchemeById(SCHEME_IDS.HAZARD_DEFAULT)!;
  } else if (layerType.includes('exposition')) {
    return getSchemeById(SCHEME_IDS.EXPOSITION_DEFAULT)!;
  } else if (layerType.includes('relevance')) {
    return getSchemeById(SCHEME_IDS.RELEVANCE_DEFAULT)!;
  } else if (layerType.includes('economic')) {
    return getSchemeById(SCHEME_IDS.ECONOMIC_DEFAULT)!;
  }
  
  // Default fallback
  return getSchemeById(SCHEME_IDS.RISK_DEFAULT)!;
}

// Get all available categories
export function getAllCategories(): string[] {
  const categories = new Set(PREDEFINED_COLOR_SCHEMES.map(scheme => scheme.category));
  return Array.from(categories).sort();
} 