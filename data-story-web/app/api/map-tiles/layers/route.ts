import { NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";
import path from "path";

export interface MapLayerMetadata {
  id: string;
  name: string;
  dataType: "raster" | "vector";
  format: "tiff" | "geojson" | "geopackage" | "png";
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
  layer: any
): Promise<MapLayerMetadata | null> {
  try {
    const fileName = layer.name;
    const layerId = path.basename(fileName, path.extname(fileName));

    // Determine layer type from filename
    const layerType = determineLayerType(fileName);

    // Determine data type and format based on file extension
    let dataType: "raster" | "vector";
    let format: "tiff" | "geojson" | "geopackage" | "png";

    if (fileName.endsWith(".tif") || fileName.endsWith(".tiff")) {
      dataType = "raster";
      format = "tiff";
    } else if (fileName.endsWith(".png")) {
      // PNG files are typically optimized raster data from GeoTIFF conversion
      dataType = "raster";
      format = "png";
    } else if (fileName.endsWith(".geojson") || fileName.endsWith(".json")) {
      dataType = "vector";
      format = "geojson";
    } else if (fileName.endsWith(".gpkg")) {
      dataType = "vector";
      format = "geopackage";
    } else {
      // Default fallback - try to guess from filename
      if (
        layerType === "risk" ||
        layerType === "hazard" ||
        layerType === "exposition" ||
        layerType === "relevance"
      ) {
        dataType = "raster";
        format = "tiff";
      } else {
        dataType = "vector";
        format = "geopackage";
      }
    }

    return {
      id: layerId,
      name: layerId.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase()),
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

function determineLayerType(fileName: string): string {
  const name = fileName.toLowerCase();
  if (name.includes("risk")) return "risk";
  if (name.includes("hazard")) return "hazard";
  if (name.includes("exposition")) return "exposition";
  if (name.includes("relevance")) return "relevance";
  return "unknown";
}

function getDefaultColorScale(layerType: string): string[] {
  const colorScales = {
    risk: ["#ffffff", "#ffff00", "#ffa500", "#ff0000"],
    hazard: ["#add8e6", "#00bfff", "#0000ff", "#00008b"],
    exposition: ["#ffffff", "#90ee90", "#228b22", "#006400"],
    relevance: ["#ffffff", "#ffd700", "#ff8c00", "#ff4500"],
    unknown: ["#ffffff", "#cccccc", "#666666", "#000000"],
  };
  return (
    colorScales[layerType as keyof typeof colorScales] || colorScales.unknown
  );
}
