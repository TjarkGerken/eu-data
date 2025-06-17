"use client";

import type React from "react"

import { motion } from "framer-motion"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Calendar, Thermometer, Droplets, Wind, AlertTriangle } from "lucide-react"
import { useLanguage } from "@/contexts/language-context"

interface TimelineEvent {
  year: number
  title: string
  description: string
  type: "temperature" | "precipitation" | "policy" | "extreme"
  icon: React.ComponentType<{ className?: string }>
  color: string
}

export function ClimateTimeline() {
  const { language } = useLanguage()

  const events: TimelineEvent[] = [
    {
      year: 1990,
      title: language === "de" ? "Referenzjahr für Emissionen" : "Emissions Reference Year",
      description:
        language === "de" ? "Basislinie für EU-Klimaziele festgelegt" : "Baseline established for EU climate targets",
      type: "policy",
      icon: Calendar,
      color: "bg-blue-500",
    },
    {
      year: 2003,
      title: language === "de" ? "Jahrhundertsommer" : "Century Summer",
      description:
        language === "de" ? "Extreme Hitzewelle fordert 70.000 Todesopfer" : "Extreme heatwave claims 70,000 lives",
      type: "extreme",
      icon: AlertTriangle,
      color: "bg-red-500",
    },
    {
      year: 2009,
      title: language === "de" ? "Erneuerbare Energien Richtlinie" : "Renewable Energy Directive",
      description:
        language === "de" ? "EU setzt 20% Ziel für erneuerbare Energien" : "EU sets 20% renewable energy target",
      type: "policy",
      icon: Wind,
      color: "bg-green-500",
    },
    {
      year: 2016,
      title: language === "de" ? "Pariser Abkommen" : "Paris Agreement",
      description: language === "de" ? "EU verpflichtet sich zu 1.5°C Ziel" : "EU commits to 1.5°C target",
      type: "policy",
      icon: Thermometer,
      color: "bg-orange-500",
    },
    {
      year: 2021,
      title: language === "de" ? "Rekordfluten" : "Record Floods",
      description:
        language === "de" ? "Jahrhundertflut in Deutschland und Belgien" : "Century floods in Germany and Belgium",
      type: "extreme",
      icon: Droplets,
      color: "bg-blue-600",
    },
    {
      year: 2023,
      title: language === "de" ? "Heißester Sommer" : "Hottest Summer",
      description:
        language === "de" ? "Neue Temperaturrekorde in ganz Europa" : "New temperature records across Europe",
      type: "temperature",
      icon: Thermometer,
      color: "bg-red-600",
    },
  ]

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.3,
      },
    },
  }

  const itemVariants = {
    hidden: { x: -50, opacity: 0 },
    visible: {
      x: 0,
      opacity: 1,
      transition: {
        duration: 0.8,
        ease: "easeOut",
      },
    },
  }

  return (
    <div className="my-16 p-8 bg-gradient-to-br from-[#2d5a3d]/10 to-[#c4a747]/10 rounded-lg">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6 }}
        className="text-center mb-12"
      >
        <h3 className="text-3xl font-bold text-[#2d5a3d] mb-4">
          {language === "de" ? "Klimawandel Zeitlinie" : "Climate Change Timeline"}
        </h3>
        <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
          {language === "de"
            ? "Wichtige Ereignisse und Meilensteine der letzten Jahrzehnte"
            : "Key events and milestones from recent decades"}
        </p>
      </motion.div>

      <motion.div
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: "-100px" }}
        variants={containerVariants}
        className="relative"
      >
        <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-gradient-to-b from-[#2d5a3d] to-[#c4a747]" />

        <div className="space-y-8">
          {events.map((event, index) => (
            <motion.div key={event.year} variants={itemVariants} className="relative flex items-start gap-6">
              <motion.div
                whileHover={{ scale: 1.2 }}
                className={`relative z-10 flex items-center justify-center w-16 h-16 rounded-full ${event.color} shadow-lg`}
              >
                <event.icon className="h-6 w-6 text-white" />
              </motion.div>

              <motion.div
                whileHover={{ scale: 1.02 }}
                transition={{ type: "spring", stiffness: 300 }}
                className="flex-1"
              >
                <Card className="overflow-hidden">
                  <CardContent className="p-6">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <Badge variant="outline" className="mb-2">
                          {event.year}
                        </Badge>
                        <h4 className="text-xl font-semibold text-[#2d5a3d]">{event.title}</h4>
                      </div>
                    </div>
                    <p className="text-muted-foreground leading-relaxed">{event.description}</p>
                  </CardContent>
                </Card>
              </motion.div>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </div>
  )
}
