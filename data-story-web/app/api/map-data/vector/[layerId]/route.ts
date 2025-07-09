import { NextRequest, NextResponse } from "next/server";
import {
  S3Client,
  ListObjectsV2Command,
  GetObjectCommand,
} from "@aws-sdk/client-s3";
import { R2_CONFIG, R2_BUCKET_NAME } from "@/lib/r2-config";
import Database from "better-sqlite3";
import { writeFileSync, unlinkSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";
import path from "path";

const s3Client = new S3Client(R2_CONFIG);

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ layerId: string }> }
) {
  try {
    const resolvedParams = await params;
    const { layerId } = resolvedParams;

    if (!layerId) {
      return NextResponse.json(
        { error: "Layer ID is required" },
        { status: 400 }
      );
    }

    // Find the actual filename for this layer ID
    const actualFileName = await findFileByLayerId(layerId);

    if (!actualFileName) {
      return NextResponse.json(
        { error: `Layer ${layerId} not found` },
        { status: 404 }
      );
    }

    try {
      // If the client explicitly asks for an outline, short-circuit normal logic
      if (request.nextUrl.searchParams.get("outline") === "1") {
        const outline = await getLayerOutline(layerId);
        if (outline) {
          return NextResponse.json(outline);
        }
        // fall through to normal handling if outline generation failed
      }

      const command = new GetObjectCommand({
        Bucket: R2_BUCKET_NAME,
        Key: `map-layers/${actualFileName}`,
      });

      const response = await s3Client.send(command);

      if (!response.Body) {
        return NextResponse.json(
          { error: `Layer ${layerId} not found` },
          { status: 404 }
        );
      }

      // Convert to GeoJSON based on file type
      const arrayBuffer = await response.Body.transformToByteArray();
      const buffer = Buffer.from(arrayBuffer);

      // For GeoJSON files, return directly
      if (actualFileName.endsWith(".geojson")) {
        const geoJson = JSON.parse(buffer.toString());
        return NextResponse.json(geoJson);
      }

      // For MBTiles files, extract tile coverage information
      if (actualFileName.endsWith(".mbtiles")) {
        const geoJson = await analyzeMBTilesCoverage(
          buffer,
          layerId,
          actualFileName
        );
        return NextResponse.json(geoJson);
      }

      // For other formats, return error as they need processing
      return NextResponse.json(
        {
          error: `Unsupported vector format for ${actualFileName}. Expected .geojson or .mbtiles`,
        },
        { status: 400 }
      );
    } catch (error) {
      console.error("Error processing vector data:", error);
      return NextResponse.json(
        { error: "Failed to process vector data" },
        { status: 500 }
      );
    }
  } catch (error) {
    console.error("Error serving vector data:", error);
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

interface CoverageAnalysis {
  total_tiles: number;
  min_zoom: number | null;
  max_zoom: number | null;
  min_x: number | null;
  max_x: number | null;
  min_y: number | null;
  max_y: number | null;
  features: Array<{
    type: string;
    geometry: {
      type: string;
      coordinates: number[][][];
    };
    properties: Record<string, string | number>;
  }>;
}

async function analyzeMBTilesCoverage(
  mbtileBuffer: Buffer,
  layerId: string,
  fileName: string
): Promise<CoverageAnalysis> {
  let tempFilePath: string | null = null;

  try {
    // Write MBTiles buffer to temporary file
    tempFilePath = join(tmpdir(), `temp_${Date.now()}.mbtiles`);
    writeFileSync(tempFilePath, mbtileBuffer);

    // Open MBTiles database
    const db = new Database(tempFilePath, { readonly: true });

    // Get metadata
    const metadataStmt = db.prepare("SELECT name, value FROM metadata");
    const metadataRows = metadataStmt.all() as Array<{
      name: string;
      value: string;
    }>;

    const metadata: Record<string, string> = {};
    for (const row of metadataRows) {
      metadata[row.name] = row.value;
    }

    // Check what tables exist
    // const tablesStmt = db.prepare(
    //   "SELECT name FROM sqlite_master WHERE type='table'"
    // );
    // const tables = tablesStmt.all() as Array<{ name: string }>;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    function analyzeCoverageFromDB(db: any) {
      const patterns = [
        // Standard MBTiles schema
        `SELECT 
           COUNT(*) as total_tiles,
           MIN(zoom_level) as min_zoom,
           MAX(zoom_level) as max_zoom,
           MIN(tile_column) as min_x,
           MAX(tile_column) as max_x,
           MIN(tile_row) as min_y,
           MAX(tile_row) as max_y
         FROM tiles`,
        // Alternative column names
        `SELECT 
           COUNT(*) as total_tiles,
           MIN(z) as min_zoom,
           MAX(z) as max_zoom,
           MIN(x) as min_x,
           MAX(x) as max_x,
           MIN(y) as min_y,
           MAX(y) as max_y
         FROM tiles`,
        // Map table variant
        `SELECT 
           COUNT(*) as total_tiles,
           MIN(zoom_level) as min_zoom,
           MAX(zoom_level) as max_zoom,
           MIN(tile_column) as min_x,
           MAX(tile_column) as max_x,
           MIN(tile_row) as min_y,
           MAX(tile_row) as max_y
         FROM map`,
      ];

      for (const pattern of patterns) {
        try {
          const stmt = db.prepare(pattern);
          const result = stmt.get();
          if (result && result.total_tiles > 0) {
            return result;
          }
        } catch (error) {
          console.log("Coverage pattern failed:", (error as Error).message);
        }
      }

      // Return default if all patterns fail
      return {
        total_tiles: 0,
        min_zoom: null,
        max_zoom: null,
        min_x: null,
        max_x: null,
        min_y: null,
        max_y: null,
      };
    }

    // Get tile coverage information using the function
    const coverage = analyzeCoverageFromDB(db);

    // Try to get actual tiles using different query patterns
    let sampleTiles: Array<Record<string, number>> = [];
    const sampleQueries = [
      "SELECT zoom_level, tile_column, tile_row FROM tiles LIMIT 10",
      "SELECT z, x, y FROM tiles LIMIT 10",
      "SELECT zoom_level, tile_column, tile_row FROM map LIMIT 10",
    ];

    for (const query of sampleQueries) {
      try {
        const stmt = db.prepare(query);
        sampleTiles = stmt.all() as Array<Record<string, number>>;
        if (sampleTiles && sampleTiles.length > 0) {
          break;
        }
      } catch (error) {
        console.log("Sample query failed:", query, (error as Error).message);
      }
    }

    // Close database
    db.close();

    // Extract scenario and risk type from filename
    let scenario = "unknown";
    let riskType = "unknown";

    if (fileName.includes("clusters_SLR")) {
      const match = fileName.match(/clusters_SLR-(\d+)-(\w+)_(\w+)/);
      if (match) {
        scenario = match[2].toLowerCase();
        riskType = match[3].toLowerCase();
      }
    }

    // Create features based on tile coverage
    const features = [];

    if (coverage.total_tiles > 0 && sampleTiles.length > 0) {
      // Create features for each sample tile to show actual coverage
      for (const tile of sampleTiles.slice(0, 5)) {
        // Limit to 5 features for performance
        const z = tile.zoom_level || tile.z;
        const x = tile.tile_column || tile.x;
        const y = tile.tile_row || tile.y;

        if (z !== undefined && x !== undefined && y !== undefined) {
          const bounds = getTileBounds(x, y, z);

          features.push({
            type: "Feature",
            geometry: {
              type: "Polygon",
              coordinates: [
                [
                  [bounds.west, bounds.north],
                  [bounds.east, bounds.north],
                  [bounds.east, bounds.south],
                  [bounds.west, bounds.south],
                  [bounds.west, bounds.north],
                ],
              ],
            },
            properties: {
              tile_x: x,
              tile_y: y,
              zoom_level: z,
              scenario: scenario,
              risk_type: riskType,
              layer_id: layerId,
            },
          });
        }
      }
    } else {
      // Fallback: create a feature based on metadata bounds if available
      let bounds = [-180, -90, 180, 90]; // Default world bounds

      if (metadata.bounds) {
        try {
          bounds = metadata.bounds.split(",").map(Number);
        } catch {
          console.warn(
            "Could not parse bounds from metadata:",
            metadata.bounds
          );
        }
      }

      features.push({
        type: "Feature",
        geometry: {
          type: "Polygon",
          coordinates: [
            [
              [bounds[0], bounds[3]], // west, north
              [bounds[2], bounds[3]], // east, north
              [bounds[2], bounds[1]], // east, south
              [bounds[0], bounds[1]], // west, south
              [bounds[0], bounds[3]], // west, north
            ],
          ],
        },
        properties: {
          scenario: scenario,
          risk_type: riskType,
          layer_id: layerId,
          source: "metadata_bounds",
          note: "Fallback bounds from MBTiles metadata",
        },
      });
    }

    // Return coverage analysis with features
    return {
      total_tiles: coverage.total_tiles,
      min_zoom: coverage.min_zoom,
      max_zoom: coverage.max_zoom,
      min_x: coverage.min_x,
      max_x: coverage.max_x,
      min_y: coverage.min_y,
      max_y: coverage.max_y,
      features: features,
    };
  } catch (error) {
    console.error("Error analyzing MBTiles coverage:", error);
    throw new Error(
      `Failed to analyze MBTiles coverage: ${(error as Error).message}`
    );
  } finally {
    // Clean up temporary file
    if (tempFilePath) {
      try {
        unlinkSync(tempFilePath);
      } catch (cleanupError) {
        console.warn("Failed to clean up temporary file:", cleanupError);
      }
    }
  }
}

function getTileBounds(x: number, y: number, z: number) {
  const n = Math.pow(2, z);
  const west = (x / n) * 360 - 180;
  const east = ((x + 1) / n) * 360 - 180;
  const north =
    (Math.atan(Math.sinh(Math.PI * (1 - (2 * y) / n))) * 180) / Math.PI;
  const south =
    (Math.atan(Math.sinh(Math.PI * (1 - (2 * (y + 1)) / n))) * 180) / Math.PI;

  return { west, east, north, south };
}

// Extract actual vector features from MBTiles for better outline generation
async function extractVectorFeaturesFromMBTiles(
  mbtileBuffer: Buffer,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _layerId: string,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _fileName: string
): Promise<GeoJSON.FeatureCollection | null> {
  let tempFilePath: string | null = null;

  try {
    // Write MBTiles buffer to temporary file
    tempFilePath = join(tmpdir(), `temp_vector_${Date.now()}.mbtiles`);
    writeFileSync(tempFilePath, mbtileBuffer);

    // Open MBTiles database
    const db = new Database(tempFilePath, { readonly: true });

    // Try to get actual vector tile data from a few sample tiles
    const sampleQueries = [
      "SELECT tile_data, zoom_level, tile_column, tile_row FROM tiles WHERE zoom_level <= 8 LIMIT 5",
      "SELECT tile_data, z, x, y FROM tiles WHERE z <= 8 LIMIT 5",
      "SELECT tile_data, zoom_level, tile_column, tile_row FROM map WHERE zoom_level <= 8 LIMIT 5",
    ];

    let tileRows: Array<{
      tile_data: Buffer;
      zoom_level?: number;
      tile_column?: number;
      tile_row?: number;
      z?: number;
      x?: number;
      y?: number;
    }> = [];

    for (const query of sampleQueries) {
      try {
        const stmt = db.prepare(query);
        tileRows = stmt.all() as Array<{
          tile_data: Buffer;
          zoom_level?: number;
          tile_column?: number;
          tile_row?: number;
          z?: number;
          x?: number;
          y?: number;
        }>;
        if (tileRows && tileRows.length > 0) {
          break;
        }
      } catch (error) {
        console.log(
          "Vector tile query failed:",
          query,
          (error as Error).message
        );
      }
    }

    db.close();

    if (tileRows.length === 0) {
      return null;
    }

    // Decode vector tiles and extract features
    const { VectorTile } = await import("@mapbox/vector-tile");
    const { default: Protobuf } = await import("pbf");

    const allFeatures: GeoJSON.Feature[] = [];

    for (const tileRow of tileRows) {
      try {
        const tile = new VectorTile(new Protobuf(tileRow.tile_data));

        // Get layer names from the tile
        const layerNames = Object.keys(tile.layers);

        for (const layerName of layerNames) {
          const layer = tile.layers[layerName];

          // Extract features from this layer
          for (let i = 0; i < layer.length; i++) {
            try {
              const feature = layer.feature(i);
              const geom = feature.toGeoJSON(
                tileRow.tile_column || tileRow.x || 0,
                tileRow.tile_row || tileRow.y || 0,
                tileRow.zoom_level || tileRow.z || 0
              );

              if (geom && geom.geometry) {
                allFeatures.push(geom as GeoJSON.Feature);
              }
            } catch (featureError) {
              // Handle individual feature extraction errors
              if (featureError instanceof Error) {
                if (featureError.message.includes("Unimplemented type")) {
                  console.warn(`Skipping feature ${i} in layer ${layerName}: Unsupported geometry type (${featureError.message})`);
                } else {
                  console.warn(`Failed to extract feature ${i} in layer ${layerName}:`, featureError.message);
                }
              } else {
                console.warn(`Failed to extract feature ${i} in layer ${layerName}:`, featureError);
              }
              // Continue processing other features
              continue;
            }
          }
        }
      } catch (error) {
        if (error instanceof Error) {
          if (error.message.includes("Unimplemented type")) {
            console.warn(`Skipping tile due to unsupported geometry type: ${error.message}`);
          } else {
            console.warn("Failed to decode vector tile:", error.message);
          }
        } else {
          console.warn("Failed to decode vector tile:", error);
        }
        // Continue processing other tiles
        continue;
      }
    }

    if (allFeatures.length === 0) {
      return null;
    }

    return {
      type: "FeatureCollection",
      features: allFeatures,
    } as GeoJSON.FeatureCollection;
  } catch (error) {
    console.error("Error extracting vector features from MBTiles:", error);
    return null;
  } finally {
    // Clean up temporary file
    if (tempFilePath) {
      try {
        unlinkSync(tempFilePath);
      } catch (cleanupError) {
        console.warn("Failed to clean up temporary vector file:", cleanupError);
      }
    }
  }
}

// Dynamic turf import helper to avoid bundling turf in edge environment until needed
async function dissolvePolygons(
  featureCollection: GeoJSON.FeatureCollection
): Promise<GeoJSON.FeatureCollection> {
  try {
    // Filter to only polygon/multipolygon features for dissolve
    const polygonFeatures = featureCollection.features.filter(
      (feature) =>
        feature.geometry?.type === "Polygon" ||
        feature.geometry?.type === "MultiPolygon"
    );

    if (polygonFeatures.length === 0) {
      return featureCollection; // Return original if no polygons to dissolve
    }

    const polygonCollection = {
      type: "FeatureCollection" as const,
      features: polygonFeatures,
    };

    // Lazy-load turf only when we actually need it
    const { default: dissolve } = await import("@turf/dissolve");

    // Type assertion since we've filtered to only polygons
    const result = dissolve(
      polygonCollection as GeoJSON.FeatureCollection<GeoJSON.Polygon>
    );

    // turf/dissolve sometimes returns a FeatureCollection and sometimes a single Feature
    if (result.type === "FeatureCollection") {
      return result as GeoJSON.FeatureCollection;
    }

    // If it is a single Feature, wrap it into a FeatureCollection
    return {
      type: "FeatureCollection",
      features: [result as unknown as GeoJSON.Feature],
    } as GeoJSON.FeatureCollection;
  } catch (error) {
    console.error("Turf dissolve failed", error);
    // Fallback: return original
    return featureCollection;
  }
}

// Generate a dissolved outline for the given layer. Returns null on failure.
async function getLayerOutline(
  layerId: string
): Promise<GeoJSON.FeatureCollection | null> {
  try {
    // Locate the file first
    const actualFileName = await findFileByLayerId(layerId);
    if (!actualFileName) return null;

    const command = new GetObjectCommand({
      Bucket: R2_BUCKET_NAME,
      Key: `map-layers/${actualFileName}`,
    });

    const response = await s3Client.send(command);
    if (!response.Body) return null;

    const arrayBuffer = await response.Body.transformToByteArray();
    const buffer = Buffer.from(arrayBuffer);

    if (actualFileName.endsWith(".geojson")) {
      const geoJson = JSON.parse(
        buffer.toString()
      ) as GeoJSON.FeatureCollection;
      return await dissolvePolygons(geoJson);
    }

    if (actualFileName.endsWith(".mbtiles")) {
      // For MBTiles, extract actual vector data from a few tiles for outline generation
      const vectorFeatures = await extractVectorFeaturesFromMBTiles(
        buffer,
        layerId,
        actualFileName
      );
      if (vectorFeatures && vectorFeatures.features.length > 0) {
        return await dissolvePolygons(vectorFeatures);
      } else {
        // Fallback to coverage approximation if no vector features found
        const coverage = await analyzeMBTilesCoverage(
          buffer,
          layerId,
          actualFileName
        );
        const fc: GeoJSON.FeatureCollection = {
          type: "FeatureCollection",
          features: coverage.features,
        } as GeoJSON.FeatureCollection;
        return await dissolvePolygons(fc);
      }
    }

    return null;
  } catch (error) {
    console.error("Failed to generate outline", error);
    return null;
  }
}
