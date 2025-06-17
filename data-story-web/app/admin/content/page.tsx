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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Plus,
  Trash2,
  Edit,
  Save,
  X,
  ChevronUp,
  ChevronDown,
  Move,
  BookOpen,
} from "lucide-react";
import {
  DataStoryBlock,
  Reference,
  ContentData,
  Visualization,
} from "@/lib/types";
import { ReferencesDropdown } from "@/components/references-dropdown";
import { ImageDropdown } from "@/components/image-dropdown";

export default function ContentAdminPage() {
  const [content, setContent] = useState<ContentData | null>(null);
  const [activeLanguage, setActiveLanguage] = useState<"en" | "de">("en");
  const [editingBlockIndex, setEditingBlockIndex] = useState<number | null>(
    null
  );
  const [newBlock, setNewBlock] = useState<Partial<DataStoryBlock> | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadContent();
  }, []);

  const loadContent = async () => {
    try {
      const response = await fetch("/api/content");
      const data = await response.json();
      setContent(data);
    } catch (error) {
      console.error("Failed to load content:", error);
    } finally {
      setLoading(false);
    }
  };

  const saveContent = async () => {
    if (!content) return;

    setSaving(true);
    try {
      const response = await fetch("/api/content", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(content),
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.error("Server error details:", errorData);
        throw new Error(
          `HTTP error! status: ${response.status}, details: ${
            errorData.details || errorData.error
          }`
        );
      }

      const result = await response.json();
      console.log("Content saved successfully:", result);
    } catch (error) {
      console.error("Failed to save content:", error);
      alert(
        `Failed to save content: ${
          error instanceof Error ? error.message : "Unknown error"
        }`
      );
    } finally {
      setSaving(false);
    }
  };

  const updateBasicField = (field: string, value: string) => {
    if (!content) return;

    setContent({
      ...content,
      [activeLanguage]: {
        ...content[activeLanguage],
        [field]: value,
      },
    });
  };

  const moveBlock = (index: number, direction: "up" | "down") => {
    if (!content) return;

    const blocks = [...content[activeLanguage].blocks];
    const newIndex = direction === "up" ? index - 1 : index + 1;

    if (newIndex < 0 || newIndex >= blocks.length) return;

    [blocks[index], blocks[newIndex]] = [blocks[newIndex], blocks[index]];

    setContent({
      ...content,
      [activeLanguage]: {
        ...content[activeLanguage],
        blocks,
      },
    });
  };

  const moveBlockToPosition = (fromIndex: number, toIndex: number) => {
    if (!content) return;

    const blocks = [...content[activeLanguage].blocks];
    const [movedBlock] = blocks.splice(fromIndex, 1);
    blocks.splice(toIndex, 0, movedBlock);

    setContent({
      ...content,
      [activeLanguage]: {
        ...content[activeLanguage],
        blocks,
      },
    });
  };

  const addBlock = (type: DataStoryBlock["type"]) => {
    const createNewBlock = (): Partial<DataStoryBlock> => {
      switch (type) {
        case "markdown":
          return {
            type: "markdown",
            content: "# New Section\n\nEnter your markdown content here.",
          };
        case "callout":
          return {
            type: "callout",
            title: "Important Note",
            content: "Enter callout content here.",
            variant: "info",
          };
        case "quote":
          return {
            type: "quote",
            content: "Enter quote text here.",
            author: "Author Name",
            role: "",
          };
        case "statistics":
          return {
            type: "statistics",
            stats: [
              { label: "Metric", value: "100", description: "Description" },
            ],
          };
        case "timeline":
          return {
            type: "timeline",
            events: [
              { year: "2024", title: "Event", description: "Description" },
            ],
          };
        case "visualization":
          return {
            type: "visualization",
            data: {
              title: "New Visualization",
              description: "Description",
              content: "Content",
              type: "map",
              imageCategory: "",
              imageId: "",
              references: [],
            } as Visualization,
          };
        case "animated-quote":
          return {
            type: "animated-quote",
            text: "Enter your quote text here.",
            author: "Author Name",
            role: "Title or Role",
          };
        case "animated-statistics":
          return {
            type: "animated-statistics",
            title: "Key Metrics",
            description: "Important statistics description",
            stats: [
              {
                icon: "thermometer",
                value: "+1.2°C",
                label: "Temperature Rise",
                change: "since 1990",
                trend: "up",
                color: "text-red-500",
              },
            ],
          };
        case "climate-timeline":
          return {
            type: "climate-timeline",
            title: "Climate Timeline",
            description: "Key climate events",
            events: [
              {
                year: 2024,
                title: "Sample Event",
                description: "Event description",
                type: "policy",
                icon: "calendar",
                color: "#3b82f6",
              },
            ],
          };
        case "climate-dashboard":
          return {
            type: "climate-dashboard",
            title: "Climate Dashboard",
            description: "Overview of climate indicators",
            metrics: [
              {
                title: "Global Temperature",
                value: "+1.2°C",
                change: "+0.1°C",
                trend: "up",
                status: "warning",
                progress: 80,
                target: "1.5°C",
                description: "above pre-industrial level",
              },
            ],
          };
        case "temperature-spiral":
          return {
            type: "temperature-spiral",
            title: "Temperature Spiral",
            description: "Visualization of temperature changes over time",
            startYear: 1880,
            endYear: 2030,
            rotations: 8,
          };
        case "interactive-callout":
          return {
            type: "interactive-callout",
            title: "Interactive Note",
            content: "This is an interactive callout with enhanced features.",
            variant: "info",
            interactive: true,
          };
        default:
          return { type: "markdown", content: "" };
      }
    };

    setNewBlock(createNewBlock());
  };

  const saveNewBlock = async () => {
    if (!content || !newBlock) return;

    const blocks = [
      ...content[activeLanguage].blocks,
      newBlock as DataStoryBlock,
    ];
    const updatedContent = {
      ...content,
      [activeLanguage]: {
        ...content[activeLanguage],
        blocks,
      },
    };
    setContent(updatedContent);
    setNewBlock(null);

    // Auto-save after adding block
    setSaving(true);
    try {
      const response = await fetch("/api/content", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updatedContent),
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.error("Server error details:", errorData);
        throw new Error(
          `HTTP error! status: ${response.status}, details: ${
            errorData.details || errorData.error
          }`
        );
      }

      console.log("Block added and saved successfully");
    } catch (error) {
      console.error("Failed to auto-save after adding block:", error);
      alert(
        `Failed to save block: ${
          error instanceof Error ? error.message : "Unknown error"
        }`
      );
    } finally {
      setSaving(false);
    }
  };

  const deleteBlock = (index: number) => {
    if (!content) return;

    const blocks = content[activeLanguage].blocks.filter((_, i) => i !== index);
    setContent({
      ...content,
      [activeLanguage]: {
        ...content[activeLanguage],
        blocks,
      },
    });
  };

  const updateBlock = async (index: number, updatedBlock: DataStoryBlock) => {
    if (!content) return;

    const blocks = [...content[activeLanguage].blocks];
    blocks[index] = updatedBlock;

    const updatedContent = {
      ...content,
      [activeLanguage]: {
        ...content[activeLanguage],
        blocks,
      },
    };
    setContent(updatedContent);
    setEditingBlockIndex(null);

    // Auto-save after updating block
    setSaving(true);
    try {
      const response = await fetch("/api/content", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updatedContent),
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.error("Server error details:", errorData);
        throw new Error(
          `HTTP error! status: ${response.status}, details: ${
            errorData.details || errorData.error
          }`
        );
      }

      console.log("Block updated and saved successfully");
    } catch (error) {
      console.error("Failed to auto-save after updating block:", error);
      alert(
        `Failed to save block update: ${
          error instanceof Error ? error.message : "Unknown error"
        }`
      );
    } finally {
      setSaving(false);
    }
  };

  const updateReference = (
    index: number,
    field: keyof Reference,
    value: any
  ) => {
    if (!content) return;

    const references = [...content.references];
    references[index] = { ...references[index], [field]: value };

    setContent({
      ...content,
      references,
    });
  };

  const addReference = () => {
    if (!content) return;

    const newRef: Reference = {
      id: `ref${content.references.length + 1}`,
      title: "New Reference",
      authors: ["Author"],
      year: new Date().getFullYear(),
      type: "journal",
    };

    setContent({
      ...content,
      references: [...content.references, newRef],
    });
  };

  const deleteReference = (index: number) => {
    if (!content) return;

    const references = content.references.filter((_, i) => i !== index);
    setContent({
      ...content,
      references,
    });
  };

  const renderBlockEditor = (block: DataStoryBlock, isNew = false) => {
    const updateField = (field: string, value: any) => {
      if (isNew && newBlock) {
        setNewBlock({ ...newBlock, [field]: value });
      } else if (!isNew) {
        const updatedBlock = { ...block, [field]: value };
        const index = content![activeLanguage].blocks.findIndex(
          (b, i) => i === editingBlockIndex
        );
        if (index !== -1) {
          updateBlock(index, updatedBlock);
        }
      }
    };

    const blockData = isNew ? newBlock : block;
    if (!blockData) return null;

    switch (blockData.type) {
      case "markdown":
        return (
          <div className="space-y-4">
            <div>
              <Label>Markdown Content</Label>
              <Textarea
                value={blockData.content || ""}
                onChange={(e) => updateField("content", e.target.value)}
                placeholder="Enter markdown content..."
                rows={8}
              />
            </div>
          </div>
        );

      case "callout":
        return (
          <div className="space-y-4">
            <div>
              <Label>Title</Label>
              <Input
                value={blockData.title || ""}
                onChange={(e) => updateField("title", e.target.value)}
              />
            </div>
            <div>
              <Label>Content</Label>
              <Textarea
                value={blockData.content || ""}
                onChange={(e) => updateField("content", e.target.value)}
              />
            </div>
            <div>
              <Label>Variant</Label>
              <Select
                value={blockData.variant || "info"}
                onValueChange={(value) => updateField("variant", value)}
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
            </div>
          </div>
        );

      case "quote":
        return (
          <div className="space-y-4">
            <div>
              <Label>Quote Text</Label>
              <Textarea
                value={blockData.content || ""}
                onChange={(e) => updateField("content", e.target.value)}
              />
            </div>
            <div>
              <Label>Author</Label>
              <Input
                value={blockData.author || ""}
                onChange={(e) => updateField("author", e.target.value)}
              />
            </div>
            <div>
              <Label>Role (Optional)</Label>
              <Input
                value={blockData.role || ""}
                onChange={(e) => updateField("role", e.target.value)}
              />
            </div>
          </div>
        );

      case "statistics":
        return (
          <div className="space-y-4">
            <Label>Statistics</Label>
            {blockData.stats?.map((stat, index) => (
              <div key={index} className="grid grid-cols-3 gap-2">
                <Input
                  placeholder="Label"
                  value={stat.label}
                  onChange={(e) => {
                    const stats = [...(blockData.stats || [])];
                    stats[index] = { ...stats[index], label: e.target.value };
                    updateField("stats", stats);
                  }}
                />
                <Input
                  placeholder="Value"
                  value={stat.value}
                  onChange={(e) => {
                    const stats = [...(blockData.stats || [])];
                    stats[index] = { ...stats[index], value: e.target.value };
                    updateField("stats", stats);
                  }}
                />
                <Input
                  placeholder="Description"
                  value={stat.description || ""}
                  onChange={(e) => {
                    const stats = [...(blockData.stats || [])];
                    stats[index] = {
                      ...stats[index],
                      description: e.target.value,
                    };
                    updateField("stats", stats);
                  }}
                />
              </div>
            ))}
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                const stats = [
                  ...(blockData.stats || []),
                  { label: "", value: "", description: "" },
                ];
                updateField("stats", stats);
              }}
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Statistic
            </Button>
          </div>
        );

      case "timeline":
        return (
          <div className="space-y-4">
            <Label>Timeline Events</Label>
            {blockData.events?.map((event, index) => (
              <div key={index} className="grid grid-cols-3 gap-2">
                <Input
                  placeholder="Year"
                  value={event.year}
                  onChange={(e) => {
                    const events = [...(blockData.events || [])];
                    events[index] = { ...events[index], year: e.target.value };
                    updateField("events", events);
                  }}
                />
                <Input
                  placeholder="Title"
                  value={event.title}
                  onChange={(e) => {
                    const events = [...(blockData.events || [])];
                    events[index] = { ...events[index], title: e.target.value };
                    updateField("events", events);
                  }}
                />
                <Input
                  placeholder="Description"
                  value={event.description}
                  onChange={(e) => {
                    const events = [...(blockData.events || [])];
                    events[index] = {
                      ...events[index],
                      description: e.target.value,
                    };
                    updateField("events", events);
                  }}
                />
              </div>
            ))}
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                const events = [
                  ...(blockData.events || []),
                  { year: "", title: "", description: "" },
                ];
                updateField("events", events);
              }}
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Event
            </Button>
          </div>
        );

      case "visualization":
        if (!blockData.data) return null;
        return (
          <div className="space-y-4">
            <div>
              <Label>Title</Label>
              <Input
                value={blockData.data.title}
                onChange={(e) => {
                  updateField("data", {
                    ...blockData.data,
                    title: e.target.value,
                  });
                }}
              />
            </div>
            <div>
              <Label>Description</Label>
              <Textarea
                value={blockData.data.description}
                onChange={(e) => {
                  updateField("data", {
                    ...blockData.data,
                    description: e.target.value,
                  });
                }}
              />
            </div>
            <div>
              <Label>Content</Label>
              <Textarea
                value={blockData.data.content}
                onChange={(e) => {
                  updateField("data", {
                    ...blockData.data,
                    content: e.target.value,
                  });
                }}
              />
            </div>
            <div>
              <Label>Type</Label>
              <Select
                value={blockData.data.type}
                onValueChange={(value) => {
                  updateField("data", { ...blockData.data, type: value });
                }}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="map">Map</SelectItem>
                  <SelectItem value="chart">Chart</SelectItem>
                  <SelectItem value="trend">Trend</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Image</Label>
              <ImageDropdown
                selectedImageId={blockData.data.imageId}
                onImageChange={(imageId, imageData) => {
                  updateField("data", {
                    ...blockData.data,
                    imageId: imageId,
                    imageCategory: imageData?.category || "",
                    imageScenario: imageData?.scenario,
                  });
                }}
              />
            </div>
            <div>
              <Label>References</Label>
              <ReferencesDropdown
                selectedReferences={blockData.data.references}
                onReferencesChange={(selectedIds) => {
                  updateField("data", {
                    ...blockData.data,
                    references: selectedIds,
                  });
                }}
              />
            </div>
          </div>
        );

      case "animated-quote":
        return (
          <div className="space-y-4">
            <div>
              <Label>Quote Text</Label>
              <Textarea
                value={blockData.text || ""}
                onChange={(e) => updateField("text", e.target.value)}
                placeholder="Enter quote text..."
                rows={4}
              />
            </div>
            <div>
              <Label>Author</Label>
              <Input
                value={blockData.author || ""}
                onChange={(e) => updateField("author", e.target.value)}
              />
            </div>
            <div>
              <Label>Role/Title</Label>
              <Input
                value={blockData.role || ""}
                onChange={(e) => updateField("role", e.target.value)}
              />
            </div>
          </div>
        );

      case "animated-statistics":
        return (
          <div className="space-y-4">
            <div>
              <Label>Title</Label>
              <Input
                value={blockData.title || ""}
                onChange={(e) => updateField("title", e.target.value)}
              />
            </div>
            <div>
              <Label>Description</Label>
              <Textarea
                value={blockData.description || ""}
                onChange={(e) => updateField("description", e.target.value)}
              />
            </div>
            <div>
              <Label>Statistics (JSON format)</Label>
              <Textarea
                value={JSON.stringify(blockData.stats || [], null, 2)}
                onChange={(e) => {
                  try {
                    const stats = JSON.parse(e.target.value);
                    updateField("stats", stats);
                  } catch {}
                }}
                rows={8}
                placeholder="[{icon: 'thermometer', value: '+1.2°C', label: 'Temperature', color: 'text-red-500'}]"
              />
            </div>
          </div>
        );

      case "climate-timeline":
        return (
          <div className="space-y-4">
            <div>
              <Label>Title</Label>
              <Input
                value={blockData.title || ""}
                onChange={(e) => updateField("title", e.target.value)}
              />
            </div>
            <div>
              <Label>Description</Label>
              <Textarea
                value={blockData.description || ""}
                onChange={(e) => updateField("description", e.target.value)}
              />
            </div>
            <div>
              <Label>Events (JSON format)</Label>
              <Textarea
                value={JSON.stringify(blockData.events || [], null, 2)}
                onChange={(e) => {
                  try {
                    const events = JSON.parse(e.target.value);
                    updateField("events", events);
                  } catch {}
                }}
                rows={8}
                placeholder="[{year: 2024, title: 'Event', description: 'Description', type: 'policy', icon: 'calendar', color: '#3b82f6'}]"
              />
            </div>
          </div>
        );

      case "climate-dashboard":
        return (
          <div className="space-y-4">
            <div>
              <Label>Title</Label>
              <Input
                value={blockData.title || ""}
                onChange={(e) => updateField("title", e.target.value)}
              />
            </div>
            <div>
              <Label>Description</Label>
              <Textarea
                value={blockData.description || ""}
                onChange={(e) => updateField("description", e.target.value)}
              />
            </div>
            <div>
              <Label>Metrics (JSON format)</Label>
              <Textarea
                value={JSON.stringify(blockData.metrics || [], null, 2)}
                onChange={(e) => {
                  try {
                    const metrics = JSON.parse(e.target.value);
                    updateField("metrics", metrics);
                  } catch {}
                }}
                rows={8}
                placeholder="[{title: 'Global Temperature', value: '+1.2°C', change: '+0.1°C', trend: 'up', status: 'warning', progress: 80, target: '1.5°C', description: 'above pre-industrial level'}]"
              />
            </div>
          </div>
        );

      case "temperature-spiral":
        return (
          <div className="space-y-4">
            <div>
              <Label>Title</Label>
              <Input
                value={blockData.title || ""}
                onChange={(e) => updateField("title", e.target.value)}
              />
            </div>
            <div>
              <Label>Description</Label>
              <Textarea
                value={blockData.description || ""}
                onChange={(e) => updateField("description", e.target.value)}
              />
            </div>
            <div>
              <Label>Start Year</Label>
              <Input
                type="number"
                value={blockData.startYear || 1880}
                onChange={(e) =>
                  updateField("startYear", parseInt(e.target.value))
                }
              />
            </div>
            <div>
              <Label>End Year</Label>
              <Input
                type="number"
                value={blockData.endYear || 2030}
                onChange={(e) =>
                  updateField("endYear", parseInt(e.target.value))
                }
              />
            </div>
            <div>
              <Label>Rotations</Label>
              <Input
                type="number"
                value={blockData.rotations || 8}
                onChange={(e) =>
                  updateField("rotations", parseInt(e.target.value))
                }
              />
            </div>
          </div>
        );

      case "interactive-callout":
        return (
          <div className="space-y-4">
            <div>
              <Label>Title</Label>
              <Input
                value={blockData.title || ""}
                onChange={(e) => updateField("title", e.target.value)}
              />
            </div>
            <div>
              <Label>Content</Label>
              <Textarea
                value={blockData.content || ""}
                onChange={(e) => updateField("content", e.target.value)}
                rows={4}
              />
            </div>
            <div>
              <Label>Variant</Label>
              <Select
                value={blockData.variant || "info"}
                onValueChange={(value) => updateField("variant", value)}
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
            </div>
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={blockData.interactive !== false}
                onChange={(e) => updateField("interactive", e.target.checked)}
              />
              <Label>Interactive</Label>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#2d5a3d]"></div>
      </div>
    );
  }

  if (!content) return null;

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold text-[#2d5a3d]">
          Content Management
        </h1>
        <Button onClick={saveContent} disabled={saving}>
          {saving ? "Saving..." : "Save All Changes"}
        </Button>
      </div>

      <Tabs defaultValue="basic">
        <TabsList className="mb-6">
          <TabsTrigger value="basic">Basic Content</TabsTrigger>
          <TabsTrigger value="blocks">Data Story</TabsTrigger>
          <TabsTrigger value="references">References</TabsTrigger>
        </TabsList>

        <TabsContent value="basic">
          <Tabs
            value={activeLanguage}
            onValueChange={(value) => setActiveLanguage(value as "en" | "de")}
          >
            <TabsList className="mb-4">
              <TabsTrigger value="en">English</TabsTrigger>
              <TabsTrigger value="de">German</TabsTrigger>
            </TabsList>

            <TabsContent value={activeLanguage}>
              <Card>
                <CardHeader>
                  <CardTitle>Basic Content</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label>Hero Title</Label>
                    <Input
                      value={content[activeLanguage].heroTitle}
                      onChange={(e) =>
                        updateBasicField("heroTitle", e.target.value)
                      }
                    />
                  </div>
                  <div>
                    <Label>Hero Description</Label>
                    <Textarea
                      value={content[activeLanguage].heroDescription}
                      onChange={(e) =>
                        updateBasicField("heroDescription", e.target.value)
                      }
                      rows={3}
                    />
                  </div>
                  <div>
                    <Label>Data Story Title</Label>
                    <Input
                      value={content[activeLanguage].dataStoryTitle}
                      onChange={(e) =>
                        updateBasicField("dataStoryTitle", e.target.value)
                      }
                    />
                  </div>
                  <div>
                    <Label>Intro Text 1</Label>
                    <Textarea
                      value={content[activeLanguage].introText1}
                      onChange={(e) =>
                        updateBasicField("introText1", e.target.value)
                      }
                      rows={3}
                    />
                  </div>
                  <div>
                    <Label>Intro Text 2</Label>
                    <Textarea
                      value={content[activeLanguage].introText2}
                      onChange={(e) =>
                        updateBasicField("introText2", e.target.value)
                      }
                      rows={3}
                    />
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </TabsContent>

        <TabsContent value="blocks">
          <Tabs
            value={activeLanguage}
            onValueChange={(value) => setActiveLanguage(value as "en" | "de")}
          >
            <TabsList className="mb-4">
              <TabsTrigger value="en">English</TabsTrigger>
              <TabsTrigger value="de">German</TabsTrigger>
            </TabsList>

            <TabsContent value={activeLanguage}>
              <div className="space-y-6">
                {content[activeLanguage].blocks.map((block, index) => (
                  <Card key={index}>
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <Badge variant="outline">{block.type}</Badge>
                          <span className="text-sm text-muted-foreground">
                            Block {index + 1}
                          </span>
                        </div>
                        <div className="flex items-center space-x-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => moveBlock(index, "up")}
                            disabled={index === 0}
                          >
                            <ChevronUp className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => moveBlock(index, "down")}
                            disabled={
                              index ===
                              content[activeLanguage].blocks.length - 1
                            }
                          >
                            <ChevronDown className="h-4 w-4" />
                          </Button>
                          <Select
                            value={index.toString()}
                            onValueChange={(value) =>
                              moveBlockToPosition(index, parseInt(value))
                            }
                          >
                            <SelectTrigger className="w-20">
                              <Move className="h-4 w-4" />
                            </SelectTrigger>
                            <SelectContent>
                              {content[activeLanguage].blocks.map((_, i) => (
                                <SelectItem key={i} value={i.toString()}>
                                  {i + 1}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setEditingBlockIndex(index)}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <AlertDialog>
                            <AlertDialogTrigger asChild>
                              <Button variant="outline" size="sm">
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                              <AlertDialogHeader>
                                <AlertDialogTitle>
                                  Delete Block
                                </AlertDialogTitle>
                                <AlertDialogDescription>
                                  Are you sure you want to delete this block?
                                  This action cannot be undone.
                                </AlertDialogDescription>
                              </AlertDialogHeader>
                              <AlertDialogFooter>
                                <AlertDialogCancel>Cancel</AlertDialogCancel>
                                <AlertDialogAction
                                  onClick={() => deleteBlock(index)}
                                >
                                  Delete
                                </AlertDialogAction>
                              </AlertDialogFooter>
                            </AlertDialogContent>
                          </AlertDialog>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent>
                      {editingBlockIndex === index ? (
                        <div className="space-y-4">
                          {renderBlockEditor(block)}
                          <div className="flex space-x-2">
                            <Button onClick={() => setEditingBlockIndex(null)}>
                              <Save className="h-4 w-4 mr-2" />
                              Save
                            </Button>
                            <Button
                              variant="outline"
                              onClick={() => setEditingBlockIndex(null)}
                            >
                              <X className="h-4 w-4 mr-2" />
                              Cancel
                            </Button>
                          </div>
                        </div>
                      ) : (
                        <div className="p-4 bg-muted rounded-md">
                          <p className="text-sm text-muted-foreground">
                            {block.type === "markdown" &&
                              block.content?.slice(0, 100) + "..."}
                            {block.type === "callout" && block.title}
                            {block.type === "quote" &&
                              `"${block.content?.slice(0, 50)}..."`}
                            {block.type === "statistics" &&
                              `${block.stats?.length} statistics`}
                            {block.type === "timeline" &&
                              `${block.events?.length} events`}
                            {block.type === "visualization" &&
                              block.data?.title}
                          </p>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}

                {newBlock && (
                  <Card>
                    <CardHeader>
                      <CardTitle>New {newBlock.type} Block</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        {renderBlockEditor(newBlock as DataStoryBlock, true)}
                        <div className="flex space-x-2">
                          <Button onClick={saveNewBlock}>
                            <Save className="h-4 w-4 mr-2" />
                            Add Block
                          </Button>
                          <Button
                            variant="outline"
                            onClick={() => setNewBlock(null)}
                          >
                            <X className="h-4 w-4 mr-2" />
                            Cancel
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )}

                <Card>
                  <CardContent className="pt-6">
                    <div className="flex flex-wrap gap-2">
                      <Button
                        onClick={() => addBlock("markdown")}
                        variant="outline"
                      >
                        <Plus className="h-4 w-4 mr-2" />
                        Markdown
                      </Button>
                      <Button
                        onClick={() => addBlock("callout")}
                        variant="outline"
                      >
                        <Plus className="h-4 w-4 mr-2" />
                        Callout
                      </Button>
                      <Button
                        onClick={() => addBlock("quote")}
                        variant="outline"
                      >
                        <Plus className="h-4 w-4 mr-2" />
                        Quote
                      </Button>
                      <Button
                        onClick={() => addBlock("statistics")}
                        variant="outline"
                      >
                        <Plus className="h-4 w-4 mr-2" />
                        Statistics
                      </Button>
                      <Button
                        onClick={() => addBlock("timeline")}
                        variant="outline"
                      >
                        <Plus className="h-4 w-4 mr-2" />
                        Timeline
                      </Button>
                      <Button
                        onClick={() => addBlock("visualization")}
                        variant="outline"
                      >
                        <Plus className="h-4 w-4 mr-2" />
                        Visualization
                      </Button>
                      <Button
                        onClick={() => addBlock("animated-quote")}
                        variant="outline"
                      >
                        <Plus className="h-4 w-4 mr-2" />
                        Animated Quote
                      </Button>
                      <Button
                        onClick={() => addBlock("animated-statistics")}
                        variant="outline"
                      >
                        <Plus className="h-4 w-4 mr-2" />
                        Animated Statistics
                      </Button>
                      <Button
                        onClick={() => addBlock("climate-timeline")}
                        variant="outline"
                      >
                        <Plus className="h-4 w-4 mr-2" />
                        Climate Timeline
                      </Button>
                      <Button
                        onClick={() => addBlock("climate-dashboard")}
                        variant="outline"
                      >
                        <Plus className="h-4 w-4 mr-2" />
                        Climate Dashboard
                      </Button>
                      <Button
                        onClick={() => addBlock("temperature-spiral")}
                        variant="outline"
                      >
                        <Plus className="h-4 w-4 mr-2" />
                        Temperature Spiral
                      </Button>
                      <Button
                        onClick={() => addBlock("interactive-callout")}
                        variant="outline"
                      >
                        <Plus className="h-4 w-4 mr-2" />
                        Interactive Callout
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
          </Tabs>
        </TabsContent>

        <TabsContent value="references">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <BookOpen className="h-5 w-5" />
                  <CardTitle>References Management</CardTitle>
                </div>
                <Button onClick={addReference}>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Reference
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {content.references.map((ref, index) => (
                <Card key={ref.id}>
                  <CardHeader>
                    <div className="flex justify-between items-center">
                      <CardTitle className="flex items-center gap-2">
                        Reference [{ref.id}]
                      </CardTitle>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => deleteReference(index)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label>ID</Label>
                        <Input
                          value={ref.id}
                          onChange={(e) =>
                            updateReference(index, "id", e.target.value)
                          }
                        />
                      </div>
                      <div>
                        <Label>Type</Label>
                        <Select
                          value={ref.type}
                          onValueChange={(value: Reference["type"]) =>
                            updateReference(index, "type", value)
                          }
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="journal">Journal</SelectItem>
                            <SelectItem value="report">Report</SelectItem>
                            <SelectItem value="dataset">Dataset</SelectItem>
                            <SelectItem value="book">Book</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    <div>
                      <Label>Title</Label>
                      <Input
                        value={ref.title}
                        onChange={(e) =>
                          updateReference(index, "title", e.target.value)
                        }
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label>Authors (comma-separated)</Label>
                        <Input
                          value={
                            Array.isArray(ref.authors)
                              ? ref.authors.join(", ")
                              : ref.authors
                          }
                          onChange={(e) =>
                            updateReference(
                              index,
                              "authors",
                              e.target.value.split(", ")
                            )
                          }
                        />
                      </div>
                      <div>
                        <Label>Year</Label>
                        <Input
                          type="number"
                          value={ref.year}
                          onChange={(e) =>
                            updateReference(
                              index,
                              "year",
                              parseInt(e.target.value)
                            )
                          }
                        />
                      </div>
                    </div>

                    <div>
                      <Label>Journal (Optional)</Label>
                      <Input
                        value={ref.journal || ""}
                        onChange={(e) =>
                          updateReference(index, "journal", e.target.value)
                        }
                      />
                    </div>

                    <div>
                      <Label>URL (Optional)</Label>
                      <Input
                        value={ref.url || ""}
                        onChange={(e) =>
                          updateReference(index, "url", e.target.value)
                        }
                      />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
