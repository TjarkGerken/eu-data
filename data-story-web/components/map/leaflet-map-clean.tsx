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

  // Add custom CSS for popup styling
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const existingStyle = document.getElementById('leaflet-custom-popup-style');
      if (!existingStyle) {
        const style = document.createElement('style');
        style.id = 'leaflet-custom-popup-style';
        style.textContent = `
          .custom-popup .leaflet-popup-content-wrapper {
            padding: 8px 12px;
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
            border: none;
            background: white;
          }
          .custom-popup .leaflet-popup-content {
            margin: 0;
            line-height: 1.4;
          }
          .custom-popup .leaflet-popup-tip {
            background: white;
          }
        `;
        document.head.appendChild(style);
      }
    }
  }, []);

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
        });        if (vectorData && vectorData.features && vectorData.features.length > 0) {
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
              if (feature.properties) {                const formatNumber = (value: number): string => {
                  if (typeof value !== 'number' || isNaN(value)) return value?.toString() || '';
                  return new Intl.NumberFormat('de-DE', {
                    minimumFractionDigits: 0,
                    maximumFractionDigits: 3
                  }).format(value);
                };const formatPropertyValue = (key: string, value: unknown): string => {
                  if (typeof value === 'number') {
                    // Convert square meters to square kilometers for area fields
                    if (key.toLowerCase().includes('area') && key.toLowerCase().includes('square') && key.toLowerCase().includes('meter')) {
                      const squareKm = value / 1000000; // Convert m² to km²
                      return formatNumber(squareKm) + ' km²';
                    }
                    return formatNumber(value);
                  }
                  if (typeof value === 'string' && !isNaN(Number(value))) {
                    const numValue = Number(value);
                    // Convert square meters to square kilometers for area fields
                    if (key.toLowerCase().includes('area') && key.toLowerCase().includes('square') && key.toLowerCase().includes('meter')) {
                      const squareKm = numValue / 1000000; // Convert m² to km²
                      return formatNumber(squareKm) + ' km²';
                    }
                    return formatNumber(numValue);
                  }
                  return value?.toString() || '';
                };                const formatPropertyName = (key: string): string => {
                  let formattedName = key
                    .replace(/_/g, ' ')
                    .replace(/([A-Z])/g, ' $1')
                    .split(' ')
                    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
                    .join(' ');
                  
                  // Replace "Square Meters" with "Square Kilometers" for area fields
                  if (formattedName.toLowerCase().includes('square meters')) {
                    formattedName = formattedName.replace(/Square Meters/gi, 'Square Kilometers');
                  }
                  
                  return formattedName;
                };                const propertyEntries = Object.entries(feature.properties)
                  .filter(([, value]) => value !== null && value !== undefined && value !== '')
                  .filter(([key]) => !key.toLowerCase().includes('pixel_count') && !key.toLowerCase().includes('risk_density') && !key.toLowerCase().includes('cluster_id'))
                  .map(([key, value]) => {
                    const formattedKey = formatPropertyName(key);
                    const formattedValue = formatPropertyValue(key, value);
                    return { key: formattedKey, value: formattedValue };
                  });

                const popupContent = `
                  <div style="
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    max-width: 300px;
                    line-height: 1.4;
                  ">                    <div style="
                      background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
                      color: white;
                      padding: 12px 16px;
                      margin: -8px -12px 12px -12px;
                      border-radius: 8px 8px 0 0;
                      font-weight: 600;
                      font-size: 16px;
                      text-align: center;
                      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    ">
                      ${feature.properties.name || feature.properties.cluster_id ? 
                        `Cluster ID: ${feature.properties.cluster_id || feature.properties.name}` : 
                        'Feature Details'}
                    </div>
                    <div style="padding: 4px 0;">
                      ${propertyEntries.map(({ key, value }) => `
                        <div style="
                          display: flex;
                          justify-content: space-between;
                          align-items: center;
                          padding: 8px 12px;
                          margin: 2px 0;                          background: ${key.toLowerCase().includes('risk') ? '#fef2f2' : 
                                     key.toLowerCase().includes('area') ? '#f0fdf4' :
                                     key.toLowerCase().includes('density') ? '#f7fee7' : '#f9fafb'};
                          border-left: 3px solid ${key.toLowerCase().includes('risk') ? '#ef4444' : 
                                                  key.toLowerCase().includes('area') ? '#22c55e' :
                                                  key.toLowerCase().includes('density') ? '#84cc16' : '#6b7280'};
                          border-radius: 4px;
                          font-size: 13px;
                        ">
                          <span style="
                            font-weight: 500;
                            color: #374151;
                            margin-right: 12px;
                            flex: 1;
                          ">${key}:</span>
                          <span style="
                            font-weight: 600;
                            color: #111827;
                            font-family: 'Courier New', monospace;
                            background: white;
                            padding: 2px 6px;
                            border-radius: 3px;
                            border: 1px solid #e5e7eb;
                          ">${value}</span>
                        </div>
                      `).join('')}
                    </div>
                  </div>
                `;

                layer.bindPopup(popupContent, {
                  maxWidth: 350,
                  className: 'custom-popup'
                });
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
