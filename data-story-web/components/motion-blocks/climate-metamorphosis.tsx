"use client";

import { motion, AnimatePresence } from "framer-motion"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { useLanguage } from "@/contexts/language-context"
import { useState, useEffect } from "react"
import { Play, Pause, RotateCcw } from "lucide-react"

interface ClimateStage {
  year: number
  title: string
  description: string
  landscape: string
  temperature: number
  co2: number
  color: string
  emoji: string
}

export function ClimateMetamorphosis() {
  const { language } = useLanguage()
  const [currentStage, setCurrentStage] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [progress, setProgress] = useState(0)

  const stages: ClimateStage[] = [
    {
      year: 1850,
      title: language === "de" ? "Vorindustrielle Zeit" : "Pre-Industrial Era",
      description:
        language === "de" ? "Stabile Klimabedingungen, unberührte Natur" : "Stable climate conditions, pristine nature",
      landscape: "🌲🌲🌲🏔️🌲🌲🌲",
      temperature: 0,
      co2: 280,
      color: "#22c55e",
      emoji: "🌿",
    },
    {
      year: 1950,
      title: language === "de" ? "Industrielle Revolution" : "Industrial Revolution",
      description: language === "de" ? "Erste Fabriken, beginnende Emissionen" : "First factories, beginning emissions",
      landscape: "🌲🏭🌲🏔️🌲🏭🌲",
      temperature: 0.3,
      co2: 315,
      color: "#f59e0b",
      emoji: "🏭",
    },
    {
      year: 1990,
      title: language === "de" ? "Beschleunigte Erwärmung" : "Accelerated Warming",
      description:
        language === "de"
          ? "Massive Industrialisierung, erste Klimaeffekte"
          : "Massive industrialization, first climate effects",
      landscape: "🌲🏭🏙️🏔️🏙️🏭🌲",
      temperature: 0.8,
      co2: 354,
      color: "#f97316",
      emoji: "🌡️",
    },
    {
      year: 2023,
      title: language === "de" ? "Klimakrise" : "Climate Crisis",
      description:
        language === "de"
          ? "Extreme Wetterereignisse, dringende Maßnahmen nötig"
          : "Extreme weather events, urgent action needed",
      landscape: "🔥🏙️🌪️🏔️🌪️🏙️🔥",
      temperature: 1.2,
      co2: 421,
      color: "#ef4444",
      emoji: "🚨",
    },
    {
      year: 2050,
      title: language === "de" ? "Grüne Transformation" : "Green Transformation",
      description:
        language === "de" ? "Erneuerbare Energien, nachhaltige Zukunft" : "Renewable energy, sustainable future",
      landscape: "🌱💚🌿🏔️🌿💚🌱",
      temperature: 1.5,
      co2: 350,
      color: "#10b981",
      emoji: "♻️",
    },
  ]

  useEffect(() => {
    let interval: NodeJS.Timeout
    if (isPlaying) {
      interval = setInterval(() => {
        setProgress((prev) => {
          const newProgress = prev + 2
          if (newProgress >= 100) {
            const nextStage = (currentStage + 1) % stages.length
            setCurrentStage(nextStage)
            return 0
          }
          return newProgress
        })
      }, 100)
    }
    return () => clearInterval(interval)
  }, [isPlaying, currentStage, stages.length])

  const handlePlayPause = () => {
    setIsPlaying(!isPlaying)
  }

  const handleReset = () => {
    setIsPlaying(false)
    setCurrentStage(0)
    setProgress(0)
  }

  const handleStageClick = (index: number) => {
    setCurrentStage(index)
    setProgress(0)
    setIsPlaying(false)
  }

  const currentStageData = stages[currentStage]

  return (
    <div className="my-16 p-8 bg-gradient-to-br from-emerald-50 via-blue-50 to-purple-50 dark:from-emerald-900/20 dark:via-blue-900/20 dark:to-purple-900/20 rounded-lg">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.8 }}
        className="text-center mb-8"
      >
        <h3 className="text-4xl font-bold text-[#2d5a3d] mb-4">
          {language === "de" ? "Klimawandel-Metamorphose" : "Climate Change Metamorphosis"}
        </h3>
        <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
          {language === "de"
            ? "Erleben Sie 200 Jahre Klimawandel in einer interaktiven Zeitreise"
            : "Experience 200 years of climate change in an interactive time journey"}
        </p>
      </motion.div>

      <Card className="overflow-hidden bg-gradient-to-br from-white/80 to-gray-50/80 dark:from-gray-800/80 dark:to-gray-900/80 backdrop-blur-sm">
        <CardContent className="p-8">
          <div
            className="relative h-64 mb-8 rounded-lg overflow-hidden"
            style={{ backgroundColor: currentStageData.color + "20" }}
          >
            <AnimatePresence mode="wait">
              <motion.div
                key={currentStage}
                initial={{ opacity: 0, scale: 0.8, rotateY: -90 }}
                animate={{ opacity: 1, scale: 1, rotateY: 0 }}
                exit={{ opacity: 0, scale: 0.8, rotateY: 90 }}
                transition={{ duration: 0.8, ease: "easeInOut" }}
                className="absolute inset-0 flex flex-col items-center justify-center"
              >
                <motion.div
                  className="text-6xl font-bold mb-4"
                  style={{ color: currentStageData.color }}
                  animate={{ scale: [1, 1.1, 1] }}
                  transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY }}
                >
                  {currentStageData.year}
                </motion.div>

                <motion.div
                  className="text-4xl mb-4 tracking-wider"
                  animate={{ y: [0, -5, 0] }}
                  transition={{ duration: 3, repeat: Number.POSITIVE_INFINITY, ease: "easeInOut" }}
                >
                  {currentStageData.landscape}
                </motion.div>

                <div className="text-center">
                  <h4 className="text-2xl font-bold text-[#2d5a3d] mb-2">
                    {currentStageData.emoji} {currentStageData.title}
                  </h4>
                  <p className="text-muted-foreground max-w-md">{currentStageData.description}</p>
                </div>

                <motion.div
                  className="absolute bottom-4 left-4 right-4 flex justify-between text-sm"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.5 }}
                >
                  <div className="bg-white/80 dark:bg-gray-800/80 rounded-lg p-2">
                    <div className="font-bold text-red-600">+{currentStageData.temperature.toFixed(1)}°C</div>
                    <div className="text-xs text-muted-foreground">
                      {language === "de" ? "Temperatur" : "Temperature"}
                    </div>
                  </div>
                  <div className="bg-white/80 dark:bg-gray-800/80 rounded-lg p-2">
                    <div className="font-bold text-orange-600">{currentStageData.co2}ppm</div>
                    <div className="text-xs text-muted-foreground">CO₂</div>
                  </div>
                </motion.div>
              </motion.div>
            </AnimatePresence>

            <div className="absolute bottom-0 left-0 right-0 h-1 bg-black/20">
              <motion.div
                className="h-full bg-[#2d5a3d]"
                style={{ width: `${progress}%` }}
                transition={{ duration: 0.1 }}
              />
            </div>
          </div>

          <div className="flex justify-center gap-4 mb-6">
            <Button onClick={handlePlayPause} className="bg-[#2d5a3d] hover:bg-[#2d5a3d]/90">
              {isPlaying ? <Pause className="h-4 w-4 mr-2" /> : <Play className="h-4 w-4 mr-2" />}
              {isPlaying ? (language === "de" ? "Pause" : "Pause") : language === "de" ? "Abspielen" : "Play"}
            </Button>
            <Button onClick={handleReset} variant="outline">
              <RotateCcw className="h-4 w-4 mr-2" />
              {language === "de" ? "Zurücksetzen" : "Reset"}
            </Button>
          </div>

          <div className="flex justify-between items-center">
            {stages.map((stage, index) => (
              <motion.button
                key={stage.year}
                onClick={() => handleStageClick(index)}
                className={`flex flex-col items-center p-2 rounded-lg transition-all ${
                  index === currentStage ? "bg-[#2d5a3d]/20 scale-110" : "hover:bg-gray-100 dark:hover:bg-gray-800"
                }`}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                <div className="text-2xl mb-1">{stage.emoji}</div>
                <div className="text-xs font-medium">{stage.year}</div>
                <div className="w-2 h-2 rounded-full mt-1" style={{ backgroundColor: stage.color }} />
              </motion.button>
            ))}
          </div>
        </CardContent>
      </Card>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ delay: 0.5, duration: 0.8 }}
        className="mt-6 text-center"
      >
        <p className="text-sm text-muted-foreground max-w-3xl mx-auto">
          {language === "de"
            ? "Diese Visualisierung zeigt die dramatische Transformation unseres Planeten über 200 Jahre. Jede Stufe repräsentiert einen kritischen Wendepunkt in der Klimageschichte."
            : "This visualization shows the dramatic transformation of our planet over 200 years. Each stage represents a critical turning point in climate history."}
        </p>
      </motion.div>
    </div>
  )
}
