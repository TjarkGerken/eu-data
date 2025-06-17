"use client";

import { useState, useEffect } from "react";
import type { JSX } from "react";
import { supabase } from "@/lib/supabase";
import { Button } from "@/components/ui/button";
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
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Loader2,
  Save,
  ArrowLeft,
  Languages,
  Copy,
  Link,
  X,
} from "lucide-react";

interface ContentBlock {
  id: string;
  story_id: string | null;
  block_type: string;
  order_index: number;
  data: any;
  languageCode?: string;
}

interface BlockPair {
  orderIndex: number;
  blockType: string;
  english: ContentBlock | null;
  german: ContentBlock | null;
}

interface ClimateImage {
  id: number;
  filename: string;
  description: string | null;
  category: string;
  scenario: string;
  public_url: string;
  blob_url: string | null;
  created_at: string | null;
  file_size: number | null;
  mime_type: string | null;
  storage_path: string;
  updated_at: string | null;
}

interface Reference {
  id: string;
  title: string;
  authors: string[];
  year: number;
  journal: string | null;
  type: string;
  url: string | null;
  created_at: string | null;
  updated_at: string | null;
}

const AVAILABLE_BLOCK_TYPES = [
  "markdown",
  "callout",
  "visualization",
  "animated-quote",
  "animated-statistics",
  "climate-timeline",
  "climate-dashboard",
  "temperature-spiral",
  "interactive-callout",
  "impact-comparison",
  "kpi-showcase",
  "climate-timeline-minimal",
  "climate-infographic",
];

// Fields that should be synchronized between languages (same value for both)
const SYNCED_FIELDS = [
  "references",
  "imageId",
  "intensity",
  "speed",
  "duration",
  "particles",
  "molecules",
  "rotations",
  "startYear",
  "endYear",
  "zoom",
  "data.imageId",
  "data.intensity",
  "data.speed",
  "data.duration",
  "data.particles",
  "data.molecules",
  "data.rotations",
  "data.startYear",
  "data.endYear",
  "data.zoom",
];

export default function PairedBlockEditor() {
  const [blockPairs, setBlockPairs] = useState<BlockPair[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [selectedPair, setSelectedPair] = useState<BlockPair | null>(null);
  const [climateImages, setClimateImages] = useState<ClimateImage[]>([]);
  const [references, setReferences] = useState<Reference[]>([]);

  useEffect(() => {
    fetchBlockPairs();
    fetchClimateImages();
    fetchReferences();
  }, []);

  const fetchClimateImages = async () => {
    try {
      const { data, error } = await supabase
        .from("climate_images")
        .select("*")
        .order("display_order");

      if (error) throw error;
      setClimateImages(data || []);
    } catch (err) {
      console.error("Failed to load images:", err);
    }
  };

  const fetchReferences = async () => {
    try {
      const { data, error } = await supabase
        .from("content_references")
        .select("*")
        .order("title");

      if (error) throw error;
      setReferences(data || []);
    } catch (err) {
      console.error("Failed to load references:", err);
    }
  };

  const fetchBlockPairs = async () => {
    try {
      const { data: stories } = await supabase
        .from("content_stories")
        .select("id, language_code")
        .in("language_code", ["en", "de"]);

      if (!stories) return;

      const englishStory = stories.find((s) => s.language_code === "en");
      const germanStory = stories.find((s) => s.language_code === "de");

      if (!englishStory || !germanStory) {
        setError("Missing English or German story");
        return;
      }

      const fetchBlocksForStory = async (storyId: string) => {
        const { data, error } = await supabase
          .from("content_blocks")
          .select("*")
          .eq("story_id", storyId)
          .order("order_index");

        if (error) throw error;
        return data || [];
      };

      const [englishBlocks, germanBlocks] = await Promise.all([
        fetchBlocksForStory(englishStory.id),
        fetchBlocksForStory(germanStory.id),
      ]);

      // Create pairs by matching order_index
      const pairs: BlockPair[] = [];
      const maxIndex = Math.max(
        englishBlocks.length > 0
          ? Math.max(...englishBlocks.map((b) => b.order_index))
          : 0,
        germanBlocks.length > 0
          ? Math.max(...germanBlocks.map((b) => b.order_index))
          : 0
      );

      for (let i = 1; i <= maxIndex; i++) {
        const english = englishBlocks.find((b) => b.order_index === i) || null;
        const german = germanBlocks.find((b) => b.order_index === i) || null;

        if (english || german) {
          pairs.push({
            orderIndex: i,
            blockType: (english || german)!.block_type,
            english: english ? { ...english, languageCode: "en" } : null,
            german: german ? { ...german, languageCode: "de" } : null,
          });
        }
      }

      setBlockPairs(pairs);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load blocks");
    } finally {
      setLoading(false);
    }
  };

  const saveBothBlocks = async () => {
    if (!selectedPair) return;

    setSaving(true);
    setError(null);
    setSuccess(false);

    try {
      const updates = [];

      if (selectedPair.english) {
        updates.push(
          supabase
            .from("content_blocks")
            .update({
              block_type: selectedPair.blockType,
              data: selectedPair.english.data,
            })
            .eq("id", selectedPair.english.id)
        );
      }

      if (selectedPair.german) {
        updates.push(
          supabase
            .from("content_blocks")
            .update({
              block_type: selectedPair.blockType,
              data: selectedPair.german.data,
            })
            .eq("id", selectedPair.german.id)
        );
      }

      const results = await Promise.all(updates);

      for (const result of results) {
        if (result.error) throw result.error;
      }

      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save blocks");
    } finally {
      setSaving(false);
    }
  };

  const updateBlockType = (newType: string) => {
    if (!selectedPair) return;

    const updatedPair = { ...selectedPair, blockType: newType };
    setSelectedPair(updatedPair);
  };

  const copyContentToLanguage = (
    fromBlock: ContentBlock,
    toLanguage: "en" | "de"
  ) => {
    if (!selectedPair) return;

    const updatedPair = { ...selectedPair };
    const targetBlock =
      toLanguage === "en" ? updatedPair.english : updatedPair.german;

    if (targetBlock) {
      // Copy non-synced fields only
      const filteredData = { ...fromBlock.data };

      // Keep synced fields from target block
      SYNCED_FIELDS.forEach((field) => {
        const fieldPath = field.split(".");
        if (fieldPath.length === 1) {
          if (targetBlock.data[field] !== undefined) {
            filteredData[field] = targetBlock.data[field];
          }
        } else if (fieldPath.length === 2 && fieldPath[0] === "data") {
          if (
            targetBlock.data.data &&
            targetBlock.data.data[fieldPath[1]] !== undefined
          ) {
            if (!filteredData.data) filteredData.data = {};
            filteredData.data[fieldPath[1]] =
              targetBlock.data.data[fieldPath[1]];
          }
        }
      });

      targetBlock.data = filteredData;
      setSelectedPair(updatedPair);
    }
  };

  // Update shared field values across both languages
  const updateSharedField = (fieldPath: string[], value: any) => {
    if (!selectedPair) return;

    const updatedPair = { ...selectedPair };

    [updatedPair.english, updatedPair.german].forEach((block) => {
      if (block) {
        let current = block.data;

        // Navigate to parent object
        for (let i = 0; i < fieldPath.length - 1; i++) {
          if (!current[fieldPath[i]]) current[fieldPath[i]] = {};
          current = current[fieldPath[i]];
        }

        // Set the value
        current[fieldPath[fieldPath.length - 1]] = value;
      }
    });

    setSelectedPair(updatedPair);
  };

  const renderImageSelector = (currentValue: string) => {
    return (
      <div className="space-y-2">
        <Label className="text-sm font-medium">Image Selection</Label>
        <Select
          value={currentValue}
          onValueChange={(value) =>
            updateSharedField(["data", "imageId"], value)
          }
        >
          <SelectTrigger>
            <SelectValue placeholder="Select an image..." />
          </SelectTrigger>
          <SelectContent>
            {climateImages.map((image) => (
              <SelectItem key={image.id} value={image.id.toString()}>
                <div className="flex items-center gap-2">
                  {(image.blob_url || image.public_url) && (
                    <img
                      src={image.blob_url || image.public_url}
                      alt={image.description || image.filename}
                      className="w-8 h-8 object-cover rounded"
                    />
                  )}
                  <div className="flex flex-col">
                    <span className="font-medium">{image.filename}</span>
                    <span className="text-xs text-muted-foreground">
                      {image.description ||
                        `${image.category} - ${image.scenario}`}
                    </span>
                  </div>
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    );
  };

  const renderReferencesSelector = (currentRefs: string[]) => {
    const selectedRefs = Array.isArray(currentRefs) ? currentRefs : [];

    return (
      <div className="space-y-2">
        <Label className="text-sm font-medium">References</Label>
        <Select
          value={selectedRefs.length > 0 ? "open" : ""}
          onValueChange={() => {}} // Controlled by checkboxes
        >
          <SelectTrigger>
            <SelectValue
              placeholder={
                selectedRefs.length === 0
                  ? "Select references..."
                  : `${selectedRefs.length} reference${
                      selectedRefs.length !== 1 ? "s" : ""
                    } selected`
              }
            />
          </SelectTrigger>
          <SelectContent>
            {references.map((ref) => (
              <div
                key={ref.id}
                className="flex items-start space-x-2 px-2 py-2 hover:bg-gray-50"
                onClick={(e) => e.stopPropagation()}
              >
                <input
                  type="checkbox"
                  id={`ref-${ref.id}`}
                  checked={selectedRefs.includes(ref.id)}
                  onChange={(e) => {
                    e.stopPropagation();
                    const newRefs = e.target.checked
                      ? [...selectedRefs, ref.id]
                      : selectedRefs.filter((id) => id !== ref.id);
                    updateSharedField(["references"], newRefs);
                  }}
                  className="mt-1"
                />
                <label
                  htmlFor={`ref-${ref.id}`}
                  className="text-sm cursor-pointer flex-1"
                  onClick={(e) => e.stopPropagation()}
                >
                  <div className="font-medium">
                    {Array.isArray(ref.authors)
                      ? ref.authors.join(", ")
                      : ref.authors}{" "}
                    ({ref.year})
                  </div>
                  <div className="text-xs text-muted-foreground line-clamp-2">
                    {ref.title}
                  </div>
                </label>
              </div>
            ))}
          </SelectContent>
        </Select>

        {selectedRefs.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {selectedRefs.map((refId) => {
              const ref = references.find((r) => r.id === refId);
              if (!ref) return null;

              return (
                <Badge key={refId} variant="outline" className="text-xs">
                  {Array.isArray(ref.authors)
                    ? ref.authors.join(", ")
                    : ref.authors}{" "}
                  ({ref.year})
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      const newRefs = selectedRefs.filter((id) => id !== refId);
                      updateSharedField(["references"], newRefs);
                    }}
                    className="ml-1 hover:bg-gray-200 rounded-full p-0.5"
                  >
                    <X className="h-2 w-2" />
                  </button>
                </Badge>
              );
            })}
          </div>
        )}
      </div>
    );
  };

  const renderSharedFields = () => {
    if (!selectedPair || (!selectedPair.english && !selectedPair.german))
      return null;

    const currentData = (selectedPair.english || selectedPair.german)!.data;
    const fields = [];

    // References (always shared)
    fields.push(
      <div key="references">
        {renderReferencesSelector(currentData.references || [])}
      </div>
    );

    // Image selector for visualization blocks
    if (
      selectedPair.blockType === "visualization" &&
      currentData.data?.imageId !== undefined
    ) {
      fields.push(
        <div key="imageId">
          {renderImageSelector(currentData.data.imageId || "")}
        </div>
      );
    }

    // Other shared technical parameters
    const sharedParams = [
      "intensity",
      "speed",
      "duration",
      "particles",
      "molecules",
      "rotations",
      "startYear",
      "endYear",
      "zoom",
    ];

    sharedParams.forEach((param) => {
      const value = currentData.data?.[param];
      if (value !== undefined) {
        fields.push(
          <div key={param} className="space-y-1">
            <Label className="text-sm font-medium">{param}</Label>
            <Input
              type="number"
              value={value}
              onChange={(e) =>
                updateSharedField(
                  ["data", param],
                  parseFloat(e.target.value) || 0
                )
              }
              className="text-sm"
            />
          </div>
        );
      }
    });

    return fields.length > 0 ? (
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Link className="h-4 w-4" />
            Shared Fields
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">{fields}</CardContent>
      </Card>
    ) : null;
  };

  const renderLanguageSpecificFields = (
    data: any,
    updateData: (newData: any) => void,
    blockType: string,
    language: "en" | "de"
  ) => {
    const fields: JSX.Element[] = [];

    const isSharedField = (key: string, path: string[] = []): boolean => {
      const fieldPath = path.length > 0 ? `${path.join(".")}.${key}` : key;

      // Check if this exact field path is in SYNCED_FIELDS
      if (SYNCED_FIELDS.includes(fieldPath) || SYNCED_FIELDS.includes(key)) {
        return true;
      }

      // Always skip references as it's handled in shared section
      if (key === "references") {
        return true;
      }

      // Skip image-related fields for visualization blocks
      if (
        blockType === "visualization" &&
        (key === "imageCategory" ||
          key === "imageScenario" ||
          key === "imageId")
      ) {
        return true;
      }

      // Skip nested data fields that are shared
      if (path.length > 0 && path[0] === "data") {
        const nestedPath = `data.${key}`;
        if (SYNCED_FIELDS.includes(nestedPath)) {
          return true;
        }
      }

      return false;
    };

    const addField = (key: string, value: any, path: string[] = []) => {
      const fieldPath = path.length > 0 ? `${path.join(".")}.${key}` : key;
      const fieldId = `${fieldPath}-${language}`.replace(/\./g, "-");

      // Skip shared fields
      if (isSharedField(key, path)) {
        return;
      }

      if (value === null || value === undefined) {
        fields.push(
          <div key={fieldPath} className="space-y-1">
            <Label htmlFor={fieldId} className="text-sm">
              {key}
            </Label>
            <Input
              id={fieldId}
              value=""
              onChange={(e) => {
                const newData = { ...data };
                let current = newData;
                for (const p of path) {
                  if (!current[p]) current[p] = {};
                  current = current[p];
                }
                current[key] = e.target.value;
                updateData(newData);
              }}
              placeholder={`Enter ${key}...`}
              className="text-sm"
            />
          </div>
        );
        return;
      }

      switch (typeof value) {
        case "string":
          if (
            value.length > 100 ||
            key.includes("content") ||
            key.includes("description")
          ) {
            fields.push(
              <div key={fieldPath} className="space-y-1">
                <Label htmlFor={fieldId} className="text-sm">
                  {key}
                </Label>
                <Textarea
                  id={fieldId}
                  value={value}
                  onChange={(e) => {
                    const newData = { ...data };
                    let current = newData;
                    for (const p of path) {
                      current = current[p];
                    }
                    current[key] = e.target.value;
                    updateData(newData);
                  }}
                  rows={3}
                  className="text-sm"
                />
              </div>
            );
          } else {
            fields.push(
              <div key={fieldPath} className="space-y-1">
                <Label htmlFor={fieldId} className="text-sm">
                  {key}
                </Label>
                <Input
                  id={fieldId}
                  value={value}
                  onChange={(e) => {
                    const newData = { ...data };
                    let current = newData;
                    for (const p of path) {
                      current = current[p];
                    }
                    current[key] = e.target.value;
                    updateData(newData);
                  }}
                  className="text-sm"
                />
              </div>
            );
          }
          break;

        case "number":
          // Skip if this is a shared field
          if (
            !SYNCED_FIELDS.includes(fieldPath) &&
            !SYNCED_FIELDS.includes(key)
          ) {
            fields.push(
              <div key={fieldPath} className="space-y-1">
                <Label htmlFor={fieldId} className="text-sm">
                  {key}
                </Label>
                <Input
                  id={fieldId}
                  type="number"
                  value={value}
                  onChange={(e) => {
                    const newData = { ...data };
                    let current = newData;
                    for (const p of path) {
                      current = current[p];
                    }
                    current[key] = parseFloat(e.target.value) || 0;
                    updateData(newData);
                  }}
                  className="text-sm"
                />
              </div>
            );
          }
          break;

        case "boolean":
          fields.push(
            <div key={fieldPath} className="flex items-center space-x-2">
              <Switch
                id={fieldId}
                checked={value}
                onCheckedChange={(checked) => {
                  const newData = { ...data };
                  let current = newData;
                  for (const p of path) {
                    current = current[p];
                  }
                  current[key] = checked;
                  updateData(newData);
                }}
              />
              <Label htmlFor={fieldId} className="text-sm">
                {key}
              </Label>
            </div>
          );
          break;

        case "object":
          if (Array.isArray(value)) {
            // Handle arrays with proper editing capabilities
            fields.push(
              <div key={fieldPath} className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label className="text-sm">{key} (Array)</Label>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      const newData = { ...data };
                      let current = newData;
                      for (const p of path) {
                        current = current[p];
                      }

                      // Add a new item based on the type of existing items
                      let newItem: any;
                      if (value.length > 0) {
                        const firstItem = value[0];
                        if (typeof firstItem === "string") {
                          newItem = "";
                        } else if (typeof firstItem === "number") {
                          newItem = 0;
                        } else if (
                          typeof firstItem === "object" &&
                          firstItem !== null
                        ) {
                          // Clone the structure of the first item
                          newItem = Array.isArray(firstItem) ? [] : {};
                          if (!Array.isArray(firstItem)) {
                            Object.keys(firstItem).forEach((k) => {
                              (newItem as any)[k] =
                                typeof firstItem[k] === "string"
                                  ? ""
                                  : typeof firstItem[k] === "number"
                                  ? 0
                                  : null;
                            });
                          }
                        } else {
                          newItem = null;
                        }
                      } else {
                        // Default to string for empty arrays
                        newItem = "";
                      }

                      current[key] = [...value, newItem];
                      updateData(newData);
                    }}
                  >
                    Add Item
                  </Button>
                </div>

                <div className="space-y-2">
                  {value.map((item: any, index: number) => (
                    <div
                      key={`${fieldPath}-${index}`}
                      className="flex items-start gap-2 p-2 border rounded"
                    >
                      <div className="flex-1">
                        {typeof item === "string" ? (
                          <Input
                            value={item}
                            onChange={(e) => {
                              const newData = { ...data };
                              let current = newData;
                              for (const p of path) {
                                current = current[p];
                              }
                              current[key][index] = e.target.value;
                              updateData(newData);
                            }}
                            placeholder={`${key} item ${index + 1}`}
                            className="text-sm"
                          />
                        ) : typeof item === "number" ? (
                          <Input
                            type="number"
                            value={item}
                            onChange={(e) => {
                              const newData = { ...data };
                              let current = newData;
                              for (const p of path) {
                                current = current[p];
                              }
                              current[key][index] =
                                parseFloat(e.target.value) || 0;
                              updateData(newData);
                            }}
                            placeholder={`${key} item ${index + 1}`}
                            className="text-sm"
                          />
                        ) : typeof item === "object" && item !== null ? (
                          <div className="space-y-2">
                            <Label className="text-xs font-medium">
                              Item {index + 1}
                            </Label>
                            <div className="grid grid-cols-1 gap-2 p-2 border rounded bg-gray-50">
                              {Object.keys(item).map((objKey) => (
                                <div key={objKey} className="space-y-1">
                                  <Label className="text-xs capitalize">
                                    {objKey}
                                  </Label>
                                  {typeof item[objKey] === "string" ? (
                                    // Special handling for common enum fields
                                    objKey === "type" &&
                                    ["policy", "milestone", "event"].some(
                                      (t) => item[objKey] === t
                                    ) ? (
                                      <Select
                                        value={item[objKey]}
                                        onValueChange={(value) => {
                                          const newData = { ...data };
                                          let current = newData;
                                          for (const p of path) {
                                            current = current[p];
                                          }
                                          current[key][index] = {
                                            ...current[key][index],
                                            [objKey]: value,
                                          };
                                          updateData(newData);
                                        }}
                                      >
                                        <SelectTrigger className="text-xs">
                                          <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                          <SelectItem value="policy">
                                            Policy
                                          </SelectItem>
                                          <SelectItem value="milestone">
                                            Milestone
                                          </SelectItem>
                                          <SelectItem value="event">
                                            Event
                                          </SelectItem>
                                        </SelectContent>
                                      </Select>
                                    ) : objKey === "status" ? (
                                      <Select
                                        value={item[objKey]}
                                        onValueChange={(value) => {
                                          const newData = { ...data };
                                          let current = newData;
                                          for (const p of path) {
                                            current = current[p];
                                          }
                                          current[key][index] = {
                                            ...current[key][index],
                                            [objKey]: value,
                                          };
                                          updateData(newData);
                                        }}
                                      >
                                        <SelectTrigger className="text-xs">
                                          <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                          <SelectItem value="success">
                                            Success
                                          </SelectItem>
                                          <SelectItem value="warning">
                                            Warning
                                          </SelectItem>
                                          <SelectItem value="error">
                                            Error
                                          </SelectItem>
                                          <SelectItem value="info">
                                            Info
                                          </SelectItem>
                                        </SelectContent>
                                      </Select>
                                    ) : objKey === "trend" ? (
                                      <Select
                                        value={item[objKey]}
                                        onValueChange={(value) => {
                                          const newData = { ...data };
                                          let current = newData;
                                          for (const p of path) {
                                            current = current[p];
                                          }
                                          current[key][index] = {
                                            ...current[key][index],
                                            [objKey]: value,
                                          };
                                          updateData(newData);
                                        }}
                                      >
                                        <SelectTrigger className="text-xs">
                                          <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                          <SelectItem value="up">Up</SelectItem>
                                          <SelectItem value="down">
                                            Down
                                          </SelectItem>
                                          <SelectItem value="stable">
                                            Stable
                                          </SelectItem>
                                        </SelectContent>
                                      </Select>
                                    ) : objKey === "icon" ? (
                                      <Select
                                        value={item[objKey]}
                                        onValueChange={(value) => {
                                          const newData = { ...data };
                                          let current = newData;
                                          for (const p of path) {
                                            current = current[p];
                                          }
                                          current[key][index] = {
                                            ...current[key][index],
                                            [objKey]: value,
                                          };
                                          updateData(newData);
                                        }}
                                      >
                                        <SelectTrigger className="text-xs">
                                          <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                          <SelectItem value="calendar">
                                            Calendar
                                          </SelectItem>
                                          <SelectItem value="thermometer">
                                            Thermometer
                                          </SelectItem>
                                          <SelectItem value="water">
                                            Water
                                          </SelectItem>
                                          <SelectItem value="euro">
                                            Euro
                                          </SelectItem>
                                          <SelectItem value="map">
                                            Map
                                          </SelectItem>
                                          <SelectItem value="chart">
                                            Chart
                                          </SelectItem>
                                          <SelectItem value="warning">
                                            Warning
                                          </SelectItem>
                                        </SelectContent>
                                      </Select>
                                    ) : objKey === "color" ? (
                                      <div className="flex items-center gap-2">
                                        <Input
                                          type="color"
                                          value={item[objKey]}
                                          onChange={(e) => {
                                            const newData = { ...data };
                                            let current = newData;
                                            for (const p of path) {
                                              current = current[p];
                                            }
                                            current[key][index] = {
                                              ...current[key][index],
                                              [objKey]: e.target.value,
                                            };
                                            updateData(newData);
                                          }}
                                          className="w-12 h-8 p-1 border rounded"
                                        />
                                        <Input
                                          value={item[objKey]}
                                          onChange={(e) => {
                                            const newData = { ...data };
                                            let current = newData;
                                            for (const p of path) {
                                              current = current[p];
                                            }
                                            current[key][index] = {
                                              ...current[key][index],
                                              [objKey]: e.target.value,
                                            };
                                            updateData(newData);
                                          }}
                                          className="text-xs flex-1"
                                          placeholder="Color value..."
                                        />
                                      </div>
                                    ) : objKey.includes("description") ||
                                      objKey.includes("content") ? (
                                      <Textarea
                                        value={item[objKey]}
                                        onChange={(e) => {
                                          const newData = { ...data };
                                          let current = newData;
                                          for (const p of path) {
                                            current = current[p];
                                          }
                                          current[key][index] = {
                                            ...current[key][index],
                                            [objKey]: e.target.value,
                                          };
                                          updateData(newData);
                                        }}
                                        rows={2}
                                        className="text-xs"
                                        placeholder={`Enter ${objKey}...`}
                                      />
                                    ) : (
                                      <Input
                                        value={item[objKey]}
                                        onChange={(e) => {
                                          const newData = { ...data };
                                          let current = newData;
                                          for (const p of path) {
                                            current = current[p];
                                          }
                                          current[key][index] = {
                                            ...current[key][index],
                                            [objKey]: e.target.value,
                                          };
                                          updateData(newData);
                                        }}
                                        className="text-xs"
                                        placeholder={`Enter ${objKey}...`}
                                      />
                                    )
                                  ) : typeof item[objKey] === "number" ? (
                                    <Input
                                      type="number"
                                      value={item[objKey]}
                                      onChange={(e) => {
                                        const newData = { ...data };
                                        let current = newData;
                                        for (const p of path) {
                                          current = current[p];
                                        }
                                        current[key][index] = {
                                          ...current[key][index],
                                          [objKey]:
                                            parseFloat(e.target.value) || 0,
                                        };
                                        updateData(newData);
                                      }}
                                      className="text-xs"
                                      placeholder={`Enter ${objKey}...`}
                                    />
                                  ) : typeof item[objKey] === "boolean" ? (
                                    <div className="flex items-center space-x-2">
                                      <Switch
                                        checked={item[objKey]}
                                        onCheckedChange={(checked) => {
                                          const newData = { ...data };
                                          let current = newData;
                                          for (const p of path) {
                                            current = current[p];
                                          }
                                          current[key][index] = {
                                            ...current[key][index],
                                            [objKey]: checked,
                                          };
                                          updateData(newData);
                                        }}
                                      />
                                      <Label className="text-xs">
                                        {objKey}
                                      </Label>
                                    </div>
                                  ) : (
                                    <Input
                                      value={item[objKey]?.toString() || ""}
                                      onChange={(e) => {
                                        const newData = { ...data };
                                        let current = newData;
                                        for (const p of path) {
                                          current = current[p];
                                        }
                                        current[key][index] = {
                                          ...current[key][index],
                                          [objKey]: e.target.value,
                                        };
                                        updateData(newData);
                                      }}
                                      className="text-xs"
                                      placeholder={`Enter ${objKey}...`}
                                    />
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        ) : (
                          <Input
                            value={item?.toString() || ""}
                            onChange={(e) => {
                              const newData = { ...data };
                              let current = newData;
                              for (const p of path) {
                                current = current[p];
                              }
                              current[key][index] = e.target.value;
                              updateData(newData);
                            }}
                            placeholder={`${key} item ${index + 1}`}
                            className="text-sm"
                          />
                        )}
                      </div>

                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          const newData = { ...data };
                          let current = newData;
                          for (const p of path) {
                            current = current[p];
                          }
                          current[key] = value.filter(
                            (_: any, i: number) => i !== index
                          );
                          updateData(newData);
                        }}
                      >
                        <X className="h-3 w-3" />
                      </Button>
                    </div>
                  ))}

                  {value.length === 0 && (
                    <div className="text-xs text-muted-foreground text-center py-4">
                      No items. Click "Add Item" to add the first item.
                    </div>
                  )}
                </div>
              </div>
            );
          } else if (value !== null) {
            Object.keys(value).forEach((subKey) => {
              addField(subKey, value[subKey], [...path, key]);
            });
          }
          break;
      }
    };

    Object.keys(data).forEach((key) => {
      addField(key, data[key]);
    });

    return fields;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  if (!selectedPair) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-2">
          <Languages className="h-5 w-5" />
          <h2 className="text-xl font-semibold">Paired Block Editor</h2>
          <Badge variant="outline">{blockPairs.length} blocks</Badge>
        </div>

        <Alert>
          <Link className="h-4 w-4" />
          <AlertDescription>
            <strong>Smart Syncing:</strong> Shared fields (images, references,
            technical parameters) appear once at the top and sync between both
            languages automatically.
          </AlertDescription>
        </Alert>

        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <div className="grid grid-cols-1 gap-4">
          {blockPairs.map((pair) => (
            <Card
              key={pair.orderIndex}
              className="cursor-pointer hover:shadow-md transition-shadow"
              onClick={() => setSelectedPair(pair)}
            >
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">#{pair.orderIndex}</Badge>
                    <Badge>{pair.blockType}</Badge>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={pair.english ? "default" : "secondary"}>
                      EN {pair.english ? "✓" : "✗"}
                    </Badge>
                    <Badge variant={pair.german ? "default" : "secondary"}>
                      DE {pair.german ? "✓" : "✗"}
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setSelectedPair(null)}
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back
          </Button>
          <Badge variant="outline">#{selectedPair.orderIndex}</Badge>
          <div className="space-y-1">
            <Label className="text-xs">Block Type</Label>
            <Select
              value={selectedPair.blockType}
              onValueChange={updateBlockType}
            >
              <SelectTrigger className="w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {AVAILABLE_BLOCK_TYPES.map((type) => (
                  <SelectItem key={type} value={type}>
                    {type}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <Button onClick={saveBothBlocks} disabled={saving} size="sm">
          {saving ? (
            <>
              <Loader2 className="mr-2 h-3 w-3 animate-spin" />
              Saving...
            </>
          ) : (
            <>
              <Save className="mr-2 h-3 w-3" />
              Save Block
            </>
          )}
        </Button>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {success && (
        <Alert>
          <AlertDescription>Block saved successfully!</AlertDescription>
        </Alert>
      )}

      {/* Shared Fields Section */}
      {renderSharedFields()}

      <div className="grid grid-cols-2 gap-6">
        {/* English Column */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg">English Content</CardTitle>
              {selectedPair.german && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    copyContentToLanguage(selectedPair.german!, "en")
                  }
                >
                  <Copy className="h-3 w-3 mr-1" />
                  Copy from DE
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {selectedPair.english ? (
              <div className="space-y-3">
                {renderLanguageSpecificFields(
                  selectedPair.english.data,
                  (newData) => {
                    const updatedPair = { ...selectedPair };
                    updatedPair.english!.data = newData;
                    setSelectedPair(updatedPair);
                  },
                  selectedPair.blockType,
                  "en"
                )}
              </div>
            ) : (
              <div className="text-center p-8 text-muted-foreground">
                English block missing
              </div>
            )}
          </CardContent>
        </Card>

        {/* German Column */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg">German Content</CardTitle>
              {selectedPair.english && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    copyContentToLanguage(selectedPair.english!, "de")
                  }
                >
                  <Copy className="h-3 w-3 mr-1" />
                  Copy from EN
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {selectedPair.german ? (
              <div className="space-y-3">
                {renderLanguageSpecificFields(
                  selectedPair.german.data,
                  (newData) => {
                    const updatedPair = { ...selectedPair };
                    updatedPair.german!.data = newData;
                    setSelectedPair(updatedPair);
                  },
                  selectedPair.blockType,
                  "de"
                )}
              </div>
            ) : (
              <div className="text-center p-8 text-muted-foreground">
                German block missing
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
