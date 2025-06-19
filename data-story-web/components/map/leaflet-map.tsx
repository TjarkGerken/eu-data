"use client";

import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png",
  iconUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png",
  shadowUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
});

interface LayerState {
  id: string;
  visible: boolean;
  opacity: number;
  metadata: {
    layerName: string;
    scenario: string;
    dataType: string;
    bounds: [number, number, number, number];
    colorScale: string[];
    valueRange: [number, number];
  };
}

interface LeafletMapProps {
  layers: LayerState[];
  showClusterOverlay: boolean;
  scenario: string;
}

export default function LeafletMap({
  layers,
  showClusterOverlay,
  scenario,
}: LeafletMapProps) {
  const mapRef = useRef<L.Map | null>(null);
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const layerGroupRef = useRef<L.LayerGroup | null>(null);
  const clusterLayerRef = useRef<L.LayerGroup | null>(null);

  useEffect(() => {
    if (!mapContainerRef.current) return;

    if (!mapRef.current) {
      initializeMap();
    }

    updateMapLayers();
    loadClusterOverlay();

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, [layers, showClusterOverlay, scenario]);

  const initializeMap = () => {
    if (!mapContainerRef.current) return;

    const map = L.map(mapContainerRef.current, {
      center: [52.0, 5.0], // Netherlands center
      zoom: 7,
      zoomControl: true,
      attributionControl: true,
    });

    // Add base map
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© OpenStreetMap contributors",
      maxZoom: 19,
    }).addTo(map);

    // Create layer groups
    layerGroupRef.current = L.layerGroup().addTo(map);
    clusterLayerRef.current = L.layerGroup().addTo(map);

    mapRef.current = map;
  };

  const updateMapLayers = () => {
    if (!mapRef.current || !layerGroupRef.current) return;

    layerGroupRef.current.clearLayers();

    const visibleLayers = layers.filter(
      (layer) => layer.visible && layer.metadata.scenario === scenario
    );

    visibleLayers.forEach((layer) => {
      const tileLayer = L.tileLayer(
        `/api/map-tiles/${layer.id}/{z}/{x}/{y}.png`,
        {
          opacity: layer.opacity,
          attribution: `${layer.metadata.layerName} - ${layer.metadata.dataType}`,
          maxZoom: 18,
          tileSize: 256,
        }
      );

      layerGroupRef.current?.addLayer(tileLayer);
    });

    if (visibleLayers.length > 0) {
      const bounds = visibleLayers[0].metadata.bounds;
      const leafletBounds = L.latLngBounds([
        [bounds[1], bounds[0]], // southwest
        [bounds[3], bounds[2]], // northeast
      ]);

      mapRef.current.fitBounds(leafletBounds, { padding: [20, 20] });
    }
  };

  const loadClusterOverlay = async () => {
    if (!mapRef.current || !clusterLayerRef.current || !showClusterOverlay) {
      clusterLayerRef.current?.clearLayers();
      return;
    }

    try {
      const response = await fetch(`/api/map-data/clusters/${scenario}`);
      if (response.ok) {
        const clusterData = await response.json();

        clusterLayerRef.current.clearLayers();

        L.geoJSON(clusterData, {
          style: {
            fillColor: "#ff0000",
            weight: 2,
            opacity: 1,
            color: "#ffffff",
            fillOpacity: 0.6,
          },
          onEachFeature: (feature, layer) => {
            if (feature.properties) {
              const popupContent = `
                <div class="cluster-popup">
                  <h4>Risk Cluster</h4>
                  <p><strong>Area:</strong> ${(
                    feature.properties.cluster_area_square_meters / 1000000
                  ).toFixed(2)} km²</p>
                  <p><strong>Mean Risk:</strong> ${
                    feature.properties.mean_risk_value?.toFixed(3) || "N/A"
                  }</p>
                  <p><strong>Max Risk:</strong> ${
                    feature.properties.max_risk_value?.toFixed(3) || "N/A"
                  }</p>
                  <p><strong>Pixels:</strong> ${
                    feature.properties.pixel_count || "N/A"
                  }</p>
                </div>
              `;

              layer.bindPopup(popupContent);
            }
          },
        }).addTo(clusterLayerRef.current);
      }
    } catch (error) {
      console.error("Failed to load cluster overlay:", error);
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
