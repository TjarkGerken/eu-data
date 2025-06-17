"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { useLanguage } from "@/contexts/language-context"
import { TrendingUp, TrendingDown, AlertTriangle, CheckCircle, Clock, Target } from "lucide-react"

export function ClimateDashboard() {
  const { language } = useLanguage()

  const metrics = [
    {
      title: language === "de" ? "Globale Temperatur" : "Global Temperature",
      value: "+1.2°C",
      change: "+0.1°C",
      trend: "up" as const,
      status: "warning" as const,
      progress: 80,
      target: "1.5°C",
      description: language === "de" ? "über vorindustriellem Niveau" : "above pre-industrial level",
    },
    {
      title: "CO₂ Konzentration",
      value: "421ppm",
      change: "+2.4ppm",
      trend: "up" as const,
      status: "danger" as const,
      progress: 95,
      target: "350ppm",
      description: language === "de" ? "Rekordwerte erreicht" : "record levels reached",
    },
    {
      title: language === "de" ? "Erneuerbare Energie" : "Renewable Energy",
      value: "42%",
      change: "+3.2%",
      trend: "up" as const,
      status: "success" as const,
      progress: 42,
      target: "100%",
      description: language === "de" ? "EU Strommix" : "EU electricity mix",
    },
    {
      title: language === "de" ? "Emissionsreduktion" : "Emission Reduction",
      value: "32%",
      change: "+2.1%",
      trend: "up" as const,
      status: "success" as const,
      progress: 64,
      target: "55%",
      description: language === "de" ? "seit 1990" : "since 1990",
    },
  ]

  const getStatusColor = (status: string) => {
    switch (status) {
      case "success":
        return "text-green-600 bg-green-50 dark:bg-green-900/20"
      case "warning":
        return "text-orange-600 bg-orange-50 dark:bg-orange-900/20"
      case "danger":
        return "text-red-600 bg-red-50 dark:bg-red-900/20"
      default:
        return "text-gray-600 bg-gray-50 dark:bg-gray-900/20"
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "success":
        return CheckCircle
      case "warning":
        return Clock
      case "danger":
        return AlertTriangle
      default:
        return Target
    }
  }

  const getTrendIcon = (trend: string) => {
    return trend === "up" ? TrendingUp : TrendingDown
  }

  return (
    <div className="my-16 p-8 bg-gradient-to-br from-gray-50 to-slate-100 dark:from-gray-900 dark:to-slate-900 rounded-lg">
      <div className="text-center mb-8">
        <h3 className="text-3xl font-bold text-[#2d5a3d] mb-4">
          {language === "de" ? "Klima-Dashboard" : "Climate Dashboard"}
        </h3>
        <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
          {language === "de"
            ? "Echtzeitübersicht der wichtigsten Klimaindikatoren"
            : "Real-time overview of key climate indicators"}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        {metrics.map((metric, index) => {
          const StatusIcon = getStatusIcon(metric.status)
          const TrendIcon = getTrendIcon(metric.trend)

          return (
            <Card key={index} className="hover:shadow-lg transition-shadow duration-300">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">{metric.title}</CardTitle>
                  <div className={`p-2 rounded-full ${getStatusColor(metric.status)}`}>
                    <StatusIcon className="h-4 w-4" />
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-baseline justify-between">
                  <div className="text-3xl font-bold text-[#2d5a3d]">{metric.value}</div>
                  <div className="flex items-center gap-1 text-sm text-muted-foreground">
                    <TrendIcon className="h-3 w-3" />
                    {metric.change}
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">
                      {language === "de" ? "Fortschritt zum Ziel" : "Progress to target"}
                    </span>
                    <span className="font-medium">{metric.target}</span>
                  </div>
                  <Progress value={metric.progress} className="h-2" />
                  <div className="text-xs text-right text-muted-foreground">{metric.progress}%</div>
                </div>

                <p className="text-sm text-muted-foreground">{metric.description}</p>

                <Badge variant="secondary" className={`${getStatusColor(metric.status)} border-none`}>
                  {metric.status === "success" && (language === "de" ? "Auf Kurs" : "On Track")}
                  {metric.status === "warning" && (language === "de" ? "Aufmerksamkeit" : "Attention")}
                  {metric.status === "danger" && (language === "de" ? "Kritisch" : "Critical")}
                </Badge>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800">
          <CardContent className="p-6 text-center">
            <CheckCircle className="h-8 w-8 text-green-600 mx-auto mb-2" />
            <div className="text-2xl font-bold text-green-600">2</div>
            <div className="text-sm text-green-700 dark:text-green-300">
              {language === "de" ? "Ziele erreicht" : "Targets met"}
            </div>
          </CardContent>
        </Card>

        <Card className="bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800">
          <CardContent className="p-6 text-center">
            <Clock className="h-8 w-8 text-orange-600 mx-auto mb-2" />
            <div className="text-2xl font-bold text-orange-600">1</div>
            <div className="text-sm text-orange-700 dark:text-orange-300">
              {language === "de" ? "Aufmerksamkeit nötig" : "Needs attention"}
            </div>
          </CardContent>
        </Card>

        <Card className="bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800">
          <CardContent className="p-6 text-center">
            <AlertTriangle className="h-8 w-8 text-red-600 mx-auto mb-2" />
            <div className="text-2xl font-bold text-red-600">1</div>
            <div className="text-sm text-red-700 dark:text-red-300">
              {language === "de" ? "Kritische Bereiche" : "Critical areas"}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
