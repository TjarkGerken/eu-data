import { NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

export async function GET() {
  try {
    const { data, error } = await supabase
      .from("content_stories")
      .select("id, hero_title, hero_description")
      .order("hero_title", { ascending: true });

    if (error) {
      throw error;
    }

    // Transform the data to match the expected format
    const transformedData = data?.map((story) => ({
      id: story.id,
      title: story.hero_title,
      description: story.hero_description || "",
    }));

    return NextResponse.json(transformedData);
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
