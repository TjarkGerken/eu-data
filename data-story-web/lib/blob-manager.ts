import {
  S3Client,
  PutObjectCommand,
  GetObjectCommand,
  DeleteObjectCommand,
  ListObjectsV2Command,
} from "@aws-sdk/client-s3";
import { ImageCategory, ImageScenario } from "./blob-config";
import { R2_CONFIG, R2_BUCKET_NAME, R2_PUBLIC_URL_BASE } from "./r2-config";

export interface ImageMetadata {
  id: string;
  category: ImageCategory;
  scenario?: ImageScenario;
  indicators?: string[];
  alt?: {
    en: string;
    de: string;
  };
  caption?: {
    en: string;
    de: string;
  };
  uploadedAt: Date;
  size: number;
}

export interface CloudflareR2Image {
  url: string;
  path: string;
  metadata?: ImageMetadata;
}

interface ApiFileResponse {
  id: string;
  name: string;
  url: string;
  path: string;
  category: string;
  scenario: string;
  indicators: string[];
  alt: { en: string; de: string };
  caption: { en: string; de: string };
  size: number;
  created_at?: string;
}

export class CloudflareR2Manager {
  private static s3Client = new S3Client(R2_CONFIG);

  static async uploadImage(
    file: File,
    metadata: Omit<ImageMetadata, "uploadedAt" | "size">,
  ): Promise<{ url: string; metadata: ImageMetadata }> {
    const fileExt = file.name.split(".").pop();
    const filename = `${metadata.category}/${metadata.scenario || "default"}/${
      metadata.id
    }.${fileExt}`;

    const buffer = Buffer.from(await file.arrayBuffer());

    const command = new PutObjectCommand({
      Bucket: R2_BUCKET_NAME,
      Key: filename,
      Body: buffer,
      ContentType: file.type || "application/octet-stream",
      CacheControl: "public, max-age=31536000, immutable",
    });

    try {
      await this.s3Client.send(command);
    } catch (error) {
      throw new Error(`Failed to upload image: ${error}`);
    }

    const publicUrl = `${R2_PUBLIC_URL_BASE}/${filename}`;

    const fullMetadata: ImageMetadata = {
      ...metadata,
      uploadedAt: new Date(),
      size: file.size,
    };

    await this.saveMetadata(metadata.id, fullMetadata);

    return { url: publicUrl, metadata: fullMetadata };
  }

  static async getAllImages(): Promise<
    Array<{ url: string; path: string; metadata: ImageMetadata }>
  > {
    // In the browser we call the public API route instead of using the
    // AWS SDK (which would expose credentials). On the server we keep the
    // original direct R2 request for efficiency.
    if (typeof window !== "undefined") {
      try {
        const res = await fetch("/api/storage/upload", {
          method: "GET",
        });
        if (!res.ok) throw new Error("Failed to fetch images");
        // Response shape: { files: [{ url, path, category, scenario, size, created_at }] }
        const { files } = await res.json();
        return (files as ApiFileResponse[]).map((f) => ({
          url: f.url,
          path:
            f.path ||
            (f.url ? f.url.replace(/^https?:\/\/[^\/]+\//, "") : f.url), // extract key from URL if path missing
          metadata: {
            id: f.id || f.name,
            category: f.category as ImageCategory,
            scenario: f.scenario as ImageScenario,
            indicators: (f.indicators || []) as string[],
            alt: f.alt || { en: "", de: "" },
            caption: f.caption || { en: "", de: "" },
            uploadedAt: f.created_at ? new Date(f.created_at) : new Date(),
            size: f.size ?? 0,
          },
        }));
      } catch (err) {
        console.error("Failed to fetch images via API:", err);
        return [];
      }
    }

    // -------- Server-side path (unchanged) --------
    try {
      const command = new ListObjectsV2Command({
        Bucket: R2_BUCKET_NAME,
        Prefix: "climate-images/",
        MaxKeys: 1000,
      });

      const response = await this.s3Client.send(command);

      if (!response.Contents) {
        return [];
      }

      return await Promise.all(
        response.Contents.filter(
          (object) => object.Key && !object.Key.endsWith(".json"),
        ).map(async (object) => {
          const publicUrl = `${R2_PUBLIC_URL_BASE}/${object.Key}`;
          const pathParts = object.Key!.split("/");
          const fileName = pathParts[pathParts.length - 1];
          const fileNameWithoutExt = fileName.split(".")[0];

          // Attempt to fetch metadata JSON for richer information
          let meta: ImageMetadata | undefined;
          try {
            meta = await this.getMetadata(fileNameWithoutExt);
          } catch {
            /* ignore */
          }

          return {
            url: publicUrl,
            path: object.Key!,
            metadata: {
              id: fileNameWithoutExt,
              category:
                (meta?.category as ImageCategory) ||
                (pathParts[1] as ImageCategory),
              scenario:
                (meta?.scenario as ImageScenario) ||
                (pathParts[2] && pathParts[2] !== "default"
                  ? (pathParts[2] as ImageScenario)
                  : undefined),
              indicators: meta?.indicators || [],
              alt: (meta?.alt as { en: string; de: string }) || {
                en: "",
                de: "",
              },
              caption: (meta?.caption as { en: string; de: string }) || {
                en: `Climate visualization: ${fileNameWithoutExt}`,
                de: "",
              },
              uploadedAt: object.LastModified || new Date(),
              size: object.Size || 0,
            },
          };
        }),
      );
    } catch (error) {
      console.error("Failed to get all images:", error);
      return [];
    }
  }

  static async getImagesByCategory(
    category: ImageCategory,
  ): Promise<Array<{ url: string; path: string; metadata: ImageMetadata }>> {
    try {
      const command = new ListObjectsV2Command({
        Bucket: R2_BUCKET_NAME,
        Prefix: `climate-images/${category}/`,
        MaxKeys: 1000,
      });

      const response = await this.s3Client.send(command);

      if (!response.Contents) {
        return [];
      }

      return await Promise.all(
        response.Contents.filter(
          (object) => object.Key && !object.Key.endsWith(".json"),
        ).map(async (object) => {
          const publicUrl = `${R2_PUBLIC_URL_BASE}/${object.Key}`;
          const pathParts = object.Key!.split("/");
          const fileName = pathParts[pathParts.length - 1];
          const fileNameWithoutExt = fileName.split(".")[0];

          // Attempt to fetch metadata JSON for richer information
          let meta: ImageMetadata | undefined;
          try {
            meta = await this.getMetadata(fileNameWithoutExt);
          } catch {
            /* ignore */
          }

          return {
            url: publicUrl,
            path: object.Key!,
            metadata: {
              id: fileNameWithoutExt,
              category: (meta?.category as ImageCategory) || category,
              scenario:
                (meta?.scenario as ImageScenario) ||
                (pathParts[2] && pathParts[2] !== "default"
                  ? (pathParts[2] as ImageScenario)
                  : undefined),
              indicators: meta?.indicators || [],
              alt: (meta?.alt as { en: string; de: string }) || {
                en: "",
                de: "",
              },
              caption: (meta?.caption as { en: string; de: string }) || {
                en: `Climate visualization: ${fileNameWithoutExt}`,
                de: "",
              },
              uploadedAt: object.LastModified || new Date(),
              size: object.Size || 0,
            },
          };
        }),
      );
    } catch (error) {
      console.error(`Failed to get images for category ${category}:`, error);
      return [];
    }
  }

  static async deleteImage(imagePath: string): Promise<void> {
    // When running in the browser, call the API route to perform deletion.
    if (typeof window !== "undefined") {
      const res = await fetch("/api/storage/upload", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: imagePath }),
      });
      if (!res.ok) {
        throw new Error("Failed to delete image via API");
      }
      return;
    }

    // Server-side direct deletion (unchanged)
    try {
      const command = new DeleteObjectCommand({
        Bucket: R2_BUCKET_NAME,
        Key: imagePath,
      });

      await this.s3Client.send(command);

      // Also delete metadata file if present
      const metadataPath = imagePath.replace(/\.[^/.]+$/, ".json");
      try {
        const metadataCommand = new DeleteObjectCommand({
          Bucket: R2_BUCKET_NAME,
          Key: metadataPath,
        });
        await this.s3Client.send(metadataCommand);
      } catch {
        /* ignore */
      }
    } catch (error) {
      throw new Error(`Failed to delete image: ${error}`);
    }
  }

  private static async saveMetadata(
    imageId: string,
    metadata: ImageMetadata,
  ): Promise<void> {
    const metadataKey = `metadata/${imageId}.json`;
    const metadataContent = JSON.stringify(metadata, null, 2);

    const command = new PutObjectCommand({
      Bucket: R2_BUCKET_NAME,
      Key: metadataKey,
      Body: metadataContent,
      ContentType: "application/json",
      CacheControl: "public, max-age=3600",
    });

    try {
      await this.s3Client.send(command);
    } catch (error) {
      console.error("Failed to save metadata:", error);
    }
  }

  static async getImageByIdAndCategory(
    id: string,
    category: ImageCategory,
    scenario?: ImageScenario,
  ): Promise<CloudflareR2Image | null> {
    const searchPrefix = scenario ? `${category}/${scenario}/` : `${category}/`;

    const command = new ListObjectsV2Command({
      Bucket: R2_BUCKET_NAME,
      Prefix: searchPrefix,
      MaxKeys: 100,
    });

    try {
      const response = await this.s3Client.send(command);

      if (!response.Contents) return null;

      const matchingObject = response.Contents.find(
        (object) =>
          object.Key &&
          object.Key.includes(`${id}.`) &&
          !object.Key.endsWith(".json"),
      );

      if (!matchingObject?.Key) return null;

      const publicUrl = `${R2_PUBLIC_URL_BASE}/${matchingObject.Key}`;
      const id_extracted = matchingObject.Key.split("/").pop()?.split(".")[0];
      const metadata = id_extracted
        ? await this.getMetadata(id_extracted)
        : undefined;

      return {
        url: publicUrl,
        path: matchingObject.Key,
        metadata,
      };
    } catch (error) {
      console.error("Error fetching image:", error);
      return null;
    }
  }

  private static async getMetadata(
    id: string,
  ): Promise<ImageMetadata | undefined> {
    try {
      const metadataPath = `metadata/${id}.json`;

      const command = new GetObjectCommand({
        Bucket: R2_BUCKET_NAME,
        Key: metadataPath,
      });

      const response = await this.s3Client.send(command);

      if (response.Body) {
        const metadataStr = await response.Body.transformToString();
        return JSON.parse(metadataStr);
      }
    } catch (error) {
      console.warn("Failed to get metadata:", error);
    }

    return undefined;
  }
}
