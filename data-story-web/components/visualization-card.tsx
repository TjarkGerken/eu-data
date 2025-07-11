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
import { useGlobalCitation } from "@/contexts/global-citation-context";
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
  isOwnSource?: boolean;
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
  isOwnSource = false,
}: VisualizationCardProps) {
  const Icon = iconMap[type];
  const { t, language } = useLanguage();
  const { globalCitationData } = useGlobalCitation();
  const [captionEn, setCaptionEn] = useState<string | undefined>(undefined);
  const [captionDe, setCaptionDe] = useState<string | undefined>(undefined);

  const handleCitationClick = (referenceId: string) => {
    const event = new CustomEvent("highlightReference", {
      detail: referenceId,
    });
    window.dispatchEvent(event);
  };

  const resolveReferenceTitle = (refId: string) => {
    if (globalCitationData && globalCitationData.orderedReferences) {
      const ref = globalCitationData.orderedReferences.find(
        (r) => r.id === refId,
      );
      return ref ? ref.title : refId;
    }
    return refId;
  };

  return (
    <Card className="w-full mb-8">
      <CardHeader>
        <div className="flex items-center space-x-2">
          <Icon className="h-6 w-6 text-[#2d5a3d]" />
          <CardTitle className="text-2xl">{title}</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="w-full bg-gradient-to-br from-[#2d5a3d]/10 to-[#c4a747]/10 rounded-lg overflow-hidden">
          {imageCategory ? (
            <ClimateImage
              category={imageCategory}
              scenario={imageScenario}
              id={imageId}
              alt={title}
              className="w-full h-auto"
              priority={false}
              fill={false}
              width={800}
              height={600}
              onMetadataLoaded={(metadata) => {
                setCaptionEn(metadata?.caption?.en);
                setCaptionDe(metadata?.caption?.de);
              }}
            />
          ) : imagePath ? (
            <ClimateImage
              category="risk"
              alt={title}
              className="w-full h-auto"
              priority={false}
              fill={false}
              width={800}
              height={600}
            />
          ) : (
            <div className="aspect-[16/9] flex items-center justify-center text-center text-muted-foreground">
              <div>
                <Icon className="h-16 w-16 mx-auto mb-4 opacity-50" />
                <p className="text-lg font-medium">
                  {t.visualizationPlaceholder}
                </p>
                <p className="text-sm">
                  Interactive {type} {t.interactiveWillRender}
                </p>
              </div>
            </div>
          )}
        </div>

        {captionDe && (
          <CardDescription className="text-base">
            {language === "de" ? captionDe : captionEn}
          </CardDescription>
        )}

        <div className="prose prose-lg max-w-none">
          <p className="text-muted-foreground leading-relaxed">{content}</p>
        </div>

        <div className="border-t pt-4">
          <h4 className="text-sm font-medium mb-2">{t.referencedSources}</h4>
          <div className="flex flex-wrap gap-2">
            {isOwnSource && (
              <Badge
                variant="default"
                className="text-sm bg-[#2d5a3d] text-white"
              >
                {language === "de" ? "Eigene Darstellung" : "Own Source"}
              </Badge>
            )}
            {references.map((ref, index) => {
              const referenceTitle = resolveReferenceTitle(ref);
              return (
                <Badge
                  key={index}
                  variant="outline"
                  className="text-sm cursor-pointer hover:bg-[#2d5a3d]/10 transition-colors"
                  onClick={() => handleCitationClick(ref)}
                  title={`View reference: ${referenceTitle}`}
                >
                  {referenceTitle}
                </Badge>
              );
            })}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
