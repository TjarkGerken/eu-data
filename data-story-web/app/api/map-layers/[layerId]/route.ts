import { NextRequest, NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";
import { promises as fs } from "fs";
import path from "path";

export async function DELETE(
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

    console.log(`Attempting to delete layer: ${layerId}`);

    const deletedFiles: string[] = [];
    const foundFiles: string[] = [];

    // First, get all files from Supabase storage and find matches
    try {
      const { data: files, error: listError } = await supabase.storage
        .from("map-layers")
        .list();

      if (listError) {
        console.warn("Error listing Supabase files:", listError);
      } else if (files) {
        console.log(`Found ${files.length} files in Supabase storage`);

        // Find files that match our layerId (exact match or with common extensions)
        const matchingFiles = files.filter((file) => {
          const fileName = file.name;
          const baseName = path.basename(fileName, path.extname(fileName));
          return baseName === layerId || fileName === layerId;
        });

        console.log(
          `Found ${matchingFiles.length} matching files for layer ${layerId}`
        );

        for (const file of matchingFiles) {
          foundFiles.push(file.name);
          console.log(`Found in Supabase: ${file.name}`);

          // Attempt to delete
          const { error: deleteError } = await supabase.storage
            .from("map-layers")
            .remove([file.name]);

          if (!deleteError) {
            deletedFiles.push(file.name);
            console.log(`Deleted from Supabase: ${file.name}`);
          } else {
            console.warn(`Failed to delete ${file.name}:`, deleteError);
          }
        }
      }
    } catch (storageError) {
      console.warn("Supabase storage access failed:", storageError);
    }

    // Also check local files (for completeness)
    const localDirectories = ["risk", "hazard", "exposition", "vector"];
    const possibleExtensions = [".geojson", ".tif", ".tiff", ".gpkg", ""];

    for (const dir of localDirectories) {
      for (const ext of possibleExtensions) {
        try {
          const fileName = ext ? `${layerId}${ext}` : layerId;
          const localPath = path.join(process.cwd(), "public", dir, fileName);
          await fs.access(localPath);

          foundFiles.push(`local:${dir}/${fileName}`);
          console.log(`Found locally: ${dir}/${fileName}`);

          // For local files, we could delete them but let's just report for now
          // await fs.unlink(localPath);
          // deletedFiles.push(`local:${dir}/${fileName}`);
        } catch {
          // File doesn't exist locally, continue
        }
      }
    }

    console.log(
      `Delete operation complete. Found: ${foundFiles.length}, Deleted: ${deletedFiles.length}`
    );

    if (deletedFiles.length > 0) {
      return NextResponse.json({
        message: `Layer ${layerId} deleted successfully`,
        deletedFiles,
        foundFiles: foundFiles.length,
        totalFound: foundFiles,
      });
    } else if (foundFiles.length > 0) {
      return NextResponse.json(
        {
          error: `Layer ${layerId} found but could not be deleted (some files may be local)`,
          foundFiles,
          message: "Local files are not deleted via this API for safety",
        },
        { status: 200 } // 200 since we found the files but didn't delete locals
      );
    } else {
      return NextResponse.json(
        { error: `Layer ${layerId} not found in storage or local files` },
        { status: 404 }
      );
    }
  } catch (error) {
    console.error("Error deleting layer:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
