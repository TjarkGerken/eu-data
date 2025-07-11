/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars */

import { NextRequest, NextResponse } from "next/server";
import {
  S3Client,
  ListObjectsV2Command,
  GetObjectCommand,
} from "@aws-sdk/client-s3";
import { R2_CONFIG, R2_BUCKET_NAME } from "@/lib/r2-config";
import path from "path";
import Database from "better-sqlite3";
import { writeFileSync, unlinkSync } from "fs";
import { tmpdir } from "os";
import { join } from "path";

const s3Client = new S3Client(R2_CONFIG);

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ layerId: string }> },
) {
  try {
    const resolvedParams = await params;
    const { layerId } = resolvedParams;

    // Find the actual filename for this layer ID
    const actualFileName = await findFileByLayerId(layerId);

    if (!actualFileName) {
      return NextResponse.json({ error: "Layer not found" }, { status: 404 });
    }

    // Get the MBTiles file from R2
    const command = new GetObjectCommand({
      Bucket: R2_BUCKET_NAME,
      Key: `map-layers/${actualFileName}`,
    });

    const response = await s3Client.send(command);

    if (!response.Body) {
      return NextResponse.json(
        { error: "MBTiles file not found in storage" },
        { status: 404 },
      );
    }

    // Convert to buffer
    const arrayBuffer = await response.Body.transformToByteArray();
    const buffer = Buffer.from(arrayBuffer);

    // Analyze the MBTiles file
    const analysis = await analyzeMBTiles(buffer, layerId, actualFileName);

    return NextResponse.json(analysis);
  } catch (error) {
    console.error("Error analyzing MBTiles:", error);
    return NextResponse.json(
      { error: "Failed to analyze MBTiles file" },
      { status: 500 },
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
  let layerId = fileName.substring(0, fileName.lastIndexOf("."));

  const timestampMatch = layerId.match(/^\d+_(.+)$/);
  if (timestampMatch) {
    layerId = timestampMatch[1];
  }

  if (fileName.includes("clusters_SLR")) {
    const match = fileName.match(/clusters_SLR-(\d+)-(\w+)_(\w+)/);
    if (match) {
      const scenario = match[2].toLowerCase();
      const riskType = match[3].toLowerCase();
      layerId = `clusters-slr-${scenario}-${riskType}`;
    }
  }

  return layerId;
}

async function analyzeMBTiles(
  mbtileBuffer: Buffer,
  layerId: string,
  fileName: string,
): Promise<any> {
  let tempFilePath: string | null = null;
  let db: Database.Database | null = null;

  try {
    tempFilePath = join(tmpdir(), `debug_${Date.now()}.mbtiles`);
    writeFileSync(tempFilePath, mbtileBuffer);

    db = new Database(tempFilePath, { readonly: true });

    // Get metadata
    const metadata: Record<string, string> = {};
    try {
      const metadataStmt = db.prepare("SELECT name, value FROM metadata");
      const metadataRows = metadataStmt.all() as Array<{
        name: string;
        value: string;
      }>;

      for (const row of metadataRows) {
        metadata[row.name] = row.value;
      }
    } catch (error) {
      console.warn("Could not read metadata:", error);
    }

    // Get schema information
    const tables = db
      .prepare("SELECT name FROM sqlite_master WHERE type='table'")
      .all() as Array<{ name: string }>;

    // Get tile statistics
    let tileStats: any = {};

    // Try tiles table first
    try {
      const totalTilesStmt = db.prepare("SELECT COUNT(*) as count FROM tiles");
      const totalTiles = totalTilesStmt.get() as { count: number };

      const zoomStatsStmt = db.prepare(`
        SELECT 
          zoom_level,
          COUNT(*) as tile_count,
          MIN(tile_column) as min_x,
          MAX(tile_column) as max_x,
          MIN(tile_row) as min_y,
          MAX(tile_row) as max_y
        FROM tiles 
        GROUP BY zoom_level 
        ORDER BY zoom_level
      `);
      const zoomStats = zoomStatsStmt.all() as Array<{
        zoom_level: number;
        tile_count: number;
        min_x: number;
        max_x: number;
        min_y: number;
        max_y: number;
      }>;

      tileStats = {
        total_tiles: totalTiles.count,
        zoom_levels: zoomStats.map((z) => z.zoom_level),
        zoom_distribution: Object.fromEntries(
          zoomStats.map((z) => [z.zoom_level, z.tile_count]),
        ),
        tile_bounds_by_zoom: Object.fromEntries(
          zoomStats.map((z) => [
            z.zoom_level,
            {
              min_x: z.min_x,
              max_x: z.max_x,
              min_y: z.min_y,
              max_y: z.max_y,
            },
          ]),
        ),
      };
    } catch (error) {
      // Try map table as fallback
      try {
        const totalTilesStmt = db.prepare("SELECT COUNT(*) as count FROM map");
        const totalTiles = totalTilesStmt.get() as { count: number };
        tileStats.total_tiles = totalTiles.count;
        tileStats.schema = "map_table";
      } catch {
        tileStats.error =
          "Could not read tile data from either tiles or map table";
      }
    }

    // Sample a few tiles to check their format
    let sampleTiles: any[] = [];
    try {
      const sampleStmt = db.prepare(`
        SELECT zoom_level, tile_column, tile_row, length(tile_data) as size 
        FROM tiles 
        LIMIT 5
      `);
      sampleTiles = sampleStmt.all() as Array<{
        zoom_level: number;
        tile_column: number;
        tile_row: number;
        size: number;
      }>;
    } catch {
      // Try map table
      try {
        const sampleStmt = db.prepare(`
          SELECT zoom_level, tile_column, tile_row, length(tile_data) as size 
          FROM map 
          LIMIT 5
        `);
        sampleTiles = sampleStmt.all() as Array<{
          zoom_level: number;
          tile_column: number;
          tile_row: number;
          size: number;
        }>;
      } catch {
        sampleTiles = [];
      }
    }

    return {
      layer_id: layerId,
      file_name: fileName,
      file_size_mb: (mbtileBuffer.length / (1024 * 1024)).toFixed(2),
      metadata,
      database_schema: {
        tables: tables.map((t) => t.name),
      },
      tile_statistics: tileStats,
      sample_tiles: sampleTiles,
      bounds_analysis: analyzeBounds(metadata),
      recommendations: generateRecommendations(metadata, tileStats),
    };
  } catch (error) {
    console.error("Error analyzing MBTiles:", error);
    throw error;
  } finally {
    if (db) {
      try {
        db.close();
      } catch (error) {
        console.warn("Error closing database:", error);
      }
    }

    if (tempFilePath) {
      try {
        unlinkSync(tempFilePath);
      } catch {
        // Ignore cleanup errors
      }
    }
  }
}

function analyzeBounds(metadata: Record<string, string>) {
  if (!metadata.bounds) {
    return {
      status: "no_bounds",
      message: "No bounds found in metadata",
    };
  }

  try {
    const bounds = metadata.bounds.split(",").map(Number);
    const [west, south, east, north] = bounds;

    // Check if bounds look like they cover the Netherlands
    const netherlandsBounds = [3.36, 50.75, 7.23, 53.56]; // Approximate NL bounds
    const [nlWest, nlSouth, nlEast, nlNorth] = netherlandsBounds;

    const boundsValid =
      west >= nlWest - 1 &&
      east <= nlEast + 1 &&
      south >= nlSouth - 1 &&
      north <= nlNorth + 1;

    return {
      status: boundsValid ? "valid" : "suspicious",
      bounds: {
        west,
        south,
        east,
        north,
        width: east - west,
        height: north - south,
      },
      comparison_to_netherlands: {
        overlaps: !(
          east < nlWest ||
          west > nlEast ||
          north < nlSouth ||
          south > nlNorth
        ),
        contains_netherlands:
          west <= nlWest &&
          east >= nlEast &&
          south <= nlSouth &&
          north >= nlNorth,
      },
      message: boundsValid
        ? "Bounds appear valid for Netherlands data"
        : "Bounds may be too broad or incorrect",
    };
  } catch (error) {
    return {
      status: "invalid",
      message: `Error parsing bounds: ${error}`,
    };
  }
}

function generateRecommendations(
  metadata: Record<string, string>,
  tileStats: any,
) {
  const recommendations: string[] = [];

  if (tileStats.total_tiles < 100) {
    recommendations.push(
      "Very low tile count suggests incomplete MBTiles generation",
    );
  }

  if (metadata.bounds === "-15,30,35,75") {
    recommendations.push(
      "Bounds are set to default European extent - should be updated to actual data bounds",
    );
  }

  const maxZoom = parseInt(metadata.maxzoom || "12");
  if (maxZoom < 12) {
    recommendations.push(
      "Maximum zoom level is quite low for detailed visualization",
    );
  }

  if (tileStats.zoom_levels && Math.max(...tileStats.zoom_levels) < 10) {
    recommendations.push(
      "No high-resolution tiles available - may appear blurry at high zoom",
    );
  }

  if (!tileStats.zoom_levels || tileStats.zoom_levels.length < 6) {
    recommendations.push(
      "Limited zoom level coverage may cause display issues",
    );
  }

  return recommendations;
}
