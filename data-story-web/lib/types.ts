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
  references?: Reference[];
}

export interface CalloutBlock {
  type: "callout";
  title: string;
  content: string;
  variant: "success" | "warning" | "info" | "error";
  references?: Reference[];
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
  data: Record<string, unknown>;
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
  references?: Reference[];
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
  gridColumns?: number;
  colorScheme?: "default" | "green" | "blue" | "purple" | "orange";
  references?: Reference[];
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
  references?: Reference[];
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
  expandedContent?: string;
  variant: "success" | "warning" | "info" | "error";
  interactive?: boolean;
  references?: Reference[];
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
  comparisons: Array<{
    category: string;
    currentValue: number;
    projectedValue: number;
    unit: string;
    severity: "low" | "medium" | "high";
  }>;
  references?: Reference[];
}

export interface KpiShowcaseBlock {
  type: "kpi-showcase";
  title?: string;
  kpis: Array<{
    title: string;
    value: string;
    unit?: string;
    trend?: "up" | "down" | "stable";
    changeValue?: string;
    color?: string;
  }>;
  gridColumns?: number;
  displayFormat?: "card" | "inline" | "badge";
  references?: Reference[];
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
  centerLat?: number;
  centerLng?: number;
  zoom?: number;
  autoFitBounds?: boolean;
  // Admin control over user-facing controls
  showLayerToggles?: boolean;
  showOpacityControls?: boolean;
  showDownloadButtons?: boolean;
  // Pre-defined layer opacities
  predefinedOpacities?: Record<string, number>;
  // Cluster groups for SLR scenarios
  enableClusterGroups?: boolean;
  clusterGroups?: Array<{
    id: string;
    name: string;
    layerIds: string[];
  }>;
}

export interface ShipMapBlock {
  type: "ship-map";
  title: string;
  description: string;
  height?: string;
  centerLat?: number;
  centerLng?: number;
  zoom?: number;
  seamarkOpacity?: number;
  enableSeamarkLayer?: boolean;
  tileServerOption?: "openseamap" | "hybrid";
  portFocus?: "rotterdam" | "groningen" | "amsterdam" | "full" | "custom";
  showControls?: boolean;
  // Railway overlay options
  enableRailwayLayer?: boolean;
  railwayOpacity?: number;
  railwayStyle?: "standard" | "signals" | "maxspeed";
  // Admin control over user-facing controls
  showPortFocusControl?: boolean;
  showMapStyleControl?: boolean;
  showSeamarkLayerControl?: boolean;
  showSeamarkOpacityControl?: boolean;
  showRailwayLayerControl?: boolean;
  showRailwayStyleControl?: boolean;
  showRailwayOpacityControl?: boolean;
}

export interface InfrastructureMapBlock {
  type: "infrastructure-map";
  title: string;
  description: string;
  height?: string;
  centerLat?: number;
  centerLng?: number;
  zoom?: number;
  seamarkOpacity?: number;
  enableSeamarkLayer?: boolean;
  tileServerOption?: "openseamap" | "hybrid";
  portFocus?: "rotterdam" | "groningen" | "amsterdam" | "full" | "custom" | "schiphol" | "sloehaven";
  showControls?: boolean;
  // Railway overlay options
  enableRailwayLayer?: boolean;
  railwayOpacity?: number;
  railwayStyle?: "standard" | "signals" | "maxspeed";
  // Admin control over user-facing controls
  showPortFocusControl?: boolean;
  showMapStyleControl?: boolean;
  showSeamarkLayerControl?: boolean;
  showSeamarkOpacityControl?: boolean;
  showRailwayLayerControl?: boolean;
  showRailwayStyleControl?: boolean;
  showRailwayOpacityControl?: boolean;
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
  | InteractiveMapBlock
  | ShipMapBlock
  | InfrastructureMapBlock;

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
  caption?: { en: string; de: string };
  alt?: { en: string; de: string };
  indicators?: string[];
  uploadedAt?: string;
  size?: number;
}
