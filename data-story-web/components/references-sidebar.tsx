"use client";

import { useState, useEffect } from "react";
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
import { Reference } from "@/lib/types";

const typeColors = {
  journal: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300",
  report: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300",
  dataset:
    "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300",
  book: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300",
};

export function ReferencesSidebar() {
  const { t } = useLanguage();
  const [references, setReferences] = useState<Reference[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadReferences();
  }, []);

  const loadReferences = async () => {
    try {
      const response = await fetch("/api/content");
      const data = await response.json();
      setReferences(data.references || []);
    } catch (error) {
      console.error("Failed to load references:", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Card className="sticky top-20 h-fit">
        <CardHeader>
          <div className="flex items-center space-x-2">
            <BookOpen className="h-5 w-5 text-[#2d5a3d]" />
            <CardTitle>{t.references}</CardTitle>
          </div>
          <CardDescription>{t.referencesDesc}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="space-y-2">
                <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                <div className="h-3 bg-gray-200 rounded w-1/2"></div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="sticky top-20 h-fit">
      <CardHeader>
        <div className="flex items-center space-x-2">
          <BookOpen className="h-5 w-5 text-[#2d5a3d]" />
          <CardTitle>{t.references}</CardTitle>
        </div>
        <CardDescription>{t.referencesDesc}</CardDescription>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[600px] pr-4">
          <div className="space-y-4">
            {references.map((ref) => (
              <div
                key={ref.id}
                className="border-l-2 border-[#2d5a3d]/20 pl-4 pb-4"
              >
                <div className="flex items-start justify-between mb-2">
                  <Badge
                    variant="secondary"
                    className={`text-xs ${typeColors[ref.type]}`}
                  >
                    {ref.type}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    [{ref.id}]
                  </span>
                </div>

                <h4 className="text-sm font-medium leading-tight mb-1">
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
