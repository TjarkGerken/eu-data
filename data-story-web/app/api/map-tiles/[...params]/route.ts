import { NextRequest, NextResponse } from "next/server";
import { S3Client, ListObjectsV2Command } from "@aws-sdk/client-s3";
import { R2_CONFIG, R2_BUCKET_NAME, R2_PUBLIC_URL_BASE } from "@/lib/r2-config";
import path from "path";

const s3Client = new S3Client(R2_CONFIG);

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
      return NextResponse.json({ error: "Layer not found" }, { status: 404 });
    }

    // For modern web formats (COG/MBTiles), we redirect to the appropriate service
    // COG files should be served directly via HTTP range requests
    // MBTiles should be served via tile server or extracted tiles

    // Try to get the COG file directly from storage
    const cogFile = await getCogFile(actualFileName);
    if (cogFile) {
      return NextResponse.json(
        {
          error: "COG files should be accessed directly via range requests",
          cogUrl: cogFile,
          recommendation:
            "Use a mapping library like Leaflet with georaster-layer-for-leaflet or OpenLayers with ol-source-geotiff",
        },
        { status: 410 }
      );
    }

    // Check if this is an MBTiles file and redirect to proper tile server
    if (actualFileName.endsWith(".mbtiles") || actualFileName.endsWith(".db")) {
      // For raster MBTiles, we would need to extract and serve the tiles
      // For now, redirect to indicate this should be handled differently
      return NextResponse.json(
        {
          error: "Raster MBTiles should be served via proper tile server",
          fileName: actualFileName,
          layerId: layerName,
          recommendation:
            "Use COG format for raster data or implement MBTiles tile extraction",
          note: "MBTiles file found but raster tile extraction not implemented in this endpoint",
        },
        { status: 501 }
      );
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
    // Get all files from R2 storage
    const command = new ListObjectsV2Command({
      Bucket: R2_BUCKET_NAME,
      Prefix: "map-layers/",
      MaxKeys: 1000,
    });

    const response = await s3Client.send(command);

    if (!response.Contents) {
      return null;
    }

    // Find the file that would generate this layer ID
    for (const object of response.Contents) {
      if (!object.Key) continue;
      const fileName = path.basename(object.Key);
      const generatedLayerId = convertFilenameToLayerId(fileName);
      if (generatedLayerId === layerId) {
        return fileName;
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
  let layerId = fileName.substring(0, fileName.lastIndexOf("."));

  // Remove timestamp prefix if present (from upload process: "1234567890_originalname")
  const timestampMatch = layerId.match(/^\d+_(.+)$/);
  if (timestampMatch) {
    layerId = timestampMatch[1];
  }

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
    if (!fileName.endsWith(".cog") && !fileName.endsWith(".tif")) {
      return null;
    }

    // Construct R2 public URL
    const publicUrl = `${R2_PUBLIC_URL_BASE}/map-layers/${fileName}`;

    // Check if file exists by trying to head it
    try {
      const response = await fetch(publicUrl, { method: "HEAD" });
      if (response.ok) {
        return publicUrl;
      }
    } catch {
      return null;
    }

    return null;
  } catch (error) {
    console.error("Error getting COG file:", error);
    return null;
  }
}
