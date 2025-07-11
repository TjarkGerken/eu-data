export type Language = "en" | "de";

export interface Translation {
  // Header
  dataStories: string;
  story: string;
  visualizations: string;
  gallery: string;
  bibliography: string;

  // Video Section
  heroTitle: string;
  heroDescription: string;
  introVideo: string;
  videoOverview: string;

  // Main Content
  dataStoryTitle: string;
  introText1: string;
  introText2: string;

  // Technical Section
  technicalApproachTitle: string;
  technicalApproachDesc: string;
  methodologyTitle: string;
  methodologyContent: string;
  dataProcessingTitle: string;
  dataProcessingContent: string;
  visualizationTechTitle: string;
  visualizationTechContent: string;
  repositoriesTitle: string;
  repositoriesDesc: string;
  sourceCode: string;
  modelsData: string;

  // Visualizations
  hazardAssessmentTitle: string;
  hazardAssessmentDesc: string;
  hazardAssessmentContent: string;

  seaLevelRiseCurrentTitle: string;
  seaLevelRiseCurrentDesc: string;
  seaLevelRiseCurrentContent: string;

  seaLevelRiseSevereTitle: string;
  seaLevelRiseSevereDesc: string;
  seaLevelRiseSevereContent: string;

  expositionLayerTitle: string;
  expositionLayerDesc: string;
  expositionLayerContent: string;

  freightExpositionTitle: string;
  freightExpositionDesc: string;
  freightExpositionContent: string;

  floodRiskScenariosTitle: string;
  floodRiskScenariosDesc: string;
  floodRiskScenariosContent: string;

  // Narrative Sections
  waterCycleTitle: string;
  waterCycleContent: string;
  economicTransformationTitle: string;
  economicTransformationContent: string;
  lookingForwardTitle: string;
  lookingForwardContent1: string;
  lookingForwardContent2: string;

  // References
  references: string;
  referencesDesc: string;
  viewSource: string;
  referencedSources: string;

  // Loading Warning Dialog
  loadingWarningTitle: string;
  loadingWarningMessage: string;
  loadingWarningUnderstand: string;
  loadingWarningDontShowAgain: string;

  // Common
  visualizationPlaceholder: string;
  interactiveWillRender: string;
  copyright: string;
}

export const translations: Record<Language, Translation> = {
  en: {
    // Header
    dataStories: "Data Stories",
    story: "Story",
    visualizations: "Visualizations",
    gallery: "Gallery",
    bibliography: "Bibliography",

    // Video Section
    heroTitle: "European Climate Data Analysis",
    heroDescription:
      "Exploring climate patterns and environmental changes across European regions through comprehensive data visualization and analysis.",
    introVideo: "Introduction Video",
    videoOverview: "Climate Data Story Overview",

    // Main Content
    dataStoryTitle: "European Climate Risk Assessment",
    introText1:
      "Climate change poses significant threats to European coastal regions through sea level rise, increased storm intensity, and changing precipitation patterns. Our comprehensive risk assessment framework combines hazard analysis, exposure mapping, and vulnerability assessment to quantify climate risks across different scenarios and inform adaptation planning.",
    introText2:
      "This data story presents a systematic approach to climate risk assessment, integrating high-resolution spatial data, scenario modeling, and impact analysis. Each visualization below demonstrates different components of our risk assessment methodology, providing decision-makers with the tools needed to understand and address climate vulnerabilities in their regions.",

    // Technical Section
    technicalApproachTitle: "Technical Approach & Methodology",
    technicalApproachDesc:
      "Understanding the data processing pipeline and visualization techniques used in this analysis",
    methodologyTitle: "Data Collection & Processing",
    methodologyContent:
      "Our analysis combines multiple authoritative data sources including ERA5 reanalysis data from Copernicus Climate Change Service, temperature records from national meteorological services, and economic indicators from Eurostat. Data preprocessing involved quality control, temporal alignment, and spatial interpolation using Python's scientific computing stack including pandas, xarray, and scikit-learn.",
    dataProcessingTitle: "Statistical Analysis",
    dataProcessingContent:
      "Climate trends were calculated using robust statistical methods including Mann-Kendall trend tests and Sen's slope estimators to account for non-normal distributions. Anomalies were computed relative to the 1991-2020 climatological baseline, following WMO guidelines. Uncertainty quantification was performed using bootstrap resampling and ensemble methods.",
    visualizationTechTitle: "Visualization Framework",
    visualizationTechContent:
      "Interactive visualizations were built using D3.js and Observable Plot for web-native interactivity. Maps utilize Leaflet with custom climate data overlays, while time series charts employ responsive design principles. All visualizations follow accessibility guidelines with proper color schemes for colorblind users and screen reader compatibility.",
    repositoriesTitle: "Code & Data Repositories",
    repositoriesDesc: "Access the complete analysis pipeline and datasets",
    sourceCode: "Source Code",
    modelsData: "Models & Data",

    // Visualizations
    hazardAssessmentTitle: "Climate Hazard Risk Assessment",
    hazardAssessmentDesc:
      "Comprehensive analysis of climate hazards across different sea level rise scenarios showing current and projected risk levels.",
    hazardAssessmentContent:
      "Our hazard assessment reveals significant variations in climate risk across European coastal regions. Under current conditions, 9.7% of the study area faces high risk, with moderate and low risk areas covering 5.4% and 4.1% respectively. The analysis shows how risk escalates dramatically with sea level rise - under a severe 3-meter scenario, high-risk areas increase to 17.5%, demonstrating the urgent need for adaptation planning and risk mitigation strategies.",

    seaLevelRiseCurrentTitle: "Current Sea Level Risk Distribution",
    seaLevelRiseCurrentDesc:
      "Current baseline risk assessment showing today's vulnerability to sea level impacts across European coastal areas.",
    seaLevelRiseCurrentContent:
      "The current scenario assessment provides a baseline understanding of today's coastal vulnerability. With 0 meters of additional sea level rise, we observe concentrated risk areas primarily in low-lying coastal plains and river deltas. High-risk zones currently cover 8,635 km² (9.7% of the total area), with mean risk levels at 0.115. This baseline data is crucial for understanding how climate change will amplify existing vulnerabilities.",

    seaLevelRiseSevereTitle: "Severe Sea Level Rise Impact Assessment",
    seaLevelRiseSevereDesc:
      "Projected impacts under a severe 3-meter sea level rise scenario showing dramatically increased risk exposure.",
    seaLevelRiseSevereContent:
      "Under the severe sea level rise scenario (+3m), the transformation of risk landscapes is dramatic. High-risk areas expand to 15,556 km² (17.5% of total area), nearly doubling from current levels. The mean risk increases to 0.168, while maximum risk reaches 0.908. This scenario highlights the critical importance of immediate climate action and comprehensive adaptation strategies to protect vulnerable coastal communities and infrastructure.",

    expositionLayerTitle: "Coastal Infrastructure Exposition",
    expositionLayerDesc:
      "Analysis of exposed infrastructure, settlements, and economic assets in coastal zones vulnerable to climate impacts.",
    expositionLayerContent:
      "The exposition layer reveals the distribution of valuable assets at risk from climate hazards. This includes residential areas, commercial districts, transportation networks, and critical infrastructure located in vulnerable coastal zones. Understanding exposition patterns is essential for prioritizing protection measures and informing spatial planning decisions. The analysis shows concentrated exposition in major coastal cities and industrial areas, where both population density and economic value are highest.",

    freightExpositionTitle: "Maritime Transport Vulnerability",
    freightExpositionDesc:
      "Assessment of freight transport networks and port infrastructure exposure to climate-related hazards.",
    freightExpositionContent:
      "Maritime freight systems face increasing vulnerability to climate hazards, with major European ports and shipping routes exposed to sea level rise, storm surge, and extreme weather events. The analysis reveals critical bottlenecks in the freight network where climate impacts could disrupt European supply chains. Port infrastructure, loading facilities, and connecting transport networks require urgent adaptation measures to maintain operational continuity and economic stability.",

    floodRiskScenariosTitle: "Comparative Flood Risk Analysis",
    floodRiskScenariosDesc:
      "Comparative analysis of flood risk levels across different climate scenarios showing relative risk distribution patterns.",
    floodRiskScenariosContent:
      "The comparative flood risk analysis demonstrates how risk profiles evolve across different climate scenarios. The visualization shows relative risk levels ranging from conservative (1m SLR) to severe (3m SLR) scenarios, providing decision-makers with a clear understanding of how risk escalates with climate change. This information is vital for developing adaptive management strategies and informing long-term infrastructure planning decisions.",

    // Narrative Sections
    waterCycleTitle: "Coastal Vulnerability Assessment",
    waterCycleContent:
      "Coastal regions across Europe face unprecedented challenges from rising sea levels and increased storm intensity. The combination of physical exposure to marine hazards and high concentrations of valuable infrastructure creates complex risk scenarios that require sophisticated assessment and management approaches. Understanding these vulnerabilities is essential for developing effective adaptation strategies.",

    economicTransformationTitle: "Risk-Based Adaptation Planning",
    economicTransformationContent:
      "The integration of comprehensive risk assessment into policy and planning frameworks represents a fundamental shift in how Europe approaches climate adaptation. By quantifying risks across different scenarios, decision-makers can prioritize investments in protection measures, develop early warning systems, and implement nature-based solutions that provide multiple benefits for coastal communities and ecosystems.",

    lookingForwardTitle: "Looking Forward",
    lookingForwardContent1:
      "The data presented in this story reveals both the urgency of climate action and the remarkable progress Europe has made in addressing climate change. While challenges remain significant, particularly in adaptation and resilience building, the trajectory toward a sustainable future is clear.",
    lookingForwardContent2:
      "Continued monitoring, analysis, and data-driven decision making will be essential as Europe navigates the complex challenges of the 21st century. The visualizations and insights presented here represent just the beginning of an ongoing story of transformation, adaptation, and hope.",

    // References
    references: "References",
    referencesDesc: "Bibliography and data sources used in this analysis",
    viewSource: "View Source",
    referencedSources: "Referenced Sources:",

    // Loading Warning Dialog
    loadingWarningTitle: "Loading Performance Notice",
    loadingWarningMessage: "Due to the high complexity of climate data visualizations and interactive maps, loading times may be extended, especially with slower network connections. Thank you for your patience.",
    loadingWarningUnderstand: "I Understand",
    loadingWarningDontShowAgain: "Don't show again",

    // Common
    visualizationPlaceholder: "Visualization Placeholder",
    interactiveWillRender: "will be rendered here",
    copyright: "All rights reserved.",
  },

  de: {
    // Header
    dataStories: "Datengeschichten",
    story: "Geschichte",
    visualizations: "Visualisierungen",
    gallery: "Galerie",
    bibliography: "Bibliographie",

    // Video Section
    heroTitle: "Europäische Klimadatenanalyse",
    heroDescription:
      "Erforschung von Klimamustern und Umweltveränderungen in europäischen Regionen durch umfassende Datenvisualisierung und -analyse.",
    introVideo: "Einführungsvideo",
    videoOverview: "Klimadatengeschichte Überblick",

    // Main Content
    dataStoryTitle: "Europäische Klimarisiko-Bewertung",
    introText1:
      "Der Klimawandel stellt erhebliche Bedrohungen für europäische Küstenregionen durch Meeresspiegelanstieg, erhöhte Sturmintensität und sich verändernde Niederschlagsmuster dar. Unser umfassendes Risikobewertungsrahmen kombiniert Gefahrenanalyse, Expositionskartierung und Verwundbarkeitsbeurteilung, um Klimarisiken bei verschiedenen Szenarien zu quantifizieren und Anpassungsplanung zu informieren.",
    introText2:
      "Diese Datengeschichte präsentiert einen systematischen Ansatz zur Klimarisikobewertung, der hochauflösende räumliche Daten, Szenario-Modellierung und Auswirkungsanalyse integriert. Jede Visualisierung unten demonstriert verschiedene Komponenten unserer Risikobewertungsmethodik und bietet Entscheidungsträgern die Werkzeuge, die benötigt werden, um Klimaverwundbarkeiten in ihren Regionen zu verstehen und anzugehen.",

    // Technical Section
    technicalApproachTitle: "Technischer Ansatz & Methodik",
    technicalApproachDesc:
      "Verständnis der Datenverarbeitungspipeline und Visualisierungstechniken in dieser Analyse",
    methodologyTitle: "Datensammlung & Verarbeitung",
    methodologyContent:
      "Unsere Analyse kombiniert mehrere autoritative Datenquellen einschließlich ERA5-Reanalysedaten vom Copernicus Climate Change Service, Temperaturaufzeichnungen von nationalen meteorologischen Diensten und Wirtschaftsindikatoren von Eurostat. Die Datenvorverarbeitung umfasste Qualitätskontrolle, zeitliche Ausrichtung und räumliche Interpolation mit Pythons wissenschaftlichem Computing-Stack einschließlich pandas, xarray und scikit-learn.",
    dataProcessingTitle: "Statistische Analyse",
    dataProcessingContent:
      "Klimatrends wurden mit robusten statistischen Methoden berechnet, einschließlich Mann-Kendall-Trendtests und Sen's Slope-Schätzern, um nicht-normale Verteilungen zu berücksichtigen. Anomalien wurden relativ zur klimatologischen Basislinie 1991-2020 berechnet, gemäß WMO-Richtlinien. Unsicherheitsquantifizierung wurde mit Bootstrap-Resampling und Ensemble-Methoden durchgeführt.",
    visualizationTechTitle: "Visualisierungs-Framework",
    visualizationTechContent:
      "Interaktive Visualisierungen wurden mit D3.js und Observable Plot für web-native Interaktivität erstellt. Karten nutzen Leaflet mit benutzerdefinierten Klimadaten-Overlays, während Zeitreihendiagramme responsive Design-Prinzipien verwenden. Alle Visualisierungen folgen Barrierefreiheitsrichtlinien mit geeigneten Farbschemata für farbenblinde Benutzer und Screenreader-Kompatibilität.",
    repositoriesTitle: "Code & Daten-Repositories",
    repositoriesDesc:
      "Zugang zur vollständigen Analysepipeline und Datensätzen",
    sourceCode: "Quellcode",
    modelsData: "Modelle & Daten",

    // Visualizations
    hazardAssessmentTitle: "Klimarisiko-Gefährdungsbeurteilung",
    hazardAssessmentDesc:
      "Umfassende Analyse von Klimagefahren bei verschiedenen Meeresspiegelanstieg-Szenarien mit aktuellen und prognostizierten Risikoniveaus.",
    hazardAssessmentContent:
      "Unsere Gefährdungsbeurteilung zeigt erhebliche Variationen des Klimarisikos in europäischen Küstenregionen. Unter aktuellen Bedingungen stehen 9,7% des Untersuchungsgebiets vor hohem Risiko, wobei moderate und niedrige Risikogebiete 5,4% bzw. 4,1% abdecken. Die Analyse zeigt, wie das Risiko dramatisch mit dem Meeresspiegelanstieg eskaliert - unter einem schweren 3-Meter-Szenario steigen Hochrisikogebiete auf 17,5%, was die dringende Notwendigkeit von Anpassungsplanung und Risikominderungsstrategien verdeutlicht.",

    seaLevelRiseCurrentTitle: "Aktuelle Meeresspiegel-Risikoverteilung",
    seaLevelRiseCurrentDesc:
      "Aktuelle Basis-Risikobewertung zeigt heutige Verwundbarkeit gegenüber Meeresspiegelauswirkungen in europäischen Küstengebieten.",
    seaLevelRiseCurrentContent:
      "Die Bewertung des aktuellen Szenarios bietet ein grundlegendes Verständnis der heutigen Küstenverwundbarkeit. Mit 0 Metern zusätzlichem Meeresspiegelanstieg beobachten wir konzentrierte Risikogebiete hauptsächlich in tiefliegenden Küstenebenen und Flussdeltas. Hochrisikozonen umfassen derzeit 8.635 km² (9,7% der Gesamtfläche) mit mittleren Risikoniveaus von 0,115. Diese Basisdaten sind entscheidend für das Verständnis, wie der Klimawandel bestehende Verwundbarkeiten verstärken wird.",

    seaLevelRiseSevereTitle:
      "Schwere Meeresspiegelanstieg-Auswirkungsbewertung",
    seaLevelRiseSevereDesc:
      "Projizierte Auswirkungen unter einem schweren 3-Meter-Meeresspiegelanstieg-Szenario zeigen dramatisch erhöhte Risikoexposition.",
    seaLevelRiseSevereContent:
      "Unter dem schweren Meeresspiegelanstieg-Szenario (+3m) ist die Transformation der Risikolandschaften dramatisch. Hochrisikogebiete erweitern sich auf 15.556 km² (17,5% der Gesamtfläche), fast eine Verdopplung der aktuellen Niveaus. Das mittlere Risiko steigt auf 0,168, während das maximale Risiko 0,908 erreicht. Dieses Szenario unterstreicht die kritische Bedeutung sofortiger Klimamaßnahmen und umfassender Anpassungsstrategien zum Schutz verwundbarer Küstengemeinden und Infrastruktur.",

    expositionLayerTitle: "Küsteninfrastruktur-Exposition",
    expositionLayerDesc:
      "Analyse exponierter Infrastruktur, Siedlungen und wirtschaftlicher Güter in Küstenzonen, die klimatischen Auswirkungen unterliegen.",
    expositionLayerContent:
      "Die Expositionsschicht zeigt die Verteilung wertvoller Güter auf, die durch Klimagefahren bedroht sind. Dazu gehören Wohngebiete, Gewerbeviertel, Verkehrsnetze und kritische Infrastruktur in verwundbaren Küstenzonen. Das Verständnis von Expositionsmustern ist wesentlich für die Priorisierung von Schutzmaßnahmen und die Information raumplanerischer Entscheidungen. Die Analyse zeigt konzentrierte Exposition in großen Küstenstädten und Industriegebieten, wo sowohl Bevölkerungsdichte als auch wirtschaftlicher Wert am höchsten sind.",

    freightExpositionTitle: "Verwundbarkeit des Seetransports",
    freightExpositionDesc:
      "Bewertung der Exposition von Frachttransportnetzen und Hafeninfrastruktur gegenüber klimabedingten Gefahren.",
    freightExpositionContent:
      "Maritime Frachtsysteme stehen vor zunehmender Verwundbarkeit gegenüber Klimagefahren, wobei große europäische Häfen und Schifffahrtsrouten Meeresspiegelanstieg, Sturmfluten und extremen Wetterereignissen ausgesetzt sind. Die Analyse zeigt kritische Engpässe im Frachtnetz auf, wo Klimaauswirkungen europäische Lieferketten stören könnten. Hafeninfrastruktur, Verladeeinrichtungen und verbindende Transportnetze benötigen dringende Anpassungsmaßnahmen zur Aufrechterhaltung operativer Kontinuität und wirtschaftlicher Stabilität.",

    floodRiskScenariosTitle: "Vergleichende Hochwasserrisiko-Analyse",
    floodRiskScenariosDesc:
      "Vergleichende Analyse von Hochwasserrisikoniveaus bei verschiedenen Klimaszenarien zeigt relative Risikoverteilungsmuster.",
    floodRiskScenariosContent:
      "Die vergleichende Hochwasserrisiko-Analyse demonstriert, wie sich Risikoprofile bei verschiedenen Klimaszenarien entwickeln. Die Visualisierung zeigt relative Risikoniveaus von konservativen (1m SLR) bis schweren (3m SLR) Szenarien und bietet Entscheidungsträgern ein klares Verständnis dafür, wie das Risiko mit dem Klimawandel eskaliert. Diese Information ist vital für die Entwicklung adaptiver Managementstrategien und die Information langfristiger Infrastruktur-Planungsentscheidungen.",

    // Narrative Sections
    waterCycleTitle: "Küstenverwundbarkeits-Bewertung",
    waterCycleContent:
      "Küstenregionen in ganz Europa stehen vor beispiellosen Herausforderungen durch steigende Meeresspiegel und erhöhte Sturmintensität. Die Kombination aus physischer Exposition gegenüber marinen Gefahren und hohen Konzentrationen wertvoller Infrastruktur schafft komplexe Risikoszenarien, die ausgeklügelte Bewertungs- und Managementansätze erfordern. Das Verständnis dieser Verwundbarkeiten ist wesentlich für die Entwicklung effektiver Anpassungsstrategien.",

    economicTransformationTitle: "Risikobasierte Anpassungsplanung",
    economicTransformationContent:
      "Die Integration umfassender Risikobewertung in Politik- und Planungsrahmen stellt einen grundlegenden Wandel in Europas Herangehensweise an Klimaanpassung dar. Durch die Quantifizierung von Risiken bei verschiedenen Szenarien können Entscheidungsträger Investitionen in Schutzmaßnahmen priorisieren, Frühwarnsysteme entwickeln und naturbasierte Lösungen implementieren, die mehrfache Vorteile für Küstengemeinden und Ökosysteme bieten.",

    lookingForwardTitle: "Blick nach vorn",
    lookingForwardContent1:
      "Die in dieser Geschichte präsentierten Daten zeigen sowohl die Dringlichkeit des Klimahandelns als auch den bemerkenswerten Fortschritt, den Europa bei der Bewältigung des Klimawandels gemacht hat. Während Herausforderungen erheblich bleiben, insbesondere bei Anpassung und Resilienzaufbau, ist die Trajektorie zu einer nachhaltigen Zukunft klar.",
    lookingForwardContent2:
      "Kontinuierliche Überwachung, Analyse und datengesteuerte Entscheidungsfindung werden wesentlich sein, während Europa die komplexen Herausforderungen des 21. Jahrhunderts navigiert. Die hier präsentierten Visualisierungen und Erkenntnisse stellen nur den Beginn einer fortlaufenden Geschichte von Transformation, Anpassung und Hoffnung dar.",

    // References
    references: "Referenzen",
    referencesDesc:
      "Bibliographie und Datenquellen, die in dieser Analyse verwendet wurden",
    viewSource: "Quelle anzeigen",
    referencedSources: "Referenzierte Quellen:",

    // Loading Warning Dialog
    loadingWarningTitle: "Ladezeit-Hinweis",
    loadingWarningMessage: "Aufgrund der hohen Komplexität der Klimadaten-Visualisierungen und interaktiven Karten können die Ladezeiten verlängert sein, insbesondere bei langsameren Internetverbindungen. Vielen Dank für Ihre Geduld.",
    loadingWarningUnderstand: "Verstanden",
    loadingWarningDontShowAgain: "Nicht mehr anzeigen",

    // Common
    visualizationPlaceholder: "Visualisierungs-Platzhalter",
    interactiveWillRender: "wird hier gerendert",
    copyright: "Alle Rechte vorbehalten.",
  },
};

export function getTranslation(language: Language): Translation {
  return translations[language];
}
