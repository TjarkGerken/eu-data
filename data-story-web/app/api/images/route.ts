import { NextRequest, NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

export async function GET() {
  try {
    console.log("API: Fetching all images from Supabase database");

    const { data: images, error } = await supabase
      .from("climate_images")
      .select("*")
      .order("created_at", { ascending: false });

    if (error) {
      throw new Error(`Database query failed: ${error.message}`);
    }

    console.log("API: Successfully fetched", images?.length || 0, "images");

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
    console.error("Fetch all images error:", error);
    return NextResponse.json(
      {
        error:
          error instanceof Error ? error.message : "Failed to fetch images",
      },
      { status: 500 }
    );
  }
}

export async function DELETE(request: NextRequest) {
  try {
    console.log("API: Delete request");
    const { pathname } = await request.json();

    if (!pathname) {
      return NextResponse.json({ error: "Missing pathname" }, { status: 400 });
    }

    const { data: image, error: fetchError } = await supabase
      .from("climate_images")
      .select("*")
      .eq("storage_path", pathname)
      .single();

    if (fetchError || !image) {
      return NextResponse.json({ error: "Image not found" }, { status: 404 });
    }

    const { error: storageError } = await supabase.storage
      .from("climate-images")
      .remove([pathname]);

    if (storageError) {
      throw new Error(`Storage deletion failed: ${storageError.message}`);
    }

    const { error: dbError } = await supabase
      .from("climate_images")
      .delete()
      .eq("storage_path", pathname);

    if (dbError) {
      console.warn("Database deletion failed:", dbError.message);
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Delete image error:", error);
    return NextResponse.json(
      {
        error:
          error instanceof Error ? error.message : "Failed to delete image",
      },
      { status: 500 }
    );
  }
}
