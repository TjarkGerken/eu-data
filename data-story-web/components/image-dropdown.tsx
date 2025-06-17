"use client";

import { useState, useEffect } from "react";
import { Check, ChevronsUpDown, Image as ImageIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Badge } from "@/components/ui/badge";
import { ImageOption } from "@/lib/types";

interface ImageDropdownProps {
  selectedImageId?: string;
  onImageChange: (
    imageId: string,
    imageData?: { category: string; scenario?: string }
  ) => void;
  placeholder?: string;
  disabled?: boolean;
  category?: string;
}

export function ImageDropdown({
  selectedImageId,
  onImageChange,
  placeholder = "Select image...",
  disabled = false,
  category,
}: ImageDropdownProps) {
  const [open, setOpen] = useState(false);
  const [images, setImages] = useState<ImageOption[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadImages();
  }, [category]);

  const loadImages = async () => {
    try {
      const categories = ["hazard", "risk", "exposition", "combined"];
      const imagePromises = categories.map(async (cat) => {
        try {
          const response = await fetch(`/api/images/${cat}`);
          const data = await response.json();
          return (
            data.images
              ?.map((img: any) => {
                const filename = img.pathname?.split("/").pop() || "";
                const nameWithoutExt = filename.replace(/\.[^/.]+$/, "");
                return {
                  id:
                    nameWithoutExt ||
                    img.metadata?.id ||
                    `${cat}-${Math.random()}`,
                  name: filename || "Unknown Image",
                  url: img.url,
                  category: cat,
                  scenario: filename?.includes("current")
                    ? "current"
                    : filename?.includes("severe")
                    ? "severe"
                    : undefined,
                };
              })
              .filter((img) => img.name !== "Unknown Image" && img.url) || []
          );
        } catch (error) {
          console.error(`Failed to load images for category ${cat}:`, error);
          return [];
        }
      });

      const allImages = (await Promise.all(imagePromises)).flat();
      setImages(allImages);
    } catch (error) {
      console.error("Failed to load images:", error);
    } finally {
      setLoading(false);
    }
  };

  const selectedImage = images.find((img) => img.id === selectedImageId);

  if (loading) {
    return (
      <Button variant="outline" disabled className="w-full justify-between">
        Loading images...
        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
      </Button>
    );
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-full justify-between h-auto min-h-[40px]"
          disabled={disabled}
        >
          <div className="flex items-center gap-2 flex-1 min-w-0">
            {selectedImage ? (
              <>
                <img
                  src={selectedImage.url}
                  alt={selectedImage.name}
                  className="w-8 h-6 object-cover rounded border"
                />
                <div className="flex flex-col items-start min-w-0">
                  <span className="text-sm truncate">{selectedImage.name}</span>
                  <div className="flex gap-1">
                    <Badge variant="secondary" className="text-xs">
                      {selectedImage.category}
                    </Badge>
                    {selectedImage.scenario && (
                      <Badge variant="outline" className="text-xs">
                        {selectedImage.scenario}
                      </Badge>
                    )}
                  </div>
                </div>
              </>
            ) : (
              <>
                <ImageIcon className="h-4 w-4 text-muted-foreground" />
                <span className="text-muted-foreground">{placeholder}</span>
              </>
            )}
          </div>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[500px] p-0">
        <Command>
          <CommandInput placeholder="Search images..." />
          <CommandList>
            <CommandEmpty>No images found.</CommandEmpty>
            <CommandGroup>
              {images.map((image) => (
                <CommandItem
                  key={image.id}
                  value={`${image.name} ${image.category} ${
                    image.scenario || ""
                  }`}
                  onSelect={() => {
                    onImageChange(image.id, {
                      category: image.category,
                      scenario: image.scenario,
                    });
                    setOpen(false);
                  }}
                  className="flex items-center gap-3 p-3"
                >
                  <Check
                    className={cn(
                      "h-4 w-4 shrink-0",
                      selectedImageId === image.id ? "opacity-100" : "opacity-0"
                    )}
                  />
                  <img
                    src={image.url}
                    alt={image.name}
                    className="w-16 h-12 object-cover rounded border shrink-0"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm">{image.name}</p>
                    <div className="flex gap-1 mt-1">
                      <Badge variant="secondary" className="text-xs">
                        {image.category}
                      </Badge>
                      {image.scenario && (
                        <Badge variant="outline" className="text-xs">
                          {image.scenario}
                        </Badge>
                      )}
                    </div>
                  </div>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
