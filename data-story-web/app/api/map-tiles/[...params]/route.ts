/* eslint-disable prefer-const */

import { NextRequest, NextResponse } from "next/server";
import {
  S3Client,
  ListObjectsV2Command,
  GetObjectCommand,
} from "@aws-sdk/client-s3";
import { R2_CONFIG, R2_BUCKET_NAME, R2_PUBLIC_URL_BASE } from "@/lib/r2-config";
import path from "path";
import Database from "better-sqlite3";
import { writeFileSync, unlinkSync } from "fs";
import { tmpdir } from "os";
import { join } from "path";

const s3Client = new S3Client(R2_CONFIG);

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ params: string[] }> },
) {
  try {
    const resolvedParams = await params;

    if (!resolvedParams.params || resolvedParams.params.length < 4) {
      return NextResponse.json(
        { error: "Invalid tile request" },
        { status: 400 },
      );
    }

    const [layerName, zoomStr, xStr, yStr] = resolvedParams.params;
    const zoom = parseInt(zoomStr);
    const x = parseInt(xStr);

    // Extract requested format from the URL
    const formatMatch = yStr.match(/\.(png|jpg|jpeg|webp|mvt|pbf)$/i);
    const requestedFormat = formatMatch ? formatMatch[1].toLowerCase() : null;
    const y = parseInt(yStr.replace(/\.(png|jpg|jpeg|webp|mvt|pbf)$/i, ""));

    if (isNaN(zoom) || isNaN(x) || isNaN(y)) {
      return NextResponse.json(
        { error: "Invalid coordinates" },
        { status: 400 },
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
        { status: 410 },
      );
    }

    // Check if this is an MBTiles file and extract tiles
    if (actualFileName.endsWith(".mbtiles") || actualFileName.endsWith(".db")) {
      try {
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

        // Get MBTiles metadata to understand tile format
        const metadata = await getMBTilesMetadata(buffer);

        // Check for format mismatch: requesting image format for vector layer
        const isVectorLayer =
          metadata?.format === "pbf" || metadata?.format === "mvt";
        const isImageFormatRequested =
          requestedFormat &&
          ["png", "jpg", "jpeg", "webp"].includes(requestedFormat);

        if (isVectorLayer && isImageFormatRequested) {
          return NextResponse.json(
            {
              error: "Format mismatch",
              message: `Layer '${layerName}' contains vector tiles (${metadata.format}) but you requested ${requestedFormat} format`,
              correct_usage: {
                vector_tile_url: `/api/map-tiles/${layerName}/${zoom}/${x}/${y}`,
                protobuf_url: `/api/map-tiles/${layerName}/${zoom}/${x}/${y}.mvt`,
                format: metadata.format,
                content_type: "application/x-protobuf",
              },
              suggestion:
                "Use a mapping library like Leaflet with VectorGrid plugin to display vector tiles",
              debug_info: `/api/map-tiles/debug/${layerName}`,
            },
            {
              status: 400,
              headers: {
                "Content-Type": "application/json",
                "X-Layer-Format": metadata.format || "unknown",
                "X-Layer-Type": "vector",
              },
            },
          );
        }

        // Extract tile from MBTiles with fallback to lower zoom levels
        let tileData = await getTileFromMBTiles(buffer, zoom, x, y);
        let actualZoom = zoom;

        // If tile not found at requested zoom, try lower zoom levels down to 6
        if (!tileData && zoom > 6) {
          console.log(
            `Tile not found at zoom ${zoom}, trying lower zoom levels...`,
          );

          for (let fallbackZoom = zoom - 1; fallbackZoom >= 6; fallbackZoom--) {
            // Calculate parent tile coordinates
            const parentX = Math.floor(x / Math.pow(2, zoom - fallbackZoom));
            const parentY = Math.floor(y / Math.pow(2, zoom - fallbackZoom));

            tileData = await getTileFromMBTiles(
              buffer,
              fallbackZoom,
              parentX,
              parentY,
            );
            if (tileData) {
              actualZoom = fallbackZoom;
              console.log(
                `Found tile at fallback zoom ${fallbackZoom} (${parentX}/${parentY})`,
              );
              break;
            }
          }
        }

        if (!tileData) {
          return NextResponse.json(
            {
              error: `Tile not found: ${zoom}/${x}/${y}`,
              details: `No tile available at requested coordinates or fallback zoom levels (6-${zoom})`,
              suggestion:
                "This layer may have limited zoom coverage or incorrect bounds",
            },
            { status: 404 },
          );
        }

        // Determine content type based on tile data and metadata
        const contentType = detectTileContentType(tileData, metadata);

        const headers: Record<string, string> = {
          "Content-Type": contentType,
          "Cache-Control": "public, max-age=31536000",
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET",
          "Access-Control-Allow-Headers": "*",
        };

        // Add header if we served a fallback tile
        if (actualZoom !== zoom) {
          headers["X-Tile-Fallback"] = `${actualZoom}`;
          headers["X-Tile-Requested"] = `${zoom}`;
        }

        // Add header to indicate tile format from metadata
        if (metadata?.format) {
          headers["X-Tile-Format"] = metadata.format;
        }

        // Add helpful header for vector tiles
        if (contentType === "application/x-protobuf") {
          headers["X-Tile-Type"] = "vector";
          headers["X-Tile-Info"] =
            "This is a vector tile (protobuf/MVT format), not a raster image";
        } else if (contentType.startsWith("image/")) {
          headers["X-Tile-Type"] = "raster";
        }

        return new NextResponse(tileData, { headers });
      } catch (error) {
        console.error("Error extracting tile from MBTiles:", error);
        return NextResponse.json(
          { error: "Failed to extract tile from MBTiles" },
          { status: 500 },
        );
      }
    }

    return NextResponse.json(
      { error: "Layer not found or not in supported format (COG/MBTiles)" },
      { status: 404 },
    );
  } catch (error) {
    console.error("Error serving tile:", error);
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

async function getMBTilesMetadata(
  mbtileBuffer: Buffer,
): Promise<Record<string, string>> {
  let tempFilePath: string | null = null;
  let db: Database.Database | null = null;

  try {
    tempFilePath = join(tmpdir(), `metadata_${Date.now()}.mbtiles`);
    writeFileSync(tempFilePath, mbtileBuffer);

    db = new Database(tempFilePath, { readonly: true });

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
      console.warn("Could not read MBTiles metadata:", error);
    }

    return metadata;
  } catch (error) {
    console.error("Error reading MBTiles metadata:", error);
    return {};
  } finally {
    if (db) {
      try {
        db.close();
      } catch (error) {
        console.warn("Error closing metadata database:", error);
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

async function getTileFromMBTiles(
  mbtileBuffer: Buffer,
  zoom: number,
  x: number,
  y: number,
): Promise<Buffer | null> {
  let tempFilePath: string | null = null;
  let db: Database.Database | null = null;

  try {
    tempFilePath = join(
      tmpdir(),
      `temp_${Date.now()}_${zoom}_${x}_${y}.mbtiles`,
    );
    writeFileSync(tempFilePath, mbtileBuffer);

    db = new Database(tempFilePath, { readonly: true });

    // First, get metadata to understand the MBTiles structure
    let metadata: Record<string, string> = {};
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
      console.warn("Could not read MBTiles metadata:", error);
    }

    // Check zoom level bounds
    const minZoom = parseInt(metadata.minzoom || "0");
    const maxZoom = parseInt(metadata.maxzoom || "18");

    if (zoom < minZoom || zoom > maxZoom) {
      console.log(`Zoom ${zoom} outside available range ${minZoom}-${maxZoom}`);
      return null;
    }

    // Check if we have bounds and validate coordinates
    if (metadata.bounds) {
      const bounds = metadata.bounds.split(",").map(Number);
      const [west, south, east, north] = bounds;

      // Convert tile coordinates to geographic bounds
      const tileWest = (x / Math.pow(2, zoom)) * 360 - 180;
      const tileEast = ((x + 1) / Math.pow(2, zoom)) * 360 - 180;
      const n = Math.PI - (2 * Math.PI * y) / Math.pow(2, zoom);
      const tileNorth =
        (180 / Math.PI) * Math.atan(0.5 * (Math.exp(n) - Math.exp(-n)));
      const n2 = Math.PI - (2 * Math.PI * (y + 1)) / Math.pow(2, zoom);
      const tileSouth =
        (180 / Math.PI) * Math.atan(0.5 * (Math.exp(n2) - Math.exp(-n2)));

      // Check if tile overlaps with layer bounds
      if (
        tileEast < west ||
        tileWest > east ||
        tileNorth < south ||
        tileSouth > north
      ) {
        console.log(`Tile ${zoom}/${x}/${y} outside layer bounds`);
        return null;
      }
    }

    // Convert Y coordinate from XYZ to TMS (flip Y axis)
    const tmsY = Math.pow(2, zoom) - 1 - y;

    // Try different query patterns for tiles
    const queries = [
      // Standard MBTiles schema
      "SELECT tile_data FROM tiles WHERE zoom_level = ? AND tile_column = ? AND tile_row = ?",
      // Alternative schema
      "SELECT tile_data FROM map WHERE zoom_level = ? AND tile_column = ? AND tile_row = ?",
      // Try without TMS conversion (in case tiles are stored in XYZ format)
      "SELECT tile_data FROM tiles WHERE zoom_level = ? AND tile_column = ? AND tile_row = ?",
      "SELECT tile_data FROM map WHERE zoom_level = ? AND tile_column = ? AND tile_row = ?",
    ];

    const coordinates = [
      [zoom, x, tmsY], // TMS format
      [zoom, x, tmsY], // TMS format (map table)
      [zoom, x, y], // XYZ format
      [zoom, x, y], // XYZ format (map table)
    ];

    for (let i = 0; i < queries.length; i++) {
      try {
        const stmt = db.prepare(queries[i]);
        const [z, tx, ty] = coordinates[i];
        const row = stmt.get(z, tx, ty) as { tile_data: Buffer } | undefined;

        if (row && row.tile_data) {
          console.log(
            `Found tile ${zoom}/${x}/${y} using query ${
              i + 1
            } with coordinates ${z}/${tx}/${ty}`,
          );
          return row.tile_data;
        }
      } catch (error) {
        console.warn(`Query ${i + 1} failed:`, error);
        continue;
      }
    }

    // If no tile found, check if any tiles exist at this zoom level
    try {
      const zoomCheckStmt = db.prepare(
        "SELECT COUNT(*) as count FROM tiles WHERE zoom_level = ?",
      );
      const zoomCount = zoomCheckStmt.get(zoom) as
        | { count: number }
        | undefined;
      console.log(`Tiles available at zoom ${zoom}: ${zoomCount?.count || 0}`);
    } catch (error) {
      console.warn("Could not check zoom level availability:", error);
    }

    return null;
  } catch (error) {
    console.error("Error extracting tile from MBTiles:", error);
    return null;
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

function detectTileContentType(
  tileData: Buffer,
  metadata?: Record<string, string>,
): string {
  // First check metadata format if available
  if (metadata?.format) {
    switch (metadata.format.toLowerCase()) {
      case "pbf":
      case "mvt":
        return "application/x-protobuf";
      case "png":
        return "image/png";
      case "jpg":
      case "jpeg":
        return "image/jpeg";
      case "webp":
        return "image/webp";
    }
  }

  // Fallback to magic bytes detection
  if (tileData.length >= 8) {
    // PNG magic bytes: 89 50 4E 47
    if (
      tileData[0] === 0x89 &&
      tileData[1] === 0x50 &&
      tileData[2] === 0x4e &&
      tileData[3] === 0x47
    ) {
      return "image/png";
    }

    // JPEG magic bytes: FF D8
    if (tileData[0] === 0xff && tileData[1] === 0xd8) {
      return "image/jpeg";
    }

    // WebP magic bytes: RIFF ... WEBP
    if (
      tileData[0] === 0x52 && // R
      tileData[1] === 0x49 && // I
      tileData[2] === 0x46 && // F
      tileData[3] === 0x46 && // F
      tileData[8] === 0x57 && // W
      tileData[9] === 0x45 && // E
      tileData[10] === 0x42 && // B
      tileData[11] === 0x50 // P
    ) {
      return "image/webp";
    }
  }

  // Default to protobuf for vector tiles (MVT)
  return "application/x-protobuf";
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
