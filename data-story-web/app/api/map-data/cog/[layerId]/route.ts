import { NextResponse } from "next/server";
import {
  S3Client,
  GetObjectCommand,
  ListObjectsV2Command,
} from "@aws-sdk/client-s3";
import { R2_CONFIG, R2_BUCKET_NAME } from "@/lib/r2-config";
import path from "path";

const s3Client = new S3Client(R2_CONFIG);

async function findFileByLayerId(layerId: string): Promise<string | null> {
  try {
    const command = new ListObjectsV2Command({
      Bucket: R2_BUCKET_NAME,
      Prefix: "map-layers/",
      MaxKeys: 1000,
    });

    const response = await s3Client.send(command);

    if (!response.Contents) {
      return null;
    }

    for (const object of response.Contents) {
      if (!object.Key) continue;
      const fileName = path.basename(object.Key);

      // Remove timestamp prefix if present
      let baseLayerId = path.basename(fileName, path.extname(fileName));
      const timestampMatch = baseLayerId.match(/^\d+_(.+)$/);
      if (timestampMatch) {
        baseLayerId = timestampMatch[1];
      }

      // Match the layer ID
      if (
        baseLayerId === layerId &&
        (fileName.endsWith(".tif") || fileName.endsWith(".cog"))
      ) {
        return fileName;
      }
    }

    return null;
  } catch (error) {
    console.error("Error finding COG file by layer ID:", error);
    return null;
  }
}

export async function GET(
  request: Request,
  { params }: { params: Promise<{ layerId: string }> },
) {
  try {
    const resolvedParams = await params;
    const { layerId } = resolvedParams;

    // Find the COG file for this layer
    const actualFileName = await findFileByLayerId(layerId);

    if (!actualFileName) {
      return NextResponse.json(
        { error: `COG file not found for layer ${layerId}` },
        { status: 404 },
      );
    }

    // Get the full file path in R2
    const cogFilePath = `map-layers/${actualFileName}`;

    // Get the COG file from R2
    const command = new GetObjectCommand({
      Bucket: R2_BUCKET_NAME,
      Key: cogFilePath,
    });

    const response = await s3Client.send(command);

    if (!response.Body) {
      return NextResponse.json(
        { error: `COG file not found in storage` },
        { status: 404 },
      );
    }

    // Stream the response body to a buffer
    const chunks: Uint8Array[] = [];
    const reader = response.Body.transformToWebStream().getReader();

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        chunks.push(value);
      }
    } finally {
      reader.releaseLock();
    }

    // Combine all chunks into a single buffer
    const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
    const combinedBuffer = new Uint8Array(totalLength);
    let offset = 0;
    for (const chunk of chunks) {
      combinedBuffer.set(chunk, offset);
      offset += chunk.length;
    }

    // Return the COG file with appropriate headers
    return new NextResponse(combinedBuffer, {
      headers: {
        "Content-Type": "image/tiff",
        "Content-Length": combinedBuffer.length.toString(),
        "Cache-Control": "public, max-age=31536000",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET",
        "Access-Control-Allow-Headers": "*",
      },
    });
  } catch (error) {
    console.error("Error serving COG file:", error);
    return NextResponse.json(
      { error: "Failed to serve COG file" },
      { status: 500 },
    );
  }
}
