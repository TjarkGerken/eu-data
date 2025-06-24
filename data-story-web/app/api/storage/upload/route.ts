import { NextRequest, NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const file = formData.get("file") as File;
    const category = formData.get("category") as string;
    const scenario = formData.get("scenario") as string;
    const description = formData.get("description") as string;

    if (!file) {
      return NextResponse.json({ error: "No file provided" }, { status: 400 });
    }

    const fileExt = file.name.split(".").pop();
    const fileName = `${category}/${
      scenario || "default"
    }/${Date.now()}.${fileExt}`;

    const { error } = await supabase.storage
      .from("climate-images")
      .upload(fileName, file, {
        cacheControl: "3600",
        upsert: false,
      });

    if (error) {
      console.error("Supabase storage error:", error);
      return NextResponse.json(
        { error: "Failed to upload file" },
        { status: 500 }
      );
    }

    const {
      data: { publicUrl },
    } = supabase.storage.from("climate-images").getPublicUrl(fileName);

    const uniqueFilename = fileName.split("/").pop() || fileName; // Use the timestamped filename

    const { error: dbError } = await supabase.from("climate_images").insert({
      filename: uniqueFilename,
      category,
      scenario: scenario || "default",
      storage_path: fileName,
      public_url: publicUrl,
      description: description || `${category} ${scenario} image`,
      file_size: file.size,
      mime_type: file.type || "image/png",
    });

    if (dbError) {
      console.error("Database save error:", dbError);
      // Continue anyway since file was uploaded successfully
    }

    return NextResponse.json({
      url: publicUrl,
      path: fileName,
      category,
      scenario: scenario || "default",
    });
  } catch (error) {
    console.error("Upload error:", error);
    return NextResponse.json(
      { error: "Failed to process upload" },
      { status: 500 }
    );
  }
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const category = searchParams.get("category");
    const scenario = searchParams.get("scenario");

    let path = "";
    if (category && scenario) {
      path = `${category}/${scenario}`;
    } else if (category) {
      path = category;
    }

    const { data, error } = await supabase.storage
      .from("climate-images")
      .list(path, {
        limit: 100,
        sortBy: { column: "name", order: "asc" },
      });

    if (error) {
      console.error("Error listing files:", error);
      return NextResponse.json(
        { error: "Failed to list files" },
        { status: 500 }
      );
    }

    const files =
      data?.map((file) => {
        const fullPath = path ? `${path}/${file.name}` : file.name;
        const {
          data: { publicUrl },
        } = supabase.storage.from("climate-images").getPublicUrl(fullPath);

        return {
          id: file.name,
          name: file.name,
          url: publicUrl,
          category: category || "default",
          scenario: scenario || "default",
          size: file.metadata?.size || 0,
          created_at: file.created_at,
        };
      }) || [];

    return NextResponse.json({ files });
  } catch (error) {
    console.error("List error:", error);
    return NextResponse.json(
      { error: "Failed to list files" },
      { status: 500 }
    );
  }
}
