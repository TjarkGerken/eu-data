"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useLanguage } from "@/contexts/language-context"
import { Thermometer, Droplets, Wind, Zap, TreePine, Factory } from "lucide-react"

export function ClimateInfographic() {
  const { language } = useLanguage()

  const climateData = [
    {
      icon: Thermometer,
      value: "+1.2°C",
      label: language === "de" ? "Globale Erwärmung" : "Global Warming",
      description: language === "de" ? "seit 1880" : "since 1880",
      color: "text-red-500",
      bgColor: "bg-red-50 dark:bg-red-900/20",
      progress: 80,
    },
    {
      icon: Droplets,
      value: "421ppm",
      label: "CO₂",
      description: language === "de" ? "Rekordwerte" : "Record levels",
      color: "text-orange-500",
      bgColor: "bg-orange-50 dark:bg-orange-900/20",
      progress: 95,
    },
    {
      icon: Wind,
      value: "42%",
      label: language === "de" ? "Erneuerbare" : "Renewables",
      description: language === "de" ? "EU Strom" : "EU electricity",
      color: "text-green-500",
      bgColor: "bg-green-50 dark:bg-green-900/20",
      progress: 42,
    },
    {
      icon: Zap,
      value: "-32%",
      label: language === "de" ? "Emissionen" : "Emissions",
      description: language === "de" ? "seit 1990" : "since 1990",
      color: "text-blue-500",
      bgColor: "bg-blue-50 dark:bg-blue-900/20",
      progress: 68,
    },
    {
      icon: TreePine,
      value: "3.1B",
      label: language === "de" ? "Bäume" : "Trees",
      description: language === "de" ? "EU Aufforstung" : "EU reforestation",
      color: "text-emerald-500",
      bgColor: "bg-emerald-50 dark:bg-emerald-900/20",
      progress: 65,
    },
    {
      icon: Factory,
      value: "55%",
      label: language === "de" ? "Industrie" : "Industry",
      description: language === "de" ? "Dekarbonisierung" : "decarbonization",
      color: "text-purple-500",
      bgColor: "bg-purple-50 dark:bg-purple-900/20",
      progress: 55,
    },
  ]

  return (
    <div className="my-16 p-8 bg-gradient-to-br from-slate-50 to-blue-50 dark:from-slate-900 dark:to-blue-900 rounded-lg">
      <div className="text-center mb-12">
        <h3 className="text-3xl font-bold text-[#2d5a3d] mb-4">
          {language === "de" ? "Klimawandel auf einen Blick" : "Climate Change at a Glance"}
        </h3>
        <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
          {language === "de"
            ? "Die wichtigsten Kennzahlen zur aktuellen Klimasituation"
            : "Key metrics on the current climate situation"}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {climateData.map((item, index) => (
          <Card
            key={index}
            className={`${item.bgColor} border-none shadow-lg hover:shadow-xl transition-shadow duration-300`}
          >
            <CardContent className="p-6">
              <div className="flex items-start justify-between mb-4">
                <div className={`p-3 rounded-full bg-white dark:bg-gray-800 shadow-sm ${item.color}`}>
                  <item.icon className="h-6 w-6" />
                </div>
                <Badge variant="secondary" className="text-xs">
                  {language === "de" ? "Aktuell" : "Current"}
                </Badge>
              </div>

              <div className="space-y-3">
                <div>
                  <div className={`text-3xl font-bold ${item.color}`}>{item.value}</div>
                  <div className="text-sm font-medium text-foreground">{item.label}</div>
                  <div className="text-xs text-muted-foreground">{item.description}</div>
                </div>

                {/* Progress bar */}
                <div className="space-y-2">
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>{language === "de" ? "Fortschritt" : "Progress"}</span>
                    <span>{item.progress}%</span>
                  </div>
                  <div className="w-full bg-white/50 dark:bg-gray-700/50 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full transition-all duration-1000 ${item.color.replace("text-", "bg-")}`}
                      style={{ width: `${item.progress}%` }}
                    />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Summary section */}
      <div className="mt-12 text-center">
        <Card className="bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm border-[#2d5a3d]/20">
          <CardContent className="p-8">
            <h4 className="text-xl font-semibold text-[#2d5a3d] mb-4">
              {language === "de" ? "Zusammenfassung" : "Summary"}
            </h4>
            <p className="text-muted-foreground leading-relaxed max-w-3xl mx-auto">
              {language === "de"
                ? "Europa macht bedeutende Fortschritte bei der Bekämpfung des Klimawandels, aber die Herausforderungen bleiben groß. Die Kombination aus erneuerbaren Energien, Emissionsreduktion und Aufforstung zeigt den Weg zu einer nachhaltigen Zukunft."
                : "Europe is making significant progress in combating climate change, but challenges remain substantial. The combination of renewable energy, emission reduction, and reforestation shows the path to a sustainable future."}
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
