import { NextResponse } from "next/server";
import { styleService } from "@/lib/style-service";
import type { LayerStyleConfig } from "@/lib/map-types";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ layerId: string }> },
) {
  const { layerId } = await params;
  try {
    const styleConfig = await styleService.getLayerStyle(layerId);

    if (!styleConfig) {
      return NextResponse.json({ error: "Style not found" }, { status: 404 });
    }
    return NextResponse.json(styleConfig);
  } catch (error) {
    console.error(`Error fetching style for layer ${layerId}:`, error);
    return NextResponse.json(
      { error: "Internal Server Error" },
      { status: 500 },
    );
  }
}

export async function PUT(
  request: Request,
  { params }: { params: Promise<{ layerId: string }> },
) {
  const { layerId } = await params;
  try {
    const body: LayerStyleConfig = await request.json();

    const updatedStyle = await styleService.updateLayerStyle(layerId, body);
    return NextResponse.json(updatedStyle);
  } catch (error) {
    console.error(`Error updating style for layer ${layerId}:`, error);
    return NextResponse.json(
      { error: "Internal Server Error" },
      { status: 500 },
    );
  }
}

export async function DELETE(
  request: Request,
  { params }: { params: Promise<{ layerId: string }> },
) {
  const { layerId } = await params;
  try {
    await styleService.deleteLayerStyle(layerId);

    return NextResponse.json({ message: "Layer style deleted successfully" });
  } catch (error) {
    console.error(`Error deleting style for layer ${layerId}:`, error);
    return NextResponse.json(
      { error: "Failed to delete layer style" },
      { status: 500 },
    );
  }
}
