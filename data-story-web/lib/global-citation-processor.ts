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
  readable_id: string;
}

function createReadableIdMap(references: Reference[]): Map<string, string> {
  const readableIdMap = new Map<string, string>();

  if (!Array.isArray(references)) return readableIdMap;

  references.forEach((ref) => {
    if (ref?.readable_id && ref?.id) {
      readableIdMap.set(ref.readable_id, ref.id);
    }
  });

  return readableIdMap;
}

function extractCitationsFromContent(content: string): string[] {
  if (!content || typeof content !== "string") return [];

  const citations: string[] = [];
  const citationMatches = [...content.matchAll(/\\cite\{([^}]+)\}/g)];

  citationMatches.forEach((match) => {
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

  if (!Array.isArray(blocks)) return allReferences;

  blocks.forEach((block) => {
    if ("references" in block && Array.isArray(block.references)) {
      block.references.forEach((ref) => {
        // Handle both string IDs and Reference objects
        if (typeof ref === "string") {
          // Skip string references as we can't process them without full data
          return;
        }

        if (ref && ref.id && !seenIds.has(ref.id)) {
          seenIds.add(ref.id);
          allReferences.push({
            ...ref,
            year: ref.year || new Date().getFullYear(),
            readable_id: ref.id, // Use id as readable_id if not present
          });
        }
      });
    }
  });

  return allReferences;
}

export function processGlobalCitations(
  blocks: DataStoryBlock[],
  globalReferences: Reference[] = []
): GlobalCitationData {
  const citationMap = new Map<string, number>();
  const referenceToNumberMap = new Map<string, number>(); // Maps reference ID to citation number
  const citationOrder: string[] = [];
  let citationCounter = 1;

  // Ensure we have valid arrays
  const safeBlocks = Array.isArray(blocks) ? blocks : [];
  const safeGlobalReferences = Array.isArray(globalReferences)
    ? globalReferences
    : [];

  // Get all available references from all blocks
  const allReferences = getAllReferencesFromBlocks(safeBlocks);

  // Create readable ID mapping from globalReferences (not just block references)
  const readableIdMap = createReadableIdMap(
    safeGlobalReferences.length > 0 ? safeGlobalReferences : allReferences
  );

  // Process blocks in order to maintain citation sequence
  safeBlocks.forEach((block) => {
    let content = "";

    // Extract content that might contain citations
    switch (block.type) {
      case "markdown":
        content = block.content || "";
        break;
      case "callout":
      case "interactive-callout":
        content = block.content || "";
        break;
      default:
        // Other blocks might have content in different places
        break;
    }

    if (content) {
      const citations = extractCitationsFromContent(content);
      citations.forEach((citationId) => {
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
  citationOrder.forEach((refId) => {
    const ref = allReferences.find((r) => r.id === refId);
    if (ref) {
      orderedReferences.push(ref);
    }
  });

  // Then add uncited references
  allReferences.forEach((ref) => {
    if (!referencedIds.has(ref.id)) {
      orderedReferences.push(ref);
    }
  });

  return {
    citationMap,
    orderedReferences,
    totalCitations: citationCounter - 1,
    readableIdMap,
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
  if (!content || typeof content !== "string") {
    return {
      content: content || "",
      citationReferences: new Map(),
    };
  }

  let processedContent = content;
  const citationReferences = new Map<number, string>();

  // Replace each citation with its global number
  globalCitationMap.forEach((number, citationId) => {
    const regex = new RegExp(
      `\\\\cite\\{${citationId.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\}`,
      "g"
    );

    // Determine the actual reference ID for click handling
    const actualRefId = readableIdMap.get(citationId) || citationId;
    citationReferences.set(number, actualRefId);

    // Replace with simple numbered citation
    processedContent = processedContent.replace(regex, `[${number}]`);
  });

  return {
    content: processedContent,
    citationReferences,
  };
}
