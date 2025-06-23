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
  title: string;
  content: string;
  author: string;
  role?: string;
}

export interface StatisticsBlock {
  type: "statistics";
  title: string;
  description: string;
  stats: Array<{
    label: string;
    value: string;
    description?: string;
  }>;
}

export interface TimelineBlock {
  type: "timeline";
  title: string;
  description: string;
  events: Array<{
    year: string;
    title: string;
    description: string;
  }>;
}

export interface VisualizationBlock {
  type: "visualization";
  title: string;
  description: string;
  content: string;
  visualizationType: "map" | "chart" | "trend";
  imageCategory: string;
  imageScenario?: string;
  imageId: string;
  references: string[];
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

export interface NeuralClimateNetworkBlock {
  type: "neural-climate-network";
  title?: string;
  description?: string;
  intensity?: number;
  speed?: number;
}

export interface EarthPulseBlock {
  type: "earth-pulse";
  title?: string;
  description?: string;
  intensity?: number;
  speed?: number;
}

export interface ImpactComparisonBlock {
  type: "impact-comparison";
  title?: string;
  description?: string;
  scenarios: Array<{
    name: string;
    temperature: number;
    seaLevel: number;
    precipitation: number;
    extremeEvents: number;
  }>;
}

export interface KpiShowcaseBlock {
  type: "kpi-showcase";
  title?: string;
  description?: string;
  kpis: Array<{
    label: string;
    value: string;
    change: string;
    trend: "up" | "down";
    icon: string;
  }>;
}

export interface ClimateMetamorphosisBlock {
  type: "climate-metamorphosis";
  title?: string;
  description?: string;
  stages: Array<{
    year: number;
    title: string;
    description: string;
    data: number;
  }>;
}

export interface ClimateTimelineMinimalBlock {
  type: "climate-timeline-minimal";
  title?: string;
  description?: string;
  events: Array<{
    year: number;
    title: string;
    description: string;
  }>;
}

export interface DataStormBlock {
  type: "data-storm";
  title?: string;
  description?: string;
  intensity?: number;
  particles?: number;
}

export interface CarbonMoleculeDanceBlock {
  type: "carbon-molecule-dance";
  title?: string;
  description?: string;
  molecules?: number;
  speed?: number;
}

export interface ClimateInfographicBlock {
  type: "climate-infographic";
  title?: string;
  description?: string;
  sections: Array<{
    title: string;
    value: string;
    description: string;
    icon: string;
  }>;
}

export interface ClimateMapStaticBlock {
  type: "climate-map-static";
  title?: string;
  description?: string;
}

export interface InteractiveMapBlock {
  type: "interactive-map";
  title: string;
  description: string;
  selectedLayers: string[];
  height?: string;
  enableLayerControls?: boolean;
}

export interface Story {
  id: string;
  title: string;
  description: string;
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
  | InteractiveCalloutBlock
  | NeuralClimateNetworkBlock
  | EarthPulseBlock
  | ImpactComparisonBlock
  | KpiShowcaseBlock
  | ClimateMapStaticBlock
  | ClimateMetamorphosisBlock
  | ClimateTimelineMinimalBlock
  | DataStormBlock
  | CarbonMoleculeDanceBlock
  | ClimateInfographicBlock
  | InteractiveMapBlock;

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
  visualizations?: Visualization[];
}

export interface ImageOption {
  id: string;
  name: string;
  url: string;
  category: string;
  scenario?: string;
}
