"use client";

import { Header } from "@/components/header";
import { VideoSection } from "@/components/video-section";
import { VisualizationCard } from "@/components/visualization-card";
import { ReferencesSidebar } from "@/components/references-sidebar";
import { TechnicalSection } from "@/components/technical-section";
import { useLanguage } from "@/contexts/language-context";

export default function Page() {
  const { t } = useLanguage();

  const visualizations = [
    {
      title: t.hazardAssessmentTitle,
      description: t.hazardAssessmentDesc,
      content: t.hazardAssessmentContent,
      type: "map" as const,
      imagePath: "/hazard_risk_current_scenario.png",
      references: ["1", "3"],
    },
    {
      title: t.seaLevelRiseCurrentTitle,
      description: t.seaLevelRiseCurrentDesc,
      content: t.seaLevelRiseCurrentContent,
      type: "map" as const,
      imagePath: "/risk_SLR-0-Current_COMBINED.png",
      references: ["2", "5"],
    },
    {
      title: t.seaLevelRiseSevereTitle,
      description: t.seaLevelRiseSevereDesc,
      content: t.seaLevelRiseSevereContent,
      type: "map" as const,
      imagePath: "/risk_SLR-3-Severe_COMBINED.png",
      references: ["1", "4"],
    },
    {
      title: t.expositionLayerTitle,
      description: t.expositionLayerDesc,
      content: t.expositionLayerContent,
      type: "map" as const,
      imagePath: "/exposition_layer.png",
      references: ["2", "4"],
    },
    {
      title: t.freightExpositionTitle,
      description: t.freightExpositionDesc,
      content: t.freightExpositionContent,
      type: "chart" as const,
      imagePath: "/exposition_freight_loading.png",
      references: ["3", "4", "5"],
    },
    {
      title: t.floodRiskScenariosTitle,
      description: t.floodRiskScenariosDesc,
      content: t.floodRiskScenariosContent,
      type: "trend" as const,
      imagePath: "/flood_risk_relative_by_scenario.png",
      references: ["2", "4"],
    },
  ];

  return (
    <div className="min-h-screen bg-background flex flex-col items-center">
      <Header />

      <VideoSection />

      <main className="container py-12 flex justify-center items-center ">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Main Content - Blog-like layout */}
          <div className="lg:col-span-3">
            <div className="mb-12">
              <h2 className="text-4xl font-bold text-[#2d5a3d] mb-6">
                {t.dataStoryTitle}
              </h2>
              <div className="prose prose-lg max-w-none">
                <p className="text-xl text-muted-foreground leading-relaxed">
                  {t.introText1}
                </p>
                <p className="text-lg text-muted-foreground leading-relaxed mt-4">
                  {t.introText2}
                </p>
              </div>
            </div>

            {/* Blog-style stacked visualizations */}
            <div className="space-y-12" id="visualizations">
              {visualizations.map((viz, index) => (
                <div key={index}>
                  <VisualizationCard
                    title={viz.title}
                    description={viz.description}
                    content={viz.content}
                    type={viz.type}
                    references={viz.references}
                    imagePath={viz.imagePath}
                  />

                  {/* Add narrative sections between some visualizations */}
                  {index === 1 && (
                    <div className="my-12 p-8 bg-gradient-to-r from-[#2d5a3d]/5 to-[#c4a747]/5 rounded-lg">
                      <h3 className="text-2xl font-semibold text-[#2d5a3d] mb-4">
                        {t.waterCycleTitle}
                      </h3>
                      <div className="prose prose-lg max-w-none">
                        <p className="text-muted-foreground leading-relaxed">
                          {t.waterCycleContent}
                        </p>
                      </div>
                    </div>
                  )}

                  {index === 3 && (
                    <div className="my-12 p-8 bg-gradient-to-r from-[#c4a747]/5 to-[#2d5a3d]/5 rounded-lg">
                      <h3 className="text-2xl font-semibold text-[#2d5a3d] mb-4">
                        {t.economicTransformationTitle}
                      </h3>
                      <div className="prose prose-lg max-w-none">
                        <p className="text-muted-foreground leading-relaxed">
                          {t.economicTransformationContent}
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Technical Section */}
            <TechnicalSection />

            {/* Conclusion section */}
            <div className="mt-16 p-8 bg-gradient-to-r from-[#2d5a3d]/10 to-[#c4a747]/10 rounded-lg">
              <h3 className="text-3xl font-semibold text-[#2d5a3d] mb-6">
                {t.lookingForwardTitle}
              </h3>
              <div className="prose prose-lg max-w-none">
                <p className="text-muted-foreground leading-relaxed">
                  {t.lookingForwardContent1}
                </p>
                <p className="text-muted-foreground leading-relaxed mt-4">
                  {t.lookingForwardContent2}
                </p>
              </div>
            </div>
          </div>

          {/* Sidebar - 1/3 width on large screens */}
          <div className="lg:col-span-1">
            <ReferencesSidebar />
          </div>
        </div>
      </main>

      <footer className="border-t py-8 mt-12">
        <div className="container text-center text-muted-foreground">
          <p>&copy; 2024 EU Geolytics. {t.copyright}</p>
        </div>
      </footer>
    </div>
  );
}
