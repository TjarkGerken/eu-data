"use client";

import { motion, useAnimationFrame } from "framer-motion"
import { Card, CardContent } from "@/components/ui/card"
import { useLanguage } from "@/contexts/language-context"
import { useRef, useState } from "react"

export function EarthPulse() {
  const { language } = useLanguage()
  const [temperature, setTemperature] = useState(1.2)
  const pulseRef = useRef(0)

  useAnimationFrame(() => {
    pulseRef.current += 0.02
    const newTemp = 1.2 + Math.sin(pulseRef.current) * 0.3
    setTemperature(newTemp)
  })

  const getTemperatureColor = (temp: number) => {
    // Temperature color gradient from blue (cold) to red (hot)
    const intensity = Math.min(Math.max((temp - 1) / 0.5, 0), 1)
    return `hsl(${240 - intensity * 240}, 100%, 50%)`
  }

  const continents = [
    { name: "Europe", x: 50, y: 45, temp: temperature + 0.2 },
    { name: "North America", x: 20, y: 35, temp: temperature + 0.1 },
    { name: "Asia", x: 70, y: 40, temp: temperature + 0.3 },
    { name: "Africa", x: 52, y: 65, temp: temperature - 0.1 },
    { name: "South America", x: 30, y: 75, temp: temperature + 0.15 },
    { name: "Australia", x: 80, y: 80, temp: temperature + 0.25 },
  ]

  return (
    <div className="my-16 p-8 bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 rounded-lg overflow-hidden relative">
      {[...Array(50)].map((_, index) => (
        <motion.div
          key={index}
          className="absolute w-1 h-1 bg-white rounded-full"
          style={{
            left: `${Math.random() * 100}%`,
            top: `${Math.random() * 100}%`,
          }}
          animate={{
            opacity: [0.3, 1, 0.3],
            scale: [0.5, 1, 0.5],
          }}
          transition={{
            duration: 2 + Math.random() * 3,
            repeat: Number.POSITIVE_INFINITY,
            delay: Math.random() * 2,
          }}
        />
      ))}

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 1 }}
        className="text-center mb-8 relative z-10"
      >
        <h3 className="text-4xl font-bold text-white mb-4">
          {language === "de" ? "Der Puls unseres Planeten" : "The Pulse of Our Planet"}
        </h3>
        <p className="text-xl text-blue-200 max-w-2xl mx-auto">
          {language === "de"
            ? "Erleben Sie die Erwärmung der Erde in Echtzeit"
            : "Experience Earth's warming in real-time"}
        </p>
      </motion.div>

      <div className="relative max-w-4xl mx-auto">
        <motion.div
          className="relative w-80 h-80 mx-auto rounded-full overflow-hidden"
          style={{
            background: `radial-gradient(circle at 30% 30%, ${getTemperatureColor(temperature)}, #1e40af, #0f172a)`,
          }}
          animate={{
            boxShadow: [
              `0 0 50px ${getTemperatureColor(temperature)}40`,
              `0 0 80px ${getTemperatureColor(temperature)}60`,
              `0 0 50px ${getTemperatureColor(temperature)}40`,
            ],
          }}
          transition={{
            duration: 2,
            repeat: Number.POSITIVE_INFINITY,
            ease: "easeInOut",
          }}
        >
          {continents.map((continent, index) => (
            <motion.div
              key={continent.name}
              className="absolute w-8 h-8 rounded-full"
              style={{
                left: `${continent.x}%`,
                top: `${continent.y}%`,
                background: `radial-gradient(circle, ${getTemperatureColor(continent.temp)}, transparent)`,
              }}
              animate={{
                scale: [1, 1.5, 1],
                opacity: [0.6, 1, 0.6],
              }}
              transition={{
                duration: 1.5 + index * 0.2,
                repeat: Number.POSITIVE_INFINITY,
                ease: "easeInOut",
              }}
            />
          ))}

          <motion.div
            className="absolute inset-0 rounded-full border-4 border-white/20"
            animate={{
              scale: [1, 1.1, 1],
              opacity: [0.3, 0.6, 0.3],
            }}
            transition={{
              duration: 3,
              repeat: Number.POSITIVE_INFINITY,
              ease: "easeInOut",
            }}
          />
          <motion.div
            className="absolute inset-0 rounded-full border-2 border-white/10"
            style={{ transform: "scale(1.2)" }}
            animate={{
              scale: [1.2, 1.3, 1.2],
              opacity: [0.2, 0.4, 0.2],
            }}
            transition={{
              duration: 4,
              repeat: Number.POSITIVE_INFINITY,
              ease: "easeInOut",
            }}
          />
        </motion.div>

        <motion.div
          className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center"
          animate={{
            scale: [1, 1.05, 1],
          }}
          transition={{
            duration: 2,
            repeat: Number.POSITIVE_INFINITY,
            ease: "easeInOut",
          }}
        >
          <div className="text-6xl font-bold text-white drop-shadow-lg">+{temperature.toFixed(1)}°C</div>
          <div className="text-sm text-blue-200 mt-2">{language === "de" ? "Globale Erwärmung" : "Global Warming"}</div>
        </motion.div>

        <div className="absolute inset-0 pointer-events-none">
          {continents.map((continent, index) => (
            <motion.div
              key={`data-${continent.name}`}
              className="absolute"
              style={{
                left: `${continent.x + 15}%`,
                top: `${continent.y - 10}%`,
              }}
              initial={{ opacity: 0, scale: 0 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.3, duration: 0.5 }}
            >
              <Card className="bg-black/50 backdrop-blur-sm border-white/20">
                <CardContent className="p-3 text-center">
                  <div className="text-lg font-bold text-white">+{continent.temp.toFixed(1)}°C</div>
                  <div className="text-xs text-blue-200">{continent.name}</div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ delay: 1, duration: 0.8 }}
        className="mt-12 grid grid-cols-3 gap-6 text-center relative z-10"
      >
        <div className="text-white">
          <div className="text-3xl font-bold text-red-400">2023</div>
          <div className="text-sm text-blue-200">{language === "de" ? "Heißestes Jahr" : "Hottest Year"}</div>
        </div>
        <div className="text-white">
          <div className="text-3xl font-bold text-orange-400">1.5°C</div>
          <div className="text-sm text-blue-200">{language === "de" ? "Paris Ziel" : "Paris Target"}</div>
        </div>
        <div className="text-white">
          <div className="text-3xl font-bold text-yellow-400">7 Jahre</div>
          <div className="text-sm text-blue-200">
            {language === "de" ? "Verbleibendes Zeitfenster" : "Time Window Left"}
          </div>
        </div>
      </motion.div>
    </div>
  )
}
