import { NextRequest, NextResponse } from "next/server";
import {
  GetObjectCommand,
  ListObjectsV2Command,
  S3Client,
} from "@aws-sdk/client-s3";
import { R2_CONFIG, R2_BUCKET_NAME } from "@/lib/r2-config";
import path from "path";
import Database from "better-sqlite3";
import { writeFileSync, unlinkSync } from "fs";
import { tmpdir } from "os";
import { join } from "path";

// Create S3 client with R2 config
const s3Client = new S3Client(R2_CONFIG);

export async function GET(
  request: NextRequest,
  {
    params,
  }: { params: Promise<{ layerId: string; z: string; x: string; y: string }> }
) {
  try {
    const resolvedParams = await params;
    const { layerId, z, x, y } = resolvedParams;

    // Remove any common vector-tile extensions from Y (e.g. .mvt, .pbf)
    const cleanedY = y.replace(/\.(mvt|pbf|json)$/i, "");

    const zoom = parseInt(z);
    const tileX = parseInt(x);
    const tileY = parseInt(cleanedY);

    if (isNaN(zoom) || isNaN(tileX) || isNaN(tileY)) {
      return NextResponse.json(
        { error: "Invalid tile coordinates" },
        { status: 400 }
      );
    }

    // Find the MBTiles file for this layer
    const actualFileName = await findFileByLayerId(layerId);

    if (!actualFileName) {
      return NextResponse.json(
        { error: `Layer ${layerId} not found` },
        { status: 404 }
      );
    }

    // Get the MBTiles file from R2
    const command = new GetObjectCommand({
      Bucket: R2_BUCKET_NAME,
      Key: `map-layers/${actualFileName}`,
    });

    const response = await s3Client.send(command);

    if (!response.Body) {
      return NextResponse.json(
        { error: `MBTiles file not found` },
        { status: 404 }
      );
    }

    // Convert to buffer
    const arrayBuffer = await response.Body.transformToByteArray();
    const buffer = Buffer.from(arrayBuffer);

    // Get the tile from MBTiles
    const tileData = await getTileFromMBTiles(buffer, zoom, tileX, tileY);

    if (!tileData) {
      return NextResponse.json(
        { error: `Tile not found: ${z}/${x}/${y}` },
        { status: 404 }
      );
    }

    const headers: Record<string, string> = {
      "Content-Type": "application/x-protobuf",
      "Cache-Control": "public, max-age=31536000",
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET",
      "Access-Control-Allow-Headers": "*",
    };

    // Add Content-Encoding header only if data starts with gzip magic bytes
    if (tileData.length >= 2 && tileData[0] === 0x1f && tileData[1] === 0x8b) {
      headers["Content-Encoding"] = "gzip";
    }

    return new NextResponse(tileData, {
      headers,
    });
  } catch (error) {
    console.error("Error serving vector tile:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

async function findFileByLayerId(layerId: string): Promise<string | null> {
  try {
    const command = new ListObjectsV2Command({
      Bucket: R2_BUCKET_NAME,
      Prefix: "map-layers/",
      MaxKeys: 1000,
    });

    const response = await s3Client.send(command);

    if (!response.Contents) {
      return null;
    }

    for (const object of response.Contents) {
      if (!object.Key) continue;
      const fileName = path.basename(object.Key);
      const generatedLayerId = convertFilenameToLayerId(fileName);

      if (generatedLayerId === layerId && fileName.endsWith(".mbtiles")) {
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
  let layerId = fileName.substring(0, fileName.lastIndexOf("."));

  // Remove timestamp prefix if present
  const timestampMatch = layerId.match(/^\d+_(.+)$/);
  if (timestampMatch) {
    layerId = timestampMatch[1];
  }

  // Handle clusters_SLR pattern
  if (layerId.includes("clusters_SLR")) {
    const match = layerId.match(/clusters_SLR-(\d+)-(\w+)_(\w+)/);
    if (match) {
      const scenario = match[2].toLowerCase();
      const riskType = match[3].toLowerCase();
      layerId = `clusters-slr-${scenario}-${riskType}`;
    }
  }

  return layerId;
}

async function getTileFromMBTiles(
  mbtileBuffer: Buffer,
  zoom: number,
  x: number,
  y: number
): Promise<Buffer | null> {
  let tempFilePath: string | null = null;

  try {
    tempFilePath = join(
      tmpdir(),
      `temp_${Date.now()}_${zoom}_${x}_${y}.mbtiles`
    );
    writeFileSync(tempFilePath, mbtileBuffer);

    const db = new Database(tempFilePath, { readonly: true });

    // Convert Y coordinate from XYZ to TMS (flip Y axis)
    const tmsY = Math.pow(2, zoom) - 1 - y;

    // Try different query patterns for tiles
    const queries = [
      "SELECT tile_data FROM tiles WHERE zoom_level = ? AND tile_column = ? AND tile_row = ?",
      "SELECT tile_data FROM map WHERE zoom_level = ? AND tile_column = ? AND tile_row = ?",
    ];

    for (const query of queries) {
      try {
        const stmt = db.prepare(query);
        const row = stmt.get(zoom, x, tmsY) as
          | { tile_data: Buffer }
          | undefined;

        if (row && row.tile_data) {
          return row.tile_data;
        }
      } catch {
        // Try next query
        continue;
      }
    }

    db.close();
    return null;
  } catch {
    return null;
  } finally {
    if (tempFilePath) {
      try {
        unlinkSync(tempFilePath);
      } catch {
        // Ignore cleanup errors
      }
    }
  }
}
