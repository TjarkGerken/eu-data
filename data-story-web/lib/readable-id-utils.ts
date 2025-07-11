import { supabase } from "./supabase";

export interface ReadableIdGenerationOptions {
  authors: string[];
  year: number;
  excludeId?: string; // ID to exclude when checking for conflicts (for updates)
}

export function generateBaseReadableId(
  authors: string[],
  year: number
): string {
  if (!authors || authors.length === 0) {
    return `Unknown${year}`;
  }

  const firstAuthor = authors[0].trim();
  if (!firstAuthor) {
    return `Unknown${year}`;
  }

  const lastNameMatch = firstAuthor.match(/([A-Za-z]+)(?:\s|$)/);
  const lastName = lastNameMatch
    ? lastNameMatch[1]
    : firstAuthor.replace(/\s+/g, "");

  return `${lastName}${year}`;
}

export async function generateUniqueReadableId(
  options: ReadableIdGenerationOptions
): Promise<string> {
  const baseId = generateBaseReadableId(options.authors, options.year);

  let { data: existingRefs, error } = await supabase
    .from("content_references")
    .select("readable_id, id")
    .ilike("readable_id", `${baseId}%`);

  if (error) {
    console.error("Error checking existing readable IDs:", error);
    throw error;
  }

  existingRefs = existingRefs || [];

  // Filter out the current reference if we're updating
  if (options.excludeId) {
    existingRefs = existingRefs.filter((ref) => ref.id !== options.excludeId);
  }

  const existingIds = new Set(existingRefs.map((ref) => ref.readable_id));

  // If base ID is available, use it
  if (!existingIds.has(baseId)) {
    return baseId;
  }

  // Find the next available suffix
  let suffix = 2;
  let candidateId = `${baseId}-${suffix}`;

  while (existingIds.has(candidateId)) {
    suffix++;
    candidateId = `${baseId}-${suffix}`;
  }

  return candidateId;
}

export async function validateReadableIdUniqueness(
  readableId: string,
  excludeId?: string
): Promise<{ isValid: boolean; suggestedId?: string }> {
  const { data: existing, error } = await supabase
    .from("content_references")
    .select("id")
    .eq("readable_id", readableId)
    .maybeSingle();

  if (error) {
    console.error("Error validating readable ID:", error);
    throw error;
  }

  // If no existing reference found, ID is valid
  if (!existing) {
    return { isValid: true };
  }

  // If we're updating and the existing ID belongs to the same reference, it's valid
  if (excludeId && existing.id === excludeId) {
    return { isValid: true };
  }

  // ID is taken, suggest an alternative
  const parts = readableId.match(/^(.+?)(-\d+)?$/);
  if (!parts) {
    return { isValid: false, suggestedId: `${readableId}-2` };
  }

  const baseId = parts[1];
  const year = baseId.match(/(\d{4})$/)?.[1];

  if (!year) {
    return { isValid: false, suggestedId: `${readableId}-2` };
  }

  // Generate a new unique ID based on the base
  try {
    const suggestedId = await generateUniqueReadableId({
      authors: [baseId.replace(year, "")],
      year: parseInt(year),
      excludeId,
    });

    return { isValid: false, suggestedId };
  } catch {
    return { isValid: false, suggestedId: `${readableId}-2` };
  }
}

export function sanitizeReadableId(input: string): string {
  return input
    .trim()
    .replace(/[^a-zA-Z0-9-]/g, "") // Remove special characters except hyphen
    .replace(/^-+|-+$/g, "") // Remove leading/trailing hyphens
    .replace(/-+/g, "-") // Collapse multiple hyphens
    .substring(0, 50); // Limit length
}
