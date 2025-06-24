"use client";

import { motion } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { Quote } from "lucide-react";
// import { useLanguage } from "@/contexts/language-context";

interface AnimatedQuoteBlockProps {
  text: string;
  author: string;
  role?: string;
}

export function AnimatedQuoteBlock({
  text,
  author,
  role,
}: AnimatedQuoteBlockProps) {
  // const { language } = useLanguage();

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
      },
    },
  };

  const wordVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.5,
      },
    },
  };

  const words = text.split(" ");

  return (
    <div className="my-16">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        whileInView={{ opacity: 1, scale: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 0.8 }}
      >
        <Card className="relative overflow-hidden bg-gradient-to-br from-[#2d5a3d]/5 to-[#c4a747]/5 border-none shadow-lg">
          <CardContent className="p-12 text-center">
            <motion.div
              initial={{ scale: 0, rotate: -180 }}
              whileInView={{ scale: 1, rotate: 0 }}
              viewport={{ once: true }}
              transition={{
                delay: 0.2,
                duration: 0.8,
                type: "spring",
                stiffness: 200,
              }}
              className="inline-flex p-4 rounded-full bg-[#2d5a3d]/10 mb-8"
            >
              <Quote className="h-8 w-8 text-[#2d5a3d]" />
            </motion.div>

            <motion.div
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
              variants={containerVariants}
              className="mb-8"
            >
              <blockquote className="text-2xl md:text-3xl font-medium text-foreground leading-relaxed">
                {words.map((word, index) => (
                  <motion.span
                    key={index}
                    variants={wordVariants}
                    className="inline-block mr-2"
                  >
                    {word}
                  </motion.span>
                ))}
              </blockquote>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 1, duration: 0.6 }}
              className="space-y-2"
            >
              <div className="text-lg font-semibold text-[#2d5a3d]">
                {author}
              </div>
              {role && (
                <div className="text-sm text-muted-foreground">{role}</div>
              )}
            </motion.div>

            <motion.div
              animate={{
                rotate: 360,
              }}
              transition={{
                duration: 20,
                repeat: Number.POSITIVE_INFINITY,
                ease: "linear",
              }}
              className="absolute -top-4 -right-4 w-24 h-24 bg-gradient-to-br from-[#c4a747]/20 to-[#2d5a3d]/20 rounded-full blur-xl"
            />
            <motion.div
              animate={{
                rotate: -360,
              }}
              transition={{
                duration: 25,
                repeat: Number.POSITIVE_INFINITY,
                ease: "linear",
              }}
              className="absolute -bottom-4 -left-4 w-32 h-32 bg-gradient-to-br from-[#2d5a3d]/20 to-[#c4a747]/20 rounded-full blur-xl"
            />
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
