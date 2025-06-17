"use client";

import { Card } from "@/components/ui/card";
import { Play } from "lucide-react";
import { useLanguage } from "@/contexts/language-context";

export function VideoSection() {
  const { t } = useLanguage();

  return (
    <section className="w-full py-12 bg-gradient-to-r from-[#2d5a3d]/5 to-[#c4a747]/5 flex justify-center items-center">
      <div className="container">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold tracking-tight text-[#2d5a3d] mb-4">
            {t.heroTitle}
          </h1>
          <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
            {t.heroDescription}
          </p>
        </div>

        <Card className="relative aspect-video max-w-4xl mx-auto overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-[#2d5a3d] to-[#c4a747] flex items-center justify-center">
            <div className="text-center text-white">
              <Play className="h-16 w-16 mx-auto mb-4 opacity-80" />
              <h3 className="text-2xl font-semibold mb-2">{t.introVideo}</h3>
              <p className="text-lg opacity-90">{t.videoOverview}</p>
            </div>
          </div>
        </Card>
      </div>
    </section>
  );
}
