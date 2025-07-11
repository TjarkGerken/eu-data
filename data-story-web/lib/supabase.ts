import { createClient } from "@supabase/supabase-js";

export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  public: {
    Tables: {
      block_references: {
        Row: {
          block_id: string
          reference_id: string
        }
        Insert: {
          block_id: string
          reference_id: string
        }
        Update: {
          block_id?: string
          reference_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "block_references_block_id_fkey"
            columns: ["block_id"]
            isOneToOne: false
            referencedRelation: "content_blocks"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "block_references_reference_id_fkey"
            columns: ["reference_id"]
            isOneToOne: false
            referencedRelation: "content_references"
            referencedColumns: ["id"]
          },
        ]
      }
      climate_images: {
        Row: {
          blob_url: string | null
          category: string
          created_at: string | null
          description: string | null
          display_order: number | null
          file_size: number | null
          filename: string
          id: number
          mime_type: string | null
          public_url: string
          scenario: string
          storage_path: string
          thumbnail_url: string | null
          updated_at: string | null
        }
        Insert: {
          blob_url?: string | null
          category: string
          created_at?: string | null
          description?: string | null
          display_order?: number | null
          file_size?: number | null
          filename: string
          id?: number
          mime_type?: string | null
          public_url: string
          scenario: string
          storage_path: string
          thumbnail_url?: string | null
          updated_at?: string | null
        }
        Update: {
          blob_url?: string | null
          category?: string
          created_at?: string | null
          description?: string | null
          display_order?: number | null
          file_size?: number | null
          filename?: string
          id?: number
          mime_type?: string | null
          public_url?: string
          scenario?: string
          storage_path?: string
          thumbnail_url?: string | null
          updated_at?: string | null
        }
        Relationships: []
      }
      content_blocks: {
        Row: {
          block_type: string
          content: string | null
          created_at: string | null
          data: Json
          id: string
          language: string | null
          order_index: number
          story_id: string | null
          title: string | null
          updated_at: string | null
        }
        Insert: {
          block_type: string
          content?: string | null
          created_at?: string | null
          data: Json
          id?: string
          language?: string | null
          order_index: number
          story_id?: string | null
          title?: string | null
          updated_at?: string | null
        }
        Update: {
          block_type?: string
          content?: string | null
          created_at?: string | null
          data?: Json
          id?: string
          language?: string | null
          order_index?: number
          story_id?: string | null
          title?: string | null
          updated_at?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "content_blocks_story_id_fkey"
            columns: ["story_id"]
            isOneToOne: false
            referencedRelation: "content_stories"
            referencedColumns: ["id"]
          },
        ]
      }
      content_references: {
        Row: {
          authors: string[]
          created_at: string | null
          id: string
          journal: string | null
          readable_id: string
          title: string
          type: string
          updated_at: string | null
          url: string | null
          year: number
        }
        Insert: {
          authors: string[]
          created_at?: string | null
          id: string
          journal?: string | null
          readable_id: string
          title: string
          type: string
          updated_at?: string | null
          url?: string | null
          year: number
        }
        Update: {
          authors?: string[]
          created_at?: string | null
          id?: string
          journal?: string | null
          readable_id?: string
          title?: string
          type?: string
          updated_at?: string | null
          url?: string | null
          year?: number
        }
        Relationships: []
      }
      content_stories: {
        Row: {
          created_at: string | null
          data_story_title: string | null
          hero_description: string | null
          hero_title: string
          id: string
          intro_text_1: string | null
          intro_text_2: string | null
          language_code: string
          updated_at: string | null
        }
        Insert: {
          created_at?: string | null
          data_story_title?: string | null
          hero_description?: string | null
          hero_title: string
          id?: string
          intro_text_1?: string | null
          intro_text_2?: string | null
          language_code?: string
          updated_at?: string | null
        }
        Update: {
          created_at?: string | null
          data_story_title?: string | null
          hero_description?: string | null
          hero_title?: string
          id?: string
          intro_text_1?: string | null
          intro_text_2?: string | null
          language_code?: string
          updated_at?: string | null
        }
        Relationships: []
      }
      layer_styles: {
        Row: {
          layer_id: string
          style_config: Json
          updated_at: string
        }
        Insert: {
          layer_id: string
          style_config: Json
          updated_at?: string
        }
        Update: {
          layer_id?: string
          style_config?: Json
          updated_at?: string
        }
        Relationships: []
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      [_ in never]: never
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DefaultSchema = Database[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof Database },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof Database
  }
    ? keyof (Database[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        Database[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends { schema: keyof Database }
  ? (Database[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      Database[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof Database },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof Database
  }
    ? keyof Database[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends { schema: keyof Database }
  ? Database[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof Database },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof Database
  }
    ? keyof Database[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends { schema: keyof Database }
  ? Database[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof Database },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof Database
  }
    ? keyof Database[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends { schema: keyof Database }
  ? Database[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof Database },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof Database
  }
    ? keyof Database[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends { schema: keyof Database }
  ? Database[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {},
  },
} as const;

// Specific type exports for easier use
export type ClimateImage = Tables<"climate_images">;
export type ClimateImageInsert = TablesInsert<"climate_images">;
export type ClimateImageUpdate = TablesUpdate<"climate_images">;

export type ContentStory = Tables<"content_stories">;
export type ContentStoryInsert = TablesInsert<"content_stories">;
export type ContentStoryUpdate = TablesUpdate<"content_stories">;

export type ContentBlock = Tables<"content_blocks">;
export type ContentBlockInsert = TablesInsert<"content_blocks">;
export type ContentBlockUpdate = TablesUpdate<"content_blocks">;

export type ContentReference = Tables<"content_references">;
export type ContentReferenceInsert = TablesInsert<"content_references">;
export type ContentReferenceUpdate = TablesUpdate<"content_references">;

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

export const supabase = createClient<Database>(supabaseUrl, supabaseAnonKey);

