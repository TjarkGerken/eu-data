"use client";

import { Header } from "@/components/header";
import { VideoSection } from "@/components/video-section";
import { TechnicalSection } from "@/components/technical-section";
import { ReferencesSidebar } from "@/components/references-sidebar";
import { DataStoryRenderer } from "@/components/blocks/data-story-renderer";
import { useDynamicContent } from "@/hooks/use-dynamic-content";

export default function HomePage() {
  const { content } = useDynamicContent();

  if (!content) return null;

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          <main className="lg:col-span-3">
            <section className="mb-12">
              <h1 className="text-4xl font-bold text-[#2d5a3d] mb-6">
                {content.heroTitle}
              </h1>
              <p className="text-xl text-muted-foreground mb-8">
                {content.heroDescription}
              </p>
            </section>

            <VideoSection />

            <section className="mb-12">
              <p className="text-lg text-muted-foreground mb-6">
                {content.introText1}
              </p>
              <p className="text-lg text-muted-foreground mb-8">
                {content.introText2}
              </p>
            </section>

            <section>
              <h2 className="text-3xl font-bold text-[#2d5a3d] mb-8">
                {content.dataStoryTitle}
              </h2>
              <DataStoryRenderer blocks={content.blocks} />
            </section>

            <TechnicalSection />
          </main>

          <aside className="lg:col-span-1">
            <ReferencesSidebar references={content.references || []} />
          </aside>
        </div>
      </div>
    </div>
  );
}
