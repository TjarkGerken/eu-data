import { supabase } from "./supabase";
import { ImageCategory, ImageScenario } from "./blob-config";

export interface ImageMetadata {
  id: string;
  category: ImageCategory;
  scenario?: ImageScenario;
  description: string;
  uploadedAt: Date;
  size: number;
}

export interface SupabaseImage {
  url: string;
  path: string;
  metadata?: ImageMetadata;
}

export class SupabaseImageManager {
  private static BUCKET = "climate-images";

  static async uploadImage(
    file: File,
    metadata: Omit<ImageMetadata, "uploadedAt" | "size">
  ): Promise<{ url: string; metadata: ImageMetadata }> {
    const fileExt = file.name.split(".").pop();
    const filename = `${metadata.category}/${metadata.scenario || "default"}/${
      metadata.id
    }.${fileExt}`;

    const { data: uploadData, error: uploadError } = await supabase.storage
      .from(this.BUCKET)
      .upload(filename, file, {
        cacheControl: "3600",
        upsert: true,
      });

    if (uploadError) {
      throw new Error(`Failed to upload image: ${uploadError.message}`);
    }

    const {
      data: { publicUrl },
    } = supabase.storage.from(this.BUCKET).getPublicUrl(filename);

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
  ): Promise<SupabaseImage[]> {
    const { data: files, error } = await supabase.storage
      .from(this.BUCKET)
      .list(category, {
        limit: 100,
        sortBy: { column: "name", order: "asc" },
      });

    if (error) {
      throw new Error(`Failed to list images: ${error.message}`);
    }

    if (!files) return [];

    const images = await Promise.all(
      files
        .filter((file) => !file.name.endsWith(".json"))
        .map(async (file) => {
          const fullPath = `${category}/${file.name}`;
          const {
            data: { publicUrl },
          } = supabase.storage.from(this.BUCKET).getPublicUrl(fullPath);

          const id = file.name.split(".")[0];
          const metadata = await this.getMetadata(id);

          return {
            url: publicUrl,
            path: fullPath,
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
  ): Promise<SupabaseImage | null> {
    const searchPath = scenario ? `${category}/${scenario}` : category;

    const { data: files, error } = await supabase.storage
      .from(this.BUCKET)
      .list(searchPath, {
        limit: 100,
      });

    if (error || !files) return null;

    const matchingFile = files.find(
      (file) => file.name.startsWith(`${id}.`) && !file.name.endsWith(".json")
    );

    if (!matchingFile) return null;

    const fullPath = `${searchPath}/${matchingFile.name}`;
    const {
      data: { publicUrl },
    } = supabase.storage.from(this.BUCKET).getPublicUrl(fullPath);

    const metadata = await this.getMetadata(id);

    return {
      url: publicUrl,
      path: fullPath,
      metadata,
    };
  }

  static async deleteImage(path: string): Promise<void> {
    const { error } = await supabase.storage.from(this.BUCKET).remove([path]);

    if (error) {
      throw new Error(`Failed to delete image: ${error.message}`);
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

  static async getAllImages(): Promise<SupabaseImage[]> {
    const categories: ImageCategory[] = [
      "risk",
      "exposition",
      "hazard",
      "combined",
    ];
    const allImages: SupabaseImage[] = [];

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
      const metadataBlob = new Blob([JSON.stringify(metadata)], {
        type: "application/json",
      });

      const { error } = await supabase.storage
        .from(this.BUCKET)
        .upload(metadataPath, metadataBlob, {
          cacheControl: "3600",
          upsert: true,
        });

      if (error) {
        throw new Error(`Failed to save metadata: ${error.message}`);
      }
    } catch (error) {
      console.warn("Failed to save metadata:", error);
    }
  }

  private static async getMetadata(
    id: string
  ): Promise<ImageMetadata | undefined> {
    try {
      const metadataPath = `metadata/${id}.json`;

      const { data, error } = await supabase.storage
        .from(this.BUCKET)
        .download(metadataPath);

      if (error || !data) return undefined;

      const text = await data.text();
      const metadata = JSON.parse(text);

      return {
        ...metadata,
        uploadedAt: new Date(metadata.uploadedAt),
      };
    } catch (error) {
      console.warn("Failed to load metadata:", error);
      return undefined;
    }
  }

  private static async deleteMetadata(id: string): Promise<void> {
    const metadataPath = `metadata/${id}.json`;

    const { error } = await supabase.storage
      .from(this.BUCKET)
      .remove([metadataPath]);

    if (error) {
      throw new Error(`Failed to delete metadata: ${error.message}`);
    }
  }
}
