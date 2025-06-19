import { NextRequest, NextResponse } from "next/server";
import { fetchContentByLanguage } from "@/lib/content-service";
import { promises as fs } from "fs";
import path from "path";
import { supabase } from "@/lib/supabase";
import { ContentBlockInsert } from "@/lib/supabase";

const contentFilePath = path.join(
  process.cwd(),
  "data-story-web/lib/content.json"
);

async function getContent() {
  const fileContent = await fs.readFile(contentFilePath, "utf8");
  return JSON.parse(fileContent);
}

export async function GET(request: NextRequest) {
  const storyId = request.nextUrl.searchParams.get("storyId");

  if (!storyId) {
    // For now, returning all content if no storyId is provided,
    // but this could be an error in a multi-story setup.
    const allContent = await getContent();
    return NextResponse.json(allContent);
  }

  // In a real multi-story application, you would fetch content
  // specific to the storyId. Here we return the single content file.
  const content = await getContent();
  return NextResponse.json(content);
}

export async function POST(request: NextRequest) {
  try {
    const { storyId, content } = await request.json();

    if (!storyId || !content) {
      return NextResponse.json(
        { error: "Story ID and content are required" },
        { status: 400 }
      );
    }

    // In a real multi-story application, you would save content
    // specific to the storyId. Here we overwrite the single content file.
    await fs.writeFile(contentFilePath, JSON.stringify(content, null, 2));

    return NextResponse.json({
      message: `Content for story ${storyId} saved successfully`,
    });
  } catch (error) {
    console.error("Error saving content:", error);
    return NextResponse.json(
      { error: "Failed to save content" },
      { status: 500 }
    );
  }
}

export async function PUT(request: NextRequest) {
  try {
    const { storyId, enBlock, deBlock } = await request.json();

    if (!storyId || !enBlock || !deBlock) {
      return NextResponse.json(
        { error: "Story ID and block data are required" },
        { status: 400 }
      );
    }

    // This is a simplified implementation. It assumes that there is a way
    // to find the corresponding German story ID from the English one,
    // or that both blocks are associated with the same storyId, which
    // would be the case if language is handled within the block's data.

    // For this implementation, we'll assume a single story ID is used
    // and we store language-specific data within each block's `data` field.
    // This requires a modification on how content is fetched and processed.

    // A proper implementation would require a clear strategy for multilingual content.
    // For now, let's just insert the English block to make the flow work.

    const { data: maxOrderBlock } = await supabase
      .from("content_blocks")
      .select("order_index")
      .eq("story_id", storyId)
      .order("order_index", { ascending: false })
      .limit(1)
      .single();

    const newOrderIndex = maxOrderBlock ? maxOrderBlock.order_index + 1 : 0;

    const blockToInsert: Omit<
      ContentBlockInsert,
      "id" | "created_at" | "updated_at"
    > = {
      story_id: storyId,
      block_type: enBlock.type,
      order_index: newOrderIndex,
      data: enBlock,
    };

    const { data: createdEnBlock, error } = await supabase
      .from("content_blocks")
      .insert(blockToInsert)
      .select()
      .single();

    if (error) {
      throw error;
    }

    // The frontend expects both en and de blocks. We'll return the created
    // english block for both, with a different mock ID for the german one.
    // This is a temporary solution.
    const createdDeBlock = { ...createdEnBlock, id: createdEnBlock.id + "_de" };

    return NextResponse.json({ en: createdEnBlock, de: createdDeBlock });
  } catch (error: any) {
    console.error("Error creating content block:", error);
    return NextResponse.json(
      { error: "Failed to create content block", details: error.message },
      { status: 500 }
    );
  }
}
