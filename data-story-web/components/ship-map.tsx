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
import { Ship, Anchor, Settings, Waves, Train } from "lucide-react";
import dynamic from "next/dynamic";

const BaseLeafletMap = dynamic(() => import("./map/base-leaflet-map"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-96 bg-blue-50 rounded-lg animate-pulse" />
  ),
});

interface ShipMapProps {
  title?: string;
  description?: string;
  height?: string;
  centerLat?: number;
  centerLng?: number;
  zoom?: number;
  seamarkOpacity?: number;
  enableSeamarkLayer?: boolean;
  tileServerOption?: "openseamap" | "hybrid";
  portFocus?: "rotterdam" | "groningen" | "amsterdam" | "full" | "custom";
  showControls?: boolean;
  // Railway overlay options
  enableRailwayLayer?: boolean;
  railwayOpacity?: number;
  railwayStyle?: "standard" | "signals" | "maxspeed";
  // Admin control over user-facing controls
  showPortFocusControl?: boolean;
  showMapStyleControl?: boolean;
  showSeamarkLayerControl?: boolean;
  showSeamarkOpacityControl?: boolean;
  showRailwayLayerControl?: boolean;
  showRailwayStyleControl?: boolean;
  showRailwayOpacityControl?: boolean;
}

// Pre-defined port coordinates for quick selection
const PORT_COORDINATES = {
  rotterdam: { lat: 51.93971438866205, lng: 4.1296399384512394, zoom: 12 }, 
  groningen: { lat: 53.3217, lng: 6.9413, zoom: 13 }, 
  amsterdam: { lat: 52.41698553531954, lng: 4.804527798530235, zoom: 12 },
  full: { lat: 52.1326, lng: 5.2913, zoom: 7 },
  custom: { lat: 52.1326, lng: 5.2913, zoom: 8 },
};

export function ShipMap({
  title = "Interactive Ship Map",
  description = "Explore maritime data and sea routes",
  height = "600px",
  centerLat,
  centerLng,
  zoom,
  seamarkOpacity = 80,
  enableSeamarkLayer = true,
  tileServerOption = "openseamap",
  portFocus = "rotterdam",
  showControls = true,
  // Railway overlay defaults
  enableRailwayLayer = false,
  railwayOpacity = 70,
  railwayStyle = "standard",
  // Admin control defaults (all enabled by default for backward compatibility)
  showPortFocusControl = true,
  showMapStyleControl = true,
  showSeamarkLayerControl = true,
  showSeamarkOpacityControl = true,
  showRailwayLayerControl = true,
  showRailwayStyleControl = true,
  showRailwayOpacityControl = true,
}: ShipMapProps) {
  const [mapControls, setMapControls] = useState({
    seamarkOpacity: seamarkOpacity,
    enableSeamarkLayer: enableSeamarkLayer,
    tileServerOption: tileServerOption,
    portFocus: portFocus,
    // Railway layer controls
    enableRailwayLayer: enableRailwayLayer,
    railwayOpacity: railwayOpacity,
    railwayStyle: railwayStyle,
  });

  const [showControlPanel, setShowControlPanel] = useState(showControls);

  // Get coordinates based on port focus or custom values
  const getMapCoordinates = () => {
    if (centerLat && centerLng && zoom) {
      return { lat: centerLat, lng: centerLng, zoom: zoom };
    }
    return PORT_COORDINATES[mapControls.portFocus] || PORT_COORDINATES.rotterdam;
  };

  const coordinates = getMapCoordinates();

  // Configure tile layers based on selection
  const getTileConfiguration = () => {
    const baseConfig = {
      baseTileLayer: {
        url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
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
        attribution: 'Sea marks &copy; <a href="http://www.openseamap.org">OpenSeaMap</a> contributors',
        maxZoom: 18,
        opacity: mapControls.seamarkOpacity / 100,
      });
    }

    // Add OpenRailwayMap layer if enabled
    if (mapControls.enableRailwayLayer) {
      baseConfig.overlayTileLayers.push({
        url: `https://{s}.tiles.openrailwaymap.org/${mapControls.railwayStyle}/{z}/{x}/{y}.png`,
        attribution: 'Railways: <a href="https://www.openstreetmap.org/copyright">&copy; OpenStreetMap contributors</a>, Style: <a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA 2.0</a> <a href="http://www.openrailwaymap.org/">OpenRailwayMap</a>',
        maxZoom: 19,
        opacity: mapControls.railwayOpacity / 100,
      });
    }

    if (mapControls.tileServerOption === "hybrid") {
      // Use satellite imagery as base for hybrid view
      baseConfig.baseTileLayer = {
        url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attribution: "Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community",
        maxZoom: 18,
      };
    }

    return baseConfig;
  };

  const tileConfig = getTileConfiguration();

  const updateControl = (key: keyof typeof mapControls, value: string | number | boolean) => {
    setMapControls(prev => ({ ...prev, [key]: value }));
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Ship className="h-5 w-5 text-blue-600" />
              {title}
            </CardTitle>
            {description && (
              <p className="text-muted-foreground mt-2">{description}</p>
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
              className="relative rounded-lg overflow-hidden border-2 border-blue-200 ship-map-container"
              style={{ height }}
            >
              <BaseLeafletMap
                centerLat={coordinates.lat}
                centerLng={coordinates.lng}
                zoom={coordinates.zoom}
                baseTileLayer={tileConfig.baseTileLayer}
                overlayTileLayers={tileConfig.overlayTileLayers}
                customPopupStyle="maritime-popup"
                enableDataLayers={false}
              />

              {/* Maritime Legend */}
              <div className="absolute bottom-4 left-4 bg-white/95 backdrop-blur-sm rounded-lg p-3 shadow-lg z-[1000] border-2 border-blue-200">
                <h4 className="text-sm font-semibold mb-2 text-blue-800 flex items-center gap-1">
                  <Waves className="h-4 w-4" />
                  Maritime Legend
                </h4>
                <div className="space-y-2">
                  {mapControls.enableSeamarkLayer && (
                    <div className="flex items-center gap-2 text-xs">
                      <div className="w-4 h-3 rounded border border-blue-400 bg-blue-100" />
                      <span className="text-blue-700">Sea Marks & Navigation</span>
                    </div>
                  )}
                  {mapControls.enableRailwayLayer && (
                    <div className="flex items-center gap-2 text-xs">
                      <Train className="h-3 w-3 text-gray-700" />
                      <span className="text-gray-700">
                        Railway {mapControls.railwayStyle === "standard" ? "Infrastructure" : 
                                  mapControls.railwayStyle === "signals" ? "Signals" : "Speed Limits"}
                      </span>
                    </div>
                  )}
                  <div className="flex items-center gap-2 text-xs">
                    <Anchor className="h-3 w-3 text-blue-600" />
                    <span className="text-blue-700">
                      {PORT_COORDINATES[mapControls.portFocus as keyof typeof PORT_COORDINATES] 
                        ? mapControls.portFocus.charAt(0).toUpperCase() + mapControls.portFocus.slice(1) + " Port Area"
                        : "Custom Location"
                      }
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
                    <Ship className="h-5 w-5" />
                    Ship Map Controls
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Port Focus Selection */}
                    {showPortFocusControl && (
                      <div className="space-y-2">
                        <Label className="text-sm font-medium">Port Focus</Label>
                        <Select
                          value={mapControls.portFocus}
                          onValueChange={(value) => updateControl("portFocus", value)}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="rotterdam">Rotterdam (NL)</SelectItem>
                            <SelectItem value="groningen">Groningen (NL)</SelectItem>
                            <SelectItem value="amsterdam">Amsterdam (NL)</SelectItem>
                            <SelectItem value="full">Full View (NL)</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    )}

                    {/* Tile Server Selection */}
                    {showMapStyleControl && (
                      <div className="space-y-2">
                        <Label className="text-sm font-medium">Map Style</Label>
                        <Select
                          value={mapControls.tileServerOption}
                          onValueChange={(value) => updateControl("tileServerOption", value)}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="openseamap">OpenSeaMap Standard</SelectItem>
                            <SelectItem value="hybrid">Satellite + Sea Marks</SelectItem>
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
                              onCheckedChange={(checked) => updateControl("enableSeamarkLayer", checked)}
                            />
                            <Label className="text-sm font-medium">Sea Marks Layer</Label>
                          </div>
                        </div>

                        {mapControls.enableSeamarkLayer && showSeamarkOpacityControl && (
                          <div className="space-y-2">
                            <Label className="text-xs text-blue-700">
                              Opacity: {mapControls.seamarkOpacity}%
                            </Label>
                            <Slider
                              value={[mapControls.seamarkOpacity]}
                              onValueChange={([value]) => updateControl("seamarkOpacity", value)}
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
                              onCheckedChange={(checked) => updateControl("enableRailwayLayer", checked)}
                            />
                            <Label className="text-sm font-medium flex items-center gap-2">
                              <Train className="h-4 w-4" />
                              Railway Layer
                            </Label>
                          </div>
                        </div>

                        {mapControls.enableRailwayLayer && (
                          <div className="space-y-3">
                            {/* Railway Style Selection */}
                            {showRailwayStyleControl && (
                              <div className="space-y-2">
                                <Label className="text-xs text-gray-700">Railway Style</Label>
                                <Select
                                  value={mapControls.railwayStyle}
                                  onValueChange={(value) => updateControl("railwayStyle", value)}
                                >
                                  <SelectTrigger className="h-8 text-xs">
                                    <SelectValue />
                                  </SelectTrigger>
                                  <SelectContent>
                                    <SelectItem value="standard">Infrastructure & Tracks</SelectItem>
                                    <SelectItem value="signals">Railway Signals</SelectItem>
                                    <SelectItem value="maxspeed">Speed Limits</SelectItem>
                                  </SelectContent>
                                </Select>
                              </div>
                            )}

                            {/* Railway Opacity */}
                            {showRailwayOpacityControl && (
                              <div className="space-y-2">
                                <Label className="text-xs text-gray-700">
                                  Opacity: {mapControls.railwayOpacity}%
                                </Label>
                                <Slider
                                  value={[mapControls.railwayOpacity]}
                                  onValueChange={([value]) => updateControl("railwayOpacity", value)}
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

        {/* Statistics Card */}
        <Card>
          <CardContent className="pt-6">
            <div className={`grid grid-cols-1 ${mapControls.enableRailwayLayer ? 'md:grid-cols-4' : 'md:grid-cols-3'} gap-4 text-center`}>
              <div>
                <div className="text-2xl font-bold text-blue-600">
                  {mapControls.enableSeamarkLayer ? "ON" : "OFF"}
                </div>
                <div className="text-sm text-muted-foreground">
                  Sea Marks Layer
                </div>
              </div>
              {mapControls.enableRailwayLayer && (
                <div>
                  <div className="text-2xl font-bold text-gray-600">
                    {mapControls.enableRailwayLayer ? "ON" : "OFF"}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    Railway Layer
                  </div>
                </div>
              )}
              <div>
                <div className="text-2xl font-bold text-green-600">
                  {mapControls.enableSeamarkLayer ? mapControls.seamarkOpacity : 
                   mapControls.enableRailwayLayer ? mapControls.railwayOpacity : mapControls.seamarkOpacity}%
                </div>
                <div className="text-sm text-muted-foreground">
                  Layer Opacity
                </div>
              </div>
              <div>
                <div className="text-2xl font-bold text-orange-600">
                  {mapControls.portFocus.toUpperCase()}
                </div>
                <div className="text-sm text-muted-foreground">
                  Port Focus
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </CardContent>
    </Card>
  );
} 