"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { useLanguage } from "@/contexts/language-context";

interface WaveSliderProps {
  scenarios: Array<{
    id: string;
    name: string;
  }>;
  selectedScenario: string;
  onScenarioChange: (scenarioId: string) => void;
  className?: string;
}

// Wave slider translations
const waveSliderTranslations = {
  en: {
    title: "Sea Level Rise Scenarios",
    current: "Current",
    none: "None"
  },
  de: {
    title: "Meeresspiegelanstieg-Szenarien",
    current: "Aktuell",
    none: "Keine"
  }
};

export function WaveSlider({
  scenarios,
  selectedScenario,
  onScenarioChange,
  className,
}: WaveSliderProps) {
  const { language } = useLanguage();
  const t = waveSliderTranslations[language];
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const selectedIndex = scenarios.findIndex((s) => s.id === selectedScenario);

  // Get scenario colors based on severity (green -> yellow -> orange -> dark red)
  const getScenarioColors = (index: number) => {
    const colors = [
      {
        bg: "bg-green-100/80",
        bgSelected: "bg-green-600",
        text: "text-green-900",
        textSelected: "text-white",
        border: "border-green-700",
        shadow: "rgba(34, 197, 94, 0.4)",
        waterLevel: "bg-green-400/60",
        waterLevelInactive: "bg-green-300/40",
      },
      {
        bg: "bg-yellow-100/80",
        bgSelected: "bg-yellow-600",
        text: "text-yellow-900",
        textSelected: "text-white",
        border: "border-yellow-700",
        shadow: "rgba(234, 179, 8, 0.4)",
        waterLevel: "bg-yellow-400/60",
        waterLevelInactive: "bg-yellow-300/40",
      },
      {
        bg: "bg-orange-100/80",
        bgSelected: "bg-orange-600",
        text: "text-orange-900",
        textSelected: "text-white",
        border: "border-orange-700",
        shadow: "rgba(234, 88, 12, 0.4)",
        waterLevel: "bg-orange-400/60",
        waterLevelInactive: "bg-orange-300/40",
      },
      {
        bg: "bg-red-100/80",
        bgSelected: "bg-red-800",
        text: "text-red-900",
        textSelected: "text-white",
        border: "border-red-900",
        shadow: "rgba(153, 27, 27, 0.4)",
        waterLevel: "bg-red-500/60",
        waterLevelInactive: "bg-red-400/40",
      },
    ];

    // Use modulo to cycle through colors if there are more than 4 scenarios
    return colors[index % colors.length];
  };

  return (
    <div className={cn("w-full space-y-3", className)}>
      <div className="text-sm font-medium text-center">
        {t.title}
      </div>

      <div className="relative bg-stone-100 rounded-lg p-4 overflow-hidden border border-stone-200">
        {/* Wave background animation - earthy colors */}
        <div className="absolute inset-0 opacity-20">
          <svg
            viewBox="0 0 400 100"
            className="w-full h-full"
            preserveAspectRatio="none"
          >
            <path
              d="M0,50 Q100,20 200,50 T400,50 V100 H0 V50"
              fill="url(#earthyWaveGradient)"
              className="animate-pulse"
            />
            <defs>
              <linearGradient
                id="earthyWaveGradient"
                x1="0%"
                y1="0%"
                x2="100%"
                y2="0%"
              >
                <stop offset="0%" stopColor="#8b5cf6" />
                <stop offset="25%" stopColor="#a16207" />
                <stop offset="50%" stopColor="#78716c" />
                <stop offset="75%" stopColor="#57534e" />
                <stop offset="100%" stopColor="#44403c" />
              </linearGradient>
            </defs>
          </svg>
        </div>

        {/* Blue wave level indicator - subtle but visible */}
        <div
          className="absolute inset-x-0 transition-all duration-500 ease-in-out"
          style={{
            bottom: 0,
            height: `${
              20 + (selectedIndex / Math.max(scenarios.length - 1, 1)) * 60
            }%`,
            background:
              "linear-gradient(to top, rgba(59, 130, 246, 0.5), rgba(147, 197, 253, 0.3), rgba(191, 219, 254, 0.2))",
            boxShadow: "0 -2px 10px rgba(59, 130, 246, 0.2)",
          }}
        >
          {/* Animated water surface */}
          <div className="absolute top-0 inset-x-0 h-1 bg-blue-400 opacity-60">
            <div className="absolute inset-0 bg-gradient-to-r from-blue-300 via-blue-400 to-blue-300 animate-pulse"></div>
          </div>
        </div>

        {/* Scenario selection buttons */}
        <div className="relative z-10 grid grid-cols-4 gap-2">
          {scenarios.map((scenario, index) => {
            const isSelected = scenario.id === selectedScenario;
            const isHovered = hoveredIndex === index;
            const waveHeight =
              20 + (index / Math.max(scenarios.length - 1, 1)) * 60;
            const colors = getScenarioColors(index);

            return (
              <button
                key={scenario.id}
                onClick={() => onScenarioChange(scenario.id)}
                onMouseEnter={() => setHoveredIndex(index)}
                onMouseLeave={() => setHoveredIndex(null)}
                className={cn(
                  "relative p-3 rounded-lg text-xs font-medium transition-all duration-200",
                  "border-2 backdrop-blur-sm hover:backdrop-blur-md",
                  isSelected
                    ? `${colors.bgSelected} ${colors.textSelected} ${colors.border} shadow-lg`
                    : `${colors.bg} ${colors.text} border-white/50 hover:border-white/80 hover:bg-white/80`
                )}
                style={{
                  transform: isHovered ? "translateY(-2px)" : "none",
                  boxShadow: isSelected
                    ? `0 4px 20px ${colors.shadow}`
                    : isHovered
                    ? "0 2px 10px rgba(0, 0, 0, 0.1)"
                    : "none",
                }}
              >
                <div className="space-y-1">
                  <div className="font-semibold">{scenario.id}</div>
                  <div className="text-xs opacity-80 leading-tight">
                    {scenario.name}
                  </div>
                </div>

                {/* Water level indicator */}
                <div
                  className={cn(
                    "absolute bottom-0 left-0 right-0 rounded-b-lg transition-all duration-300",
                    isSelected ? colors.waterLevel : colors.waterLevelInactive
                  )}
                  style={{
                    height: `${Math.min(waveHeight / 2, 30)}px`,
                  }}
                />
              </button>
            );
          })}
        </div>

        {/* Current scenario label */}
        <div className="relative z-10 mt-3 text-center">
          <div className="text-sm text-stone-800 font-semibold bg-white/80 backdrop-blur-sm rounded-md px-3 py-1 inline-block shadow-sm border border-stone-200">
            {t.current}:{" "}
            {scenarios.find((s) => s.id === selectedScenario)?.name || t.none}
          </div>
        </div>
      </div>
    </div>
  );
}
