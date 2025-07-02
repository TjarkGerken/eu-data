-- Create layer_styles table to store style configurations for map layers
CREATE TABLE
  public.layer_styles (
    layer_id TEXT NOT NULL,
    style_config JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (layer_id)
  );

-- Enable Row-Level Security
ALTER TABLE public.layer_styles ENABLE ROW LEVEL SECURITY;

-- Create policies for access
-- This policy allows public read access to everyone
CREATE POLICY "Allow public read access" ON public.layer_styles FOR
SELECT
  USING (true);

-- This policy allows users with the 'authenticated' role to insert, update, or delete their own data
-- In a real application, you would likely have more granular controls,
-- e.g., allowing only service roles to write or specific admin users.
CREATE POLICY "Allow authenticated write access" ON public.layer_styles FOR ALL USING (auth.role () = 'authenticated');

-- Add a comment to the table for clarity
COMMENT ON TABLE public.layer_styles IS 'Stores custom style configurations for map layers.'; 