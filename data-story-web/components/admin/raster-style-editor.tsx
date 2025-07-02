"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { 
  PREDEFINED_COLOR_SCHEMES, 
  getSchemesByCategory, 
  getAllCategories,
  createGradientFromStops,
  getDefaultSchemeForLayerType
} from "@/lib/color-schemes";
import { RasterColorScheme } from "@/lib/map-types";
import { Palette, Eye, RotateCcw } from "lucide-react";

interface RasterStyleEditorProps {
  layerName: string;
  layerType: string;
  currentScheme?: RasterColorScheme;
  onSchemeChange: (scheme: RasterColorScheme) => void;
  onReset?: () => void;
}

export function RasterStyleEditor({
  layerName,
  layerType,
  currentScheme,
  onSchemeChange,
  onReset
}: RasterStyleEditorProps) {
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  
  const categories = getAllCategories();
  const availableSchemes = selectedCategory === "all" 
    ? PREDEFINED_COLOR_SCHEMES 
    : getSchemesByCategory(selectedCategory);

  const handleSchemeSelect = (schemeId: string) => {
    const scheme = PREDEFINED_COLOR_SCHEMES.find(s => s.id === schemeId);
    if (scheme) {
      onSchemeChange(scheme);
    }
  };

  const handleReset = () => {
    const defaultScheme = getDefaultSchemeForLayerType(layerType);
    onSchemeChange(defaultScheme);
    if (onReset) onReset();
  };

  const ColorSchemePreview = ({ scheme }: { scheme: RasterColorScheme }) => (
    <div className="space-y-2">
      <div
        className="w-full h-6 rounded border"
        style={{
          background: createGradientFromStops(scheme.colors)
        }}
      />
      <div className="flex flex-wrap gap-1">
        {scheme.colors.map((stop, index) => (
          <div
            key={index}
            className="w-4 h-4 rounded-sm border border-gray-300"
            style={{ backgroundColor: stop.color }}
            title={`${Math.round(stop.position * 100)}%: ${stop.color}`}
          />
        ))}
      </div>
    </div>
  );

  return (
    <Card className="w-full">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2">
          <Palette className="h-5 w-5" />
          Raster Color Scheme - {layerName}
        </CardTitle>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Current scheme preview */}
        {currentScheme && (
          <div className="space-y-2">
            <Label className="text-sm font-medium">Current Scheme</Label>
            <div className="p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium">{currentScheme.displayName}</span>
                <Badge variant="outline">{currentScheme.category}</Badge>
              </div>
              <ColorSchemePreview scheme={currentScheme} />
              <p className="text-xs text-muted-foreground mt-2">
                {currentScheme.description}
              </p>
            </div>
          </div>
        )}

        {/* Category filter */}
        <div className="space-y-2">
          <Label className="text-sm font-medium">Filter by Category</Label>
          <Select value={selectedCategory} onValueChange={setSelectedCategory}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Categories</SelectItem>
              {categories.map((category) => (
                <SelectItem key={category} value={category}>
                  {category.charAt(0).toUpperCase() + category.slice(1)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Available color schemes */}
        <div className="space-y-2">
          <Label className="text-sm font-medium">Available Color Schemes</Label>
          <div className="grid grid-cols-1 gap-3 max-h-96 overflow-y-auto">
            {availableSchemes.map((scheme) => (
              <div
                key={scheme.id}
                className={`p-3 border rounded-lg cursor-pointer transition-all hover:border-blue-500 ${
                  currentScheme?.id === scheme.id 
                    ? 'border-blue-500 bg-blue-50' 
                    : 'border-gray-200'
                }`}
                onClick={() => handleSchemeSelect(scheme.id)}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-sm">{scheme.displayName}</span>
                  <Badge variant="outline" className="text-xs">
                    {scheme.category}
                  </Badge>
                </div>
                <ColorSchemePreview scheme={scheme} />
                <p className="text-xs text-muted-foreground mt-2">
                  {scheme.description}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex gap-2 pt-4 border-t">
          <Button
            variant="outline"
            size="sm"
            onClick={handleReset}
            className="flex-1"
          >
            <RotateCcw className="h-4 w-4 mr-2" />
            Reset to Default
          </Button>
        </div>

        {/* Legend */}
        <div className="text-xs text-muted-foreground bg-gray-50 p-3 rounded-lg">
          <div className="flex items-center gap-2 mb-2">
            <Eye className="h-4 w-4" />
            <span className="font-medium">How to use:</span>
          </div>
          <ul className="space-y-1 ml-6">
            <li>• Click on any color scheme to apply it to your layer</li>
            <li>• Use category filters to find specific types of schemes</li>
            <li>• Color gradients show how data values map to colors</li>
            <li>• Reset button restores the default scheme for this layer type</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  );
} 