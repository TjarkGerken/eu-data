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
} from "@/lib/types";
import { MultiSelectReferences } from "@/components/ui/multi-select-references";
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
  const [storyId, setStoryId] = useState<string>("");

  useEffect(() => {
    loadStoryAndContent();
  }, []);

  const loadStoryAndContent = async () => {
    setLoading(true);
    try {
      // Fetch the single story ID from Supabase
      const response = await fetch("/api/stories");
      const stories = await response.json();

      if (stories.length === 0) {
        console.error("No stories found");
        setContent(null);
        return;
      }

      const currentStoryId = stories[0].id;
      setStoryId(currentStoryId);

      // Load content for this story
      const contentResponse = await fetch(
        `/api/content?storyId=${currentStoryId}`
      );
      const data = await contentResponse.json();
      setContent(data);
    } catch (error) {
      console.error("Failed to load story and content:", error);
      setContent(null);
    } finally {
      setLoading(false);
    }
  };

  const saveContent = async () => {
    if (!content || !storyId) return;

    setSaving(true);
    try {
      // Automatically synchronize both languages before saving
      const synchronizedContent = { ...content };

      // Ensure both languages have the same block structure
      const enBlocks = [...synchronizedContent.en.blocks];
      const deBlocks = [...synchronizedContent.de.blocks];

      // Use the language with more blocks as the reference, or English as fallback
      const referenceBlocks =
        enBlocks.length >= deBlocks.length ? enBlocks : deBlocks;
      const referenceLanguage =
        enBlocks.length >= deBlocks.length ? "en" : "de";
      const targetLanguage = referenceLanguage === "en" ? "de" : "en";
      const targetBlocks = referenceLanguage === "en" ? deBlocks : enBlocks;

      // Synchronize target language with reference language structure
      ensureBlocksSynchronized(targetBlocks, referenceBlocks);

      // Update the synchronized content
      synchronizedContent[targetLanguage].blocks = targetBlocks;

      const response = await fetch("/api/content", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          storyId: storyId,
          content: synchronizedContent,
        }),
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
      console.log("Content saved successfully with automatic sync:", result);

      // Update local state with synchronized content
      setContent(synchronizedContent);
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

  const moveBlock = async (index: number, direction: "up" | "down") => {
    if (!content) return;

    const blocks = [...content[activeLanguage].blocks];
    const newIndex = direction === "up" ? index - 1 : index + 1;

    if (newIndex < 0 || newIndex >= blocks.length) return;

    [blocks[index], blocks[newIndex]] = [blocks[newIndex], blocks[index]];

    // Apply the same ordering to both languages
    const otherLanguage = activeLanguage === "en" ? "de" : "en";
    const otherBlocks = [...content[otherLanguage].blocks];

    // Ensure both languages have the same number of blocks
    ensureBlocksSynchronized(otherBlocks, blocks);

    [otherBlocks[index], otherBlocks[newIndex]] = [
      otherBlocks[newIndex],
      otherBlocks[index],
    ];

    const updatedContent = {
      ...content,
      [activeLanguage]: {
        ...content[activeLanguage],
        blocks,
      },
      [otherLanguage]: {
        ...content[otherLanguage],
        blocks: otherBlocks,
      },
    };

    setContent(updatedContent);

    // Auto-save after moving block to persist synchronization
    try {
      const response = await fetch("/api/content", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          storyId: storyId,
          content: updatedContent,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      console.log("Block moved and synchronized successfully");
    } catch (error) {
      console.error("Failed to save after moving block:", error);
    }
  };

  const moveBlockToPosition = async (fromIndex: number, toIndex: number) => {
    if (!content) return;

    const blocks = [...content[activeLanguage].blocks];
    const [movedBlock] = blocks.splice(fromIndex, 1);
    blocks.splice(toIndex, 0, movedBlock);

    // Apply the same ordering to both languages
    const otherLanguage = activeLanguage === "en" ? "de" : "en";
    const otherBlocks = [...content[otherLanguage].blocks];

    // Ensure both languages have the same number of blocks
    ensureBlocksSynchronized(otherBlocks, blocks);

    const [movedOtherBlock] = otherBlocks.splice(fromIndex, 1);
    otherBlocks.splice(toIndex, 0, movedOtherBlock);

    const updatedContent = {
      ...content,
      [activeLanguage]: {
        ...content[activeLanguage],
        blocks,
      },
      [otherLanguage]: {
        ...content[otherLanguage],
        blocks: otherBlocks,
      },
    };

    setContent(updatedContent);

    // Auto-save after moving block to persist synchronization
    try {
      const response = await fetch("/api/content", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          storyId: storyId,
          content: updatedContent,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      console.log("Block moved and synchronized successfully");
    } catch (error) {
      console.error("Failed to save after moving block:", error);
    }
  };

  const ensureBlocksSynchronized = (
    targetBlocks: DataStoryBlock[],
    sourceBlocks: DataStoryBlock[]
  ) => {
    // If target has fewer blocks, add placeholder blocks of the same type
    while (targetBlocks.length < sourceBlocks.length) {
      const sourceBlock = sourceBlocks[targetBlocks.length];
      const placeholderBlock = createPlaceholderBlock(
        sourceBlock.type,
        activeLanguage === "en" ? "de" : "en"
      );
      targetBlocks.push(placeholderBlock);
    }

    // If target has more blocks, remove excess blocks
    while (targetBlocks.length > sourceBlocks.length) {
      targetBlocks.pop();
    }

    // Ensure block types match
    for (let i = 0; i < sourceBlocks.length; i++) {
      if (targetBlocks[i].type !== sourceBlocks[i].type) {
        targetBlocks[i] = createPlaceholderBlock(
          sourceBlocks[i].type,
          activeLanguage === "en" ? "de" : "en"
        );
      }
    }
  };

  const createPlaceholderBlock = (
    type: DataStoryBlock["type"],
    language: "en" | "de"
  ): DataStoryBlock => {
    const isGerman = language === "de";

    switch (type) {
      case "markdown":
        return {
          type: "markdown",
          content: isGerman
            ? "# Neuer Abschnitt\n\nGeben Sie hier Ihren Markdown-Inhalt ein."
            : "# New Section\n\nEnter your markdown content here.",
        };
      case "callout":
        return {
          type: "callout",
          title: isGerman ? "Wichtiger Hinweis" : "Important Note",
          content: isGerman
            ? "Geben Sie hier den Callout-Inhalt ein."
            : "Enter callout content here.",
          variant: "info",
        };
      case "quote":
        return {
          type: "quote",
          title: isGerman ? "Zitat" : "Quote",
          content: isGerman
            ? "Geben Sie hier den Zitattext ein."
            : "Enter quote text here.",
          author: isGerman ? "Autor Name" : "Author Name",
          role: "",
        };
      case "statistics":
        return {
          type: "statistics",
          title: isGerman ? "Statistiken" : "Statistics",
          description: isGerman ? "Wichtige Kennzahlen" : "Key Metrics",
          stats: [
            {
              label: isGerman ? "Metrik" : "Metric",
              value: "100",
              description: isGerman ? "Beschreibung" : "Description",
            },
          ],
        };
      case "timeline":
        return {
          type: "timeline",
          title: isGerman ? "Zeitleiste" : "Timeline",
          description: isGerman ? "Wichtige Ereignisse" : "Important Events",
          events: [
            {
              year: "2024",
              title: isGerman ? "Ereignis" : "Event",
              description: isGerman ? "Beschreibung" : "Description",
            },
          ],
        };
      case "visualization":
        return {
          type: "visualization",
          title: isGerman ? "Neue Visualisierung" : "New Visualization",
          description: isGerman ? "Beschreibung" : "Description",
          content: isGerman ? "Inhalt" : "Content",
          visualizationType: "map" as const,
          imageCategory: "",
          imageScenario: "",
          imageId: "",
          references: [],
          data: {
            title: isGerman ? "Neue Visualisierung" : "New Visualization",
            description: isGerman ? "Beschreibung" : "Description",
            content: isGerman ? "Inhalt" : "Content",
            type: "map",
            imageCategory: "",
            imageId: "",
            references: [],
          } as Record<string, unknown>,
        };
      case "interactive-map":
        return {
          type: "interactive-map",
          title: isGerman ? "Interaktive Karte" : "Interactive Map",
          description: isGerman
            ? "Interaktive Klimarisiko-Karte"
            : "Interactive climate risk map",
          selectedLayers: [],
        };
      case "animated-quote":
        return {
          type: "animated-quote",
          text: isGerman
            ? "Geben Sie hier Ihren Zitattext ein."
            : "Enter your quote text here.",
          author: isGerman ? "Autor Name" : "Author Name",
          role: isGerman ? "Titel oder Rolle" : "Title or Role",
        };
      case "animated-statistics":
        return {
          type: "animated-statistics",
          title: isGerman ? "Schlüsselkennzahlen" : "Key Metrics",
          description: isGerman
            ? "Beschreibung wichtiger Statistiken"
            : "Important statistics description",
          stats: [
            {
              icon: "thermometer",
              value: "+1.2°C",
              label: isGerman ? "Temperaturanstieg" : "Temperature Rise",
              change: isGerman ? "seit 1990" : "since 1990",
              trend: "up",
              color: "text-red-500",
            },
          ],
        };
      case "climate-timeline":
        return {
          type: "climate-timeline",
          title: isGerman ? "Klima-Zeitachse" : "Climate Timeline",
          description: isGerman
            ? "Wichtige Klimaereignisse"
            : "Key climate events",
          events: [
            {
              year: 2024,
              title: isGerman ? "Beispielereignis" : "Sample Event",
              description: isGerman
                ? "Ereignisbeschreibung"
                : "Event description",
              type: "policy",
              icon: "calendar",
              color: "#3b82f6",
            },
          ],
        };
      case "climate-dashboard":
        return {
          type: "climate-dashboard",
          title: isGerman ? "Klima-Dashboard" : "Climate Dashboard",
          description: isGerman
            ? "Überblick über Klimaindikatoren"
            : "Overview of climate indicators",
          metrics: [
            {
              title: isGerman ? "Globale Temperatur" : "Global Temperature",
              value: "+1.2°C",
              change: "+0.1°C",
              trend: "up",
              status: "warning",
              progress: 80,
              target: "1.5°C",
              description: isGerman
                ? "über vorindustriellem Niveau"
                : "above pre-industrial level",
            },
          ],
        };
      case "temperature-spiral":
        return {
          type: "temperature-spiral",
          title: isGerman ? "Temperaturspirale" : "Temperature Spiral",
          description: isGerman
            ? "Visualisierung von Temperaturveränderungen über die Zeit"
            : "Visualization of temperature changes over time",
          startYear: 1880,
          endYear: 2030,
          rotations: 8,
        };
      case "interactive-callout":
        return {
          type: "interactive-callout",
          title: isGerman ? "Interaktiver Hinweis" : "Interactive Note",
          content: isGerman
            ? "Dies ist ein interaktiver Callout mit erweiterten Funktionen."
            : "This is an interactive callout with enhanced features.",
          variant: "info",
          interactive: true,
        };
      case "neural-climate-network":
        return {
          type: "neural-climate-network",
          title: isGerman
            ? "Neurales Klima-Netzwerk"
            : "Neural Climate Network",
          description: isGerman
            ? "Interaktive neurale Netzwerk-Visualisierung"
            : "Interactive neural network visualization",
          intensity: 1.0,
          speed: 1.0,
        };
      case "earth-pulse":
        return {
          type: "earth-pulse",
          title: isGerman ? "Erdpuls" : "Earth Pulse",
          description: isGerman
            ? "Erdschlag-Visualisierung"
            : "Earth heartbeat visualization",
          intensity: 1.0,
          speed: 1.0,
        };
      case "impact-comparison":
        return {
          type: "impact-comparison",
          title: isGerman
            ? "Klimaauswirkungen-Vergleich"
            : "Climate Impact Comparison",
          description: isGerman
            ? "Verschiedene Klimaszenarien vergleichen"
            : "Compare different climate scenarios",
          scenarios: [
            {
              name: isGerman ? "Aktuell" : "Current",
              temperature: 1.2,
              seaLevel: 0.1,
              precipitation: 5,
              extremeEvents: 10,
            },
          ],
        };
      case "kpi-showcase":
        return {
          type: "kpi-showcase",
          title: isGerman
            ? "Schlüsselleistungsindikatoren"
            : "Key Performance Indicators",
          description: isGerman
            ? "Wichtige Klimakennzahlen"
            : "Important climate metrics",
          kpis: [
            {
              label: isGerman ? "Temperatur" : "Temperature",
              value: "+1.2°C",
              change: "+0.1°C",
              trend: "up",
              icon: "thermometer",
            },
          ],
        };

      case "climate-metamorphosis":
        return {
          type: "climate-metamorphosis",
          title: isGerman ? "Klima-Metamorphose" : "Climate Metamorphosis",
          description: isGerman
            ? "Evolution des Klimas über die Zeit"
            : "Evolution of climate over time",
          stages: [
            {
              year: 2020,
              title: isGerman ? "Aktueller Zustand" : "Current State",
              description: isGerman
                ? "Aktuelle Klimabedingungen"
                : "Current climate conditions",
              data: 100,
            },
          ],
        };
      case "climate-timeline-minimal":
        return {
          type: "climate-timeline-minimal",
          title: isGerman ? "Klima-Zeitachse" : "Climate Timeline",
          description: isGerman
            ? "Minimale Zeitachsenansicht"
            : "Minimal timeline view",
          events: [
            {
              year: 2024,
              title: isGerman ? "Ereignis" : "Event",
              description: isGerman ? "Beschreibung" : "Description",
            },
          ],
        };
      case "data-storm":
        return {
          type: "data-storm",
          title: isGerman ? "Datensturm" : "Data Storm",
          description: isGerman
            ? "Dynamische Datenvisualisierung"
            : "Dynamic data visualization",
          intensity: 1,
          particles: 100,
        };
      case "carbon-molecule-dance":
        return {
          type: "carbon-molecule-dance",
          title: isGerman ? "Kohlenstoffmolekül-Tanz" : "Carbon Molecule Dance",
          description: isGerman
            ? "Kohlenstoffmolekül-Animation"
            : "Carbon molecule animation",
          molecules: 50,
          speed: 1,
        };
      case "climate-infographic":
        return {
          type: "climate-infographic",
          title: isGerman ? "Klima-Infografik" : "Climate Infographic",
          description: isGerman
            ? "Visuelle Klimainformationen"
            : "Visual climate information",
          sections: [
            {
              title: isGerman ? "Temperatur" : "Temperature",
              value: "+1.2°C",
              description: isGerman
                ? "Globaler Durchschnittsanstieg"
                : "Global average increase",
              icon: "thermometer",
            },
          ],
        };
      case "interactive-map":
        return {
          type: "interactive-map",
          title: isGerman ? "Interaktive Karte" : "Interactive Map",
          description: isGerman
            ? "Interaktive Klimarisiko-Karte"
            : "Interactive climate risk map",
          selectedLayers: [],
        };
      default:
        return {
          type: "markdown",
          content: isGerman
            ? "# Neuer Abschnitt\n\nGeben Sie hier Ihren Markdown-Inhalt ein."
            : "# New Section\n\nEnter your markdown content here.",
        };
    }
  };

  const addBlock = (type: DataStoryBlock["type"]) => {
    const newBlock = createPlaceholderBlock(type, activeLanguage);
    setNewBlock(newBlock);
  };

  const saveNewBlock = async () => {
    if (!newBlock || !content) return;

    // Use placeholder creator for the new block for both languages
    const enBlock = createPlaceholderBlock(newBlock.type!, "en");
    const deBlock = createPlaceholderBlock(newBlock.type!, "de");

    // Copy over initial data from the form if it exists
    Object.assign(enBlock, newBlock);
    Object.assign(deBlock, newBlock); // Basic sync, can be refined

    try {
      const response = await fetch("/api/content", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          storyId: storyId,
          enBlock,
          deBlock,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.error("Failed to add block:", errorData);
        throw new Error(
          `Failed to add block. Status: ${response.status}. ${
            errorData.error || ""
          }`
        );
      }

      const createdBlocks = await response.json();

      setContent((prevContent) => {
        if (!prevContent) return null;
        return {
          ...prevContent,
          en: {
            ...prevContent.en,
            blocks: [...prevContent.en.blocks, createdBlocks.en],
          },
          de: {
            ...prevContent.de,
            blocks: [...prevContent.de.blocks, createdBlocks.de],
          },
        };
      });

      setNewBlock(null);
    } catch (error) {
      console.error("Failed to add block:", error);
      alert(
        `Failed to add block: ${
          error instanceof Error ? error.message : "Unknown error"
        }`
      );
    }
  };

  const deleteBlock = (index: number) => {
    if (!content) return;

    const blocks = content[activeLanguage].blocks.filter((_, i) => i !== index);

    // Also delete the corresponding block from the other language
    const otherLanguage = activeLanguage === "en" ? "de" : "en";
    const otherBlocks = content[otherLanguage].blocks.filter(
      (_, i) => i !== index
    );

    setContent({
      ...content,
      [activeLanguage]: {
        ...content[activeLanguage],
        blocks,
      },
      [otherLanguage]: {
        ...content[otherLanguage],
        blocks: otherBlocks,
      },
    });
  };

  const updateBlock = (index: number, updatedBlock: DataStoryBlock) => {
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
  };

  const saveBlockAndClose = async () => {
    if (!content) return;

    setEditingBlockIndex(null);

    // Auto-save after closing block editor
    setSaving(true);
    try {
      const response = await fetch("/api/content", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ storyId: storyId, content }),
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

      console.log("Block saved successfully");
    } catch (error) {
      console.error("Failed to save block:", error);
      alert(
        `Failed to save block: ${
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
    value: string | string[] | number
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
    const updateField = (field: string, value: string | number | boolean | object) => {
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
            {blockData.stats?.map((stat: { label: string; value: string; description?: string }, index: number) => (
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
            {blockData.events?.map((event: { year: string; title: string; description: string }, index: number) => (
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
                value={blockData.data.title as string}
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
                value={blockData.data.description as string}
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
                value={blockData.data.content as string}
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
                value={blockData.data.type as string}
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
                selectedImageId={blockData.data.imageId as string}
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
              <MultiSelectReferences
                selectedReferenceIds={(blockData.data.references as string[]) || []}
                onSelectionChange={(selectedIds) => {
                  updateField("data", {
                    ...blockData.data,
                    references: selectedIds,
                  });
                }}
                placeholder="Select references for this block..."
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

      case "neural-climate-network":
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
              <Label>Intensity</Label>
              <Input
                type="number"
                step="0.1"
                value={blockData.intensity || 1.0}
                onChange={(e) =>
                  updateField("intensity", parseFloat(e.target.value))
                }
              />
            </div>
            <div>
              <Label>Speed</Label>
              <Input
                type="number"
                step="0.1"
                value={blockData.speed || 1.0}
                onChange={(e) =>
                  updateField("speed", parseFloat(e.target.value))
                }
              />
            </div>
          </div>
        );

      case "earth-pulse":
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
              <Label>Intensity</Label>
              <Input
                type="number"
                step="0.1"
                value={blockData.intensity || 1.0}
                onChange={(e) =>
                  updateField("intensity", parseFloat(e.target.value))
                }
              />
            </div>
            <div>
              <Label>Speed</Label>
              <Input
                type="number"
                step="0.1"
                value={blockData.speed || 1.0}
                onChange={(e) =>
                  updateField("speed", parseFloat(e.target.value))
                }
              />
            </div>
          </div>
        );

      case "impact-comparison":
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
              <Label>Scenarios (JSON format)</Label>
              <Textarea
                value={JSON.stringify(blockData.scenarios || [], null, 2)}
                onChange={(e) => {
                  try {
                    const scenarios = JSON.parse(e.target.value);
                    updateField("scenarios", scenarios);
                  } catch {}
                }}
                rows={8}
                placeholder="[{name: 'Current', temperature: 1.2, seaLevel: 0.1, precipitation: 5, extremeEvents: 10}]"
              />
            </div>
          </div>
        );

      case "kpi-showcase":
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
              <Label>KPIs (JSON format)</Label>
              <Textarea
                value={JSON.stringify(blockData.kpis || [], null, 2)}
                onChange={(e) => {
                  try {
                    const kpis = JSON.parse(e.target.value);
                    updateField("kpis", kpis);
                  } catch {}
                }}
                rows={8}
                placeholder="[{label: 'Temperature', value: '+1.2°C', change: '+0.1°C', trend: 'up', icon: 'thermometer'}]"
              />
            </div>
          </div>
        );

      case "climate-metamorphosis":
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
              <Label>Stages (JSON format)</Label>
              <Textarea
                value={JSON.stringify(blockData.stages || [], null, 2)}
                onChange={(e) => {
                  try {
                    const stages = JSON.parse(e.target.value);
                    updateField("stages", stages);
                  } catch {}
                }}
                rows={8}
                placeholder="[{year: 2020, title: 'Current State', description: 'Current climate conditions', data: 100}]"
              />
            </div>
          </div>
        );

      case "climate-timeline-minimal":
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
                placeholder="[{year: 2024, title: 'Event', description: 'Description'}]"
              />
            </div>
          </div>
        );

      case "data-storm":
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
              <Label>Intensity</Label>
              <Input
                type="number"
                step="0.1"
                value={blockData.intensity || 1.0}
                onChange={(e) =>
                  updateField("intensity", parseFloat(e.target.value))
                }
              />
            </div>
            <div>
              <Label>Particles</Label>
              <Input
                type="number"
                value={blockData.particles || 100}
                onChange={(e) =>
                  updateField("particles", parseInt(e.target.value))
                }
              />
            </div>
          </div>
        );

      case "carbon-molecule-dance":
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
              <Label>Molecules</Label>
              <Input
                type="number"
                value={blockData.molecules || 50}
                onChange={(e) =>
                  updateField("molecules", parseInt(e.target.value))
                }
              />
            </div>
            <div>
              <Label>Speed</Label>
              <Input
                type="number"
                step="0.1"
                value={blockData.speed || 1.0}
                onChange={(e) =>
                  updateField("speed", parseFloat(e.target.value))
                }
              />
            </div>
          </div>
        );

      case "climate-infographic":
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
              <Label>Sections (JSON format)</Label>
              <Textarea
                value={JSON.stringify(blockData.sections || [], null, 2)}
                onChange={(e) => {
                  try {
                    const sections = JSON.parse(e.target.value);
                    updateField("sections", sections);
                  } catch {}
                }}
                rows={8}
                placeholder="[{title: 'Temperature', value: '+1.2°C', description: 'Global average increase', icon: 'thermometer'}]"
              />
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
                            <Button onClick={() => saveBlockAndClose()}>
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
                              (block.data?.title as string)}
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
                      <Button
                        onClick={() => addBlock("neural-climate-network")}
                        variant="outline"
                      >
                        <Plus className="h-4 w-4 mr-2" />
                        Neural Climate Network
                      </Button>
                      <Button
                        onClick={() => addBlock("earth-pulse")}
                        variant="outline"
                      >
                        <Plus className="h-4 w-4 mr-2" />
                        Earth Pulse
                      </Button>
                      <Button
                        onClick={() => addBlock("impact-comparison")}
                        variant="outline"
                      >
                        <Plus className="h-4 w-4 mr-2" />
                        Impact Comparison
                      </Button>
                      <Button
                        onClick={() => addBlock("kpi-showcase")}
                        variant="outline"
                      >
                        <Plus className="h-4 w-4 mr-2" />
                        KPI Showcase
                      </Button>

                      <Button
                        onClick={() => addBlock("climate-metamorphosis")}
                        variant="outline"
                      >
                        <Plus className="h-4 w-4 mr-2" />
                        Climate Metamorphosis
                      </Button>
                      <Button
                        onClick={() => addBlock("climate-timeline-minimal")}
                        variant="outline"
                      >
                        <Plus className="h-4 w-4 mr-2" />
                        Climate Timeline Minimal
                      </Button>
                      <Button
                        onClick={() => addBlock("data-storm")}
                        variant="outline"
                      >
                        <Plus className="h-4 w-4 mr-2" />
                        Data Storm
                      </Button>
                      <Button
                        onClick={() => addBlock("carbon-molecule-dance")}
                        variant="outline"
                      >
                        <Plus className="h-4 w-4 mr-2" />
                        Carbon Molecule Dance
                      </Button>
                      <Button
                        onClick={() => addBlock("climate-infographic")}
                        variant="outline"
                      >
                        <Plus className="h-4 w-4 mr-2" />
                        Climate Infographic
                      </Button>
                      <Button
                        onClick={() => addBlock("interactive-map")}
                        variant="outline"
                      >
                        <Plus className="h-4 w-4 mr-2" />
                        Interactive Map
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
