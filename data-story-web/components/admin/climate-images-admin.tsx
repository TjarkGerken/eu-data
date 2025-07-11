"use client";

import { useState, useEffect, useCallback } from "react";
import { CloudflareR2Manager, CloudflareR2Image } from "@/lib/blob-manager";
import {
  ImageCategory,
  ImageScenario,
  EconomicIndicator,
} from "@/lib/blob-config";
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Trash2, Upload, Eye, Pencil } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import Image from "next/image";

export default function ClimateImagesAdmin() {
  const [images, setImages] = useState<CloudflareR2Image[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedCategory, setSelectedCategory] =
    useState<ImageCategory>("risk");
  const [selectedScenario, setSelectedScenario] =
    useState<ImageScenario>("current");
  const [selectedIndicator, setSelectedIndicator] =
    useState<EconomicIndicator>("none");
  const [altEn, setAltEn] = useState("");
  const [altDe, setAltDe] = useState("");
  const [captionEn, setCaptionEn] = useState("");
  const [captionDe, setCaptionDe] = useState("");
  const [editingImage, setEditingImage] = useState<CloudflareR2Image | null>(
    null,
  );
  const [editIndicators, setEditIndicators] = useState<EconomicIndicator[]>([]);
  const [editCategory, setEditCategory] = useState<ImageCategory>("risk");
  const [editScenario, setEditScenario] = useState<ImageScenario>("current");
  const [editAltEn, setEditAltEn] = useState("");
  const [editAltDe, setEditAltDe] = useState("");
  const [editCaptionEn, setEditCaptionEn] = useState("");
  const [editCaptionDe, setEditCaptionDe] = useState("");
  const { toast } = useToast();

  const loadImages = useCallback(async () => {
    try {
      setLoading(true);
      const allImages = await CloudflareR2Manager.getAllImages();
      setImages(allImages);
    } catch (error) {
      console.error("Failed to load images:", error);
      toast({
        title: "Error",
        description: "Failed to load images",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    loadImages();
  }, [loadImages]);

  const handleFileUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile || !selectedCategory || !selectedScenario) {
      toast({
        title: "Error",
        description: "Please fill in all required fields",
        variant: "destructive",
      });
      return;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("category", selectedCategory);
      formData.append("scenario", selectedScenario);
      formData.append("alt_en", altEn);
      formData.append("alt_de", altDe);
      formData.append("caption_en", captionEn);
      formData.append("caption_de", captionDe);
      formData.append("indicators", JSON.stringify([selectedIndicator]));

      const response = await fetch("/api/storage/upload", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Upload failed");
      }

      toast({
        title: "Success",
        description: "Image uploaded successfully",
      });

      setSelectedFile(null);
      setAltEn("");
      setAltDe("");
      setCaptionEn("");
      setCaptionDe("");
      loadImages();
    } catch (error) {
      console.error("Upload error:", error);
      toast({
        title: "Error",
        description: "Failed to upload image",
        variant: "destructive",
      });
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (image: CloudflareR2Image) => {
    if (!confirm(`Are you sure you want to delete this image?`)) return;

    try {
      await CloudflareR2Manager.deleteImage(image.path);

      toast({
        title: "Success",
        description: "Image deleted successfully",
      });

      loadImages();
    } catch (error) {
      console.error("Delete error:", error);
      toast({
        title: "Error",
        description: "Failed to delete image",
        variant: "destructive",
      });
    }
  };

  const openEditDialog = (image: CloudflareR2Image) => {
    setEditingImage(image);
    setEditIndicators([
      (image.metadata?.indicators?.[0] as EconomicIndicator) || "none",
    ]);
    setEditCategory((image.metadata?.category as ImageCategory) || "risk");
    setEditScenario((image.metadata?.scenario as ImageScenario) || "current");
    setEditAltEn(image.metadata?.alt?.en || "");
    setEditAltDe(image.metadata?.alt?.de || "");
    setEditCaptionEn(image.metadata?.caption?.en || "");
    setEditCaptionDe(image.metadata?.caption?.de || "");
  };

  const handleUpdateImage = async () => {
    if (!editingImage) return;
    try {
      const res = await fetch("/api/storage/upload", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          path: editingImage.path,
          category: editCategory,
          scenario: editScenario,
          indicators: editIndicators,
          alt: { en: editAltEn, de: editAltDe },
          caption: { en: editCaptionEn, de: editCaptionDe },
        }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || "Update failed");
      }

      toast({ title: "Success", description: "Image updated" });
      setEditingImage(null);
      loadImages();
    } catch (error) {
      console.error("Update error", error);
      const errorMessage =
        error instanceof Error ? error.message : "Failed to update image";
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive",
      });
    }
  };

  const formatFileSize = (bytes: number | null) => {
    if (!bytes) return "Unknown";
    return (bytes / 1024 / 1024).toFixed(2) + " MB";
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return "Unknown";
    return new Date(dateString).toLocaleDateString();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">Loading...</div>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Upload className="h-5 w-5" />
            Upload New Image
          </CardTitle>
          <CardDescription>
            Upload climate visualization images to Cloudflare R2 storage
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={handleFileUpload}
            className="grid grid-cols-1 md:grid-cols-2 gap-4"
          >
            <div>
              <Label htmlFor="file">Image File</Label>
              <Input
                id="file"
                type="file"
                accept="image/*"
                onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                required
              />
            </div>
            <div>
              <Label htmlFor="category">Category</Label>
              <Select
                value={selectedCategory}
                onValueChange={(value) =>
                  setSelectedCategory(value as ImageCategory)
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select category" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="hazard">Hazard</SelectItem>
                  <SelectItem value="exposition">Exposition</SelectItem>
                  <SelectItem value="relevance">Relevance</SelectItem>
                  <SelectItem value="risk">Risk</SelectItem>
                  <SelectItem value="risk-clusters">Risk Clusters</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="scenario">Scenario</Label>
              <Select
                value={selectedScenario}
                onValueChange={(value) =>
                  setSelectedScenario(value as ImageScenario)
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select scenario" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="current">Current (SLR-0m)</SelectItem>
                  <SelectItem value="conservative">
                    Conservative (SLR-1m)
                  </SelectItem>
                  <SelectItem value="moderate">Moderate (SLR-2m)</SelectItem>
                  <SelectItem value="severe">Severe (SLR-3m)</SelectItem>
                  <SelectItem value="none">None</SelectItem>
                  <SelectItem value="all">All</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="indicator">Economic Indicator</Label>
              <Select
                value={selectedIndicator}
                onValueChange={(value) =>
                  setSelectedIndicator(value as EconomicIndicator)
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select indicator" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="freight">Freight</SelectItem>
                  <SelectItem value="hrst">HRST</SelectItem>
                  <SelectItem value="gdp">GDP</SelectItem>
                  <SelectItem value="population">Population</SelectItem>
                  <SelectItem value="combined">Combined</SelectItem>
                  <SelectItem value="none">None</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="alt-en">Alt Text (EN)</Label>
              <Input
                id="alt-en"
                value={altEn}
                onChange={(e) => setAltEn(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="alt-de">Alt Text (DE)</Label>
              <Input
                id="alt-de"
                value={altDe}
                onChange={(e) => setAltDe(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="cap-en">Caption (EN)</Label>
              <Textarea
                id="cap-en"
                value={captionEn}
                onChange={(e) => setCaptionEn(e.target.value)}
                rows={3}
              />
            </div>
            <div>
              <Label htmlFor="cap-de">Caption (DE)</Label>
              <Textarea
                id="cap-de"
                value={captionDe}
                onChange={(e) => setCaptionDe(e.target.value)}
                rows={3}
              />
            </div>
            <div className="md:col-span-2">
              <Button type="submit" disabled={uploading}>
                {uploading ? "Uploading..." : "Upload Image"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Uploaded Images ({images.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Preview</TableHead>
                  <TableHead>Filename</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead>Scenario</TableHead>
                  <TableHead>Indicators</TableHead>
                  <TableHead>Size</TableHead>
                  <TableHead>Uploaded</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {images.map((image) => (
                  <TableRow key={image.metadata?.id || image.path}>
                    <TableCell>
                      <Dialog>
                        <DialogTrigger asChild>
                          <Button variant="ghost" size="sm">
                            <Eye className="h-4 w-4" />
                          </Button>
                        </DialogTrigger>
                        <DialogContent className="max-w-4xl">
                          <DialogHeader>
                            <DialogTitle>
                              {image.path.split("/").pop() || "Image"}
                            </DialogTitle>
                          </DialogHeader>
                          <div className="relative aspect-video">
                            <Image
                              src={image.url}
                              alt={
                                image.metadata?.alt?.en ||
                                image.metadata?.alt?.de ||
                                image.metadata?.caption?.en ||
                                image.path.split("/").pop() ||
                                "Image"
                              }
                              fill
                              className="object-contain"
                            />
                          </div>
                        </DialogContent>
                      </Dialog>
                    </TableCell>
                    <TableCell className="font-medium">
                      {image.path.split("/").pop() || "Unknown"}
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary">
                        {image.metadata?.category || "Unknown"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">
                        {image.metadata?.scenario || "Unknown"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {image.metadata?.indicators?.[0] ? (
                        <Badge variant="secondary" className="text-xs">
                          {image.metadata.indicators[0]}
                        </Badge>
                      ) : (
                        <span className="text-xs text-muted-foreground">
                          None
                        </span>
                      )}
                    </TableCell>
                    <TableCell>
                      {formatFileSize(image.metadata?.size || null)}
                    </TableCell>
                    <TableCell>
                      {formatDate(
                        image.metadata?.uploadedAt
                          ? image.metadata.uploadedAt.toString()
                          : null,
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => window.open(image.url, "_blank")}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => openEditDialog(image)}
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(image)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Edit Dialog */}
      <Dialog
        open={!!editingImage}
        onOpenChange={(open) => !open && setEditingImage(null)}
      >
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle>Edit Image Metadata</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="edit-alt-en">Alt Text (EN)</Label>
                <Textarea
                  id="edit-alt-en"
                  value={editAltEn}
                  rows={7}
                  onChange={(e) => setEditAltEn(e.target.value)}
                />
              </div>
              <div>
                <Label htmlFor="edit-alt-de">Alt Text (DE)</Label>
                <Textarea
                  rows={7}
                  id="edit-alt-de"
                  value={editAltDe}
                  onChange={(e) => setEditAltDe(e.target.value)}
                />
              </div>
              <div>
                <Label htmlFor="edit-cap-en">Caption (EN)</Label>
                <Textarea
                  id="edit-cap-en"
                  value={editCaptionEn}
                  onChange={(e) => setEditCaptionEn(e.target.value)}
                  rows={7}
                />
              </div>
              <div>
                <Label htmlFor="edit-cap-de">Caption (DE)</Label>
                <Textarea
                  id="edit-cap-de"
                  value={editCaptionDe}
                  onChange={(e) => setEditCaptionDe(e.target.value)}
                  rows={7}
                />
              </div>
            </div>
            <div>
              <Label>Category</Label>
              <Select
                value={editCategory}
                onValueChange={(value) =>
                  setEditCategory(value as ImageCategory)
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select category" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="hazard">Hazard</SelectItem>
                  <SelectItem value="exposition">Exposition</SelectItem>
                  <SelectItem value="relevance">Relevance</SelectItem>
                  <SelectItem value="risk">Risk</SelectItem>
                  <SelectItem value="risk-clusters">Risk Clusters</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>SLR Scenario</Label>
              <Select
                value={editScenario}
                onValueChange={(value) =>
                  setEditScenario(value as ImageScenario)
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select scenario" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="current">Current (SLR-0m)</SelectItem>
                  <SelectItem value="conservative">
                    Conservative (SLR-1m)
                  </SelectItem>
                  <SelectItem value="moderate">Moderate (SLR-2m)</SelectItem>
                  <SelectItem value="severe">Severe (SLR-3m)</SelectItem>
                  <SelectItem value="none">None</SelectItem>
                  <SelectItem value="all">All</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Economic Indicator</Label>
              <Select
                value={editIndicators[0] || "none"}
                onValueChange={(value) =>
                  setEditIndicators([value as EconomicIndicator])
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select indicator" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="freight">Freight</SelectItem>
                  <SelectItem value="hrst">HRST</SelectItem>
                  <SelectItem value="gdp">GDP</SelectItem>
                  <SelectItem value="population">Population</SelectItem>
                  <SelectItem value="combined">Combined</SelectItem>
                  <SelectItem value="none">None</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setEditingImage(null)}>
                Cancel
              </Button>
              <Button onClick={handleUpdateImage}>Save</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
