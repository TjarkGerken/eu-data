"use client";

import { motion, useAnimationFrame } from "framer-motion"
import { Card, CardContent } from "@/components/ui/card"
import { useLanguage } from "@/contexts/language-context"
import { useRef, useState } from "react"

interface DataParticle {
  id: number
  x: number
  y: number
  vx: number
  vy: number
  size: number
  color: string
  value: string
  type: "temperature" | "co2" | "renewable" | "precipitation"
}

export function DataStorm() {
  const { language } = useLanguage()
  const containerRef = useRef<HTMLDivElement>(null)
  const timeRef = useRef(0)

  const [particles, setParticles] = useState<DataParticle[]>(() => {
    const dataPoints = [
      { value: "+1.2°C", type: "temperature" as const, color: "#ef4444" },
      { value: "415ppm", type: "co2" as const, color: "#f97316" },
      { value: "42%", type: "renewable" as const, color: "#22c55e" },
      { value: "-15%", type: "precipitation" as const, color: "#3b82f6" },
      { value: "+2.1°C", type: "temperature" as const, color: "#dc2626" },
      { value: "32%↓", type: "co2" as const, color: "#16a34a" },
      { value: "80%", type: "renewable" as const, color: "#059669" },
      { value: "+20%", type: "precipitation" as const, color: "#2563eb" },
    ]

    return Array.from({ length: 50 }, (_, index) => {
      const dataPoint = dataPoints[index % dataPoints.length]
      return {
        id: index,
        x: Math.random() * 800,
        y: Math.random() * 600,
        vx: (Math.random() - 0.5) * 3,
        vy: (Math.random() - 0.5) * 3,
        size: 8 + Math.random() * 12,
        color: dataPoint.color,
        value: dataPoint.value,
        type: dataPoint.type,
      }
    })
  })

  useAnimationFrame(() => {
    timeRef.current += 0.016

    setParticles((prev) =>
      prev.map((particle) => {
        let newX = particle.x + particle.vx
        let newY = particle.y + particle.vy
        let newVx = particle.vx
        let newVy = particle.vy

        const centerX = 400
        const centerY = 300
        const dx = newX - centerX
        const dy = newY - centerY
        const distance = Math.sqrt(dx * dx + dy * dy)

        if (distance > 0) {
          const angle = Math.atan2(dy, dx)
          const swirl = 0.02
          newVx += -Math.sin(angle) * swirl
          newVy += Math.cos(angle) * swirl
        }

        if (newX <= 0 || newX >= 800) newVx = -newVx * 0.8
        if (newY <= 0 || newY >= 600) newVy = -newVy * 0.8

        newX = Math.max(particle.size, Math.min(800 - particle.size, newX))
        newY = Math.max(particle.size, Math.min(600 - particle.size, newY))

        newVx += (Math.random() - 0.5) * 0.1
        newVy += (Math.random() - 0.5) * 0.1

        const maxVel = 4
        const vel = Math.sqrt(newVx * newVx + newVy * newVy)
        if (vel > maxVel) {
          newVx = (newVx / vel) * maxVel
          newVy = (newVy / vel) * maxVel
        }

        return {
          ...particle,
          x: newX,
          y: newY,
          vx: newVx * 0.995,
          vy: newVy * 0.995,
        }
      }),
    )
  })

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "temperature":
        return "🌡️"
      case "co2":
        return "💨"
      case "renewable":
        return "⚡"
      case "precipitation":
        return "💧"
      default:
        return "📊"
    }
  }

  return (
    <div className="my-16 p-8 bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 rounded-lg overflow-hidden relative">
      <motion.div
        className="absolute inset-0 opacity-20"
        animate={{
          backgroundPosition: ["0% 0%", "100% 100%"],
        }}
        transition={{
          duration: 20,
          repeat: Number.POSITIVE_INFINITY,
          ease: "linear",
        }}
        style={{
          backgroundImage: `
            linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px),
            linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px)
          `,
          backgroundSize: "50px 50px",
        }}
      />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.8 }}
        className="text-center mb-8 relative z-10"
      >
        <h3 className="text-4xl font-bold text-white mb-4">
          {language === "de" ? "Datensturm der Klimakrise" : "Climate Data Storm"}
        </h3>
        <p className="text-xl text-purple-200 max-w-2xl mx-auto">
          {language === "de"
            ? "Tausende von Datenpunkten wirbeln durch den digitalen Raum"
            : "Thousands of data points swirling through digital space"}
        </p>
      </motion.div>

      <Card className="bg-black/30 backdrop-blur-sm border-purple-500/30 overflow-hidden">
        <CardContent className="p-0">
          <div
            ref={containerRef}
            className="relative w-full h-96 overflow-hidden bg-gradient-to-br from-purple-900/50 to-blue-900/50"
          >
            <motion.div
              className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2"
              animate={{
                rotate: 360,
                scale: [1, 1.2, 1],
              }}
              transition={{
                rotate: { duration: 10, repeat: Number.POSITIVE_INFINITY, ease: "linear" },
                scale: { duration: 4, repeat: Number.POSITIVE_INFINITY, ease: "easeInOut" },
              }}
            >
              <div className="w-32 h-32 border-4 border-purple-400/50 rounded-full">
                <div className="w-24 h-24 border-2 border-blue-400/50 rounded-full m-4">
                  <div className="w-16 h-16 border border-white/50 rounded-full m-4 flex items-center justify-center">
                    <span className="text-white text-xs font-bold">{language === "de" ? "KLIMA" : "CLIMATE"}</span>
                  </div>
                </div>
              </div>
            </motion.div>

            {particles.map((particle) => (
              <motion.div
                key={particle.id}
                className="absolute flex items-center justify-center pointer-events-none"
                style={{
                  left: particle.x,
                  top: particle.y,
                  width: particle.size * 2,
                  height: particle.size * 2,
                }}
                animate={{
                  rotate: [0, 360],
                }}
                transition={{
                  duration: 3 + Math.random() * 2,
                  repeat: Number.POSITIVE_INFINITY,
                  ease: "linear",
                }}
              >
                <div
                  className="relative rounded-full flex items-center justify-center text-white text-xs font-bold shadow-lg"
                  style={{
                    backgroundColor: particle.color,
                    width: particle.size * 2,
                    height: particle.size * 2,
                    boxShadow: `0 0 ${particle.size}px ${particle.color}40`,
                  }}
                >
                  <div className="absolute -top-1 -right-1 text-xs">{getTypeIcon(particle.type)}</div>
                  <span className="text-xs">{particle.value}</span>
                </div>
              </motion.div>
            ))}

            {[...Array(3)].map((_, index) => (
              <motion.div
                key={index}
                className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 border border-purple-400/30 rounded-full"
                animate={{
                  scale: [0, 3],
                  opacity: [0.8, 0],
                }}
                transition={{
                  duration: 4,
                  repeat: Number.POSITIVE_INFINITY,
                  delay: index * 1.3,
                }}
                style={{
                  width: "100px",
                  height: "100px",
                }}
              />
            ))}
          </div>
        </CardContent>
      </Card>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ delay: 0.5, duration: 0.8 }}
        className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4 text-center relative z-10"
      >
        <div className="text-white">
          <div className="text-2xl mb-1">🌡️</div>
          <div className="text-sm text-red-300">{language === "de" ? "Temperatur" : "Temperature"}</div>
        </div>
        <div className="text-white">
          <div className="text-2xl mb-1">💨</div>
          <div className="text-sm text-orange-300">CO₂</div>
        </div>
        <div className="text-white">
          <div className="text-2xl mb-1">⚡</div>
          <div className="text-sm text-green-300">{language === "de" ? "Erneuerbar" : "Renewable"}</div>
        </div>
        <div className="text-white">
          <div className="text-2xl mb-1">💧</div>
          <div className="text-sm text-blue-300">{language === "de" ? "Niederschlag" : "Precipitation"}</div>
        </div>
      </motion.div>
    </div>
  )
}
