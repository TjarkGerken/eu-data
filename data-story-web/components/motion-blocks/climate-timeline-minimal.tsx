"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useLanguage } from "@/contexts/language-context"
import { Calendar, Thermometer, Zap, TreePine, Factory, Globe } from "lucide-react"

export function ClimateTimelineMinimal() {
  const { language } = useLanguage()

  const events = [
    {
      year: 1880,
      title: language === "de" ? "Temperaturmessungen beginnen" : "Temperature Records Begin",
      description: language === "de" ? "Erste systematische globale Messungen" : "First systematic global measurements",
      icon: Thermometer,
      color: "bg-blue-500",
      impact: "baseline",
    },
    {
      year: 1958,
      title: language === "de" ? "Keeling-Kurve startet" : "Keeling Curve Starts",
      description: language === "de" ? "CO₂-Messungen am Mauna Loa" : "CO₂ measurements at Mauna Loa",
      icon: Globe,
      color: "bg-purple-500",
      impact: "monitoring",
    },
    {
      year: 1988,
      title: "IPCC " + (language === "de" ? "gegründet" : "Founded"),
      description: language === "de" ? "Wissenschaftlicher Klimarat etabliert" : "Scientific climate panel established",
      icon: Calendar,
      color: "bg-indigo-500",
      impact: "science",
    },
    {
      year: 1997,
      title: language === "de" ? "Kyoto-Protokoll" : "Kyoto Protocol",
      description: language === "de" ? "Erstes globales Klimaabkommen" : "First global climate agreement",
      icon: Factory,
      color: "bg-orange-500",
      impact: "policy",
    },
    {
      year: 2015,
      title: language === "de" ? "Paris-Abkommen" : "Paris Agreement",
      description: language === "de" ? "1.5°C Ziel vereinbart" : "1.5°C target agreed",
      icon: Globe,
      color: "bg-green-500",
      impact: "commitment",
    },
    {
      year: 2019,
      title: language === "de" ? "European Green Deal" : "European Green Deal",
      description: language === "de" ? "EU Klimaneutralität bis 2050" : "EU climate neutrality by 2050",
      icon: TreePine,
      color: "bg-emerald-500",
      impact: "action",
    },
    {
      year: 2023,
      title: language === "de" ? "Heißestes Jahr" : "Hottest Year",
      description: language === "de" ? "Neue Temperaturrekorde weltweit" : "New temperature records worldwide",
      icon: Thermometer,
      color: "bg-red-500",
      impact: "crisis",
    },
    {
      year: 2030,
      title: language === "de" ? "Klimaziele" : "Climate Targets",
      description: language === "de" ? "55% Emissionsreduktion geplant" : "55% emission reduction planned",
      icon: Zap,
      color: "bg-cyan-500",
      impact: "future",
    },
  ]

  const getImpactBadge = (impact: string) => {
    const badges = {
      baseline: { text: language === "de" ? "Grundlage" : "Baseline", variant: "secondary" as const },
      monitoring: { text: language === "de" ? "Überwachung" : "Monitoring", variant: "secondary" as const },
      science: { text: language === "de" ? "Wissenschaft" : "Science", variant: "outline" as const },
      policy: { text: language === "de" ? "Politik" : "Policy", variant: "outline" as const },
      commitment: { text: language === "de" ? "Verpflichtung" : "Commitment", variant: "default" as const },
      action: { text: language === "de" ? "Aktion" : "Action", variant: "default" as const },
      crisis: { text: language === "de" ? "Krise" : "Crisis", variant: "destructive" as const },
      future: { text: language === "de" ? "Zukunft" : "Future", variant: "secondary" as const },
    }
    return badges[impact as keyof typeof badges] || badges.baseline
  }

  return (
    <div className="my-16 p-8 bg-gradient-to-r from-slate-50 to-gray-50 dark:from-slate-900 dark:to-gray-900 rounded-lg">
      <div className="text-center mb-12">
        <h3 className="text-3xl font-bold text-[#2d5a3d] mb-4">
          {language === "de" ? "Klimageschichte im Überblick" : "Climate History Overview"}
        </h3>
        <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
          {language === "de"
            ? "Wichtige Meilensteine in der Klimaforschung und -politik"
            : "Key milestones in climate science and policy"}
        </p>
      </div>

      <div className="relative">
        {/* Timeline line */}
        <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-gradient-to-b from-[#2d5a3d] via-[#c4a747] to-[#2d5a3d]"></div>

        <div className="space-y-8">
          {events.map((event, index) => (
            <div key={event.year} className="relative flex items-start gap-6">
              {/* Timeline dot */}
              <div
                className={`relative z-10 flex items-center justify-center w-16 h-16 rounded-full ${event.color} shadow-lg flex-shrink-0`}
              >
                <event.icon className="h-6 w-6 text-white" />
              </div>

              {/* Content */}
              <Card className="flex-1 hover:shadow-md transition-shadow duration-300">
                <CardContent className="p-6">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <div className="flex items-center gap-3 mb-2">
                        <Badge variant="outline" className="font-mono">
                          {event.year}
                        </Badge>
                        <Badge {...getImpactBadge(event.impact)}>{getImpactBadge(event.impact).text}</Badge>
                      </div>
                      <h4 className="text-xl font-semibold text-[#2d5a3d] mb-2">{event.title}</h4>
                    </div>
                  </div>
                  <p className="text-muted-foreground leading-relaxed">{event.description}</p>
                </CardContent>
              </Card>
            </div>
          ))}
        </div>
      </div>

      {/* Summary */}
      <div className="mt-12 text-center">
        <Card className="bg-gradient-to-r from-[#2d5a3d]/5 to-[#c4a747]/5 border-none">
          <CardContent className="p-8">
            <h4 className="text-xl font-semibold text-[#2d5a3d] mb-4">
              {language === "de" ? "Von der Erkenntnis zur Aktion" : "From Recognition to Action"}
            </h4>
            <p className="text-muted-foreground leading-relaxed max-w-3xl mx-auto">
              {language === "de"
                ? "Diese Zeitlinie zeigt den Weg von den ersten Klimamessungen bis zu den heutigen Klimaschutzmaßnahmen. Jeder Meilenstein hat unser Verständnis vertieft und den Grundstein für zukünftige Aktionen gelegt."
                : "This timeline shows the journey from first climate measurements to today's climate action. Each milestone has deepened our understanding and laid the foundation for future actions."}
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
