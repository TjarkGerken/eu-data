import { NextResponse } from "next/server";
import { BlobAnalytics } from "@/lib/blob-analytics";

export async function GET() {
  try {
    const [usageStats, cachePerformance] = await Promise.all([
      BlobAnalytics.getUsageStats(),
      BlobAnalytics.getCachePerformance(),
    ]);

    return NextResponse.json({
      usage: usageStats,
      performance: cachePerformance,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Stats retrieval error:", error);
    return NextResponse.json(
      { error: "Failed to retrieve stats" },
      { status: 500 }
    );
  }
}
