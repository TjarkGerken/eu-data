import { put, list, del } from "@vercel/blob";
import { ImageCategory, ImageScenario } from "./blob-config";

export interface ImageMetadata {
  id: string;
  category: ImageCategory;
  scenario?: ImageScenario;
  description: string;
  uploadedAt: Date;
  size: number;
}

export interface BlobImage {
  url: string;
  pathname: string;
  downloadUrl: string;
  metadata?: ImageMetadata;
}

export class BlobImageManager {
  private static PREFIX = "climate-data";

  static async uploadImage(
    file: File,
    metadata: Omit<ImageMetadata, "uploadedAt" | "size">
  ): Promise<{ url: string; metadata: ImageMetadata }> {
    const filename = `${this.PREFIX}/${metadata.category}/${
      metadata.id
    }.${file.name.split(".").pop()}`;

    const blob = await put(filename, file, {
      access: "public",
      addRandomSuffix: false,
      token: process.env.BLOB_READ_WRITE_TOKEN,
    });

    const fullMetadata: ImageMetadata = {
      ...metadata,
      uploadedAt: new Date(),
      size: file.size,
    };

    await this.saveMetadata(blob.url, fullMetadata);

    return { url: blob.url, metadata: fullMetadata };
  }

  static async getImagesByCategory(
    category: ImageCategory
  ): Promise<BlobImage[]> {
    const { blobs } = await list({
      prefix: `${this.PREFIX}/${category}/`,
      token: process.env.BLOB_READ_WRITE_TOKEN,
    });

    const images = await Promise.all(
      blobs
        .filter((blob) => !blob.pathname.includes("/metadata/"))
        .map(async (blob) => {
          const metadata = await this.getMetadata(blob.pathname);
          return {
            url: blob.url,
            pathname: blob.pathname,
            downloadUrl: blob.downloadUrl,
            metadata,
          };
        })
    );

    return images;
  }

  static async getImageByIdAndCategory(
    id: string,
    category: ImageCategory,
    scenario?: ImageScenario
  ): Promise<BlobImage | null> {
    const images = await this.getImagesByCategory(category);
    return (
      images.find(
        (img) =>
          img.pathname.includes(`/${id}.`) &&
          (!scenario || img.metadata?.scenario === scenario)
      ) || null
    );
  }

  static async deleteImage(pathname: string): Promise<void> {
    await del(pathname, { token: process.env.BLOB_READ_WRITE_TOKEN });

    const metadataPath = pathname
      .replace(/\.[^/.]+$/, ".json")
      .replace(`/${this.PREFIX}/`, `/${this.PREFIX}/metadata/`);
    try {
      await del(metadataPath, { token: process.env.BLOB_READ_WRITE_TOKEN });
    } catch (error) {
      console.warn("Failed to delete metadata:", error);
    }
  }

  static async getAllImages(): Promise<BlobImage[]> {
    const { blobs } = await list({
      prefix: this.PREFIX,
      token: process.env.BLOB_READ_WRITE_TOKEN,
    });

    const images = await Promise.all(
      blobs
        .filter((blob) => !blob.pathname.includes("/metadata/"))
        .map(async (blob) => {
          const metadata = await this.getMetadata(blob.pathname);
          return {
            url: blob.url,
            pathname: blob.pathname,
            downloadUrl: blob.downloadUrl,
            metadata,
          };
        })
    );

    return images;
  }

  private static async saveMetadata(
    imageUrl: string,
    metadata: ImageMetadata
  ): Promise<void> {
    const metadataPath = `${this.PREFIX}/metadata/${metadata.id}.json`;

    try {
      await put(metadataPath, JSON.stringify(metadata), {
        access: "public",
        token: process.env.BLOB_READ_WRITE_TOKEN,
      });
    } catch (error) {
      console.warn("Failed to save metadata:", error);
    }
  }

  private static async getMetadata(
    pathname: string
  ): Promise<ImageMetadata | undefined> {
    try {
      const id = pathname.split("/").pop()?.split(".")[0];
      if (!id) return undefined;

      const { blobs } = await list({
        prefix: `${this.PREFIX}/metadata/${id}.json`,
        token: process.env.BLOB_READ_WRITE_TOKEN,
      });
      if (blobs.length === 0) return undefined;

      const response = await fetch(blobs[0].downloadUrl);
      const metadata = await response.json();

      return {
        ...metadata,
        uploadedAt: new Date(metadata.uploadedAt),
      };
    } catch (error) {
      console.warn("Failed to load metadata:", error);
      return undefined;
    }
  }
}
