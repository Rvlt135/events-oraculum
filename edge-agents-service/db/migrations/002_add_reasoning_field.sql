/*
  # Add reasoning field to recommendations

  1. Changes
    - Add `reasoning` TEXT NOT NULL column to recommendations table
    - This field stores detailed explanation of why this event and outcome were selected

  2. Migration notes
    - For existing records without reasoning, a default value is required
    - In production, consider a data migration to populate reasoning for existing records
*/

-- Add reasoning column with a temporary default for existing records
ALTER TABLE recommendations
ADD COLUMN IF NOT EXISTS reasoning TEXT NOT NULL DEFAULT 'Analysis in progress';

-- Remove default constraint after adding column (for new records, app will provide value)
ALTER TABLE recommendations
ALTER COLUMN reasoning DROP DEFAULT;
