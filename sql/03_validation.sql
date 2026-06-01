-- =============================================================================
-- DATA VALIDATION QUERIES
--
-- Purpose:
-- Verify correctness and integrity of loaded data.
--
-- These checks ensure:
-- - expected number of records
-- - absence of duplicates
-- - correct structure of fact table
-- - consistency between fact and dimension tables
-- - completeness of country-region mapping
--
-- Useful for:
-- - debugging ETL processes
-- - validating data before analysis
-- - ensuring reproducibility
-- =============================================================================


-- =====================================================
-- DIMENSION TABLE VALIDATION
-- =====================================================

-- Validate number of records in dim_country

SELECT COUNT(*) FROM dim_country;


-- Validate number of records in dim_age (expected: 15)

SELECT COUNT(*) FROM dim_age;


-- Validate absence of duplicates in dim_age

SELECT 
    age_range, 
    COUNT(*) as cnt
FROM dim_age
GROUP BY age_range
HAVING cnt > 1;


-- Validate that all countries have a valid region

SELECT 
    country, 
    region
FROM dim_country
WHERE region IS NULL
   OR region = 'Unknown';


-- Validate regional distribution of countries

SELECT 
    region, 
    COUNT(*) AS countries
FROM dim_country
GROUP BY region
ORDER BY region;


-- =====================================================
-- FACT TABLE VALIDATION
-- =====================================================

-- Validate number of records in fact table

SELECT COUNT(*) FROM fact_asd_prevalence;


-- Validate absence of duplicate records
-- GROUP BY groups identical records
-- HAVING filters groups with more than 1 occurrence

SELECT 
    year, 
    gender, 
    age_range, 
    country_id, 
    COUNT(*) as cnt
FROM fact_asd_prevalence
GROUP BY 
    year, 
    gender, 
    age_range, 
    country_id
HAVING cnt > 1;


-- =====================================================
-- RELATIONAL CONSISTENCY VALIDATION
-- =====================================================

-- Check that all country_id values in fact exist in dim_country

SELECT DISTINCT f.country_id
FROM fact_asd_prevalence f
LEFT JOIN dim_country d
    ON f.country_id = d.country_id
WHERE d.country_id IS NULL;


-- Check that all age_range values in fact exist in dim_age

SELECT DISTINCT f.age_range
FROM fact_asd_prevalence f
LEFT JOIN dim_age d
    ON f.age_range = d.age_range
WHERE d.age_range IS NULL;


-- =====================================================
-- DATA INSPECTION
-- =====================================================

-- Inspect sample of fact data

SELECT * 
FROM fact_asd_prevalence
LIMIT 100;