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

export interface LanguageContent {
  heroTitle: string;
  heroDescription: string;
  dataStoryTitle: string;
  introText1: string;
  introText2: string;
  visualizations: Visualization[];
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
