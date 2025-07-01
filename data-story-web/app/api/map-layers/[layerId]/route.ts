import { NextRequest, NextResponse } from "next/server";
import {
  S3Client,
  ListObjectsV2Command,
  DeleteObjectCommand,
} from "@aws-sdk/client-s3";
import { R2_CONFIG, R2_BUCKET_NAME } from "@/lib/r2-config";
import { promises as fs } from "fs";
import path from "path";

const s3Client = new S3Client(R2_CONFIG);

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

    // Get all files from R2 storage and find matches
    try {
      const command = new ListObjectsV2Command({
        Bucket: R2_BUCKET_NAME,
        Prefix: "map-layers/",
        MaxKeys: 1000,
      });

      const response = await s3Client.send(command);

      if (response.Contents) {
        console.log(`Found ${response.Contents.length} files in R2 storage`);

        // Find files that match our layerId (exact match or with common extensions)
        const matchingFiles = response.Contents.filter((object) => {
          if (!object.Key) return false;
          const fileName = path.basename(object.Key);
          const baseName = path.basename(fileName, path.extname(fileName));
          return baseName === layerId || fileName === layerId;
        });

        console.log(
          `Found ${matchingFiles.length} matching files for layer ${layerId}`
        );

        for (const file of matchingFiles) {
          if (!file.Key) continue;

          foundFiles.push(file.Key);
          console.log(`Found in R2: ${file.Key}`);

          // Attempt to delete
          try {
            const deleteCommand = new DeleteObjectCommand({
              Bucket: R2_BUCKET_NAME,
              Key: file.Key,
            });

            await s3Client.send(deleteCommand);
            deletedFiles.push(file.Key);
            console.log(`Deleted from R2: ${file.Key}`);
          } catch (deleteError) {
            console.warn(`Failed to delete ${file.Key}:`, deleteError);
          }
        }
      }
    } catch (storageError) {
      console.warn("R2 storage access failed:", storageError);
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
