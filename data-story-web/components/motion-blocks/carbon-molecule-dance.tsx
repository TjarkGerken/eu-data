"use client";

import { motion, useAnimationFrame } from "framer-motion"
import { Card, CardContent } from "@/components/ui/card"
import { useLanguage } from "@/contexts/language-context"
import { useRef, useState } from "react"

interface Molecule {
  id: number
  x: number
  y: number
  vx: number
  vy: number
  type: "co2" | "o2" | "tree"
  size: number
}

export function CarbonMoleculeDance() {
  const { language } = useLanguage()
  const containerRef = useRef<HTMLDivElement>(null)
  const [molecules, setMolecules] = useState<Molecule[]>(() => {
    const initialMolecules: Molecule[] = []

    for (let index = 0; index < 15; index++) {
      initialMolecules.push({
        id: index,
        x: Math.random() * 800,
        y: Math.random() * 400,
        vx: (Math.random() - 0.5) * 2,
        vy: (Math.random() - 0.5) * 2,
        type: "co2",
        size: 20 + Math.random() * 10,
      })
    }

    for (let index = 15; index < 25; index++) {
      initialMolecules.push({
        id: index,
        x: Math.random() * 800,
        y: Math.random() * 400,
        vx: (Math.random() - 0.5) * 1.5,
        vy: (Math.random() - 0.5) * 1.5,
        type: "o2",
        size: 15 + Math.random() * 8,
      })
    }

    for (let index = 25; index < 30; index++) {
      initialMolecules.push({
        id: index,
        x: Math.random() * 800,
        y: 350 + Math.random() * 50,
        vx: 0,
        vy: 0,
        type: "tree",
        size: 30 + Math.random() * 15,
      })
    }

    return initialMolecules
  })

  useAnimationFrame(() => {
    setMolecules((prev) =>
      prev.map((molecule) => {
        if (molecule.type === "tree") return molecule

        let newX = molecule.x + molecule.vx
        let newY = molecule.y + molecule.vy
        let newVx = molecule.vx
        let newVy = molecule.vy

        if (newX <= 0 || newX >= 800) newVx = -newVx
        if (newY <= 0 || newY >= 400) newVy = -newVy

        newX = Math.max(0, Math.min(800, newX))
        newY = Math.max(0, Math.min(400, newY))

        if (molecule.type === "co2") {
          prev.forEach((other) => {
            if (other.type === "tree") {
              const dx = other.x - newX
              const dy = other.y - newY
              const distance = Math.sqrt(dx * dx + dy * dy)
              if (distance < 100) {
                newVx += (dx / distance) * 0.1
                newVy += (dy / distance) * 0.1
              }
            }
          })
        }

        return {
          ...molecule,
          x: newX,
          y: newY,
          vx: newVx * 0.99,
          vy: newVy * 0.99,
        }
      }),
    )
  })

  const getMoleculeComponent = (molecule: Molecule) => {
    switch (molecule.type) {
      case "co2":
        return (
          <motion.div
            key={molecule.id}
            className="absolute flex items-center justify-center"
            style={{
              left: molecule.x,
              top: molecule.y,
              width: molecule.size,
              height: molecule.size,
            }}
            animate={{
              rotate: 360,
            }}
            transition={{
              duration: 4,
              repeat: Number.POSITIVE_INFINITY,
              ease: "linear",
            }}
          >
            <div className="relative">
              <div className="w-4 h-4 bg-red-500 rounded-full absolute top-0 left-1/2 transform -translate-x-1/2" />
              <div className="w-3 h-3 bg-gray-800 rounded-full absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2" />
              <div className="w-4 h-4 bg-red-500 rounded-full absolute bottom-0 left-1/2 transform -translate-x-1/2" />
            </div>
          </motion.div>
        )
      case "o2":
        return (
          <motion.div
            key={molecule.id}
            className="absolute flex items-center justify-center"
            style={{
              left: molecule.x,
              top: molecule.y,
              width: molecule.size,
              height: molecule.size,
            }}
            animate={{
              scale: [1, 1.2, 1],
            }}
            transition={{
              duration: 2,
              repeat: Number.POSITIVE_INFINITY,
              ease: "easeInOut",
            }}
          >
            <div className="flex gap-1">
              <div className="w-3 h-3 bg-blue-400 rounded-full" />
              <div className="w-3 h-3 bg-blue-400 rounded-full" />
            </div>
          </motion.div>
        )
      case "tree":
        return (
          <motion.div
            key={molecule.id}
            className="absolute flex items-center justify-center"
            style={{
              left: molecule.x,
              top: molecule.y,
              width: molecule.size,
              height: molecule.size,
            }}
            animate={{
              y: [-2, 2, -2],
            }}
            transition={{
              duration: 3,
              repeat: Number.POSITIVE_INFINITY,
              ease: "easeInOut",
            }}
          >
            <div className="text-green-500 text-2xl">🌳</div>
          </motion.div>
        )
    }
  }

  return (
    <div className="my-16 p-8 bg-gradient-to-br from-green-50 via-blue-50 to-gray-50 dark:from-green-900/20 dark:via-blue-900/20 dark:to-gray-900/20 rounded-lg">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.8 }}
        className="text-center mb-8"
      >
        <h3 className="text-3xl font-bold text-[#2d5a3d] mb-4">
          {language === "de" ? "Der Kohlenstoff-Kreislauf" : "The Carbon Cycle"}
        </h3>
        <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
          {language === "de"
            ? "Beobachten Sie, wie CO₂-Moleküle mit der Natur interagieren"
            : "Watch CO₂ molecules interact with nature"}
        </p>
      </motion.div>

      <Card className="overflow-hidden bg-gradient-to-br from-sky-100 to-green-100 dark:from-sky-900/30 dark:to-green-900/30">
        <CardContent className="p-0">
          <div
            ref={containerRef}
            className="relative w-full h-96 overflow-hidden"
            style={{ background: "linear-gradient(to bottom, #87CEEB 0%, #98FB98 100%)" }}
          >
            <motion.div
              className="absolute top-4 left-10 w-16 h-8 bg-white/60 rounded-full"
              animate={{
                x: [0, 20, 0],
              }}
              transition={{
                duration: 8,
                repeat: Number.POSITIVE_INFINITY,
                ease: "easeInOut",
              }}
            />
            <motion.div
              className="absolute top-8 right-20 w-20 h-10 bg-white/50 rounded-full"
              animate={{
                x: [0, -15, 0],
              }}
              transition={{
                duration: 10,
                repeat: Number.POSITIVE_INFINITY,
                ease: "easeInOut",
              }}
            />

            <motion.div
              className="absolute top-6 right-6 w-12 h-12 bg-yellow-400 rounded-full"
              animate={{
                rotate: 360,
                scale: [1, 1.1, 1],
              }}
              transition={{
                rotate: { duration: 20, repeat: Number.POSITIVE_INFINITY, ease: "linear" },
                scale: { duration: 4, repeat: Number.POSITIVE_INFINITY, ease: "easeInOut" },
              }}
            />

            <div className="absolute bottom-0 left-0 right-0 h-16 bg-gradient-to-t from-green-600 to-green-400" />

            {molecules.map((molecule) => getMoleculeComponent(molecule))}

            {molecules
              .filter((m) => m.type === "tree")
              .map((tree) => (
                <motion.div
                  key={`effect-${tree.id}`}
                  className="absolute"
                  style={{
                    left: tree.x + 15,
                    top: tree.y - 10,
                  }}
                  animate={{
                    scale: [0, 1, 0],
                    opacity: [0, 0.6, 0],
                  }}
                  transition={{
                    duration: 2,
                    repeat: Number.POSITIVE_INFINITY,
                    ease: "easeInOut",
                  }}
                >
                  <div className="w-8 h-8 border-2 border-green-400 rounded-full" />
                </motion.div>
              ))}
          </div>
        </CardContent>
      </Card>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ delay: 0.5, duration: 0.8 }}
        className="mt-6 flex justify-center gap-8 text-sm"
      >
        <div className="flex items-center gap-2">
          <div className="flex">
            <div className="w-3 h-3 bg-red-500 rounded-full" />
            <div className="w-2 h-2 bg-gray-800 rounded-full -ml-1 mt-0.5" />
            <div className="w-3 h-3 bg-red-500 rounded-full -ml-1" />
          </div>
          <span>CO₂</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex gap-1">
            <div className="w-3 h-3 bg-blue-400 rounded-full" />
            <div className="w-3 h-3 bg-blue-400 rounded-full" />
          </div>
          <span>O₂</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xl">🌳</span>
          <span>{language === "de" ? "Bäume" : "Trees"}</span>
        </div>
      </motion.div>
    </div>
  )
}
