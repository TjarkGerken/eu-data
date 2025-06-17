"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ArrowLeft, Save, Plus, Trash2, BookOpen } from "lucide-react";
import Link from "next/link";
import { ReferencesDropdown } from "@/components/references-dropdown";
import { ImageDropdown } from "@/components/image-dropdown";
import {
  Reference,
  Visualization,
  LanguageContent,
  ContentData,
} from "@/lib/types";

export default function ContentManagementPage() {
  const [content, setContent] = useState<ContentData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [selectedLang, setSelectedLang] = useState<"en" | "de">("en");
  const [selectedTab, setSelectedTab] = useState("basic");

  useEffect(() => {
    const authenticated = sessionStorage.getItem("admin_authenticated");
    if (authenticated !== "true") {
      window.location.href = "/admin";
      return;
    }

    loadContent();
  }, []);

  const loadContent = async () => {
    try {
      const response = await fetch("/api/content");
      const data = await response.json();
      setContent(data);
    } catch (error) {
      setMessage("Failed to load content");
    } finally {
      setLoading(false);
    }
  };

  const saveContent = async () => {
    if (!content) return;

    setSaving(true);
    try {
      const response = await fetch("/api/content", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(content),
      });

      if (response.ok) {
        setMessage("Content saved successfully");
      } else {
        setMessage("Failed to save content");
      }
    } catch (error) {
      setMessage("Failed to save content");
    } finally {
      setSaving(false);
    }
  };

  const updateBasicField = (field: keyof LanguageContent, value: string) => {
    if (!content) return;

    setContent({
      ...content,
      [selectedLang]: {
        ...content[selectedLang],
        [field]: value,
      },
    });
  };

  const updateVisualization = (
    index: number,
    field: keyof Visualization,
    value: string | string[]
  ) => {
    if (!content) return;

    const updatedVisualizations = [...content[selectedLang].visualizations];
    updatedVisualizations[index] = {
      ...updatedVisualizations[index],
      [field]: value,
    };

    setContent({
      ...content,
      [selectedLang]: {
        ...content[selectedLang],
        visualizations: updatedVisualizations,
      },
    });
  };

  const addVisualization = () => {
    if (!content) return;

    const newVisualization: Visualization = {
      title: "New Visualization",
      description: "Description here",
      content: "Content here",
      type: "map",
      imageCategory: "hazard",
      imageId: "new-id",
      references: [],
    };

    setContent({
      ...content,
      [selectedLang]: {
        ...content[selectedLang],
        visualizations: [
          ...content[selectedLang].visualizations,
          newVisualization,
        ],
      },
    });
  };

  const removeVisualization = (index: number) => {
    if (!content) return;

    const updatedVisualizations = content[selectedLang].visualizations.filter(
      (_, i) => i !== index
    );

    setContent({
      ...content,
      [selectedLang]: {
        ...content[selectedLang],
        visualizations: updatedVisualizations,
      },
    });
  };

  const updateReference = (
    index: number,
    field: keyof Reference,
    value: string | string[] | number
  ) => {
    if (!content) return;

    const updatedReferences = [...content.references];
    updatedReferences[index] = {
      ...updatedReferences[index],
      [field]: value,
    };

    setContent({
      ...content,
      references: updatedReferences,
    });
  };

  const addReference = () => {
    if (!content) return;

    const newReference: Reference = {
      id: String(
        Math.max(...content.references.map((r) => parseInt(r.id)), 0) + 1
      ),
      title: "New Reference",
      authors: ["Author Name"],
      year: new Date().getFullYear(),
      type: "journal",
      url: "",
    };

    setContent({
      ...content,
      references: [...content.references, newReference],
    });
  };

  const removeReference = (index: number) => {
    if (!content) return;

    setContent({
      ...content,
      references: content.references.filter((_, i) => i !== index),
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div>Loading...</div>
      </div>
    );
  }

  if (!content) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div>Failed to load content</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto py-8">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <Link href="/admin">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Dashboard
              </Button>
            </Link>
            <h1 className="text-3xl font-bold">Content Management</h1>
          </div>
          <Button onClick={saveContent} disabled={saving}>
            <Save className="h-4 w-4 mr-2" />
            {saving ? "Saving..." : "Save Changes"}
          </Button>
        </div>

        {message && (
          <Alert className="mb-6">
            <AlertDescription>{message}</AlertDescription>
          </Alert>
        )}

        <Tabs
          value={selectedTab}
          onValueChange={setSelectedTab}
          className="space-y-6"
        >
          <div className="flex items-center gap-4">
            <TabsList>
              <TabsTrigger value="basic">Basic Content</TabsTrigger>
              <TabsTrigger value="visualizations">Visualizations</TabsTrigger>
              <TabsTrigger value="references">References</TabsTrigger>
            </TabsList>

            {["basic", "visualizations"].includes(selectedTab) && (
              <Select
                value={selectedLang}
                onValueChange={(value: "en" | "de") => setSelectedLang(value)}
              >
                <SelectTrigger className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="en">English</SelectItem>
                  <SelectItem value="de">German</SelectItem>
                </SelectContent>
              </Select>
            )}
          </div>

          <TabsContent value="basic" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Hero Section</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="heroTitle">Hero Title</Label>
                  <Input
                    id="heroTitle"
                    value={content[selectedLang].heroTitle}
                    onChange={(e) =>
                      updateBasicField("heroTitle", e.target.value)
                    }
                  />
                </div>
                <div>
                  <Label htmlFor="heroDescription">Hero Description</Label>
                  <Textarea
                    id="heroDescription"
                    value={content[selectedLang].heroDescription}
                    onChange={(e) =>
                      updateBasicField("heroDescription", e.target.value)
                    }
                    rows={3}
                  />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Main Content</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="dataStoryTitle">Data Story Title</Label>
                  <Input
                    id="dataStoryTitle"
                    value={content[selectedLang].dataStoryTitle}
                    onChange={(e) =>
                      updateBasicField("dataStoryTitle", e.target.value)
                    }
                  />
                </div>
                <div>
                  <Label htmlFor="introText1">Introduction Text 1</Label>
                  <Textarea
                    id="introText1"
                    value={content[selectedLang].introText1}
                    onChange={(e) =>
                      updateBasicField("introText1", e.target.value)
                    }
                    rows={4}
                  />
                </div>
                <div>
                  <Label htmlFor="introText2">Introduction Text 2</Label>
                  <Textarea
                    id="introText2"
                    value={content[selectedLang].introText2}
                    onChange={(e) =>
                      updateBasicField("introText2", e.target.value)
                    }
                    rows={4}
                  />
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="visualizations" className="space-y-6">
            <div className="flex justify-between items-center">
              <h3 className="text-xl font-semibold">Visualizations</h3>
              <Button onClick={addVisualization}>
                <Plus className="h-4 w-4 mr-2" />
                Add Visualization
              </Button>
            </div>

            {content[selectedLang].visualizations.map((viz, index) => (
              <Card key={index}>
                <CardHeader>
                  <div className="flex justify-between items-center">
                    <CardTitle>Visualization {index + 1}</CardTitle>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => removeVisualization(index)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>Title</Label>
                      <Input
                        value={viz.title}
                        onChange={(e) =>
                          updateVisualization(index, "title", e.target.value)
                        }
                      />
                    </div>
                    <div>
                      <Label>Type</Label>
                      <Select
                        value={viz.type}
                        onValueChange={(value) =>
                          updateVisualization(index, "type", value)
                        }
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
                  </div>

                  <div>
                    <Label>Description</Label>
                    <Textarea
                      value={viz.description}
                      onChange={(e) =>
                        updateVisualization(
                          index,
                          "description",
                          e.target.value
                        )
                      }
                      rows={2}
                    />
                  </div>

                  <div>
                    <Label>Content</Label>
                    <Textarea
                      value={viz.content}
                      onChange={(e) =>
                        updateVisualization(index, "content", e.target.value)
                      }
                      rows={4}
                    />
                  </div>

                  <div>
                    <Label>Image</Label>
                    <ImageDropdown
                      selectedImageId={viz.imageId}
                      onImageChange={(imageId, imageData) => {
                        updateVisualization(index, "imageId", imageId);
                        if (imageData) {
                          updateVisualization(
                            index,
                            "imageCategory",
                            imageData.category
                          );
                          if (imageData.scenario) {
                            updateVisualization(
                              index,
                              "imageScenario",
                              imageData.scenario
                            );
                          }
                        }
                      }}
                    />
                  </div>

                  <div>
                    <Label>References</Label>
                    <ReferencesDropdown
                      selectedReferences={viz.references}
                      onReferencesChange={(references) =>
                        updateVisualization(index, "references", references)
                      }
                    />
                  </div>
                </CardContent>
              </Card>
            ))}
          </TabsContent>

          <TabsContent value="references" className="space-y-6">
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-2">
                <BookOpen className="h-5 w-5" />
                <h3 className="text-xl font-semibold">References Management</h3>
              </div>
              <Button onClick={addReference}>
                <Plus className="h-4 w-4 mr-2" />
                Add Reference
              </Button>
            </div>

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
                      onClick={() => removeReference(index)}
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
                        value={ref.authors.join(", ")}
                        onChange={(e) =>
                          updateReference(
                            index,
                            "authors",
                            e.target.value
                              .split(",")
                              .map((author) => author.trim())
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
                    <Label>Journal (optional)</Label>
                    <Input
                      value={ref.journal || ""}
                      onChange={(e) =>
                        updateReference(index, "journal", e.target.value)
                      }
                    />
                  </div>

                  <div>
                    <Label>URL (optional)</Label>
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
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
