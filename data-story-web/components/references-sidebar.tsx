"use client";

import { useState, useEffect, useRef } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ExternalLink, BookOpen } from "lucide-react";
import { useLanguage } from "@/contexts/language-context";
import { useGlobalCitation } from "@/contexts/global-citation-context";
import { Reference } from "@/lib/types";

const typeColors = {
  journal: "bg-blue-100 text-blue-800",
  report: "bg-green-100 text-green-800",
  dataset: "bg-purple-100 text-purple-800",
  book: "bg-orange-100 text-orange-800",
};

interface ReferencesSidebarProps {
  references?: Reference[];
}

export function ReferencesSidebar({ references = [] }: ReferencesSidebarProps) {
  const { t } = useLanguage();
  const { globalCitationData } = useGlobalCitation();
  const [highlightedRef, setHighlightedRef] = useState<string | null>(null);
  const refRefs = useRef<{ [key: string]: HTMLDivElement | null }>({});

  useEffect(() => {
    const handleHighlightReference = (event: CustomEvent) => {
      const refId = event.detail;
      setHighlightedRef(refId);

      // Scroll to the highlighted reference
      const refElement = refRefs.current[refId];
      if (refElement) {
        refElement.scrollIntoView({
          behavior: "smooth",
          block: "center",
        });
      }

      // Clear highlight after 3 seconds
      setTimeout(() => {
        setHighlightedRef(null);
      }, 3000);
    };

    window.addEventListener(
      "highlightReference",
      handleHighlightReference as EventListener,
    );

    return () => {
      window.removeEventListener(
        "highlightReference",
        handleHighlightReference as EventListener,
      );
    };
  }, []);

  // Use global citation data if available, otherwise fall back to provided references
  const referencesToDisplay =
    globalCitationData?.orderedReferences || references;

  // Create references with citation numbers from global data
  const referencesWithNumbers = referencesToDisplay.map((ref) => {
    const citationNumber = globalCitationData?.citationMap.get(ref.id);
    return {
      ...ref,
      citationNumber: citationNumber || null,
    } as Reference & { citationNumber: number | null };
  });

  return (
    <Card className="sticky top-20 h-fit">
      <CardHeader>
        <div className="flex items-center space-x-2">
          <BookOpen className="h-5 w-5 text-[#2d5a3d]" />
          <CardTitle>{t.references}</CardTitle>
        </div>
        <CardDescription>{t.referencesDesc}</CardDescription>
      </CardHeader>
      <CardContent className="overflow-visible">
        <ScrollArea className="h-[600px] pr-4">
          <div className="space-y-4 p-2" style={{ overflow: "visible" }}>
            {referencesWithNumbers.map((ref) => (
              <div
                key={ref.id}
                ref={(el) => {
                  refRefs.current[ref.id] = el;
                }}
                className={`border-l-2 pl-4 pb-4 mx-2 transition-all duration-300 transform-gpu ${
                  highlightedRef === ref.id
                    ? "border-[#2d5a3d] bg-[#2d5a3d]/5 shadow-lg scale-105 z-10"
                    : "border-[#2d5a3d]/20"
                }`}
                style={{
                  transformOrigin: "center center",
                }}
              >
                <div className="flex items-start justify-between mb-2">
                  <Badge
                    variant="secondary"
                    className={`text-xs ${
                      typeColors[ref.type as keyof typeof typeColors] ||
                      typeColors.journal
                    }`}
                  >
                    {ref.type}
                  </Badge>
                  {ref.citationNumber && (
                    <span
                      className={`text-xs font-mono transition-colors ${
                        highlightedRef === ref.id
                          ? "text-[#2d5a3d] font-semibold"
                          : "text-muted-foreground"
                      }`}
                    >
                      [{ref.citationNumber}]
                    </span>
                  )}
                </div>

                <h4
                  className={`text-sm font-medium leading-tight mb-1 transition-colors ${
                    highlightedRef === ref.id ? "text-[#2d5a3d]" : ""
                  }`}
                >
                  {ref.title}
                </h4>

                <p className="text-xs text-muted-foreground mb-1">
                  {ref.authors.join(", ")} ({ref.year})
                </p>

                {ref.journal && (
                  <p className="text-xs text-muted-foreground italic mb-2">
                    {ref.journal}
                  </p>
                )}

                {ref.url && (
                  <a
                    href={ref.url}
                    className="inline-flex items-center text-xs text-[#2d5a3d] hover:underline"
                  >
                    <ExternalLink className="h-3 w-3 mr-1" />
                    {t.viewSource}
                  </a>
                )}
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
