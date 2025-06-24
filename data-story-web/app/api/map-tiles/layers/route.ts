import { NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";
import path from "path";

export interface MapLayerMetadata {
  id: string;
  name: string;
  dataType: "raster" | "vector";
  format: "cog" | "mbtiles";
  bounds: [number, number, number, number];
  colorScale: string[];
  valueRange: [number, number];
  description?: string;
  uploadedAt: string;
  fileSize: number;
}

export async function GET() {
  try {
    const layers: MapLayerMetadata[] = [];

    // Only get layers from Supabase storage
    const { data: storageLayers, error: storageError } = await supabase.storage
      .from("map-layers")
      .list();

    if (storageError) {
      console.error("Error loading from Supabase storage:", storageError);
      return NextResponse.json(
        { error: "Failed to load layers from storage" },
        { status: 500 }
      );
    }

    if (storageLayers) {
      for (const layer of storageLayers) {
        const layerMetadata = await extractLayerMetadata(layer);
        if (layerMetadata) {
          layers.push(layerMetadata);
        }
      }
    }

    return NextResponse.json({ layers });
  } catch (error) {
    console.error("Error listing layers:", error);
    return NextResponse.json(
      { error: "Failed to list layers" },
      { status: 500 }
    );
  }
}

async function extractLayerMetadata(
  layer: { name: string; created_at?: string; updated_at?: string; metadata?: { size?: number } }
): Promise<MapLayerMetadata | null> {
  try {
    const fileName = layer.name;
    // Start with the full filename without extension
    let layerId = path.basename(fileName, path.extname(fileName));
    
    // Handle special naming patterns for clusters to create more readable IDs
    if (fileName.includes("clusters_SLR")) {
      // Extract scenario and risk type from filename like "clusters_SLR-0-Current_GDP.mbtiles"
      const match = fileName.match(/clusters_SLR-(\d+)-(\w+)_(\w+)/);
      if (match) {
        const scenario = match[2].toLowerCase(); // "current", "severe", etc.
        const riskType = match[3].toLowerCase(); // "gdp", "population", "freight", etc.
        layerId = `clusters-slr-${scenario}-${riskType}`;
      }
      // If no match, keep the original layerId (full filename without extension)
    }
    
    // For all other files, preserve the original filename
    // This ensures files like "risk_SLR-3-Severe_COMBINED.cog" become "risk_SLR-3-Severe_COMBINED"

    // Determine layer type from filename
    const layerType = determineLayerType(fileName);

    // Determine data type and format based on file extension
    let dataType: "raster" | "vector";
    let format: "cog" | "mbtiles";

    if (fileName.endsWith(".cog")) {
      dataType = "raster";
      format = "cog";
    } else if (fileName.endsWith(".mbtiles")) {
      dataType = "vector";
      format = "mbtiles";
    } else {
      // Default fallback - try to guess from filename
      if (
        layerType === "risk" ||
        layerType === "hazard" ||
        layerType === "exposition" ||
        layerType === "relevance"
      ) {
        dataType = "raster";
        format = "cog";
      } else {
        dataType = "vector";
        format = "mbtiles";
      }
    }

    return {
      id: layerId,
      name: formatDisplayName(layerId),
      dataType,
      format,
      bounds: [-180, -90, 180, 90],
      colorScale: getDefaultColorScale(layerType),
      valueRange: [0, 100],
      description: `${layerType} layer: ${layerId}`,
      uploadedAt:
        layer.created_at || layer.updated_at || new Date().toISOString(),
      fileSize: layer.metadata?.size || 0,
    };
  } catch (error) {
    console.error("Error extracting layer metadata:", error);
    return null;
  }
}

function formatDisplayName(layerId: string): string {
  // Create a more readable display name
  return layerId
    .replace(/_/g, " ")           // Replace underscores with spaces
    .replace(/-/g, " ")           // Replace hyphens with spaces  
    .replace(/\b\w/g, (l) => l.toUpperCase())  // Capitalize first letter of each word
    .replace(/\bSlr\b/g, "SLR")   // Fix SLR capitalization
    .replace(/\bGdp\b/g, "GDP")   // Fix GDP capitalization
    .replace(/\bHrst\b/g, "HRST") // Fix HRST capitalization
    .trim();
}

function determineLayerType(fileName: string): string {
  const name = fileName.toLowerCase();
  if (name.includes("risk")) return "risk";
  if (name.includes("hazard")) return "hazard";
  if (name.includes("exposition")) return "exposition";
  if (name.includes("relevance")) return "relevance";
  if (name.includes("cluster")) return "clusters";
  if (name.includes("slr")) return "sea-level-rise";
  return "unknown";
}

function getDefaultColorScale(layerType: string): string[] {
  const colorScales = {
    risk: ["#ffffff", "#ffff00", "#ffa500", "#ff0000"],
    hazard: ["#add8e6", "#00bfff", "#0000ff", "#00008b"],
    exposition: ["#ffffff", "#90ee90", "#228b22", "#006400"],
    relevance: ["#ffffff", "#ffd700", "#ff8c00", "#ff4500"],
    clusters: ["#ffffff", "#4fc3f7", "#2196f3", "#0d47a1"],
    "sea-level-rise": ["#ffffff", "#81c784", "#4caf50", "#1b5e20"],
    unknown: ["#ffffff", "#ff6b6b", "#e53935", "#b71c1c"],
  };
  return (
    colorScales[layerType as keyof typeof colorScales] || colorScales.unknown
  );
}
