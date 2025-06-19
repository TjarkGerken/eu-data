export interface TileConfiguration {
  layerName: string;
  sourceFile: string;
  zoomLevels: number[];
  tileSize: number;
  format: "png" | "webp" | "jpg";
}

export interface MapLayerMetadata {
  layerName: string;
  scenario: string;
  dataType: "risk" | "hazard" | "exposition" | "relevance";
  bounds: [number, number, number, number];
  colorScale: string[];
  valueRange: [number, number];
}

export class MapTileService {
  private readonly apiEndpoint: string;

  constructor(apiEndpoint: string = "/api/map-tiles") {
    this.apiEndpoint = apiEndpoint;
  }

  generateTileUrl(
    layerName: string,
    zoom: number,
    x: number,
    y: number
  ): string {
    return `${this.apiEndpoint}/${layerName}/${zoom}/${x}/${y}.png`;
  }

  async getLayerMetadata(layerName: string): Promise<MapLayerMetadata> {
    const response = await fetch(`${this.apiEndpoint}/metadata/${layerName}`);
    return response.json();
  }

  async getAvailableLayers(): Promise<MapLayerMetadata[]> {
    const response = await fetch(`${this.apiEndpoint}/layers`);
    return response.json();
  }
}

export const mapTileService = new MapTileService();
