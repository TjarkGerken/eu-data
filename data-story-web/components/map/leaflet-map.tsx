"use client";

import { useEffect, useRef, useCallback } from "react";
import "leaflet/dist/leaflet.css";
import "leaflet-defaulticon-compatibility/dist/leaflet-defaulticon-compatibility.css";
import "leaflet-defaulticon-compatibility";
// @ts-expect-error - georaster library doesn't have TypeScript definitions
import parseGeoraster from "georaster";
// @ts-expect-error - georaster-layer-for-leaflet library doesn't have TypeScript definitions
import GeoRasterLayer from "georaster-layer-for-leaflet";
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

// Dynamic imports to avoid SSR issues
// eslint-disable-next-line @typescript-eslint/no-require-imports
const L = typeof window !== "undefined" ? require("leaflet") : null;

// Import VectorGrid correctly - it extends L when required
let VectorGrid: typeof L.VectorGrid | null = null;
if (typeof window !== "undefined") {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  require("leaflet.vectorgrid");
  VectorGrid = L?.VectorGrid;
}

export default function LeafletMap({
  layers,
  centerLat = 52.1326,
  centerLng = 5.2913,
  zoom = 8,
  autoFitBounds = false,
}: LeafletMapProps) {
  const mapRef = useRef<L.Map | null>(null);
  const layerGroupRef = useRef<L.LayerGroup | null>(null);
  const vectorLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const cogLayerGroupRef = useRef<L.LayerGroup | null>(null);

  // Add custom CSS for popup styling
  useEffect(() => {
    if (typeof window !== "undefined") {
      const existingStyle = document.getElementById(
        "leaflet-custom-popup-style"
      );
      if (!existingStyle) {
        const style = document.createElement("style");
        style.id = "leaflet-custom-popup-style";
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
    if (typeof window !== "undefined" && L && !mapRef.current) {
      const map = L.map("leaflet-map", {
        center: [centerLat, centerLng],
        zoom: zoom,
        zoomControl: true,
      });

      L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
        attribution:
          "Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community",
      }).addTo(map);

      // Create layer groups for different data types
      const layerGroup = L.layerGroup().addTo(map);
      const vectorLayerGroup = L.layerGroup().addTo(map);
      const cogLayerGroup = L.layerGroup().addTo(map);

      mapRef.current = map;
      layerGroupRef.current = layerGroup;
      vectorLayerGroupRef.current = vectorLayerGroup;
      cogLayerGroupRef.current = cogLayerGroup;

      return () => {
        if (mapRef.current) {
          mapRef.current.remove();
          mapRef.current = null;
        }
      };
    }
  }, [centerLat, centerLng, zoom]);

  useEffect(() => {
    if (mapRef.current) {
      mapRef.current.setView([centerLat, centerLng], zoom);
    }
  }, [centerLat, centerLng, zoom]);

  // Function to get actual layer names from vector tile metadata
  const getActualLayerName = useCallback(
    async (layerId: string): Promise<string> => {
      try {
        const response = await fetch(`/api/map-data/vector/${layerId}`);
        if (response.ok) {
          const data = await response.json();

          // Extract layer name from the metadata JSON
          if (
            data.properties &&
            data.properties.metadata &&
            data.properties.metadata.json
          ) {
            const parsedJson = JSON.parse(data.properties.metadata.json);
            if (
              parsedJson.vector_layers &&
              parsedJson.vector_layers.length > 0
            ) {
              const actualLayerName = parsedJson.vector_layers[0].id;
              console.log(
                `Found actual layer name: ${actualLayerName} for layer ID: ${layerId}`
              );
              return actualLayerName;
            }
          }
        }
      } catch (error) {
        console.warn(`Could not fetch metadata for layer ${layerId}:`, error);
      }

      // Return the layer ID as fallback
      return layerId;
    },
    []
  );

  // Load vector layers with popups for GeoJSON data
  const loadVectorLayer = useCallback(async (layer: LayerState) => {
    if (!vectorLayerGroupRef.current || !L) return;

    try {
      console.log("Loading vector layer:", layer.id, layer.metadata);
      const response = await fetch(`/api/map-data/vector/${layer.id}`);

      if (response.ok) {
        const vectorData = await response.json();
        console.log("Vector data loaded:", {
          layerId: layer.id,
          featureCount: vectorData?.features?.length || 0,
          type: vectorData?.type,
        });
        
        if (vectorData && vectorData.features && vectorData.features.length > 0) {
          const geoJSONLayer = L.geoJSON(vectorData, {
            style: () => {
              const fillColor = layer.metadata.colorScale[1] || "#ff6b6b";
              return {
                fillColor: fillColor,
                weight: 2,
                color: "#ffffff",
                opacity: layer.opacity,
                fillOpacity: Math.max(layer.opacity * 0.7, 0.3),
              };
            },
            onEachFeature: (feature: GeoJSON.Feature, geoLayer: L.Layer) => {
              if (feature.properties) {
                const formatNumber = (value: number): string => {
                  if (typeof value !== "number" || isNaN(value))
                    return value?.toString() || "";
                  return new Intl.NumberFormat("de-DE", {
                    minimumFractionDigits: 0,
                    maximumFractionDigits: 3,
                  }).format(value);
                };
                
                const formatPropertyValue = (key: string, value: unknown): string => {
                  if (typeof value === "number") {
                    if (
                      key.toLowerCase().includes("area") &&
                      key.toLowerCase().includes("square") &&
                      key.toLowerCase().includes("meter")
                    ) {
                      const squareKm = value / 1000000;
                      return formatNumber(squareKm) + " km²";
                    }
                    return formatNumber(value);
                  }
                  if (typeof value === "string" && !isNaN(Number(value))) {
                    const numValue = Number(value);
                    if (
                      key.toLowerCase().includes("area") &&
                      key.toLowerCase().includes("square") &&
                      key.toLowerCase().includes("meter")
                    ) {
                      const squareKm = numValue / 1000000;
                      return formatNumber(squareKm) + " km²";
                    }
                    return formatNumber(numValue);
                  }
                  return value?.toString() || "";
                };
                
                const formatPropertyName = (key: string): string => {
                  let formattedName = key
                    .replace(/_/g, " ")
                    .replace(/([A-Z])/g, " $1")
                    .split(" ")
                    .map(
                      (word) =>
                        word.charAt(0).toUpperCase() +
                        word.slice(1).toLowerCase()
                    )
                    .join(" ");

                  if (formattedName.toLowerCase().includes("square meters")) {
                    formattedName = formattedName.replace(
                      /Square Meters/gi,
                      "Square Kilometers"
                    );
                  }

                  return formattedName;
                };
                
                const propertyEntries = Object.entries(feature.properties)
                  .filter(
                    ([, value]) =>
                      value !== null && value !== undefined && value !== ""
                  )
                  .filter(
                    ([key]) =>
                      !key.toLowerCase().includes("pixel_count") &&
                      !key.toLowerCase().includes("risk_density") &&
                      !key.toLowerCase().includes("cluster_id")
                  )
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
                  ">
                    <div style="
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
                      ${feature.properties.name || feature.properties.cluster_id
                          ? `Cluster ID: ${feature.properties.cluster_id || feature.properties.name}`
                          : "Feature Details"
                      }
                    </div>
                    <div style="padding: 4px 0;">
                      ${propertyEntries
                        .map(
                          ({ key, value }) => `
                        <div style="
                          display: flex;
                          justify-content: space-between;
                          align-items: center;
                          padding: 8px 12px;
                          margin: 2px 0;
                          background: ${key.toLowerCase().includes("risk")
                              ? "#fef2f2"
                              : key.toLowerCase().includes("area")
                              ? "#f0fdf4"
                              : key.toLowerCase().includes("density")
                              ? "#f7fee7"
                              : "#f9fafb"
                          };
                          border-left: 3px solid ${key.toLowerCase().includes("risk")
                              ? "#ef4444"
                              : key.toLowerCase().includes("area")
                              ? "#22c55e"
                              : key.toLowerCase().includes("density")
                              ? "#84cc16"
                              : "#6b7280"
                          };
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
                      `
                        )
                        .join("")}
                    </div>
                  </div>
                `;

                geoLayer.bindPopup(popupContent, {
                  maxWidth: 350,
                  className: "custom-popup",
                });
              }
            },
          });
          vectorLayerGroupRef.current.addLayer(geoJSONLayer);
        } else {
          console.warn("No valid features found in vector data");
        }
      } else {
        console.error(
          "Failed to load vector layer:",
          response.status,
          response.statusText
        );
      }
    } catch (error) {
      console.error("Failed to load vector layer:", error);
    }
  }, []);

  // Load COG layers using georaster
  const loadCogLayer = useCallback(async (layer: LayerState) => {
    if (!cogLayerGroupRef.current) return;

    try {
      // Fetch the COG file from our API
      const response = await fetch(`/api/map-data/cog/${layer.id}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch COG: ${response.statusText}`);
      }

      const arrayBuffer = await response.arrayBuffer();
      const georaster = await parseGeoraster(arrayBuffer);

      // Create a custom color scale based on layer metadata
      const colorScale = layer.metadata.colorScale;
      const valueRange = layer.metadata.valueRange;

      const cogLayer = new GeoRasterLayer({
        georaster: georaster,
        opacity: layer.opacity || 0.8,
        pixelValuesToColorFn: function (pixelValues: number[]) {
          const pixelValue = pixelValues[0];
          if (
            pixelValue === georaster.noDataValue ||
            pixelValue === null ||
            pixelValue === undefined ||
            pixelValue === 0
          ) {
            return null; // transparent for no data or zero values
          }

          // Check if this is a risk layer based on the layer ID
          const isRiskLayer =
            layer.id.includes("risk") ||
            layer.metadata.name.toLowerCase().includes("risk");

          if (isRiskLayer) {
            // Custom risk gradient: transparent -> orange -> red -> dark red
            const normalized =
              (pixelValue - valueRange[0]) / (valueRange[1] - valueRange[0]);
            const clampedNormalized = Math.max(0, Math.min(1, normalized));

            if (clampedNormalized <= 0.33) {
              // Low risk: transparent to orange
              const t = clampedNormalized / 0.33;
              const r = Math.round(255 * t);
              const g = Math.round(165 * t);
              const b = 0;
              const a = t * 0.8; // Start with some transparency
              return `rgba(${r}, ${g}, ${b}, ${a})`;
            } else if (clampedNormalized <= 0.66) {
              // Medium risk: orange to red
              const t = (clampedNormalized - 0.33) / 0.33;
              const r = 255;
              const g = Math.round(165 * (1 - t));
              const b = 0;
              const a = 0.8 + t * 0.15; // Increase opacity
              return `rgba(${r}, ${g}, ${b}, ${a})`;
            } else {
              // High risk: red to dark red
              const t = (clampedNormalized - 0.66) / 0.34;
              const r = Math.round(255 * (1 - t * 0.4)); // Darken red
              const g = 0;
              const b = 0;
              const a = 0.95; // High opacity for maximum visibility
              return `rgba(${r}, ${g}, ${b}, ${a})`;
            }
          } else {
            // Use existing color scale for non-risk layers
            const normalized =
              (pixelValue - valueRange[0]) / (valueRange[1] - valueRange[0]);
            const clampedNormalized = Math.max(0, Math.min(1, normalized));

            const colorIndex = Math.floor(
              clampedNormalized * (colorScale.length - 1)
            );
            const color =
              colorScale[colorIndex] || colorScale[colorScale.length - 1];

            return color;
          }
        },
        resolution: 256,
      });

      cogLayerGroupRef.current.addLayer(cogLayer);
    } catch (error) {
      console.error(`Failed to load COG layer ${layer.id}:`, error);
    }
  }, []);

  const updateMapLayers = useCallback(() => {
    if (
      !mapRef.current ||
      !layerGroupRef.current ||
      !vectorLayerGroupRef.current ||
      !cogLayerGroupRef.current
    )
      return;

    // Clear all layer groups
    layerGroupRef.current.clearLayers();
    vectorLayerGroupRef.current.clearLayers();
    cogLayerGroupRef.current.clearLayers();

    const visibleLayers = layers.filter((layer) => layer.visible);

    visibleLayers.forEach((layer) => {
      if (layer.metadata.dataType === "vector") {
        // Vector tiles from MBTiles
        if (layer.metadata.format === "mbtiles") {
          if (L && VectorGrid) {
            // Get the actual layer name dynamically
            getActualLayerName(layer.id)
              .then((actualLayerName) => {
                const vectorTileLayer = L.vectorGrid.protobuf(
                  `/api/map-data/vector/${layer.id}/{z}/{x}/{y}`,
                  {
                    rendererFactory: L.canvas.tile,
                    vectorTileLayerStyles: {
                      // Use the actual layer name from the MBTiles file
                      [actualLayerName]: {
                        weight: 2,
                        color: "#1e40af",
                        opacity: 0.9,
                        fillColor: "#1e3a8a",
                        fillOpacity: Math.max(layer.opacity * 0.7, 0.3),
                      },
                      // Also add a fallback with the converted layer ID
                      [layer.id]: {
                        weight: 2,
                        color: "#1e40af",
                        opacity: 0.9,
                        fillColor: "#1e3a8a",
                        fillOpacity: Math.max(layer.opacity * 0.7, 0.3),
                      },
                    },
                    maxZoom: 18,
                    pane: "overlayPane",
                    attribution: "EU Climate Risk Data",
                  }
                );

                vectorLayerGroupRef.current?.addLayer(vectorTileLayer);
              })
              .catch((error) => {
                console.error(
                  `Failed to get layer name for ${layer.id}:`,
                  error
                );
                // Fallback to basic rendering without dynamic name resolution
                const vectorTileLayer = L.vectorGrid.protobuf(
                  `/api/map-data/vector/${layer.id}/{z}/{x}/{y}`,
                  {
                    rendererFactory: L.canvas.tile,
                    vectorTileLayerStyles: {
                      [layer.id]: {
                        weight: 2,
                        color: "#1e40af",
                        opacity: 0.9,
                        fillColor: "#1e3a8a",
                        fillOpacity: Math.max(layer.opacity * 0.7, 0.3),
                      },
                    },
                    maxZoom: 18,
                    pane: "overlayPane",
                    attribution: "EU Climate Risk Data",
                  }
                );
                vectorLayerGroupRef.current?.addLayer(vectorTileLayer);
              });
          } else {
            console.warn("VectorGrid not available - skipping vector layer");
          }
        } else {
          // Try loading as GeoJSON vector data
          loadVectorLayer(layer);
        }
      } else if (layer.metadata.dataType === "raster") {
        if (layer.metadata.format === "mbtiles") {
          // Raster tiles from MBTiles
          const tileLayer = L.tileLayer(
            `/api/map-tiles/${layer.id}/{z}/{x}/{y}.png`,
            {
              opacity: layer.opacity || 0.8,
              maxZoom: 18,
            }
          );
          layerGroupRef.current?.addLayer(tileLayer);
        } else if (layer.metadata.format === "cog") {
          // COG files using georaster
          loadCogLayer(layer);
        }
      }
    });

    // Auto-fit bounds if enabled
    if (autoFitBounds && visibleLayers.length > 0) {
      const allBounds = visibleLayers.map((layer) => layer.metadata.bounds);
      const combinedBounds = allBounds.reduce((acc, bounds) => {
        const [minLng, minLat, maxLng, maxLat] = bounds;
        return [
          Math.min(acc[0], minLng),
          Math.min(acc[1], minLat),
          Math.max(acc[2], maxLng),
          Math.max(acc[3], maxLat),
        ];
      });

      const [[minLng, minLat, maxLng, maxLat]] = [combinedBounds];
      mapRef.current.fitBounds([
        [minLat, minLng],
        [maxLat, maxLng],
      ]);
    }
  }, [layers, autoFitBounds, loadCogLayer, getActualLayerName, loadVectorLayer]);

  useEffect(() => {
    updateMapLayers();
  }, [updateMapLayers]);

  return (
    <div
      id="leaflet-map"
      className="w-full h-full relative"
      style={{ minHeight: "400px" }}
    />
  );
}
