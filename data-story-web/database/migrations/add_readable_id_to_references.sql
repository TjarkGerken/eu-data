-- Add readable_id field to content_references table
ALTER TABLE content_references 
ADD COLUMN readable_id VARCHAR(100) UNIQUE;

-- Create index for faster lookups
CREATE INDEX idx_content_references_readable_id ON content_references(readable_id);

-- Add constraint to ensure readable_id is not null for new records
ALTER TABLE content_references 
ADD CONSTRAINT readable_id_not_null CHECK (readable_id IS NOT NULL); 