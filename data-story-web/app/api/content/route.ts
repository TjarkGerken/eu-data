import { NextRequest, NextResponse } from "next/server";
import { fetchContentByLanguage } from "@/lib/content-service";
import { supabase } from "@/lib/supabase";
import { ContentBlockInsert } from "@/lib/supabase";

export async function GET(request: NextRequest) {
  try {
    const storyId = request.nextUrl.searchParams.get("storyId");
    const language = request.nextUrl.searchParams.get("language") || "en";

    if (storyId) {
      // Fetch content for specific story
      const { data: blocks, error } = await supabase
        .from("content_blocks")
        .select("*")
        .eq("story_id", storyId)
        .order("order_index");

      if (error) {
        throw error;
      }

      return NextResponse.json(blocks || []);
    } else {
      // Fetch content using the content service
      const content = await fetchContentByLanguage(language);
      return NextResponse.json(content);
    }
  } catch (error) {
    console.error("Error fetching content:", error);
    return NextResponse.json(
      { error: "Failed to fetch content" },
      { status: 500 }
    );
  }
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

    // For backward compatibility, if content is provided as an array of blocks
    if (Array.isArray(content)) {
      const blocksToInsert = content.map((block, index) => ({
        story_id: storyId,
        block_type: block.type || "markdown",
        order_index: index,
        data: block,
        title: block.title || null,
        content: block.content || null,
      }));

      const { data, error } = await supabase
        .from("content_blocks")
        .insert(blocksToInsert)
        .select();

      if (error) {
        throw error;
      }

      return NextResponse.json({
        message: `Content for story ${storyId} saved successfully`,
        blocks: data,
      });
    }

    return NextResponse.json({
      message: "Content saved successfully",
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

    // Get the next order index
    const { data: maxOrderBlock } = await supabase
      .from("content_blocks")
      .select("order_index")
      .eq("story_id", storyId)
      .order("order_index", { ascending: false })
      .limit(1)
      .single();

    const newOrderIndex = maxOrderBlock ? maxOrderBlock.order_index + 1 : 1;

    // Create blocks for both languages
    const blocksToInsert = [
      {
        story_id: storyId,
        block_type: enBlock.type || "markdown",
        order_index: newOrderIndex,
        data: enBlock,
        language: "en",
        title: enBlock.title || null,
        content: enBlock.content || null,
      },
      {
        story_id: storyId,
        block_type: deBlock.type || "markdown",
        order_index: newOrderIndex,
        data: deBlock,
        language: "de",
        title: deBlock.title || null,
        content: deBlock.content || null,
      },
    ];

    const { data: createdBlocks, error } = await supabase
      .from("content_blocks")
      .insert(blocksToInsert)
      .select();

    if (error) {
      throw error;
    }

    const [createdEnBlock, createdDeBlock] = createdBlocks || [];

    return NextResponse.json({
      en: createdEnBlock,
      de: createdDeBlock,
    });
  } catch (error: any) {
    console.error("Error creating content block:", error);
    return NextResponse.json(
      { error: "Failed to create content block", details: error.message },
      { status: 500 }
    );
  }
}
