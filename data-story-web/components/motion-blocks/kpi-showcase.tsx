"use client";

import type React from "react"

import { motion } from "framer-motion"
import { Card, CardContent } from "@/components/ui/card"
import { TrendingUp, TrendingDown, Thermometer, Droplets, Wind, Zap } from "lucide-react"
import { useLanguage } from "@/contexts/language-context"

interface KPI {
  icon: React.ComponentType<{ className?: string }>
  value: string
  label: string
  change: string
  trend: "up" | "down"
  color: string
}

export function KPIShowcase() {
  const { language } = useLanguage()

  const kpis: KPI[] = [
    {
      icon: Thermometer,
      value: "+1.2°C",
      label: language === "de" ? "Temperaturanstieg" : "Temperature Rise",
      change: language === "de" ? "seit 1990" : "since 1990",
      trend: "up",
      color: "text-red-500",
    },
    {
      icon: Droplets,
      value: "-15%",
      label: language === "de" ? "Sommerniederschlag" : "Summer Precipitation",
      change: language === "de" ? "Südeuropa" : "Southern Europe",
      trend: "down",
      color: "text-blue-500",
    },
    {
      icon: Wind,
      value: "42%",
      label: language === "de" ? "Erneuerbare Energie" : "Renewable Energy",
      change: language === "de" ? "EU-Durchschnitt" : "EU Average",
      trend: "up",
      color: "text-green-500",
    },
    {
      icon: Zap,
      value: "-32%",
      label: language === "de" ? "CO₂-Emissionen" : "CO₂ Emissions",
      change: language === "de" ? "seit 1990" : "since 1990",
      trend: "down",
      color: "text-emerald-500",
    },
  ]

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.2,
      },
    },
  }

  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: {
        duration: 0.6,
        ease: "easeOut",
      },
    },
  }

  return (
    <div className="my-16 p-8 bg-gradient-to-r from-[#2d5a3d]/5 to-[#c4a747]/5 rounded-lg">
      <motion.div
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: "-100px" }}
        variants={containerVariants}
        className="text-center mb-8"
      >
        <motion.h3 variants={itemVariants} className="text-3xl font-bold text-[#2d5a3d] mb-4">
          {language === "de" ? "Klimawandel in Zahlen" : "Climate Change by the Numbers"}
        </motion.h3>
        <motion.p variants={itemVariants} className="text-lg text-muted-foreground max-w-2xl mx-auto">
          {language === "de"
            ? "Schlüsselindikatoren zeigen das Ausmaß der Veränderungen in Europa"
            : "Key indicators showing the scale of change across Europe"}
        </motion.p>
      </motion.div>

      <motion.div
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: "-50px" }}
        variants={containerVariants}
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"
      >
        {kpis.map((kpi, index) => (
          <motion.div key={index} variants={itemVariants}>
            <Card className="relative overflow-hidden group hover:shadow-lg transition-shadow duration-300">
              <CardContent className="p-6 text-center">
                <motion.div
                  whileHover={{ scale: 1.1, rotate: 5 }}
                  transition={{ type: "spring", stiffness: 300 }}
                  className={`inline-flex p-3 rounded-full bg-background shadow-sm mb-4 ${kpi.color}`}
                >
                  <kpi.icon className="h-6 w-6" />
                </motion.div>

                <motion.div
                  initial={{ scale: 0.8 }}
                  whileInView={{ scale: 1 }}
                  transition={{ delay: 0.2 + index * 0.1, type: "spring", stiffness: 200 }}
                  className="space-y-2"
                >
                  <div className={`text-3xl font-bold ${kpi.color}`}>{kpi.value}</div>
                  <div className="text-sm font-medium text-foreground">{kpi.label}</div>
                  <div className="flex items-center justify-center gap-1 text-xs text-muted-foreground">
                    {kpi.trend === "up" ? (
                      <TrendingUp className="h-3 w-3 text-red-500" />
                    ) : (
                      <TrendingDown className="h-3 w-3 text-green-500" />
                    )}
                    {kpi.change}
                  </div>
                </motion.div>

                <motion.div
                  className="absolute inset-0 bg-gradient-to-r from-[#2d5a3d]/10 to-[#c4a747]/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                  initial={false}
                />
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </motion.div>
    </div>
  )
}
