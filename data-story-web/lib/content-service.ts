import { supabase } from "./supabase";

export interface ContentReference {
  id: string;
  title: string;
  authors: string[];
  year: number;
  journal: string | null;
  url: string | null;
  type: string;
  readable_id: string;
}

export interface ContentStory {
  id: string;
  languageCode: string;
  heroTitle: string;
  heroDescription: string | null;
  dataStoryTitle: string | null;
  introText1: string | null;
  introText2: string | null;
}

export interface ContentBlock {
  id: string;
  storyId: string | null;
  blockType: string;
  orderIndex: number;
  title?: string;
  content?: string;
  data: Record<string, unknown> | null;
  references?: ContentReference[];
}

export interface ContentData {
  story: ContentStory;
  blocks: ContentBlock[];
  references: ContentReference[];
}

export async function fetchContentByLanguage(
  languageCode: string = "en"
): Promise<ContentData | null> {
  try {
    const { data: story, error: storyError } = await supabase
      .from("content_stories")
      .select("*")
      .eq("language_code", languageCode)
      .single();

    if (storyError) {
      console.error("Error fetching story:", storyError);
      return null;
    }

    if (!story) return null;

    const { data: blocksData, error: blocksError } = await supabase
      .from("content_blocks")
      .select(
        `
        *,
        block_references(
          reference_id,
          content_references(*)
        )
      `
      )
      .eq("story_id", story.id)
      .order("order_index");

    if (blocksError) {
      console.error("Error fetching blocks:", blocksError);
      return null;
    }

    const { data: allReferences, error: referencesError } = await supabase
      .from("content_references")
      .select("*");

    if (referencesError) {
      console.error("Error fetching references:", referencesError);
      return null;
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const processedBlocks: ContentBlock[] = (blocksData || []).map((block: any) => ({
      id: block.id,
      storyId: block.story_id,
      blockType: block.block_type,
      orderIndex: block.order_index,
      title: block.title || undefined,
      content: block.content || undefined,
      data: (block.data as Record<string, unknown>) || null,
      references:
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        block.block_references?.map((br: any) => br.content_references) || [],
    }));

    const transformedStory: ContentStory = {
      id: story.id,
      languageCode: story.language_code,
      heroTitle: story.hero_title,
      heroDescription: story.hero_description,
      dataStoryTitle: story.data_story_title,
      introText1: story.intro_text_1,
      introText2: story.intro_text_2,
    };

    return {
      story: transformedStory,
      blocks: processedBlocks,
      references: allReferences || [],
    };
  } catch (error) {
    console.error("Error in fetchContentByLanguage:", error);
    return null;
  }
}

export async function fetchAllReferences(): Promise<ContentReference[]> {
  try {
    const { data, error } = await supabase
      .from("content_references")
      .select("*")
      .order("year", { ascending: false });

    if (error) {
      console.error("Error fetching references:", error);
      return [];
    }

    return data || [];
  } catch (error) {
    console.error("Error in fetchAllReferences:", error);
    return [];
  }
}

export async function fetchBlocksByType(
  blockType: string,
  languageCode: string = "en"
): Promise<ContentBlock[]> {
  try {
    const { data: story } = await supabase
      .from("content_stories")
      .select("id")
      .eq("language_code", languageCode)
      .single();

    if (!story) return [];

    const { data, error } = await supabase
      .from("content_blocks")
      .select(
        `
        *,
        block_references(
          content_references(*)
        )
      `
      )
      .eq("story_id", story.id)
      .eq("block_type", blockType)
      .order("order_index");

    if (error) {
      console.error("Error fetching blocks by type:", error);
      return [];
    }

    return (data || []).map((block) => ({
      id: block.id,
      storyId: block.story_id,
      blockType: block.block_type,
      orderIndex: block.order_index,
      data: block.data as Record<string, unknown> | null,
      references:
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        block.block_references?.map((br: any) => br.content_references) || [],
    }));
  } catch (error) {
    console.error("Error in fetchBlocksByType:", error);
    return [];
  }
}
