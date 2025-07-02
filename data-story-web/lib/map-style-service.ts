/**
 * Map Style Service - Utility functions for managing layer style configurations
 */

import { MapLayerMetadata } from './map-tile-service';
import { LayerStyleConfig } from './map-types';

/**
 * Load style configuration for a single layer
 */
export async function loadLayerStyleConfig(layerId: string): Promise<LayerStyleConfig | null> {
  try {
    const response = await fetch(`/api/map-layers/${layerId}/style`);
    if (response.ok) {
      return await response.json();
    }
    return null;
  } catch {
    console.log(`No style config found for layer ${layerId}`);
    return null;
  }
}

/**
 * Save style configuration for a layer
 */
export async function saveLayerStyleConfig(layerId: string, styleConfig: LayerStyleConfig): Promise<boolean> {
  try {
    const response = await fetch(`/api/map-layers/${layerId}/style`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(styleConfig),
    });

    return response.ok;
  } catch (error) {
    console.error('Error saving layer style:', error);
    return false;
  }
}

/**
 * Load style configurations for multiple layers
 */
export async function loadLayersWithStyleConfigs(layers: MapLayerMetadata[]): Promise<MapLayerMetadata[]> {
  // Guard against undefined or null layers array
  if (!layers || !Array.isArray(layers)) {
    return [];
  }

  const layersWithStyles = await Promise.all(
    layers.map(async (layer) => {
      const styleConfig = await loadLayerStyleConfig(layer.id);
      return styleConfig ? { ...layer, styleConfig } : layer;
    })
  );
  
  return layersWithStyles;
}

/**
 * Delete style configuration for a layer
 */
export async function deleteLayerStyleConfig(layerId: string): Promise<boolean> {
  try {
    const response = await fetch(`/api/map-layers/${layerId}/style`, {
      method: 'DELETE',
    });

    return response.ok;
  } catch (error) {
    console.error('Error deleting layer style:', error);
    return false;
  }
} 
