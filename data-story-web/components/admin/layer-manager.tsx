"use client";

import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Upload, Trash2, FileImage, Map, Loader2, Palette } from "lucide-react";
import {
  mapTileService,
  MapLayerMetadata,
  LayerUploadResult,
} from "@/lib/map-tile-service";
import { useToast } from "@/hooks/use-toast";
import { LayerStyleConfig, RasterColorScheme, VectorStyle } from "@/lib/map-types";
import { getDefaultSchemeForLayerType } from "@/lib/color-schemes";
import { RasterStyleEditor } from "./raster-style-editor";
import { VectorStyleEditor } from "./vector-style-editor";

export default function LayerManager() {
  const [layers, setLayers] = useState<MapLayerMetadata[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [layerName, setLayerName] = useState("");
  const [layerType, setLayerType] = useState<string>("");
  const [showUploadDialog, setShowUploadDialog] = useState(false);
  const [showStyleDialog, setShowStyleDialog] = useState(false);
  const [selectedLayerForStyling, setSelectedLayerForStyling] = useState<MapLayerMetadata | null>(null);
  const { toast } = useToast();

  const loadLayers = useCallback(async () => {
    try {
      const availableLayers = await mapTileService.getAvailableLayers();
      setLayers(availableLayers);
    } catch (error) {
      console.error("Failed to load layers:", error);
      toast({
        title: "Error",
        description: "Failed to load layers",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    loadLayers();
  }, [loadLayers]);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      const baseName = file.name.split(".")[0];
      setLayerName(baseName);

      const extension = file.name.split(".").pop()?.toLowerCase();
      if (extension === "cog" || extension === "tif" || extension === "tiff") {
        setLayerType("raster");
      } else if (extension === "mbtiles") {
        setLayerType("vector");
      }
    }
  };

  const handleUpload = async () => {
    if (!selectedFile || !layerName || !layerType) {
      toast({
        title: "Error",
        description: "Please select a file and provide layer details",
        variant: "destructive",
      });
      return;
    }

    setUploading(true);
    setUploadProgress(0);

    try {
      const result: LayerUploadResult = await mapTileService.uploadLayer(
        selectedFile,
        layerName,
        layerType
      );

      setUploadProgress(100);

      const compressionInfo = result.compressionRatio
        ? ` (${result.compressionRatio}% smaller after optimization)`
        : "";

      toast({
        title: "Success",
        description: `${
          result.message || "Layer uploaded successfully"
        }${compressionInfo}`,
      });

      setShowUploadDialog(false);
      resetUploadForm();
      await loadLayers();
    } catch (error) {
      toast({
        title: "Upload Failed",
        description:
          error instanceof Error ? error.message : "Unknown error occurred",
        variant: "destructive",
      });
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  const handleDelete = async (layerId: string) => {
    if (!confirm("Are you sure you want to delete this layer?")) {
      return;
    }

    try {
      await mapTileService.deleteLayer(layerId);
      toast({
        title: "Success",
        description: "Layer deleted successfully",
      });
      await loadLayers();
    } catch (error) {
      console.error("Failed to delete layer:", error);
      toast({
        title: "Error",
        description: "Failed to delete layer",
        variant: "destructive",
      });
    }
  };

  const resetUploadForm = () => {
    setSelectedFile(null);
    setLayerName("");
    setLayerType("");
    setUploadProgress(0);
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const handleOpenStyleDialog = (layer: MapLayerMetadata) => {
    setSelectedLayerForStyling(layer);
    setShowStyleDialog(true);
  };

  const handleStyleChange = async (styleConfig: LayerStyleConfig) => {
    if (!selectedLayerForStyling) return;

    try {
      // Save to backend API
      const response = await fetch(`/api/map-layers/${selectedLayerForStyling.id}/style`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(styleConfig),
      });

      if (!response.ok) {
        throw new Error('Failed to save style configuration');
      }

      // Update local state
      const updatedLayers = layers.map(layer => 
        layer.id === selectedLayerForStyling.id 
          ? { ...layer, styleConfig }
          : layer
      );
      setLayers(updatedLayers);

      toast({
        title: "Success",
        description: "Layer style updated successfully",
      });
    } catch (error) {
      console.error('Error updating layer style:', error);
      toast({
        title: "Error",
        description: "Failed to update layer style",
        variant: "destructive",
      });
    }
  };

  const handleRasterSchemeChange = (scheme: RasterColorScheme) => {
    if (!selectedLayerForStyling) return;
    
    const styleConfig: LayerStyleConfig = {
      id: selectedLayerForStyling.id,
      type: 'raster',
      rasterScheme: scheme,
      lastModified: new Date().toISOString()
    };
    
    handleStyleChange(styleConfig);
  };

  const handleVectorStyleChange = (vectorStyle: VectorStyle) => {
    if (!selectedLayerForStyling) return;
    
    const styleConfig: LayerStyleConfig = {
      id: selectedLayerForStyling.id,
      type: 'vector',
      vectorStyle: vectorStyle,
      lastModified: new Date().toISOString()
    };
    
    handleStyleChange(styleConfig);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="ml-2">Loading layers...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Layer Management</h2>
          <p className="text-muted-foreground">
            Upload and manage map layers for your interactive maps
          </p>
        </div>
        <Dialog open={showUploadDialog} onOpenChange={setShowUploadDialog}>
          <DialogTrigger asChild>
            <Button>
              <Upload className="w-4 h-4 mr-2" />
              Upload Layer
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>Upload New Layer</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label htmlFor="file">Select File</Label>
                <Input
                  id="file"
                  type="file"
                  accept=".cog,.mbtiles,.tif,.tiff"
                  onChange={handleFileSelect}
                  disabled={uploading}
                />
                <p className="text-sm text-muted-foreground mt-1">
                  Supported formats: COG, MBTiles, TIFF (for cluster processing)
                  <br />
                  Files are already web-optimized and ready for efficient
                  serving
                </p>
              </div>

              {selectedFile && (
                <Alert>
                  <FileImage className="h-4 w-4" />
                  <AlertDescription>
                    Selected: {selectedFile.name} (
                    {formatFileSize(selectedFile.size)})
                  </AlertDescription>
                </Alert>
              )}

              <div>
                <Label htmlFor="layerName">Layer Name</Label>
                <Input
                  id="layerName"
                  value={layerName}
                  onChange={(e) => setLayerName(e.target.value)}
                  placeholder="Enter layer name"
                  disabled={uploading}
                />
              </div>

              <div>
                <Label htmlFor="layerType">Layer Type</Label>
                <Select
                  value={layerType}
                  onValueChange={setLayerType}
                  disabled={uploading}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select layer type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="raster">Raster (COG)</SelectItem>
                    <SelectItem value="vector">Vector (MBTiles)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {uploading && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span>Uploading...</span>
                    <span>{uploadProgress}%</span>
                  </div>
                  <Progress value={uploadProgress} />
                </div>
              )}

              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => setShowUploadDialog(false)}
                  disabled={uploading}
                  className="flex-1"
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleUpload}
                  disabled={
                    !selectedFile || !layerName || !layerType || uploading
                  }
                  className="flex-1"
                >
                  {uploading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Uploading
                    </>
                  ) : (
                    <>
                      <Upload className="w-4 h-4 mr-2" />
                      Upload
                    </>
                  )}
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>

        {/* Style Configuration Dialog */}
        <Dialog open={showStyleDialog} onOpenChange={setShowStyleDialog}>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>
                Configure Layer Style - {selectedLayerForStyling?.name}
              </DialogTitle>
            </DialogHeader>
            
            {selectedLayerForStyling && (
              <div className="space-y-4">
                {selectedLayerForStyling.dataType === "raster" ? (
                  <RasterStyleEditor
                    layerName={selectedLayerForStyling.name}
                    layerType={selectedLayerForStyling.id}
                    currentScheme={
                      selectedLayerForStyling.styleConfig?.rasterScheme || 
                      getDefaultSchemeForLayerType(selectedLayerForStyling.id)
                    }
                    onSchemeChange={handleRasterSchemeChange}
                    onReset={() => {
                      const defaultScheme = getDefaultSchemeForLayerType(selectedLayerForStyling.id);
                      handleRasterSchemeChange(defaultScheme);
                    }}
                  />
                ) : (
                  <VectorStyleEditor
                    layerName={selectedLayerForStyling.name}
                    layerType={selectedLayerForStyling.id}
                    currentStyle={selectedLayerForStyling.styleConfig?.vectorStyle}
                    onStyleChange={handleVectorStyleChange}
                    onReset={() => {
                      // Will be handled by the VectorStyleEditor component
                    }}
                  />
                )}
                
                <div className="flex gap-2 pt-4 border-t">
                  <Button
                    variant="outline"
                    onClick={() => setShowStyleDialog(false)}
                    className="flex-1"
                  >
                    Close
                  </Button>
                </div>
              </div>
            )}
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {layers.map((layer) => (
          <Card key={layer.id} className="relative">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg flex items-center gap-2">
                  {layer.dataType === "raster" ? (
                    <FileImage className="w-4 h-4" />
                  ) : (
                    <Map className="w-4 h-4" />
                  )}
                  {layer.name}
                </CardTitle>
                <Badge
                  variant={
                    layer.dataType === "raster" ? "default" : "secondary"
                  }
                >
                  {layer.format.toUpperCase()}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="text-sm text-muted-foreground">
                <p>
                  <strong>Type:</strong> {layer.dataType}
                </p>
                <p>
                  <strong>Size:</strong> {formatFileSize(layer.fileSize)}
                </p>
                <p>
                  <strong>Uploaded:</strong>{" "}
                  {new Date(layer.uploadedAt).toLocaleDateString()}
                </p>
              </div>

              {layer.description && (
                <p className="text-sm">{layer.description}</p>
              )}

              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleOpenStyleDialog(layer)}
                  className="flex-1"
                >
                  <Palette className="w-3 h-3 mr-1" />
                  Style
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleDelete(layer.id)}
                  className="flex-1"
                >
                  <Trash2 className="w-3 h-3 mr-1" />
                  Delete
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {layers.length === 0 && (
        <Card>
          <CardContent className="pt-6 text-center">
            <Map className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No layers found</h3>
            <p className="text-muted-foreground mb-4">
              Upload your first layer to get started with interactive maps
            </p>
            <Button onClick={() => setShowUploadDialog(true)}>
              <Upload className="w-4 h-4 mr-2" />
              Upload Layer
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
