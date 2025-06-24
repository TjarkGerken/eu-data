"use client";

import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useLanguage } from "@/contexts/language-context"

export function ClimateMapStatic() {
  const { language } = useLanguage()

  const countries = [
    { name: "Norway", x: 50, y: 15, temp: 2.1, renewable: 98, color: "#dc2626" },
    { name: "Sweden", x: 55, y: 20, temp: 1.8, renewable: 65, color: "#dc2626" },
    { name: "Finland", x: 65, y: 18, temp: 2.3, renewable: 45, color: "#dc2626" },
    { name: "Denmark", x: 48, y: 35, temp: 1.5, renewable: 80, color: "#f97316" },
    { name: "Germany", x: 48, y: 45, temp: 1.6, renewable: 46, color: "#f97316" },
    { name: "France", x: 40, y: 55, temp: 1.4, renewable: 23, color: "#f97316" },
    { name: "Spain", x: 25, y: 75, temp: 1.3, renewable: 47, color: "#f59e0b" },
    { name: "Italy", x: 50, y: 70, temp: 1.5, renewable: 40, color: "#f97316" },
    { name: "Poland", x: 60, y: 45, temp: 1.7, renewable: 16, color: "#f97316" },
    { name: "UK", x: 30, y: 35, temp: 1.2, renewable: 43, color: "#f59e0b" },
  ]

  const getTemperatureColor = (temp: number): string => {
    if (temp < 0.5) return "#3b82f6"; // blue for lower temps
    if (temp < 1.0) return "#f59e0b"; // amber for medium temps
    return "#ef4444"; // red for higher temps
  }

  const getRenewableColor = (renewable: number): string => {
    if (renewable < 25) return "#ef4444"; // red for low renewable
    if (renewable < 50) return "#f59e0b"; // amber for medium renewable
    return "#10b981"; // green for high renewable
  }

  return (
    <div className="my-16 p-8 bg-gradient-to-br from-blue-50 via-green-50 to-yellow-50 dark:from-blue-900/20 dark:via-green-900/20 dark:to-yellow-900/20 rounded-lg">
      <div className="text-center mb-8">
        <h3 className="text-3xl font-bold text-[#2d5a3d] mb-4">
          {language === "de" ? "Europäische Klimakarte" : "European Climate Map"}
        </h3>
        <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
          {language === "de"
            ? "Temperaturanstieg und erneuerbare Energien nach Ländern"
            : "Temperature rise and renewable energy by country"}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <Card className="overflow-hidden">
          <CardContent className="p-6">
            <h4 className="text-xl font-semibold text-[#2d5a3d] mb-4 text-center">
              {language === "de" ? "Temperaturanstieg seit 1900" : "Temperature Rise Since 1900"}
            </h4>

            <div className="relative bg-gradient-to-b from-blue-100 to-green-100 dark:from-blue-900/30 dark:to-green-900/30 rounded-lg p-4 h-80">
              <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100">
                <path
                  d="M20,30 Q30,25 40,30 Q50,20 60,25 Q70,15 75,25 Q80,30 75,40 Q70,50 65,60 Q60,70 50,75 Q40,80 30,75 Q20,70 15,60 Q10,50 15,40 Q20,35 20,30 Z"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="0.5"
                  opacity="0.3"
                />

                {countries.map((country, index) => (
                  <g key={index}>
                    <circle
                      cx={country.x}
                      cy={country.y}
                      r="3"
                      fill={getTemperatureColor(country.temp)}
                      className="hover:r-4 transition-all cursor-pointer"
                    >
                      <title>{`${country.name}: +${country.temp}°C`}</title>
                    </circle>
                    <text
                      x={country.x}
                      y={country.y - 5}
                      textAnchor="middle"
                      className="text-xs font-medium fill-current"
                      style={{ fontSize: "3px" }}
                    >
                      +{country.temp}°C
                    </text>
                  </g>
                ))}
              </svg>
            </div>

            <div className="flex justify-center gap-4 mt-4 text-xs">
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                <span>&lt;1.0°C</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 bg-amber-500 rounded-full"></div>
                <span>1.0-1.5°C</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 bg-orange-500 rounded-full"></div>
                <span>1.5-2.0°C</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                <span>&gt;2.0°C</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="overflow-hidden">
          <CardContent className="p-6">
            <h4 className="text-xl font-semibold text-[#2d5a3d] mb-4 text-center">
              {language === "de" ? "Erneuerbare Energien %" : "Renewable Energy %"}
            </h4>

            <div className="relative bg-gradient-to-b from-green-100 to-blue-100 dark:from-green-900/30 dark:to-blue-900/30 rounded-lg p-4 h-80">
              <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100">
                <path
                  d="M20,30 Q30,25 40,30 Q50,20 60,25 Q70,15 75,25 Q80,30 75,40 Q70,50 65,60 Q60,70 50,75 Q40,80 30,75 Q20,70 15,60 Q10,50 15,40 Q20,35 20,30 Z"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="0.5"
                  opacity="0.3"
                />

                {countries.map((country, index) => (
                  <g key={index}>
                    <circle
                      cx={country.x}
                      cy={country.y}
                      r="3"
                      fill={getRenewableColor(country.renewable)}
                      className="hover:r-4 transition-all cursor-pointer"
                    >
                      <title>{`${country.name}: ${country.renewable}%`}</title>
                    </circle>
                    <text
                      x={country.x}
                      y={country.y - 5}
                      textAnchor="middle"
                      className="text-xs font-medium fill-current"
                      style={{ fontSize: "3px" }}
                    >
                      {country.renewable}%
                    </text>
                  </g>
                ))}
              </svg>
            </div>

            <div className="flex justify-center gap-4 mt-4 text-xs">
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                <span>&lt;20%</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                <span>20-40%</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 bg-lime-500 rounded-full"></div>
                <span>40-70%</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                <span>&gt;70%</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="mt-8 grid grid-cols-2 md:grid-cols-5 gap-4">
        {countries.slice(0, 5).map((country, index) => (
          <Card key={index} className="text-center">
            <CardContent className="p-4">
              <h5 className="font-semibold text-sm mb-2">{country.name}</h5>
              <div className="space-y-1">
                <Badge variant="outline" className="text-xs">
                  +{country.temp}°C
                </Badge>
                <Badge variant="outline" className="text-xs">
                  {country.renewable}% {language === "de" ? "Erneuerbar" : "Renewable"}
                </Badge>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
