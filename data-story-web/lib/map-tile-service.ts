export interface TileConfiguration {
  layerName: string;
  sourceFile: string;
  zoomLevels: number[];
  tileSize: number;
  format: "png" | "webp" | "jpg";
}

export interface MapLayerMetadata {
  id: string;
  name: string;
  dataType: "raster" | "vector";
  format: "tiff" | "geojson" | "geopackage";
  bounds: [number, number, number, number];
  colorScale: string[];
  valueRange: [number, number];
  description?: string;
  uploadedAt: string;
  fileSize: number;
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
        `Failed to fetch available layers: ${response.statusText}`
      );
    }
    const data = await response.json();
    return Array.isArray(data) ? data : data.layers || [];
  }

  async uploadLayer(
    file: File,
    layerName: string,
    layerType: string
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

  async getVectorLayerData(layerId: string): Promise<any> {
    const response = await fetch(`/api/map-data/vector/${layerId}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch vector data: ${response.statusText}`);
    }
    return response.json();
  }
}

export const mapTileService = new MapTileService();
