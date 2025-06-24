"use client";

import { useState, useEffect } from "react";
import { Check, ChevronsUpDown, X } from "lucide-react";
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
import { supabase, type ContentReference } from "@/lib/supabase";

interface MultiSelectReferencesProps {
  selectedReferenceIds: string[];
  onSelectionChange: (referenceIds: string[]) => void;
  placeholder?: string;
  className?: string;
}

export function MultiSelectReferences({
  selectedReferenceIds,
  onSelectionChange,
  placeholder = "Select references...",
  className,
}: MultiSelectReferencesProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [references, setReferences] = useState<ContentReference[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    loadReferences();
  }, []);

  const loadReferences = async () => {
    try {
      const { data, error } = await supabase
        .from("content_references")
        .select("*")
        .order("title", { ascending: true });

      if (error) throw error;
      setReferences(data || []);
    } catch (error) {
      console.error("Error loading references:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const selectedReferences = references.filter((ref) =>
    selectedReferenceIds.includes(ref.id)
  );

  const filteredReferences = references.filter(
    (ref) =>
      ref.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ref.authors.some((author) =>
        author.toLowerCase().includes(searchQuery.toLowerCase())
      )
  );

  const handleReferenceToggle = (referenceId: string) => {
    const newSelection = selectedReferenceIds.includes(referenceId)
      ? selectedReferenceIds.filter((id) => id !== referenceId)
      : [...selectedReferenceIds, referenceId];

    onSelectionChange(newSelection);
  };

  const removeReference = (referenceId: string) => {
    onSelectionChange(selectedReferenceIds.filter((id) => id !== referenceId));
  };

  // const formatReferenceDisplay = (reference: ContentReference) => {
  //   return `${reference.title} (${reference.authors.join(", ")}, ${
  //     reference.year
  //   })`;
  // };

  const formatReferenceShort = (reference: ContentReference) => {
    const firstAuthor = reference.authors[0] || "Unknown";
    return `${firstAuthor} et al. (${reference.year})`;
  };

  return (
    <div className={cn("w-full", className)}>
      <Popover open={isOpen} onOpenChange={setIsOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            role="combobox"
            aria-expanded={isOpen}
            className="w-full justify-start h-auto min-h-[40px] p-2 text-left"
          >
            <div className="flex flex-wrap gap-1 flex-1 min-h-[24px]">
              {selectedReferences.length === 0 ? (
                <span className="text-muted-foreground text-sm">
                  {placeholder}
                </span>
              ) : (
                selectedReferences.map((reference) => (
                  <Badge
                    key={reference.id}
                    variant="secondary"
                    className="text-xs"
                  >
                    {formatReferenceShort(reference)}
                    <span
                      className="ml-1 hover:bg-destructive hover:text-destructive-foreground rounded-full p-0.5 transition-colors cursor-pointer"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        removeReference(reference.id);
                      }}
                    >
                      <X className="h-3 w-3" />
                    </span>
                  </Badge>
                ))
              )}
            </div>
            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-full p-0" align="start">
          <Command>
            <CommandInput
              placeholder="Search references..."
              value={searchQuery}
              onValueChange={setSearchQuery}
            />
            <CommandList>
              <CommandEmpty>
                {isLoading ? "Loading references..." : "No references found."}
              </CommandEmpty>
              <CommandGroup>
                {filteredReferences.map((reference) => (
                  <CommandItem
                    key={reference.id}
                    value={reference.id}
                    onSelect={() => handleReferenceToggle(reference.id)}
                  >
                    <Check
                      className={cn(
                        "mr-2 h-4 w-4",
                        selectedReferenceIds.includes(reference.id)
                          ? "opacity-100"
                          : "opacity-0"
                      )}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm line-clamp-1">
                        {reference.title}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {reference.authors.join(", ")} ({reference.year})
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {reference.type}{" "}
                        {reference.journal && `• ${reference.journal}`}
                      </div>
                    </div>
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
    </div>
  );
}
