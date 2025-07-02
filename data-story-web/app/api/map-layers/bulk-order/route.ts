import { NextRequest, NextResponse } from "next/server";

export async function PUT(request: NextRequest) {
  try {
    const body = await request.json();
    const { updates } = body;

    if (!Array.isArray(updates)) {
      return NextResponse.json(
        { error: "Updates array is required" },
        { status: 400 }
      );
    }

    // Validate all updates have required fields
    for (const update of updates) {
      if (!update.id || typeof update.zIndex !== "number") {
        return NextResponse.json(
          { error: "Each update must have 'id' and 'zIndex' fields" },
          { status: 400 }
        );
      }
    }

    // TODO: Implement actual bulk layer order update logic
    // This would typically update multiple layers' zIndex in your database/storage
    // For now, we'll return success since the actual storage implementation
    // depends on your specific backend architecture

    console.log(`Bulk updating layer orders:`, updates);

    // In a real implementation, you would:
    // 1. Validate all layers exist
    // 2. Update all layers' zIndex in your storage system (preferably in a transaction)
    // 3. Potentially update related cache/metadata

    return NextResponse.json({
      success: true,
      updatedCount: updates.length,
      message: "Layer orders updated successfully",
    });
  } catch (error) {
    console.error("Error updating layer orders:", error);
    return NextResponse.json(
      { error: "Failed to update layer orders" },
      { status: 500 }
    );
  }
}
