import { NextRequest, NextResponse } from "next/server";
import { CloudflareR2Manager } from "@/lib/blob-manager";
import { ImageCategory } from "@/lib/blob-config";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ category: string }> },
) {
  try {
    const { category } = await params;
    console.log(`API: Fetching images for category: ${category}`);

    const images = await CloudflareR2Manager.getImagesByCategory(
      category as ImageCategory,
    );

    console.log(
      `API: Found ${images?.length || 0} images for category ${category}`,
    );

    return NextResponse.json({ images });
  } catch (error) {
    console.error(`Fetch images for category error:`, error);
    return NextResponse.json(
      {
        error:
          error instanceof Error ? error.message : "Failed to fetch images",
      },
      { status: 500 },
    );
  }
}
