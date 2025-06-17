import { NextRequest, NextResponse } from "next/server";
import { BlobImageManager } from "@/lib/blob-manager";
import { BLOB_CONFIG } from "@/lib/blob-config";

export async function GET(
  request: NextRequest,
  { params }: { params: { category: string } }
) {
  try {
    if (!BLOB_CONFIG.categories.includes(params.category as any)) {
      return NextResponse.json({ error: "Invalid category" }, { status: 400 });
    }

    const images = await BlobImageManager.getImagesByCategory(
      params.category as any
    );
    return NextResponse.json({ images });
  } catch (error) {
    console.error("Fetch error:", error);
    return NextResponse.json(
      {
        error:
          error instanceof Error ? error.message : "Failed to fetch images",
      },
      { status: 500 }
    );
  }
}
