"use client";

import { useMemo } from "react";
import { DataStoryBlock, Reference } from "@/lib/types";
import { MarkdownBlock } from "./markdown-block";
import { CalloutBlock } from "./callout-block";

import { VisualizationCard } from "@/components/visualization-card";
import { InteractiveMap } from "@/components/interactive-map";
import { ShipMap } from "@/components/ship-map";
import { AnimatedQuoteBlock } from "./animated-quote-block";
import { AnimatedStatisticsBlock } from "./animated-statistics-block";
import { ClimateDashboardBlock } from "./climate-dashboard-block";
import { InteractiveCalloutBlock } from "./interactive-callout-block";
import ImpactComparisonBlockComponent from "./impact-comparison-block";
import KpiShowcaseBlockComponent from "./kpi-showcase-block";
import { GlobalCitationProvider } from "@/contexts/global-citation-context";
import { processGlobalCitations } from "@/lib/global-citation-processor";

interface DataStoryRendererProps {
  blocks: DataStoryBlock[];
  globalReferences: Reference[];
}

export function DataStoryRenderer({
  blocks,
  globalReferences,
}: DataStoryRendererProps) {
  // Process global citations once for all blocks, using the global references list
  const globalCitationData = useMemo(() => {
    return processGlobalCitations(blocks || [], globalReferences || []);
  }, [blocks, globalReferences]);
  const renderBlock = (block: DataStoryBlock, index: number) => {
    switch (block.type) {
      case "markdown":
        return (
          <MarkdownBlock
            key={index}
            content={block.content}
            references={block.references}
          />
        );

      case "callout":
        return (
          <CalloutBlock
            key={index}
            title={block.title}
            content={block.content}
            variant={block.variant}
            references={block.references}
          />
        );

      case "visualization":
        return (
          <VisualizationCard
            key={index}
            title={block.data.title as string}
            captionEn={block.data.captionEn as string}
            captionDe={block.data.captionDe as string}
            imageCategory={
              block.data.imageCategory as
                | "hazard"
                | "exposition"
                | "relevance"
                | "risk"
                | "risk-clusters"
                | undefined
            }
            imageScenario={
              block.data.imageScenario as
                | "current"
                | "conservative"
                | "moderate"
                | "severe"
                | "none"
                | "all"
                | undefined
            }
            imageId={block.data.imageId as string}
            content={block.data.content as string}
            type={block.data.type as "map" | "chart" | "trend" | "gauge"}
            references={block.data.references as string[]}
          />
        );

      case "animated-quote":
        return (
          <AnimatedQuoteBlock
            key={index}
            text={block.text}
            author={block.author}
            role={block.role}
            references={block.references}
          />
        );

      case "animated-statistics":
        return (
          <AnimatedStatisticsBlock
            key={index}
            title={block.title}
            description={block.description}
            stats={block.stats}
            gridColumns={block.gridColumns}
            colorScheme={block.colorScheme}
            references={block.references}
          />
        );

      case "climate-dashboard":
        return (
          <ClimateDashboardBlock
            key={index}
            title={block.title}
            metrics={block.metrics}
            references={block.references}
          />
        );

      case "interactive-callout":
        return (
          <InteractiveCalloutBlock
            key={index}
            title={block.title}
            content={block.content}
            expandedContent={block.expandedContent}
            variant={block.variant}
            interactive={block.interactive}
            references={block.references}
          />
        );

      case "impact-comparison":
        return <ImpactComparisonBlockComponent key={index} block={block} />;

      case "kpi-showcase":
        return <KpiShowcaseBlockComponent key={index} block={block} />;

      case "interactive-map":
        return (
          <InteractiveMap
            key={index}
            title={block.title}
            description={block.description}
            selectedLayers={block.selectedLayers || []}
            height={block.height || "600px"}
            enableLayerControls={block.enableLayerControls !== false}
            centerLat={block.centerLat || 52.1326}
            centerLng={block.centerLng || 5.2913}
            zoom={block.zoom || 8}
            autoFitBounds={block.autoFitBounds || false}
            showLayerToggles={block.showLayerToggles !== false}
            showOpacityControls={block.showOpacityControls !== false}
            showDownloadButtons={block.showDownloadButtons !== false}
            predefinedOpacities={block.predefinedOpacities || {}}
          />
        );

      case "ship-map":
        return (
          <ShipMap
            key={index}
            title={block.title}
            description={block.description}
            height={block.height || "600px"}
            centerLat={block.centerLat}
            centerLng={block.centerLng}
            zoom={block.zoom}
            seamarkOpacity={block.seamarkOpacity || 80}
            enableSeamarkLayer={block.enableSeamarkLayer !== false}
            tileServerOption={block.tileServerOption || "openseamap"}
            portFocus={block.portFocus || "rotterdam"}
            showControls={block.showControls !== false}
            enableRailwayLayer={block.enableRailwayLayer || false}
            railwayOpacity={block.railwayOpacity || 70}
            railwayStyle={block.railwayStyle || "standard"}
            showPortFocusControl={block.showPortFocusControl !== false}
            showMapStyleControl={block.showMapStyleControl !== false}
            showSeamarkLayerControl={block.showSeamarkLayerControl !== false}
            showSeamarkOpacityControl={
              block.showSeamarkOpacityControl !== false
            }
            showRailwayLayerControl={block.showRailwayLayerControl !== false}
            showRailwayStyleControl={block.showRailwayStyleControl !== false}
            showRailwayOpacityControl={
              block.showRailwayOpacityControl !== false
            }
          />
        );

      default:
        return null;
    }
  };

  if (!blocks || blocks.length === 0) {
    return (
      <div className="space-y-8">
        <div className="text-center text-muted-foreground py-8">
          No content blocks available.
        </div>
      </div>
    );
  }

  return (
    <GlobalCitationProvider globalCitationData={globalCitationData}>
      <div className="space-y-8">
        {blocks.map((block, index) => renderBlock(block, index))}
      </div>
    </GlobalCitationProvider>
  );
}
