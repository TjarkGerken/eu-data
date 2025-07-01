import { NextRequest, NextResponse } from "next/server";
import { CloudflareR2Manager } from "@/lib/blob-manager";

export async function GET() {
  try {
    console.log("API: Fetching all images from R2 storage");

    const images = await CloudflareR2Manager.getAllImages();

    console.log("API: Successfully fetched", images?.length || 0, "images");
    console.log(images[0].metadata.caption);
    return NextResponse.json({ images });
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

    await CloudflareR2Manager.deleteImage(pathname);

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
