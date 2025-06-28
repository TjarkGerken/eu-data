"use client";

import BaseLeafletMap from "./base-leaflet-map";
import { MapLayerMetadata } from "@/lib/map-tile-service";

interface LayerState {
  id: string;
  visible: boolean;
  opacity: number;
  metadata: MapLayerMetadata;
}

interface LeafletMapProps {
  layers: LayerState[];
  centerLat?: number;
  centerLng?: number;
  zoom?: number;
  autoFitBounds?: boolean;
}

export default function LeafletMap({
  layers,
  centerLat = 52.1326,
  centerLng = 5.2913,
  zoom = 8,
  autoFitBounds = false,
}: LeafletMapProps) {
  return (
    <BaseLeafletMap
      layers={layers}
      centerLat={centerLat}
      centerLng={centerLng}
      zoom={zoom}
      autoFitBounds={autoFitBounds}
      enableDataLayers={true}
    />
  );
}
