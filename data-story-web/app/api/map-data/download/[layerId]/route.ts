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

    // Find the actual filename in storage that corresponds to this layer ID
    const actualFileName = await findFileByLayerId(layerId);
    
    if (!actualFileName) {
      return NextResponse.json(
        { error: `Layer ${layerId} not found for download` },
        { status: 404 }
      );
    }

    try {
      const { data, error } = await supabase.storage
        .from("map-layers")
        .download(actualFileName);

      if (error || !data) {
        return NextResponse.json(
          { error: `Layer ${layerId} not found for download` },
          { status: 404 }
        );
      }

      const fileBuffer = await data.arrayBuffer();
      const extension = actualFileName.substring(actualFileName.lastIndexOf("."));
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
        { status: 404 }
      );
    }
  } catch (error) {
    console.error("Error downloading layer:", error);
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

function getContentType(extension: string): string {
  const contentTypes: { [key: string]: string } = {
    ".cog": "image/tiff",
    ".tif": "image/tiff",
    ".mbtiles": "application/x-mbtiles",
    ".db": "application/x-mbtiles",
  };

  return contentTypes[extension] || "application/octet-stream";
}
