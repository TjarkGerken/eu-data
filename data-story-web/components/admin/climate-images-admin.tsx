"use client";

import { useState, useEffect, useCallback } from "react";
import { CloudflareR2Manager, CloudflareR2Image } from "@/lib/blob-manager";
import { ImageCategory, ImageScenario } from "@/lib/blob-config";
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
import { Trash2, Upload, Eye } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import Image from "next/image";

export default function ClimateImagesAdmin() {
  const [images, setImages] = useState<CloudflareR2Image[]>([]);
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedCategory, setSelectedCategory] =
    useState<ImageCategory>("risk");
  const [selectedScenario, setSelectedScenario] =
    useState<ImageScenario>("current");
  const [description, setDescription] = useState("");
  const { toast } = useToast();

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
      formData.append("description", description);

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
      setDescription("");
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
            Upload climate visualization images to Supabase storage
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
                  <SelectItem value="risk">Risk</SelectItem>
                  <SelectItem value="hazard">Hazard</SelectItem>
                  <SelectItem value="exposition">Exposition</SelectItem>
                  <SelectItem value="relevance">Relevance</SelectItem>
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
                  <SelectItem value="current">Current</SelectItem>
                  <SelectItem value="severe">Severe</SelectItem>
                  <SelectItem value="comparison">Comparison</SelectItem>
                  <SelectItem value="freight">Freight</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe the image content"
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
                  <TableHead>Size</TableHead>
                  <TableHead>Uploaded</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {images.map((image) => (
                  <TableRow key={image.id}>
                    <TableCell>
                      <Dialog>
                        <DialogTrigger asChild>
                          <Button variant="ghost" size="sm">
                            <Eye className="h-4 w-4" />
                          </Button>
                        </DialogTrigger>
                        <DialogContent className="max-w-4xl">
                          <DialogHeader>
                            <DialogTitle>{image.filename}</DialogTitle>
                          </DialogHeader>
                          <div className="relative aspect-video">
                            <Image
                              src={image.public_url}
                              alt={image.description || image.filename}
                              fill
                              className="object-contain"
                            />
                          </div>
                        </DialogContent>
                      </Dialog>
                    </TableCell>
                    <TableCell className="font-medium">
                      {image.filename}
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary">{image.category}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{image.scenario}</Badge>
                    </TableCell>
                    <TableCell>{formatFileSize(image.file_size)}</TableCell>
                    <TableCell>{formatDate(image.created_at)}</TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() =>
                            window.open(image.public_url, "_blank")
                          }
                        >
                          <Eye className="h-4 w-4" />
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
    </div>
  );
}
