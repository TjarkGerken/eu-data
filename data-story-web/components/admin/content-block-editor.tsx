"use client";

import { useState, useEffect } from "react";
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
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { BlockTypeFields } from "./block-type-fields";
import {
  Loader2,
  Save,
  ArrowLeft,
  Languages,
  Copy,
  Link,
  X,
  Plus,
  Trash2,
  Edit,
  ArrowUp,
  ArrowDown,
  AlertCircle,
} from "lucide-react";
import { MultiSelectReferences } from "@/components/ui/multi-select-references";
import { useToast } from "@/hooks/use-toast";
import {
  validateContentBlock,
  getFieldError,
  hasFieldError,
  getDefaultBlockData,
  type ValidationError,
  type ContentBlockFormData,
} from "@/lib/validation";

interface ContentBlock {
  id: string;
  story_id: string | null;
  block_type: string;
  order_index: number;
  data: any;
  title?: string;
  content?: string;
  language?: string;
}

interface BlockPair {
  orderIndex: number;
  blockType: string;
  english: ContentBlock | null;
  german: ContentBlock | null;
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

export default function ContentBlockEditor() {
  const [blockPairs, setBlockPairs] = useState<BlockPair[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedPair, setSelectedPair] = useState<BlockPair | null>(null);
  const [showNewForm, setShowNewForm] = useState(false);
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>(
    []
  );
  const [formData, setFormData] = useState<ContentBlockFormData>({
    story_id: "",
    block_type: "",
    title: "",
    content: "",
    data: {},
    language: "en",
    order_index: 0,
    selectedReferences: [],
  });
  const { toast } = useToast();

  useEffect(() => {
    fetchBlockPairs();
  }, []);

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
            english,
            german,
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

  const resetForm = () => {
    setFormData({
      story_id: "",
      block_type: "",
      title: "",
      content: "",
      data: {},
      language: "en",
      order_index: blockPairs.length + 1,
      selectedReferences: [],
    });
    setValidationErrors([]);
  };

  const updateFormField = (field: keyof ContentBlockFormData, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }));

    if (validationErrors.length > 0) {
      setValidationErrors((prev) =>
        prev.filter((error) => error.field !== field)
      );
    }
  };

  const createNewBlockPair = async () => {
    const validation = validateContentBlock(formData);
    setValidationErrors(validation.errors);

    if (!validation.isValid) {
      toast({
        title: "Validation failed",
        description: "Please fix the errors before creating the block pair",
        variant: "destructive",
      });
      return;
    }

    setSaving(true);
    try {
      const { data: stories } = await supabase
        .from("content_stories")
        .select("id, language_code")
        .in("language_code", ["en", "de"]);

      if (!stories) throw new Error("No stories found");

      const englishStory = stories.find((s) => s.language_code === "en");
      const germanStory = stories.find((s) => s.language_code === "de");

      if (!englishStory || !germanStory) {
        throw new Error("Missing English or German story");
      }

      const blockData = {
        block_type: formData.block_type,
        order_index: formData.order_index,
        data: formData.data || {},
      };

      const [englishResult, germanResult] = await Promise.all([
        supabase
          .from("content_blocks")
          .insert([
            {
              ...blockData,
              story_id: englishStory.id,
              title: formData.title || null,
              content: formData.content || null,
              language: "en",
            },
          ])
          .select("id")
          .single(),
        supabase
          .from("content_blocks")
          .insert([
            {
              ...blockData,
              story_id: germanStory.id,
              title: formData.title || null,
              content: formData.content || null,
              language: "de",
            },
          ])
          .select("id")
          .single(),
      ]);

      if (englishResult.error) throw englishResult.error;
      if (germanResult.error) throw germanResult.error;

      if (
        formData.selectedReferences &&
        formData.selectedReferences.length > 0
      ) {
        const referenceInserts = [
          ...formData.selectedReferences.map((refId) => ({
            block_id: englishResult.data.id,
            reference_id: refId,
          })),
          ...formData.selectedReferences.map((refId) => ({
            block_id: germanResult.data.id,
            reference_id: refId,
          })),
        ];

        await supabase.from("block_references").insert(referenceInserts);
      }

      toast({
        title: "Success",
        description: "Block pair created successfully",
      });

      setShowNewForm(false);
      resetForm();
      fetchBlockPairs();
    } catch (error) {
      toast({
        title: "Failed to create block pair",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  const deletePair = async (orderIndex: number) => {
    if (!confirm("Are you sure you want to delete this block pair?")) return;

    try {
      const pair = blockPairs.find((p) => p.orderIndex === orderIndex);
      if (!pair) return;

      const deletePromises = [];

      if (pair.english) {
        deletePromises.push(
          supabase
            .from("block_references")
            .delete()
            .eq("block_id", pair.english.id),
          supabase.from("content_blocks").delete().eq("id", pair.english.id)
        );
      }

      if (pair.german) {
        deletePromises.push(
          supabase
            .from("block_references")
            .delete()
            .eq("block_id", pair.german.id),
          supabase.from("content_blocks").delete().eq("id", pair.german.id)
        );
      }

      await Promise.all(deletePromises);

      toast({
        title: "Success",
        description: "Block pair deleted successfully",
      });

      fetchBlockPairs();
    } catch (error) {
      toast({
        title: "Failed to delete block pair",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      });
    }
  };

  const moveBlockPair = async (
    orderIndex: number,
    direction: "up" | "down"
  ) => {
    const targetIndex = direction === "up" ? orderIndex - 1 : orderIndex + 1;
    const currentPair = blockPairs.find((p) => p.orderIndex === orderIndex);
    const targetPair = blockPairs.find((p) => p.orderIndex === targetIndex);

    if (!currentPair || !targetPair) return;

    try {
      const updates = [];

      if (currentPair.english) {
        updates.push(
          supabase
            .from("content_blocks")
            .update({ order_index: targetIndex })
            .eq("id", currentPair.english.id)
        );
      }
      if (currentPair.german) {
        updates.push(
          supabase
            .from("content_blocks")
            .update({ order_index: targetIndex })
            .eq("id", currentPair.german.id)
        );
      }
      if (targetPair.english) {
        updates.push(
          supabase
            .from("content_blocks")
            .update({ order_index: orderIndex })
            .eq("id", targetPair.english.id)
        );
      }
      if (targetPair.german) {
        updates.push(
          supabase
            .from("content_blocks")
            .update({ order_index: orderIndex })
            .eq("id", targetPair.german.id)
        );
      }

      await Promise.all(updates);

      toast({
        title: "Success",
        description: `Block pair moved ${direction} successfully`,
      });

      fetchBlockPairs();
    } catch (error) {
      toast({
        title: "Failed to move block pair",
        description: "Could not reorder blocks",
        variant: "destructive",
      });
    }
  };

  const updateSharedField = (fieldPath: string[], value: any) => {
    if (!selectedPair) return;

    const updatedPair = { ...selectedPair };

    [updatedPair.english, updatedPair.german].forEach((block) => {
      if (block) {
        if (fieldPath.length === 0) {
          // Replace entire data object
          block.data = value;
        } else {
          // Update specific field path
          let current = block.data;

          for (let i = 0; i < fieldPath.length - 1; i++) {
            if (!current[fieldPath[i]]) current[fieldPath[i]] = {};
            current = current[fieldPath[i]];
          }

          current[fieldPath[fieldPath.length - 1]] = value;
        }
      }
    });

    setSelectedPair(updatedPair);
  };

  const saveBothBlocks = async () => {
    if (!selectedPair) return;

    setSaving(true);
    setError(null);

    try {
      const updates = [];

      if (selectedPair.english) {
        updates.push(
          supabase
            .from("content_blocks")
            .update({
              block_type: selectedPair.blockType,
              data: selectedPair.english.data,
              title: selectedPair.english.title || null,
              content: selectedPair.english.content || null,
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
              title: selectedPair.german.title || null,
              content: selectedPair.german.content || null,
            })
            .eq("id", selectedPair.german.id)
        );
      }

      const results = await Promise.all(updates);

      for (const result of results) {
        if (result.error) throw result.error;
      }

      toast({
        title: "Success",
        description: "Block pair saved successfully",
      });

      fetchBlockPairs();
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to save blocks";
      setError(errorMessage);
      toast({
        title: "Failed to save blocks",
        description: errorMessage,
        variant: "destructive",
      });
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
      targetBlock.data = { ...fromBlock.data };
      targetBlock.title = fromBlock.title;
      targetBlock.content = fromBlock.content;
      setSelectedPair(updatedPair);
    }
  };

  const renderSharedFields = () => {
    if (!selectedPair || (!selectedPair.english && !selectedPair.german))
      return null;

    const currentData = (selectedPair.english || selectedPair.german)!.data;
    const blockType = selectedPair.blockType;

    return (
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Link className="h-4 w-4" />
            Shared Fields
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <BlockTypeFields
            blockType={blockType}
            data={currentData}
            onDataChange={(newData) => {
              updateSharedField([], newData);
            }}
            validationErrors={[]}
            mode="shared"
          />
        </CardContent>
      </Card>
    );
  };

  const renderLanguageSpecificFields = (
    block: ContentBlock | null,
    updateBlock: (updatedBlock: ContentBlock) => void,
    language: "en" | "de"
  ) => {
    if (!block) return null;

    return (
      <BlockTypeFields
        blockType={block.block_type}
        data={block.data}
        onDataChange={(newData) => updateBlock({ ...block, data: newData })}
        validationErrors={[]}
        title={block.title}
        content={block.content}
        onTitleChange={(title) => updateBlock({ ...block, title })}
        onContentChange={(content) => updateBlock({ ...block, content })}
        mode="language-specific"
      />
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
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Languages className="h-5 w-5" />
          <h2 className="text-xl font-semibold">Content Block Editor</h2>
          <Badge variant="outline">{blockPairs.length} block pairs</Badge>
        </div>
        <Button onClick={() => setShowNewForm(true)}>
          <Plus className="w-4 h-4 mr-2" />
          Add Block Pair
        </Button>
      </div>

      <Alert>
        <Link className="h-4 w-4" />
        <AlertDescription>
          <strong>Smart Syncing:</strong> Shared fields (references, technical
          parameters) sync between both languages automatically.
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
            className="hover:shadow-md transition-shadow"
          >
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Badge variant="outline">#{pair.orderIndex}</Badge>
                  <Badge>{pair.blockType}</Badge>
                  <Badge variant={pair.english ? "default" : "secondary"}>
                    EN {pair.english ? "✓" : "✗"}
                  </Badge>
                  <Badge variant={pair.german ? "default" : "secondary"}>
                    DE {pair.german ? "✓" : "✗"}
                  </Badge>
                </div>
                <div className="flex gap-1">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => moveBlockPair(pair.orderIndex, "up")}
                    disabled={pair.orderIndex === 1}
                    title="Move up"
                  >
                    <ArrowUp className="w-3 h-3" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => moveBlockPair(pair.orderIndex, "down")}
                    disabled={pair.orderIndex === blockPairs.length}
                    title="Move down"
                  >
                    <ArrowDown className="w-3 h-3" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setSelectedPair(pair)}
                    title="Edit pair"
                  >
                    <Edit className="w-3 h-3" />
                  </Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => deletePair(pair.orderIndex)}
                    title="Delete pair"
                  >
                    <Trash2 className="w-3 h-3" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {blockPairs.length === 0 && (
        <Card>
          <CardContent className="pt-6 text-center text-muted-foreground">
            No block pairs found. Add one to get started.
          </CardContent>
        </Card>
      )}

      <Dialog open={showNewForm} onOpenChange={setShowNewForm}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Create New Block Pair</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="block_type">Block Type</Label>
                <Select
                  value={formData.block_type}
                  onValueChange={(value) => {
                    updateFormField("block_type", value);
                    updateFormField("data", getDefaultBlockData(value));
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select block type" />
                  </SelectTrigger>
                  <SelectContent>
                    {AVAILABLE_BLOCK_TYPES.map((type) => (
                      <SelectItem key={type} value={type}>
                        {type}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {validationErrors.find((e) => e.field === "block_type") && (
                  <p className="text-sm text-red-500 mt-1">
                    {
                      validationErrors.find((e) => e.field === "block_type")
                        ?.message
                    }
                  </p>
                )}
              </div>
              <div>
                <Label htmlFor="order_index">Order Index</Label>
                <Input
                  type="number"
                  value={formData.order_index}
                  onChange={(e) =>
                    updateFormField("order_index", parseInt(e.target.value))
                  }
                  min="1"
                />
              </div>
            </div>

            {formData.block_type && (
              <BlockTypeFields
                blockType={formData.block_type}
                data={formData.data}
                onDataChange={(newData) => updateFormField("data", newData)}
                validationErrors={validationErrors}
                title={formData.title}
                content={formData.content}
                onTitleChange={(title) => updateFormField("title", title)}
                onContentChange={(content) =>
                  updateFormField("content", content)
                }
              />
            )}

            <div>
              <Label>References</Label>
              <MultiSelectReferences
                selectedReferenceIds={formData.selectedReferences || []}
                onSelectionChange={(referenceIds) =>
                  updateFormField("selectedReferences", referenceIds)
                }
                placeholder="Select references for this block..."
              />
            </div>

            {validationErrors.length > 0 && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  <ul className="list-disc pl-4">
                    {validationErrors.map((error, index) => (
                      <li key={index}>{error.message}</li>
                    ))}
                  </ul>
                </AlertDescription>
              </Alert>
            )}

            <div className="flex gap-2 pt-4">
              <Button
                variant="outline"
                onClick={() => setShowNewForm(false)}
                className="flex-1"
              >
                Cancel
              </Button>
              <Button
                onClick={createNewBlockPair}
                disabled={saving}
                className="flex-1"
              >
                {saving ? "Creating..." : "Create Block Pair"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog
        open={!!selectedPair}
        onOpenChange={(open) => !open && setSelectedPair(null)}
      >
        <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              Edit Block Pair #{selectedPair?.orderIndex} -{" "}
              {selectedPair?.blockType}
            </DialogTitle>
          </DialogHeader>

          {selectedPair && (
            <div className="space-y-6">
              <div className="flex items-center gap-4 p-4 bg-muted rounded-lg">
                <div className="flex items-center gap-2">
                  <Label>Block Type:</Label>
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

              {renderSharedFields()}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card>
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base flex items-center gap-2">
                        🇺🇸 English
                        {selectedPair.english && (
                          <Badge variant="outline" className="text-xs">
                            ID: {selectedPair.english.id.slice(0, 8)}
                          </Badge>
                        )}
                      </CardTitle>
                      {selectedPair.german && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() =>
                            copyContentToLanguage(selectedPair.german!, "en")
                          }
                          title="Copy from German"
                        >
                          <Copy className="w-3 h-3" />
                        </Button>
                      )}
                    </div>
                  </CardHeader>
                  <CardContent>
                    {selectedPair.english ? (
                      renderLanguageSpecificFields(
                        selectedPair.english,
                        (updatedBlock) =>
                          setSelectedPair({
                            ...selectedPair,
                            english: updatedBlock,
                          }),
                        "en"
                      )
                    ) : (
                      <p className="text-muted-foreground text-sm">
                        No English version available
                      </p>
                    )}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base flex items-center gap-2">
                        🇩🇪 German
                        {selectedPair.german && (
                          <Badge variant="outline" className="text-xs">
                            ID: {selectedPair.german.id.slice(0, 8)}
                          </Badge>
                        )}
                      </CardTitle>
                      {selectedPair.english && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() =>
                            copyContentToLanguage(selectedPair.english!, "de")
                          }
                          title="Copy from English"
                        >
                          <Copy className="w-3 h-3" />
                        </Button>
                      )}
                    </div>
                  </CardHeader>
                  <CardContent>
                    {selectedPair.german ? (
                      renderLanguageSpecificFields(
                        selectedPair.german,
                        (updatedBlock) =>
                          setSelectedPair({
                            ...selectedPair,
                            german: updatedBlock,
                          }),
                        "de"
                      )
                    ) : (
                      <p className="text-muted-foreground text-sm">
                        No German version available
                      </p>
                    )}
                  </CardContent>
                </Card>
              </div>

              {error && (
                <Alert variant="destructive">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <div className="flex gap-2 pt-4">
                <Button
                  variant="outline"
                  onClick={() => setSelectedPair(null)}
                  className="flex-1"
                >
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back to List
                </Button>
                <Button
                  onClick={saveBothBlocks}
                  disabled={saving}
                  className="flex-1"
                >
                  <Save className="w-4 h-4 mr-2" />
                  {saving ? "Saving..." : "Save Block Pair"}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
