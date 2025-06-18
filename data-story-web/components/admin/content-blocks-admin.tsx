"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import {
  Trash2,
  Plus,
  Save,
  X,
  Edit,
  AlertCircle,
  ArrowUp,
  ArrowDown,
  List,
} from "lucide-react";
import { supabase } from "@/lib/supabase";
import type { ContentBlock } from "@/lib/supabase";
import { useToast } from "@/hooks/use-toast";
import { MultiSelectReferences } from "@/components/ui/multi-select-references";
import {
  validateContentBlock,
  getFieldError,
  hasFieldError,
  type ValidationError,
  type ContentBlockFormData,
} from "@/lib/validation";
import { Alert, AlertDescription } from "@/components/ui/alert";

const BLOCK_TYPES = [
  "visualization",
  "callout",
  "statistics",
  "markdown",
  "timeline",
  "quote",
  "climate-timeline",
  "animated-quote",
  "climate-dashboard",
  "temperature-spiral",
  "animated-statistics",
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

export default function ContentBlocksAdmin() {
  const [blocks, setBlocks] = useState<ContentBlock[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [showNewForm, setShowNewForm] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>(
    []
  );
  const [blockReferences, setBlockReferences] = useState<
    Record<string, string[]>
  >({});
  const { toast } = useToast();

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

  useEffect(() => {
    loadBlocks();
    loadBlockReferences();
  }, []);

  const loadBlocks = async () => {
    setIsLoading(true);
    try {
      const { data, error } = await supabase
        .from("content_blocks")
        .select("*")
        .order("order_index", { ascending: true });

      if (error) throw error;
      setBlocks(data || []);
    } catch (error) {
      toast({
        title: "Failed to load blocks",
        description:
          error instanceof Error ? error.message : "Unknown error occurred",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const loadBlockReferences = async () => {
    try {
      const { data, error } = await supabase
        .from("block_references")
        .select("block_id, reference_id");

      if (error) throw error;

      const referencesMap: Record<string, string[]> = {};
      data?.forEach(({ block_id, reference_id }) => {
        if (!referencesMap[block_id]) {
          referencesMap[block_id] = [];
        }
        referencesMap[block_id].push(reference_id);
      });

      setBlockReferences(referencesMap);
    } catch (error) {
      console.error("Error loading block references:", error);
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
      order_index: 0,
      selectedReferences: [],
    });
    setValidationErrors([]);
  };

  const handleSave = async () => {
    const validation = validateContentBlock(formData);
    setValidationErrors(validation.errors);

    if (!validation.isValid) {
      toast({
        title: "Validation failed",
        description: "Please fix the errors before saving",
        variant: "destructive",
      });
      return;
    }

    setIsSaving(true);
    try {
      const saveData = {
        story_id: formData.story_id,
        block_type: formData.block_type,
        title: formData.title || null,
        content: formData.content || null,
        data:
          formData.data && Object.keys(formData.data).length > 0
            ? formData.data
            : null,
        language: formData.language,
        order_index: formData.order_index,
      };

      let blockId = editingId;

      if (editingId) {
        const { error } = await supabase
          .from("content_blocks")
          .update(saveData)
          .eq("id", editingId);

        if (error) throw error;
        toast({
          title: "Success",
          description: "Block updated successfully",
        });
      } else {
        const { data: insertedData, error } = await supabase
          .from("content_blocks")
          .insert([saveData])
          .select("id")
          .single();

        if (error) throw error;
        blockId = insertedData.id;
        toast({
          title: "Success",
          description: "Block created successfully",
        });
      }

      if (blockId && formData.selectedReferences) {
        await updateBlockReferences(blockId, formData.selectedReferences);
      }

      setEditingId(null);
      setShowNewForm(false);
      resetForm();
      loadBlocks();
      loadBlockReferences();
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Operation failed";
      toast({
        title: editingId ? "Failed to update block" : "Failed to create block",
        description: errorMessage,
        variant: "destructive",
      });

      if (errorMessage.includes("foreign key")) {
        toast({
          title: "Invalid Story ID",
          description:
            "The specified story ID does not exist. Please check the story ID.",
          variant: "destructive",
        });
      }
    } finally {
      setIsSaving(false);
    }
  };

  const updateBlockReferences = async (
    blockId: string,
    referenceIds: string[]
  ) => {
    await supabase.from("block_references").delete().eq("block_id", blockId);

    if (referenceIds.length > 0) {
      const insertData = referenceIds.map((refId) => ({
        block_id: blockId,
        reference_id: refId,
      }));

      const { error } = await supabase
        .from("block_references")
        .insert(insertData);

      if (error) throw error;
    }
  };

  const handleEdit = (block: ContentBlock) => {
    setFormData({
      story_id: block.story_id || "",
      block_type: block.block_type,
      title: (block as any).title || "",
      content: (block as any).content || "",
      data: block.data || {},
      language: ((block as any).language as "en" | "de") || "en",
      order_index: block.order_index,
      selectedReferences: blockReferences[block.id] || [],
    });
    setEditingId(block.id);
    setShowNewForm(false);
    setValidationErrors([]);
  };

  const handleDelete = async (id: string) => {
    if (
      !confirm(
        "Are you sure you want to delete this block? This will also remove all associated references."
      )
    )
      return;

    try {
      await supabase.from("block_references").delete().eq("block_id", id);

      const { error } = await supabase
        .from("content_blocks")
        .delete()
        .eq("id", id);

      if (error) throw error;
      toast({
        title: "Success",
        description: "Block deleted successfully",
      });
      loadBlocks();
      loadBlockReferences();
    } catch (error) {
      toast({
        title: "Failed to delete block",
        description:
          error instanceof Error ? error.message : "Unknown error occurred",
        variant: "destructive",
      });
    }
  };

  const handleCancel = () => {
    setEditingId(null);
    setShowNewForm(false);
    resetForm();
  };

  const updateFormField = (field: keyof ContentBlockFormData, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }));

    if (validationErrors.length > 0) {
      setValidationErrors((prev) =>
        prev.filter((error) => error.field !== field)
      );
    }
  };

  const moveBlockUp = async (blockId: string, currentOrder: number) => {
    const blockToMoveUp = blocks.find(
      (b) => b.order_index === currentOrder - 1
    );
    if (!blockToMoveUp) return;

    try {
      const { error: updateError1 } = await supabase
        .from("content_blocks")
        .update({ order_index: currentOrder - 1 })
        .eq("id", blockId);

      const { error: updateError2 } = await supabase
        .from("content_blocks")
        .update({ order_index: currentOrder })
        .eq("id", blockToMoveUp.id);

      if (updateError1 || updateError2) {
        throw new Error("Failed to swap blocks");
      }

      toast({
        title: "Success",
        description: "Block moved up successfully",
      });
      loadBlocks();
    } catch (error) {
      toast({
        title: "Failed to move block",
        description: "Could not reorder blocks",
        variant: "destructive",
      });
    }
  };

  const moveBlockDown = async (blockId: string, currentOrder: number) => {
    const blockToMoveDown = blocks.find(
      (b) => b.order_index === currentOrder + 1
    );
    if (!blockToMoveDown) return;

    try {
      const { error: updateError1 } = await supabase
        .from("content_blocks")
        .update({ order_index: currentOrder + 1 })
        .eq("id", blockId);

      const { error: updateError2 } = await supabase
        .from("content_blocks")
        .update({ order_index: currentOrder })
        .eq("id", blockToMoveDown.id);

      if (updateError1 || updateError2) {
        throw new Error("Failed to swap blocks");
      }

      toast({
        title: "Success",
        description: "Block moved down successfully",
      });
      loadBlocks();
    } catch (error) {
      toast({
        title: "Failed to move block",
        description: "Could not reorder blocks",
        variant: "destructive",
      });
    }
  };

  const moveBlockToIndex = async (blockId: string, targetIndex: number) => {
    if (targetIndex < 0 || targetIndex >= blocks.length) {
      toast({
        title: "Invalid index",
        description: `Index must be between 0 and ${blocks.length - 1}`,
        variant: "destructive",
      });
      return;
    }

    const currentBlock = blocks.find((b) => b.id === blockId);
    if (!currentBlock) return;

    const currentIndex = currentBlock.order_index;
    if (currentIndex === targetIndex) return;

    try {
      const isMovingUp = targetIndex < currentIndex;
      const affectedBlocks = blocks.filter((b) => {
        if (isMovingUp) {
          return b.order_index >= targetIndex && b.order_index < currentIndex;
        } else {
          return b.order_index > currentIndex && b.order_index <= targetIndex;
        }
      });

      const updates = [
        supabase
          .from("content_blocks")
          .update({ order_index: targetIndex })
          .eq("id", blockId),
      ];

      affectedBlocks.forEach((block) => {
        const newOrder = isMovingUp
          ? block.order_index + 1
          : block.order_index - 1;
        updates.push(
          supabase
            .from("content_blocks")
            .update({ order_index: newOrder })
            .eq("id", block.id)
        );
      });

      await Promise.all(updates);

      toast({
        title: "Success",
        description: `Block moved to position ${targetIndex}`,
      });
      loadBlocks();
    } catch (error) {
      toast({
        title: "Failed to move block",
        description: "Could not move block to specified index",
        variant: "destructive",
      });
    }
  };

  if (isLoading) {
    return <div>Loading blocks...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Content Blocks</h2>
        <Button
          onClick={() => setShowNewForm(true)}
          disabled={editingId !== null || showNewForm}
        >
          <Plus className="w-4 h-4 mr-2" />
          Add Block
        </Button>
      </div>

      {(showNewForm || editingId) && (
        <Card>
          <CardHeader>
            <CardTitle>{editingId ? "Edit Block" : "New Block"}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {validationErrors.length > 0 && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  Please fix the following errors:
                  <ul className="list-disc list-inside mt-2">
                    {validationErrors.map((error, index) => (
                      <li key={index}>{error.message}</li>
                    ))}
                  </ul>
                </AlertDescription>
              </Alert>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="story_id">Story ID *</Label>
                <Input
                  id="story_id"
                  value={formData.story_id}
                  onChange={(e) => updateFormField("story_id", e.target.value)}
                  placeholder="main-story"
                  className={
                    hasFieldError(validationErrors, "story_id")
                      ? "border-destructive"
                      : ""
                  }
                />
                {getFieldError(validationErrors, "story_id") && (
                  <p className="text-sm text-destructive mt-1">
                    {getFieldError(validationErrors, "story_id")}
                  </p>
                )}
              </div>
              <div>
                <Label htmlFor="language">Language *</Label>
                <Select
                  value={formData.language}
                  onValueChange={(value) => updateFormField("language", value)}
                >
                  <SelectTrigger
                    className={
                      hasFieldError(validationErrors, "language")
                        ? "border-destructive"
                        : ""
                    }
                  >
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="en">English</SelectItem>
                    <SelectItem value="de">German</SelectItem>
                  </SelectContent>
                </Select>
                {getFieldError(validationErrors, "language") && (
                  <p className="text-sm text-destructive mt-1">
                    {getFieldError(validationErrors, "language")}
                  </p>
                )}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="block_type">Block Type *</Label>
                <Select
                  value={formData.block_type}
                  onValueChange={(value) =>
                    updateFormField("block_type", value)
                  }
                >
                  <SelectTrigger
                    className={
                      hasFieldError(validationErrors, "block_type")
                        ? "border-destructive"
                        : ""
                    }
                  >
                    <SelectValue placeholder="Select block type" />
                  </SelectTrigger>
                  <SelectContent>
                    {BLOCK_TYPES.map((type) => (
                      <SelectItem key={type} value={type}>
                        {type}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {getFieldError(validationErrors, "block_type") && (
                  <p className="text-sm text-destructive mt-1">
                    {getFieldError(validationErrors, "block_type")}
                  </p>
                )}
              </div>
              <div>
                <Label htmlFor="order_index">Order *</Label>
                <Input
                  id="order_index"
                  type="number"
                  value={formData.order_index}
                  onChange={(e) =>
                    updateFormField(
                      "order_index",
                      parseInt(e.target.value) || 0
                    )
                  }
                  className={
                    hasFieldError(validationErrors, "order_index")
                      ? "border-destructive"
                      : ""
                  }
                />
                {getFieldError(validationErrors, "order_index") && (
                  <p className="text-sm text-destructive mt-1">
                    {getFieldError(validationErrors, "order_index")}
                  </p>
                )}
              </div>
            </div>

            <div>
              <Label htmlFor="title">Title (Optional)</Label>
              <Input
                id="title"
                value={formData.title}
                onChange={(e) => updateFormField("title", e.target.value)}
                placeholder="Block title"
                className={
                  hasFieldError(validationErrors, "title")
                    ? "border-destructive"
                    : ""
                }
              />
              {getFieldError(validationErrors, "title") && (
                <p className="text-sm text-destructive mt-1">
                  {getFieldError(validationErrors, "title")}
                </p>
              )}
            </div>

            <div>
              <Label htmlFor="content">Content</Label>
              <Textarea
                id="content"
                value={formData.content}
                onChange={(e) => updateFormField("content", e.target.value)}
                placeholder="Block content"
                rows={4}
                className={
                  hasFieldError(validationErrors, "content")
                    ? "border-destructive"
                    : ""
                }
              />
              {getFieldError(validationErrors, "content") && (
                <p className="text-sm text-destructive mt-1">
                  {getFieldError(validationErrors, "content")}
                </p>
              )}
            </div>

            <div>
              <Label htmlFor="data">Data (JSON)</Label>
              <Textarea
                id="data"
                value={JSON.stringify(formData.data, null, 2)}
                onChange={(e) => {
                  try {
                    const parsed = JSON.parse(e.target.value);
                    updateFormField("data", parsed);
                  } catch {
                    updateFormField("data", e.target.value);
                  }
                }}
                placeholder='{"key": "value"}'
                rows={6}
                className={
                  hasFieldError(validationErrors, "data")
                    ? "border-destructive"
                    : ""
                }
              />
              {getFieldError(validationErrors, "data") && (
                <p className="text-sm text-destructive mt-1">
                  {getFieldError(validationErrors, "data")}
                </p>
              )}
            </div>

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

            <div className="flex gap-2">
              <Button onClick={handleSave} disabled={isSaving}>
                <Save className="w-4 h-4 mr-2" />
                {isSaving ? "Saving..." : editingId ? "Update" : "Create"}
              </Button>
              <Button
                variant="outline"
                onClick={handleCancel}
                disabled={isSaving}
              >
                <X className="w-4 h-4 mr-2" />
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="space-y-4">
        {blocks.map((block) => (
          <Card key={block.id}>
            <CardContent className="pt-6">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <Badge variant="outline">{block.block_type}</Badge>
                    <Badge variant="secondary">#{block.order_index}</Badge>
                    <Badge variant="outline">
                      {(block as any).language || "en"}
                    </Badge>
                    {blockReferences[block.id] &&
                      blockReferences[block.id].length > 0 && (
                        <Badge variant="default">
                          {blockReferences[block.id].length} ref
                          {blockReferences[block.id].length !== 1 ? "s" : ""}
                        </Badge>
                      )}
                  </div>
                  {(block as any).title && (
                    <h3 className="font-semibold text-lg mb-1">
                      {(block as any).title}
                    </h3>
                  )}
                  <p className="text-sm text-muted-foreground mb-2">
                    Story: {block.story_id || "No story ID"}
                  </p>
                  {(block as any).content && (
                    <p className="text-sm line-clamp-3">
                      {(block as any).content}
                    </p>
                  )}
                  {block.data && Object.keys(block.data).length > 0 && (
                    <details className="mt-2">
                      <summary className="text-sm text-muted-foreground cursor-pointer">
                        View data
                      </summary>
                      <pre className="text-xs bg-muted p-2 rounded mt-1 overflow-auto max-h-32">
                        {JSON.stringify(block.data, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
                <div className="flex flex-col gap-2">
                  <div className="flex gap-1">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => moveBlockUp(block.id, block.order_index)}
                      disabled={
                        editingId !== null ||
                        showNewForm ||
                        block.order_index === 0
                      }
                      title="Move up"
                    >
                      <ArrowUp className="w-3 h-3" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => moveBlockDown(block.id, block.order_index)}
                      disabled={
                        editingId !== null ||
                        showNewForm ||
                        block.order_index === blocks.length - 1
                      }
                      title="Move down"
                    >
                      <ArrowDown className="w-3 h-3" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        const input = prompt(
                          `Move to position (0-${blocks.length - 1}):`
                        );
                        if (input !== null) {
                          const targetIndex = parseInt(input);
                          if (!isNaN(targetIndex)) {
                            moveBlockToIndex(block.id, targetIndex);
                          }
                        }
                      }}
                      disabled={editingId !== null || showNewForm}
                      title="Move to specific position"
                    >
                      <List className="w-3 h-3" />
                    </Button>
                  </div>
                  <div className="flex gap-1">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleEdit(block)}
                      disabled={editingId !== null || showNewForm}
                      title="Edit block"
                    >
                      <Edit className="w-3 h-3" />
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => handleDelete(block.id)}
                      disabled={editingId !== null || showNewForm}
                      title="Delete block"
                    >
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {blocks.length === 0 && (
        <Card>
          <CardContent className="pt-6 text-center text-muted-foreground">
            No blocks found. Add one to get started.
          </CardContent>
        </Card>
      )}
    </div>
  );
}
