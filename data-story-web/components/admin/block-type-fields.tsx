"use client";

import { useState, useEffect } from "react";
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
import { Plus, Trash2, Move, Palette, Layers, Settings } from "lucide-react";
import { getFieldError, type ValidationError } from "@/lib/validation";
import { Switch } from "@/components/ui/switch";
import { mapTileService, MapLayerMetadata } from "@/lib/map-tile-service";
import LayerManager from "./layer-manager";

interface BlockTypeFieldsProps {
  blockType: string;
  data: any;
  onDataChange: (newData: any) => void;
  validationErrors: ValidationError[];
  title?: string;
  content?: string;
  onTitleChange?: (title: string) => void;
  onContentChange?: (content: string) => void;
  mode?: "shared" | "language-specific" | "all";
}

interface MapLayerSelectorProps {
  data: any;
  onDataChange: (newData: any) => void;
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

  const updateDataField = (field: string, value: any) => {
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
            onChange={(e) => updateDataField("centerLat", parseFloat(e.target.value) || 52.1326)}
            placeholder="52.1326"
            type="number"
            step="0.0001"
          />
          <Input
            value={data?.centerLng || "5.2913"}
            onChange={(e) => updateDataField("centerLng", parseFloat(e.target.value) || 5.2913)}
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
          onChange={(e) => updateDataField("zoom", parseInt(e.target.value) || 8)}
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
  mode = "all",
}: BlockTypeFieldsProps) {
  const updateDataField = (path: string, value: any) => {
    const newData = { ...data };
    const pathParts = path.split(".");
    let current = newData;

    for (let i = 0; i < pathParts.length - 1; i++) {
      if (!current[pathParts[i]]) current[pathParts[i]] = {};
      current = current[pathParts[i]];
    }

    current[pathParts[pathParts.length - 1]] = value;
    onDataChange(newData);
  };

  const addArrayItem = (arrayPath: string, defaultItem: any) => {
    const currentArray = getNestedValue(data, arrayPath) || [];
    updateDataField(arrayPath, [...currentArray, defaultItem]);
  };

  const removeArrayItem = (arrayPath: string, index: number) => {
    const currentArray = getNestedValue(data, arrayPath) || [];
    const newArray = currentArray.filter((_: any, i: number) => i !== index);
    updateDataField(arrayPath, newArray);
  };

  const updateArrayItem = (
    arrayPath: string,
    index: number,
    field: string,
    value: any
  ) => {
    const currentArray = getNestedValue(data, arrayPath) || [];
    const newArray = [...currentArray];
    newArray[index] = { ...newArray[index], [field]: value };
    updateDataField(arrayPath, newArray);
  };

  const getNestedValue = (obj: any, path: string): any => {
    return path.split(".").reduce((current, key) => current?.[key], obj);
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
    "climate-timeline",
    "climate-dashboard",
    "temperature-spiral",
    "interactive-map",
    "impact-comparison",
    "kpi-showcase",
    "climate-timeline-minimal",
    "climate-infographic"
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
      <div className="space-y-1">
        <Label>Description</Label>
        <Textarea
          value={content || ""}
          onChange={(e) => onContentChange?.(e.target.value)}
          placeholder="Enter block description..."
          rows={3}
        />
        {renderFieldError("content")}
      </div>
    </>
  );

  const renderSharedFields = () => {
    switch (blockType) {
      case "callout":
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
          </div>
        );

      case "interactive-map":
        return <MapLayerSelector data={data} onDataChange={onDataChange} />;

      case "animated-statistics":
        return (
          <div className="space-y-4">
            <Label>Statistics Configuration *</Label>
            {renderFieldError("data.stats")}
            {(data?.stats || []).map((stat: any, index: number) => (
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
                      <Label>Trend</Label>
                      <Select
                        value={stat?.trend || "up"}
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
                    <div>
                      <Label>Color</Label>
                      <Input
                        type="color"
                        value={stat?.color || "#000000"}
                        onChange={(e) =>
                          updateArrayItem(
                            "stats",
                            index,
                            "color",
                            e.target.value
                          )
                        }
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
            <Button
              type="button"
              size="sm"
              onClick={() =>
                addArrayItem("stats", {
                  trend: "up",
                  color: "#000000",
                })
              }
            >
              Add Statistic
            </Button>
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

      case "quote":
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
        return (
          <div className="space-y-1">
            <Label>Content</Label>
            <Textarea
              value={content || ""}
              onChange={(e) => onContentChange?.(e.target.value)}
              placeholder="Enter markdown content..."
              rows={10}
            />
            {renderFieldError("content")}
          </div>
        );

      case "interactive-map":
        return renderLanguageSpecificFields();

      case "animated-statistics":
        return (
          <div className="space-y-4">
            {renderLanguageSpecificFields()}
            {(data?.stats || []).map((stat: any, index: number) => (
              <div key={index} className="p-4 border rounded-md space-y-3">
                <h4 className="font-medium">Statistic {index + 1} Content</h4>
                <div className="space-y-1">
                  <Label>Icon</Label>
                  <Input
                    value={stat.icon || ""}
                    onChange={(e) =>
                      updateArrayItem("stats", index, "icon", e.target.value)
                    }
                  />
                </div>
                <div className="space-y-1">
                  <Label>Value</Label>
                  <Input
                    value={stat.value || ""}
                    onChange={(e) =>
                      updateArrayItem("stats", index, "value", e.target.value)
                    }
                  />
                </div>
                <div className="space-y-1">
                  <Label>Label</Label>
                  <Input
                    value={stat.label || ""}
                    onChange={(e) =>
                      updateArrayItem("stats", index, "label", e.target.value)
                    }
                  />
                </div>
                <div className="space-y-1">
                  <Label>Change</Label>
                  <Input
                    value={stat.change || ""}
                    onChange={(e) =>
                      updateArrayItem("stats", index, "change", e.target.value)
                    }
                  />
                </div>
              </div>
            ))}
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

      case "visualization":
        return renderLanguageSpecificFields();

      default:
        return renderLanguageSpecificFields();
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

  return (
    <div className="space-y-4">
      {renderLanguageSpecificFieldsForType()}
      {blockType !== "markdown" && renderSharedFields()}
    </div>
  );
}
