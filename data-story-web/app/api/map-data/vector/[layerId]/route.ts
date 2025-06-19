import { NextRequest, NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

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

    // Try different possible file extensions for vector data
    const possibleFileNames = [
      `${layerId}.geojson`,
      `${layerId}_optimized.geojson`,
      `${layerId}.json`,
    ];

    for (const fileName of possibleFileNames) {
      try {
        const { data, error } = await supabase.storage
          .from("map-layers")
          .download(fileName);

        if (!error && data) {
          const text = await data.text();
          const vectorData = JSON.parse(text);

          return NextResponse.json(vectorData, {
            headers: {
              "Cache-Control": "public, max-age=3600",
              "Content-Type": "application/json",
            },
          });
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
