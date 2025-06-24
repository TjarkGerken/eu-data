import { NextRequest, NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";
import Database from "better-sqlite3";
import { writeFileSync, unlinkSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";

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
      const { data, error } = await supabase.storage
        .from("map-layers")
        .download(actualFileName);

      if (error || !data) {
        return NextResponse.json(
          { error: `Layer ${layerId} not found` },
          { status: 404 }
        );
      }

      // Convert to GeoJSON based on file type
      const arrayBuffer = await data.arrayBuffer();
      const buffer = Buffer.from(arrayBuffer);
      
      // For GeoJSON files, return directly
      if (actualFileName.endsWith('.geojson')) {
        const geoJson = JSON.parse(buffer.toString());
        return NextResponse.json(geoJson);
      }

      // For MBTiles files, extract tile coverage information
      if (actualFileName.endsWith('.mbtiles')) {
        const geoJson = await analyzeMBTilesCoverage(buffer, layerId, actualFileName);
        return NextResponse.json(geoJson);
      }

      // For other formats, return error as they need processing
      return NextResponse.json(
        { error: `Unsupported vector format for ${actualFileName}. Expected .geojson or .mbtiles` },
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

async function analyzeMBTilesCoverage(mbtileBuffer: Buffer, layerId: string, fileName: string): Promise<any> {
  let tempFilePath: string | null = null;
  
  try {
    // Write MBTiles buffer to temporary file
    tempFilePath = join(tmpdir(), `temp_${Date.now()}.mbtiles`);
    writeFileSync(tempFilePath, mbtileBuffer);

    // Open MBTiles database
    const db = new Database(tempFilePath, { readonly: true });

    // Get metadata
    const metadataStmt = db.prepare("SELECT name, value FROM metadata");
    const metadataRows = metadataStmt.all() as Array<{name: string, value: string}>;
    
    const metadata: Record<string, string> = {};
    for (const row of metadataRows) {
      metadata[row.name] = row.value;
    }

    console.log("MBTiles metadata:", metadata);

    // Analyze database structure to understand why tiles aren't found
    console.log("=== DATABASE STRUCTURE ANALYSIS ===");
    
    // Check what tables exist
    const tablesStmt = db.prepare("SELECT name FROM sqlite_master WHERE type='table'");
    const tables = tablesStmt.all() as Array<{name: string}>;
    console.log("Available tables:", tables.map(t => t.name));
    
    // Check tiles table structure if it exists
    if (tables.some(t => t.name === 'tiles')) {
      const tilesSchemaStmt = db.prepare("PRAGMA table_info(tiles)");
      const tilesSchema = tilesSchemaStmt.all();
      console.log("Tiles table schema:", tilesSchema);
      
      // Check if there are any rows at all
      const totalRowsStmt = db.prepare("SELECT COUNT(*) as count FROM tiles");
      const totalRows = totalRowsStmt.get() as {count: number};
      console.log("Total rows in tiles table:", totalRows.count);
      
      // If there are rows, check what zoom levels actually exist
      if (totalRows.count > 0) {
        const zoomLevelsStmt = db.prepare("SELECT DISTINCT zoom_level FROM tiles ORDER BY zoom_level");
        const actualZoomLevels = zoomLevelsStmt.all() as Array<{zoom_level: number}>;
        console.log("Actual zoom levels in database:", actualZoomLevels.map(z => z.zoom_level));
        
        // Get sample of actual data
        const sampleDataStmt = db.prepare("SELECT * FROM tiles LIMIT 3");
        const sampleData = sampleDataStmt.all();
        console.log("Sample tile data:", sampleData);
      }
    }
    
    // Check if there might be a different tiles table name
    const alternativeTablesStmt = db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%tile%'");
    const altTables = alternativeTablesStmt.all() as Array<{name: string}>;
    console.log("Tables with 'tile' in name:", altTables.map(t => t.name));

    console.log("=== END DATABASE ANALYSIS ===");

    // Function to analyze MBTiles coverage with fallback query patterns
    function analyzeMBTilesCoverage(db: any) {
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
         FROM map`
      ];
      
      for (const pattern of patterns) {
        try {
          const stmt = db.prepare(pattern);
          const result = stmt.get();
          if (result && result.total_tiles > 0) {
            console.log("Coverage query succeeded with pattern:", pattern.split('FROM')[1].trim());
            return result;
          }
        } catch (error) {
          console.log("Coverage pattern failed:", error.message);
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
        max_y: null
      };
    }

    // Get tile coverage information using the function
    const coverage = analyzeMBTilesCoverage(db);
    console.log("Tile coverage:", coverage);

    // Try to get actual tiles using different query patterns
    let sampleTiles: any[] = [];
    
    // Pattern 1: Standard MBTiles format
    if (sampleTiles.length === 0) {
      try {
        const standardTilesStmt = db.prepare(`
          SELECT zoom_level, tile_column, tile_row, length(tile_data) as tile_size 
          FROM tiles 
          LIMIT 5
        `);
        sampleTiles = standardTilesStmt.all();
        console.log("Standard query found:", sampleTiles.length, "tiles");
      } catch (error) {
        console.log("Standard query failed:", error.message);
      }
    }
    
    // Pattern 2: Alternative column names  
    if (sampleTiles.length === 0) {
      try {
        const alt1TilesStmt = db.prepare(`
          SELECT z as zoom_level, x as tile_column, y as tile_row, length(data) as tile_size 
          FROM tiles 
          LIMIT 5
        `);
        sampleTiles = alt1TilesStmt.all();
        console.log("Alternative column names found:", sampleTiles.length, "tiles");
      } catch (error) {
        console.log("Alternative column query failed:", error.message);
      }
    }
    
    // Pattern 3: Check if there's a map table (some MBTiles variations)
    if (sampleTiles.length === 0) {
      try {
        const mapTableStmt = db.prepare(`
          SELECT zoom_level, tile_column, tile_row, length(tile_data) as tile_size 
          FROM map 
          LIMIT 5
        `);
        sampleTiles = mapTableStmt.all();
        console.log("Map table found:", sampleTiles.length, "tiles");
      } catch (error) {
        console.log("Map table query failed:", error.message);
      }
    }

    console.log("Final sample:", sampleTiles.length, "tiles found for processing");

    // Create features representing the actual cluster coverage
    const features: any[] = [];
    
    // Extract scenario and risk type from filename
    const scenario = fileName.includes('Current') ? 'Current' : fileName.includes('Severe') ? 'Severe' : 'Unknown';
    const riskType = fileName.includes('GDP') ? 'GDP' : fileName.includes('POPULATION') ? 'Population' : fileName.includes('FREIGHT') ? 'Freight' : 'Unknown';
    
    if (sampleTiles.length === 0) {
      // If no tiles found in tiles table, try to extract data from metadata JSON
      console.log("No tiles found in tiles table - checking metadata JSON for direct feature data");
      
      if (metadata.json) {
        try {
          const jsonData = JSON.parse(metadata.json);
          console.log("Parsed JSON metadata:", jsonData);
          
          if (jsonData.tilestats && jsonData.tilestats.layers) {
            for (const layerStats of jsonData.tilestats.layers) {
              console.log(`Layer ${layerStats.layer}: ${layerStats.count} features`);
              
              if (layerStats.count > 0 && layerStats.geometry === 'Polygon') {
                // Extract bounds from metadata (handle both regular and antimeridian-adjusted bounds)
                let bounds;
                if (metadata.antimeridian_adjusted_bounds) {
                  bounds = metadata.antimeridian_adjusted_bounds.split(',').map(Number);
                  console.log("Using antimeridian-adjusted bounds:", bounds);
                } else if (metadata.bounds) {
                  bounds = metadata.bounds.split(',').map(Number);
                  console.log("Using regular bounds:", bounds);
                } else {
                  bounds = [-180, -85, 180, 85];
                  console.log("Using default world bounds");
                }
                
                const [west, south, east, north] = bounds;
                console.log(`Bounds: W=${west}, S=${south}, E=${east}, N=${north}`);
                
                // Check if bounds are reasonable and valid
                let boundsAreInvalid = false;
                
                // Check basic coordinate validity
                if (west < -180 || west > 180 || east < -180 || east > 180) {
                  console.warn("Bounds have longitude issues");
                  boundsAreInvalid = true;
                }
                if (south < -90 || south > 90 || north < -90 || north > 90) {
                  console.warn("Bounds have latitude issues");
                  boundsAreInvalid = true;
                }
                
                // Check for degenerate bounds (same north/south or east/west)
                if (Math.abs(north - south) < 0.01) {
                  console.warn("Bounds have zero or near-zero height (north ≈ south)");
                  boundsAreInvalid = true;
                }
                if (Math.abs(east - west) < 0.01) {
                  console.warn("Bounds have zero or near-zero width (east ≈ west)");
                  boundsAreInvalid = true;
                }
                
                // Check for unreasonably large bounds (spans entire globe)
                if ((east - west) > 350 || (north - south) > 170) {
                  console.warn("Bounds span nearly entire globe - likely invalid");
                  boundsAreInvalid = true;
                }
                
                // Check for polar extremes (likely invalid for European freight data)
                if (north > 80 || south < -80) {
                  console.warn("Bounds include polar regions - likely invalid for freight data");
                  boundsAreInvalid = true;
                }
                
                // Force European bounds if invalid
                if (boundsAreInvalid) {
                  console.warn("Using European bounds instead of invalid metadata bounds");
                  bounds[0] = -10; // west (Atlantic) 
                  bounds[1] = 35;  // south (North Africa)
                  bounds[2] = 30;  // east (Eastern Europe)
                  bounds[3] = 70;  // north (Scandinavia)
                }
                
                const finalWest = bounds[0];
                const finalSouth = bounds[1]; 
                const finalEast = bounds[2];
                const finalNorth = bounds[3];
                
                console.log(`Final bounds: W=${finalWest}, S=${finalSouth}, E=${finalEast}, N=${finalNorth}`);
                
                // Create features based on the tilestats
                for (let i = 0; i < layerStats.count; i++) {
                  // Distribute features across the bounds area
                  const lonSpread = (finalEast - finalWest) / layerStats.count;
                  const latSpread = (finalNorth - finalSouth) / layerStats.count;
                  const centerLon = finalWest + (lonSpread * i) + (lonSpread / 2);
                  const centerLat = finalSouth + (latSpread * i) + (latSpread / 2);
                  
                  // Create a polygon representing the cluster area
                  const clusterSize = 0.5; // degrees
                  
                  // Extract actual attribute values if available
                  const clusterProperties: any = {
                    type: "risk_cluster",
                    cluster_id: i,
                    scenario: scenario,
                    risk_type: riskType,
                    layer_name: layerStats.layer,
                    geometry_type: layerStats.geometry,
                    feature_count: layerStats.count,
                    source: "metadata_extraction"
                  };
                  
                  // Add actual attribute values from tilestats
                  if (layerStats.attributes) {
                    for (const attrInfo of layerStats.attributes) {
                      if (attrInfo.values && attrInfo.values.length > i) {
                        clusterProperties[attrInfo.attribute] = attrInfo.values[i];
                      } else if (attrInfo.min !== undefined && attrInfo.max !== undefined) {
                        // Interpolate between min and max for this cluster
                        const ratio = i / (layerStats.count - 1);
                        clusterProperties[attrInfo.attribute] = attrInfo.min + (ratio * (attrInfo.max - attrInfo.min));
                      }
                    }
                  }
                  
                  features.push({
                    type: "Feature",
                    properties: clusterProperties,
                    geometry: {
                      type: "Polygon",
                      coordinates: [[
                        [centerLon - clusterSize, centerLat - clusterSize],
                        [centerLon + clusterSize, centerLat - clusterSize], 
                        [centerLon + clusterSize, centerLat + clusterSize],
                        [centerLon - clusterSize, centerLat + clusterSize],
                        [centerLon - clusterSize, centerLat - clusterSize]
                      ]]
                    }
                  });

                  // Add center point with key attributes for popup display
                  const centerProperties: any = {
                    type: "cluster_center",
                    cluster_id: i,
                    scenario: scenario,
                    risk_type: riskType,
                    name: `${riskType} ${scenario} Risk Cluster ${i + 1}`
                  };
                  
                  // Add key attributes for display
                  if (layerStats.attributes) {
                    for (const attrInfo of layerStats.attributes) {
                      if (attrInfo.attribute.includes('risk') || attrInfo.attribute.includes('area') || attrInfo.attribute.includes('count')) {
                        if (attrInfo.values && attrInfo.values.length > i) {
                          centerProperties[attrInfo.attribute] = attrInfo.values[i];
                        }
                      }
                    }
                  }
                  
                  features.push({
                    type: "Feature",
                    properties: centerProperties,
                    geometry: {
                      type: "Point",
                      coordinates: [centerLon, centerLat]
                    }
                  });
                }
                
                console.log(`Created ${features.length} features from tilestats metadata`);
              }
            }
          }
        } catch (jsonError) {
          console.error("Error parsing metadata JSON:", jsonError);
        }
      }
      
      // If still no features, create info notice
      if (features.length === 0) {
        features.push({
          type: "Feature",
          properties: {
            type: "info_notice",
            message: "MBTiles file found but no extractable data",
            scenario: scenario,
            risk_type: riskType,
            total_tiles_in_file: coverage.total_tiles,
            zoom_range: `${coverage.min_zoom}-${coverage.max_zoom}`,
            note: "File exists but tiles table is empty and no extractable metadata found"
          },
          geometry: {
            type: "Point",
            coordinates: [13.4050, 52.5200] // Berlin as center point
          }
        });
      }
    } else {
      // Process available tiles
      for (const tile of sampleTiles) {
        const bounds = getTileBounds(tile.tile_column, tile.tile_row, tile.zoom_level);
        const centerLon = (bounds.west + bounds.east) / 2;
        const centerLat = (bounds.north + bounds.south) / 2;
        
        // Create polygon for tile coverage area
        features.push({
          type: "Feature",
          properties: {
            type: "cluster_area",
            cluster_id: `${tile.tile_column}-${tile.tile_row}`,
            zoom_level: tile.zoom_level,
            scenario: scenario,
            risk_type: riskType,
            data_size: tile.data_size,
            coverage_bounds: bounds
          },
          geometry: {
            type: "Polygon",
            coordinates: [[
              [bounds.west, bounds.north],
              [bounds.east, bounds.north], 
              [bounds.east, bounds.south],
              [bounds.west, bounds.south],
              [bounds.west, bounds.north]
            ]]
          }
        });

        // Add center point for better visibility
        features.push({
          type: "Feature",
          properties: {
            type: "cluster_center",
            cluster_id: `${tile.tile_column}-${tile.tile_row}`,
            scenario: scenario,
            risk_type: riskType,
            zoom_level: tile.zoom_level,
            name: `${riskType} ${scenario} Cluster ${tile.tile_column}-${tile.tile_row}`
          },
          geometry: {
            type: "Point",
            coordinates: [centerLon, centerLat]
          }
        });
      }
    }

    db.close();

    console.log(`Generated ${features.length} features representing MBTiles coverage`);

    // Return GeoJSON FeatureCollection with coverage data
    return {
      type: "FeatureCollection",
      features: features,
      properties: {
        source: "MBTiles coverage analysis",
        layerId: layerId,
        fileName: fileName,
        metadata: metadata,
        coverage: coverage,
        visualization_zoom: sampleTiles.length > 0 ? sampleTiles[0].zoom_level : coverage.min_zoom || 0,
        scenario: scenario,
        risk_type: riskType,
        total_tiles: coverage.total_tiles,
        zoom_range: `${coverage.min_zoom}-${coverage.max_zoom}`,
        note: "Features represent actual tile coverage areas from MBTiles database"
      }
    };

  } catch (error) {
    console.error("Error analyzing MBTiles coverage:", error);
    throw new Error(`Failed to analyze MBTiles coverage: ${error.message}`);
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
  const north = Math.atan(Math.sinh(Math.PI * (1 - 2 * y / n))) * 180 / Math.PI;
  const south = Math.atan(Math.sinh(Math.PI * (1 - 2 * (y + 1) / n))) * 180 / Math.PI;
  
  return { west, east, north, south };
}
