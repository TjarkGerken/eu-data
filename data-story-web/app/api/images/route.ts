import { NextRequest, NextResponse } from "next/server";
import { BlobImageManager } from "@/lib/blob-manager";

export async function GET() {
  try {
    console.log(
      "API: Fetching all images, token available:",
      !!process.env.BLOB_READ_WRITE_TOKEN
    );
    const images = await BlobImageManager.getAllImages();
    console.log("API: Successfully fetched", images.length, "images");
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
    console.log(
      "API: Delete request, token available:",
      !!process.env.BLOB_READ_WRITE_TOKEN
    );
    const { pathname } = await request.json();

    if (!pathname) {
      return NextResponse.json({ error: "Missing pathname" }, { status: 400 });
    }

    await BlobImageManager.deleteImage(pathname);
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
