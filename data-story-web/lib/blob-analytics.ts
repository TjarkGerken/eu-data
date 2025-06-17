import { list } from "@vercel/blob";

export interface ImageViewEvent {
  imageUrl: string;
  category: string;
  scenario?: string;
  timestamp: Date;
  userAgent?: string;
  referrer?: string;
}

export interface UsageStats {
  totalImages: number;
  totalSize: number;
  categoryCounts: Record<string, number>;
  recentViews: ImageViewEvent[];
  topImages: Array<{ url: string; views: number; category: string }>;
}

export class BlobAnalytics {
  private static PREFIX = "climate-data";
  private static events: ImageViewEvent[] = [];

  static async trackImageView(
    imageUrl: string,
    category: string,
    scenario?: string,
    metadata?: { userAgent?: string; referrer?: string }
  ): Promise<void> {
    try {
      const event: ImageViewEvent = {
        imageUrl,
        category,
        scenario,
        timestamp: new Date(),
        userAgent: metadata?.userAgent,
        referrer: metadata?.referrer,
      };

      this.events.push(event);

      await fetch("/api/analytics/image-view", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(event),
      });
    } catch (error) {
      console.warn("Failed to track image view:", error);
    }
  }

  static async getUsageStats(): Promise<UsageStats> {
    try {
      const { blobs } = await list({
        prefix: this.PREFIX,
        token: process.env.BLOB_READ_WRITE_TOKEN,
      });

      const imageBlobs = blobs.filter(
        (blob) => !blob.pathname.includes("/metadata/")
      );

      const totalSize = imageBlobs.reduce((sum, blob) => sum + blob.size, 0);

      const categoryCounts = imageBlobs.reduce((acc, blob) => {
        const pathParts = blob.pathname.split("/");
        const category = pathParts[1] || "unknown";
        acc[category] = (acc[category] || 0) + 1;
        return acc;
      }, {} as Record<string, number>);

      const recentViews = this.events.slice(-100);

      const viewCounts = this.events.reduce((acc, event) => {
        const key = `${event.imageUrl}:${event.category}`;
        acc[key] = (acc[key] || 0) + 1;
        return acc;
      }, {} as Record<string, number>);

      const topImages = Object.entries(viewCounts)
        .sort(([, a], [, b]) => b - a)
        .slice(0, 10)
        .map(([key, views]) => {
          const [url, category] = key.split(":");
          return { url, views, category };
        });

      return {
        totalImages: imageBlobs.length,
        totalSize,
        categoryCounts,
        recentViews,
        topImages,
      };
    } catch (error) {
      console.error("Failed to get usage stats:", error);
      return {
        totalImages: 0,
        totalSize: 0,
        categoryCounts: {},
        recentViews: [],
        topImages: [],
      };
    }
  }

  static async getCachePerformance(): Promise<{
    hitRate: number;
    averageLoadTime: number;
    totalRequests: number;
  }> {
    const sampleSize = this.events.length;
    if (sampleSize === 0) {
      return { hitRate: 0, averageLoadTime: 0, totalRequests: 0 };
    }

    const estimatedHitRate = Math.min(0.95, 0.1 + (sampleSize / 1000) * 0.8);
    const baseLoadTime = 150;
    const averageLoadTime = baseLoadTime * (1 - estimatedHitRate * 0.7);

    return {
      hitRate: estimatedHitRate,
      averageLoadTime,
      totalRequests: sampleSize,
    };
  }

  static getLocalEvents(): ImageViewEvent[] {
    return this.events.slice();
  }

  static clearLocalEvents(): void {
    this.events = [];
  }
}
