import { NextRequest, NextResponse } from "next/server";
import {
  S3Client,
  ListObjectsV2Command,
  GetObjectCommand,
} from "@aws-sdk/client-s3";
import { R2_CONFIG, R2_BUCKET_NAME } from "@/lib/r2-config";
import path from "path";

const s3Client = new S3Client(R2_CONFIG);

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ layerId: string }> },
) {
  try {
    const resolvedParams = await params;
    const { layerId } = resolvedParams;

    if (!layerId) {
      return NextResponse.json(
        { error: "Layer ID is required" },
        { status: 400 },
      );
    }

    // Find the actual filename in storage that corresponds to this layer ID
    const actualFileName = await findFileByLayerId(layerId);

    if (!actualFileName) {
      return NextResponse.json(
        { error: `Layer ${layerId} not found for download` },
        { status: 404 },
      );
    }

    try {
      const command = new GetObjectCommand({
        Bucket: R2_BUCKET_NAME,
        Key: `map-layers/${actualFileName}`,
      });

      const response = await s3Client.send(command);

      if (!response.Body) {
        return NextResponse.json(
          { error: `Layer ${layerId} not found for download` },
          { status: 404 },
        );
      }

      const fileBuffer = await response.Body.transformToByteArray();
      const extension = actualFileName.substring(
        actualFileName.lastIndexOf("."),
      );
      const contentType = getContentType(extension);

      return new NextResponse(fileBuffer, {
        headers: {
          "Content-Type": contentType,
          "Content-Disposition": `attachment; filename="${actualFileName}"`,
          "Cache-Control": "public, max-age=3600",
        },
      });
    } catch (downloadError) {
      console.error(`Could not download ${actualFileName}:`, downloadError);
      return NextResponse.json(
        { error: `Layer ${layerId} not found for download` },
        { status: 404 },
      );
    }
  } catch (error) {
    console.error("Error downloading layer:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 },
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
  let layerId = path.basename(fileName, path.extname(fileName));

  // Remove timestamp prefix if present (from upload process: "1234567890_originalname")
  const timestampMatch = layerId.match(/^\d+_(.+)$/);
  if (timestampMatch) {
    layerId = timestampMatch[1];
  }

  // Handle special naming patterns for clusters to create more readable IDs
  if (fileName.includes("clusters_SLR")) {
    // Extract scenario and risk type from filename like "clusters_SLR-0-Current_GDP.mbtiles"
    const match = fileName.match(/clusters_SLR-(\d+)-(\w+)_(\w+)/);
    if (match) {
      const scenario = match[2].toLowerCase(); // "current", "severe", etc.
      const riskType = match[3].toLowerCase(); // "gdp", "population", "freight", etc.
      layerId = `clusters-slr-${scenario}-${riskType}`;
    }
  }

  return layerId;
}

function getContentType(extension: string): string {
  const contentTypes: Record<string, string> = {
    ".cog": "image/tiff",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".mbtiles": "application/vnd.mapbox-vector-tile",
    ".gpkg": "application/geopackage+sqlite3",
    ".geojson": "application/geo+json",
  };

  return contentTypes[extension.toLowerCase()] || "application/octet-stream";
}
