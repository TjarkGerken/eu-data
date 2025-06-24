"use client";

import { motion } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import {
  TrendingUp,
  TrendingDown,
  Thermometer,
  Droplets,
  Wind,
  Zap,
  BarChart3,
  Globe,
} from "lucide-react";
// import { useLanguage } from "@/contexts/language-context";

interface AnimatedStatisticsBlockProps {
  title?: string;
  description?: string;
  stats: Array<{
    icon: string;
    value: string;
    label: string;
    change?: string;
    trend?: "up" | "down";
    color: string;
  }>;
}

const iconMap = {
  thermometer: Thermometer,
  droplets: Droplets,
  wind: Wind,
  zap: Zap,
  barchart: BarChart3,
  globe: Globe,
  trending: TrendingUp,
};

export function AnimatedStatisticsBlock({
  title,
  description,
  stats,
}: AnimatedStatisticsBlockProps) {
  // const { language } = useLanguage();

  const getIconComponent = (iconName: string) => {
    return iconMap[iconName as keyof typeof iconMap] || BarChart3;
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.2,
      },
    },
  };

  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: {
        duration: 0.6,
      },
    },
  };

  return (
    <div className="my-16 p-8 bg-gradient-to-r from-[#2d5a3d]/5 to-[#c4a747]/5 rounded-lg">
      {(title || description) && (
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          variants={containerVariants}
          className="text-center mb-8"
        >
          {title && (
            <motion.h3
              variants={itemVariants}
              className="text-3xl font-bold text-[#2d5a3d] mb-4"
            >
              {title}
            </motion.h3>
          )}
          {description && (
            <motion.p
              variants={itemVariants}
              className="text-lg text-muted-foreground max-w-2xl mx-auto"
            >
              {description}
            </motion.p>
          )}
        </motion.div>
      )}

      <motion.div
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: "-50px" }}
        variants={containerVariants}
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"
      >
        {stats.map((stat, index) => {
          const IconComponent = getIconComponent(stat.icon);

          return (
            <motion.div key={index} variants={itemVariants}>
              <Card className="relative overflow-hidden group hover:shadow-lg transition-shadow duration-300">
                <CardContent className="p-6 text-center">
                  <motion.div
                    whileHover={{ scale: 1.1, rotate: 5 }}
                    transition={{ type: "spring", stiffness: 300 }}
                    className={`inline-flex p-3 rounded-full bg-background shadow-sm mb-4 ${stat.color}`}
                  >
                    <IconComponent className="h-6 w-6" />
                  </motion.div>

                  <motion.div
                    initial={{ scale: 0.8 }}
                    whileInView={{ scale: 1 }}
                    transition={{
                      delay: 0.2 + index * 0.1,
                      type: "spring",
                      stiffness: 200,
                    }}
                    className="space-y-2"
                  >
                    <div className={`text-3xl font-bold ${stat.color}`}>
                      {stat.value}
                    </div>
                    <div className="text-sm font-medium text-foreground">
                      {stat.label}
                    </div>
                    {stat.change && (
                      <div className="flex items-center justify-center gap-1 text-xs text-muted-foreground">
                        {stat.trend === "up" ? (
                          <TrendingUp className="h-3 w-3 text-red-500" />
                        ) : stat.trend === "down" ? (
                          <TrendingDown className="h-3 w-3 text-green-500" />
                        ) : null}
                        {stat.change}
                      </div>
                    )}
                  </motion.div>

                  <motion.div
                    className="absolute inset-0 bg-gradient-to-r from-[#2d5a3d]/10 to-[#c4a747]/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                    initial={false}
                  />
                </CardContent>
              </Card>
            </motion.div>
          );
        })}
      </motion.div>
    </div>
  );
}
