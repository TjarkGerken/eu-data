"use client";

import ReactMarkdown from "react-markdown";
import { useMemo } from "react";
import { useGlobalCitation } from "@/contexts/global-citation-context";
import { processContentWithGlobalCitations } from "@/lib/global-citation-processor";

interface CitationAwareMarkdownProps {
  content: string;
  references?: Array<{
    id: string;
    title: string;
    authors: string[];
    type: string;
    year?: number;
  }>;
}

export function CitationAwareMarkdown({ content, references = [] }: CitationAwareMarkdownProps) {
  const { globalCitationData } = useGlobalCitation();
  
  const processedData = useMemo(() => {
    if (!content || typeof content !== 'string') {
      return {
        processedContent: content || '',
        citationMap: new Map(),
        orderedReferences: references || [],
        citationReferences: new Map()
      };
    }

    // Use global citation data if available
    if (globalCitationData) {
      const processedData = processContentWithGlobalCitations(
        content, 
        globalCitationData.citationMap,
        globalCitationData.readableIdMap
      );
      
      return {
        processedContent: processedData.content,
        citationMap: globalCitationData.citationMap,
        orderedReferences: globalCitationData.orderedReferences,
        citationReferences: processedData.citationReferences
      };
    }

    // Fallback to local processing if no global data (shouldn't happen in normal usage)
    const citationMap = new Map<string, number>();
    const citationReferences = new Map<number, string>();
    const referencedIds = new Set<string>();
    let citationCounter = 1;

    const citationMatches = [...content.matchAll(/\\cite\{([^}]+)\}/g)];
    
    citationMatches.forEach(match => {
      const refId = match[1];
      if (refId && !citationMap.has(refId)) {
        citationMap.set(refId, citationCounter);
        citationReferences.set(citationCounter, refId);
        citationCounter++;
        referencedIds.add(refId);
      }
    });

    let processedContent = content;
    citationMap.forEach((number, refId) => {
      const regex = new RegExp(`\\\\cite\\{${refId.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\}`, 'g');
      processedContent = processedContent.replace(regex, `[${number}]`);
    });

    const orderedReferences = Array.from(citationMap.entries())
      .sort((a, b) => a[1] - b[1])
      .map(([refId]) => references.find(r => r && r.id === refId))
      .filter(Boolean)
      .concat(references.filter(r => r && !referencedIds.has(r.id)));

    return {
      processedContent,
      citationMap,
      orderedReferences,
      citationReferences
    };
  }, [content, references, globalCitationData]);

  const handleCitationClick = (referenceId: string) => {
    const event = new CustomEvent('highlightReference', { detail: referenceId });
    window.dispatchEvent(event);
  };

  const createCitationButton = (citationNumber: number, referenceId: string) => {
    const reference = processedData.orderedReferences.find(r => r?.id === referenceId);
    return (
      <button
        key={`citation-${citationNumber}-${referenceId}`}
        className="inline-flex items-center justify-center min-w-[1.5rem] h-6 text-xs bg-[#2d5a3d] text-white rounded hover:bg-[#2d5a3d]/80 transition-colors cursor-pointer mx-1"
        onClick={() => handleCitationClick(referenceId)}
        title={`View reference: ${reference?.title || 'Unknown'}`}
      >
        {citationNumber}
      </button>
    );
  };

  const processTextForCitations = (text: string) => {
    if (!text || typeof text !== 'string') return text;
    
    const parts = text.split(/(\[\d+\])/);
    return parts.map((part) => {
      const citationMatch = part.match(/^\[(\d+)\]$/);
      if (citationMatch) {
        const citationNumber = parseInt(citationMatch[1]);
        const referenceId = processedData.citationReferences.get(citationNumber);
        if (referenceId) {
          return createCitationButton(citationNumber, referenceId);
        }
      }
      return part;
    });
  };

  return (
    <div className="prose prose-lg max-w-none">
      <ReactMarkdown
        components={{
          h1: ({ children }) => (
            <h1 className="text-3xl font-bold text-[#2d5a3d] mb-6">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-2xl font-semibold text-[#2d5a3d] mb-4">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-xl font-medium text-[#2d5a3d] mb-3">
              {children}
            </h3>
          ),
          p: ({ children }) => {
            const processChildren = (children: React.ReactNode): React.ReactNode => {
              if (Array.isArray(children)) {
                return children.map((child, index) => {
                  if (typeof child === 'string') {
                    const processed = processTextForCitations(child);
                    if (Array.isArray(processed)) {
                      return processed.map((part, partIndex) => (
                        <span key={`${index}-${partIndex}`}>{part}</span>
                      ));
                    }
                    return processed;
                  }
                  return child;
                });
              }
              if (typeof children === 'string') {
                return processTextForCitations(children);
              }
              return children;
            };

            return (
              <p className="text-muted-foreground leading-relaxed mb-4">
                {processChildren(children)}
              </p>
            );
          },
          ul: ({ children }) => (
            <ul className="list-disc list-inside space-y-2 mb-4">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal list-inside space-y-2 mb-4">
              {children}
            </ol>
          ),
          li: ({ children }) => {
            const processChildren = (children: React.ReactNode): React.ReactNode => {
              if (Array.isArray(children)) {
                return children.map((child, index) => {
                  if (typeof child === 'string') {
                    const processed = processTextForCitations(child);
                    if (Array.isArray(processed)) {
                      return processed.map((part, partIndex) => (
                        <span key={`${index}-${partIndex}`}>{part}</span>
                      ));
                    }
                    return processed;
                  }
                  return child;
                });
              }
              if (typeof children === 'string') {
                return processTextForCitations(children);
              }
              return children;
            };

            return (
              <li className="text-muted-foreground">
                {processChildren(children)}
              </li>
            );
          },
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-[#2d5a3d] pl-4 italic text-muted-foreground">
              {children}
            </blockquote>
          ),
        }}
      >
        {processedData.processedContent}
      </ReactMarkdown>

      {processedData.orderedReferences.length > 0 && (
        <div className="mt-8 pt-6 border-t border-muted">
          <h4 className="text-sm font-semibold text-muted-foreground mb-3">References</h4>
          <div className="space-y-2">
            {processedData.orderedReferences.map((ref) => {
              if (!ref) return null;
              const citationNumber = processedData.citationMap.get(ref.id);
              return (
                <div 
                  key={ref.id} 
                  className="text-xs text-muted-foreground cursor-pointer hover:text-foreground transition-colors flex items-start gap-2"
                  onClick={() => handleCitationClick(ref.id)}
                >
                  {citationNumber && (
                    <span className="inline-flex items-center justify-center min-w-[1.5rem] h-5 text-xs bg-muted text-muted-foreground rounded font-mono">
                      {citationNumber}
                    </span>
                  )}
                  <div className="flex-1">
                    <span className="font-medium">{ref.title}</span>
                    {ref.authors && ref.authors.length > 0 && (
                      <span className="ml-2">- {ref.authors.join(", ")}</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
} 