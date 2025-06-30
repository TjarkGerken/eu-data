import { DataStoryBlock } from "@/lib/types";

export interface GlobalCitationData {
  citationMap: Map<string, number>;
  orderedReferences: Array<{
    id: string;
    title: string;
    authors: string[];
    type: string;
    year?: number;
  }>;
  totalCitations: number;
  readableIdMap: Map<string, string>; // Maps readable IDs to actual reference IDs
}

export interface Reference {
  id: string;
  title: string;
  authors: string[];
  type: string;
  year?: number;
}

function generateReadableId(ref: Reference, index: number = 0): string {
  if (!ref?.authors?.[0]) return `Unknown${ref?.year || new Date().getFullYear()}`;
  const firstAuthor = ref.authors[0].split(' ').pop() || 'Unknown';
  const year = ref.year || new Date().getFullYear();
  return `${firstAuthor}${year}${index > 0 ? `-${index + 1}` : ''}`;
}

function createReadableIdMap(references: Reference[]): Map<string, string> {
  const readableIdMap = new Map<string, string>();
  
  references.forEach((ref) => {
    // Check for duplicates to generate unique readable ID
    const duplicates = references.filter(r => {
      if (!r?.authors?.[0] || !ref?.authors?.[0]) return false;
      const rFirstAuthor = r.authors[0].split(' ').pop() || 'Unknown';
      const refFirstAuthor = ref.authors[0].split(' ').pop() || 'Unknown';
      return rFirstAuthor === refFirstAuthor && r.year === ref.year;
    });

    const duplicateIndex = duplicates.findIndex(r => r?.id === ref.id);
    const readableId = generateReadableId(ref, duplicateIndex >= 0 ? duplicateIndex : 0);
    readableIdMap.set(readableId, ref.id);
  });
  
  return readableIdMap;
}

function extractCitationsFromContent(content: string): string[] {
  if (!content || typeof content !== 'string') return [];
  
  const citations: string[] = [];
  const citationMatches = [...content.matchAll(/\\cite\{([^}]+)\}/g)];
  
  citationMatches.forEach(match => {
    const refId = match[1];
    if (refId && !citations.includes(refId)) {
      citations.push(refId);
    }
  });
  
  return citations;
}

function getAllReferencesFromBlocks(blocks: DataStoryBlock[]): Reference[] {
  const allReferences: Reference[] = [];
  const seenIds = new Set<string>();
  
  blocks.forEach(block => {
    if ('references' in block && block.references) {
      block.references.forEach((ref) => {
        // Handle both string IDs and Reference objects
        if (typeof ref === 'string') {
          // Skip string references as we can't process them without full data
          return;
        }
        
        if (ref && ref.id && !seenIds.has(ref.id)) {
          seenIds.add(ref.id);
          allReferences.push({
            ...ref,
            year: ref.year || new Date().getFullYear()
          });
        }
      });
    }
  });
  
  return allReferences;
}

export function processGlobalCitations(blocks: DataStoryBlock[]): GlobalCitationData {
  const citationMap = new Map<string, number>();
  const referenceToNumberMap = new Map<string, number>(); // Maps reference ID to citation number
  const citationOrder: string[] = [];
  let citationCounter = 1;
  
  // Get all available references from all blocks
  const allReferences = getAllReferencesFromBlocks(blocks);
  
  // Create readable ID mapping
  const readableIdMap = createReadableIdMap(allReferences);
  
  // Process blocks in order to maintain citation sequence
  blocks.forEach(block => {
    let content = '';
    
    // Extract content that might contain citations
    switch (block.type) {
      case 'markdown':
        content = block.content || '';
        break;
      case 'callout':
      case 'interactive-callout':
        content = block.content || '';
        break;
      default:
        // Other blocks might have content in different places
        break;
    }
    
    if (content) {
      const citations = extractCitationsFromContent(content);
      citations.forEach(citationId => {
        // Resolve readable ID to actual reference ID if needed
        const actualRefId = readableIdMap.get(citationId) || citationId;
        
        // Check if we've already assigned a number to this reference
        if (referenceToNumberMap.has(actualRefId)) {
          // Use existing number for this citation variant
          const existingNumber = referenceToNumberMap.get(actualRefId)!;
          citationMap.set(citationId, existingNumber);
        } else {
          // First time seeing this reference, assign new number
          const newNumber = citationCounter++;
          referenceToNumberMap.set(actualRefId, newNumber);
          citationMap.set(citationId, newNumber);
          citationOrder.push(actualRefId);
        }
      });
    }
  });
  
  // Order references by citation appearance, then add uncited references
  const orderedReferences: Reference[] = [];
  const referencedIds = new Set(citationOrder);
  
  // First, add cited references in order of appearance
  citationOrder.forEach(refId => {
    const ref = allReferences.find(r => r.id === refId);
    if (ref) {
      orderedReferences.push(ref);
    }
  });
  
  // Then add uncited references
  allReferences.forEach(ref => {
    if (!referencedIds.has(ref.id)) {
      orderedReferences.push(ref);
    }
  });
  
  return {
    citationMap,
    orderedReferences,
    totalCitations: citationCounter - 1,
    readableIdMap
  };
}

export interface ProcessedCitationData {
  content: string;
  citationReferences: Map<number, string>; // Maps citation number to actual reference ID
}

export function processContentWithGlobalCitations(
  content: string, 
  globalCitationMap: Map<string, number>,
  readableIdMap: Map<string, string>
): ProcessedCitationData {
  if (!content || typeof content !== 'string') {
    return {
      content: content || '',
      citationReferences: new Map()
    };
  }
  
  let processedContent = content;
  const citationReferences = new Map<number, string>();
  
  // Replace each citation with its global number
  globalCitationMap.forEach((number, citationId) => {
    const regex = new RegExp(
      `\\\\cite\\{${citationId.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\}`, 
      'g'
    );
    
    // Determine the actual reference ID for click handling
    const actualRefId = readableIdMap.get(citationId) || citationId;
    citationReferences.set(number, actualRefId);
    
    // Replace with simple numbered citation
    processedContent = processedContent.replace(regex, `[${number}]`);
  });
  
  return {
    content: processedContent,
    citationReferences
  };
} 