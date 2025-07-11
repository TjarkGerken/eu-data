export interface TileConfiguration {
  layerName: string;
  sourceFile: string;
  zoomLevels: number[];
  tileSize: number;
  format: "png" | "webp" | "jpg";
}

import { LayerStyleConfig } from "./map-types";

export interface MapLayerMetadata {
  id: string;
  name: string;
  dataType: "raster" | "vector";
  format: "cog" | "mbtiles";
  bounds: [number, number, number, number];
  colorScale: string[];
  valueRange: [number, number];
  description?: string;
  uploadedAt: string;
  fileSize: number;
  styleConfig?: LayerStyleConfig;
  zIndex?: number;
}

export interface LayerUploadResult {
  success: boolean;
  layerId: string;
  fileName: string;
  url: string;
  size?: number;
  originalSize?: number;
  optimizedSize?: number;
  compressionRatio?: number;
  message: string;
}

// Helper function to determine default z-index based on layer characteristics
export function getDefaultZIndex(layer: MapLayerMetadata): number {
  const name = layer.name.toLowerCase();
  const dataType = layer.dataType;

  // Base z-index values - lower numbers render first (behind)
  if (
    name.includes("nuts") ||
    name.includes("administrative") ||
    name.includes("boundary")
  ) {
    return 10; // Administrative boundaries - background
  }

  if (name.includes("exposition") || name.includes("exposure")) {
    return 20; // Exposition layers
  }

  if (name.includes("relevance")) {
    return 30; // Relevance layers
  }

  if (name.includes("hazard")) {
    return 40; // Hazard layers
  }

  if (name.includes("risk")) {
    return 50; // Risk layers - usually on top
  }

  if (name.includes("cluster")) {
    return 60; // Cluster analysis - highest priority
  }

  // Default based on data type if no specific pattern matches
  if (dataType === "vector") {
    return 45; // Vector layers generally on top of raster
  } else {
    return 25; // Raster layers as background/mid-ground
  }
}

export class MapTileService {
  private readonly apiEndpoint: string;

  constructor(apiEndpoint: string = "/api/map-tiles") {
    this.apiEndpoint = apiEndpoint;
  }

  generateTileUrl(layerId: string, zoom: number, x: number, y: number): string {
    return `${this.apiEndpoint}/${layerId}/${zoom}/${x}/${y}.png`;
  }

  async getLayerMetadata(layerId: string): Promise<MapLayerMetadata> {
    const response = await fetch(`${this.apiEndpoint}/layers/${layerId}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch layer metadata: ${response.statusText}`);
    }
    return response.json();
  }

  async getAvailableLayers(): Promise<MapLayerMetadata[]> {
    const response = await fetch(`${this.apiEndpoint}/layers`);
    if (!response.ok) {
      throw new Error(
        `Failed to fetch available layers: ${response.statusText}`,
      );
    }
    const data = await response.json();
    const layers: MapLayerMetadata[] = Array.isArray(data)
      ? data
      : data.layers || [];

    // Concurrently fetch style configurations for all layers
    const layersWithStyles = await Promise.all(
      layers.map(async (layer) => {
        try {
          const styleResponse = await fetch(
            `/api/map-layers/${layer.id}/style`,
          );
          if (styleResponse.ok) {
            const styleConfig = await styleResponse.json();
            // Avoid assigning empty or invalid style configs
            if (styleConfig && Object.keys(styleConfig).length > 0) {
              return { ...layer, styleConfig };
            }
          }
        } catch (error) {
          console.warn(`Could not fetch style for layer ${layer.id}:`, error);
        }
        return layer;
      }),
    );

    // Ensure all layers have z-index values and sort by z-index
    const layersWithZIndex = layersWithStyles.map((layer) => ({
      ...layer,
      zIndex: layer.zIndex ?? getDefaultZIndex(layer),
    }));

    // Sort layers by z-index (ascending - lower values render first)
    return layersWithZIndex.sort((a, b) => (a.zIndex || 0) - (b.zIndex || 0));
  }

  async uploadLayer(
    file: File,
    layerName: string,
    layerType: string,
  ): Promise<LayerUploadResult> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("layerName", layerName);
    formData.append("layerType", layerType);

    const response = await fetch("/api/map-layers/upload", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || "Failed to upload layer");
    }

    return response.json();
  }

  async deleteLayer(layerId: string): Promise<void> {
    const response = await fetch(`/api/map-layers/${layerId}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      throw new Error(`Failed to delete layer: ${response.statusText}`);
    }
  }

  async getVectorLayerData(layerId: string): Promise<unknown> {
    const response = await fetch(`/api/map-data/vector/${layerId}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch vector data: ${response.statusText}`);
    }
    return response.json();
  }

  async updateLayerOrder(layerId: string, zIndex: number): Promise<void> {
    const response = await fetch(`/api/map-layers/${layerId}/order`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ zIndex }),
    });

    if (!response.ok) {
      throw new Error(`Failed to update layer order: ${response.statusText}`);
    }
  }

  async updateLayersOrder(
    layerOrderUpdates: Array<{ id: string; zIndex: number }>,
  ): Promise<void> {
    const response = await fetch(`/api/map-layers/bulk-order`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ updates: layerOrderUpdates }),
    });

    if (!response.ok) {
      throw new Error(`Failed to update layers order: ${response.statusText}`);
    }
  }
}

export const mapTileService = new MapTileService();
