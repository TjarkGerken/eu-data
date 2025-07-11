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
import {
  Search,
  Filter,
  Image as ImageIcon,
  X,
  Globe,
  Activity,
} from "lucide-react";
import { ImageOption } from "@/lib/types";
import { useLanguage } from "@/contexts/language-context";
import { Header } from "@/components/header";

interface ImageApiResponse {
  url: string;
  path?: string;
  metadata?: {
    id?: string;
    category?: string;
    scenario?: string;
    description?: string;
    alt?: { en: string; de: string };
    caption?: { en: string; de: string };
    indicators?: string[];
    uploadedAt?: string;
    size?: number;
  };
}

export default function GalleryPage() {
  const { language } = useLanguage();
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
            caption:
              img.metadata?.caption ||
              (img.metadata?.description
                ? { en: img.metadata.description, de: "" }
                : undefined),
            alt: img.metadata?.alt,
            indicators: img.metadata?.indicators,
            uploadedAt: img.metadata?.uploadedAt,
            size: img.metadata?.size,
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
          img.caption?.en?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          img.caption?.de?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          img.category.toLowerCase().includes(searchTerm.toLowerCase()) ||
          img.scenario?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          img.indicators?.some((indicator) =>
            indicator.toLowerCase().includes(searchTerm.toLowerCase()),
          ),
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
    new Set(
      images
        .map((img) => img.scenario)
        .filter((scenario): scenario is string => Boolean(scenario)),
    ),
  );

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <Header enableAnimations={false} />
        <div className="flex items-center justify-center min-h-screen">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#2d5a3d]"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <Header enableAnimations={false} />
      <div className="container mx-auto px-4 py-8 pt-24">
        {/* Header Section */}
        <div className="mb-8 text-center">
          <div className="flex items-center justify-center gap-3 mb-4">
            <Globe className="h-8 w-8 text-[#2d5a3d]" />
            <h1 className="text-4xl font-bold text-[#2d5a3d]">
              {language === "de"
                ? "Visualisierungsgalerie"
                : "Visualization Gallery"}
            </h1>
            <Activity className="h-8 w-8 text-[#2d5a3d]" />
          </div>
          <p className="text-gray-600 text-lg max-w-2xl mx-auto mb-6">
            {language === "de"
              ? "Entdecken Sie unsere Sammlung von Klimavisualisierungen und Datenanalysen für die EU-Klimarisikobewertung"
              : "Explore our comprehensive collection of climate visualizations and data insights for EU climate risk assessment"}
          </p>
          <div className="flex items-center justify-center gap-4 text-sm text-gray-500">
            <span className="flex items-center gap-1">
              <Badge variant="outline" className="text-xs">
                {images.length}
              </Badge>
              {language === "de" ? "Gesamte Bilder" : "Total Images"}
            </span>
            <span className="flex items-center gap-1">
              <Badge variant="outline" className="text-xs">
                {categories.length}
              </Badge>
              {language === "de" ? "Kategorien" : "Categories"}
            </span>
            <span className="flex items-center gap-1">
              <Badge variant="outline" className="text-xs">
                {scenarios.length}
              </Badge>
              {language === "de" ? "Szenarien" : "Scenarios"}
            </span>
          </div>
        </div>

        {/* Enhanced Filters */}
        <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
          <div className="flex flex-col lg:flex-row gap-4">
            <div className="flex-1">
              <Label className="text-sm font-medium text-gray-700 mb-2 block">
                {language === "de" ? "Suche" : "Search"}
              </Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                <Input
                  placeholder={
                    language === "de"
                      ? "Bilder, Kategorien, Szenarien durchsuchen..."
                      : "Search images, categories, scenarios..."
                  }
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10 h-10"
                />
              </div>
            </div>
            <div className="flex gap-3">
              <div className="min-w-[160px]">
                <Label className="text-sm font-medium text-gray-700 mb-2 block">
                  {language === "de" ? "Kategorie" : "Category"}
                </Label>
                <Select
                  value={categoryFilter}
                  onValueChange={setCategoryFilter}
                >
                  <SelectTrigger className="h-10">
                    <SelectValue
                      placeholder={language === "de" ? "Kategorie" : "Category"}
                    />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">
                      {language === "de" ? "Alle Kategorien" : "All Categories"}
                    </SelectItem>
                    {categories.map((category) => (
                      <SelectItem key={category} value={category}>
                        {language === "de"
                          ? getCategoryTranslation(category)
                          : category.charAt(0).toUpperCase() +
                            category.slice(1)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="min-w-[140px]">
                <Label className="text-sm font-medium text-gray-700 mb-2 block">
                  {language === "de" ? "Szenario" : "Scenario"}
                </Label>
                <Select
                  value={scenarioFilter}
                  onValueChange={setScenarioFilter}
                >
                  <SelectTrigger className="h-10">
                    <SelectValue
                      placeholder={language === "de" ? "Szenario" : "Scenario"}
                    />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">
                      {language === "de" ? "Alle Szenarien" : "All Scenarios"}
                    </SelectItem>
                    {scenarios.map((scenario) => (
                      <SelectItem key={scenario} value={scenario}>
                        {language === "de"
                          ? getScenarioTranslation(scenario)
                          : scenario?.charAt(0).toUpperCase() +
                            scenario?.slice(1)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
        </div>

        {/* Results count */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-gray-400" />
            <span className="text-sm text-gray-600">
              {language === "de"
                ? `${filteredImages.length} von ${images.length} Bildern angezeigt`
                : `Showing ${filteredImages.length} of ${images.length} images`}
            </span>
          </div>
          {(categoryFilter !== "all" ||
            scenarioFilter !== "all" ||
            searchTerm) && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setSearchTerm("");
                setCategoryFilter("all");
                setScenarioFilter("all");
              }}
            >
              {language === "de" ? "Filter zurücksetzen" : "Clear filters"}
            </Button>
          )}
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
                  <div className="flex flex-wrap gap-1 mb-2">
                    <Badge variant="secondary" className="text-xs">
                      {language === "de"
                        ? getCategoryTranslation(image.category)
                        : image.category}
                    </Badge>
                    {image.scenario && (
                      <Badge variant="outline" className="text-xs">
                        {language === "de"
                          ? getScenarioTranslation(image.scenario)
                          : image.scenario}
                      </Badge>
                    )}
                    {image.indicators && image.indicators.length > 0 && (
                      <Badge
                        variant="outline"
                        className="text-xs bg-blue-50 text-blue-700"
                      >
                        {image.indicators.length}{" "}
                        {language === "de" ? "Indikator(en)" : "Indicator(s)"}
                      </Badge>
                    )}
                  </div>
                  {(image.caption?.[language] || image.caption?.en) && (
                    <p className="text-xs text-gray-600 overflow-hidden text-ellipsis">
                      {(() => {
                        const caption =
                          image.caption?.[language] || image.caption?.en || "";
                        return caption.length > 80
                          ? caption.slice(0, 80) + "..."
                          : caption;
                      })()}
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {filteredImages.length === 0 && (
          <div className="text-center py-12 bg-white rounded-lg shadow-sm">
            <ImageIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-600 mb-2">
              {language === "de" ? "Keine Bilder gefunden" : "No images found"}
            </h3>
            <p className="text-gray-500">
              {language === "de"
                ? "Versuchen Sie, Ihre Suchbegriffe oder Filter anzupassen"
                : "Try adjusting your search terms or filters"}
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

                {/* Enhanced Metadata Section */}
                <div className="w-full lg:w-96 p-6 bg-white overflow-y-auto">
                  <DialogHeader className="mb-6">
                    <DialogTitle className="text-xl text-[#2d5a3d]">
                      {selectedImage.name}
                    </DialogTitle>
                  </DialogHeader>

                  <div className="space-y-6">
                    {/* Classification */}
                    <div className="space-y-3">
                      <Label className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
                        {language === "de"
                          ? "Klassifizierung"
                          : "Classification"}
                      </Label>
                      <div className="flex flex-wrap gap-2">
                        <Badge variant="secondary" className="">
                          {language === "de"
                            ? getCategoryTranslation(selectedImage.category)
                            : selectedImage.category}
                        </Badge>
                        {selectedImage.scenario && (
                          <Badge variant="outline" className="">
                            {language === "de"
                              ? getScenarioTranslation(selectedImage.scenario)
                              : selectedImage.scenario}
                          </Badge>
                        )}
                      </div>
                    </div>

                    {/* Scientific Caption */}
                    {(selectedImage.caption?.[language] ||
                      selectedImage.caption?.en) && (
                      <div>
                        <Label className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
                          {language === "de"
                            ? "Wissenschaftliche Beschreibung"
                            : "Scientific Description"}
                        </Label>
                        <div className="mt-2 p-3 bg-gray-50 rounded-lg">
                          <p className="text-sm text-gray-700 leading-relaxed">
                            {selectedImage.caption?.[language] ||
                              selectedImage.caption?.en}
                          </p>
                        </div>
                      </div>
                    )}

                    {/* Economic Indicators */}
                    {selectedImage.indicators &&
                      selectedImage.indicators.length > 0 && (
                        <div>
                          <Label className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
                            {language === "de"
                              ? "Wirtschaftsindikatoren"
                              : "Economic Indicators"}
                          </Label>
                          <div className="mt-2 flex flex-wrap gap-1">
                            {selectedImage.indicators.map(
                              (indicator, index) => (
                                <Badge
                                  key={index}
                                  variant="outline"
                                  className="text-xs bg-blue-50 text-blue-700"
                                >
                                  {indicator.toUpperCase()}
                                </Badge>
                              ),
                            )}
                          </div>
                        </div>
                      )}

                    {/* Technical Details */}
                    <div className="space-y-3">
                      <Label className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
                        {language === "de"
                          ? "Technische Details"
                          : "Technical Details"}
                      </Label>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span className="text-gray-600">
                            {language === "de" ? "Bild-ID:" : "Image ID:"}
                          </span>
                          <span className="font-mono text-gray-800">
                            {selectedImage.id}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600">
                            {language === "de" ? "Dateiname:" : "File Name:"}
                          </span>
                          <span className="font-mono text-gray-800 break-all">
                            {selectedImage.name}
                          </span>
                        </div>
                        {selectedImage.uploadedAt && (
                          <div className="flex justify-between">
                            <span className="text-gray-600">
                              {language === "de" ? "Hochgeladen:" : "Uploaded:"}
                            </span>
                            <span className="text-gray-800">
                              {new Date(
                                selectedImage.uploadedAt,
                              ).toLocaleDateString(
                                language === "de" ? "de-DE" : "en-US",
                              )}
                            </span>
                          </div>
                        )}
                        {selectedImage.size && (
                          <div className="flex justify-between">
                            <span className="text-gray-600">
                              {language === "de" ? "Dateigröße:" : "File Size:"}
                            </span>
                            <span className="text-gray-800">
                              {formatFileSize(selectedImage.size)}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="pt-4 border-t space-y-2">
                      <Button
                        variant="outline"
                        className="w-full"
                        onClick={() => window.open(selectedImage.url, "_blank")}
                      >
                        {language === "de"
                          ? "Vollbild öffnen"
                          : "Open Full Size"}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="w-full text-gray-500"
                        onClick={() =>
                          navigator.clipboard.writeText(selectedImage.url)
                        }
                      >
                        {language === "de"
                          ? "Bild-URL kopieren"
                          : "Copy Image URL"}
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );

  // Helper functions
  function getCategoryTranslation(category: string): string {
    const translations: Record<string, string> = {
      hazard: "Gefahr",
      exposition: "Exposition",
      relevance: "Relevanz",
      risk: "Risiko",
      "risk-clusters": "Risiko-Cluster",
    };
    return translations[category] || category;
  }

  function getScenarioTranslation(scenario: string): string {
    const translations: Record<string, string> = {
      current: "Aktuell",
      conservative: "Konservativ",
      moderate: "Moderat",
      severe: "Schwerwiegend",
      none: "Keine",
      all: "Alle Szenarien",
    };
    return translations[scenario] || scenario;
  }

  function formatFileSize(bytes: number): string {
    const units = ["B", "KB", "MB", "GB"];
    let size = bytes;
    let unitIndex = 0;

    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }

    return `${size.toFixed(1)} ${units[unitIndex]}`;
  }
}
