"use client";

import { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Trash2, Upload, RefreshCw, Eye } from "lucide-react";
import { CloudflareR2Manager, CloudflareR2Image } from "@/lib/blob-manager";
import { BLOB_CONFIG, ImageCategory, ImageScenario } from "@/lib/blob-config";
import ClimateImage from "./climate-image";
import { toast } from "@/components/ui/use-toast";

export default function ImageAdmin() {
  const [images, setImages] = useState<CloudflareR2Image[]>([]);
  const [uploading, setUploading] = useState(false);
  const [selectedCategory, setSelectedCategory] =
    useState<ImageCategory>("risk");
  const [selectedScenario, setSelectedScenario] = useState<
    ImageScenario | "none"
  >("none");
  const [uploadForm, setUploadForm] = useState({
    id: "",
    file: null as File | null,
    description: "",
  });

  useEffect(() => {
    loadImages();
  }, [loadImages]);

  const loadImages = useCallback(async () => {
    try {
      const allImages = await CloudflareR2Manager.getAllImages();
      setImages(allImages);
    } catch (error) {
      console.error("Failed to load images:", error);
      toast({
        title: "Error",
        description: "Failed to load images",
        variant: "destructive",
      });
    }
  }, []);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadForm.file || !selectedCategory || !uploadForm.id) {
      alert("Please fill in all required fields");
      return;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", uploadForm.file);
      formData.append("category", selectedCategory);
      formData.append(
        "scenario",
        selectedScenario === "none" ? "" : selectedScenario
      );
      formData.append("description", uploadForm.description);
      formData.append("id", uploadForm.id);

      const response = await fetch("/api/images/upload", {
        method: "POST",
        body: formData,
      });

      if (response.ok) {
        setUploadForm({ id: "", file: null, description: "" });
        setSelectedCategory("risk");
        setSelectedScenario("none");
        await loadImages();
      } else {
        const error = await response.json();
        alert(`Upload failed: ${error.error}`);
      }
    } catch (error) {
      console.error("Upload error:", error);
      alert("Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (pathname: string) => {
    if (!confirm("Are you sure you want to delete this image?")) return;

    try {
      const response = await fetch("/api/images", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pathname }),
      });

      if (response.ok) {
        await loadImages();
      } else {
        const error = await response.json();
        alert(`Delete failed: ${error.error}`);
      }
    } catch (error) {
      console.error("Delete error:", error);
      alert("Delete failed");
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Upload className="h-5 w-5" />
            Upload New Climate Image
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={handleUpload}
            className="grid grid-cols-1 md:grid-cols-2 gap-4"
          >
            <div className="space-y-2">
              <Label htmlFor="category">Category</Label>
              <Select
                value={selectedCategory}
                onValueChange={(value) =>
                  setSelectedCategory(value as ImageCategory)
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {BLOB_CONFIG.categories.map((category) => (
                    <SelectItem key={category} value={category}>
                      {category.charAt(0).toUpperCase() + category.slice(1)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="scenario">Scenario (Optional)</Label>
              <Select
                value={selectedScenario}
                onValueChange={(value) =>
                  setSelectedScenario(value as ImageScenario | "none")
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select scenario" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">None</SelectItem>
                  {BLOB_CONFIG.scenarios.map((scenario) => (
                    <SelectItem key={scenario} value={scenario}>
                      {scenario.charAt(0).toUpperCase() + scenario.slice(1)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="id">Image ID</Label>
              <Input
                id="id"
                value={uploadForm.id}
                onChange={(e) =>
                  setUploadForm({ ...uploadForm, id: e.target.value })
                }
                placeholder="e.g., freight-loading"
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="file">Image File</Label>
              <Input
                id="file"
                type="file"
                accept={BLOB_CONFIG.allowedTypes.join(",")}
                onChange={(e) =>
                  setUploadForm({
                    ...uploadForm,
                    file: e.target.files?.[0] || null,
                  })
                }
                required
              />
            </div>

            <div className="md:col-span-2 space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={uploadForm.description}
                onChange={(e) =>
                  setUploadForm({ ...uploadForm, description: e.target.value })
                }
                placeholder="Describe the image content..."
                required
              />
            </div>

            <div className="md:col-span-2">
              <Button type="submit" disabled={uploading} className="w-full">
                {uploading ? (
                  <>
                    <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                    Uploading...
                  </>
                ) : (
                  <>
                    <Upload className="mr-2 h-4 w-4" />
                    Upload Image
                  </>
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Eye className="h-5 w-5" />
            Manage Images
            <Button variant="outline" size="sm" onClick={loadImages}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {images.length === 0 ? (
            <div className="text-center py-8">Loading images...</div>
          ) : (
            <div className="space-y-6">
              {images.map((image) => (
                <Card key={image.path} className="overflow-hidden">
                  <div className="aspect-video relative">
                    <ClimateImage
                      category={image.metadata?.category || "combined"}
                      scenario={image.metadata?.scenario}
                      id={image.metadata?.id}
                      alt={image.metadata?.description || "Climate image"}
                      className="object-cover"
                    />
                  </div>
                  <CardContent className="p-4">
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <Badge variant="outline">{image.metadata?.id}</Badge>
                        {image.metadata?.scenario && (
                          <Badge variant="secondary">
                            {image.metadata.scenario}
                          </Badge>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {image.metadata?.description}
                      </p>
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-muted-foreground">
                          {image.metadata?.size
                            ? `${Math.round(image.metadata.size / 1024)} KB`
                            : ""}
                        </span>
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => handleDelete(image.path)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
