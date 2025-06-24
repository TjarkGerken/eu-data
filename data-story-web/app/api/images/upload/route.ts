import { NextRequest, NextResponse } from "next/server";
import { SupabaseImageManager } from "@/lib/blob-manager";
import { BLOB_CONFIG, ImageCategory, ImageScenario } from "@/lib/blob-config";

export async function POST(request: NextRequest) {
  try {
    console.log(
      "API: Upload request, token available:",
      !!process.env.BLOB_READ_WRITE_TOKEN
    );
    const formData = await request.formData();
    const file = formData.get("file") as File;
    const category = formData.get("category") as string;
    const scenario = formData.get("scenario") as string;
    const description = formData.get("description") as string;
    const id = formData.get("id") as string;

    if (!file || !category || !description || !id) {
      return NextResponse.json(
        { error: "Missing required fields" },
        { status: 400 }
      );
    }

    if (file.size > BLOB_CONFIG.maxFileSize) {
      return NextResponse.json({ error: "File too large" }, { status: 400 });
    }

    if (!BLOB_CONFIG.allowedTypes.includes(file.type)) {
      return NextResponse.json({ error: "Invalid file type" }, { status: 400 });
    }

    if (!BLOB_CONFIG.categories.includes(category as ImageCategory)) {
      return NextResponse.json({ error: "Invalid category" }, { status: 400 });
    }

    const result = await SupabaseImageManager.uploadImage(file, {
      id,
      category: category as ImageCategory,
      scenario: scenario === "" ? undefined : (scenario as ImageScenario),
      description,
    });

    return NextResponse.json(result);
  } catch (error) {
    console.error("Upload error:", error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Upload failed" },
      { status: 500 }
    );
  }
}
