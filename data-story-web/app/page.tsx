"use client";

import { Header } from "@/components/header";
import { HeroVideoSection } from "@/components/hero-video-section";
import { TechnicalSection } from "@/components/technical-section";
import { ReferencesSidebar } from "@/components/references-sidebar";
import { DataStoryRenderer } from "@/components/blocks/data-story-renderer";
import { useDynamicContent } from "@/hooks/use-dynamic-content";
import { motion } from "motion/react";

export default function HomePage() {
  const { content } = useDynamicContent();

  if (!content) return null;

  return (
    <div className="min-h-screen bg-background">
      <Header />

      {/* Hero Video Section - Above the Fold */}
      <HeroVideoSection />

      {/* Main Content Section - Below the Fold */}
      <div id="main-content" className="bg-background">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
            className="grid grid-cols-1 lg:grid-cols-4 gap-8"
          >
            <main className="lg:col-span-3">
              {/* Introduction Section */}
              <motion.section
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.1 }}
                viewport={{ once: true }}
                className="mb-12"
              >
                <div className="prose max-w-none">
                  <p className="text-lg text-muted-foreground mb-6 leading-relaxed">
                    {content.introText1}
                  </p>
                  <p className="text-lg text-muted-foreground mb-8 leading-relaxed">
                    {content.introText2}
                  </p>
                </div>
              </motion.section>

              {/* Data Story Section */}
              <motion.section
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.2 }}
                viewport={{ once: true }}
                className="mb-12"
              >
                <div className="mb-8">
                  <h2 className="text-3xl font-bold text-[#2d5a3d] mb-4">
                    {content.dataStoryTitle}
                  </h2>
                  <div className="w-24 h-1 bg-gradient-to-r from-[#2d5a3d] to-[#c4a747] rounded-full"></div>
                </div>
                <DataStoryRenderer blocks={content.blocks} />
              </motion.section>

              {/* Technical Section */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.3 }}
                viewport={{ once: true }}
              >
                <TechnicalSection />
              </motion.div>
            </main>

            {/* References Sidebar */}
            <aside className="lg:col-span-1">
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                whileInView={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.6, delay: 0.4 }}
                viewport={{ once: true }}
                className="sticky top-8"
              >
                <ReferencesSidebar references={content.references || []} />
              </motion.div>
            </aside>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
