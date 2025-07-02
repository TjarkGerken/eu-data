import { NextRequest, NextResponse } from "next/server";
import { styleService } from '@/lib/style-service';
import type { LayerStyleConfig } from "@/lib/map-types";

const layerStyles = new Map<string, LayerStyleConfig>();

export async function GET(
  request: Request,
  { params }: { params: { layerId: string } }
) {
  try {
    const styleConfig = await styleService.getLayerStyle(params.layerId);
    if (!styleConfig) {
      return NextResponse.json({ error: 'Style not found' }, { status: 404 });
    }
    return NextResponse.json(styleConfig);
  } catch (error) {
    console.error(`Error fetching style for layer ${params.layerId}:`, error);
    return NextResponse.json(
      { error: 'Internal Server Error' },
      { status: 500 }
    );
  }
}

export async function PUT(
  request: Request,
  { params }: { params: { layerId: string } }
) {
  try {
    const body: LayerStyleConfig = await request.json();
    const updatedStyle = await styleService.updateLayerStyle(
      params.layerId,
      body
    );
    return NextResponse.json(updatedStyle);
  } catch (error) {
    console.error(`Error updating style for layer ${params.layerId}:`, error);
    return NextResponse.json(
      { error: 'Internal Server Error' },
      { status: 500 }
    );
  }
}

export async function DELETE(
  _req: NextRequest,
  context: { params: Promise<{ layerId: string }> }
) {
  try {
    const { layerId } = await context.params;
    
    if (layerStyles.has(layerId)) {
      layerStyles.delete(layerId);
      return NextResponse.json({ message: "Layer style deleted successfully" });
    } else {
      return NextResponse.json(
        { error: "Style configuration not found" },
        { status: 404 }
      );
    }
  } catch (error) {
    console.error("Error deleting layer style:", error);
    return NextResponse.json(
      { error: "Failed to delete layer style" },
      { status: 500 }
    );
  }
} 