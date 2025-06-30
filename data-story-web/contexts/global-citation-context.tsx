"use client";

import React, { createContext, useContext, ReactNode } from 'react';
import { GlobalCitationData } from '@/lib/global-citation-processor';

interface GlobalCitationContextType {
  globalCitationData: GlobalCitationData | null;
}

const GlobalCitationContext = createContext<GlobalCitationContextType>({
  globalCitationData: null,
});

interface GlobalCitationProviderProps {
  children: ReactNode;
  globalCitationData: GlobalCitationData;
}

export function GlobalCitationProvider({ 
  children, 
  globalCitationData 
}: GlobalCitationProviderProps) {
  return (
    <GlobalCitationContext.Provider value={{ globalCitationData }}>
      {children}
    </GlobalCitationContext.Provider>
  );
}

export function useGlobalCitation() {
  const context = useContext(GlobalCitationContext);
  if (!context) {
    throw new Error('useGlobalCitation must be used within a GlobalCitationProvider');
  }
  return context;
} 