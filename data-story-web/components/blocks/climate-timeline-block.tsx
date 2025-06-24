"use client";

import { motion } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Calendar,
  Thermometer,
  Droplets,
  Wind,
  AlertTriangle,
  Zap,
  BarChart3,
  Globe,
} from "lucide-react";
import { useLanguage } from "@/contexts/language-context";

interface ClimateTimelineBlockProps {
  title?: string;
  description?: string;
  events: Array<{
    year: number;
    title: string;
    description: string;
    type: "temperature" | "precipitation" | "policy" | "extreme";
    icon: string;
    color: string;
  }>;
}

const iconMap = {
  calendar: Calendar,
  thermometer: Thermometer,
  droplets: Droplets,
  wind: Wind,
  alert: AlertTriangle,
  zap: Zap,
  barchart: BarChart3,
  globe: Globe,
};

export function ClimateTimelineBlock({
  title,
  description,
  events,
}: ClimateTimelineBlockProps) {
  const { language } = useLanguage();

  const getIconComponent = (iconName: string) => {
    return iconMap[iconName as keyof typeof iconMap] || Calendar;
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.3,
      },
    },
  };

  const itemVariants = {
    hidden: { x: -50, opacity: 0 },
    visible: {
      x: 0,
      opacity: 1,
      transition: {
        duration: 0.8,
      },
    },
  };

  const defaultTitle =
    language === "de" ? "Klimawandel Zeitlinie" : "Climate Change Timeline";
  const defaultDescription =
    language === "de"
      ? "Wichtige Ereignisse und Meilensteine der letzten Jahrzehnte"
      : "Key events and milestones from recent decades";

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
          {title || defaultTitle}
        </h3>
        <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
          {description || defaultDescription}
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
          {events.map((event) => {
            const IconComponent = getIconComponent(event.icon);

            return (
              <motion.div
                key={event.year}
                variants={itemVariants}
                className="relative flex items-start gap-6"
              >
                <motion.div
                  whileHover={{ scale: 1.2 }}
                  className={`relative z-10 flex items-center justify-center w-16 h-16 rounded-full shadow-lg`}
                  style={{ backgroundColor: event.color }}
                >
                  <IconComponent className="h-6 w-6 text-white" />
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
                          <h4 className="text-xl font-semibold text-[#2d5a3d]">
                            {event.title}
                          </h4>
                        </div>
                      </div>
                      <p className="text-muted-foreground leading-relaxed">
                        {event.description}
                      </p>
                    </CardContent>
                  </Card>
                </motion.div>
              </motion.div>
            );
          })}
        </div>
      </motion.div>
    </div>
  );
}
