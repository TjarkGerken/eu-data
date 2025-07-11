import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { motion } from "framer-motion";
import { useLanguage } from "@/contexts/language-context";

interface ImpactComparisonBlockProps {
  block: {
    title?: string;
    comparisons: Array<{
      category: string;
      currentValue: number;
      projectedValue: number;
      unit: string;
      severity: "low" | "medium" | "high";
    }>;
    references?: Array<{
      id: string;
      title: string;
      authors: string[];
      type: string;
    }>;
  };
}

export default function ImpactComparisonBlockComponent({
  block,
}: ImpactComparisonBlockProps) {
  const { language } = useLanguage();

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "low":
        return "text-green-600 bg-green-100";
      case "medium":
        return "text-yellow-600 bg-yellow-100";
      case "high":
        return "text-red-600 bg-red-100";
      default:
        return "text-gray-600 bg-gray-100";
    }
  };

  return (
    <div className="my-8">
      {block.title && (
        <h3 className="text-2xl font-bold mb-4 text-[#2d5a3d]">
          {block.title}
        </h3>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {block.comparisons?.map((comparison, index) => {
          const impactPercentage =
            ((comparison.projectedValue - comparison.currentValue) /
              comparison.currentValue) *
            100;

          return (
            <motion.div
              key={index}
              initial={{ opacity: 0, scale: 0.95 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.1 }}
            >
              <Card>
                <CardHeader>
                  <div className="flex justify-between items-center">
                    <CardTitle className="text-lg">
                      {comparison.category}
                    </CardTitle>
                    <Badge className={getSeverityColor(comparison.severity)}>
                      {comparison.severity}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex justify-between text-sm">
                    <span>
                      {language === "de" ? "Aktuell:" : "Current:"}{" "}
                      {comparison.currentValue}
                      {comparison.unit}
                    </span>
                    <span>
                      {language === "de" ? "Prognose:" : "Projected:"}{" "}
                      {comparison.projectedValue}
                      {comparison.unit}
                    </span>
                  </div>

                  <Progress
                    value={Math.min(Math.abs(impactPercentage), 100)}
                    className="h-2"
                  />

                  <div className="text-center">
                    <span
                      className={`text-lg font-bold ${
                        impactPercentage > 0 ? "text-red-600" : "text-green-600"
                      }`}
                    >
                      {impactPercentage > 0 ? "+" : ""}
                      {impactPercentage.toFixed(1)}%
                    </span>
                    <p className="text-sm text-muted-foreground mt-1">
                      {impactPercentage > 0
                        ? language === "de"
                          ? "Anstieg erwartet"
                          : "Increase expected"
                        : language === "de"
                          ? "Rückgang erwartet"
                          : "Decrease expected"}
                    </p>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          );
        })}
      </div>

      {block.references && block.references.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.3 }}
          className="mt-8 pt-6 border-t border-muted"
        >
          <h4 className="text-sm font-semibold text-muted-foreground mb-3">
            {language === "de" ? "Referenzen" : "References"}
          </h4>
          <div className="space-y-2">
            {block.references.map((ref) => (
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
        </motion.div>
      )}
    </div>
  );
}
