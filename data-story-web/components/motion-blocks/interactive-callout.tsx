"use client"

import { motion } from "framer-motion"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { AlertTriangle, ExternalLink, Info, Lightbulb } from "lucide-react"
import { useLanguage } from "@/contexts/language-context"
import { useState } from "react"

interface CalloutData {
  type: "warning" | "info" | "tip"
  title: string
  content: string
  action?: {
    label: string
    url: string
  }
  stats?: {
    label: string
    value: string
  }[]
}

export function InteractiveCallout() {
  const { language } = useLanguage()
  const [isExpanded, setIsExpanded] = useState(false)

  const callout: CalloutData = {
    type: "warning",
    title:
      language === "de" ? "Kritischer Wendepunkt: Die nächsten 10 Jahre" : "Critical Turning Point: The Next 10 Years",
    content:
      language === "de"
        ? "Wissenschaftler warnen, dass wir uns einem kritischen Wendepunkt nähern. Ohne drastische Maßnahmen bis 2030 könnten irreversible Klimaveränderungen eintreten. Europa hat bereits bedeutende Fortschritte gemacht, aber die Geschwindigkeit der Veränderung muss sich verdoppeln, um die Pariser Klimaziele zu erreichen."
        : "Scientists warn we are approaching a critical tipping point. Without drastic action by 2030, irreversible climate changes could occur. Europe has already made significant progress, but the pace of change must double to meet Paris climate goals.",
    action: {
      label: language === "de" ? "Mehr erfahren" : "Learn More",
      url: "https://www.ipcc.ch/",
    },
    stats: [
      {
        label: language === "de" ? "Verbleibendes CO₂-Budget" : "Remaining CO₂ Budget",
        value: "400 Gt",
      },
      {
        label: language === "de" ? "Jahre bis zum Ziel" : "Years to Target",
        value: "7",
      },
      {
        label: language === "de" ? "Benötigte Reduktion/Jahr" : "Required Reduction/Year",
        value: "7.6%",
      },
    ],
  }

  const getIcon = () => {
    switch (callout.type) {
      case "warning":
        return AlertTriangle
      case "info":
        return Info
      case "tip":
        return Lightbulb
      default:
        return Info
    }
  }

  const getColors = () => {
    switch (callout.type) {
      case "warning":
        return {
          bg: "bg-orange-50 dark:bg-orange-900/10",
          border: "border-orange-200 dark:border-orange-800",
          icon: "text-orange-600 dark:text-orange-400",
          badge: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300",
        }
      case "info":
        return {
          bg: "bg-blue-50 dark:bg-blue-900/10",
          border: "border-blue-200 dark:border-blue-800",
          icon: "text-blue-600 dark:text-blue-400",
          badge: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300",
        }
      case "tip":
        return {
          bg: "bg-green-50 dark:bg-green-900/10",
          border: "border-green-200 dark:border-green-800",
          icon: "text-green-600 dark:text-green-400",
          badge: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300",
        }
    }
  }

  const Icon = getIcon()
  const colors = getColors()

  return (
    <div className="my-16">
      <motion.div
        initial={{ opacity: 0, y: 50 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.8, ease: "easeOut" }}
      >
        <Card className={`${colors.bg} ${colors.border} border-2 overflow-hidden`}>
          <CardContent className="p-0">
            <motion.div
              className="p-6 cursor-pointer"
              onClick={() => setIsExpanded(!isExpanded)}
              whileHover={{ scale: 1.01 }}
              transition={{ type: "spring", stiffness: 300 }}
            >
              <div className="flex items-start gap-4">
                <motion.div
                  animate={{ rotate: isExpanded ? 360 : 0 }}
                  transition={{ duration: 0.5 }}
                  className={`flex-shrink-0 p-3 rounded-full bg-background shadow-sm ${colors.icon}`}
                >
                  <Icon className="h-6 w-6" />
                </motion.div>

                <div className="flex-1 space-y-3">
                  <div className="flex items-center gap-2">
                    <Badge className={colors.badge}>{language === "de" ? "Wichtig" : "Important"}</Badge>
                  </div>

                  <h4 className="text-xl font-semibold text-foreground">{callout.title}</h4>

                  <motion.div
                    initial={false}
                    animate={{ height: isExpanded ? "auto" : 0, opacity: isExpanded ? 1 : 0 }}
                    transition={{ duration: 0.3 }}
                    className="overflow-hidden"
                  >
                    <div className="space-y-4">
                      <p className="text-muted-foreground leading-relaxed">{callout.content}</p>

                      {callout.stats && (
                        <motion.div
                          initial={{ opacity: 0, y: 20 }}
                          animate={{ opacity: isExpanded ? 1 : 0, y: isExpanded ? 0 : 20 }}
                          transition={{ delay: 0.2, duration: 0.3 }}
                          className="grid grid-cols-3 gap-4 p-4 bg-background/50 rounded-lg"
                        >
                          {callout.stats.map((stat, index) => (
                            <div key={index} className="text-center">
                              <div className="text-2xl font-bold text-[#2d5a3d]">{stat.value}</div>
                              <div className="text-xs text-muted-foreground">{stat.label}</div>
                            </div>
                          ))}
                        </motion.div>
                      )}

                      {callout.action && (
                        <motion.div
                          initial={{ opacity: 0, y: 20 }}
                          animate={{ opacity: isExpanded ? 1 : 0, y: isExpanded ? 0 : 20 }}
                          transition={{ delay: 0.3, duration: 0.3 }}
                        >
                          <Button asChild className="bg-[#2d5a3d] hover:bg-[#2d5a3d]/90">
                            <a href={callout.action.url} target="_blank" rel="noopener noreferrer">
                              {callout.action.label}
                              <ExternalLink className="h-4 w-4 ml-2" />
                            </a>
                          </Button>
                        </motion.div>
                      )}
                    </div>
                  </motion.div>

                  <div className="text-sm text-muted-foreground">
                    {isExpanded
                      ? language === "de"
                        ? "Klicken zum Schließen"
                        : "Click to collapse"
                      : language === "de"
                        ? "Klicken für Details"
                        : "Click for details"}
                  </div>
                </div>
              </div>
            </motion.div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  )
}
