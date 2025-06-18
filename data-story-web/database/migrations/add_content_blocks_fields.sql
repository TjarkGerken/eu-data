-- Add missing fields to content_blocks table
-- Run this migration to ensure the admin panel works correctly

-- Add title field if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'content_blocks' AND column_name = 'title') THEN
        ALTER TABLE content_blocks ADD COLUMN title TEXT;
    END IF;
END $$;

-- Add content field if it doesn't exist  
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'content_blocks' AND column_name = 'content') THEN
        ALTER TABLE content_blocks ADD COLUMN content TEXT;
    END IF;
END $$;

-- Add language field if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'content_blocks' AND column_name = 'language') THEN
        ALTER TABLE content_blocks ADD COLUMN language TEXT DEFAULT 'en' CHECK (language IN ('en', 'de'));
    END IF;
END $$;

-- Ensure block_references table exists
CREATE TABLE IF NOT EXISTS block_references (
    block_id UUID NOT NULL REFERENCES content_blocks(id) ON DELETE CASCADE,
    reference_id UUID NOT NULL REFERENCES content_references(id) ON DELETE CASCADE,
    PRIMARY KEY (block_id, reference_id)
);

-- Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_block_references_block_id ON block_references(block_id);
CREATE INDEX IF NOT EXISTS idx_block_references_reference_id ON block_references(reference_id);
CREATE INDEX IF NOT EXISTS idx_content_blocks_story_id ON content_blocks(story_id);
CREATE INDEX IF NOT EXISTS idx_content_blocks_order_index ON content_blocks(order_index); 