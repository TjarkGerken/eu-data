"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { VectorStyle, DEFAULT_VECTOR_STYLES } from "@/lib/map-types";
import { Shapes, RotateCcw, Eye } from "lucide-react";

interface VectorStyleEditorProps {
  layerName: string;
  layerType: string;
  currentStyle?: VectorStyle;
  onStyleChange: (style: VectorStyle) => void;
  onReset?: () => void;
}

const PREDEFINED_COLORS = [
  { name: "Transparent", value: "transparent" },
  { name: "White", value: "#ffffff" },
  { name: "Black", value: "#000000" },
  { name: "Red", value: "#ef4444" },
  { name: "Green", value: "#22c55e" },
  { name: "Blue", value: "#3b82f6" },
  { name: "Yellow", value: "#eab308" },
  { name: "Purple", value: "#a855f7" },
  { name: "Orange", value: "#f97316" },
  { name: "Pink", value: "#ec4899" },
  { name: "Cyan", value: "#06b6d4" },
  { name: "Gray", value: "#6b7280" },
];

const BORDER_STYLES = [
  { name: "Solid", value: undefined },
  { name: "Dashed", value: "5,5" },
  { name: "Dotted", value: "2,3" },
  { name: "Long Dash", value: "10,5" },
  { name: "Dash Dot", value: "8,3,2,3" },
];

export function VectorStyleEditor({
  layerName,
  layerType,
  currentStyle,
  onStyleChange,
  onReset,
}: VectorStyleEditorProps) {
  const [customFillColor, setCustomFillColor] = useState(
    currentStyle?.fillColor || "#3b82f6",
  );
  const [customBorderColor, setCustomBorderColor] = useState(
    currentStyle?.borderColor || "#ffffff",
  );

  const handleStyleUpdate = (updates: Partial<VectorStyle>) => {
    const updatedStyle: VectorStyle = {
      fillColor: currentStyle?.fillColor || "#3b82f6",
      fillOpacity: currentStyle?.fillOpacity || 0.6,
      borderColor: currentStyle?.borderColor || "#ffffff",
      borderWidth: currentStyle?.borderWidth || 2,
      borderOpacity: currentStyle?.borderOpacity || 1.0,
      borderDashArray: currentStyle?.borderDashArray,
      ...updates,
    };
    onStyleChange(updatedStyle);
  };

  const handleReset = () => {
    const defaultKey = layerType as keyof typeof DEFAULT_VECTOR_STYLES;
    const defaultStyle =
      DEFAULT_VECTOR_STYLES[defaultKey] || DEFAULT_VECTOR_STYLES.default;
    onStyleChange(defaultStyle);
    setCustomFillColor(defaultStyle.fillColor);
    setCustomBorderColor(defaultStyle.borderColor);
    if (onReset) onReset();
  };

  const ColorPreview = ({
    color,
    opacity = 1,
  }: {
    color: string;
    opacity?: number;
  }) => (
    <div
      className="w-6 h-6 rounded border border-gray-300 flex-shrink-0"
      style={{
        backgroundColor: color === "transparent" ? "transparent" : color,
        opacity: color === "transparent" ? 1 : opacity,
        backgroundImage:
          color === "transparent"
            ? "linear-gradient(45deg, #ccc 25%, transparent 25%), linear-gradient(-45deg, #ccc 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #ccc 75%), linear-gradient(-45deg, transparent 75%, #ccc 75%)"
            : undefined,
        backgroundSize: color === "transparent" ? "8px 8px" : undefined,
        backgroundPosition:
          color === "transparent"
            ? "0 0, 0 4px, 4px -4px, -4px 0px"
            : undefined,
      }}
    />
  );

  const StylePreview = () => (
    <div className="p-4 bg-gray-50 rounded-lg">
      <Label className="text-sm font-medium mb-2 block">Style Preview</Label>
      <div className="flex items-center justify-center h-20 bg-white rounded border">
        <svg width="60" height="40" viewBox="0 0 60 40">
          <rect
            x="5"
            y="5"
            width="50"
            height="30"
            fill={
              currentStyle?.fillColor === "transparent"
                ? "none"
                : currentStyle?.fillColor
            }
            fillOpacity={currentStyle?.fillOpacity || 0.6}
            stroke={currentStyle?.borderColor}
            strokeWidth={currentStyle?.borderWidth || 2}
            strokeOpacity={currentStyle?.borderOpacity || 1}
            strokeDasharray={currentStyle?.borderDashArray}
          />
        </svg>
      </div>
    </div>
  );

  return (
    <Card className="w-full">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2">
          <Shapes className="h-5 w-5" />
          Vector Style - {layerName}
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-6">
        <StylePreview />

        <div className="space-y-3">
          <Label className="text-sm font-medium">Fill Color</Label>

          <div className="grid grid-cols-4 gap-2">
            {PREDEFINED_COLORS.map((color) => (
              <button
                key={color.value}
                className={`flex items-center gap-2 p-2 rounded border text-xs hover:bg-gray-100 ${
                  currentStyle?.fillColor === color.value
                    ? "border-blue-500 bg-blue-50"
                    : "border-gray-200"
                }`}
                onClick={() => handleStyleUpdate({ fillColor: color.value })}
              >
                <ColorPreview
                  color={color.value}
                  opacity={currentStyle?.fillOpacity}
                />
                <span className="truncate">{color.name}</span>
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <Label className="text-xs">Custom:</Label>
            <Input
              type="color"
              value={customFillColor}
              onChange={(e) => {
                setCustomFillColor(e.target.value);
                handleStyleUpdate({ fillColor: e.target.value });
              }}
              className="w-12 h-8 p-1 border rounded"
            />
            <Input
              type="text"
              value={customFillColor}
              onChange={(e) => {
                setCustomFillColor(e.target.value);
                handleStyleUpdate({ fillColor: e.target.value });
              }}
              className="flex-1 text-xs"
              placeholder="#3b82f6"
            />
          </div>

          <div className="space-y-2">
            <div className="flex justify-between">
              <Label className="text-xs">Fill Opacity</Label>
              <span className="text-xs text-muted-foreground">
                {Math.round((currentStyle?.fillOpacity || 0.6) * 100)}%
              </span>
            </div>
            <Slider
              value={[
                currentStyle?.fillOpacity ? currentStyle.fillOpacity * 100 : 60,
              ]}
              onValueChange={([value]) =>
                handleStyleUpdate({ fillOpacity: value / 100 })
              }
              max={100}
              step={5}
              className="w-full"
            />
          </div>
        </div>

        <div className="space-y-3">
          <Label className="text-sm font-medium">Border</Label>

          <div className="space-y-2">
            <Label className="text-xs">Border Color</Label>
            <div className="grid grid-cols-4 gap-2">
              {PREDEFINED_COLORS.slice(1, 9).map((color) => (
                <button
                  key={color.value}
                  className={`flex items-center gap-2 p-2 rounded border text-xs hover:bg-gray-100 ${
                    currentStyle?.borderColor === color.value
                      ? "border-blue-500 bg-blue-50"
                      : "border-gray-200"
                  }`}
                  onClick={() =>
                    handleStyleUpdate({ borderColor: color.value })
                  }
                >
                  <ColorPreview
                    color={color.value}
                    opacity={currentStyle?.borderOpacity}
                  />
                  <span className="truncate">{color.name}</span>
                </button>
              ))}
            </div>

            <div className="flex items-center gap-2">
              <Label className="text-xs">Custom:</Label>
              <Input
                type="color"
                value={customBorderColor}
                onChange={(e) => {
                  setCustomBorderColor(e.target.value);
                  handleStyleUpdate({ borderColor: e.target.value });
                }}
                className="w-12 h-8 p-1 border rounded"
              />
              <Input
                type="text"
                value={customBorderColor}
                onChange={(e) => {
                  setCustomBorderColor(e.target.value);
                  handleStyleUpdate({ borderColor: e.target.value });
                }}
                className="flex-1 text-xs"
                placeholder="#ffffff"
              />
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between">
              <Label className="text-xs">Border Width</Label>
              <span className="text-xs text-muted-foreground">
                {currentStyle?.borderWidth || 2}px
              </span>
            </div>
            <Slider
              value={[currentStyle?.borderWidth || 2]}
              onValueChange={([value]) =>
                handleStyleUpdate({ borderWidth: value })
              }
              max={10}
              min={0}
              step={0.5}
              className="w-full"
            />
          </div>

          <div className="space-y-2">
            <div className="flex justify-between">
              <Label className="text-xs">Border Opacity</Label>
              <span className="text-xs text-muted-foreground">
                {Math.round((currentStyle?.borderOpacity || 1.0) * 100)}%
              </span>
            </div>
            <Slider
              value={[
                currentStyle?.borderOpacity
                  ? currentStyle.borderOpacity * 100
                  : 100,
              ]}
              onValueChange={([value]) =>
                handleStyleUpdate({ borderOpacity: value / 100 })
              }
              max={100}
              step={5}
              className="w-full"
            />
          </div>

          <div className="space-y-2">
            <Label className="text-xs">Border Style</Label>
            <Select
              value={currentStyle?.borderDashArray || "solid"}
              onValueChange={(value) =>
                handleStyleUpdate({
                  borderDashArray: value === "solid" ? undefined : value,
                })
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {BORDER_STYLES.map((style) => (
                  <SelectItem
                    key={style.value || "solid"}
                    value={style.value || "solid"}
                  >
                    {style.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

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

        <div className="text-xs text-muted-foreground bg-gray-50 p-3 rounded-lg">
          <div className="flex items-center gap-2 mb-2">
            <Eye className="h-4 w-4" />
            <span className="font-medium">Style Options:</span>
          </div>
          <ul className="space-y-1 ml-6">
            <li>
              • <strong>Fill:</strong> Interior color and transparency of shapes
            </li>
            <li>
              • <strong>Border:</strong> Outline color, thickness, and style
            </li>
            <li>
              • <strong>Opacity:</strong> 0% = invisible, 100% = solid
            </li>
            <li>
              • <strong>Transparent fill:</strong> Shows only the border outline
            </li>
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}
