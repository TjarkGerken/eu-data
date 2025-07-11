"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Building, MapPin, Settings, Waves, Train } from "lucide-react";
import { useLanguage } from "@/contexts/language-context";
import dynamic from "next/dynamic";

const BaseLeafletMap = dynamic(() => import("./map/base-leaflet-map"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-96 bg-blue-50 rounded-lg animate-pulse" />
  ),
});

interface InfrastructureMapProps {
  title?: string;
  description?: string;
  height?: string;
  centerLat?: number;
  centerLng?: number;
  zoom?: number;
  seamarkOpacity?: number;
  enableSeamarkLayer?: boolean;
  tileServerOption?: "openseamap" | "hybrid";
  infrastructureFocus?:
    | "rotterdam"
    | "groningen"
    | "amsterdam"
    | "schiphol"
    | "sloehaven"
    | "full"
    | "custom";
  showControls?: boolean;
  enableRailwayLayer?: boolean;
  railwayOpacity?: number;
  railwayStyle?: "standard" | "signals" | "maxspeed";
  showInfrastructureFocusControl?: boolean;
  showMapStyleControl?: boolean;
  showSeamarkLayerControl?: boolean;
  showSeamarkOpacityControl?: boolean;
  showRailwayLayerControl?: boolean;
  showRailwayStyleControl?: boolean;
  showRailwayOpacityControl?: boolean;
}

const INFRASTRUCTURE_COORDINATES = {
  rotterdam: { lat: 51.93971438866205, lng: 4.1296399384512394, zoom: 12 },
  groningen: { lat: 53.44610707492235, lng: 6.8335077397728945, zoom: 13 },
  amsterdam: { lat: 52.41698553531954, lng: 4.804527798530235, zoom: 12 },
  schiphol: { lat: 52.3105, lng: 4.7683, zoom: 13 },
  sloehaven: { lat: 51.3774, lng: 3.5952, zoom: 13 },
  full: { lat: 52.1326, lng: 5.2913, zoom: 7 },
  custom: { lat: 52.1326, lng: 5.2913, zoom: 8 },
};

// Infrastructure map translations
const infrastructureTranslations = {
  en: {
    title: "Interactive Infrastructure Map",
    description:
      "Explore transportation infrastructure and connectivity networks",
    controlsTitle: "Infrastructure Map Controls",
    focusLabel: "Infrastructure Focus",
    mapStyleLabel: "Map Style",
    seaMarkLayerLabel: "Sea Marks Layer",
    railwayLayerLabel: "Railway Layer",
    opacityLabel: "Opacity",
    railwayStyleLabel: "Railway Style",
    legend: "Infrastructure Legend",
    seaMarksNav: "Sea Marks & Navigation",
    railwayInfrastructure: "Railway Infrastructure",
    railwaySignals: "Railway Signals",
    railwaySpeedLimits: "Railway Speed Limits",
    openseamapStandard: "OpenSeaMap Standard",
    satelliteSeaMarks: "Satellite + Sea Marks",
    infrastructureSignals: "Infrastructure & Signals",
    speedLimits: "Speed Limits",
    layerOpacity: "Layer Opacity",
    locations: {
      rotterdam: "Rotterdam Port (NL)",
      groningen: "Groningen (NL)",
      amsterdam: "Amsterdam (NL)",
      schiphol: "Schiphol Airport (NL)",
      sloehaven: "Sloehaven Port (NL)",
      full: "Full View (NL)",
    },
    focusArea: "Focus Area",
    seaMarkLayerStatus: "Sea Marks Layer",
    railwayLayerStatus: "Railway Layer",
  },
  de: {
    title: "Interaktive Infrastrukturkarte",
    description: "Erkunden Sie Verkehrsinfrastruktur und Verbindungsnetzwerke",
    controlsTitle: "Infrastrukturkarte Steuerung",
    focusLabel: "Infrastruktur-Fokus",
    mapStyleLabel: "Kartenstil",
    seaMarkLayerLabel: "Seezeichen-Schicht",
    railwayLayerLabel: "Eisenbahn-Schicht",
    opacityLabel: "Deckkraft",
    railwayStyleLabel: "Eisenbahn-Stil",
    legend: "Infrastruktur-Legende",
    seaMarksNav: "Seezeichen & Navigation",
    railwayInfrastructure: "Eisenbahn-Infrastruktur",
    railwaySignals: "Eisenbahn-Signale",
    railwaySpeedLimits: "Eisenbahn-Geschwindigkeitsbegrenzungen",
    openseamapStandard: "OpenSeaMap Standard",
    satelliteSeaMarks: "Satellit + Seezeichen",
    infrastructureSignals: "Infrastruktur & Signale",
    speedLimits: "Geschwindigkeitsbegrenzungen",
    layerOpacity: "Schicht-Deckkraft",
    locations: {
      rotterdam: "Rotterdam Hafen (NL)",
      groningen: "Groningen (NL)",
      amsterdam: "Amsterdam (NL)",
      schiphol: "Schiphol Flughafen (NL)",
      sloehaven: "Sloehaven Hafen (NL)",
      full: "Vollansicht (NL)",
    },
    focusArea: "Fokusbereich",
    seaMarkLayerStatus: "Seezeichen-Schicht",
    railwayLayerStatus: "Eisenbahn-Schicht",
  },
};

export function InfrastructureMap({
  title,
  description,
  height = "600px",
  centerLat,
  centerLng,
  zoom,
  seamarkOpacity = 80,
  enableSeamarkLayer = true,
  tileServerOption = "openseamap",
  infrastructureFocus = "rotterdam",
  showControls = true,
  enableRailwayLayer = false,
  railwayOpacity = 70,
  railwayStyle = "standard",
  showInfrastructureFocusControl = true,
  showMapStyleControl = true,
  showSeamarkLayerControl = true,
  showSeamarkOpacityControl = true,
  showRailwayLayerControl = true,
  showRailwayStyleControl = true,
  showRailwayOpacityControl = true,
}: InfrastructureMapProps) {
  const { language } = useLanguage();
  const t = infrastructureTranslations[language];

  const [mapControls, setMapControls] = useState({
    seamarkOpacity: seamarkOpacity,
    enableSeamarkLayer: enableSeamarkLayer,
    tileServerOption: tileServerOption,
    infrastructureFocus: infrastructureFocus,
    enableRailwayLayer: enableRailwayLayer,
    railwayOpacity: railwayOpacity,
    railwayStyle: railwayStyle,
  });

  const [showControlPanel, setShowControlPanel] = useState(showControls);

  const getMapCoordinates = () => {
    if (centerLat && centerLng && zoom) {
      return { lat: centerLat, lng: centerLng, zoom: zoom };
    }
    return (
      INFRASTRUCTURE_COORDINATES[mapControls.infrastructureFocus] ||
      INFRASTRUCTURE_COORDINATES.rotterdam
    );
  };

  const coordinates = getMapCoordinates();

  const getTileConfiguration = () => {
    const baseConfig = {
      baseTileLayer: {
        url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 18,
      },
      overlayTileLayers: [] as Array<{
        url: string;
        attribution: string;
        maxZoom?: number;
        opacity?: number;
      }>,
    };

    if (mapControls.enableSeamarkLayer) {
      baseConfig.overlayTileLayers.push({
        url: "https://t1.openseamap.org/seamark/{z}/{x}/{y}.png",
        attribution:
          'Sea marks &copy; <a href="http://www.openseamap.org">OpenSeaMap</a> contributors',
        maxZoom: 18,
        opacity: mapControls.seamarkOpacity / 100,
      });
    }

    // Add OpenRailwayMap layer if enabled
    if (mapControls.enableRailwayLayer) {
      baseConfig.overlayTileLayers.push({
        url: `https://{s}.tiles.openrailwaymap.org/${mapControls.railwayStyle}/{z}/{x}/{y}.png`,
        attribution:
          'Railways: <a href="https://www.openstreetmap.org/copyright">&copy; OpenStreetMap contributors</a>, Style: <a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA 2.0</a> <a href="http://www.openrailwaymap.org/">OpenRailwayMap</a>',
        maxZoom: 19,
        opacity: mapControls.railwayOpacity / 100,
      });
    }

    if (mapControls.tileServerOption === "hybrid") {
      // Use satellite imagery as base for hybrid view
      baseConfig.baseTileLayer = {
        url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attribution:
          "Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community",
        maxZoom: 18,
      };
    }

    return baseConfig;
  };

  const tileConfig = getTileConfiguration();

  const updateControl = (
    key: keyof typeof mapControls,
    value: string | number | boolean,
  ) => {
    setMapControls((prev) => ({ ...prev, [key]: value }));
  };

  const getLocationDisplayName = (location: string) => {
    return t.locations[location as keyof typeof t.locations] || location;
  };

  const getRailwayStyleDisplayName = (style: string) => {
    switch (style) {
      case "standard":
        return t.infrastructureSignals;
      case "signals":
        return t.railwaySignals;
      case "maxspeed":
        return t.speedLimits;
      default:
        return style;
    }
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Building className="h-5 w-5 text-blue-600" />
              {title || t.title}
            </CardTitle>
            {(description || t.description) && (
              <p className="text-muted-foreground mt-2">
                {description || t.description}
              </p>
            )}
          </div>
          {showControls && (
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowControlPanel(!showControlPanel)}
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
              className="relative rounded-lg overflow-hidden border-2 border-blue-200 infrastructure-map-container"
              style={{ height }}
            >
              <BaseLeafletMap
                centerLat={coordinates.lat}
                centerLng={coordinates.lng}
                zoom={coordinates.zoom}
                baseTileLayer={tileConfig.baseTileLayer}
                overlayTileLayers={tileConfig.overlayTileLayers}
                customPopupStyle="infrastructure-popup"
                enableDataLayers={false}
              />

              {/* Infrastructure Legend */}
              <div className="absolute bottom-4 left-4 bg-white/95 backdrop-blur-sm rounded-lg p-3 shadow-lg z-[400] border-2 border-blue-200">
                <h4 className="text-sm font-semibold mb-2 text-blue-800 flex items-center gap-1">
                  <Waves className="h-4 w-4" />
                  {t.legend}
                </h4>
                <div className="space-y-2">
                  {mapControls.enableSeamarkLayer && (
                    <div className="flex items-center gap-2 text-xs">
                      <div className="w-4 h-3 rounded border border-blue-400 bg-blue-100" />
                      <span className="text-blue-700">{t.seaMarksNav}</span>
                    </div>
                  )}
                  {mapControls.enableRailwayLayer && (
                    <div className="flex items-center gap-2 text-xs">
                      <Train className="h-3 w-3 text-gray-700" />
                      <span className="text-gray-700">
                        {getRailwayStyleDisplayName(mapControls.railwayStyle)}
                      </span>
                    </div>
                  )}
                  <div className="flex items-center gap-2 text-xs">
                    <MapPin className="h-3 w-3 text-blue-600" />
                    <span className="text-blue-700">
                      {getLocationDisplayName(mapControls.infrastructureFocus)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {showControlPanel && (
            <div className="w-full">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Building className="h-5 w-5" />
                    {t.controlsTitle}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Infrastructure Focus Selection */}
                    {showInfrastructureFocusControl && (
                      <div className="space-y-2">
                        <Label className="text-sm font-medium">
                          {t.focusLabel}
                        </Label>
                        <Select
                          value={mapControls.infrastructureFocus}
                          onValueChange={(value) =>
                            updateControl("infrastructureFocus", value)
                          }
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="rotterdam">
                              {t.locations.rotterdam}
                            </SelectItem>
                            <SelectItem value="groningen">
                              {t.locations.groningen}
                            </SelectItem>
                            <SelectItem value="amsterdam">
                              {t.locations.amsterdam}
                            </SelectItem>
                            <SelectItem value="schiphol">
                              {t.locations.schiphol}
                            </SelectItem>
                            <SelectItem value="sloehaven">
                              {t.locations.sloehaven}
                            </SelectItem>
                            <SelectItem value="full">
                              {t.locations.full}
                            </SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    )}

                    {/* Tile Server Selection */}
                    {showMapStyleControl && (
                      <div className="space-y-2">
                        <Label className="text-sm font-medium">
                          {t.mapStyleLabel}
                        </Label>
                        <Select
                          value={mapControls.tileServerOption}
                          onValueChange={(value) =>
                            updateControl("tileServerOption", value)
                          }
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="openseamap">
                              {t.openseamapStandard}
                            </SelectItem>
                            <SelectItem value="hybrid">
                              {t.satelliteSeaMarks}
                            </SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    )}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Seamark Layer Toggle */}
                    {showSeamarkLayerControl && (
                      <div className="space-y-3 p-3 bg-blue-50 rounded-lg">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Switch
                              checked={mapControls.enableSeamarkLayer}
                              onCheckedChange={(checked) =>
                                updateControl("enableSeamarkLayer", checked)
                              }
                            />
                            <Label className="text-sm font-medium">
                              {t.seaMarkLayerLabel}
                            </Label>
                          </div>
                        </div>

                        {mapControls.enableSeamarkLayer &&
                          showSeamarkOpacityControl && (
                            <div className="space-y-2">
                              <Label className="text-xs text-blue-700">
                                {t.opacityLabel}: {mapControls.seamarkOpacity}%
                              </Label>
                              <Slider
                                value={[mapControls.seamarkOpacity]}
                                onValueChange={([value]) =>
                                  updateControl("seamarkOpacity", value)
                                }
                                max={100}
                                min={10}
                                step={10}
                                className="w-full"
                              />
                            </div>
                          )}
                      </div>
                    )}

                    {/* Railway Layer Toggle */}
                    {showRailwayLayerControl && (
                      <div className="space-y-3 p-3 bg-gray-50 rounded-lg">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Switch
                              checked={mapControls.enableRailwayLayer}
                              onCheckedChange={(checked) =>
                                updateControl("enableRailwayLayer", checked)
                              }
                            />
                            <Label className="text-sm font-medium flex items-center gap-2">
                              <Train className="h-4 w-4" />
                              {t.railwayLayerLabel}
                            </Label>
                          </div>
                        </div>

                        {mapControls.enableRailwayLayer && (
                          <div className="space-y-3">
                            {/* Railway Style Selection */}
                            {showRailwayStyleControl && (
                              <div className="space-y-2">
                                <Label className="text-xs text-gray-700">
                                  {t.railwayStyleLabel}
                                </Label>
                                <Select
                                  value={mapControls.railwayStyle}
                                  onValueChange={(value) =>
                                    updateControl("railwayStyle", value)
                                  }
                                >
                                  <SelectTrigger className="h-8 text-xs">
                                    <SelectValue />
                                  </SelectTrigger>
                                  <SelectContent>
                                    <SelectItem value="standard">
                                      {t.infrastructureSignals}
                                    </SelectItem>
                                    <SelectItem value="signals">
                                      {t.railwaySignals}
                                    </SelectItem>
                                    <SelectItem value="maxspeed">
                                      {t.speedLimits}
                                    </SelectItem>
                                  </SelectContent>
                                </Select>
                              </div>
                            )}

                            {/* Railway Opacity */}
                            {showRailwayOpacityControl && (
                              <div className="space-y-2">
                                <Label className="text-xs text-gray-700">
                                  {t.opacityLabel}: {mapControls.railwayOpacity}
                                  %
                                </Label>
                                <Slider
                                  value={[mapControls.railwayOpacity]}
                                  onValueChange={([value]) =>
                                    updateControl("railwayOpacity", value)
                                  }
                                  max={100}
                                  min={10}
                                  step={10}
                                  className="w-full"
                                />
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
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
