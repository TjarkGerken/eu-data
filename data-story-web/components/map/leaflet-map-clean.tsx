"use client";

import { useEffect, useRef, useCallback } from "react";
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
  autoFitBounds = false 
}: LeafletMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const layerGroupRef = useRef<L.LayerGroup | null>(null);
  const vectorLayerGroupRef = useRef<L.LayerGroup | null>(null);

  useEffect(() => {
    if (!mapContainerRef.current) return;

    console.log("Initializing map with:", { centerLat, centerLng, zoom });

    const map = L.map(mapContainerRef.current).setView(
      [centerLat, centerLng],
      zoom
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
  }, [centerLat, centerLng, zoom]);

  // Update map view when center/zoom props change
  useEffect(() => {
    if (mapRef.current) {
      console.log("Updating map view to:", { centerLat, centerLng, zoom });
      mapRef.current.setView([centerLat, centerLng], zoom);
    }
  }, [centerLat, centerLng, zoom]);

  const loadVectorLayer = useCallback(async (layer: LayerState) => {
    if (!vectorLayerGroupRef.current) return;

    try {
      console.log("Loading vector layer:", layer.id, layer.metadata);
      const response = await fetch(`/api/map-data/vector/${layer.id}`);
      
      if (response.ok) {
        const vectorData = await response.json();
        console.log("Vector data loaded:", {
          layerId: layer.id,
          featureCount: vectorData?.features?.length || 0,
          type: vectorData?.type,
          firstFeature: vectorData?.features?.[0]
        });

        if (vectorData && vectorData.features && vectorData.features.length > 0) {
          const geoJSONLayer = L.geoJSON(vectorData, {
            style: () => {
              // Use the improved color scale, but fallback to a visible color
              const fillColor = layer.metadata.colorScale[1] || "#ff6b6b";
              return {
                fillColor: fillColor,
                weight: 2,
                color: "#ffffff",
                opacity: layer.opacity,
                fillOpacity: layer.opacity * 0.6,
              };
            },
            onEachFeature: (feature, layer) => {
              // Add popup or tooltip functionality here if needed
              if (feature.properties) {
                layer.bindPopup(`
                  <div>
                    <h3 class="font-bold">${feature.properties.name || 'Feature'}</h3>
                    <pre class="text-xs bg-gray-100 p-2 rounded mt-2">${JSON.stringify(feature.properties, null, 2)}</pre>
                  </div>
                `);
              }
            }
          });
          vectorLayerGroupRef.current.addLayer(geoJSONLayer);
        } else {
          console.warn("No valid features found in vector data");
        }
      } else {
        console.error("Failed to load vector layer:", response.status, response.statusText);
      }
    } catch (error) {
      console.error("Failed to load vector layer:", error);
    }
  }, []);

  const updateMapLayers = useCallback(() => {
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

    if (autoFitBounds && visibleLayers.length > 0) {
      const bounds = visibleLayers[0].metadata.bounds;
      const leafletBounds = L.latLngBounds([
        [bounds[1], bounds[0]],
        [bounds[3], bounds[2]],
      ]);
      mapRef.current.fitBounds(leafletBounds, { padding: [20, 20] });
    }
  }, [layers, autoFitBounds, loadVectorLayer]);

  useEffect(() => {
    updateMapLayers();
  }, [updateMapLayers]);

  return (
    <div
      ref={mapContainerRef}
      className="w-full h-full relative"
      style={{ minHeight: "400px" }}
    />
  );
}
