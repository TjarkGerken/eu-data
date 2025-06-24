import { NextRequest, NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";
import proj4 from "proj4";

// Define common coordinate systems
proj4.defs(
  "EPSG:3857",
  "+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs"
);
proj4.defs("EPSG:4326", "+proj=longlat +datum=WGS84 +no_defs");
proj4.defs(
  "EPSG:3035",
  "+proj=laea +lat_0=52 +lon_0=10 +x_0=4321000 +y_0=3210000 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs"
);

type Coordinate = [number, number];
type CoordinateArray = Coordinate | Coordinate[] | Coordinate[][] | Coordinate[][][];

function transformCoordinates(
  coords: CoordinateArray | null | undefined,
  sourceCRS: string = "EPSG:3857"
): CoordinateArray | null | undefined {
  if (!coords) return coords;

  // Check if coordinates look like they're already in lat/lng (WGS84)
  if (Array.isArray(coords) && coords.length >= 2 && typeof coords[0] === 'number') {
    const [x, y] = coords as Coordinate;
    if (x >= -180 && x <= 180 && y >= -90 && y <= 90) {
      // Already in WGS84, no transformation needed
      return coords;
    }
  }

  if (Array.isArray(coords) && Array.isArray(coords[0])) {
    // Array of coordinates
    return (coords as CoordinateArray[]).map((coord) => transformCoordinates(coord, sourceCRS)) as CoordinateArray;
  } else if (Array.isArray(coords) && coords.length >= 2 && typeof coords[0] === 'number') {
    // Single coordinate pair
    try {
      const [x, y] = coords as Coordinate;
      
      // Skip transformation if coordinates are clearly invalid
      if (!isFinite(x) || !isFinite(y)) {
        console.warn("Invalid coordinates detected:", coords);
        return coords;
      }
      
      const transformed = proj4(sourceCRS, "EPSG:4326", [x, y]) as Coordinate;
      return transformed;
    } catch (error) {
      console.warn("Failed to transform coordinates:", coords, error);
      return coords;
    }
  }

  return coords;
}

interface GeoJSONFeature {
  type: string;
  geometry?: {
    coordinates?: CoordinateArray;
  };
  properties?: Record<string, unknown>;
}

interface GeoJSONObject {
  type: string;
  features?: GeoJSONFeature[];
  crs?: {
    properties?: {
      name?: string;
    };
  };
}

function transformGeoJSONCoordinates(geojson: GeoJSONObject): GeoJSONObject {
  if (!geojson || !geojson.features) return geojson;

  // Check if CRS is specified in the GeoJSON
  let sourceCRS = "EPSG:3857"; // Default assumption

  if (geojson.crs && geojson.crs.properties && geojson.crs.properties.name) {
    const crsName = geojson.crs.properties.name;
    if (typeof crsName === "string") {
      if (crsName.includes("3857")) sourceCRS = "EPSG:3857";
      else if (crsName.includes("4326")) sourceCRS = "EPSG:4326";
      else if (crsName.includes("3035")) sourceCRS = "EPSG:3035";
    }
  }

  console.log(
    "Vector API: Transforming coordinates from",
    sourceCRS,
    "to EPSG:4326"
  );

  const transformedFeatures = geojson.features.map((feature: GeoJSONFeature) => {
    if (feature.geometry && feature.geometry.coordinates) {
      const transformedCoords = transformCoordinates(
        feature.geometry.coordinates,
        sourceCRS
      );
      return {
        ...feature,
        geometry: {
          ...feature.geometry,
          coordinates: transformedCoords || feature.geometry.coordinates,
        },
      };
    }
    return feature;
  });

  return {
    ...geojson,
    features: transformedFeatures,
    // Remove the original CRS and let Leaflet assume WGS84
    crs: undefined,
  };
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ layerId: string }> }
) {
  try {
    const resolvedParams = await params;
    const { layerId } = resolvedParams;

    console.log("Vector API: Requested layer ID:", layerId);

    if (!layerId) {
      return NextResponse.json(
        { error: "Layer ID is required" },
        { status: 400 }
      );
    }

    // Try different possible file extensions for vector data
    const possibleFileNames = [
      `${layerId}.geojson`,
      `${layerId}_optimized.geojson`,
      `${layerId}.json`,
      `clusters_${layerId}_optimized.geojson`,
      `clusters_${layerId}.geojson`,
      `${layerId}_COMBINED_optimized.geojson`,
      `${layerId}_COMBINED.geojson`,
    ];

    // Special handling for cluster layers with SLR scenario patterns
    if (layerId.includes('clusters-slr')) {
      const scenario = layerId.replace('clusters-slr-', '');
      const scenarioCapitalized = scenario.charAt(0).toUpperCase() + scenario.slice(1);
      possibleFileNames.push(
        `clusters_SLR-0-${scenarioCapitalized}_COMBINED_optimized.geojson`,
        `clusters_SLR-0-${scenarioCapitalized}_COMBINED.geojson`,
        `clusters_SLR-1-${scenarioCapitalized}_COMBINED_optimized.geojson`,
        `clusters_SLR-1-${scenarioCapitalized}_COMBINED.geojson`,
        `clusters_SLR-2-${scenarioCapitalized}_COMBINED_optimized.geojson`,
        `clusters_SLR-2-${scenarioCapitalized}_COMBINED.geojson`,
        `clusters_SLR-3-${scenarioCapitalized}_COMBINED_optimized.geojson`,
        `clusters_SLR-3-${scenarioCapitalized}_COMBINED.geojson`
      );
    }

    console.log("Vector API: Trying file names:", possibleFileNames);

    for (const fileName of possibleFileNames) {
      try {
        console.log("Vector API: Attempting to download:", fileName);
        const { data, error } = await supabase.storage
          .from("map-layers")
          .download(fileName);

        if (!error && data) {
          console.log("Vector API: Successfully downloaded:", fileName);
          const text = await data.text();
          const vectorData = JSON.parse(text);

          console.log(
            "Vector API: Parsed data features count:",
            vectorData?.features?.length || 0
          );

          // Transform coordinates to WGS84 if needed
          const transformedData = transformGeoJSONCoordinates(vectorData);

          return NextResponse.json(transformedData, {
            headers: {
              "Cache-Control": "public, max-age=3600",
              "Content-Type": "application/json",
            },
          });
        } else {
          console.log("Vector API: Failed to download:", fileName, error);
        }
      } catch (downloadError) {
        console.warn(`Could not download ${fileName}:`, downloadError);
        // Continue trying other file names
      }
    }

    // If no vector data found, return empty GeoJSON
    console.warn(
      `Layer ${layerId} not found in storage, returning empty GeoJSON`
    );
    return NextResponse.json(
      {
        type: "FeatureCollection",
        features: [],
      },
      {
        headers: {
          "Cache-Control": "public, max-age=300", // Shorter cache for missing data
          "Content-Type": "application/json",
        },
      }
    );
  } catch (error) {
    console.error("Error serving vector data:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
