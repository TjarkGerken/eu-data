"use client";

import { useState, useEffect, useCallback } from "react";
import NextImage from "next/image";
import { supabase } from "@/lib/supabase";
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
  id: number;
  filename: string;
  category: string;
  scenario: string;
  description: string | null;
  publicUrl: string;
  storageType: string;
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
      let query = supabase.from("climate_images").select("*");

      if (category) {
        query = query.eq("category", category);
      }

      if (scenario) {
        query = query.eq("scenario", scenario);
      }

      const { data, error } = await query.order("display_order", {
        ascending: true,
      });

      if (error) throw error;

      const mappedImages: ClimateImage[] = (data || []).map(item => ({
        id: item.id,
        filename: item.filename,
        category: item.category,
        scenario: item.scenario,
        description: item.description,
        publicUrl: item.public_url,
        storageType: 'blob'
      }));

      setImages(mappedImages);
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
        (img) => img.id.toString() === value || img.filename === value
      );
      setSelectedImageData(found || null);
    }
  }, [value, images]);

  const handleImageSelect = (imageId: string) => {
    const imageData = images.find((img) => img.id.toString() === imageId);
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
            <SelectItem key={image.id} value={image.id.toString()}>
              <div className="flex items-center space-x-2">
                <Image className="h-4 w-4" aria-label="Image icon" />
                <span className="truncate max-w-48">{image.filename}</span>
                <Badge
                  className={getCategoryColor(image.category)}
                  variant="secondary"
                >
                  {image.category}
                </Badge>
                {image.scenario && (
                  <Badge variant="outline">{image.scenario}</Badge>
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
                  src={selectedImageData.publicUrl}
                  alt={
                    selectedImageData.description || selectedImageData.filename
                  }
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
                    className={getCategoryColor(selectedImageData.category)}
                  >
                    {selectedImageData.category}
                  </Badge>
                  {selectedImageData.scenario && (
                    <Badge variant="outline">
                      {selectedImageData.scenario}
                    </Badge>
                  )}
                </div>

                <div>
                  <p className="font-medium text-sm">
                    {selectedImageData.filename}
                  </p>
                  {selectedImageData.description && (
                    <p className="text-sm text-muted-foreground">
                      {selectedImageData.description}
                    </p>
                  )}
                </div>

                <div className="text-xs text-muted-foreground">
                  Image ID: {selectedImageData.id}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {images.length === 0 && (
        <div className="text-center p-8 text-muted-foreground">
          <Image className="h-12 w-12 mx-auto mb-4 opacity-50" aria-label="No images found" />
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
