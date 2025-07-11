"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { useLanguage } from "@/contexts/language-context";

interface EconomicIndicatorSelectorProps {
  indicators: string[];
  selectedIndicator: string;
  onIndicatorChange: (indicator: string) => void;
  className?: string;
}

// Economic indicator translations
const economicIndicatorTranslations = {
  en: {
    title: "Economic Indicators",
    selected: "Selected",
    indicators: {
      Combined: "Combined",
      Freight: "Freight",
      Population: "Population",
      HRST: "HRST",
      GDP: "GDP",
    },
  },
  de: {
    title: "Wirtschaftsindikatoren",
    selected: "Ausgewählt",
    indicators: {
      Combined: "Kombiniert",
      Freight: "Fracht",
      Population: "Bevölkerung",
      HRST: "HRST",
      GDP: "BIP",
    },
  },
};

export function EconomicIndicatorSelector({
  indicators,
  selectedIndicator,
  onIndicatorChange,
  className,
}: EconomicIndicatorSelectorProps) {
  const { language } = useLanguage();
  const t = economicIndicatorTranslations[language];
  const [hoveredIndicator, setHoveredIndicator] = useState<string | null>(null);

  const getTranslatedIndicator = (indicator: string) => {
    return t.indicators[indicator as keyof typeof t.indicators] || indicator;
  };

  const getIndicatorStyles = (indicator: string) => {
    const colorMap = {
      Combined: {
        bg: "bg-purple-100/80",
        bgSelected: "bg-purple-600",
        text: "text-purple-900",
        textSelected: "text-white",
        border: "border-purple-600",
        shadow: "rgba(147, 51, 234, 0.4)",
        icon: "📊",
      },
      Freight: {
        bg: "bg-blue-100/80",
        bgSelected: "bg-blue-600",
        text: "text-blue-900",
        textSelected: "text-white",
        border: "border-blue-600",
        shadow: "rgba(37, 99, 235, 0.4)",
        icon: "🚛",
      },
      Population: {
        bg: "bg-green-100/80",
        bgSelected: "bg-green-600",
        text: "text-green-900",
        textSelected: "text-white",
        border: "border-green-600",
        shadow: "rgba(34, 197, 94, 0.4)",
        icon: "👥",
      },
      HRST: {
        bg: "bg-orange-100/80",
        bgSelected: "bg-orange-600",
        text: "text-orange-900",
        textSelected: "text-white",
        border: "border-orange-600",
        shadow: "rgba(234, 88, 12, 0.4)",
        icon: "🔬",
      },
      GDP: {
        bg: "bg-amber-100/80",
        bgSelected: "bg-amber-600",
        text: "text-amber-900",
        textSelected: "text-white",
        border: "border-amber-600",
        shadow: "rgba(245, 158, 11, 0.4)",
        icon: "💰",
      },
    };

    return colorMap[indicator as keyof typeof colorMap] || colorMap.Combined;
  };

  return (
    <div className={cn("w-full space-y-3", className)}>
      <div className="text-sm font-medium text-center">{t.title}</div>

      <div className="relative bg-gradient-to-br from-slate-50 to-slate-100 rounded-lg p-4 border border-slate-200">
        {/* Background pattern */}
        <div className="absolute inset-0 opacity-5">
          <svg
            viewBox="0 0 400 100"
            className="w-full h-full"
            preserveAspectRatio="none"
          >
            <pattern
              id="economicPattern"
              x="0"
              y="0"
              width="40"
              height="40"
              patternUnits="userSpaceOnUse"
            >
              <circle cx="20" cy="20" r="2" fill="currentColor" />
            </pattern>
            <rect width="100%" height="100%" fill="url(#economicPattern)" />
          </svg>
        </div>

        {/* Indicator selection buttons */}
        <div className="relative z-10 grid grid-cols-5 gap-2">
          {indicators.map((indicator) => {
            const isSelected = indicator === selectedIndicator;
            const isHovered = hoveredIndicator === indicator;
            const styles = getIndicatorStyles(indicator);

            return (
              <button
                key={indicator}
                onClick={() => onIndicatorChange(indicator)}
                onMouseEnter={() => setHoveredIndicator(indicator)}
                onMouseLeave={() => setHoveredIndicator(null)}
                className={cn(
                  "relative p-3 rounded-lg text-xs font-medium transition-all duration-200",
                  "border-2 backdrop-blur-sm hover:backdrop-blur-md min-h-[80px] flex flex-col items-center justify-center",
                  isSelected
                    ? `${styles.bgSelected} ${styles.textSelected} ${styles.border} shadow-lg`
                    : `${styles.bg} ${styles.text} border-white/50 hover:border-white/80 hover:bg-white/80`,
                )}
                style={{
                  transform: isHovered ? "translateY(-2px)" : "none",
                  boxShadow: isSelected
                    ? `0 4px 20px ${styles.shadow}`
                    : isHovered
                      ? "0 2px 10px rgba(0, 0, 0, 0.1)"
                      : "none",
                }}
              >
                <div className="space-y-1 text-center">
                  <div className="text-lg">{styles.icon}</div>
                  <div className="font-semibold text-xs leading-tight">
                    {getTranslatedIndicator(indicator)}
                  </div>
                </div>

                {/* Selection indicator */}
                {isSelected && (
                  <div className="absolute -top-1 -right-1 w-3 h-3 bg-white rounded-full shadow-sm border-2 border-current" />
                )}
              </button>
            );
          })}
        </div>

        {/* Current selection label */}
        <div className="relative z-10 mt-3 text-center">
          <div className="text-sm text-slate-800 font-semibold bg-white/80 backdrop-blur-sm rounded-md px-3 py-1 inline-block shadow-sm border border-slate-200">
            {t.selected}: {getTranslatedIndicator(selectedIndicator)}
          </div>
        </div>
      </div>
    </div>
  );
}
