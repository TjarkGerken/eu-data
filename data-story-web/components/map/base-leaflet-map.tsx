"use client";

import { useEffect, useRef, useCallback, useMemo } from "react";
import "leaflet/dist/leaflet.css";
import "leaflet-defaulticon-compatibility/dist/leaflet-defaulticon-compatibility.css";
import "leaflet-defaulticon-compatibility";
import { MapLayerMetadata } from "@/lib/map-tile-service";
import type { LayerStyleConfig } from "@/lib/map-types";

// Minimal interface for georaster object (library doesn't provide types)
interface GeorasterObject {
  noDataValue: number | null;
  [key: string]: any; // eslint-disable-line @typescript-eslint/no-explicit-any
}

export interface TileLayerConfig {
  url: string;
  attribution: string;
  maxZoom?: number;
  opacity?: number;
}

import { createLeafletColorFunction } from '@/lib/color-schemes';

interface LayerState {
  id: string;
  visible: boolean;
  opacity: number;
  metadata: MapLayerMetadata;
}

interface BaseLeafletMapProps {
  layers?: LayerState[];
  centerLat?: number;
  centerLng?: number;
  zoom?: number;
  autoFitBounds?: boolean;
  baseTileLayer?: TileLayerConfig;
  overlayTileLayers?: TileLayerConfig[];
  customPopupStyle?: string;
  enableDataLayers?: boolean;
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

export default function BaseLeafletMap({
  layers = [],
  centerLat = 52.1326,
  centerLng = 5.2913,
  zoom = 8,
  autoFitBounds = false,
  baseTileLayer = {
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attribution:
      "Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community",
    maxZoom: 18,
  },
  overlayTileLayers = [],
  customPopupStyle = "climate-popup",
  enableDataLayers = true,
}: BaseLeafletMapProps) {
  // Generate unique map ID to avoid conflicts between multiple map instances
  const mapId = useMemo(
    () => `leaflet-map-${Math.random().toString(36).substr(2, 9)}`,
    []
  );

  const mapRef = useRef<L.Map | null>(null);
  const layerGroupRef = useRef<L.LayerGroup | null>(null);
  const vectorLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const cogLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const overlayLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const loadedLayersRef = useRef<
    Map<
      string,
      {
        layer: L.Layer;
        opacity: number;
        visible: boolean;
        isCogLayer?: boolean;
        styleConfig?: LayerStyleConfig;
      }
    >
  >(new Map());
  const dataCacheRef = useRef<
    Map<
      string,
      {
        data: ArrayBuffer | GeoJSON.FeatureCollection | string;
        timestamp: number;
        type: "cog" | "vector" | "raster";
      }
    >
  >(new Map());
  const georasterCacheRef = useRef<Map<string, GeorasterObject>>(new Map());

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
          .climate-popup .leaflet-popup-content-wrapper {
            padding: 8px 12px;
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
            border: none;
            background: white;
          }
          .climate-popup .leaflet-popup-content {
            margin: 0;
            line-height: 1.4;
          }
          .climate-popup .leaflet-popup-tip {
            background: white;
          }
          .maritime-popup .leaflet-popup-content-wrapper {
            padding: 8px 12px;
            border-radius: 8px;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
            border: 2px solid #1e40af;
            background: #f8fafc;
          }
          .maritime-popup .leaflet-popup-content {
            margin: 0;
            line-height: 1.4;
            color: #1e40af;
          }
          .maritime-popup .leaflet-popup-tip {
            background: #f8fafc;
            border: 2px solid #1e40af;
          }
        `;
        document.head.appendChild(style);
      }
    }
  }, []);

  useEffect(() => {
    if (typeof window !== "undefined" && L && !mapRef.current) {
      const mapContainer = document.getElementById(mapId);
      if (!mapContainer) {
        console.warn(`Map container with ID ${mapId} not found`);
        return;
      }

      // Clean up any existing map instance on this container
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      if ((mapContainer as any)._leaflet_id) {
        try {
          // Remove existing leaflet instance
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          delete (mapContainer as any)._leaflet_id;
        } catch (error) {
          console.warn("Error cleaning up existing map container:", error);
        }
      }

      const map = L.map(mapId, {
        center: [centerLat, centerLng],
        zoom: zoom,
        zoomControl: true,
      });

      // Add base tile layer
      L.tileLayer(baseTileLayer.url, {
        attribution: baseTileLayer.attribution,
        maxZoom: baseTileLayer.maxZoom || 18,
        opacity: baseTileLayer.opacity || 1,
      }).addTo(map);

      // Create layer groups for different data types
      const layerGroup = L.layerGroup().addTo(map);
      const vectorLayerGroup = L.layerGroup().addTo(map);
      const cogLayerGroup = L.layerGroup().addTo(map);
      const overlayLayerGroup = L.layerGroup().addTo(map);

      // Add overlay tile layers (e.g., OpenSeaMap, OpenRailwayMap)
      overlayTileLayers.forEach((tileConfig) => {
        const overlayLayer = L.tileLayer(tileConfig.url, {
          attribution: tileConfig.attribution,
          maxZoom: tileConfig.maxZoom || 18,
          opacity: tileConfig.opacity || 0.8,
        });
        overlayLayerGroup.addLayer(overlayLayer);
      });

      mapRef.current = map;
      layerGroupRef.current = layerGroup;
      vectorLayerGroupRef.current = vectorLayerGroup;
      cogLayerGroupRef.current = cogLayerGroup;
      overlayLayerGroupRef.current = overlayLayerGroup;
    }

    const currentLoadedLayers = loadedLayersRef.current;
    // Cleanup function
    return () => {
      if (mapRef.current) {
        try {
          mapRef.current.remove();
        } catch (error) {
          console.warn("Error removing map:", error);
        }
        mapRef.current = null;
        layerGroupRef.current = null;
        vectorLayerGroupRef.current = null;
        cogLayerGroupRef.current = null;
        overlayLayerGroupRef.current = null;
        currentLoadedLayers.clear();
      }
    };
  }, [mapId, centerLat, centerLng, zoom, baseTileLayer, overlayTileLayers]);

  // Separate effect for updating map view when coordinates/zoom change
  useEffect(() => {
    if (mapRef.current) {
      try {
        mapRef.current.setView([centerLat, centerLng], zoom);
      } catch (error) {
        console.warn("Error updating map view:", error);
      }
    }
  }, [centerLat, centerLng, zoom]);

  // Function to get actual layer names from vector tile metadata
  const getActualLayerName = useCallback(
    async (layerId: string): Promise<string> => {
      try {
        const response = await fetch(`/api/map-data/vector/${layerId}`);
        if (response.ok) {
          const data = await response.json();

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
              return actualLayerName;
            }
          }
        }
      } catch (error) {
        console.warn(`Could not fetch metadata for layer ${layerId}:`, error);
      }

      return layerId;
    },
    []
  );

  // Load vector layers with popups for GeoJSON data
  const loadVectorLayer = useCallback(
    async (layer: LayerState, storeReference: boolean = true) => {
      if (!vectorLayerGroupRef.current || !L || !enableDataLayers) return;

      try {
        const cached = dataCacheRef.current.get(layer.id);
        let vectorData;

        if (cached && cached.type === "vector") {
          vectorData = cached.data as GeoJSON.FeatureCollection;
        } else {
          const response = await fetch(`/api/map-data/vector/${layer.id}`);

          if (response.ok) {
            vectorData = await response.json();
            dataCacheRef.current.set(layer.id, {
              data: vectorData,
              timestamp: Date.now(),
              type: "vector",
            });
          } else {
            console.error(
              "Failed to load vector layer:",
              response.status,
              response.statusText
            );
            return;
          }
        }

        if (
          vectorData &&
          vectorData.features &&
          vectorData.features.length > 0
        ) {
          const geoJSONLayer = L.geoJSON(vectorData, {
            style: () => {
              // Use custom style configuration if available
              const vectorStyle = layer.metadata.styleConfig?.vectorStyle;
              
              if (vectorStyle) {
                return {
                  fillColor: vectorStyle.fillColor === "transparent" ? "transparent" : vectorStyle.fillColor,
                  weight: vectorStyle.borderWidth,
                  color: vectorStyle.borderColor,
                  opacity: vectorStyle.borderOpacity,
                  fillOpacity: vectorStyle.fillColor === "transparent" ? 0 : vectorStyle.fillOpacity,
                  dashArray: vectorStyle.borderDashArray,
                };
              } else {
                // Fallback to original styling
              const fillColor = layer.metadata.colorScale[1] || "#ff6b6b";
              return {
                fillColor: fillColor,
                weight: 2,
                color: "#ffffff",
                opacity: layer.opacity,
                fillOpacity: Math.max(layer.opacity * 0.6, 0.4),
              };
              }
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

                const formatPropertyValue = (
                  key: string,
                  value: unknown
                ): string => {
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
                    ${
                      feature.properties.name || feature.properties.cluster_id
                        ? `Cluster ID: ${
                            feature.properties.cluster_id ||
                            feature.properties.name
                          }`
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
                        background: ${
                          key.toLowerCase().includes("risk")
                            ? "#fef2f2"
                            : key.toLowerCase().includes("area")
                            ? "#f0fdf4"
                            : key.toLowerCase().includes("density")
                            ? "#f7fee7"
                            : "#f9fafb"
                        };
                        border-left: 3px solid ${
                          key.toLowerCase().includes("risk")
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
                  className: customPopupStyle,
                });
              }
            },
          });
          vectorLayerGroupRef.current.addLayer(geoJSONLayer);

          if (storeReference) {
            loadedLayersRef.current.set(layer.id, {
              layer: geoJSONLayer,
              opacity: layer.opacity,
              visible: layer.visible,
              styleConfig: layer.metadata.styleConfig,
            });
          }
        } else {
          console.warn("No valid features found in vector data");
        }
      } catch (error) {
        console.error("Failed to load vector layer:", error);
      }
    },
    [customPopupStyle, enableDataLayers]
  );

  // Load COG layers using dynamic georaster imports
  const loadCogLayer = useCallback(
    async (layer: LayerState) => {
      if (!cogLayerGroupRef.current || !enableDataLayers) return;

      try {
        // Dynamic imports for georaster libraries (only loaded when needed)
        const [parseGeoraster, GeoRasterLayer] = await Promise.all([
          // @ts-expect-error - georaster library doesn't have TypeScript definitions
          import("georaster").then((module) => module.default),
          // @ts-expect-error - georaster-layer-for-leaflet library doesn't have TypeScript definitions
          import("georaster-layer-for-leaflet").then(
            (module) => module.default
          ),
        ]);

        let georaster = georasterCacheRef.current.get(layer.id);

        if (georaster) {
          // Using cached georaster
        } else {
          const response = await fetch(`/api/map-data/cog/${layer.id}`);
          if (!response.ok) {
            throw new Error(`Failed to fetch COG: ${response.statusText}`);
          }

          const arrayBuffer = await response.arrayBuffer();
          georaster = (await parseGeoraster(arrayBuffer)) as GeorasterObject;

          georasterCacheRef.current.set(layer.id, georaster);
        }

        if (!georaster) {
          throw new Error("Failed to load or parse georaster data");
        }

        const colorScale = layer.metadata.colorScale;
        const valueRange = layer.metadata.valueRange;

        // Get custom color scheme if available
        const rasterScheme = layer.metadata.styleConfig?.rasterScheme;

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
              return null;
            }

            // Use custom color scheme if available
            if (rasterScheme) {
              const colorFunction = createLeafletColorFunction(rasterScheme, valueRange);
              return colorFunction(pixelValue);
            }

            // Fallback to original logic
            const isRiskLayer =
              layer.id.includes("risk") ||
              layer.metadata.name.toLowerCase().includes("risk");

            if (isRiskLayer) {
              const normalized =
                (pixelValue - valueRange[0]) / (valueRange[1] - valueRange[0]);
              const clampedNormalized = Math.max(0, Math.min(1, normalized));

              if (clampedNormalized <= 0.33) {
                const t = clampedNormalized / 0.33;
                const r = Math.round(255 * t);
                const g = Math.round(165 * t);
                const b = 0;
                const a = t * 0.8;
                return `rgba(${r}, ${g}, ${b}, ${a})`;
              } else if (clampedNormalized <= 0.66) {
                const t = (clampedNormalized - 0.33) / 0.33;
                const r = 255;
                const g = Math.round(165 * (1 - t));
                const b = 0;
                const a = 0.8 + t * 0.15;
                return `rgba(${r}, ${g}, ${b}, ${a})`;
              } else {
                const t = (clampedNormalized - 0.66) / 0.34;
                const r = Math.round(255 * (1 - t * 0.4));
                const g = 0;
                const b = 0;
                const a = 0.95;
                return `rgba(${r}, ${g}, ${b}, ${a})`;
              }
            } else {
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

        if (cogLayerGroupRef.current) {
          loadedLayersRef.current.set(layer.id, {
            layer: cogLayer,
            opacity: layer.opacity,
            visible: layer.visible,
            isCogLayer: true,
            styleConfig: layer.metadata.styleConfig,
          });
        }
      } catch (error) {
        console.error(`Failed to load COG layer ${layer.id}:`, error);
      }
    },
    [enableDataLayers]
  );

  const updateMapLayers = useCallback(() => {
    if (
      !mapRef.current ||
      !layerGroupRef.current ||
      !vectorLayerGroupRef.current ||
      !cogLayerGroupRef.current ||
      !enableDataLayers
    )
      return;

    const currentLayerStates = new Map(
      layers.map((layer) => [
        layer.id,
        { visible: layer.visible, opacity: layer.opacity },
      ])
    );
    const loadedLayers = loadedLayersRef.current;

    // Remove layers that are no longer visible or no longer exist
    for (const [layerId, loadedLayer] of loadedLayers.entries()) {
      const currentState = currentLayerStates.get(layerId);
      if (!currentState || !currentState.visible) {
        try {
          if (loadedLayer.isCogLayer && cogLayerGroupRef.current) {
            cogLayerGroupRef.current.removeLayer(loadedLayer.layer);
          } else {
            if (
              vectorLayerGroupRef.current &&
              vectorLayerGroupRef.current.hasLayer(loadedLayer.layer)
            ) {
              vectorLayerGroupRef.current.removeLayer(loadedLayer.layer);
            }
            if (
              layerGroupRef.current &&
              layerGroupRef.current.hasLayer(loadedLayer.layer)
            ) {
              layerGroupRef.current.removeLayer(loadedLayer.layer);
            }
            if (mapRef.current.hasLayer(loadedLayer.layer)) {
              mapRef.current.removeLayer(loadedLayer.layer);
            }
          }
        } catch (error) {
          console.warn(`Error removing layer ${layerId}:`, error);
        }

        loadedLayers.delete(layerId);
      }
    }

    // Add new visible layers or update existing ones
    const visibleLayers = layers.filter((layer) => layer.visible);

    visibleLayers.forEach((layer) => {
      const loadedLayer = loadedLayers.get(layer.id);
      const styleChanged =
        loadedLayer &&
        JSON.stringify(loadedLayer.styleConfig) !==
          JSON.stringify(layer.metadata.styleConfig);

      // If layer is loaded, but style or opacity has changed, remove it to be re-added
      if (
        loadedLayer &&
        (styleChanged || loadedLayer.opacity !== layer.opacity)
      ) {
        try {
          if (loadedLayer.isCogLayer && cogLayerGroupRef.current) {
            cogLayerGroupRef.current.removeLayer(loadedLayer.layer);
          } else if (
            vectorLayerGroupRef.current?.hasLayer(loadedLayer.layer)
          ) {
            vectorLayerGroupRef.current.removeLayer(loadedLayer.layer);
          } else if (layerGroupRef.current?.hasLayer(loadedLayer.layer)) {
            layerGroupRef.current.removeLayer(loadedLayer.layer);
          } else if (mapRef.current?.hasLayer(loadedLayer.layer)) {
            mapRef.current.removeLayer(loadedLayer.layer);
          }
        } catch (error) {
          console.warn(`Error removing layer ${layer.id} for update:`, error);
        }
        loadedLayers.delete(layer.id);
      } else if (loadedLayer) {
        // If no significant changes, no need to do anything
        return;
      }

      if (layer.metadata.dataType === "vector") {
        if (layer.metadata.format === "mbtiles") {
          if (L && VectorGrid) {
            const cachedLayerName = dataCacheRef.current.get(
              `${layer.id}_layername`
            );

            const createVectorTileLayer = (actualLayerName: string) => {
              const vectorTileLayer = L.vectorGrid.protobuf(
                `/api/map-data/vector/${layer.id}/{z}/{x}/{y}.mvt`,
                {
                  rendererFactory: L.canvas.tile,
                  vectorTileLayerStyles: {
                    [actualLayerName]: (() => {
                      const vectorStyle = layer.metadata.styleConfig?.vectorStyle;
                      
                      if (vectorStyle) {
                        return {
                          weight: vectorStyle.borderWidth,
                          color: vectorStyle.borderColor,
                          opacity: vectorStyle.borderOpacity,
                          fillColor: vectorStyle.fillColor === "transparent" ? "transparent" : vectorStyle.fillColor,
                          fillOpacity: vectorStyle.fillColor === "transparent" ? 0 : vectorStyle.fillOpacity,
                          dashArray: vectorStyle.borderDashArray,
                        };
                      } else {
                        return {
                      weight: 2,
                      color: "#1e40af",
                      opacity: 0.9,
                      fillColor: "#1e3a8a",
                      fillOpacity: Math.max(layer.opacity * 0.7, 0.3),
                        };
                      }
                    })(),
                    [layer.id]: (() => {
                      const vectorStyle = layer.metadata.styleConfig?.vectorStyle;
                      
                      if (vectorStyle) {
                        return {
                          weight: vectorStyle.borderWidth,
                          color: vectorStyle.borderColor,
                          opacity: vectorStyle.borderOpacity,
                          fillColor: vectorStyle.fillColor === "transparent" ? "transparent" : vectorStyle.fillColor,
                          fillOpacity: vectorStyle.fillColor === "transparent" ? 0 : vectorStyle.fillOpacity,
                          dashArray: vectorStyle.borderDashArray,
                        };
                      } else {
                        return {
                      weight: 2,
                      color: "#1e40af",
                      opacity: 0.9,
                      fillColor: "#1e3a8a",
                      fillOpacity: Math.max(layer.opacity * 0.7, 0.3),
                        };
                      }
                    })(),
                  },
                  maxZoom: 18,
                  pane: "overlayPane",
                  attribution: "EU Climate Risk Data",
                }
              );

              vectorLayerGroupRef.current?.addLayer(vectorTileLayer);
              loadedLayersRef.current.set(layer.id, {
                layer: vectorTileLayer,
                opacity: layer.opacity,
                visible: layer.visible,
                styleConfig: layer.metadata.styleConfig,
              });
            };

            if (cachedLayerName && cachedLayerName.type === "vector") {
              createVectorTileLayer(cachedLayerName.data as string);
            } else {
              getActualLayerName(layer.id)
                .then((actualLayerName) => {
                  dataCacheRef.current.set(`${layer.id}_layername`, {
                    data: actualLayerName,
                    timestamp: Date.now(),
                    type: "vector",
                  });
                  createVectorTileLayer(actualLayerName);
                })
                .catch((error) => {
                  console.error(
                    `Failed to get layer name for ${layer.id}:`,
                    error
                  );
                  createVectorTileLayer(layer.id);
                });
            }
          } else {
            console.warn("VectorGrid not available - skipping vector layer");
          }
        } else {
          loadVectorLayer(layer);
        }
      } else if (layer.metadata.dataType === "raster") {
        if (layer.metadata.format === "mbtiles") {
          const tileLayer = L.tileLayer(
            `/api/map-tiles/${layer.id}/{z}/{x}/{y}.png`,
            {
              opacity: layer.opacity || 0.8,
              maxZoom: 18,
            }
          );
          layerGroupRef.current?.addLayer(tileLayer);

          loadedLayersRef.current.set(layer.id, {
            layer: tileLayer,
            opacity: layer.opacity,
            visible: layer.visible,
            styleConfig: layer.metadata.styleConfig,
          });
        } else if (layer.metadata.format === "cog") {
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

      const [minLng, minLat, maxLng, maxLat] = combinedBounds;
      mapRef.current.fitBounds([
        [minLat, minLng],
        [maxLat, maxLng],
      ]);
    }
  }, [
    layers,
    autoFitBounds,
    loadCogLayer,
    getActualLayerName,
    loadVectorLayer,
    enableDataLayers,
  ]);

  useEffect(() => {
    if (enableDataLayers) {
      updateMapLayers();
    }
  }, [updateMapLayers, enableDataLayers]);

  return (
    <div
      id={mapId}
      className="w-full h-full relative"
      style={{ minHeight: "400px" }}
    />
  );
}
