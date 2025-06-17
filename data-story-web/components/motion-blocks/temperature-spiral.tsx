"use client"

import { Card, CardContent } from "@/components/ui/card"
import { useLanguage } from "@/contexts/language-context"
import { useMemo } from "react"

export function TemperatureSpiral() {
  const { language } = useLanguage()

  // Generate temperature spiral data (simplified version)
  const spiralData = useMemo(() => {
    const data = []
    const years = 150 // 1880-2030
    const centerX = 200
    const centerY = 200

    for (let i = 0; i < years; i++) {
      const year = 1880 + i
      const angle = (i / years) * 8 * Math.PI // 8 full rotations
      const baseRadius = 20
      const tempAnomaly = Math.sin(i * 0.1) * 0.5 + (i / years) * 1.5 // Simulated warming trend
      const radius = baseRadius + (i / years) * 120 + tempAnomaly * 20

      const x = centerX + Math.cos(angle) * radius
      const y = centerY + Math.sin(angle) * radius

      // Color based on temperature
      const temp = tempAnomaly
      let color = "#3b82f6" // Blue for cold
      if (temp > 0.5)
        color = "#ef4444" // Red for hot
      else if (temp > 0) color = "#f59e0b" // Orange for warm

      data.push({
        x,
        y,
        year,
        temp: tempAnomaly,
        color,
        radius: 2 + Math.abs(tempAnomaly) * 2,
      })
    }
    return data
  }, [])

  const decades = [1880, 1900, 1920, 1940, 1960, 1980, 2000, 2020]

  return (
    <div className="my-16 p-8 bg-gradient-to-br from-blue-50 via-white to-red-50 dark:from-blue-900/20 dark:via-gray-900 dark:to-red-900/20 rounded-lg">
      <div className="text-center mb-8">
        <h3 className="text-3xl font-bold text-[#2d5a3d] mb-4">
          {language === "de" ? "Temperaturspirale 1880-2030" : "Temperature Spiral 1880-2030"}
        </h3>
        <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
          {language === "de"
            ? "Jeder Punkt repräsentiert ein Jahr - die Spirale zeigt die beschleunigte Erwärmung"
            : "Each dot represents a year - the spiral shows accelerated warming"}
        </p>
      </div>

      <Card className="overflow-hidden bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm">
        <CardContent className="p-8">
          <div className="relative w-full max-w-lg mx-auto">
            <svg width="400" height="400" className="w-full h-auto">
              {/* Background circles for reference */}
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

              {/* Decade labels */}
              {decades.map((decade, index) => {
                const angle = (index / decades.length) * 8 * Math.PI
                const radius = 20 + (index / decades.length) * 120
                const x = 200 + Math.cos(angle) * (radius + 30)
                const y = 200 + Math.sin(angle) * (radius + 30)

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
                )
              })}

              {/* Temperature spiral */}
              {spiralData.map((point, index) => (
                <circle key={index} cx={point.x} cy={point.y} r={point.radius} fill={point.color} opacity="0.8">
                  <title>{`${point.year}: ${point.temp > 0 ? "+" : ""}${point.temp.toFixed(2)}°C`}</title>
                </circle>
              ))}

              {/* Center point */}
              <circle cx="200" cy="200" r="8" fill="#2d5a3d" className="drop-shadow-lg" />
              <text
                x="200"
                y="200"
                textAnchor="middle"
                dominantBaseline="middle"
                className="text-xs font-bold fill-white"
              >
                1880
              </text>
            </svg>
          </div>

          {/* Legend */}
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
  )
}
