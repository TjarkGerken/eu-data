-- Migration to populate readable_id for existing references
-- This script will generate unique readable IDs for all existing references

-- Function to generate a base readable ID from author and year
CREATE OR REPLACE FUNCTION generate_base_readable_id(authors TEXT[], ref_year INTEGER)
RETURNS TEXT AS $$
DECLARE
    first_author TEXT;
    last_name TEXT;
BEGIN
    -- Handle empty or null authors array
    IF authors IS NULL OR array_length(authors, 1) IS NULL OR array_length(authors, 1) = 0 THEN
        RETURN 'Unknown' || ref_year::TEXT;
    END IF;
    
    first_author := trim(authors[1]);
    
    -- Extract last name (last word) from first author
    last_name := regexp_replace(first_author, '^.*\s+([A-Za-z]+)$', '\1');
    
    -- If no space found, use the whole name
    IF last_name = first_author THEN
        last_name := regexp_replace(first_author, '[^A-Za-z]', '', 'g');
    END IF;
    
    -- Fallback if still empty
    IF last_name = '' THEN
        last_name := 'Unknown';
    END IF;
    
    RETURN last_name || ref_year::TEXT;
END;
$$ LANGUAGE plpgsql;

-- Function to generate unique readable ID with conflict resolution
CREATE OR REPLACE FUNCTION generate_unique_readable_id(ref_id TEXT, authors TEXT[], ref_year INTEGER)
RETURNS TEXT AS $$
DECLARE
    base_id TEXT;
    candidate_id TEXT;
    suffix INTEGER;
    conflict_count INTEGER;
BEGIN
    base_id := generate_base_readable_id(authors, ref_year);
    candidate_id := base_id;
    suffix := 2;
    
    -- Check for conflicts and resolve them
    LOOP
        SELECT COUNT(*) INTO conflict_count
        FROM content_references 
        WHERE readable_id = candidate_id 
        AND id != ref_id;
        
        -- If no conflict, we're good
        IF conflict_count = 0 THEN
            EXIT;
        END IF;
        
        -- Try next suffix
        candidate_id := base_id || '-' || suffix::TEXT;
        suffix := suffix + 1;
        
        -- Safety check to prevent infinite loop
        IF suffix > 100 THEN
            candidate_id := base_id || '-' || extract(epoch from now())::INTEGER::TEXT;
            EXIT;
        END IF;
    END LOOP;
    
    RETURN candidate_id;
END;
$$ LANGUAGE plpgsql;

-- Update all existing references with readable IDs
DO $$
DECLARE
    ref_record RECORD;
    new_readable_id TEXT;
BEGIN
    -- Process each reference that doesn't have a readable_id
    FOR ref_record IN 
        SELECT id, authors, year 
        FROM content_references 
        WHERE readable_id IS NULL 
        ORDER BY created_at ASC
    LOOP
        -- Generate unique readable ID
        new_readable_id := generate_unique_readable_id(
            ref_record.id, 
            ref_record.authors, 
            ref_record.year
        );
        
        -- Update the record
        UPDATE content_references 
        SET readable_id = new_readable_id 
        WHERE id = ref_record.id;
        
        RAISE NOTICE 'Updated reference % with readable_id: %', ref_record.id, new_readable_id;
    END LOOP;
END $$;

-- Clean up the helper functions
DROP FUNCTION generate_base_readable_id(TEXT[], INTEGER);
DROP FUNCTION generate_unique_readable_id(TEXT, TEXT[], INTEGER);

-- Verify all references now have readable IDs
SELECT 
    COUNT(*) as total_references,
    COUNT(readable_id) as references_with_readable_id,
    COUNT(*) - COUNT(readable_id) as missing_readable_ids
FROM content_references; 