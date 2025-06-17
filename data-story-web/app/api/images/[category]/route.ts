import { NextRequest, NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ category: string }> }
) {
  try {
    const { category } = await params;
    console.log(`API: Fetching images for category: ${category}`);

    const { data: images, error } = await supabase
      .from("climate_images")
      .select("*")
      .eq("category", category)
      .order("created_at", { ascending: false });

    if (error) {
      throw new Error(`Database query failed: ${error.message}`);
    }

    console.log(
      `API: Found ${images?.length || 0} images for category ${category}`
    );

    const formattedImages =
      images?.map((img) => ({
        url: img.public_url,
        path: img.storage_path,
        metadata: {
          id: img.filename.split(".")[0],
          category: img.category,
          scenario: img.scenario,
          description: img.description,
          uploadedAt: new Date(img.created_at),
          size: img.file_size,
        },
      })) || [];

    return NextResponse.json({ images: formattedImages });
  } catch (error) {
    console.error(`Fetch images for category error:`, error);
    return NextResponse.json(
      {
        error:
          error instanceof Error ? error.message : "Failed to fetch images",
      },
      { status: 500 }
    );
  }
}
