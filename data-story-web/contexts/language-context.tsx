"use client"

import { createContext, useContext, useState, useEffect, type ReactNode } from "react"
import { type Language, getTranslation, type Translation } from "@/lib/i18n"

interface LanguageContextType {
  language: Language
  setLanguage: (language: Language) => void
  t: Translation
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined)

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>("en")
  const [t, setT] = useState<Translation>(getTranslation("en"))

  useEffect(() => {
    // Load language from localStorage on mount
    const savedLanguage = localStorage.getItem("language") as Language
    if (savedLanguage && (savedLanguage === "en" || savedLanguage === "de")) {
      setLanguageState(savedLanguage)
      setT(getTranslation(savedLanguage))
    }
  }, [])

  const setLanguage = (newLanguage: Language) => {
    setLanguageState(newLanguage)
    setT(getTranslation(newLanguage))
    localStorage.setItem("language", newLanguage)
  }

  return <LanguageContext.Provider value={{ language, setLanguage, t }}>{children}</LanguageContext.Provider>
}

export function useLanguage() {
  const context = useContext(LanguageContext)
  if (context === undefined) {
    throw new Error("useLanguage must be used within a LanguageProvider")
  }
  return context
}
