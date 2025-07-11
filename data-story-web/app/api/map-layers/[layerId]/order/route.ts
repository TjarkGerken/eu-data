import { NextRequest, NextResponse } from "next/server";

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ layerId: string }> },
) {
  try {
    const resolvedParams = await params;
    const { layerId } = resolvedParams;
    const body = await request.json();
    const { zIndex } = body;

    if (!layerId) {
      return NextResponse.json(
        { error: "Layer ID is required" },
        { status: 400 },
      );
    }

    if (typeof zIndex !== "number") {
      return NextResponse.json(
        { error: "Valid zIndex number is required" },
        { status: 400 },
      );
    }

    // TODO: Implement actual layer order update logic
    // This would typically update the layer's zIndex in your database/storage
    // For now, we'll return success since the actual storage implementation
    // depends on your specific backend architecture

    console.log(`Updating layer ${layerId} zIndex to ${zIndex}`);

    // In a real implementation, you would:
    // 1. Validate the layer exists
    // 2. Update the layer's zIndex in your storage system
    // 3. Potentially update related cache/metadata

    return NextResponse.json({
      success: true,
      layerId,
      zIndex,
      message: "Layer order updated successfully",
    });
  } catch (error) {
    console.error("Error updating layer order:", error);
    return NextResponse.json(
      { error: "Failed to update layer order" },
      { status: 500 },
    );
  }
}
