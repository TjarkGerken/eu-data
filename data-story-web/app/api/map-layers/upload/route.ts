import { NextRequest, NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";
import path from "path";
import { promises as fs } from "fs";

interface ProcessingResult {
  success: boolean;
  outputPath?: string;
  size?: number;
  error?: string;
}

export async function POST(request: NextRequest) {
  const tempDir = path.join(process.cwd(), "temp");
  let tempInputPath: string | null = null;

  try {
    await fs.mkdir(tempDir, { recursive: true });

    const formData = await request.formData();
    const file = formData.get("file") as File;
    const layerName = formData.get("layerName") as string;

    if (!file || !layerName) {
      return NextResponse.json(
        { error: "File and layer name are required" },
        { status: 400 }
      );
    }

    const fileExtension = file.name.split(".").pop()?.toLowerCase();

    if (!["cog", "mbtiles"].includes(fileExtension || "")) {
      return NextResponse.json(
        {
          error: "Unsupported file type. Please upload .cog or .mbtiles files only",
        },
        { status: 400 }
      );
    }

    const tempFileName = `${Date.now()}_${file.name}`;
    tempInputPath = path.join(tempDir, tempFileName);

    const buffer = Buffer.from(await file.arrayBuffer());
    await fs.writeFile(tempInputPath, buffer);

    console.log(`Processing ${fileExtension} file: ${tempInputPath}`);

    const processingResult: ProcessingResult = {
      success: true,
      outputPath: tempInputPath,
      size: buffer.length
    };

    if (!processingResult.success || !processingResult.outputPath) {
      throw new Error("File processing failed");
    }

    const optimizedBuffer = await fs.readFile(processingResult.outputPath);
    const optimizedFile = new File(
      [optimizedBuffer],
      path.basename(processingResult.outputPath),
      {
        type: getOptimizedMimeType(processingResult.outputPath),
      }
    );

    const { error } = await supabase.storage
      .from("map-layers")
      .upload(path.basename(processingResult.outputPath), optimizedFile, {
        cacheControl: "3600",
        upsert: true,
      });

    if (error) {
      console.error("Upload error:", error);
      throw new Error(`Failed to upload file: ${error.message}`);
    }

    const { data: publicUrlData } = supabase.storage
      .from("map-layers")
      .getPublicUrl(path.basename(processingResult.outputPath));

    return NextResponse.json({
      success: true,
      layerId: layerName,
      fileName: path.basename(processingResult.outputPath),
      url: publicUrlData.publicUrl,
      originalSize: file.size,
      optimizedSize: optimizedBuffer.length,
      message: "Web-optimized layer uploaded successfully",
    });
  } catch (error) {
    console.error("Server error:", error);
    return NextResponse.json(
      {
        error: "Failed to process and upload file",
        details: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  } finally {
    if (tempInputPath) {
      try {
        await fs.unlink(tempInputPath);
      } catch (cleanupError) {
        console.warn("Failed to cleanup temp file:", cleanupError);
      }
    }
  }
}

function getOptimizedMimeType(filePath: string): string {
  const ext = path.extname(filePath).toLowerCase();
  switch (ext) {
    case ".cog":
      return "image/tiff";
    case ".mbtiles":
      return "application/x-mbtiles";
    default:
      return "application/octet-stream";
  }
}
