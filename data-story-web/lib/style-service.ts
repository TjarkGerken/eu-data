import { LayerStyleConfig } from "./map-types";
import { Json, supabase } from "./supabase";

/**
 * Service for managing layer style configurations in Supabase.
 */
export const styleService = {
  /**
   * Retrieves the style configuration for a specific layer.
   * @param layerId The ID of the layer.
   * @returns The style configuration or null if not found.
   */
  async getLayerStyle(
    layerId: string,
  ): Promise<LayerStyleConfig | null> {
    const { data, error } = await supabase
      .from("layer_styles")
      .select("style_config")
      .eq("layer_id", layerId)
      .single();

    if (error) {
      if (error.code === 'PGRST116') { // PostgREST error for "Not found"
        return null; 
      }
      console.error("Error fetching layer style:", error);
      throw error;
    }

    return data?.style_config as unknown as LayerStyleConfig;
  },

  /**
   * Creates or updates the style configuration for a specific layer.
   * @param layerId The ID of the layer.
   * @param styleConfig The style configuration to save.
   * @returns The updated style configuration.
   */
  async updateLayerStyle(
    layerId: string,
    styleConfig: LayerStyleConfig,
  ): Promise<LayerStyleConfig> {
    const { data, error } = await supabase
      .from("layer_styles")
      .upsert(
        { layer_id: layerId, style_config: styleConfig as unknown as Json },
        { onConflict: "layer_id" }
      )
      .select()
      .single();

    if (error) {
      console.error("Error updating layer style:", error);
      throw error;
    }

    return data.style_config as unknown as LayerStyleConfig;
  },

  /**
   * Retrieves all layer styles and returns them as a map.
   * Useful for joining with layer metadata in a single operation.
   * @returns A Map where keys are layer IDs and values are style configs.
   */
  async getAllLayerStyles(): Promise<Map<string, LayerStyleConfig>> {
    const { data, error } = await supabase
      .from("layer_styles")
      .select("layer_id, style_config");

    if (error) {
      console.error("Error fetching all layer styles:", error);
      throw error;
    }

    const styleMap = new Map<string, LayerStyleConfig>();
    if (data) {
      for (const row of data) {
        styleMap.set(row.layer_id, row.style_config as unknown as LayerStyleConfig);
      }
    }
    return styleMap;
  },

  /**
   * Deletes the style configuration for a specific layer.
   * @param layerId The ID of the layer.
   */
  async deleteLayerStyle(
    layerId: string,
      ): Promise<void> {
    const { error } = await supabase
      .from("layer_styles")
      .delete()
      .eq("layer_id", layerId);

    if (error) {
      console.error("Error deleting layer style:", error);
      throw error;
    }
  },
}; 