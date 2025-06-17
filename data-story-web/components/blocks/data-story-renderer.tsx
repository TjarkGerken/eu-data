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
            imageCategory={block.data.imageCategory}
            imageScenario={block.data.imageScenario}
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
