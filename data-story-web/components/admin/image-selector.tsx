"use client";

import { useState, useEffect, useCallback } from "react";
import NextImage from "next/image";
import { CloudflareR2Manager } from "@/lib/blob-manager";
import { ImageCategory } from "@/lib/blob-config";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Image, Loader2 } from "lucide-react";

interface ClimateImage {
  url: string;
  path: string;
  metadata: {
    id: string;
    category: string;
    scenario: string;
    description: string;
    uploadedAt: Date;
    size: number;
  };
}

interface ImageSelectorProps {
  value?: string;
  onChange: (imageId: string, imageData?: ClimateImage) => void;
  category?: string;
  scenario?: string;
}

export default function ImageSelector({
  value,
  onChange,
  category,
  scenario,
}: ImageSelectorProps) {
  const [images, setImages] = useState<ClimateImage[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedImageData, setSelectedImageData] =
    useState<ClimateImage | null>(null);

  const fetchImages = useCallback(async () => {
    try {
      let imageData: ClimateImage[];

      if (category && category !== "all") {
        imageData = await CloudflareR2Manager.getImagesByCategory(
          category as ImageCategory
        );
      } else {
        imageData = await CloudflareR2Manager.getAllImages();
      }

      // Filter by scenario if specified
      if (scenario && scenario !== "all") {
        imageData = imageData.filter(
          (img) => img.metadata.scenario === scenario
        );
      }

      setImages(imageData);
    } catch (error) {
      console.error("Error fetching images:", error);
    } finally {
      setLoading(false);
    }
  }, [category, scenario]);

  useEffect(() => {
    fetchImages();
  }, [fetchImages]);

  useEffect(() => {
    if (value && images.length > 0) {
      const found = images.find(
        (img) => img.metadata.id === value || img.url === value
      );
      setSelectedImageData(found || null);
    }
  }, [value, images]);

  const handleImageSelect = (imageId: string) => {
    const imageData = images.find((img) => img.metadata.id === imageId);
    setSelectedImageData(imageData || null);
    onChange(imageId, imageData);
  };

  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      hazard: "bg-red-100 text-red-800",
      exposition: "bg-blue-100 text-blue-800",
      risk: "bg-orange-100 text-orange-800",
      relevance: "bg-green-100 text-green-800",
      combined: "bg-purple-100 text-purple-800",
    };
    return colors[category] || "bg-gray-100 text-gray-800";
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-4">
        <Loader2 className="h-4 w-4 animate-spin mr-2" />
        Loading images...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <Select value={value || ""} onValueChange={handleImageSelect}>
        <SelectTrigger>
          <SelectValue placeholder="Select an image..." />
        </SelectTrigger>
        <SelectContent>
          {images.map((image) => (
            <SelectItem key={image.metadata.id} value={image.metadata.id}>
              <div className="flex items-center space-x-2">
                <Image className="h-4 w-4" aria-label="Image icon" />
                <span className="truncate max-w-48">{image.metadata.id}</span>
                <Badge
                  className={getCategoryColor(image.metadata.category)}
                  variant="secondary"
                >
                  {image.metadata.category}
                </Badge>
                {image.metadata.scenario && (
                  <Badge variant="outline">{image.metadata.scenario}</Badge>
                )}
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {selectedImageData && (
        <Card>
          <CardContent className="p-4">
            <div className="space-y-3">
              <div className="aspect-video relative bg-gray-100 rounded-lg overflow-hidden">
                <NextImage
                  src={selectedImageData.url}
                  alt={selectedImageData.metadata.description}
                  fill
                  className="object-cover"
                  onError={(e) => {
                    (e.target as HTMLImageElement).src = "/placeholder.svg";
                  }}
                />
              </div>

              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Badge
                    className={getCategoryColor(
                      selectedImageData.metadata.category
                    )}
                  >
                    {selectedImageData.metadata.category}
                  </Badge>
                  {selectedImageData.metadata.scenario && (
                    <Badge variant="outline">
                      {selectedImageData.metadata.scenario}
                    </Badge>
                  )}
                </div>

                <div>
                  <p className="font-medium text-sm">
                    {selectedImageData.metadata.id}
                  </p>
                  {selectedImageData.metadata.description && (
                    <p className="text-sm text-muted-foreground">
                      {selectedImageData.metadata.description}
                    </p>
                  )}
                </div>

                <div className="text-xs text-muted-foreground">
                  Image ID: {selectedImageData.metadata.id}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {images.length === 0 && (
        <div className="text-center p-8 text-muted-foreground">
          <Image
            className="h-12 w-12 mx-auto mb-4 opacity-50"
            aria-label="No images found"
          />
          <p>No images found</p>
          {(category || scenario) && (
            <p className="text-sm">
              for category: {category}, scenario: {scenario}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
