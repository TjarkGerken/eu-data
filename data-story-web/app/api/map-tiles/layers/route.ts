import { NextResponse } from "next/server";
import { S3Client, ListObjectsV2Command } from "@aws-sdk/client-s3";
import { R2_CONFIG, R2_BUCKET_NAME } from "@/lib/r2-config";
import path from "path";

const s3Client = new S3Client(R2_CONFIG);

export interface MapLayerMetadata {
  id: string;
  name: string;
  dataType: "raster" | "vector";
  format: "cog" | "mbtiles";
  bounds: [number, number, number, number];
  colorScale: string[];
  valueRange: [number, number];
  uploadedAt: string;
  fileSize: number;
}

export async function GET() {
  try {
    const layers: MapLayerMetadata[] = [];

    // Get layers from R2 storage
    const command = new ListObjectsV2Command({
      Bucket: R2_BUCKET_NAME,
      Prefix: "map-layers/",
      MaxKeys: 1000,
    });

    const response = await s3Client.send(command);

    if (!response.Contents) {
      console.error("No contents found in R2 storage");
      return NextResponse.json({ layers: [] });
    }

    for (const object of response.Contents) {
      if (!object.Key) continue;

      const layerMetadata = await extractLayerMetadata({
        name: path.basename(object.Key),
        created_at: object.LastModified?.toISOString(),
        updated_at: object.LastModified?.toISOString(),
        metadata: { size: object.Size },
      });

      if (layerMetadata) {
        layers.push(layerMetadata);
      }
    }

    return NextResponse.json({ layers });
  } catch (error) {
    console.error("Error listing layers from R2:", error);
    return NextResponse.json(
      { error: "Failed to load layers from R2 storage" },
      { status: 500 }
    );
  }
}

async function extractLayerMetadata(layer: {
  name: string;
  created_at?: string;
  updated_at?: string;
  metadata?: { size?: number };
}): Promise<MapLayerMetadata | null> {
  try {
    const fileName = layer.name;

    let layerId = path.basename(fileName, path.extname(fileName));

    // Remove timestamp prefix if present
    const timestampMatch = layerId.match(/^\d+_(.+)$/);
    if (timestampMatch) {
      layerId = timestampMatch[1];
    }

    // Handle special naming patterns for clusters to create more readable IDs
    if (fileName.includes("clusters_SLR")) {
      const match = fileName.match(/clusters_SLR-(\d+)-(\w+)_(\w+)/);
      if (match) {
        const scenario = match[2].toLowerCase();
        const riskType = match[3].toLowerCase();
        layerId = `clusters-slr-${scenario}-${riskType}`;
      }
    }

    // Determine layer type from filename - be more specific with pattern matching
    const layerType = determineLayerType(fileName);

    // Determine data type and format based on file extension AND content analysis
    let dataType: "raster" | "vector";
    let format: "cog" | "mbtiles";

    if (fileName.endsWith(".cog") || fileName.endsWith(".tif")) {
      dataType = "raster";
      format = "cog";
    } else if (fileName.endsWith(".mbtiles")) {
      // For MBTiles, determine type based on MORE SPECIFIC filename patterns
      // Priority order: clusters > specific layer types
      if (
        fileName.startsWith("clusters_") ||
        fileName.includes("clusters_SLR")
      ) {
        dataType = "vector";
        format = "mbtiles";
      } else if (
        fileName.startsWith("risk_") ||
        fileName.startsWith("hazard_") ||
        fileName.startsWith("exposition_") ||
        fileName.startsWith("relevance_")
      ) {
        dataType = "raster";
        format = "mbtiles";
      } else {
        // For ambiguous cases, decide based on layerType
        if (layerType === "clusters" || layerType === "nuts") {
          dataType = "vector";
          format = "mbtiles";
        } else {
          dataType = "raster";
          format = "mbtiles";
        }
      }
    } else {
      // Skip unsupported file types
      return null;
    }

    const metadata = {
      id: layerId,
      name: formatDisplayName(layerId),
      dataType,
      format,
      bounds: getDefaultBounds(layerType),
      colorScale: getDefaultColorScale(layerType),
      valueRange: getDefaultValueRange(layerType),
      uploadedAt:
        layer.created_at || layer.updated_at || new Date().toISOString(),
      fileSize: layer.metadata?.size || 0,
    };

    return metadata;
  } catch (error) {
    console.error("Error extracting layer metadata:", error);
    return null;
  }
}

function formatDisplayName(layerId: string): string {
  // Create a more readable display name
  return layerId
    .replace(/_/g, " ") // Replace underscores with spaces
    .replace(/-/g, " ") // Replace hyphens with spaces
    .replace(/\b\w/g, (l) => l.toUpperCase()) // Capitalize first letter of each word
    .replace(/\bSlr\b/g, "SLR") // Fix SLR capitalization
    .replace(/\bGdp\b/g, "GDP") // Fix GDP capitalization
    .replace(/\bHrst\b/g, "HRST") // Fix HRST capitalization
    .trim();
}

function determineLayerType(fileName: string): string {
  const name = fileName.toLowerCase();

  // Priority order: check for clusters first to avoid false matches
  if (name.includes("cluster") || name.includes("clusters_slr"))
    return "clusters";
  if (name.startsWith("risk_") || name.includes("_risk_")) return "risk";
  if (name.startsWith("hazard_") || name.includes("_hazard_")) return "hazard";
  if (name.startsWith("exposition_") || name.includes("_exposition_"))
    return "exposition";
  if (name.startsWith("relevance_") || name.includes("_relevance_"))
    return "relevance";
  if (name.includes("slr")) return "sea-level-rise";
  if (name.startsWith("nuts") || name.includes("_nuts")) return "nuts";

  console.log(
    `Could not determine specific layer type for: ${fileName}, defaulting to unknown`
  );
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
    nuts: ["#ffffff", "#4fc3f7", "#2196f3", "#0d47a1"],
    unknown: ["#ffffff", "#ff6b6b", "#e53935", "#b71c1c"],
  };
  return (
    colorScales[layerType as keyof typeof colorScales] || colorScales.unknown
  );
}

function getDefaultBounds(layerType: string): [number, number, number, number] {
  // Default bounds for EU region
  const euBounds: [number, number, number, number] = [3.5, 51.2, 7.2, 53.5];

  const bounds = {
    risk: euBounds,
    hazard: euBounds,
    exposition: euBounds,
    relevance: euBounds,
    clusters: euBounds,
    "sea-level-rise": euBounds,
    nuts: euBounds,
    unknown: [-180, -90, 180, 90] as [number, number, number, number],
  };

  return bounds[layerType as keyof typeof bounds] || bounds.unknown;
}

function getDefaultValueRange(layerType: string): [number, number] {
  const valueRanges = {
    risk: [0, 1] as [number, number],
    hazard: [0, 1] as [number, number],
    exposition: [0, 100] as [number, number],
    relevance: [0, 100] as [number, number],
    clusters: [0, 500] as [number, number],
    "sea-level-rise": [0, 3] as [number, number],
    nuts: [0, 500] as [number, number],
    unknown: [0, 100] as [number, number],
  };

  return (
    valueRanges[layerType as keyof typeof valueRanges] || valueRanges.unknown
  );
}
