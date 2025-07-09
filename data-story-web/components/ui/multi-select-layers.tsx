"use client";

import { useState } from "react";
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
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { MapLayerMetadata } from "@/lib/map-tile-service";

interface MultiSelectLayersProps {
  layers: MapLayerMetadata[];
  selectedLayerIds: string[];
  onSelectionChange: (layerIds: string[]) => void;
  placeholder?: string;
  className?: string;
  groupByEconomicIndicator?: boolean;
}

export function MultiSelectLayers({
  layers,
  selectedLayerIds,
  onSelectionChange,
  placeholder = "Select layers...",
  className,
  groupByEconomicIndicator = false,
}: MultiSelectLayersProps) {
  const [isOpen, setIsOpen] = useState(false);

  const selectedLayers = layers.filter((layer) =>
    selectedLayerIds.includes(layer.id)
  );

  const handleLayerToggle = (layerId: string) => {
    const newSelection = selectedLayerIds.includes(layerId)
      ? selectedLayerIds.filter((id) => id !== layerId)
      : [...selectedLayerIds, layerId];

    onSelectionChange(newSelection);
  };

  const removeLayer = (layerId: string) => {
    onSelectionChange(selectedLayerIds.filter((id) => id !== layerId));
  };

  // Simplified keyword-based grouping
  const getEconomicIndicatorForLayer = (layerName: string): string | null => {
    const name = layerName.toLowerCase();
    
    if (name.includes('freight')) return 'Freight';
    if (name.includes('gdp')) return 'GDP';
    if (name.includes('hrst')) return 'HRST';
    if (name.includes('population')) return 'Population';
    if (name.includes('combined')) return 'Combined';
    
    return null;
  };

  const getEconomicIndicatorIcon = (indicator: string): string => {
    const iconMap: { [key: string]: string } = {
      Combined: "📊",
      Freight: "🚛",
      Population: "👥",
      HRST: "🔬",
      GDP: "💰",
    };
    return iconMap[indicator] || "📊";
  };

  // Extract SLR scenario from layer name
  const getSLRScenario = (layerName: string): string | null => {
    const name = layerName.toLowerCase();
    
    // Match both "SLR 0", "SLR-0", "SLR 1", "SLR-1", etc.
    const slrMatch = name.match(/slr[-\s]?(\d+)/);
    if (slrMatch) {
      return `SLR ${slrMatch[1]}`;
    }
    
    return null;
  };

  const groupedLayers = () => {
    if (!groupByEconomicIndicator) {
      return { "All Layers": layers };
    }

    // Create nested structure: Economic Indicator -> SLR Scenarios -> Layers
    const nestedGroups: { [indicator: string]: { [scenario: string]: MapLayerMetadata[] } } = {};
    const otherLayers: MapLayerMetadata[] = [];

    layers.forEach((layer) => {
      const indicator = getEconomicIndicatorForLayer(layer.name);
      const slrScenario = getSLRScenario(layer.name) || "No SLR";
      
      if (indicator) {
        if (!nestedGroups[indicator]) {
          nestedGroups[indicator] = {};
        }
        if (!nestedGroups[indicator][slrScenario]) {
          nestedGroups[indicator][slrScenario] = [];
        }
        nestedGroups[indicator][slrScenario].push(layer);
      } else {
        otherLayers.push(layer);
      }
    });

    // Flatten for Command component (since Command doesn't support true nesting)
    const flattenedGroups: { [key: string]: MapLayerMetadata[] } = {};
    const economicIndicators = ["Combined", "Freight", "Population", "HRST", "GDP"];
    
    economicIndicators.forEach((indicator) => {
      if (nestedGroups[indicator]) {
        // Always add main indicator header (empty if no non-SLR layers)
        flattenedGroups[`${indicator}__header`] = [];
        
        const scenarios = Object.keys(nestedGroups[indicator]).sort((a, b) => {
          // Sort so "No SLR" comes first, then SLR scenarios numerically
          if (a === "No SLR") return -1;
          if (b === "No SLR") return 1;
          const aNum = parseInt(a.replace("SLR ", ""));
          const bNum = parseInt(b.replace("SLR ", ""));
          return aNum - bNum;
        });
        
        scenarios.forEach((scenario) => {
          if (nestedGroups[indicator][scenario].length > 0) {
            if (scenario === "No SLR") {
              // Add non-SLR layers directly under the main indicator
              flattenedGroups[`${indicator}__header`] = nestedGroups[indicator][scenario];
            } else {
              // Add SLR scenarios as subgroups
              flattenedGroups[`${indicator} → ${scenario}`] = nestedGroups[indicator][scenario];
            }
          }
        });
      }
    });
    
    // Add other layers at the end
    if (otherLayers.length > 0) {
      flattenedGroups["Other Layers"] = otherLayers;
    }

    return flattenedGroups;
  };

  return (
    <div className={cn("w-full", className)}>
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogTrigger asChild>
          <Button
            variant="outline"
            className="w-full justify-start h-auto min-h-[40px] p-2 text-left"
          >
            <div className="flex flex-wrap gap-1 flex-1 min-h-[24px]">
              {selectedLayers.length === 0 ? (
                <span className="text-muted-foreground text-sm">
                  {placeholder}
                </span>
              ) : (
                selectedLayers.map((layer) => {
                  const indicator = getEconomicIndicatorForLayer(layer.name);
                  return (
                    <Badge
                      key={layer.id}
                      variant="secondary"
                      className="text-xs"
                    >
                      {indicator && (
                        <span className="mr-1">
                          {getEconomicIndicatorIcon(indicator)}
                        </span>
                      )}
                      {layer.name}
                      <span
                        className="ml-1 hover:bg-destructive hover:text-destructive-foreground rounded-full p-0.5 transition-colors cursor-pointer"
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          removeLayer(layer.id);
                        }}
                      >
                        <X className="h-3 w-3" />
                      </span>
                    </Badge>
                  );
                })
              )}
            </div>
            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </DialogTrigger>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-hidden">
          <DialogHeader>
            <DialogTitle>Select Layers</DialogTitle>
          </DialogHeader>
          <div className="flex-1 overflow-hidden">
            <Command className="h-full">
              <CommandInput placeholder="Search layers..." />
              <CommandList className="max-h-[60vh] overflow-y-auto">
                <CommandEmpty>No layers found.</CommandEmpty>
                {Object.entries(groupedLayers()).map(([groupName, groupLayers]) => {
                  const isNestedGroup = groupName.includes(' → ');
                  const isHeaderGroup = groupName.includes('__header');
                  const parts = groupName.split(' → ');
                  const economicIndicator = isHeaderGroup ? groupName.replace('__header', '') : parts[0];
                  const slrScenario = parts[1];
                  
                  return (
                    <CommandGroup key={groupName} heading={
                      <div className="flex items-center gap-2">
                        {isNestedGroup ? (
                          // SLR scenario subgroup with indentation
                          <div className="flex items-center gap-2 ml-6">
                            <span className="text-xs text-muted-foreground">└─</span>
                            <span className="text-sm font-mono bg-blue-50 text-blue-700 px-2 py-0.5 rounded">
                              {slrScenario}
                            </span>
                            <Badge variant="outline" className="text-xs">
                              {groupLayers.length}
                            </Badge>
                          </div>
                        ) : (
                          // Main economic indicator group
                          <div className="flex items-center gap-2">
                            {groupByEconomicIndicator && economicIndicator !== "Other Layers" && (
                              <span>{getEconomicIndicatorIcon(economicIndicator)}</span>
                            )}
                            <span className="font-medium">
                              {isHeaderGroup ? economicIndicator : groupName}
                            </span>
                            {groupLayers.length > 0 && (
                              <Badge variant="outline" className="text-xs">
                                {groupLayers.length}
                              </Badge>
                            )}
                          </div>
                        )}
                      </div>
                    }>
                      {groupLayers.map((layer) => (
                        <CommandItem
                          key={layer.id}
                          value={layer.name}
                          onSelect={() => handleLayerToggle(layer.id)}
                          className={isNestedGroup ? "ml-8" : ""}
                        >
                          <Check
                            className={cn(
                              "mr-2 h-4 w-4",
                              selectedLayerIds.includes(layer.id)
                                ? "opacity-100"
                                : "opacity-0"
                            )}
                          />
                          <div className="flex-1 min-w-0">
                            <div className="font-medium text-sm line-clamp-1">
                              {layer.name}
                            </div>
                            <div className="text-xs text-muted-foreground">
                              {layer.dataType} • {layer.format}
                            </div>
                            <div className="text-xs text-muted-foreground">
                              Range: {layer.valueRange[0].toFixed(2)} - {layer.valueRange[1].toFixed(2)}
                            </div>
                          </div>
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  );
                })}
              </CommandList>
            </Command>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}