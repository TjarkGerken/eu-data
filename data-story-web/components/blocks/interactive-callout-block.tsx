"use client";

import { motion } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { AlertCircle, CheckCircle, Info, AlertTriangle } from "lucide-react";
import { useState } from "react";
import { CitationAwareMarkdown } from "./citation-aware-markdown";

interface InteractiveCalloutBlockProps {
  title: string;
  content: string;
  variant: "success" | "warning" | "info" | "error";
  interactive?: boolean;
  references?: Array<{
    id: string;
    title: string;
    authors: string[];
    type: string;
  }>;
}

export function InteractiveCalloutBlock({
  title,
  content,
  variant,
  interactive = true,
  references,
}: InteractiveCalloutBlockProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isHovered, setIsHovered] = useState(false);

  const getVariantConfig = () => {
    switch (variant) {
      case "success":
        return {
          icon: CheckCircle,
          bgColor: "from-green-50 to-emerald-50",
          borderColor: "border-green-200",
          iconColor: "text-green-600",
          titleColor: "text-green-800",
        };
      case "warning":
        return {
          icon: AlertTriangle,
          bgColor: "from-yellow-50 to-orange-50",
          borderColor: "border-yellow-200",
          iconColor: "text-yellow-600",
          titleColor: "text-yellow-800",
        };
      case "error":
        return {
          icon: AlertCircle,
          bgColor: "from-red-50 to-pink-50",
          borderColor: "border-red-200",
          iconColor: "text-red-600",
          titleColor: "text-red-800",
        };
      default:
        return {
          icon: Info,
          bgColor: "from-blue-50 to-cyan-50",
          borderColor: "border-blue-200",
          iconColor: "text-blue-600",
          titleColor: "text-blue-800",
        };
    }
  };

  const config = getVariantConfig();
  const IconComponent = config.icon;

  return (
    <div className="my-8">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6 }}
        whileHover={interactive ? { scale: 1.02 } : {}}
        onHoverStart={() => setIsHovered(true)}
        onHoverEnd={() => setIsHovered(false)}
        onClick={interactive ? () => setIsExpanded(!isExpanded) : undefined}
        className={interactive ? "cursor-pointer" : ""}
      >
        <Card
          className={`
            bg-gradient-to-br ${config.bgColor} 
            ${config.borderColor} 
            border-2 
            overflow-hidden 
            transition-all 
            duration-300
            ${interactive && isHovered ? "shadow-lg" : ""}
          `}
        >
          <CardContent className="p-6">
            <div className="flex items-start gap-4">
              <motion.div
                animate={
                  interactive
                    ? {
                        rotate: isExpanded ? 180 : 0,
                        scale: isHovered ? 1.1 : 1,
                      }
                    : {}
                }
                transition={{ duration: 0.3 }}
                className={`flex-shrink-0 p-2 rounded-full bg-white/50 ${config.iconColor}`}
              >
                <IconComponent className="h-5 w-5" />
              </motion.div>

              <div className="flex-1 min-w-0">
                <motion.h4
                  className={`text-lg font-semibold mb-2 ${config.titleColor}`}
                  animate={
                    interactive
                      ? {
                          x: isHovered ? 4 : 0,
                        }
                      : {}
                  }
                  transition={{ duration: 0.2 }}
                >
                  {title}
                </motion.h4>

                <motion.div
                  initial={false}
                  animate={
                    interactive
                      ? {
                          height: isExpanded ? "auto" : "auto",
                          opacity: isExpanded ? 1 : 0.8,
                        }
                      : {}
                  }
                  transition={{ duration: 0.3 }}
                  className="text-sm text-muted-foreground leading-relaxed"
                >
                  <CitationAwareMarkdown
                    content={content}
                    references={references}
                  />
                </motion.div>

                {interactive && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: isHovered ? 1 : 0.6 }}
                    transition={{ duration: 0.2 }}
                    className="mt-3 text-xs text-muted-foreground"
                  >
                    {isExpanded ? "Click to collapse" : "Click to expand"}
                  </motion.div>
                )}
              </div>

              {interactive && (
                <motion.div
                  animate={{
                    rotate: isExpanded ? 90 : 0,
                  }}
                  transition={{ duration: 0.3 }}
                  className="flex-shrink-0 text-muted-foreground"
                >
                  <svg
                    className="h-4 w-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 5l7 7-7 7"
                    />
                  </svg>
                </motion.div>
              )}
            </div>
          </CardContent>

          {interactive && (
            <motion.div
              className="absolute inset-0 bg-white/10"
              initial={{ opacity: 0 }}
              animate={{ opacity: isHovered ? 1 : 0 }}
              transition={{ duration: 0.3 }}
              style={{ pointerEvents: "none" }}
            />
          )}
        </Card>
      </motion.div>

      {references && references.length > 0 && (
        <div className="mt-4 pt-4 border-t border-muted">
          <h4 className="text-sm font-semibold text-muted-foreground mb-3">
            References
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
