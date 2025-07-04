"use client";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { BarChart3, TrendingUp, Globe, Thermometer } from "lucide-react";
import { useLanguage } from "@/contexts/language-context";
import ClimateImage from "@/components/climate-image";
import { ImageCategory, ImageScenario } from "@/lib/blob-config";
import { useState } from "react";

interface VisualizationCardProps {
  title: string;
  content: string;
  type: "chart" | "map" | "trend" | "gauge";
  references: string[];
  imagePath?: string;
  imageCategory?: ImageCategory;
  imageScenario?: ImageScenario;
  imageId?: string;
}

const iconMap = {
  chart: BarChart3,
  map: Globe,
  trend: TrendingUp,
  gauge: Thermometer,
};

export function VisualizationCard({
  title,
  content,
  type,
  references,
  imagePath,
  imageCategory,
  imageScenario,
  imageId,
}: VisualizationCardProps) {
  const Icon = iconMap[type];
  const { t, language } = useLanguage();
  const [captionEn, setCaptionEn] = useState<string | undefined>(undefined);
  const [captionDe, setCaptionDe] = useState<string | undefined>(undefined);

  return (
    <Card className="w-full mb-8">
      <CardHeader>
        <div className="flex items-center space-x-2">
          <Icon className="h-6 w-6 text-[#2d5a3d]" />
          <CardTitle className="text-2xl">{title}</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Visualization Area */}
        <div className="aspect-[16/9] bg-gradient-to-br from-[#2d5a3d]/10 to-[#c4a747]/10 rounded-lg flex items-center justify-center overflow-hidden">
          {imageCategory ? (
            <div className="relative w-full h-full">
              <ClimateImage
                category={imageCategory}
                scenario={imageScenario}
                id={imageId}
                alt={title}
                className="object-contain"
                priority={false}
                onMetadataLoaded={(metadata) => {
                  setCaptionEn(metadata?.caption?.en);
                  setCaptionDe(metadata?.caption?.de);
                }}
              />
            </div>
          ) : imagePath ? (
            <div className="relative w-full h-full">
              <ClimateImage
                category="risk"
                alt={title}
                className="object-contain"
                priority={false}
              />
            </div>
          ) : (
            <div className="text-center text-muted-foreground">
              <Icon className="h-16 w-16 mx-auto mb-4 opacity-50" />
              <p className="text-lg font-medium">
                {t.visualizationPlaceholder}
              </p>
              <p className="text-sm">
                Interactive {type} {t.interactiveWillRender}
              </p>
            </div>
          )}
        </div>

        {captionEn && (
          <CardDescription className="text-base">
            {language === "de" ? captionDe || captionEn : captionEn}
          </CardDescription>
        )}

        {/* Content Text */}
        <div className="prose prose-lg max-w-none">
          <p className="text-muted-foreground leading-relaxed">{content}</p>
        </div>

        {/* References */}
        <div className="border-t pt-4">
          <h4 className="text-sm font-medium mb-2">{t.referencedSources}</h4>
          <div className="flex flex-wrap gap-2">
            {references.map((ref, index) => (
              <Badge
                key={index}
                variant="outline"
                className="text-sm cursor-pointer hover:bg-[#2d5a3d]/10"
              >
                [{ref}]
              </Badge>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
