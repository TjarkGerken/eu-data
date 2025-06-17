"use client";

import { Card, CardContent } from "@/components/ui/card";
import { useLanguage } from "@/contexts/language-context";
import { useMemo } from "react";

interface TemperatureSpiralBlockProps {
  title?: string;
  description?: string;
  startYear?: number;
  endYear?: number;
  rotations?: number;
}

export function TemperatureSpiralBlock({
  title,
  description,
  startYear = 1880,
  endYear = 2030,
  rotations = 8,
}: TemperatureSpiralBlockProps) {
  const { language } = useLanguage();

  const spiralData = useMemo(() => {
    const data = [];
    const years = endYear - startYear;
    const centerX = 200;
    const centerY = 200;

    for (let i = 0; i < years; i++) {
      const year = startYear + i;
      const angle = (i / years) * rotations * Math.PI;
      const baseRadius = 20;
      const tempAnomaly = Math.sin(i * 0.1) * 0.5 + (i / years) * 1.5;
      const radius = baseRadius + (i / years) * 120 + tempAnomaly * 20;

      const x = centerX + Math.cos(angle) * radius;
      const y = centerY + Math.sin(angle) * radius;

      let color = "#3b82f6";
      if (tempAnomaly > 0.5) {
        color = "#ef4444";
      } else if (tempAnomaly > 0) {
        color = "#f59e0b";
      }

      data.push({
        x,
        y,
        year,
        temp: tempAnomaly,
        color,
        radius: 2 + Math.abs(tempAnomaly) * 2,
      });
    }
    return data;
  }, [startYear, endYear, rotations]);

  const decades = useMemo(() => {
    const result = [];
    for (let year = startYear; year <= endYear; year += 20) {
      result.push(year);
    }
    return result;
  }, [startYear, endYear]);

  const defaultTitle =
    language === "de"
      ? `Temperaturspirale ${startYear}-${endYear}`
      : `Temperature Spiral ${startYear}-${endYear}`;

  const defaultDescription =
    language === "de"
      ? "Jeder Punkt repräsentiert ein Jahr - die Spirale zeigt die beschleunigte Erwärmung"
      : "Each dot represents a year - the spiral shows accelerated warming";

  return (
    <div className="my-16 p-8 bg-gradient-to-br from-blue-50 via-white to-red-50 dark:from-blue-900/20 dark:via-gray-900 dark:to-red-900/20 rounded-lg">
      <div className="text-center mb-8">
        <h3 className="text-3xl font-bold text-[#2d5a3d] mb-4">
          {title || defaultTitle}
        </h3>
        <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
          {description || defaultDescription}
        </p>
      </div>

      <Card className="overflow-hidden bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm">
        <CardContent className="p-8">
          <div className="relative w-full max-w-lg mx-auto">
            <svg width="400" height="400" className="w-full h-auto">
              {[50, 100, 150, 200].map((radius) => (
                <circle
                  key={radius}
                  cx="200"
                  cy="200"
                  r={radius}
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1"
                  opacity="0.1"
                />
              ))}

              {decades.map((decade, index) => {
                const angle = (index / decades.length) * rotations * Math.PI;
                const radius = 20 + (index / decades.length) * 120;
                const x = 200 + Math.cos(angle) * (radius + 30);
                const y = 200 + Math.sin(angle) * (radius + 30);

                return (
                  <text
                    key={decade}
                    x={x}
                    y={y}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    className="text-xs font-medium fill-current text-muted-foreground"
                  >
                    {decade}
                  </text>
                );
              })}

              {spiralData.map((point, index) => (
                <circle
                  key={index}
                  cx={point.x}
                  cy={point.y}
                  r={point.radius}
                  fill={point.color}
                  opacity="0.8"
                >
                  <title>{`${point.year}: ${
                    point.temp > 0 ? "+" : ""
                  }${point.temp.toFixed(2)}°C`}</title>
                </circle>
              ))}

              <circle
                cx="200"
                cy="200"
                r="8"
                fill="#2d5a3d"
                className="drop-shadow-lg"
              />
              <text
                x="200"
                y="200"
                textAnchor="middle"
                dominantBaseline="middle"
                className="text-xs font-bold fill-white"
              >
                {startYear}
              </text>
            </svg>
          </div>

          <div className="mt-8 flex justify-center gap-8 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-blue-500 rounded-full"></div>
              <span>{language === "de" ? "Kälter" : "Cooler"}</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-orange-500 rounded-full"></div>
              <span>{language === "de" ? "Wärmer" : "Warmer"}</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-red-500 rounded-full"></div>
              <span>{language === "de" ? "Heißer" : "Hotter"}</span>
            </div>
          </div>

          <div className="mt-6 text-center text-sm text-muted-foreground">
            <p>
              {language === "de"
                ? "Die äußeren Ringe zeigen die jüngsten Jahre mit deutlich höheren Temperaturen"
                : "Outer rings show recent years with significantly higher temperatures"}
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
