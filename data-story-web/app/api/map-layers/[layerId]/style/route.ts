import { NextRequest, NextResponse } from "next/server";
import { LayerStyleConfig } from "@/lib/map-types";

// In a real implementation, this would be stored in a database
// For now, we'll use in-memory storage (will reset on server restart)
const layerStyles = new Map<string, LayerStyleConfig>();

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ layerId: string }> }
) {
  try {
    const { layerId } = await params;
    const styleConfig = layerStyles.get(layerId);
    
    if (!styleConfig) {
      return NextResponse.json(
        { error: "Style configuration not found" },
        { status: 404 }
      );
    }
    
    return NextResponse.json(styleConfig);
  } catch (error) {
    console.error("Error fetching layer style:", error);
    return NextResponse.json(
      { error: "Failed to fetch layer style" },
      { status: 500 }
    );
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ layerId: string }> }
) {
  try {
    const { layerId } = await params;
    const styleConfig: LayerStyleConfig = await request.json();
    
    // Validate the style config
    if (!styleConfig || !styleConfig.id || !styleConfig.type) {
      return NextResponse.json(
        { error: "Invalid style configuration" },
        { status: 400 }
      );
    }
    
    // Ensure the ID matches
    if (styleConfig.id !== layerId) {
      return NextResponse.json(
        { error: "Style configuration ID does not match layer ID" },
        { status: 400 }
      );
    }
    
    // Update timestamp
    styleConfig.lastModified = new Date().toISOString();
    
    // Store the style configuration
    layerStyles.set(layerId, styleConfig);
    
    return NextResponse.json({
      message: "Layer style updated successfully",
      styleConfig
    });
  } catch (error) {
    console.error("Error updating layer style:", error);
    return NextResponse.json(
      { error: "Failed to update layer style" },
      { status: 500 }
    );
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ layerId: string }> }
) {
  try {
    const { layerId } = await params;
    
    if (layerStyles.has(layerId)) {
      layerStyles.delete(layerId);
      return NextResponse.json({
        message: "Layer style deleted successfully"
      });
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