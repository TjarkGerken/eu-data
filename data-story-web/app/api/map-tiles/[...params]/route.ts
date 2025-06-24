import { NextRequest, NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ params: string[] }> }
) {
  try {
    const resolvedParams = await params;

    if (!resolvedParams.params || resolvedParams.params.length < 4) {
      return NextResponse.json(
        { error: "Invalid tile request" },
        { status: 400 }
      );
    }

    const [layerName, zoomStr, xStr, yStr] = resolvedParams.params;
    const zoom = parseInt(zoomStr);
    const x = parseInt(xStr);
    const y = parseInt(yStr.replace(".png", ""));

    if (isNaN(zoom) || isNaN(x) || isNaN(y)) {
      return NextResponse.json(
        { error: "Invalid coordinates" },
        { status: 400 }
      );
    }

    // Find the actual filename for this layer ID
    const actualFileName = await findFileByLayerId(layerName);
    
    if (!actualFileName) {
      return NextResponse.json(
        { error: "Layer not found" },
        { status: 404 }
      );
    }

    // For modern web formats (COG/MBTiles), we redirect to the appropriate service
    // COG files should be served directly via HTTP range requests
    // MBTiles should be served via tile server or extracted tiles
    
    // Try to get the COG file directly from storage
    const cogFile = await getCogFile(actualFileName);
    if (cogFile) {
      return NextResponse.json({
        error: "COG files should be accessed directly via range requests",
        cogUrl: cogFile,
        recommendation: "Use a mapping library like Leaflet with georaster-layer-for-leaflet or OpenLayers with ol-source-geotiff"
      }, { status: 410 });
    }

    // Check if this is an MBTiles file and return appropriate response
    if (actualFileName.endsWith('.mbtiles') || actualFileName.endsWith('.db')) {
      return NextResponse.json({
        error: "MBTiles tile serving not fully implemented",
        fileName: actualFileName,
        recommendation: "Use a proper vector tile server like TileServer GL",
        note: "MBTiles file found but tile extraction not implemented"
      }, { status: 501 });
    }

    return NextResponse.json(
      { error: "Layer not found or not in supported format (COG/MBTiles)" },
      { status: 404 }
    );

  } catch (error) {
    console.error("Error serving tile:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

async function findFileByLayerId(layerId: string): Promise<string | null> {
  try {
    // Get all files from storage
    const { data: files, error } = await supabase.storage
      .from("map-layers")
      .list();

    if (error || !files) {
      return null;
    }

    // Find the file that would generate this layer ID
    for (const file of files) {
      const generatedLayerId = convertFilenameToLayerId(file.name);
      if (generatedLayerId === layerId) {
        return file.name;
      }
    }

    return null;
  } catch (error) {
    console.error("Error finding file by layer ID:", error);
    return null;
  }
}

function convertFilenameToLayerId(fileName: string): string {
  // Remove extension
  let layerId = fileName.substring(0, fileName.lastIndexOf('.'));
  
  // Handle special naming patterns for clusters to create more readable IDs
  if (fileName.includes("clusters_SLR")) {
    // Extract scenario and risk type from filename like "123456_clusters_SLR-0-Current_GDP.mbtiles"
    const match = fileName.match(/clusters_SLR-(\d+)-(\w+)_(\w+)/);
    if (match) {
      const scenario = match[2].toLowerCase(); // "current", "severe", etc.
      const riskType = match[3].toLowerCase(); // "gdp", "population", "freight", etc.
      layerId = `clusters-slr-${scenario}-${riskType}`;
    }
  }
  
  return layerId;
}

async function getCogFile(fileName: string): Promise<string | null> {
  try {
    if (!fileName.endsWith('.cog') && !fileName.endsWith('.tif')) {
      return null;
    }

    const { data } = supabase.storage
      .from("map-layers")
      .getPublicUrl(fileName);
    
    if (data?.publicUrl) {
      // Check if file exists by trying to head it
      try {
        const response = await fetch(data.publicUrl, { method: 'HEAD' });
        if (response.ok) {
          return data.publicUrl;
        }
      } catch {
        return null;
      }
    }
    return null;
  } catch (error) {
    console.error("Error getting COG file:", error);
    return null;
  }
}

async function getMBTilesTile(fileName: string, zoom: number, x: number, y: number): Promise<Buffer | null> {
  try {
    if (!fileName.endsWith('.mbtiles') && !fileName.endsWith('.db')) {
      return null;
    }

    const { data, error } = await supabase.storage
      .from("map-layers")
      .download(fileName);

    if (!error && data) {
      // For now, return a placeholder response
      // In a production setup, you'd want to use a proper MBTiles reader
      console.log(`MBTiles tile requested: ${fileName}/${zoom}/${x}/${y}`);
      console.warn("MBTiles tile extraction not implemented. Use a dedicated tile server like TileServer GL.");
      return null;
    }
    return null;
  } catch (error) {
    console.error("Error getting MBTiles tile:", error);
    return null;
  }
}
