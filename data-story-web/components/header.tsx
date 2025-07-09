"use client";

import { Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import Image from "next/image";
import { useLanguage } from "@/contexts/language-context";
import { motion, useScroll, useTransform } from "motion/react";
import { useEffect, useState } from "react";

interface HeaderProps {
  enableAnimations?: boolean;
}

export function Header({ enableAnimations = true }: HeaderProps) {
  const { t } = useLanguage();
  const { scrollY } = useScroll();
  const [isScrolled, setIsScrolled] = useState(false);

  const backgroundColor = useTransform(
    scrollY,
    [0, 100],
    ["rgba(255, 255, 255, 0)", "rgba(255, 255, 255, 0.95)"]
  );

  const textColor = useTransform(
    scrollY,
    [0, 100],
    ["rgb(255, 255, 255)", "rgb(45, 90, 61)"]
  );

  useEffect(() => {
    if (!enableAnimations) return;

    const unsubscribe = scrollY.on("change", (latest) => {
      setIsScrolled(latest > 50);
    });
    return () => unsubscribe();
  }, [scrollY, enableAnimations]);

  // Static styles for when animations are disabled
  const staticStyles = {
    backgroundColor: "rgba(255, 255, 255, 0.95)",
    textColor: "rgb(45, 90, 61)",
  };

  if (enableAnimations) {
    return (
      <motion.header
        className="fixed top-0 z-[9999] w-full transition-all duration-300"
        style={{ backgroundColor }}
      >
        <div
          className={`w-full transition-all duration-300 flex justify-center ${
            isScrolled ? "border-b border-border/40 backdrop-blur-md" : ""
          }`}
        >
          <div className="container flex h-16 items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <Image
                  src="/logo.png"
                  alt="EU Geolytics"
                  width={40}
                  height={40}
                  className="rounded-full"
                />
                <div className="flex flex-col">
                  <motion.span
                    className="text-lg font-bold transition-colors duration-300"
                    style={{ color: textColor }}
                  >
                    EU GEOLYTICS
                  </motion.span>
                  <motion.span
                    className="text-xs transition-colors duration-300"
                    style={{
                      color: isScrolled
                        ? "rgb(113, 113, 122)"
                        : "rgba(255, 255, 255, 0.8)",
                    }}
                  >
                    {t.dataStories}
                  </motion.span>
                </div>
              </div>
            </div>

            <nav className="hidden md:flex items-center space-x-6">
              <motion.a
                href="#main-content"
                className="text-sm font-medium transition-colors duration-300 hover:opacity-80"
                style={{ color: isScrolled ? "#2d5a3d" : "#ffffff" }}
              >
                {t.story}
              </motion.a>
              <motion.a
                href="#visualizations"
                className="text-sm font-medium transition-colors duration-300 hover:opacity-80"
                style={{ color: isScrolled ? "#2d5a3d" : "#ffffff" }}
              >
                {t.visualizations}
              </motion.a>
              <motion.a
                href="/gallery"
                className="text-sm font-medium transition-colors duration-300 hover:opacity-80"
                style={{ color: isScrolled ? "#2d5a3d" : "#ffffff" }}
              >
                {t.gallery || "Gallery"}
              </motion.a>
              <motion.a
                href="#bibliography"
                className="text-sm font-medium transition-colors duration-300 hover:opacity-80"
                style={{ color: isScrolled ? "#2d5a3d" : "#ffffff" }}
              >
                {t.bibliography}
              </motion.a>
            </nav>

            <div className="flex items-center space-x-2">
              <Button
                variant={isScrolled ? "outline" : "ghost"}
                size="icon"
                className={`md:hidden transition-all duration-300 ${
                  isScrolled
                    ? ""
                    : "text-white hover:bg-white/20 border-white/30"
                }`}
              >
                <Menu className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </motion.header>
    );
  }

  return (
    <header
      className="fixed top-0 z-[9999] w-full transition-all duration-300"
      style={{ backgroundColor: staticStyles.backgroundColor }}
    >
      <div className="w-full transition-all duration-300 flex justify-center border-b border-border/40 backdrop-blur-md">
        <div className="container flex h-16 items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <Image
                src="/logo.png"
                alt="EU Geolytics"
                width={40}
                height={40}
                className="rounded-full"
              />
              <div className="flex flex-col">
                <span
                  className="text-lg font-bold transition-colors duration-300"
                  style={{ color: staticStyles.textColor }}
                >
                  EU GEOLYTICS
                </span>
                <span
                  className="text-xs transition-colors duration-300"
                  style={{ color: "rgb(113, 113, 122)" }}
                >
                  {t.dataStories}
                </span>
              </div>
            </div>
          </div>

          <nav className="hidden md:flex items-center space-x-6">
            <a
              href="#main-content"
              className="text-sm font-medium transition-colors duration-300 hover:opacity-80"
              style={{ color: "#2d5a3d" }}
            >
              {t.story}
            </a>
            <a
              href="#visualizations"
              className="text-sm font-medium transition-colors duration-300 hover:opacity-80"
              style={{ color: "#2d5a3d" }}
            >
              {t.visualizations}
            </a>
            <a
              href="/gallery"
              className="text-sm font-medium transition-colors duration-300 hover:opacity-80"
              style={{ color: "#2d5a3d" }}
            >
              {t.gallery || "Gallery"}
            </a>
            <a
              href="#bibliography"
              className="text-sm font-medium transition-colors duration-300 hover:opacity-80"
              style={{ color: "#2d5a3d" }}
            >
              {t.bibliography}
            </a>
          </nav>

          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="icon"
              className="md:hidden transition-all duration-300"
            >
              <Menu className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
}
