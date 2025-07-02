// Simple in-memory style API route for layer style configuration
import { NextResponse } from "next/server";
import type { LayerStyleConfig } from "@/lib/map-types";

// Simple in-memory style store (replace with DB in production)
const layerStyles = new Map<string, LayerStyleConfig>();

export async function GET(
  _req: Request,
  context: { params: { layerId: string } }
) {
  try {
    const { layerId } = context.params;
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
  request: Request,
  context: { params: { layerId: string } }
) {
  try {
    const { layerId } = context.params;
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
  _req: Request,
  context: { params: { layerId: string } }
) {
  try {
    const { layerId } = context.params;
    
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