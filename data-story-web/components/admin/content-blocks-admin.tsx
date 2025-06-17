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
import { Trash2, Plus, Save, X, Edit } from "lucide-react";
import { supabase } from "@/lib/supabase";
import type { ContentBlock } from "@/lib/supabase";
import { useToast } from "@/hooks/use-toast";

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
  const { toast } = useToast();

  const [formData, setFormData] = useState({
    story_id: "",
    block_type: "",
    title: "",
    content: "",
    data: {} as any,
    language: "en" as const,
    order_index: 0,
  });

  useEffect(() => {
    loadBlocks();
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
        title: "Error loading blocks",
        description:
          error instanceof Error ? error.message : "Failed to load blocks",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
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
    });
  };

  const handleSave = async () => {
    try {
      const saveData = {
        ...formData,
        data:
          formData.data && Object.keys(formData.data).length > 0
            ? formData.data
            : null,
      };

      if (editingId) {
        const { error } = await supabase
          .from("content_blocks")
          .update(saveData)
          .eq("id", editingId);

        if (error) throw error;
        toast({ title: "Block updated successfully" });
      } else {
        const { error } = await supabase
          .from("content_blocks")
          .insert([saveData]);

        if (error) throw error;
        toast({ title: "Block created successfully" });
      }

      setEditingId(null);
      setShowNewForm(false);
      resetForm();
      loadBlocks();
    } catch (error) {
      toast({
        title: editingId ? "Error updating block" : "Error creating block",
        description:
          error instanceof Error ? error.message : "Operation failed",
        variant: "destructive",
      });
    }
  };

  const handleEdit = (block: ContentBlock) => {
    setFormData({
      story_id: block.story_id,
      block_type: block.block_type,
      title: block.title || "",
      content: block.content || "",
      data: block.data || {},
      language: block.language as "en" | "de",
      order_index: block.order_index,
    });
    setEditingId(block.id);
    setShowNewForm(false);
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this block?")) return;

    try {
      const { error } = await supabase
        .from("content_blocks")
        .delete()
        .eq("id", id);

      if (error) throw error;
      toast({ title: "Block deleted successfully" });
      loadBlocks();
    } catch (error) {
      toast({
        title: "Error deleting block",
        description:
          error instanceof Error ? error.message : "Failed to delete block",
        variant: "destructive",
      });
    }
  };

  const handleCancel = () => {
    setEditingId(null);
    setShowNewForm(false);
    resetForm();
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
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="story_id">Story ID</Label>
                <Input
                  id="story_id"
                  value={formData.story_id}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      story_id: e.target.value,
                    }))
                  }
                  placeholder="main-story"
                />
              </div>
              <div>
                <Label htmlFor="language">Language</Label>
                <Select
                  value={formData.language}
                  onValueChange={(value) =>
                    setFormData((prev) => ({ ...prev, language: value as any }))
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="en">English</SelectItem>
                    <SelectItem value="de">German</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="block_type">Block Type</Label>
                <Select
                  value={formData.block_type}
                  onValueChange={(value) =>
                    setFormData((prev) => ({ ...prev, block_type: value }))
                  }
                >
                  <SelectTrigger>
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
              </div>
              <div>
                <Label htmlFor="order_index">Order</Label>
                <Input
                  id="order_index"
                  type="number"
                  value={formData.order_index}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      order_index: parseInt(e.target.value),
                    }))
                  }
                />
              </div>
            </div>

            <div>
              <Label htmlFor="title">Title (Optional)</Label>
              <Input
                id="title"
                value={formData.title}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, title: e.target.value }))
                }
                placeholder="Block title"
              />
            </div>

            <div>
              <Label htmlFor="content">Content</Label>
              <Textarea
                id="content"
                value={formData.content}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, content: e.target.value }))
                }
                placeholder="Block content"
                rows={4}
              />
            </div>

            <div>
              <Label htmlFor="data">Data (JSON)</Label>
              <Textarea
                id="data"
                value={JSON.stringify(formData.data, null, 2)}
                onChange={(e) => {
                  try {
                    const parsed = JSON.parse(e.target.value);
                    setFormData((prev) => ({ ...prev, data: parsed }));
                  } catch {
                    // Invalid JSON, keep as string for now
                  }
                }}
                placeholder='{"key": "value"}'
                rows={6}
              />
            </div>

            <div className="flex gap-2">
              <Button onClick={handleSave}>
                <Save className="w-4 h-4 mr-2" />
                {editingId ? "Update" : "Create"}
              </Button>
              <Button variant="outline" onClick={handleCancel}>
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
                    <Badge variant="outline">{block.language}</Badge>
                  </div>
                  {block.title && (
                    <h3 className="font-semibold text-lg mb-1">
                      {block.title}
                    </h3>
                  )}
                  <p className="text-sm text-muted-foreground mb-2">
                    Story: {block.story_id}
                  </p>
                  {block.content && (
                    <p className="text-sm line-clamp-3">{block.content}</p>
                  )}
                  {block.data && Object.keys(block.data).length > 0 && (
                    <details className="mt-2">
                      <summary className="text-sm text-muted-foreground cursor-pointer">
                        View data
                      </summary>
                      <pre className="text-xs bg-muted p-2 rounded mt-1 overflow-auto">
                        {JSON.stringify(block.data, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleEdit(block)}
                    disabled={editingId !== null || showNewForm}
                  >
                    <Edit className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDelete(block.id)}
                    disabled={editingId !== null || showNewForm}
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
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
