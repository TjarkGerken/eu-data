"use client";

import { useState, useEffect, useRef } from "react";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ImageDropdown } from "@/components/image-dropdown";
import { MultiSelectReferences } from "@/components/ui/multi-select-references";
import { CitationInsertionButton } from "@/components/admin/citation-insertion-button";
import { Trash2, Layers, Settings, Plus } from "lucide-react";
import { getFieldError, type ValidationError } from "@/lib/validation";
import { Switch } from "@/components/ui/switch";
import { mapTileService, MapLayerMetadata } from "@/lib/map-tile-service";
import LayerManager from "./layer-manager";

interface BlockTypeFieldsProps {
  blockType: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onDataChange: (newData: any) => void;
  validationErrors: ValidationError[];
  title?: string;
  content?: string;
  onTitleChange?: (title: string) => void;
  onContentChange?: (content: string) => void;
  language?: "en" | "de";
  mode?: "shared" | "language-specific" | "all";
}

interface MapLayerData {
  selectedLayers?: string[];
  height?: string;
  centerLat?: string | number;
  centerLng?: string | number;
  zoom?: string | number;
  autoFitBounds?: boolean;
  enableLayerControls?: boolean;
  // Admin control over user-facing controls
  showLayerToggles?: boolean;
  showOpacityControls?: boolean;
  showDownloadButtons?: boolean;
  // Pre-defined layer opacities
  predefinedOpacities?: Record<string, number>;
}

interface ShipMapData {
  height?: string;
  centerLat?: string | number;
  centerLng?: string | number;
  zoom?: string | number;
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

interface MapLayerSelectorProps {
  data: MapLayerData;
  onDataChange: (newData: MapLayerData) => void;
}

function MapLayerSelector({ data, onDataChange }: MapLayerSelectorProps) {
  const [availableLayers, setAvailableLayers] = useState<MapLayerMetadata[]>(
    []
  );
  const [loading, setLoading] = useState(true);
  const [showLayerManager, setShowLayerManager] = useState(false);

  useEffect(() => {
    loadLayers();
  }, []);

  const loadLayers = async () => {
    try {
      const layers = await mapTileService.getAvailableLayers();
      setAvailableLayers(Array.isArray(layers) ? layers : []);
    } catch (error) {
      console.error("Failed to load layers:", error);
      setAvailableLayers([]);
    } finally {
      setLoading(false);
    }
  };

  const updateDataField = (
    field: keyof MapLayerData,
    value: string | boolean | string[] | number | Record<string, number>
  ) => {
    onDataChange({ ...data, [field]: value });
  };

  const toggleLayer = (layerId: string) => {
    const selectedLayers = data?.selectedLayers || [];
    const isSelected = selectedLayers.includes(layerId);

    const newLayers = isSelected
      ? selectedLayers.filter((id: string) => id !== layerId)
      : [...selectedLayers, layerId];

    updateDataField("selectedLayers", newLayers);
  };

  return (
    <div className="space-y-4">
      <div className="space-y-1">
        <Label>Map Height</Label>
        <Input
          value={data?.height || "600px"}
          onChange={(e) => updateDataField("height", e.target.value)}
          placeholder="e.g., 600px"
        />
      </div>

      <div className="space-y-1">
        <Label>Map Center (Latitude, Longitude)</Label>
        <div className="grid grid-cols-2 gap-2">
          <Input
            value={data?.centerLat || "52.1326"}
            onChange={(e) =>
              updateDataField(
                "centerLat",
                parseFloat(e.target.value) || 52.1326
              )
            }
            placeholder="52.1326"
            type="number"
            step="0.0001"
          />
          <Input
            value={data?.centerLng || "5.2913"}
            onChange={(e) =>
              updateDataField("centerLng", parseFloat(e.target.value) || 5.2913)
            }
            placeholder="5.2913"
            type="number"
            step="0.0001"
          />
        </div>
        <p className="text-xs text-muted-foreground">
          Default: Netherlands center (52.1326, 5.2913)
        </p>
      </div>

      <div className="space-y-1">
        <Label>Initial Zoom Level</Label>
        <Input
          value={data?.zoom || "8"}
          onChange={(e) =>
            updateDataField("zoom", parseInt(e.target.value) || 8)
          }
          placeholder="8"
          type="number"
          min="1"
          max="18"
        />
        <p className="text-xs text-muted-foreground">
          Zoom level: 1 (world) to 18 (street level)
        </p>
      </div>

      <div className="flex items-center space-x-2">
        <Switch
          id="enable-layer-controls"
          checked={data?.enableLayerControls !== false}
          onCheckedChange={(checked) =>
            updateDataField("enableLayerControls", checked)
          }
        />
        <Label htmlFor="enable-layer-controls">Enable Layer Controls</Label>
      </div>

      <div className="flex items-center space-x-2">
        <Switch
          id="auto-fit-bounds"
          checked={data?.autoFitBounds || false}
          onCheckedChange={(checked) =>
            updateDataField("autoFitBounds", checked)
          }
        />
        <Label htmlFor="auto-fit-bounds">Auto Fit to Layer Bounds</Label>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label>Available Layers</Label>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowLayerManager(!showLayerManager)}
          >
            <Settings className="h-4 w-4 mr-2" />
            Manage Layers
          </Button>
        </div>

        {showLayerManager && (
          <Card>
            <CardContent className="pt-4">
              <LayerManager />
            </CardContent>
          </Card>
        )}

        {loading ? (
          <div className="text-sm text-muted-foreground">Loading layers...</div>
        ) : availableLayers.length === 0 ? (
          <div className="text-sm text-muted-foreground">
            No layers available. Upload layers using the manager above.
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-2">
            {availableLayers.map((layer) => {
              const isSelected = (data?.selectedLayers || []).includes(
                layer.id
              );
              return (
                <Card
                  key={layer.id}
                  className={`cursor-pointer transition-colors ${
                    isSelected
                      ? "border-primary bg-primary/5"
                      : "hover:border-muted-foreground/50"
                  }`}
                  onClick={() => toggleLayer(layer.id)}
                >
                  <CardContent className="p-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Layers className="h-4 w-4" />
                        <div>
                          <div className="font-medium text-sm">
                            {layer.name}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {layer.dataType} • {layer.format}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {isSelected && (
                          <Badge variant="default" className="text-xs">
                            Selected
                          </Badge>
                        )}
                        <Badge variant="outline" className="text-xs">
                          {layer.dataType}
                        </Badge>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {data?.selectedLayers && data.selectedLayers.length > 0 && (
        <div className="space-y-2">
          <Label>Selected Layers ({data.selectedLayers.length})</Label>
          <div className="flex flex-wrap gap-2">
            {data.selectedLayers.map((layerId: string) => {
              const layer = availableLayers.find((l) => l.id === layerId);
              return (
                <Badge
                  key={layerId}
                  variant="secondary"
                  className="cursor-pointer"
                  onClick={() => toggleLayer(layerId)}
                >
                  {layer?.name || layerId}
                  <Trash2 className="h-3 w-3 ml-1" />
                </Badge>
              );
            })}
          </div>
        </div>
      )}

      <div className="border-t pt-4 mt-4">
        <h4 className="text-sm font-medium mb-3">User Control Visibility</h4>
        <div className="grid grid-cols-2 gap-4">
          <div className="flex items-center space-x-2">
            <Switch
              id="show-layer-toggles"
              checked={data?.showLayerToggles !== false}
              onCheckedChange={(checked) =>
                updateDataField("showLayerToggles", checked)
              }
            />
            <Label htmlFor="show-layer-toggles" className="text-sm">
              Layer Toggle Controls
            </Label>
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              id="show-opacity-controls"
              checked={data?.showOpacityControls !== false}
              onCheckedChange={(checked) =>
                updateDataField("showOpacityControls", checked)
              }
            />
            <Label htmlFor="show-opacity-controls" className="text-sm">
              Opacity Controls
            </Label>
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              id="show-download-buttons"
              checked={data?.showDownloadButtons !== false}
              onCheckedChange={(checked) =>
                updateDataField("showDownloadButtons", checked)
              }
            />
            <Label htmlFor="show-download-buttons" className="text-sm">
              Download Buttons
            </Label>
          </div>
        </div>

        {data?.selectedLayers && data.selectedLayers.length > 0 && (
          <div className="mt-4">
            <h5 className="text-sm font-medium mb-2">
              Pre-defined Layer Opacities
            </h5>
            <div className="space-y-2">
              {data.selectedLayers.map((layerId: string) => {
                const layer = availableLayers.find((l) => l.id === layerId);
                const currentOpacity =
                  data?.predefinedOpacities?.[layerId] || 80;
                return (
                  <div key={layerId} className="flex items-center space-x-2">
                    <Label className="text-xs w-32 truncate">
                      {layer?.name || layerId}
                    </Label>
                    <Input
                      type="range"
                      min="0"
                      max="100"
                      step="1"
                      value={currentOpacity}
                      onChange={(e) => {
                        const newOpacities = {
                          ...(data?.predefinedOpacities || {}),
                        };
                        newOpacities[layerId] = parseInt(e.target.value);
                        updateDataField("predefinedOpacities", newOpacities);
                      }}
                      className="flex-1"
                    />
                    <span className="text-xs w-12">{currentOpacity}%</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

interface ShipMapSelectorProps {
  data: ShipMapData;
  onDataChange: (newData: ShipMapData) => void;
}

function ShipMapSelector({ data, onDataChange }: ShipMapSelectorProps) {
  const updateDataField = (
    field: keyof ShipMapData,
    value: string | boolean | number
  ) => {
    onDataChange({ ...data, [field]: value });
  };

  return (
    <div className="space-y-4">
      <div className="space-y-1">
        <Label>Map Height</Label>
        <Input
          value={data?.height || "600px"}
          onChange={(e) => updateDataField("height", e.target.value)}
          placeholder="e.g., 600px"
        />
      </div>

      <div className="space-y-1">
        <Label>Port Focus</Label>
        <Select
          value={data?.portFocus || "rotterdam"}
          onValueChange={(value) => updateDataField("portFocus", value)}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="rotterdam">Rotterdam (NL)</SelectItem>
            <SelectItem value="groningen">Groningen (NL)</SelectItem>
            <SelectItem value="amsterdam">Amsterdam (NL)</SelectItem>
            <SelectItem value="full">Full View (NL)</SelectItem>
            <SelectItem value="custom">Custom Location</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {data?.portFocus === "custom" && (
        <div className="space-y-1">
          <Label>Custom Coordinates (Latitude, Longitude)</Label>
          <div className="grid grid-cols-2 gap-2">
            <Input
              value={data?.centerLat || "52.1326"}
              onChange={(e) =>
                updateDataField(
                  "centerLat",
                  parseFloat(e.target.value) || 52.1326
                )
              }
              placeholder="52.1326"
              type="number"
              step="0.0001"
            />
            <Input
              value={data?.centerLng || "5.2913"}
              onChange={(e) =>
                updateDataField(
                  "centerLng",
                  parseFloat(e.target.value) || 5.2913
                )
              }
              placeholder="5.2913"
              type="number"
              step="0.0001"
            />
          </div>
        </div>
      )}

      <div className="space-y-1">
        <Label>Initial Zoom Level</Label>
        <Input
          value={data?.zoom || "12"}
          onChange={(e) =>
            updateDataField("zoom", parseInt(e.target.value) || 12)
          }
          placeholder="12"
          type="number"
          min="1"
          max="18"
        />
        <p className="text-xs text-muted-foreground">
          Zoom level: 1 (world) to 18 (street level)
        </p>
      </div>

      <div className="space-y-1">
        <Label>Map Style</Label>
        <Select
          value={data?.tileServerOption || "openseamap"}
          onValueChange={(value) => updateDataField("tileServerOption", value)}
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

      <div className="flex items-center space-x-2">
        <Switch
          id="enable-seamark-layer"
          checked={data?.enableSeamarkLayer !== false}
          onCheckedChange={(checked) =>
            updateDataField("enableSeamarkLayer", checked)
          }
        />
        <Label htmlFor="enable-seamark-layer">Enable Sea Marks Layer</Label>
      </div>

      {data?.enableSeamarkLayer !== false && (
        <div className="space-y-1">
          <Label>Sea Marks Opacity: {data?.seamarkOpacity || 80}%</Label>
          <Input
            type="range"
            min="10"
            max="100"
            step="10"
            value={data?.seamarkOpacity || 80}
            onChange={(e) =>
              updateDataField("seamarkOpacity", parseInt(e.target.value))
            }
            className="w-full"
          />
        </div>
      )}

      <div className="flex items-center space-x-2">
        <Switch
          id="show-controls"
          checked={data?.showControls !== false}
          onCheckedChange={(checked) =>
            updateDataField("showControls", checked)
          }
        />
        <Label htmlFor="show-controls">Show Control Panel</Label>
      </div>

      <div className="flex items-center space-x-2">
        <Switch
          id="enable-railway-layer"
          checked={data?.enableRailwayLayer || false}
          onCheckedChange={(checked) =>
            updateDataField("enableRailwayLayer", checked)
          }
        />
        <Label htmlFor="enable-railway-layer">Enable Railway Layer</Label>
      </div>

      {data?.enableRailwayLayer && (
        <>
          <div className="space-y-1">
            <Label>Railway Style</Label>
            <Select
              value={data?.railwayStyle || "standard"}
              onValueChange={(value) => updateDataField("railwayStyle", value)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="standard">
                  Infrastructure & Tracks
                </SelectItem>
                <SelectItem value="signals">Railway Signals</SelectItem>
                <SelectItem value="maxspeed">Speed Limits</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1">
            <Label>Railway Opacity: {data?.railwayOpacity || 70}%</Label>
            <Input
              type="range"
              min="10"
              max="100"
              step="10"
              value={data?.railwayOpacity || 70}
              onChange={(e) =>
                updateDataField("railwayOpacity", parseInt(e.target.value))
              }
              className="w-full"
            />
          </div>
        </>
      )}

      <div className="border-t pt-4 mt-4">
        <h4 className="text-sm font-medium mb-3">User Control Visibility</h4>
        <div className="grid grid-cols-2 gap-4">
          <div className="flex items-center space-x-2">
            <Switch
              id="show-port-focus-control"
              checked={data?.showPortFocusControl !== false}
              onCheckedChange={(checked) =>
                updateDataField("showPortFocusControl", checked)
              }
            />
            <Label htmlFor="show-port-focus-control" className="text-sm">
              Port Focus Control
            </Label>
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              id="show-map-style-control"
              checked={data?.showMapStyleControl !== false}
              onCheckedChange={(checked) =>
                updateDataField("showMapStyleControl", checked)
              }
            />
            <Label htmlFor="show-map-style-control" className="text-sm">
              Map Style Control
            </Label>
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              id="show-seamark-layer-control"
              checked={data?.showSeamarkLayerControl !== false}
              onCheckedChange={(checked) =>
                updateDataField("showSeamarkLayerControl", checked)
              }
            />
            <Label htmlFor="show-seamark-layer-control" className="text-sm">
              Seamark Layer Control
            </Label>
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              id="show-seamark-opacity-control"
              checked={data?.showSeamarkOpacityControl !== false}
              onCheckedChange={(checked) =>
                updateDataField("showSeamarkOpacityControl", checked)
              }
            />
            <Label htmlFor="show-seamark-opacity-control" className="text-sm">
              Seamark Opacity Control
            </Label>
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              id="show-railway-layer-control"
              checked={data?.showRailwayLayerControl !== false}
              onCheckedChange={(checked) =>
                updateDataField("showRailwayLayerControl", checked)
              }
            />
            <Label htmlFor="show-railway-layer-control" className="text-sm">
              Railway Layer Control
            </Label>
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              id="show-railway-style-control"
              checked={data?.showRailwayStyleControl !== false}
              onCheckedChange={(checked) =>
                updateDataField("showRailwayStyleControl", checked)
              }
            />
            <Label htmlFor="show-railway-style-control" className="text-sm">
              Railway Style Control
            </Label>
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              id="show-railway-opacity-control"
              checked={data?.showRailwayOpacityControl !== false}
              onCheckedChange={(checked) =>
                updateDataField("showRailwayOpacityControl", checked)
              }
            />
            <Label htmlFor="show-railway-opacity-control" className="text-sm">
              Railway Opacity Control
            </Label>
          </div>
        </div>
      </div>
    </div>
  );
}

export function BlockTypeFields({
  blockType,
  data,
  onDataChange,
  validationErrors,
  title,
  content,
  onTitleChange,
  onContentChange,
  language,
  mode = "all",
}: BlockTypeFieldsProps) {
  const markdownTextareaRef = useRef<HTMLTextAreaElement>(null);
  const [availableReferences, setAvailableReferences] = useState<
    Array<{
      id: string;
      title: string;
      authors: string[];
      year: number;
      type: "journal" | "report" | "dataset" | "book";
    }>
  >([]);

  useEffect(() => {
    if (blockType === "markdown") {
      loadReferences();
    }
  }, [blockType]);

  const loadReferences = async () => {
    try {
      const response = await fetch("/api/content");
      const data = await response.json();
      setAvailableReferences(data.references || []);
    } catch (error) {
      console.error("Failed to load references:", error);
    }
  };
  const updateDataField = (path: string, value: unknown) => {
    const newData = { ...data };
    const pathParts = path.split(".");
    let current: Record<string, unknown> = newData;

    for (let i = 0; i < pathParts.length - 1; i++) {
      if (!current[pathParts[i]]) current[pathParts[i]] = {};
      current = current[pathParts[i]] as Record<string, unknown>;
    }

    current[pathParts[pathParts.length - 1]] = value;
    onDataChange(newData);
  };

  const addArrayItem = (arrayPath: string, defaultItem: unknown) => {
    const currentArray = getNestedValue(data, arrayPath) || [];
    updateDataField(arrayPath, [...(currentArray as unknown[]), defaultItem]);
  };

  const removeArrayItem = (arrayPath: string, index: number) => {
    const currentArray = getNestedValue(data, arrayPath) || [];
    const newArray = (currentArray as unknown[]).filter(
      (_: unknown, i: number) => i !== index
    );
    updateDataField(arrayPath, newArray);
  };

  const updateArrayItem = (
    arrayPath: string,
    index: number,
    field: string,
    value: unknown
  ) => {
    const currentArray = getNestedValue(data, arrayPath) || [];
    const newArray = [...(currentArray as Record<string, unknown>[])];
    newArray[index] = { ...newArray[index], [field]: value };
    updateDataField(arrayPath, newArray);
  };

  const getNestedValue = (
    obj: Record<string, unknown>,
    path: string
  ): unknown => {
    return path.split(".").reduce((current: unknown, key: string) => {
      return current && typeof current === "object" && !Array.isArray(current)
        ? (current as Record<string, unknown>)[key]
        : undefined;
    }, obj);
  };

  const renderFieldError = (fieldPath: string) => {
    const error = getFieldError(validationErrors, fieldPath);
    return error ? <p className="text-sm text-red-500 mt-1">{error}</p> : null;
  };

  // Block types that actually use and display the title field
  const blockTypesWithTitle = [
    "callout",
    "interactive-callout",
    "animated-statistics",
    "climate-dashboard",
    "interactive-map",
    "ship-map",
    "impact-comparison",
    "kpi-showcase",
  ];

  const renderLanguageSpecificFields = () => (
    <>
      {blockTypesWithTitle.includes(blockType) && (
        <div className="space-y-1">
          <Label>Section Title (optional)</Label>
          <Input
            value={title || ""}
            onChange={(e) => onTitleChange?.(e.target.value)}
            placeholder="Enter section title..."
          />
          {renderFieldError("title")}
        </div>
      )}
    </>
  );

  const renderSharedFields = () => {
    switch (blockType) {
      case "callout":
        return (
          <div className="space-y-4">
            <div className="space-y-1">
              <Label>Variant *</Label>
              <Select
                value={data?.variant || "info"}
                onValueChange={(value) => updateDataField("variant", value)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="success">Success</SelectItem>
                  <SelectItem value="warning">Warning</SelectItem>
                  <SelectItem value="info">Info</SelectItem>
                  <SelectItem value="error">Error</SelectItem>
                </SelectContent>
              </Select>
              {renderFieldError("data.variant")}
            </div>
          </div>
        );

      case "interactive-callout":
        return (
          <div className="space-y-4">
            <div className="space-y-1">
              <Label>Variant *</Label>
              <Select
                value={data?.variant || "info"}
                onValueChange={(value) => updateDataField("variant", value)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="success">Success</SelectItem>
                  <SelectItem value="warning">Warning</SelectItem>
                  <SelectItem value="info">Info</SelectItem>
                  <SelectItem value="error">Error</SelectItem>
                </SelectContent>
              </Select>
              {renderFieldError("data.variant")}
            </div>
            <div className="space-y-1">
              <Label>Expanded Content</Label>
              <Textarea
                value={data?.expandedContent || ""}
                onChange={(e) =>
                  updateDataField("expandedContent", e.target.value)
                }
                placeholder="Content to show when expanded..."
                rows={3}
              />
              {renderFieldError("data.expandedContent")}
            </div>
          </div>
        );

      case "interactive-map":
        return <MapLayerSelector data={data} onDataChange={onDataChange} />;

      case "ship-map":
        return <ShipMapSelector data={data} onDataChange={onDataChange} />;

      case "animated-statistics":
        return (
          <div className="space-y-4">
            <Label>Statistics Configuration *</Label>
            {renderFieldError("data.stats")}
            {((data?.stats as Record<string, unknown>[]) || []).map(
              (stat: Record<string, unknown>, index: number) => (
                <Card key={index}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm">
                        Statistic {index + 1}
                      </CardTitle>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => removeArrayItem("stats", index)}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label>Icon *</Label>
                        <Select
                          value={(stat?.icon as string) || "thermometer"}
                          onValueChange={(value) =>
                            updateArrayItem("stats", index, "icon", value)
                          }
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="thermometer">
                              Thermometer
                            </SelectItem>
                            <SelectItem value="droplets">Droplets</SelectItem>
                            <SelectItem value="wind">Wind</SelectItem>
                            <SelectItem value="zap">Zap</SelectItem>
                            <SelectItem value="barchart">Bar Chart</SelectItem>
                            <SelectItem value="globe">Globe</SelectItem>
                            <SelectItem value="trending">Trending</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label>Value *</Label>
                        <Input
                          value={(stat?.value as string) || ""}
                          onChange={(e) =>
                            updateArrayItem(
                              "stats",
                              index,
                              "value",
                              e.target.value
                            )
                          }
                          placeholder="e.g., +1.2°C"
                        />
                      </div>
                    </div>
                    <div>
                      <Label>Label *</Label>
                      <Input
                        value={(stat?.label as string) || ""}
                        onChange={(e) =>
                          updateArrayItem(
                            "stats",
                            index,
                            "label",
                            e.target.value
                          )
                        }
                        placeholder="e.g., Temperature Rise"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label>Change (optional)</Label>
                        <Input
                          value={(stat?.change as string) || ""}
                          onChange={(e) =>
                            updateArrayItem(
                              "stats",
                              index,
                              "change",
                              e.target.value
                            )
                          }
                          placeholder="e.g., since 1990"
                        />
                      </div>
                      <div>
                        <Label>Trend</Label>
                        <Select
                          value={(stat?.trend as string) || "up"}
                          onValueChange={(value) =>
                            updateArrayItem("stats", index, "trend", value)
                          }
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="up">Up</SelectItem>
                            <SelectItem value="down">Down</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                    <div>
                      <Label>Color</Label>
                      <Select
                        value={(stat?.color as string) || "text-red-500"}
                        onValueChange={(value) =>
                          updateArrayItem("stats", index, "color", value)
                        }
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="text-red-500">Red</SelectItem>
                          <SelectItem value="text-blue-500">Blue</SelectItem>
                          <SelectItem value="text-green-500">Green</SelectItem>
                          <SelectItem value="text-orange-500">
                            Orange
                          </SelectItem>
                          <SelectItem value="text-purple-500">
                            Purple
                          </SelectItem>
                          <SelectItem value="text-[#2d5a3d]">
                            Theme Green
                          </SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </CardContent>
                </Card>
              )
            )}
            <Button
              type="button"
              size="sm"
              onClick={() =>
                addArrayItem("stats", {
                  icon: "thermometer",
                  value: "",
                  label: "",
                  change: "",
                  trend: "up",
                  color: "text-red-500",
                })
              }
            >
              <Plus className="w-4 h-4 mr-2" />
              Add Statistic
            </Button>

            <div className="grid grid-cols-2 gap-3 pt-4 border-t">
              <div>
                <Label>Grid Columns</Label>
                <Select
                  value={String(data?.gridColumns || 4)}
                  onValueChange={(value) =>
                    updateDataField("gridColumns", parseInt(value))
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1">1 Column</SelectItem>
                    <SelectItem value="2">2 Columns</SelectItem>
                    <SelectItem value="3">3 Columns</SelectItem>
                    <SelectItem value="4">4 Columns</SelectItem>
                    <SelectItem value="5">5 Columns</SelectItem>
                    <SelectItem value="6">6 Columns</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Color Scheme</Label>
                <Select
                  value={data?.colorScheme || "default"}
                  onValueChange={(value) =>
                    updateDataField("colorScheme", value)
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="default">Default</SelectItem>
                    <SelectItem value="green">Green</SelectItem>
                    <SelectItem value="blue">Blue</SelectItem>
                    <SelectItem value="purple">Purple</SelectItem>
                    <SelectItem value="orange">Orange</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
        );

      case "climate-dashboard":
        return (
          <div className="space-y-4">
            <Label>Dashboard Metrics *</Label>
            {renderFieldError("data.metrics")}
            {((data?.metrics as Record<string, unknown>[]) || []).map(
              (metric: Record<string, unknown>, index: number) => (
                <Card key={index}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm">
                        Metric {index + 1}
                      </CardTitle>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => removeArrayItem("metrics", index)}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label>Title *</Label>
                        <Input
                          value={(metric?.title as string) || ""}
                          onChange={(e) =>
                            updateArrayItem(
                              "metrics",
                              index,
                              "title",
                              e.target.value
                            )
                          }
                          placeholder="e.g., Global Temperature"
                        />
                      </div>
                      <div>
                        <Label>Value *</Label>
                        <Input
                          value={(metric?.value as string) || ""}
                          onChange={(e) =>
                            updateArrayItem(
                              "metrics",
                              index,
                              "value",
                              e.target.value
                            )
                          }
                          placeholder="e.g., +1.2°C"
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-3">
                      <div>
                        <Label>Change</Label>
                        <Input
                          value={(metric?.change as string) || ""}
                          onChange={(e) =>
                            updateArrayItem(
                              "metrics",
                              index,
                              "change",
                              e.target.value
                            )
                          }
                          placeholder="e.g., +0.1°C"
                        />
                      </div>
                      <div>
                        <Label>Trend</Label>
                        <Select
                          value={(metric?.trend as string) || "up"}
                          onValueChange={(value) =>
                            updateArrayItem("metrics", index, "trend", value)
                          }
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="up">Up</SelectItem>
                            <SelectItem value="down">Down</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label>Status</Label>
                        <Select
                          value={(metric?.status as string) || "success"}
                          onValueChange={(value) =>
                            updateArrayItem("metrics", index, "status", value)
                          }
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="success">Success</SelectItem>
                            <SelectItem value="warning">Warning</SelectItem>
                            <SelectItem value="danger">Danger</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label>Progress (%)</Label>
                        <Input
                          type="number"
                          min="0"
                          max="100"
                          value={(metric?.progress as number) || 0}
                          onChange={(e) =>
                            updateArrayItem(
                              "metrics",
                              index,
                              "progress",
                              parseInt(e.target.value)
                            )
                          }
                          placeholder="0-100"
                        />
                      </div>
                      <div>
                        <Label>Target</Label>
                        <Input
                          value={(metric?.target as string) || ""}
                          onChange={(e) =>
                            updateArrayItem(
                              "metrics",
                              index,
                              "target",
                              e.target.value
                            )
                          }
                          placeholder="e.g., 1.5°C"
                        />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )
            )}
            <Button
              type="button"
              size="sm"
              onClick={() =>
                addArrayItem("metrics", {
                  title: "",
                  value: "",
                  change: "",
                  trend: "up",
                  status: "success",
                  progress: 50,
                  target: "",
                })
              }
            >
              <Plus className="w-4 h-4 mr-2" />
              Add Metric
            </Button>
          </div>
        );

      case "impact-comparison":
        return (
          <div className="space-y-4">
            <Label>Impact Comparisons *</Label>
            {renderFieldError("data.comparisons")}
            {((data?.comparisons as Record<string, unknown>[]) || []).map(
              (comparison: Record<string, unknown>, index: number) => (
                <Card key={index}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm">
                        Comparison {index + 1}
                      </CardTitle>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => removeArrayItem("comparisons", index)}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div>
                      <Label>Category *</Label>
                      <Input
                        value={(comparison?.category as string) || ""}
                        onChange={(e) =>
                          updateArrayItem(
                            "comparisons",
                            index,
                            "category",
                            e.target.value
                          )
                        }
                        placeholder="e.g., Temperature"
                      />
                    </div>
                    <div className="grid grid-cols-3 gap-3">
                      <div>
                        <Label>Current Value *</Label>
                        <Input
                          type="number"
                          step="0.1"
                          value={(comparison?.currentValue as number) || 0}
                          onChange={(e) =>
                            updateArrayItem(
                              "comparisons",
                              index,
                              "currentValue",
                              parseFloat(e.target.value)
                            )
                          }
                          placeholder="1.2"
                        />
                      </div>
                      <div>
                        <Label>Projected Value *</Label>
                        <Input
                          type="number"
                          step="0.1"
                          value={(comparison?.projectedValue as number) || 0}
                          onChange={(e) =>
                            updateArrayItem(
                              "comparisons",
                              index,
                              "projectedValue",
                              parseFloat(e.target.value)
                            )
                          }
                          placeholder="2.0"
                        />
                      </div>
                      <div>
                        <Label>Unit *</Label>
                        <Input
                          value={(comparison?.unit as string) || ""}
                          onChange={(e) =>
                            updateArrayItem(
                              "comparisons",
                              index,
                              "unit",
                              e.target.value
                            )
                          }
                          placeholder="°C"
                        />
                      </div>
                    </div>
                    <div>
                      <Label>Severity</Label>
                      <Select
                        value={(comparison?.severity as string) || "medium"}
                        onValueChange={(value) =>
                          updateArrayItem(
                            "comparisons",
                            index,
                            "severity",
                            value
                          )
                        }
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="low">Low</SelectItem>
                          <SelectItem value="medium">Medium</SelectItem>
                          <SelectItem value="high">High</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </CardContent>
                </Card>
              )
            )}
            <Button
              type="button"
              size="sm"
              onClick={() =>
                addArrayItem("comparisons", {
                  category: "",
                  currentValue: 0,
                  projectedValue: 0,
                  unit: "",
                  severity: "medium",
                })
              }
            >
              <Plus className="w-4 h-4 mr-2" />
              Add Comparison
            </Button>
          </div>
        );

      case "kpi-showcase":
        return (
          <div className="space-y-4">
            <Label>KPI Configuration *</Label>
            {renderFieldError("data.kpis")}
            {((data?.kpis as Record<string, unknown>[]) || []).map(
              (kpi: Record<string, unknown>, index: number) => (
                <Card key={index}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm">KPI {index + 1}</CardTitle>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => removeArrayItem("kpis", index)}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label>Title *</Label>
                        <Input
                          value={(kpi?.title as string) || ""}
                          onChange={(e) =>
                            updateArrayItem(
                              "kpis",
                              index,
                              "title",
                              e.target.value
                            )
                          }
                          placeholder="e.g., Global Temperature"
                        />
                      </div>
                      <div>
                        <Label>Value *</Label>
                        <Input
                          value={(kpi?.value as string) || ""}
                          onChange={(e) =>
                            updateArrayItem(
                              "kpis",
                              index,
                              "value",
                              e.target.value
                            )
                          }
                          placeholder="e.g., +1.2"
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label>Unit</Label>
                        <Input
                          value={(kpi?.unit as string) || ""}
                          onChange={(e) =>
                            updateArrayItem(
                              "kpis",
                              index,
                              "unit",
                              e.target.value
                            )
                          }
                          placeholder="e.g., °C"
                        />
                      </div>
                      <div>
                        <Label>Trend</Label>
                        <Select
                          value={(kpi?.trend as string) || "stable"}
                          onValueChange={(value) =>
                            updateArrayItem("kpis", index, "trend", value)
                          }
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="up">Up</SelectItem>
                            <SelectItem value="down">Down</SelectItem>
                            <SelectItem value="stable">Stable</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label>Change Value</Label>
                        <Input
                          value={(kpi?.changeValue as string) || ""}
                          onChange={(e) =>
                            updateArrayItem(
                              "kpis",
                              index,
                              "changeValue",
                              e.target.value
                            )
                          }
                          placeholder="e.g., +0.1°C since last year"
                        />
                      </div>
                      <div>
                        <Label>Color</Label>
                        <Select
                          value={(kpi?.color as string) || "text-[#2d5a3d]"}
                          onValueChange={(value) =>
                            updateArrayItem("kpis", index, "color", value)
                          }
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="text-red-600">Red</SelectItem>
                            <SelectItem value="text-blue-600">Blue</SelectItem>
                            <SelectItem value="text-green-600">
                              Green
                            </SelectItem>
                            <SelectItem value="text-orange-600">
                              Orange
                            </SelectItem>
                            <SelectItem value="text-purple-600">
                              Purple
                            </SelectItem>
                            <SelectItem value="text-[#2d5a3d]">
                              Theme Green
                            </SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )
            )}
            <Button
              type="button"
              size="sm"
              onClick={() =>
                addArrayItem("kpis", {
                  title: "",
                  value: "",
                  unit: "",
                  trend: "stable",
                  changeValue: "",
                  color: "text-[#2d5a3d]",
                })
              }
            >
              <Plus className="w-4 h-4 mr-2" />
              Add KPI
            </Button>

            <div className="grid grid-cols-2 gap-3 pt-4 border-t">
              <div>
                <Label>Grid Columns</Label>
                <Select
                  value={String(data?.gridColumns || 3)}
                  onValueChange={(value) =>
                    updateDataField("gridColumns", parseInt(value))
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1">1 Column</SelectItem>
                    <SelectItem value="2">2 Columns</SelectItem>
                    <SelectItem value="3">3 Columns</SelectItem>
                    <SelectItem value="4">4 Columns</SelectItem>
                    <SelectItem value="5">5 Columns</SelectItem>
                    <SelectItem value="6">6 Columns</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Display Format</Label>
                <Select
                  value={data?.displayFormat || "card"}
                  onValueChange={(value) =>
                    updateDataField("displayFormat", value)
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="card">Card Format</SelectItem>
                    <SelectItem value="compact">Compact Format</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
        );

      case "visualization":
        return (
          <div className="space-y-4">
            <div className="space-y-1">
              <Label>Visualization Type *</Label>
              <Select
                value={data?.type || "chart"}
                onValueChange={(value) => updateDataField("type", value)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="map">Map</SelectItem>
                  <SelectItem value="chart">Chart</SelectItem>
                  <SelectItem value="trend">Trend</SelectItem>
                  <SelectItem value="gauge">Gauge</SelectItem>
                </SelectContent>
              </Select>
              {renderFieldError("data.type")}
            </div>
            <div className="space-y-1">
              <Label>Image Selection</Label>
              <ImageDropdown
                selectedImageId={data?.imageId}
                onImageChange={(imageId, imageData) => {
                  const newData = { ...data };
                  newData.imageId = imageId;
                  if (imageData) {
                    newData.imageCategory = imageData.category;
                    newData.imageScenario = imageData.scenario;
                    if (imageData.caption) {
                      console.log(imageData);
                      newData.captionEn = imageData.caption.en;
                      newData.captionDe = imageData.caption.de;
                    }
                  }
                  onDataChange(newData);
                }}
                placeholder="Select visualization image..."
              />
            </div>
            <div className="space-y-1">
              <Label>References</Label>
              <MultiSelectReferences
                selectedReferenceIds={data?.references || []}
                onSelectionChange={(ids) => updateDataField("references", ids)}
                placeholder="Select references..."
              />
            </div>
          </div>
        );

      case "animated-quote":
        return (
          <div className="space-y-4">
            <div className="space-y-1">
              <Label>References</Label>
              <MultiSelectReferences
                selectedReferenceIds={data?.references || []}
                onSelectionChange={(ids) => updateDataField("references", ids)}
                placeholder="Select references..."
              />
            </div>
          </div>
        );

      default:
        return (
          <div className="space-y-1">
            <Label>References</Label>
            <MultiSelectReferences
              selectedReferenceIds={data?.references || []}
              onSelectionChange={(ids) => updateDataField("references", ids)}
              placeholder="Select references..."
            />
          </div>
        );
    }
  };

  const renderLanguageSpecificFieldsForType = () => {
    switch (blockType) {
      case "markdown":
        console.log(content);
        return (
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <Label>Content</Label>
              <CitationInsertionButton
                textareaRef={markdownTextareaRef}
                onContentChange={(newContent) => onContentChange?.(newContent)}
                availableReferences={availableReferences}
              />
            </div>
            <Textarea
              ref={markdownTextareaRef}
              value={content || ""}
              onChange={(e) => onContentChange?.(e.target.value)}
              placeholder="Enter markdown content... Use \cite{ReadableId} for citations (e.g., \cite{Smith2023})."
              rows={10}
            />
            <div className="text-xs text-muted-foreground">
              Use <code>\cite{`{ReadableId}`}</code> to insert citations.
              Example: <code>\cite{`{Smith2023}`}</code>
            </div>
            {renderFieldError("content")}
          </div>
        );

      case "interactive-map":
        return renderLanguageSpecificFields();

      case "ship-map":
        return renderLanguageSpecificFields();

      case "animated-statistics":
        return (
          <div className="space-y-4">
            {renderLanguageSpecificFields()}
            {((data?.stats as Record<string, unknown>[]) || []).map(
              (stat: Record<string, unknown>, index: number) => (
                <div key={index} className="p-4 border rounded-md space-y-3">
                  <h4 className="font-medium">Statistic {index + 1} Content</h4>
                  <div className="space-y-1">
                    <Label>Icon</Label>
                    <Input
                      value={(stat.icon as string) || ""}
                      onChange={(e) =>
                        updateArrayItem("stats", index, "icon", e.target.value)
                      }
                    />
                  </div>
                  <div className="space-y-1">
                    <Label>Value</Label>
                    <Input
                      value={(stat.value as string) || ""}
                      onChange={(e) =>
                        updateArrayItem("stats", index, "value", e.target.value)
                      }
                    />
                  </div>
                  <div className="space-y-1">
                    <Label>Label</Label>
                    <Input
                      value={(stat.label as string) || ""}
                      onChange={(e) =>
                        updateArrayItem("stats", index, "label", e.target.value)
                      }
                    />
                  </div>
                  <div className="space-y-1">
                    <Label>Change</Label>
                    <Input
                      value={(stat.change as string) || ""}
                      onChange={(e) =>
                        updateArrayItem(
                          "stats",
                          index,
                          "change",
                          e.target.value
                        )
                      }
                    />
                  </div>
                </div>
              )
            )}
          </div>
        );

      case "quote":
      case "animated-quote":
        return (
          <div className="space-y-4">
            {renderLanguageSpecificFields()}
            <div className="space-y-1">
              <Label>Quote Text *</Label>
              <Textarea
                value={data?.text || ""}
                onChange={(e) => updateDataField("text", e.target.value)}
                placeholder="Enter the quote text..."
                rows={4}
              />
              {renderFieldError("data.text")}
            </div>
            <div className="space-y-1">
              <Label>Author *</Label>
              <Input
                value={data?.author || ""}
                onChange={(e) => updateDataField("author", e.target.value)}
                placeholder="Enter author name..."
              />
              {renderFieldError("data.author")}
            </div>
            <div className="space-y-1">
              <Label>Role (optional)</Label>
              <Input
                value={data?.role || ""}
                onChange={(e) => updateDataField("role", e.target.value)}
                placeholder="Enter author role..."
              />
            </div>
          </div>
        );

      case "climate-dashboard":
        return (
          <div className="space-y-4">
            {renderLanguageSpecificFields()}
            <div className="space-y-1">
              <Label>References</Label>
              <MultiSelectReferences
                selectedReferenceIds={data?.references || []}
                onSelectionChange={(ids) => updateDataField("references", ids)}
                placeholder="Select references..."
              />
            </div>
          </div>
        );

      case "impact-comparison":
        return (
          <div className="space-y-4">
            {renderLanguageSpecificFields()}
            <div className="space-y-1">
              <Label>References</Label>
              <MultiSelectReferences
                selectedReferenceIds={data?.references || []}
                onSelectionChange={(ids) => updateDataField("references", ids)}
                placeholder="Select references..."
              />
            </div>
          </div>
        );

      case "kpi-showcase":
        return (
          <div className="space-y-4">
            {renderLanguageSpecificFields()}
            <div className="space-y-1">
              <Label>References</Label>
              <MultiSelectReferences
                selectedReferenceIds={data?.references || []}
                onSelectionChange={(ids) => updateDataField("references", ids)}
                placeholder="Select references..."
              />
            </div>
          </div>
        );

      case "callout":
        return (
          <div className="space-y-4">
            {renderLanguageSpecificFields()}
            <div className="space-y-1">
              <Label>References</Label>
              <MultiSelectReferences
                selectedReferenceIds={data?.references || []}
                onSelectionChange={(ids) => updateDataField("references", ids)}
                placeholder="Select references..."
              />
            </div>
          </div>
        );

      case "interactive-callout":
        return (
          <div className="space-y-4">
            {renderLanguageSpecificFields()}
            <div className="space-y-1">
              <Label>References</Label>
              <MultiSelectReferences
                selectedReferenceIds={data?.references || []}
                onSelectionChange={(ids) => updateDataField("references", ids)}
                placeholder="Select references..."
              />
            </div>
          </div>
        );

      case "visualization":
        console.log(data, content, blockType, language);
        return (
          <div className="space-y-4">
            <div className="space-y-1">
              <Label>Caption</Label>
              {language === "en" ? (
                <Textarea readOnly value={data?.captionEn || ""} rows={3} />
              ) : (
                <Textarea readOnly value={data?.captionDe || ""} rows={3} />
              )}
            </div>
          </div>
        );

      default:
        return (
          <div className="space-y-4">
            {renderLanguageSpecificFields()}
            <div className="space-y-1">
              <Label>References</Label>
              <MultiSelectReferences
                selectedReferenceIds={data?.references || []}
                onSelectionChange={(ids) => updateDataField("references", ids)}
                placeholder="Select references..."
              />
            </div>
          </div>
        );
    }
  };

  if (mode === "shared") {
    return <div className="space-y-4">{renderSharedFields()}</div>;
  }

  if (mode === "language-specific") {
    return (
      <div className="space-y-4">{renderLanguageSpecificFieldsForType()}</div>
    );
  }
  console.log("Rendering all fields for block type:", blockType);
  return (
    <div className="space-y-4">
      {renderLanguageSpecificFieldsForType()}
      {blockType !== "markdown" && renderSharedFields()}
    </div>
  );
}
