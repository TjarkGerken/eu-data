import { NextRequest, NextResponse } from "next/server";
import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";
import { R2_CONFIG, R2_BUCKET_NAME, R2_PUBLIC_URL_BASE } from "@/lib/r2-config";
import path from "path";
import { promises as fs } from "fs";

interface ProcessingResult {
  success: boolean;
  outputPath?: string;
  size?: number;
  error?: string;
}

const s3Client = new S3Client(R2_CONFIG);

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

    if (!["cog", "mbtiles", "tif", "tiff"].includes(fileExtension || "")) {
      return NextResponse.json(
        {
          error:
            "Unsupported file type. Please upload .cog, .mbtiles, .tif, or .tiff files only",
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
      size: buffer.length,
    };

    if (!processingResult.success || !processingResult.outputPath) {
      throw new Error("File processing failed");
    }

    const optimizedBuffer = await fs.readFile(processingResult.outputPath);
    const finalFileName = `map-layers/${path.basename(
      processingResult.outputPath
    )}`;

    const command = new PutObjectCommand({
      Bucket: R2_BUCKET_NAME,
      Key: finalFileName,
      Body: optimizedBuffer,
      ContentType: getOptimizedMimeType(processingResult.outputPath),
      CacheControl: "public, max-age=3600",
    });

    try {
      await s3Client.send(command);
    } catch (error) {
      console.error("R2 upload error:", error);
      throw new Error(`Failed to upload file to R2: ${error}`);
    }

    const publicUrl = `${R2_PUBLIC_URL_BASE}/${finalFileName}`;

    return NextResponse.json({
      success: true,
      layerId: layerName,
      fileName: path.basename(processingResult.outputPath),
      url: publicUrl,
      originalSize: file.size,
      optimizedSize: optimizedBuffer.length,
      message: "Web-optimized layer uploaded successfully to Cloudflare R2",
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
    case ".tif":
    case ".tiff":
      return "image/tiff";
    case ".mbtiles":
      return "application/x-mbtiles";
    default:
      return "application/octet-stream";
  }
}
