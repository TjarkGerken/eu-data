"use client";

import { motion } from "motion/react";
import { Card } from "@/components/ui/card";
import { ChevronDown } from "lucide-react";
import { useLanguage } from "@/contexts/language-context";
import { useDynamicContent } from "@/hooks/use-dynamic-content";

export function HeroVideoSection() {
  const { t } = useLanguage();
  const { content: dynamicContent } = useDynamicContent();

  const scrollToContent = () => {
    const contentSection = document.getElementById("main-content");
    contentSection?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <section className="relative h-screen flex flex-col justify-center items-center bg-gradient-to-br from-[#2d5a3d] to-[#c4a747] text-white overflow-hidden pt-16">
      {/* Background Pattern */}
      <div className="absolute inset-0 opacity-10">
        <motion.div
          className="absolute inset-0"
          style={{
            background: `radial-gradient(circle at 25% 25%, #ffffff 1px, transparent 1px),
                         radial-gradient(circle at 75% 75%, #ffffff 1px, transparent 1px)`,
            backgroundSize: "60px 60px",
          }}
          animate={{
            backgroundPosition: ["0px 0px", "60px 60px"],
          }}
          transition={{
            duration: 20,
            repeat: Infinity,
            ease: "linear",
          }}
        />
      </div>

      <div className="container relative z-10 max-w-6xl mx-auto px-4 text-center">
        {/* Title Animation */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="mb-8"
        >
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6">
            {dynamicContent?.heroTitle || t.heroTitle}
          </h1>
          <p className="text-xl md:text-2xl text-white/90 max-w-4xl mx-auto leading-relaxed">
            {dynamicContent?.heroDescription || t.heroDescription}
          </p>
        </motion.div>

        {/* Video Card with Motion */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8, delay: 0.3 }}
          className="relative max-w-4xl mx-auto mb-16"
        >
          <Card className="relative aspect-video overflow-hidden border-0 shadow-2xl bg-black/20 backdrop-blur-sm">
            <iframe
              src="https://www.youtube.com/embed/HwzwvXECIFY"
              title="YouTube video player"
              frameBorder="0"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
              referrerPolicy="strict-origin-when-cross-origin"
              allowFullScreen
              className="w-full h-full"
            />
          </Card>
        </motion.div>

        {/* Scroll Indicator */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.8 }}
          className="absolute bottom-8 left-1/2 transform -translate-x-1/2"
        >
          <motion.button
            onClick={scrollToContent}
            className="flex flex-col items-center text-white/80 hover:text-white transition-colors cursor-pointer"
            animate={{
              y: [0, 10, 0],
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: "easeInOut",
            }}
            whileHover={{ scale: 1.1 }}
          >
            <span className="text-sm mb-2 font-medium">Zur Data Story</span>
            <ChevronDown className="h-6 w-6" />
          </motion.button>
        </motion.div>
      </div>

      {/* Floating Elements */}
      <motion.div
        className="absolute top-20 left-10 w-4 h-4 bg-white/20 rounded-full"
        animate={{
          y: [0, -20, 0],
          opacity: [0.3, 0.7, 0.3],
        }}
        transition={{
          duration: 3,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      />
      <motion.div
        className="absolute top-40 right-20 w-6 h-6 bg-white/15 rounded-full"
        animate={{
          y: [0, 15, 0],
          opacity: [0.2, 0.6, 0.2],
        }}
        transition={{
          duration: 4,
          repeat: Infinity,
          ease: "easeInOut",
          delay: 1,
        }}
      />
      <motion.div
        className="absolute bottom-40 left-20 w-3 h-3 bg-white/25 rounded-full"
        animate={{
          y: [0, -10, 0],
          opacity: [0.4, 0.8, 0.4],
        }}
        transition={{
          duration: 2.5,
          repeat: Infinity,
          ease: "easeInOut",
          delay: 0.5,
        }}
      />
    </section>
  );
}
