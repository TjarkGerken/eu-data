"use client";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { cn } from "@/lib/utils";
import { CitationAwareMarkdown } from "./citation-aware-markdown";
import { useLanguage } from "@/contexts/language-context";

interface CalloutBlockProps {
  title: string;
  content: string;
  variant: "success" | "warning" | "info" | "error";
  references?: Array<{
    id: string;
    title: string;
    authors: string[];
    type: string;
  }>;
}

export function CalloutBlock({
  title,
  content,
  variant,
  references,
}: CalloutBlockProps) {
  const { language } = useLanguage();

  const variantStyles = {
    success: "border-green-200 bg-green-50 text-green-800",
    warning: "border-yellow-200 bg-yellow-50 text-yellow-800",
    info: "border-blue-200 bg-blue-50 text-blue-800",
    error: "border-red-200 bg-red-50 text-red-800",
  };

  return (
    <div className="space-y-4">
      <Alert className={cn("border-l-4", variantStyles[variant])}>
        <AlertTitle className="text-lg font-semibold mb-2">{title}</AlertTitle>
        <AlertDescription className="text-base">
          <CitationAwareMarkdown content={content} references={references} />
        </AlertDescription>
      </Alert>

      {references && references.length > 0 && (
        <div className="mt-4 pt-4 border-t border-muted">
          <h4 className="text-sm font-semibold text-muted-foreground mb-3">
            {language === "de" ? "Referenzen" : "References"}
          </h4>
          <div className="space-y-2">
            {references.map((ref) => (
              <div
                key={ref.id}
                className="text-xs text-muted-foreground cursor-pointer hover:text-foreground transition-colors"
                onClick={() => {
                  const event = new CustomEvent("highlightReference", {
                    detail: ref.id,
                  });
                  window.dispatchEvent(event);
                }}
              >
                <span className="font-medium">{ref.title}</span>
                {ref.authors && ref.authors.length > 0 && (
                  <span className="ml-2">- {ref.authors.join(", ")}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
