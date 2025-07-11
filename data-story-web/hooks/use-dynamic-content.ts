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
    // Helper function to resolve reference IDs to full reference objects
    const resolveReferences = (block: any) => {
      // References can come from multiple sources:
      // 1. block.references (direct from database) - already full objects
      // 2. block.data.references (from admin interface) - array of IDs that need resolution
      // 3. block.references (from content) - array of string IDs that need resolution

      let referenceIds: string[] = [];

      if (
        block.references &&
        Array.isArray(block.references) &&
        block.references.length > 0
      ) {
        // Check if we have full reference objects
        if (typeof block.references[0] === "object" && block.references[0].id) {
          return block.references;
        }
        // Otherwise, they're string IDs
        referenceIds = block.references;
      }

      // Also check data.references for IDs
      if (block.data?.references && Array.isArray(block.data.references)) {
        referenceIds = [...referenceIds, ...block.data.references];
      }

      // Resolve all collected IDs to full reference objects
      if (referenceIds.length > 0) {
        const resolvedReferences = referenceIds
          .map((id: string) => {
            const fullRef = data.references?.find((ref: any) => ref.id === id);
            return fullRef || null;
          })
          .filter(Boolean); // Remove any null values

        return resolvedReferences;
      }

      return [];
    };

    const transformBlock = (block: any) => {
      // Handle specific block type transformations
      switch (block.blockType) {
        case "visualization":
          return {
            type: "visualization",
            title: block.title,
            content: block.content,
            data: {
              ...block.data, // Preserve all original data fields including isOwnSource
              references: block.data.references || [], // Use data.references, not block.references
            },
          };

        case "markdown":
          const markdownBlock = {
            type: "markdown",
            content: block.content || block.data.content || "",
            references: resolveReferences(block),
          };
          return markdownBlock;

        case "callout":
          return {
            type: "callout",
            title: block.title || block.data.title || "",
            content: block.content || block.data.content || "",
            variant: block.data.variant || "default",
            references: resolveReferences(block),
          };

        case "quote":
          return {
            type: "quote",
            content: block.data.content,
            author: block.data.author,
            role: block.data.role,
            references: resolveReferences(block),
          };

        case "statistics":
          return {
            type: "statistics",
            stats: block.data.stats,
            references: resolveReferences(block),
          };

        case "timeline":
          return {
            type: "timeline",
            events: block.data.events,
            references: resolveReferences(block),
          };

        case "animated-quote":
          return {
            type: "animated-quote",
            title: block.title || "",
            content: block.content || "",
            text: block.data.text || "",
            author: block.data.author || "",
            role: block.data.role || "",
            references: resolveReferences(block),
          };

        case "climate-dashboard":
          const resolvedRefs = resolveReferences(block);
          return {
            type: "climate-dashboard",
            title: block.title || block.data.title,
            metrics: block.data.metrics || [],
            references: resolvedRefs,
          };

        default:
          return {
            type: block.blockType,
            title: block.title || block.data.title,
            content: block.content || block.data.content,
            references: resolveReferences(block),
            ...block.data,
          };
      }
    };

    const transformedBlocks = data.blocks.map(transformBlock);

    const visualizations = data.blocks
      .filter((block: any) => block.blockType === "visualization")
      .map((block: any) => ({
        title: block.data.title || "",
        captionDe: block.data.captionDe || "",
        captionEn: block.data.captionEn || "",
        content: block.data.content || "",
        type: block.data.type || "map",
        imageCategory: block.data.imageCategory || "",
        imageScenario: block.data.imageScenario || "",
        imageIndicator: block.data.imageIndicator || "",
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
      const cacheParam = forceReload ? `&_t=${Date.now()}` : "";
      const response = await fetch(
        `/api/content?language=${language}${cacheParam}`,
      );
      if (!response.ok) {
        throw new Error("Failed to fetch content");
      }

      const contentData = await response.json();

      if (!contentData) {
        throw new Error(`Content not found for language: ${language}`);
      }

      const transformedContent = transformContentData(contentData);
      setContent(transformedContent);
    } catch (err) {
      console.error("Error loading content:", err);
      setError(err instanceof Error ? err.message : "Failed to load content");
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
      loadContent(true);
    });

    return unsubscribe;
  }, [language]);

  return { content, loading, error, reload: loadContent };
}
