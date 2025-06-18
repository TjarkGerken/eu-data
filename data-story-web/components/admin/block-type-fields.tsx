"use client";

import { useState } from "react";
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
import { Plus, Trash2, Move, Palette } from "lucide-react";
import { getFieldError, type ValidationError } from "@/lib/validation";

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

  const renderLanguageSpecificFields = () => (
    <>
      <div className="space-y-1">
        <Label>Title</Label>
        <Input
          value={title || ""}
          onChange={(e) => onTitleChange?.(e.target.value)}
          placeholder="Enter block title..."
        />
        {renderFieldError("title")}
      </div>
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

  const renderSharedReferences = () => (
    <div className="space-y-1">
      <Label>References</Label>
      <MultiSelectReferences
        selectedReferenceIds={data?.references || []}
        onSelectionChange={(referenceIds) =>
          updateDataField("references", referenceIds)
        }
        placeholder="Select references for this block..."
      />
    </div>
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
            {renderSharedReferences()}
          </div>
        );

      case "animated-statistics":
        return (
          <div className="space-y-4">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <Label>Statistics Configuration *</Label>
                <Button
                  type="button"
                  size="sm"
                  onClick={() =>
                    addArrayItem("stats", {
                      icon: "",
                      value: "",
                      label: "",
                      change: "",
                      trend: "up",
                      color: "#2d5a3d",
                    })
                  }
                >
                  <Plus className="w-4 h-4 mr-1" />
                  Add Statistic
                </Button>
              </div>
              {renderFieldError("data.stats")}
              {(data?.stats || []).map((stat: any, index: number) => (
                <Card key={index}>
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm">
                        Statistic {index + 1} - Shared Settings
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
                        <div className="flex gap-2">
                          <Input
                            type="color"
                            value={stat?.color || "#2d5a3d"}
                            onChange={(e) =>
                              updateArrayItem(
                                "stats",
                                index,
                                "color",
                                e.target.value
                              )
                            }
                            className="w-16 h-9 p-1"
                          />
                          <Input
                            value={stat?.color || "#2d5a3d"}
                            onChange={(e) =>
                              updateArrayItem(
                                "stats",
                                index,
                                "color",
                                e.target.value
                              )
                            }
                            placeholder="#2d5a3d"
                            className="flex-1"
                          />
                        </div>
                        {renderFieldError(`data.stats.${index}.color`)}
                      </div>
                    </div>
                    <div>
                      <Label>Icon Name</Label>
                      <Input
                        value={stat?.icon || ""}
                        onChange={(e) =>
                          updateArrayItem(
                            "stats",
                            index,
                            "icon",
                            e.target.value
                          )
                        }
                        placeholder="e.g., TrendingUp"
                      />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
            {renderSharedReferences()}
          </div>
        );

      case "climate-timeline":
        return (
          <div className="space-y-4">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <Label>Timeline Configuration *</Label>
                <Button
                  type="button"
                  size="sm"
                  onClick={() =>
                    addArrayItem("events", {
                      year: 2024,
                      title: "",
                      description: "",
                      type: "temperature",
                      icon: "",
                      color: "#2d5a3d",
                    })
                  }
                >
                  <Plus className="w-4 h-4 mr-1" />
                  Add Event
                </Button>
              </div>
              {renderFieldError("data.events")}
              {(data?.events || []).map((event: any, index: number) => (
                <Card key={index}>
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm">
                        Event {index + 1} - Shared Settings
                      </CardTitle>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => removeArrayItem("events", index)}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label>Year *</Label>
                        <Input
                          type="number"
                          value={event?.year || 2024}
                          onChange={(e) =>
                            updateArrayItem(
                              "events",
                              index,
                              "year",
                              parseInt(e.target.value)
                            )
                          }
                          min="1850"
                          max="2100"
                        />
                        {renderFieldError(`data.events.${index}.year`)}
                      </div>
                      <div>
                        <Label>Type</Label>
                        <Select
                          value={event?.type || "temperature"}
                          onValueChange={(value) =>
                            updateArrayItem("events", index, "type", value)
                          }
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="temperature">
                              Temperature
                            </SelectItem>
                            <SelectItem value="precipitation">
                              Precipitation
                            </SelectItem>
                            <SelectItem value="policy">Policy</SelectItem>
                            <SelectItem value="extreme">
                              Extreme Event
                            </SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label>Icon Name</Label>
                        <Input
                          value={event?.icon || ""}
                          onChange={(e) =>
                            updateArrayItem(
                              "events",
                              index,
                              "icon",
                              e.target.value
                            )
                          }
                          placeholder="e.g., Thermometer"
                        />
                      </div>
                      <div>
                        <Label>Color</Label>
                        <div className="flex gap-2">
                          <Input
                            type="color"
                            value={event?.color || "#2d5a3d"}
                            onChange={(e) =>
                              updateArrayItem(
                                "events",
                                index,
                                "color",
                                e.target.value
                              )
                            }
                            className="w-16 h-9 p-1"
                          />
                          <Input
                            value={event?.color || "#2d5a3d"}
                            onChange={(e) =>
                              updateArrayItem(
                                "events",
                                index,
                                "color",
                                e.target.value
                              )
                            }
                            placeholder="#2d5a3d"
                            className="flex-1"
                          />
                        </div>
                        {renderFieldError(`data.events.${index}.color`)}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
            {renderSharedReferences()}
          </div>
        );

      case "climate-dashboard":
        return (
          <div className="space-y-4">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <Label>Dashboard Configuration *</Label>
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
                      description: "",
                    })
                  }
                >
                  <Plus className="w-4 h-4 mr-1" />
                  Add Metric
                </Button>
              </div>
              {renderFieldError("data.metrics")}
              {(data?.metrics || []).map((metric: any, index: number) => (
                <Card key={index}>
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm">
                        Metric {index + 1} - Shared Settings
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
                    <div className="grid grid-cols-3 gap-3">
                      <div>
                        <Label>Trend</Label>
                        <Select
                          value={metric?.trend || "up"}
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
                          value={metric?.status || "success"}
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
                      <div>
                        <Label>Progress (%)</Label>
                        <Input
                          type="number"
                          value={metric?.progress || 50}
                          onChange={(e) =>
                            updateArrayItem(
                              "metrics",
                              index,
                              "progress",
                              parseInt(e.target.value)
                            )
                          }
                          min="0"
                          max="100"
                        />
                        {renderFieldError(`data.metrics.${index}.progress`)}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
            {renderSharedReferences()}
          </div>
        );

      case "temperature-spiral":
        return (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <Label>Start Year</Label>
                <Input
                  type="number"
                  value={data?.startYear || 1880}
                  onChange={(e) =>
                    updateDataField("startYear", parseInt(e.target.value))
                  }
                  min="1850"
                  max="2100"
                />
                {renderFieldError("data.startYear")}
              </div>
              <div className="space-y-1">
                <Label>End Year</Label>
                <Input
                  type="number"
                  value={data?.endYear || 2030}
                  onChange={(e) =>
                    updateDataField("endYear", parseInt(e.target.value))
                  }
                  min="1850"
                  max="2100"
                />
                {renderFieldError("data.endYear")}
              </div>
            </div>
            <div className="space-y-1">
              <Label>Rotations</Label>
              <Input
                type="number"
                value={data?.rotations || 8}
                onChange={(e) =>
                  updateDataField("rotations", parseInt(e.target.value))
                }
                min="1"
                max="20"
              />
              {renderFieldError("data.rotations")}
            </div>
            {renderSharedReferences()}
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
                    if (imageData.scenario) {
                      newData.imageScenario = imageData.scenario;
                    }
                  }
                  onDataChange(newData);
                }}
                placeholder="Select visualization image..."
              />
            </div>
            {renderSharedReferences()}
          </div>
        );

      case "climate-timeline-minimal":
        return (
          <div className="space-y-4">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <Label>Timeline Configuration *</Label>
                <Button
                  type="button"
                  size="sm"
                  onClick={() =>
                    addArrayItem("events", {
                      year: 2024,
                      title: "",
                      description: "",
                    })
                  }
                >
                  <Plus className="w-4 h-4 mr-1" />
                  Add Event
                </Button>
              </div>
              {renderFieldError("data.events")}
              {(data?.events || []).map((event: any, index: number) => (
                <Card key={index}>
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm">
                        Event {index + 1} - Shared Settings
                      </CardTitle>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => removeArrayItem("events", index)}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div>
                      <Label>Year *</Label>
                      <Input
                        type="number"
                        value={event?.year || 2024}
                        onChange={(e) =>
                          updateArrayItem(
                            "events",
                            index,
                            "year",
                            parseInt(e.target.value)
                          )
                        }
                        min="1850"
                        max="2100"
                      />
                      {renderFieldError(`data.events.${index}.year`)}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
            {renderSharedReferences()}
          </div>
        );

      default:
        return renderSharedReferences();
    }
  };

  const renderLanguageSpecificFieldsForType = () => {
    switch (blockType) {
      case "markdown":
        return (
          <div className="space-y-1">
            <Label>Markdown Content *</Label>
            <Textarea
              value={content || ""}
              onChange={(e) => onContentChange?.(e.target.value)}
              placeholder="Enter markdown content..."
              rows={6}
              className="font-mono"
            />
            {renderFieldError("content")}
          </div>
        );

      case "animated-quote":
        return (
          <div className="space-y-4">
            <div className="space-y-1">
              <Label>Quote Text *</Label>
              <Textarea
                value={data?.text || ""}
                onChange={(e) => updateDataField("text", e.target.value)}
                placeholder="Enter quote text..."
                rows={4}
              />
              {renderFieldError("data.text")}
            </div>
            <div className="space-y-1">
              <Label>Author *</Label>
              <Input
                value={data?.author || ""}
                onChange={(e) => updateDataField("author", e.target.value)}
                placeholder="Author name..."
              />
              {renderFieldError("data.author")}
            </div>
            <div className="space-y-1">
              <Label>Role/Title</Label>
              <Input
                value={data?.role || ""}
                onChange={(e) => updateDataField("role", e.target.value)}
                placeholder="Author's role or title..."
              />
            </div>
          </div>
        );

      case "animated-statistics":
        return (
          <div className="space-y-4">
            {renderLanguageSpecificFields()}
            <div className="space-y-4">
              <Label>Statistics Text Content</Label>
              {(data?.stats || []).map((stat: any, index: number) => (
                <Card key={index}>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm">
                      Statistic {index + 1} - Text Content
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label>Value *</Label>
                        <Input
                          value={stat?.value || ""}
                          onChange={(e) =>
                            updateArrayItem(
                              "stats",
                              index,
                              "value",
                              e.target.value
                            )
                          }
                          placeholder="e.g., 42%"
                        />
                        {renderFieldError(`data.stats.${index}.value`)}
                      </div>
                      <div>
                        <Label>Label *</Label>
                        <Input
                          value={stat?.label || ""}
                          onChange={(e) =>
                            updateArrayItem(
                              "stats",
                              index,
                              "label",
                              e.target.value
                            )
                          }
                          placeholder="e.g., CO2 Reduction"
                        />
                        {renderFieldError(`data.stats.${index}.label`)}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        );

      case "climate-timeline":
        return (
          <div className="space-y-4">
            {renderLanguageSpecificFields()}
            <div className="space-y-4">
              <Label>Timeline Events Text Content</Label>
              {(data?.events || []).map((event: any, index: number) => (
                <Card key={index}>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm">
                      Event {index + 1} - Text Content
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div>
                      <Label>Title *</Label>
                      <Input
                        value={event?.title || ""}
                        onChange={(e) =>
                          updateArrayItem(
                            "events",
                            index,
                            "title",
                            e.target.value
                          )
                        }
                        placeholder="Event title..."
                      />
                      {renderFieldError(`data.events.${index}.title`)}
                    </div>
                    <div>
                      <Label>Description</Label>
                      <Textarea
                        value={event?.description || ""}
                        onChange={(e) =>
                          updateArrayItem(
                            "events",
                            index,
                            "description",
                            e.target.value
                          )
                        }
                        placeholder="Event description..."
                        rows={2}
                      />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        );

      case "climate-dashboard":
        return (
          <div className="space-y-4">
            {renderLanguageSpecificFields()}
            <div className="space-y-4">
              <Label>Dashboard Metrics Text Content</Label>
              {(data?.metrics || []).map((metric: any, index: number) => (
                <Card key={index}>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm">
                      Metric {index + 1} - Text Content
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label>Title *</Label>
                        <Input
                          value={metric?.title || ""}
                          onChange={(e) =>
                            updateArrayItem(
                              "metrics",
                              index,
                              "title",
                              e.target.value
                            )
                          }
                          placeholder="Metric title..."
                        />
                        {renderFieldError(`data.metrics.${index}.title`)}
                      </div>
                      <div>
                        <Label>Value *</Label>
                        <Input
                          value={metric?.value || ""}
                          onChange={(e) =>
                            updateArrayItem(
                              "metrics",
                              index,
                              "value",
                              e.target.value
                            )
                          }
                          placeholder="e.g., 85%"
                        />
                        {renderFieldError(`data.metrics.${index}.value`)}
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label>Change</Label>
                        <Input
                          value={metric?.change || ""}
                          onChange={(e) =>
                            updateArrayItem(
                              "metrics",
                              index,
                              "change",
                              e.target.value
                            )
                          }
                          placeholder="e.g., +5%"
                        />
                      </div>
                      <div>
                        <Label>Target</Label>
                        <Input
                          value={metric?.target || ""}
                          onChange={(e) =>
                            updateArrayItem(
                              "metrics",
                              index,
                              "target",
                              e.target.value
                            )
                          }
                          placeholder="Target value..."
                        />
                      </div>
                    </div>
                    <div>
                      <Label>Description</Label>
                      <Textarea
                        value={metric?.description || ""}
                        onChange={(e) =>
                          updateArrayItem(
                            "metrics",
                            index,
                            "description",
                            e.target.value
                          )
                        }
                        placeholder="Metric description..."
                        rows={2}
                      />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        );

      case "climate-timeline-minimal":
        return (
          <div className="space-y-4">
            {renderLanguageSpecificFields()}
            <div className="space-y-4">
              <Label>Timeline Events Text Content</Label>
              {(data?.events || []).map((event: any, index: number) => (
                <Card key={index}>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm">
                      Event {index + 1} - Text Content
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div>
                      <Label>Title *</Label>
                      <Input
                        value={event?.title || ""}
                        onChange={(e) =>
                          updateArrayItem(
                            "events",
                            index,
                            "title",
                            e.target.value
                          )
                        }
                        placeholder="Event title..."
                      />
                      {renderFieldError(`data.events.${index}.title`)}
                    </div>
                    <div>
                      <Label>Description</Label>
                      <Textarea
                        value={event?.description || ""}
                        onChange={(e) =>
                          updateArrayItem(
                            "events",
                            index,
                            "description",
                            e.target.value
                          )
                        }
                        placeholder="Event description..."
                        rows={2}
                      />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        );

      case "visualization":
        return (
          <div className="space-y-4">
            {renderLanguageSpecificFields()}
            <div className="space-y-1">
              <Label>Additional Content</Label>
              <Textarea
                value={data?.additionalContent || ""}
                onChange={(e) =>
                  updateDataField("additionalContent", e.target.value)
                }
                placeholder="Additional content or analysis..."
                rows={3}
              />
            </div>
          </div>
        );

      case "impact-comparison":
      case "kpi-showcase":
      case "climate-infographic":
        return (
          <div className="space-y-4">
            {renderLanguageSpecificFields()}
            <div className="p-4 bg-muted rounded-lg">
              <p className="text-sm text-muted-foreground">
                This block type uses predefined data and animations. Only title
                and description can be customized.
              </p>
            </div>
          </div>
        );

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

  // mode === "all" - used for create new form
  return (
    <div className="space-y-4">
      {renderLanguageSpecificFieldsForType()}
      {blockType !== "markdown" && renderSharedFields()}
    </div>
  );
}
