import { useState, useEffect } from "react";
import { useLanguage } from "@/contexts/language-context";
import { DynamicContent } from "@/lib/types";
import { fetchContentByLanguage, ContentData } from "@/lib/content-service";
import { contentCacheService } from "@/lib/content-cache";

export function useDynamicContent() {
  const { language } = useLanguage();
  const [content, setContent] = useState<DynamicContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const transformContentData = (data: any): DynamicContent => {
    const transformBlock = (block: any) => {
      // Handle specific block type transformations
      switch (block.blockType) {
        case "visualization":
          return {
            type: "visualization",
            data: {
              title: block.data.title || "",
              description: block.data.description || "",
              content: block.data.content || "",
              type: block.data.type || "map",
              imageCategory: block.data.imageCategory || "",
              imageScenario: block.data.imageScenario || "",
              imageId: block.data.imageId || "",
              references: block.references?.map((ref: any) => ref.id) || [],
            },
          };

        case "markdown":
          console.log("Transforming markdown block:", block);
          const markdownBlock = {
            type: "markdown",
            content: block.content || block.data.content || "",
          };
          console.log("Transformed markdown block:", markdownBlock);
          return markdownBlock;

        case "callout":
          return {
            type: "callout",
            title: block.title || block.data.title || "",
            content: block.content || block.data.content || "",
            variant: block.data.variant || "default",
          };

        case "quote":
          return {
            type: "quote",
            content: block.data.content,
            author: block.data.author,
            role: block.data.role,
          };

        case "statistics":
          return {
            type: "statistics",
            stats: block.data.stats,
          };

        case "timeline":
          return {
            type: "timeline",
            events: block.data.events,
          };

        case "animated-quote":
          return {
            type: "animated-quote",
            title: block.title || "",
            content: block.content || "",
            text: block.data.text || "",
            author: block.data.author || "",
            role: block.data.role || "",
          };

        default:
          return {
            type: block.blockType,
            title: block.title || block.data.title,
            content: block.content || block.data.content,
            ...block.data,
          };
      }
    };

    const transformedBlocks = data.blocks.map(transformBlock);

    const visualizations = data.blocks
      .filter((block: any) => block.blockType === "visualization")
      .map((block: any) => ({
        title: block.data.title || "",
        description: block.data.description || "",
        content: block.data.content || "",
        type: block.data.type || "map",
        imageCategory: block.data.imageCategory || "",
        imageScenario: block.data.imageScenario || "",
        imageId: block.data.imageId || "",
        references: block.references?.map((ref: any) => ref.id) || [],
      }));

    return {
      heroTitle: data.story.heroTitle,
      heroDescription: data.story.heroDescription || "",
      dataStoryTitle: data.story.dataStoryTitle || "",
      introText1: data.story.introText1 || "",
      introText2: data.story.introText2 || "",
      blocks: transformedBlocks,
      visualizations,
      references: data.references,
    };
  };

  const loadContent = async (forceReload = false) => {
    try {
      setLoading(true);
      setError(null);

      // Add cache busting for forced reloads
      const cacheParam = forceReload ? `&_t=${Date.now()}` : '';
      const response = await fetch(`/api/content?language=${language}${cacheParam}`);
      if (!response.ok) {
        throw new Error("Failed to fetch content");
      }

      const contentData = await response.json();

      if (!contentData) {
        throw new Error(`Content not found for language: ${language}`);
      }

      console.log("Fetched content data:", contentData);
      console.log("Content blocks:", contentData.blocks);

      const transformedContent = transformContentData(contentData);
      console.log("Transformed content blocks:", transformedContent.blocks);
      setContent(transformedContent);
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
        blocks: [],
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

  // Subscribe to cache invalidation events
  useEffect(() => {
    const unsubscribe = contentCacheService.subscribe(() => {
      console.log('Content cache invalidated, reloading...');
      loadContent(true);
    });

    return unsubscribe;
  }, [language]);

  return { content, loading, error, reload: loadContent };
}
