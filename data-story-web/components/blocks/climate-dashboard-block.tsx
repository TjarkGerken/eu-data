"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { useLanguage } from "@/contexts/language-context";
import {
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  Clock,
  Target,
} from "lucide-react";

interface ClimateDashboardBlockProps {
  title?: string;
  description?: string;
  metrics: Array<{
    title: string;
    value: string;
    change: string;
    trend: "up" | "down";
    status: "success" | "warning" | "danger";
    progress: number;
    target: string;
    description: string;
  }>;
  references?: Array<{
    id: string;
    title: string;
    authors: string[];
    type: string;
  }>;
}

export function ClimateDashboardBlock({
  title,
  description,
  metrics,
  references,
}: ClimateDashboardBlockProps) {
  const { language } = useLanguage();

  const getStatusColor = (status: string) => {
    switch (status) {
      case "success":
        return "text-green-600 bg-green-50";
      case "warning":
        return "text-orange-600 bg-orange-50";
      case "danger":
        return "text-red-600 bg-red-50";
      default:
        return "text-gray-600 bg-gray-50";
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "success":
        return CheckCircle;
      case "warning":
        return Clock;
      case "danger":
        return AlertTriangle;
      default:
        return Target;
    }
  };

  const getTrendIcon = (trend: string) => {
    return trend === "up" ? TrendingUp : TrendingDown;
  };

  const defaultTitle =
    language === "de" ? "Klima-Dashboard" : "Climate Dashboard";
  const defaultDescription =
    language === "de"
      ? "Echtzeitübersicht der wichtigsten Klimaindikatoren"
      : "Real-time overview of key climate indicators";

  const successCount = metrics.filter((m) => m.status === "success").length;
  const warningCount = metrics.filter((m) => m.status === "warning").length;
  const dangerCount = metrics.filter((m) => m.status === "danger").length;

  return (
    <div className="my-16 p-8 bg-gradient-to-br from-gray-50 to-slate-100 rounded-lg">
      <div className="text-center mb-8">
        <h3 className="text-3xl font-bold text-[#2d5a3d] mb-4">
          {title || defaultTitle}
        </h3>
        <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
          {description || defaultDescription}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        {metrics.map((metric, index) => {
          const StatusIcon = getStatusIcon(metric.status);
          const TrendIcon = getTrendIcon(metric.trend);

          return (
            <Card
              key={index}
              className="hover:shadow-lg transition-shadow duration-300"
            >
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">{metric.title}</CardTitle>
                  <div
                    className={`p-2 rounded-full ${getStatusColor(
                      metric.status
                    )}`}
                  >
                    <StatusIcon className="h-4 w-4" />
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-baseline justify-between">
                  <div className="text-3xl font-bold text-[#2d5a3d]">
                    {metric.value}
                  </div>
                  <div className="flex items-center gap-1 text-sm text-muted-foreground">
                    <TrendIcon className="h-3 w-3" />
                    {metric.change}
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">
                      {language === "de"
                        ? "Fortschritt zum Ziel"
                        : "Progress to target"}
                    </span>
                    <span className="font-medium">{metric.target}</span>
                  </div>
                  <Progress value={metric.progress} className="h-2" />
                  <div className="text-xs text-right text-muted-foreground">
                    {metric.progress}%
                  </div>
                </div>

                <p className="text-sm text-muted-foreground">
                  {metric.description}
                </p>

                <Badge
                  variant="secondary"
                  className={`${getStatusColor(metric.status)} border-none`}
                >
                  {metric.status === "success" &&
                    (language === "de" ? "Auf Kurs" : "On Track")}
                  {metric.status === "warning" &&
                    (language === "de" ? "Aufmerksamkeit" : "Attention")}
                  {metric.status === "danger" &&
                    (language === "de" ? "Kritisch" : "Critical")}
                </Badge>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="bg-green-50 border-green-200">
          <CardContent className="p-6 text-center">
            <CheckCircle className="h-8 w-8 text-green-600 mx-auto mb-2" />
            <div className="text-2xl font-bold text-green-600">
              {successCount}
            </div>
            <div className="text-sm text-green-700">
              {language === "de" ? "Ziele erreicht" : "Targets met"}
            </div>
          </CardContent>
        </Card>

        <Card className="bg-orange-50 border-orange-200">
          <CardContent className="p-6 text-center">
            <Clock className="h-8 w-8 text-orange-600 mx-auto mb-2" />
            <div className="text-2xl font-bold text-orange-600">
              {warningCount}
            </div>
            <div className="text-sm text-orange-700">
              {language === "de" ? "Aufmerksamkeit nötig" : "Needs attention"}
            </div>
          </CardContent>
        </Card>

        <Card className="bg-red-50 border-red-200">
          <CardContent className="p-6 text-center">
            <AlertTriangle className="h-8 w-8 text-red-600 mx-auto mb-2" />
            <div className="text-2xl font-bold text-red-600">{dangerCount}</div>
            <div className="text-sm text-red-700">
              {language === "de" ? "Kritische Bereiche" : "Critical areas"}
            </div>
          </CardContent>
        </Card>
      </div>

      {references && references.length > 0 && (
        <div className="mt-8 pt-6 border-t border-muted">
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
