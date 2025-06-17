import { useState, useEffect } from "react";
import { useLanguage } from "@/contexts/language-context";
import { DynamicContent } from "@/lib/types";

export function useDynamicContent() {
  const { language } = useLanguage();
  const [content, setContent] = useState<DynamicContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadContent = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch("/api/content");
      if (!response.ok) {
        throw new Error("Failed to fetch content");
      }

      const data = await response.json();
      const languageContent = data[language];

      if (!languageContent) {
        throw new Error(`Content not found for language: ${language}`);
      }

      const contentWithReferences = {
        ...languageContent,
        references: data.references || [],
      };

      setContent(contentWithReferences);
    } catch (err) {
      console.error("Error loading content:", err);
      setError(err instanceof Error ? err.message : "Failed to load content");

      const fallbackContent: DynamicContent = {
        heroTitle: "European Climate Data Analysis",
        heroDescription:
          "Exploring climate patterns and environmental changes across European regions through comprehensive data visualization and analysis.",
        dataStoryTitle: "European Climate Risk Assessment",
        introText1:
          "Climate change poses significant threats to European coastal regions through sea level rise, increased storm intensity, and changing precipitation patterns.",
        introText2:
          "This data story presents a systematic approach to climate risk assessment, integrating high-resolution spatial data, scenario modeling, and impact analysis.",
        visualizations: [
          {
            title: "Climate Hazard Risk Assessment",
            description:
              "Comprehensive analysis of climate hazards across different sea level rise scenarios showing current and projected risk levels.",
            content:
              "Our hazard assessment reveals significant variations in climate risk across European coastal regions. Under current conditions, 9.7% of the study area faces high risk.",
            type: "map",
            imageCategory: "hazard",
            imageScenario: "current",
            imageId: "current-scenario",
            references: ["1", "3"],
          },
        ],
        references: [],
      };
      setContent(fallbackContent);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadContent();
  }, [language]);

  return { content, loading, error, reload: loadContent };
}
