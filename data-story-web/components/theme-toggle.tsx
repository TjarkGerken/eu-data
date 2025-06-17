"use client";

import { useState, useEffect } from "react";
import { useTheme } from "next-themes";
import { Sun, Moon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useScroll } from "motion/react";

export function ThemeToggle() {
  const [mounted, setMounted] = useState(false);
  const { theme, setTheme, resolvedTheme } = useTheme();
  const { scrollY } = useScroll();
  const [isScrolled, setIsScrolled] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    const unsubscribe = scrollY.on("change", (latest) => {
      setIsScrolled(latest > 50);
    });
    return () => unsubscribe();
  }, [scrollY]);

  if (!mounted) {
    return (
      <Button
        variant={isScrolled ? "outline" : "ghost"}
        size="icon"
        disabled
        className={`transition-all duration-300 ${
          isScrolled ? "" : "text-white hover:bg-white/20 border-white/30"
        }`}
      >
        <Sun className="h-[1.2rem] w-[1.2rem]" />
        <span className="sr-only">Toggle theme</span>
      </Button>
    );
  }

  const toggleTheme = () => {
    setTheme(resolvedTheme === "light" ? "dark" : "light");
  };

  return (
    <Button
      variant={isScrolled ? "outline" : "ghost"}
      size="icon"
      onClick={toggleTheme}
      className={`transition-all duration-300 ${
        isScrolled ? "" : "text-white hover:bg-white/20 border-white/30"
      }`}
    >
      {resolvedTheme === "light" ? (
        <Moon className="h-[1.2rem] w-[1.2rem]" />
      ) : (
        <Sun className="h-[1.2rem] w-[1.2rem]" />
      )}
      <span className="sr-only">Toggle theme</span>
    </Button>
  );
}
