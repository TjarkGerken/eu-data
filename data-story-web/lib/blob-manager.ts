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
  description: string;
  uploadedAt: Date;
  size: number;
}

export interface CloudflareR2Image {
  url: string;
  path: string;
  metadata?: ImageMetadata;
}

export class CloudflareR2Manager {
  private static s3Client = new S3Client(R2_CONFIG);

  static async uploadImage(
    file: File,
    metadata: Omit<ImageMetadata, "uploadedAt" | "size">
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

  static async getImagesByCategory(
    category: ImageCategory
  ): Promise<CloudflareR2Image[]> {
    const command = new ListObjectsV2Command({
      Bucket: R2_BUCKET_NAME,
      Prefix: `${category}/`,
      MaxKeys: 100,
    });

    try {
      const response = await this.s3Client.send(command);

      if (!response.Contents) return [];

      const images = await Promise.all(
        response.Contents.filter(
          (object) => object.Key && !object.Key.endsWith(".json")
        ).map(async (object) => {
          const publicUrl = `${R2_PUBLIC_URL_BASE}/${object.Key}`;

          const pathParts = object.Key!.split("/");
          const fileName = pathParts[pathParts.length - 1];
          const id = fileName.split(".")[0];
          const metadata = await this.getMetadata(id);

          return {
            url: publicUrl,
            path: object.Key!,
            metadata,
          };
        })
      );

      return images;
    } catch (error) {
      throw new Error(`Failed to list images: ${error}`);
    }
  }

  static async getImageByIdAndCategory(
    id: string,
    category: ImageCategory,
    scenario?: ImageScenario
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
          !object.Key.endsWith(".json")
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

  static async deleteImage(path: string): Promise<void> {
    const command = new DeleteObjectCommand({
      Bucket: R2_BUCKET_NAME,
      Key: path,
    });

    try {
      await this.s3Client.send(command);
    } catch (error) {
      throw new Error(`Failed to delete image: ${error}`);
    }

    const id = path.split("/").pop()?.split(".")[0];
    if (id) {
      try {
        await this.deleteMetadata(id);
      } catch (error) {
        console.warn("Failed to delete metadata:", error);
      }
    }
  }

  static async getAllImages(): Promise<CloudflareR2Image[]> {
    const categories: ImageCategory[] = [
      "risk",
      "exposition",
      "hazard",
      "combined",
    ];
    const allImages: CloudflareR2Image[] = [];

    for (const category of categories) {
      try {
        const categoryImages = await this.getImagesByCategory(category);
        allImages.push(...categoryImages);
      } catch (error) {
        console.warn(`Failed to fetch images for category ${category}:`, error);
      }
    }

    return allImages;
  }

  private static async saveMetadata(
    id: string,
    metadata: ImageMetadata
  ): Promise<void> {
    const metadataPath = `metadata/${id}.json`;

    try {
      const metadataBuffer = Buffer.from(JSON.stringify(metadata));

      const command = new PutObjectCommand({
        Bucket: R2_BUCKET_NAME,
        Key: metadataPath,
        Body: metadataBuffer,
        ContentType: "application/json",
        CacheControl: "public, max-age=3600",
      });

      await this.s3Client.send(command);
    } catch (error) {
      console.warn("Failed to save metadata:", error);
    }
  }

  private static async getMetadata(
    id: string
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

  private static async deleteMetadata(id: string): Promise<void> {
    try {
      const metadataPath = `metadata/${id}.json`;

      const command = new DeleteObjectCommand({
        Bucket: R2_BUCKET_NAME,
        Key: metadataPath,
      });

      await this.s3Client.send(command);
    } catch (error) {
      console.warn("Failed to delete metadata:", error);
    }
  }
}
