"use client";

import { useState, useEffect } from "react";
import Image from "next/image";
import { SupabaseImage } from "@/lib/blob-manager";
import { ImageCategory, ImageScenario } from "@/lib/blob-config";
import { SupabaseAnalytics } from "@/lib/blob-analytics";

interface ClimateImageProps {
  category: ImageCategory;
  scenario?: ImageScenario;
  id?: string;
  alt: string;
  className?: string;
  priority?: boolean;
  fill?: boolean;
  width?: number;
  height?: number;
}

export default function ClimateImage({
  category,
  scenario,
  id,
  alt,
  className,
  priority = false,
  fill = true,
  width,
  height,
}: ClimateImageProps) {
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadImage() {
      try {
        let targetImage: SupabaseImage | null = null;

        // Use API routes instead of direct blob manager calls
        const response = await fetch(`/api/images/${category}`);
        if (!response.ok) {
          throw new Error("Failed to fetch images");
        }

        const data = await response.json();
        const images = data.images as SupabaseImage[];

        if (id) {
          targetImage =
            images.find(
              (img) =>
                img.metadata?.id === id &&
                (!scenario || img.metadata?.scenario === scenario)
            ) || null;
        } else {
          targetImage =
            images.find(
              (img) => !scenario || img.metadata?.scenario === scenario
            ) ||
            images[0] ||
            null;
        }

        if (targetImage) {
          setImageUrl(targetImage.url);

          // Track analytics
          SupabaseAnalytics.trackImageView(
            targetImage.url,
            category,
            scenario,
            {
              userAgent: navigator.userAgent,
              referrer: document.referrer,
            }
          );
        } else {
          setError(
            `No image found for ${category}${scenario ? ` - ${scenario}` : ""}${
              id ? ` (${id})` : ""
            }`
          );
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load image");
      } finally {
        setLoading(false);
      }
    }

    loadImage();
  }, [category, scenario, id]);

  if (loading) {
    return (
      <div
        className={`animate-pulse bg-gray-200 rounded ${className || ""}`}
        style={{ aspectRatio: "16/9", width: width, height: height }}
      />
    );
  }

  if (error || !imageUrl) {
    return (
      <div
        className={`bg-gray-100 rounded p-4 text-center text-gray-500 ${
          className || ""
        }`}
      >
        {error || "Image not available"}
      </div>
    );
  }

  const imageProps = {
    src: imageUrl,
    alt,
    className,
    priority,
    sizes: "(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw",
  };

  if (fill) {
    return <Image {...imageProps} fill />;
  }

  return <Image {...imageProps} width={width || 800} height={height || 450} />;
}
