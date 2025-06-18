import { NextRequest, NextResponse } from "next/server";
import { fetchContentByLanguage } from "@/lib/content-service";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const language = searchParams.get("language") || "en";

    const contentData = await fetchContentByLanguage(language);

    if (!contentData) {
      return NextResponse.json(
        { error: `Content not found for language: ${language}` },
        { status: 404 }
      );
    }

    return NextResponse.json({
      story: contentData.story,
      blocks: contentData.blocks,
      references: contentData.references,
    });
  } catch (error) {
    console.error("Error reading content:", error);
    return NextResponse.json(
      { error: "Failed to read content" },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const content = await request.json();
    console.log("Received content to save:", JSON.stringify(content, null, 2));

    // Validate content structure
    if (!content || typeof content !== "object") {
      throw new Error("Invalid content structure");
    }

    if (!content.en || !content.de || !content.references) {
      throw new Error(
        "Missing required content properties (en, de, references)"
      );
    }

    // Ensure directory exists
    await fs.mkdir(path.dirname(CONTENT_FILE_PATH), { recursive: true });

    // Write file
    await fs.writeFile(CONTENT_FILE_PATH, JSON.stringify(content, null, 2));
    console.log("Content saved successfully to:", CONTENT_FILE_PATH);

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Error saving content:", error);
    console.error("Error details:", {
      message: error instanceof Error ? error.message : "Unknown error",
      stack: error instanceof Error ? error.stack : undefined,
    });
    return NextResponse.json(
      {
        error: "Failed to save content",
        details: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}
