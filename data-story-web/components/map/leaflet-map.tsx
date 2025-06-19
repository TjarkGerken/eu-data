"use client";

import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { MapLayerMetadata } from "@/lib/map-tile-service";

interface LayerState {
  id: string;
  visible: boolean;
  opacity: number;
  metadata: MapLayerMetadata;
}

interface LeafletMapProps {
  layers: LayerState[];
}

const DEFAULT_CENTER: [number, number] = [52.5, 13.4];
const DEFAULT_ZOOM = 6;

export default function LeafletMap({ layers }: LeafletMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const layerGroupRef = useRef<L.LayerGroup | null>(null);
  const vectorLayerGroupRef = useRef<L.LayerGroup | null>(null);

  useEffect(() => {
    if (!mapContainerRef.current) return;

    const map = L.map(mapContainerRef.current).setView(
      DEFAULT_CENTER,
      DEFAULT_ZOOM
    );

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);

    const layerGroup = L.layerGroup().addTo(map);
    const vectorLayerGroup = L.layerGroup().addTo(map);

    mapRef.current = map;
    layerGroupRef.current = layerGroup;
    vectorLayerGroupRef.current = vectorLayerGroup;

    return () => {
      map.remove();
      mapRef.current = null;
      layerGroupRef.current = null;
      vectorLayerGroupRef.current = null;
    };
  }, []);

  useEffect(() => {
    updateMapLayers();
  }, [layers]);

  const updateMapLayers = () => {
    if (
      !mapRef.current ||
      !layerGroupRef.current ||
      !vectorLayerGroupRef.current
    )
      return;

    layerGroupRef.current.clearLayers();
    vectorLayerGroupRef.current.clearLayers();

    const visibleLayers = layers.filter((layer) => layer.visible);

    visibleLayers.forEach((layer) => {
      if (layer.metadata.dataType === "raster") {
        const tileLayer = L.tileLayer(
          `/api/map-tiles/${layer.id}/{z}/{x}/{y}.png`,
          {
            opacity: layer.opacity,
            attribution: `${layer.metadata.name} - ${layer.metadata.dataType}`,
            maxZoom: 18,
            tileSize: 256,
          }
        );
        layerGroupRef.current?.addLayer(tileLayer);
      } else if (layer.metadata.dataType === "vector") {
        loadVectorLayer(layer);
      }
    });

    if (visibleLayers.length > 0) {
      const bounds = visibleLayers[0].metadata.bounds;
      const leafletBounds = L.latLngBounds([
        [bounds[1], bounds[0]],
        [bounds[3], bounds[2]],
      ]);
      mapRef.current.fitBounds(leafletBounds, { padding: [20, 20] });
    }
  };

  const loadVectorLayer = async (layer: LayerState) => {
    if (!vectorLayerGroupRef.current) return;

    try {
      const response = await fetch(`/api/map-data/vector/${layer.id}`);
      if (response.ok) {
        const vectorData = await response.json();

        L.geoJSON(vectorData, {
          style: {
            fillColor: layer.metadata.colorScale[1] || "#ff0000",
            weight: 2,
            opacity: layer.opacity,
            color: "#ffffff",
            fillOpacity: layer.opacity * 0.6,
          },
          onEachFeature: (feature, layerInstance) => {
            if (feature.properties) {
              const popupContent = Object.entries(feature.properties)
                .map(([key, value]) => `<strong>${key}:</strong> ${value}`)
                .join("<br>");

              layerInstance.bindPopup(`
                <div class="vector-popup">
                  <h4>${layer.metadata.name}</h4>
                  ${popupContent}
                </div>
              `);
            }
          },
        }).addTo(vectorLayerGroupRef.current);
      }
    } catch (error) {
      console.error("Failed to load vector layer:", error);
    }
  };

  return (
    <div
      ref={mapContainerRef}
      className="w-full h-full relative"
      style={{ minHeight: "400px" }}
    />
  );
}
