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

    // Try different possible file names with various extensions
    const possibleFileNames = [
      `${layerId}.geojson`,
      `${layerId}_optimized.geojson`,
      `${layerId}.tif`,
      `${layerId}_optimized.tif`,
      `${layerId}.tiff`,
      `${layerId}_optimized.tiff`,
      `${layerId}.gpkg`,
      `${layerId}_optimized.gpkg`,
      `${layerId}.png`,
      `${layerId}_optimized.png`,
    ];

    for (const fileName of possibleFileNames) {
      try {
        const { data, error } = await supabase.storage
          .from("map-layers")
          .download(fileName);

        if (!error && data) {
          const fileBuffer = await data.arrayBuffer();
          const extension = fileName.substring(fileName.lastIndexOf("."));
          const contentType = getContentType(extension);

          return new NextResponse(fileBuffer, {
            headers: {
              "Content-Type": contentType,
              "Content-Disposition": `attachment; filename="${fileName}"`,
              "Cache-Control": "public, max-age=3600",
            },
          });
        }
      } catch (downloadError) {
        console.warn(`Could not download ${fileName}:`, downloadError);
        // Continue trying other file names
      }
    }

    // No file found in storage
    return NextResponse.json(
      { error: `Layer ${layerId} not found for download` },
      { status: 404 }
    );
  } catch (error) {
    console.error("Error downloading layer:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

function getContentType(extension: string): string {
  const contentTypes: { [key: string]: string } = {
    ".geojson": "application/geo+json",
    ".json": "application/json",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".gpkg": "application/geopackage+sqlite3",
    ".png": "image/png",
  };

  return contentTypes[extension] || "application/octet-stream";
}
