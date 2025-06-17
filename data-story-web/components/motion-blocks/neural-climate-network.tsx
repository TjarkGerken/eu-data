"use client";

import { motion, useAnimationFrame } from "framer-motion"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useLanguage } from "@/contexts/language-context"
import { useRef, useState } from "react"

interface Node {
  id: number
  x: number
  y: number
  type: "input" | "hidden" | "output"
  label: string
  value: number
  active: boolean
  connections: number[]
}

interface Connection {
  from: number
  to: number
  weight: number
  active: boolean
}

export function NeuralClimateNetwork() {
  const { language } = useLanguage()
  const timeRef = useRef(0)

  const [nodes] = useState<Node[]>([
    {
      id: 0,
      x: 100,
      y: 100,
      type: "input",
      label: language === "de" ? "CO₂" : "CO₂",
      value: 0.8,
      active: false,
      connections: [3, 4, 5],
    },
    {
      id: 1,
      x: 100,
      y: 200,
      type: "input",
      label: language === "de" ? "Temp" : "Temp",
      value: 0.9,
      active: false,
      connections: [3, 4, 5],
    },
    {
      id: 2,
      x: 100,
      y: 300,
      type: "input",
      label: language === "de" ? "Meer" : "Ocean",
      value: 0.7,
      active: false,
      connections: [3, 4, 5],
    },

    { id: 3, x: 300, y: 80, type: "hidden", label: "H1", value: 0.6, active: false, connections: [6, 7] },
    { id: 4, x: 300, y: 200, type: "hidden", label: "H2", value: 0.8, active: false, connections: [6, 7] },
    { id: 5, x: 300, y: 320, type: "hidden", label: "H3", value: 0.5, active: false, connections: [6, 7] },

    {
      id: 6,
      x: 500,
      y: 150,
      type: "output",
      label: language === "de" ? "Risiko" : "Risk",
      value: 0.85,
      active: false,
      connections: [],
    },
    {
      id: 7,
      x: 500,
      y: 250,
      type: "output",
      label: language === "de" ? "Maßnahmen" : "Action",
      value: 0.75,
      active: false,
      connections: [],
    },
  ])

  const [connections] = useState<Connection[]>([
    { from: 0, to: 3, weight: 0.8, active: false },
    { from: 0, to: 4, weight: 0.6, active: false },
    { from: 0, to: 5, weight: 0.9, active: false },
    { from: 1, to: 3, weight: 0.7, active: false },
    { from: 1, to: 4, weight: 0.8, active: false },
    { from: 1, to: 5, weight: 0.5, active: false },
    { from: 2, to: 3, weight: 0.6, active: false },
    { from: 2, to: 4, weight: 0.9, active: false },
    { from: 2, to: 5, weight: 0.7, active: false },
    { from: 3, to: 6, weight: 0.8, active: false },
    { from: 3, to: 7, weight: 0.6, active: false },
    { from: 4, to: 6, weight: 0.9, active: false },
    { from: 4, to: 7, weight: 0.8, active: false },
    { from: 5, to: 6, weight: 0.7, active: false },
    { from: 5, to: 7, weight: 0.9, active: false },
  ])

  const [activeNodes, setActiveNodes] = useState<Set<number>>(new Set())
  const [activeConnections, setActiveConnections] = useState<Set<string>>(new Set())

  useAnimationFrame(() => {
    timeRef.current += 0.05

    const wavePosition = (Math.sin(timeRef.current) + 1) / 2
    const newActiveNodes = new Set<number>()
    const newActiveConnections = new Set<string>()

    if (wavePosition < 0.3) {
      newActiveNodes.add(0)
      newActiveNodes.add(1)
      newActiveNodes.add(2)
    } else if (wavePosition < 0.7) {
      newActiveNodes.add(3)
      newActiveNodes.add(4)
      newActiveNodes.add(5)
      connections.forEach((conn) => {
        if (conn.from < 3 && conn.to >= 3 && conn.to < 6) {
          newActiveConnections.add(`${conn.from}-${conn.to}`)
        }
      })
    } else {
      newActiveNodes.add(6)
      newActiveNodes.add(7)
      connections.forEach((conn) => {
        if (conn.from >= 3 && conn.from < 6 && conn.to >= 6) {
          newActiveConnections.add(`${conn.from}-${conn.to}`)
        }
      })
    }

    setActiveNodes(newActiveNodes)
    setActiveConnections(newActiveConnections)
  })

  const getNodeColor = (node: Node) => {
    switch (node.type) {
      case "input":
        return "#3b82f6"
      case "hidden":
        return "#8b5cf6"
      case "output":
        return "#ef4444"
    }
  }

  const getNodeSize = (node: Node) => {
    const baseSize = 40
    const activeMultiplier = activeNodes.has(node.id) ? 1.5 : 1
    const valueMultiplier = 0.5 + node.value * 0.5
    return baseSize * activeMultiplier * valueMultiplier
  }

  return (
    <div className="my-16 p-8 bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-900 rounded-lg overflow-hidden relative">
      <motion.div
        className="absolute inset-0 opacity-10"
        animate={{
          backgroundPosition: ["0% 0%", "100% 100%"],
        }}
        transition={{
          duration: 30,
          repeat: Number.POSITIVE_INFINITY,
          ease: "linear",
        }}
        style={{
          backgroundImage: `
            radial-gradient(circle at 25% 25%, #ffffff 2px, transparent 2px),
            radial-gradient(circle at 75% 75%, #ffffff 1px, transparent 1px)
          `,
          backgroundSize: "100px 100px, 50px 50px",
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
          {language === "de" ? "KI-Klimamodell" : "AI Climate Model"}
        </h3>
        <p className="text-xl text-purple-200 max-w-2xl mx-auto">
          {language === "de"
            ? "Neuronale Netzwerke analysieren komplexe Klimamuster"
            : "Neural networks analyzing complex climate patterns"}
        </p>
      </motion.div>

      <Card className="bg-black/30 backdrop-blur-sm border-purple-500/30 overflow-hidden">
        <CardContent className="p-8">
          <div className="relative w-full h-96">
            <svg width="100%" height="100%" className="absolute inset-0">
              {connections.map((conn, index) => {
                const fromNode = nodes.find((n) => n.id === conn.from)
                const toNode = nodes.find((n) => n.id === conn.to)
                if (!fromNode || !toNode) return null

                const isActive = activeConnections.has(`${conn.from}-${conn.to}`)

                return (
                  <motion.line
                    key={index}
                    x1={fromNode.x}
                    y1={fromNode.y}
                    x2={toNode.x}
                    y2={toNode.y}
                    stroke={isActive ? "#fbbf24" : "#6b7280"}
                    strokeWidth={isActive ? 3 : 1}
                    opacity={isActive ? 1 : 0.3}
                    animate={{
                      strokeDasharray: isActive ? "5,5" : "0,0",
                      strokeDashoffset: isActive ? [0, -10] : 0,
                    }}
                    transition={{
                      strokeDashoffset: {
                        duration: 1,
                        repeat: Number.POSITIVE_INFINITY,
                        ease: "linear",
                      },
                    }}
                  />
                )
              })}
            </svg>

            {nodes.map((node) => {
              const isActive = activeNodes.has(node.id)
              const nodeSize = getNodeSize(node)

              return (
                <motion.div
                  key={node.id}
                  className="absolute flex flex-col items-center justify-center text-white font-bold text-sm"
                  style={{
                    left: node.x - nodeSize / 2,
                    top: node.y - nodeSize / 2,
                    width: nodeSize,
                    height: nodeSize,
                  }}
                  animate={{
                    scale: isActive ? 1.2 : 1,
                  }}
                  transition={{
                    duration: 0.3,
                    ease: "easeOut",
                  }}
                >
                  <motion.div
                    className="w-full h-full rounded-full flex items-center justify-center relative"
                    style={{
                      backgroundColor: getNodeColor(node),
                      boxShadow: isActive ? `0 0 20px ${getNodeColor(node)}` : "none",
                    }}
                    animate={{
                      rotate: isActive ? 360 : 0,
                    }}
                    transition={{
                      duration: 2,
                      ease: "linear",
                    }}
                  >
                    <span className="text-xs">{node.label}</span>

                    <motion.div
                      className="absolute -bottom-6 left-1/2 transform -translate-x-1/2"
                      animate={{
                        opacity: isActive ? 1 : 0.5,
                        y: isActive ? 0 : 5,
                      }}
                    >
                      <Badge variant="secondary" className="text-xs">
                        {(node.value * 100).toFixed(0)}%
                      </Badge>
                    </motion.div>
                  </motion.div>
                </motion.div>
              )
            })}

            {activeConnections.size > 0 &&
              [...Array(5)].map((_, index) => (
                <motion.div
                  key={index}
                  className="absolute w-2 h-2 bg-yellow-400 rounded-full"
                  animate={{
                    x: [100, 300, 500],
                    y: [150 + index * 20, 200, 200],
                    opacity: [0, 1, 0],
                  }}
                  transition={{
                    duration: 2,
                    repeat: Number.POSITIVE_INFINITY,
                    delay: index * 0.2,
                    ease: "easeInOut",
                  }}
                />
              ))}
          </div>

          <div className="flex justify-between mt-8 text-white text-sm">
            <div className="text-center">
              <div className="font-bold text-blue-300">{language === "de" ? "Eingabe" : "Input"}</div>
              <div className="text-xs text-gray-300">{language === "de" ? "Klimadaten" : "Climate Data"}</div>
            </div>
            <div className="text-center">
              <div className="font-bold text-purple-300">{language === "de" ? "Verarbeitung" : "Processing"}</div>
              <div className="text-xs text-gray-300">
                {language === "de" ? "Mustererkennung" : "Pattern Recognition"}
              </div>
            </div>
            <div className="text-center">
              <div className="font-bold text-red-300">{language === "de" ? "Ausgabe" : "Output"}</div>
              <div className="text-xs text-gray-300">{language === "de" ? "Vorhersagen" : "Predictions"}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ delay: 0.5, duration: 0.8 }}
        className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4 text-center relative z-10"
      >
        <div className="text-white">
          <div className="text-2xl font-bold text-blue-400">95.7%</div>
          <div className="text-sm text-blue-200">{language === "de" ? "Modellgenauigkeit" : "Model Accuracy"}</div>
        </div>
        <div className="text-white">
          <div className="text-2xl font-bold text-purple-400">1.2M</div>
          <div className="text-sm text-purple-200">{language === "de" ? "Datenpunkte" : "Data Points"}</div>
        </div>
        <div className="text-white">
          <div className="text-2xl font-bold text-red-400">2030</div>
          <div className="text-sm text-red-200">{language === "de" ? "Vorhersageziel" : "Prediction Target"}</div>
        </div>
      </motion.div>
    </div>
  )
}
