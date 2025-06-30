export interface CitationMatch {
  referenceId: string;
  index: number;
  citationNumber: number;
}

export interface Reference {
  id: string;
  title: string;
  authors: string[];
  year: number;
  type: string;
}

export function generateReadableId(ref: Reference, index: number = 0): string {
  const firstAuthor = ref.authors[0]?.split(' ').pop() || 'Unknown';
  const year = ref.year || new Date().getFullYear();
  return `${firstAuthor}${year}${index > 0 ? `-${index + 1}` : ''}`;
}

export function parseCitationsFromText(text: string): CitationMatch[] {
  if (!text || typeof text !== 'string') {
    return [];
  }
  
  const citationPattern = /\\cite\{([^}]+)\}/g;
  const matches: CitationMatch[] = [];
  const seenRefs = new Set<string>();
  let citationNumber = 1;
  let match;

  while ((match = citationPattern.exec(text)) !== null) {
    const referenceId = match[1];
    
    if (referenceId && !seenRefs.has(referenceId)) {
      seenRefs.add(referenceId);
      matches.push({
        referenceId,
        index: match.index || 0,
        citationNumber,
      });
      citationNumber++;
    }
  }

  return matches;
}

export function orderReferencesByCitation(
  references: Reference[],
  citationMatches: CitationMatch[]
): Reference[] {
  if (!Array.isArray(references) || !Array.isArray(citationMatches)) {
    return references || [];
  }

  const orderedRefs: Reference[] = [];
  const refMap = new Map<string, Reference>();
  
  references.forEach(ref => {
    if (ref && ref.id) {
      refMap.set(ref.id, ref);
    }
  });

  citationMatches.forEach(({ referenceId }) => {
    if (!referenceId) return;
    const ref = refMap.get(referenceId);
    if (ref && !orderedRefs.find(r => r.id === ref.id)) {
      orderedRefs.push(ref);
    }
  });

  references.forEach(ref => {
    if (ref && ref.id && !orderedRefs.find(r => r.id === ref.id)) {
      orderedRefs.push(ref);
    }
  });

  return orderedRefs;
}

export function getCitationNumber(
  referenceId: string,
  citationMatches: CitationMatch[]
): number | null {
  const match = citationMatches.find(m => m.referenceId === referenceId);
  return match ? match.citationNumber : null;
}

export function renderTextWithCitations(
  text: string,
  citationMatches: CitationMatch[]
): string {
  if (citationMatches.length === 0) return text;

  const refNumberMap = new Map(
    citationMatches.map(m => [m.referenceId, m.citationNumber])
  );

  return text.replace(/\\cite\{([^}]+)\}/g, (match, referenceId) => {
    const citationNumber = refNumberMap.get(referenceId);
    return citationNumber ? `[${citationNumber}]` : match;
  });
} 