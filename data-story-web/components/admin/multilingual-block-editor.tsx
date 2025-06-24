"use client";

import React, { useState, useEffect } from "react";
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import {
  Loader2,
  Save,
  Languages,
  Image as ImageIcon,
} from "lucide-react";
import ImageSelector from "./image-selector";

interface ContentBlock {
  id: string;
  storyId: string;
  blockType: string;
  orderIndex: number;
  data: Record<string, unknown> | null;
  languageCode?: string;
}

// interface FormData {
//   blockType: string;
//   data: Record<string, unknown>;
// }

// eslint-disable-next-line @typescript-eslint/no-unused-vars
const AVAILABLE_BLOCK_TYPES = [
  "markdown",
  "callout",
  "quote",
  "statistics",
  "timeline",
  "visualization",
  "animated-quote",
  "animated-statistics",
  "climate-timeline",
  "climate-dashboard",
  "temperature-spiral",
  "interactive-callout",
  "neural-climate-network",
  "earth-pulse",
  "impact-comparison",
  "kpi-showcase",
  "climate-metamorphosis",
  "climate-timeline-minimal",
  "data-storm",
  "carbon-molecule-dance",
  "climate-infographic",
];

export default function MultilingualBlockEditor() {
  const [englishBlocks, setEnglishBlocks] = useState<ContentBlock[]>([]);
  const [germanBlocks, setGermanBlocks] = useState<ContentBlock[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [selectedBlockEn, setSelectedBlockEn] = useState<ContentBlock | null>(
    null
  );
  const [selectedBlockDe, setSelectedBlockDe] = useState<ContentBlock | null>(
    null
  );

  useEffect(() => {
    fetchBlocks();
  }, []);

  const fetchBlocks = async () => {
    try {
      const { data: stories } = await supabase
        .from("content_stories")
        .select("id, language_code")
        .in("language_code", ["en", "de"]);

      if (!stories) return;

      const englishStory = stories.find((s) => s.language_code === "en");
      const germanStory = stories.find((s) => s.language_code === "de");

      const fetchBlocksForStory = async (storyId: string) => {
        const { data, error } = await supabase
          .from("content_blocks")
          .select("*")
          .eq("story_id", storyId)
          .order("order_index");

        if (error) throw error;
        return data || [];
      };

      if (englishStory) {
        const enBlocks = await fetchBlocksForStory(englishStory.id);
        setEnglishBlocks(enBlocks.map((b) => ({ 
          id: b.id,
          storyId: b.story_id || '',
          blockType: b.block_type,
          orderIndex: b.order_index,
          data: b.data as Record<string, unknown> | null,
          languageCode: "en" 
        })));
      }

      if (germanStory) {
        const deBlocks = await fetchBlocksForStory(germanStory.id);
        setGermanBlocks(deBlocks.map((b) => ({ 
          id: b.id,
          storyId: b.story_id || '',
          blockType: b.block_type,
          orderIndex: b.order_index,
          data: b.data as Record<string, unknown> | null,
          languageCode: "de" 
        })));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load blocks");
    } finally {
      setLoading(false);
    }
  };

  const saveBlock = async (block: ContentBlock) => {
    setSaving(true);
    setError(null);

    try {
      const { error } = await supabase.from("content_blocks").upsert({
        id: block.id,
        story_id: block.storyId,
        block_type: block.blockType,
        order_index: block.orderIndex,
        data: block.data as never,
      });

      if (error) throw error;

      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
      await fetchBlocks();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save block");
    } finally {
      setSaving(false);
    }
  };

  const renderFormFields = (
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    data: any,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    updateData: (newData: any) => void,
    blockType: string
  ) => {
    const fields: React.ReactElement[] = [];

    if (!data) return fields;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const addField = (key: string, value: any, path: string[] = []) => {
      const fieldPath = path.length > 0 ? `${path.join(".")}.${key}` : key;
      const fieldId = fieldPath.replace(/\./g, "-");

      if (value === null || value === undefined) {
        fields.push(
          <div key={fieldPath} className="space-y-2">
            <Label htmlFor={fieldId}>{key}</Label>
            <Input
              id={fieldId}
              value=""
              onChange={(e) => {
                const newData = { ...data };
                let current = newData;
                for (const p of path) {
                  current = current[p];
                }
                current[key] = e.target.value;
                updateData(newData);
              }}
              placeholder={`Enter ${key}...`}
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
              <div key={fieldPath} className="space-y-2">
                <Label htmlFor={fieldId}>{key}</Label>
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
                  placeholder={`Enter ${key}...`}
                />
              </div>
            );
          } else {
            fields.push(
              <div key={fieldPath} className="space-y-2">
                <Label htmlFor={fieldId}>{key}</Label>
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
                  placeholder={`Enter ${key}...`}
                />
              </div>
            );
          }
          break;

        case "number":
          fields.push(
            <div key={fieldPath} className="space-y-2">
              <Label htmlFor={fieldId}>{key}</Label>
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
              />
            </div>
          );
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
              <Label htmlFor={fieldId}>{key}</Label>
            </div>
          );
          break;

        case "object":
          if (Array.isArray(value)) {
            if (
              key === "references" &&
              Array.isArray(value) &&
              value.length > 0
            ) {
              fields.push(
                <div key={fieldPath} className="space-y-2">
                  <Label>References</Label>
                  <div className="flex flex-wrap gap-1">
                    {value.map((ref: string, idx: number) => (
                      <Badge key={idx} variant="secondary">
                        {ref}
                      </Badge>
                    ))}
                  </div>
                </div>
              );
            } else {
              fields.push(
                <div key={fieldPath} className="space-y-2">
                  <Label>{key} (Array)</Label>
                  <div className="text-sm text-muted-foreground">
                    Array with {value.length} items
                  </div>
                </div>
              );
            }
          } else if (value !== null) {
            Object.keys(value).forEach((subKey) => {
              if (key === "data" && blockType === "visualization") {
                if (subKey === "imageId") {
                  fields.push(
                    <div key={`${fieldPath}.${subKey}`} className="space-y-2">
                      <Label>
                        <ImageIcon className="inline h-4 w-4 mr-1" />
                        Image Selection
                      </Label>
                      <ImageSelector
                        value={value[subKey]}
                        onChange={(imageId) => {
                          const newData = { ...data };
                          let current = newData;
                          for (const p of path) {
                            current = current[p];
                          }
                          current[key][subKey] = imageId;
                          updateData(newData);
                        }}
                        category={value.imageCategory}
                        scenario={value.imageScenario}
                      />
                    </div>
                  );
                  return;
                }
              }
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

  const renderBlockEditor = (
    blocks: ContentBlock[],
    selectedBlock: ContentBlock | null,
    setSelectedBlock: (block: ContentBlock | null) => void,
    language: string
  ) => {
    if (!selectedBlock) {
      return (
        <div className="space-y-4">
          <div className="text-center p-8 text-muted-foreground">
            Select a block to edit or create a new one
          </div>
          <div className="grid grid-cols-1 gap-4">
            {blocks.map((block) => (
              <Card
                key={block.id}
                className="cursor-pointer hover:shadow-md transition-shadow"
                onClick={() => setSelectedBlock(block)}
              >
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <Badge variant="outline">#{block.orderIndex}</Badge>
                      <Badge className="ml-2">{block.blockType}</Badge>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {language}
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
              onClick={() => setSelectedBlock(null)}
            >
              ← Back to List
            </Button>
            <Badge variant="outline">#{selectedBlock.orderIndex}</Badge>
            <Badge>{selectedBlock.blockType}</Badge>
          </div>
          <Button onClick={() => saveBlock(selectedBlock)} disabled={saving}>
            {saving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="mr-2 h-4 w-4" />
                Save Block
              </>
            )}
          </Button>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Block Properties</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Block Type</Label>
                <Select
                  value={selectedBlock.blockType}
                  onValueChange={(value) =>
                    setSelectedBlock({ ...selectedBlock, blockType: value })
                  }
                >
                  <SelectTrigger>
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
              <div className="space-y-2">
                <Label>Order Index</Label>
                <Input
                  type="number"
                  value={selectedBlock.orderIndex}
                  onChange={(e) =>
                    setSelectedBlock({
                      ...selectedBlock,
                      orderIndex: parseInt(e.target.value) || 0,
                    })
                  }
                />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Block Data</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {renderFormFields(
              selectedBlock.data,
              (newData) =>
                setSelectedBlock({ ...selectedBlock, data: newData }),
              selectedBlock.blockType
            )}
          </CardContent>
        </Card>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Languages className="h-5 w-5" />
        <h2 className="text-xl font-semibold">Multilingual Block Editor</h2>
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

      <Tabs defaultValue="english" className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="english">
            English ({englishBlocks.length} blocks)
          </TabsTrigger>
          <TabsTrigger value="german">
            Deutsch ({germanBlocks.length} blocks)
          </TabsTrigger>
        </TabsList>

        <TabsContent value="english">
          <Card>
            <CardHeader>
              <CardTitle>English Content Blocks</CardTitle>
            </CardHeader>
            <CardContent>
              {renderBlockEditor(
                englishBlocks,
                selectedBlockEn,
                setSelectedBlockEn,
                "English"
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="german">
          <Card>
            <CardHeader>
              <CardTitle>German Content Blocks</CardTitle>
            </CardHeader>
            <CardContent>
              {renderBlockEditor(
                germanBlocks,
                selectedBlockDe,
                setSelectedBlockDe,
                "Deutsch"
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
