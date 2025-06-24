"use client";

import { useState, useEffect, useCallback } from "react";
import Image from "next/image";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
import { Search, Filter, Image as ImageIcon, X } from "lucide-react";
import { ImageOption } from "@/lib/types";

interface ImageApiResponse {
  url: string;
  path?: string;
  metadata?: {
    id?: string;
    category?: string;
    scenario?: string;
    description?: string;
  };
}

export default function GalleryPage() {
  const [images, setImages] = useState<ImageOption[]>([]);
  const [filteredImages, setFilteredImages] = useState<ImageOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedImage, setSelectedImage] = useState<ImageOption | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [scenarioFilter, setScenarioFilter] = useState<string>("all");

  useEffect(() => {
    loadImages();
  }, []);

  const loadImages = async () => {
    try {
      const response = await fetch("/api/images");
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to fetch images");
      }

      const formattedImages = (data.images || [])
        .map((img: ImageApiResponse) => {
          const filename =
            img.path?.split("/").pop() || img.metadata?.id || "unknown";
          return {
            id: img.metadata?.id || filename,
            name: filename,
            url: img.url,
            category: img.metadata?.category || "unknown",
            scenario: img.metadata?.scenario,
            description: img.metadata?.description,
          };
        })
        .filter((img: ImageOption) => img.url && img.name !== "unknown");

      setImages(formattedImages);
    } catch (error) {
      console.error("Failed to load images:", error);
      setImages([]);
    } finally {
      setLoading(false);
    }
  };

  const filterImages = useCallback(() => {
    let filtered = [...images];

    if (searchTerm) {
      filtered = filtered.filter(
        (img) =>
          img.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          img.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          img.category.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    if (categoryFilter !== "all") {
      filtered = filtered.filter((img) => img.category === categoryFilter);
    }

    if (scenarioFilter !== "all") {
      filtered = filtered.filter((img) => img.scenario === scenarioFilter);
    }

    setFilteredImages(filtered);
  }, [images, searchTerm, categoryFilter, scenarioFilter]);

  useEffect(() => {
    filterImages();
  }, [filterImages]);

  const categories = Array.from(new Set(images.map((img) => img.category)));
  const scenarios = Array.from(
    new Set(images.map((img) => img.scenario).filter((scenario): scenario is string => Boolean(scenario)))
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#2d5a3d]"></div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-[#2d5a3d] mb-4">
          Visualization Gallery
        </h1>
        <p className="text-gray-600 mb-6">
          Explore our collection of climate visualizations and data insights
        </p>

        {/* Filters */}
        <div className="flex flex-col md:flex-row gap-4 mb-6">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
              <Input
                placeholder="Search images..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>
          <div className="flex gap-2">
            <Select value={categoryFilter} onValueChange={setCategoryFilter}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Categories</SelectItem>
                {categories.map((category) => (
                  <SelectItem key={category} value={category}>
                    {category.charAt(0).toUpperCase() + category.slice(1)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={scenarioFilter} onValueChange={setScenarioFilter}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Scenario" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Scenarios</SelectItem>
                {scenarios.map((scenario) => (
                  <SelectItem key={scenario} value={scenario}>
                    {scenario?.charAt(0).toUpperCase() + scenario?.slice(1)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Results count */}
        <div className="flex items-center gap-2 mb-4">
          <Filter className="h-4 w-4 text-gray-400" />
          <span className="text-sm text-gray-600">
            Showing {filteredImages.length} of {images.length} images
          </span>
        </div>
      </div>

      {/* Image Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {filteredImages.map((image) => (
          <Card
            key={image.id}
            className="group cursor-pointer hover:shadow-lg transition-shadow duration-200"
            onClick={() => setSelectedImage(image)}
          >
            <CardContent className="p-0">
              <div className="relative aspect-video overflow-hidden rounded-t-lg">
                <Image
                  src={image.url}
                  alt={image.name}
                  fill
                  className="object-cover group-hover:scale-105 transition-transform duration-200"
                />
                <div className="absolute inset-0 bg-black opacity-0 group-hover:opacity-10 transition-opacity duration-200" />
              </div>
              <div className="p-4">
                <h3 className="font-medium text-sm mb-2 truncate">
                  {image.name}
                </h3>
                <div className="flex gap-1 mb-2">
                  <Badge variant="secondary" className="text-xs">
                    {image.category}
                  </Badge>
                  {image.scenario && (
                    <Badge variant="outline" className="text-xs">
                      {image.scenario}
                    </Badge>
                  )}
                </div>
                {image.description && (
                  <p className="text-xs text-gray-600 overflow-hidden text-ellipsis">
                    {image.description.length > 80
                      ? image.description.slice(0, 80) + "..."
                      : image.description}
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {filteredImages.length === 0 && (
        <div className="text-center py-12">
          <ImageIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-600 mb-2">
            No images found
          </h3>
          <p className="text-gray-500">
            Try adjusting your search terms or filters
          </p>
        </div>
      )}

      {/* Image Preview Modal */}
      <Dialog
        open={!!selectedImage}
        onOpenChange={() => setSelectedImage(null)}
      >
        <DialogContent className="max-w-6xl max-h-[90vh] p-0">
          {selectedImage && (
            <div className="flex flex-col lg:flex-row h-full">
              {/* Image Section */}
              <div className="flex-1 relative bg-black">
                <Image
                  src={selectedImage.url}
                  alt={selectedImage.name}
                  fill
                  className="object-contain"
                />
                <Button
                  variant="ghost"
                  size="icon"
                  className="absolute top-4 right-4 bg-black/50 hover:bg-black/70 text-white"
                  onClick={() => setSelectedImage(null)}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>

              {/* Metadata Section */}
              <div className="w-full lg:w-80 p-6 bg-white overflow-y-auto">
                <DialogHeader className="mb-4">
                  <DialogTitle className="text-lg">
                    {selectedImage.name}
                  </DialogTitle>
                </DialogHeader>

                <div className="space-y-4">
                  <div>
                    <Label className="text-sm font-medium text-gray-700">
                      Category
                    </Label>
                    <Badge variant="secondary" className="mt-1">
                      {selectedImage.category}
                    </Badge>
                  </div>

                  {selectedImage.scenario && (
                    <div>
                      <Label className="text-sm font-medium text-gray-700">
                        Scenario
                      </Label>
                      <Badge variant="outline" className="mt-1">
                        {selectedImage.scenario}
                      </Badge>
                    </div>
                  )}

                  {selectedImage.description && (
                    <div>
                      <Label className="text-sm font-medium text-gray-700">
                        Description
                      </Label>
                      <p className="mt-1 text-sm text-gray-600">
                        {selectedImage.description}
                      </p>
                    </div>
                  )}

                  <div>
                    <Label className="text-sm font-medium text-gray-700">
                      Image ID
                    </Label>
                    <p className="mt-1 text-sm text-gray-600 font-mono">
                      {selectedImage.id}
                    </p>
                  </div>

                  <div>
                    <Label className="text-sm font-medium text-gray-700">
                      File Name
                    </Label>
                    <p className="mt-1 text-sm text-gray-600 break-all">
                      {selectedImage.name}
                    </p>
                  </div>

                  <div className="pt-4 border-t">
                    <Button
                      variant="outline"
                      className="w-full"
                      onClick={() => window.open(selectedImage.url, "_blank")}
                    >
                      Open Full Size
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
