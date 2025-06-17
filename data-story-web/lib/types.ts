export interface Reference {
  id: string;
  title: string;
  authors: string[];
  year: number;
  journal?: string;
  url?: string;
  type: "journal" | "report" | "dataset" | "book";
}

export interface Visualization {
  title: string;
  description: string;
  content: string;
  type: "map" | "chart" | "trend";
  imageCategory: string;
  imageScenario?: string;
  imageId: string;
  references: string[];
}

export interface MarkdownBlock {
  type: "markdown";
  content: string;
}

export interface CalloutBlock {
  type: "callout";
  title: string;
  content: string;
  variant: "success" | "warning" | "info" | "error";
}

export interface QuoteBlock {
  type: "quote";
  content: string;
  author: string;
  role?: string;
}

export interface StatisticsBlock {
  type: "statistics";
  stats: Array<{
    label: string;
    value: string;
    description?: string;
  }>;
}

export interface TimelineBlock {
  type: "timeline";
  events: Array<{
    year: string;
    title: string;
    description: string;
  }>;
}

export interface VisualizationBlock {
  type: "visualization";
  data: Visualization;
}

export interface AnimatedQuoteBlock {
  type: "animated-quote";
  text: string;
  author: string;
  role?: string;
}

export interface AnimatedStatisticsBlock {
  type: "animated-statistics";
  title?: string;
  description?: string;
  stats: Array<{
    icon: string;
    value: string;
    label: string;
    change?: string;
    trend?: "up" | "down";
    color: string;
  }>;
}

export interface ClimateTimelineBlock {
  type: "climate-timeline";
  title?: string;
  description?: string;
  events: Array<{
    year: number;
    title: string;
    description: string;
    type: "temperature" | "precipitation" | "policy" | "extreme";
    icon: string;
    color: string;
  }>;
}

export interface ClimateDashboardBlock {
  type: "climate-dashboard";
  title?: string;
  description?: string;
  metrics: Array<{
    title: string;
    value: string;
    change: string;
    trend: "up" | "down";
    status: "success" | "warning" | "danger";
    progress: number;
    target: string;
    description: string;
  }>;
}

export interface TemperatureSpiralBlock {
  type: "temperature-spiral";
  title?: string;
  description?: string;
  startYear?: number;
  endYear?: number;
  rotations?: number;
}

export interface InteractiveCalloutBlock {
  type: "interactive-callout";
  title: string;
  content: string;
  variant: "success" | "warning" | "info" | "error";
  interactive?: boolean;
}

export type DataStoryBlock =
  | MarkdownBlock
  | CalloutBlock
  | QuoteBlock
  | StatisticsBlock
  | TimelineBlock
  | VisualizationBlock
  | AnimatedQuoteBlock
  | AnimatedStatisticsBlock
  | ClimateTimelineBlock
  | ClimateDashboardBlock
  | TemperatureSpiralBlock
  | InteractiveCalloutBlock;

export interface LanguageContent {
  heroTitle: string;
  heroDescription: string;
  dataStoryTitle: string;
  introText1: string;
  introText2: string;
  blocks: DataStoryBlock[];
}

export interface ContentData {
  references: Reference[];
  en: LanguageContent;
  de: LanguageContent;
}

export interface DynamicContent extends LanguageContent {
  references?: Reference[];
}

export interface ImageOption {
  id: string;
  name: string;
  url: string;
  category: string;
  scenario?: string;
}
