"use client";

import { DataStoryBlock } from "@/lib/types";
import { MarkdownBlock } from "./markdown-block";
import { CalloutBlock } from "./callout-block";
import { QuoteBlock } from "./quote-block";
import { StatisticsBlock } from "./statistics-block";
import { TimelineBlock } from "./timeline-block";
import { VisualizationCard } from "@/components/visualization-card";
import { AnimatedQuoteBlock } from "./animated-quote-block";
import { AnimatedStatisticsBlock } from "./animated-statistics-block";
import { ClimateTimelineBlock } from "./climate-timeline-block";
import { ClimateDashboardBlock } from "./climate-dashboard-block";
import { TemperatureSpiralBlock } from "./temperature-spiral-block";
import { InteractiveCalloutBlock } from "./interactive-callout-block";
import NeuralClimateNetworkBlockComponent from "./neural-climate-network-block";
import EarthPulseBlockComponent from "./earth-pulse-block";
import ImpactComparisonBlockComponent from "./impact-comparison-block";
import KpiShowcaseBlockComponent from "./kpi-showcase-block";
import ClimateMapStaticBlockComponent from "./climate-map-static-block";
import ClimateMetamorphosisBlockComponent from "./climate-metamorphosis-block";
import ClimateTimelineMinimalBlockComponent from "./climate-timeline-minimal-block";
import DataStormBlockComponent from "./data-storm-block";
import CarbonMoleculeDanceBlockComponent from "./carbon-molecule-dance-block";
import ClimateInfographicBlockComponent from "./climate-infographic-block";

interface DataStoryRendererProps {
  blocks: DataStoryBlock[];
}

export function DataStoryRenderer({ blocks }: DataStoryRendererProps) {
  const renderBlock = (block: DataStoryBlock, index: number) => {
    switch (block.type) {
      case "markdown":
        return <MarkdownBlock key={index} content={block.content} />;

      case "callout":
        return (
          <CalloutBlock
            key={index}
            title={block.title}
            content={block.content}
            variant={block.variant}
          />
        );

      case "quote":
        return (
          <QuoteBlock
            key={index}
            content={block.content}
            author={block.author}
            role={block.role}
          />
        );

      case "statistics":
        return <StatisticsBlock key={index} stats={block.stats} />;

      case "timeline":
        return <TimelineBlock key={index} events={block.events} />;

      case "visualization":
        return (
          <VisualizationCard
            key={index}
            title={block.data.title}
            description={block.data.description}
            imageCategory={
              block.data.imageCategory as
                | "risk"
                | "exposition"
                | "hazard"
                | "combined"
                | undefined
            }
            imageScenario={
              block.data.imageScenario as "current" | "severe" | undefined
            }
            imageId={block.data.imageId}
            content={block.data.content}
            type={block.data.type}
            references={block.data.references}
          />
        );

      case "animated-quote":
        return (
          <AnimatedQuoteBlock
            key={index}
            text={block.text}
            author={block.author}
            role={block.role}
          />
        );

      case "animated-statistics":
        return (
          <AnimatedStatisticsBlock
            key={index}
            title={block.title}
            description={block.description}
            stats={block.stats}
          />
        );

      case "climate-timeline":
        return (
          <ClimateTimelineBlock
            key={index}
            title={block.title}
            description={block.description}
            events={block.events}
          />
        );

      case "climate-dashboard":
        return (
          <ClimateDashboardBlock
            key={index}
            title={block.title}
            description={block.description}
            metrics={block.metrics}
          />
        );

      case "temperature-spiral":
        return (
          <TemperatureSpiralBlock
            key={index}
            title={block.title}
            description={block.description}
            startYear={block.startYear}
            endYear={block.endYear}
            rotations={block.rotations}
          />
        );

      case "interactive-callout":
        return (
          <InteractiveCalloutBlock
            key={index}
            title={block.title}
            content={block.content}
            variant={block.variant}
            interactive={block.interactive}
          />
        );

      case "neural-climate-network":
        return <NeuralClimateNetworkBlockComponent key={index} block={block} />;

      case "earth-pulse":
        return <EarthPulseBlockComponent key={index} block={block} />;

      case "impact-comparison":
        return <ImpactComparisonBlockComponent key={index} block={block} />;

      case "kpi-showcase":
        return <KpiShowcaseBlockComponent key={index} block={block} />;

      case "climate-map-static":
        return <ClimateMapStaticBlockComponent key={index} block={block} />;

      case "climate-metamorphosis":
        return <ClimateMetamorphosisBlockComponent key={index} block={block} />;

      case "climate-timeline-minimal":
        return (
          <ClimateTimelineMinimalBlockComponent key={index} block={block} />
        );

      case "data-storm":
        return <DataStormBlockComponent key={index} block={block} />;

      case "carbon-molecule-dance":
        return <CarbonMoleculeDanceBlockComponent key={index} block={block} />;

      case "climate-infographic":
        return <ClimateInfographicBlockComponent key={index} block={block} />;

      default:
        return null;
    }
  };

  return (
    <div className="space-y-8">
      {blocks.map((block, index) => renderBlock(block, index))}
    </div>
  );
}
