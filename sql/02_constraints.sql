-- =============================================================================
-- CONSTRAINTS AND DATA INTEGRITY RULES
--
-- Purpose:
-- Enforce data consistency and prevent invalid or duplicated records.
--
-- In this case:
-- - remove redundant column (country)
-- - enforce uniqueness in fact table
--
-- Why:
-- - avoid duplicated analytical records
-- - ensure idempotent data loads
-- - maintain clean star schema design
--
-- Note:
-- This script is intended for initial database setup.
-- Some statements will fail if executed multiple times after constraints have already been applied.
-- =============================================================================


-- Remove denormalized column from fact table
-- country is replaced by country_id (normalized design)

ALTER TABLE fact_asd_prevalence
DROP COLUMN country;

-- Add unique constraint to prevent duplicate fact records
-- Each combination represents a unique analytical observation

ALTER TABLE fact_asd_prevalence
ADD UNIQUE KEY unique_fact (
    year,
    gender,
    age_range,
    country_id
);