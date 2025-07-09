"use client";

import { useEffect, useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Layers, Download, Settings } from "lucide-react";
import { mapTileService, MapLayerMetadata } from "@/lib/map-tile-service";
import { WaveSlider } from "@/components/ui/wave-slider";
import { EconomicIndicatorSelector } from "@/components/ui/economic-indicator-selector";
import { createGradientFromStops } from "@/lib/color-schemes";
import { useLanguage } from "@/contexts/language-context";
import dynamic from "next/dynamic";

const LeafletMap = dynamic(() => import("./map/leaflet-map"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-96 bg-gray-100 rounded-lg animate-pulse" />
  ),
});

interface InteractiveMapProps {
  title?: string;
  description?: string;
  selectedLayers?: string[];
  height?: string;
  enableLayerControls?: boolean;
  centerLat?: number;
  centerLng?: number;
  zoom?: number;
  autoFitBounds?: boolean;
  // Admin control over user-facing controls
  showLayerToggles?: boolean;
  showOpacityControls?: boolean;
  showDownloadButtons?: boolean;
  // Pre-defined layer opacities
  predefinedOpacities?: Record<string, number>;
  // Cluster groups for SLR scenarios
  enableClusterGroups?: boolean;
  clusterGroups?: Array<{
    id: string;
    name: string;
    layerIds: string[];
    economicIndicators?: {
      [key: string]: {
        layers: string[];
        clusterLayer?: string;
      };
    };
  }>;
}

interface LayerState {
  id: string;
  visible: boolean;
  opacity: number;
  metadata: MapLayerMetadata;
  zIndex?: number; // Layer rendering order - optional since some layers may not have explicit z-index
}

// Interactive map translations
const interactiveMapTranslations = {
  en: {
    title: "Interactive Climate Map",
    description: "Explore climate data layers",
    loadingTitle: "Loading Interactive Map...",
    loadingText: "Loading map tiles...",
    legend: "Legend",
    layerControls: "Layer Controls",
    opacity: "Opacity",
    range: "Range",
    zIndex: "z-index"
  },
  de: {
    title: "Interaktive Klimakarte",
    description: "Erkunden Sie Klimadatenschichten",
    loadingTitle: "Interaktive Karte wird geladen...",
    loadingText: "Kartenkacheln werden geladen...",
    legend: "Legende",
    layerControls: "Ebenen-Steuerung",
    opacity: "Deckkraft",
    range: "Bereich",
    zIndex: "Z-Index"
  }
};

export function InteractiveMap({
  title,
  description,
  selectedLayers = [],
  height = "600px",
  enableLayerControls = true,
  centerLat = 52.1326,
  centerLng = 5.2913,
  zoom = 8,
  autoFitBounds = false,
  // Admin control defaults (all enabled by default for backward compatibility)
  showLayerToggles = true,
  showOpacityControls = true,
  showDownloadButtons = true,
  predefinedOpacities = {},
  // Cluster groups for SLR scenarios
  enableClusterGroups = false,
  clusterGroups = [],
}: InteractiveMapProps) {
  const { language } = useLanguage();
  const t = interactiveMapTranslations[language];
  
  const [availableLayers, setAvailableLayers] = useState<MapLayerMetadata[]>(
    []
  );
  const [layerStates, setLayerStates] = useState<LayerState[]>([]);
  const [loading, setLoading] = useState(true);
  const [showControls, setShowControls] = useState(true);
  const [selectedScenario, setSelectedScenario] = useState<string>(
    clusterGroups?.[0]?.id || ""
  );
  const [selectedEconomicIndicator, setSelectedEconomicIndicator] = useState<string>("Combined");

  const initializeLayerStates = useCallback(() => {
    if (!Array.isArray(availableLayers)) {
      console.warn("availableLayers is not an array:", availableLayers);
      return;
    }

    const states = availableLayers.map((layer) => {
      let isVisible = false;

      if (enableClusterGroups && clusterGroups && clusterGroups.length > 0) {
        // If cluster groups are enabled, show layers from the selected scenario
        const currentGroup = clusterGroups.find(
          (group) => group.id === selectedScenario
        );
        
        if (currentGroup) {
          // Start with base SLR layers from the group
          const isFromSLR = currentGroup.layerIds.includes(layer.id);
          let isFromEconomicIndicator = false;
          
          // Check if economic indicators are configured and add those layers too
          if (currentGroup.economicIndicators && currentGroup.economicIndicators[selectedEconomicIndicator]) {
            const indicator = currentGroup.economicIndicators[selectedEconomicIndicator];
            isFromEconomicIndicator = indicator.layers.includes(layer.id) || (indicator.clusterLayer === layer.id);
          }
          
          // Show layer if it's either from SLR or economic indicator (or both)
          isVisible = isFromSLR || isFromEconomicIndicator;
        } else {
          isVisible = false;
        }
      } else {
        // Original behavior: show layers from selectedLayers prop
        isVisible = selectedLayers.includes(layer.id);
      }

      return {
        id: layer.id,
        visible: isVisible,
        opacity: predefinedOpacities[layer.id]
          ? predefinedOpacities[layer.id] / 100
          : 0.8,
        metadata: layer,
        zIndex: layer.zIndex,
      };
    });
    setLayerStates(states);
  }, [
    availableLayers,
    selectedLayers,
    predefinedOpacities,
    enableClusterGroups,
    clusterGroups,
    selectedScenario,
    selectedEconomicIndicator,
  ]);

  useEffect(() => {
    loadAvailableLayers();
  }, []);

  useEffect(() => {
    if (availableLayers.length > 0) {
      initializeLayerStates();
    }
  }, [availableLayers, initializeLayerStates]);

  const loadAvailableLayers = async () => {
    try {
      const layers = await mapTileService.getAvailableLayers();
      setAvailableLayers(layers);
    } catch (error) {
      console.error("Failed to load map layers:", error);
    } finally {
      setLoading(false);
    }
  };

  const toggleLayerVisibility = (layerId: string) => {
    setLayerStates((prev) =>
      prev.map((layer) =>
        layer.id === layerId ? { ...layer, visible: !layer.visible } : layer
      )
    );
  };

  const updateLayerOpacity = (layerId: string, opacity: number) => {
    setLayerStates((prev) =>
      prev.map((layer) =>
        layer.id === layerId ? { ...layer, opacity: opacity / 100 } : layer
      )
    );
  };

  const downloadLayerData = async (layerId: string) => {
    const layer = layerStates.find((l) => l.id === layerId);
    if (!layer) return;

    window.open(`/api/map-data/download/${layerId}`, "_blank");
  };

  const handleScenarioChange = (scenarioId: string) => {
    setSelectedScenario(scenarioId);
    // Layer states will be updated automatically via the useEffect that depends on selectedScenario
  };

  const handleEconomicIndicatorChange = (indicator: string) => {
    setSelectedEconomicIndicator(indicator);
    // Layer states will be updated automatically via the useEffect that depends on selectedEconomicIndicator
  };

  const visibleLayers = layerStates.filter((layer) => layer.visible);

  if (loading) {
    return (
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Layers className="h-5 w-5" />
            {t.loadingTitle}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div
            className="w-full bg-gray-100 rounded-lg animate-pulse"
            style={{ height }}
          >
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                <p className="text-gray-600">{t.loadingText}</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Layers className="h-5 w-5" />
              {title || t.title}
            </CardTitle>
            {(description || t.description) && (
              <p className="text-muted-foreground mt-2">{description || t.description}</p>
            )}
          </div>
          {enableLayerControls && (
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowControls(!showControls)}
              >
                <Settings className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="space-y-4">
          <div className="w-full">
            <div
              className="relative rounded-lg overflow-hidden border interactive-map-container"
              style={{ height }}
            >
              <LeafletMap
                layers={layerStates}
                centerLat={centerLat}
                centerLng={centerLng}
                zoom={zoom}
                autoFitBounds={autoFitBounds}
              />

              <div className="absolute bottom-4 left-4 bg-white/90 backdrop-blur-sm rounded-lg p-3 shadow-lg z-[1000]">
                <h4 className="text-sm font-medium mb-2">{t.legend}</h4>
                <div className="space-y-1">
                  {visibleLayers.map((layer) => (
                    <div
                      key={layer.id}
                      className="flex items-center gap-2 text-xs"
                    >
                      <div
                        className="w-4 h-3 rounded border"
                        style={{
                          background: layer.metadata.styleConfig?.rasterScheme
                            ? createGradientFromStops(
                                layer.metadata.styleConfig.rasterScheme.colors
                              )
                            : `linear-gradient(to right, ${layer.metadata.colorScale.join(
                                ", "
                              )})`,
                          opacity: layer.opacity,
                        }}
                      />
                      <span>{layer.metadata.name}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Economic Indicator Selector */}
          {enableClusterGroups && clusterGroups && clusterGroups.length > 0 && (
            (() => {
              // Check if any scenario has economic indicators configured
              const hasAnyEconomicIndicators = clusterGroups.some(group => 
                group.economicIndicators && Object.keys(group.economicIndicators).length > 0
              );
              
              if (hasAnyEconomicIndicators) {
                // Get all unique economic indicators across all scenarios
                const allIndicators = new Set<string>();
                clusterGroups.forEach(group => {
                  if (group.economicIndicators) {
                    Object.keys(group.economicIndicators).forEach(indicator => {
                      allIndicators.add(indicator);
                    });
                  }
                });
                
                return (
                  <div className="w-full">
                    <EconomicIndicatorSelector
                      indicators={Array.from(allIndicators)}
                      selectedIndicator={selectedEconomicIndicator}
                      onIndicatorChange={handleEconomicIndicatorChange}
                    />
                  </div>
                );
              }
              return null;
            })()
          )}

          {/* SLR Scenario Slider */}
          {enableClusterGroups && clusterGroups && clusterGroups.length > 0 && (
            <div className="w-full">
              <WaveSlider
                scenarios={clusterGroups.map((group) => ({
                  id: group.id,
                  name: group.name,
                }))}
                selectedScenario={selectedScenario}
                onScenarioChange={handleScenarioChange}
              />
            </div>
          )}

          {enableLayerControls && showControls && (
            <div className="w-full">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg">{t.layerControls}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {layerStates
                      .sort((a, b) => {
                        // Sort by z-index for consistent display order
                        const aZIndex = a.zIndex ?? a.metadata.zIndex ?? 50;
                        const bZIndex = b.zIndex ?? b.metadata.zIndex ?? 50;
                        return aZIndex - bZIndex;
                      })
                      .map((layer) => (
                        <div
                          key={layer.id}
                          className="space-y-3 p-3 bg-gray-50 rounded-lg"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              {showLayerToggles && (
                                <Switch
                                  checked={layer.visible}
                                  onCheckedChange={() =>
                                    toggleLayerVisibility(layer.id)
                                  }
                                />
                              )}
                              <Label className="text-sm font-medium">
                                {layer.metadata.name}
                              </Label>
                            </div>
                            <div className="flex gap-1">
                              {showDownloadButtons && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => downloadLayerData(layer.id)}
                                >
                                  <Download className="h-3 w-3" />
                                </Button>
                              )}
                            </div>
                          </div>

                          <div className="flex flex-wrap items-center gap-2">
                            <Badge variant="outline" className="text-xs">
                              {layer.metadata.dataType}
                            </Badge>
                            <Badge variant="secondary" className="text-xs">
                              {layer.metadata.format}
                            </Badge>
                            <Badge variant="outline" className="text-xs">
                              {t.zIndex}:{" "}
                              {layer.zIndex ?? layer.metadata.zIndex ?? 50}
                            </Badge>
                            <span className="text-xs text-muted-foreground">
                              {t.range}: {layer.metadata.valueRange[0].toFixed(2)} -{" "}
                              {layer.metadata.valueRange[1].toFixed(2)}
                            </span>
                          </div>

                          {layer.visible && showOpacityControls && (
                            <div className="space-y-2">
                              <Label className="text-xs">
                                {t.opacity}: {Math.round(layer.opacity * 100)}%
                              </Label>
                              <Slider
                                value={[layer.opacity * 100]}
                                onValueChange={([value]) =>
                                  updateLayerOpacity(layer.id, value)
                                }
                                max={100}
                                step={10}
                                className="w-full"
                              />
                            </div>
                          )}
                        </div>
                      ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
