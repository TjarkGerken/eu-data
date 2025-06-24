"use client";

import { motion } from "framer-motion"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { ArrowRight, TrendingUp, TrendingDown } from "lucide-react"
import { useLanguage } from "@/contexts/language-context"

interface ComparisonData {
  category: string
  before: { value: number; label: string }
  after: { value: number; label: string }
  unit: string
  trend: "positive" | "negative"
  color: string
}

export function ImpactComparison() {
  const { language } = useLanguage()

  const comparisons: ComparisonData[] = [
    {
      category: language === "de" ? "Erneuerbare Energie" : "Renewable Energy",
      before: { value: 8, label: "1990" },
      after: { value: 42, label: "2023" },
      unit: "%",
      trend: "positive",
      color: "bg-green-500",
    },
    {
      category: language === "de" ? "CO₂ Emissionen" : "CO₂ Emissions",
      before: { value: 100, label: "1990" },
      after: { value: 68, label: "2023" },
      unit: "%",
      trend: "positive",
      color: "bg-blue-500",
    },
    {
      category: language === "de" ? "Extreme Hitzetage" : "Extreme Heat Days",
      before: { value: 5, label: "1990-2000" },
      after: { value: 18, label: "2010-2023" },
      unit: language === "de" ? " Tage/Jahr" : " days/year",
      trend: "negative",
      color: "bg-red-500",
    },
    {
      category: language === "de" ? "Energieeffizienz" : "Energy Efficiency",
      before: { value: 100, label: "2005" },
      after: { value: 87, label: "2023" },
      unit: "% " + (language === "de" ? "Verbrauch" : "consumption"),
      trend: "positive",
      color: "bg-purple-500",
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
    hidden: { x: -100, opacity: 0 },
    visible: {
      x: 0,
      opacity: 1,
      transition: {
        duration: 0.8,
      },
    },
  }

  return (
    <div className="my-16 p-8 bg-gradient-to-r from-[#c4a747]/5 to-[#2d5a3d]/5 rounded-lg">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6 }}
        className="text-center mb-12"
      >
        <h3 className="text-3xl font-bold text-[#2d5a3d] mb-4">
          {language === "de" ? "Dann vs. Heute" : "Then vs. Now"}
        </h3>
        <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
          {language === "de"
            ? "Wie sich Europas Klimaindikatoren über die Jahrzehnte verändert haben"
            : "How Europe's climate indicators have changed over the decades"}
        </p>
      </motion.div>

      <motion.div
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: "-50px" }}
        variants={containerVariants}
        className="grid grid-cols-1 md:grid-cols-2 gap-8"
      >
        {comparisons.map((comparison, index) => (
          <motion.div key={index} variants={itemVariants}>
            <Card className="overflow-hidden hover:shadow-lg transition-shadow duration-300">
              <CardHeader>
                <CardTitle className="text-lg text-[#2d5a3d] flex items-center gap-2">
                  {comparison.category}
                  {comparison.trend === "positive" ? (
                    <TrendingUp className="h-5 w-5 text-green-500" />
                  ) : (
                    <TrendingDown className="h-5 w-5 text-red-500" />
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">{comparison.before.label}</span>
                    <span className="font-semibold">
                      {comparison.before.value}
                      {comparison.unit}
                    </span>
                  </div>
                  <Progress value={comparison.before.value} className="h-2" />
                </div>

                <motion.div
                  animate={{ x: [0, 10, 0] }}
                  transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY, ease: "easeInOut" }}
                  className="flex justify-center"
                >
                  <ArrowRight className="h-6 w-6 text-[#2d5a3d]" />
                </motion.div>

                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">{comparison.after.label}</span>
                    <span className="font-semibold">
                      {comparison.after.value}
                      {comparison.unit}
                    </span>
                  </div>
                  <motion.div
                    initial={{ width: 0 }}
                    whileInView={{ width: "100%" }}
                    viewport={{ once: true }}
                    transition={{ delay: 0.5 + index * 0.2, duration: 1.5 }}
                  >
                    <Progress value={comparison.after.value} className={`h-2 ${comparison.color}`} />
                  </motion.div>
                </div>

                <motion.div
                  initial={{ opacity: 0, scale: 0.8 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: 1 + index * 0.2, duration: 0.5 }}
                  className="text-center p-3 bg-background/50 rounded-lg"
                >
                  <div
                    className={`text-lg font-bold ${
                      comparison.trend === "positive" ? "text-green-600" : "text-red-600"
                    }`}
                  >
                    {comparison.trend === "positive" ? "+" : ""}
                    {comparison.after.value - comparison.before.value}
                    {comparison.unit}
                  </div>
                  <div className="text-xs text-muted-foreground">{language === "de" ? "Veränderung" : "Change"}</div>
                </motion.div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </motion.div>
    </div>
  )
}
