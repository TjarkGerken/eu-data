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
  }, []);

  // Update map view when center/zoom props change
  useEffect(() => {
    if (mapRef.current) {
      console.log("Updating map view to:", { centerLat, centerLng, zoom });
      mapRef.current.setView([centerLat, centerLng], zoom);
    }
  }, [centerLat, centerLng, zoom]);

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

    if (autoFitBounds && visibleLayers.length > 0) {
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
            style: (feature) => {
              // Use the improved color scale, but fallback to a visible color
              const fillColor = layer.metadata.colorScale[1] || "#ff6b6b";
              return {
                fillColor: fillColor,
                weight: 2,
                opacity: 1,
                color: "#000000",
                fillOpacity: 0.7,
              };
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
          });
          
          geoJSONLayer.addTo(vectorLayerGroupRef.current);
          console.log("GeoJSON layer added to map, bounds:", geoJSONLayer.getBounds());
          
          // Only fit to bounds if autoFitBounds is enabled
          if (autoFitBounds && mapRef.current && geoJSONLayer.getBounds().isValid()) {
            console.log("Fitting to bounds because autoFitBounds is enabled");
            mapRef.current.fitBounds(geoJSONLayer.getBounds(), { padding: [20, 20] });
          } else {
            console.log("Not fitting to bounds - autoFitBounds:", autoFitBounds);
          }
        } else {
          console.warn("No features found in vector data for layer:", layer.id);
        }
      } else {
        console.error("Failed to load vector layer:", response.status, response.statusText);
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
