"use client";

import { Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import Image from "next/image";
import { LanguageSwitcher } from "@/components/language-switcher";
import { useLanguage } from "@/contexts/language-context";

export function Header() {
  const { t } = useLanguage();

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 flex justify-center items-center">
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
              <span className="text-lg font-bold text-[#2d5a3d]">
                EU GEOLYTICS
              </span>
              <span className="text-xs text-muted-foreground">
                {t.dataStories}
              </span>
            </div>
          </div>
        </div>

        <nav className="hidden md:flex items-center space-x-6">
          <a
            href="#story"
            className="text-sm font-medium hover:text-[#2d5a3d] transition-colors"
          >
            {t.story}
          </a>
          <a
            href="#visualizations"
            className="text-sm font-medium hover:text-[#2d5a3d] transition-colors"
          >
            {t.visualizations}
          </a>
          <a
            href="#bibliography"
            className="text-sm font-medium hover:text-[#2d5a3d] transition-colors"
          >
            {t.bibliography}
          </a>
        </nav>

        <div className="flex items-center space-x-2">
          <LanguageSwitcher />
          <ThemeToggle />
          <Button variant="outline" size="icon" className="md:hidden">
            <Menu className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </header>
  );
}
