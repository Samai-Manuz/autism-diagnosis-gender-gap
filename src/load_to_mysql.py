"""
ETL step: load dimension tables and fact table into MySQL.

This script performs the following steps:
- load processed ASD prevalence dataset from processed directory
- load country-region mapping from interim directory
- validate dataset structure and key fields
- validate country-region mapping completeness
- extract unique country values
- insert or update countries into dim_country table with their corresponding region
- insert age ranges into dim_age table with life stage classification
- retrieve country_id mapping from dim_country table
- map country names to country_id in dataframe
- validate country_id mapping completeness
- validate that all age_range values exist in dim_age
- validate that no country remains with region = 'Unknown'
- insert fact records into fact_asd_prevalence table

Notes:
- gbd_asd_prevalence_oecd_processed.csv is loaded from PROCESSED_DIR
- country_regions_oecd.csv is loaded from INTERIM_DIR
- dim_country regions are loaded from country_regions_oecd.csv
- countries without region mapping are flagged during validation
- dim_country uses INSERT ... ON DUPLICATE KEY UPDATE to update existing regions
- dim_age uses INSERT IGNORE to ensure idempotent loading
- fact_asd_prevalence uses INSERT IGNORE with a UNIQUE constraint to prevent duplicates
- pipeline is idempotent and can be safely re-executed
"""

import pandas as pd
import mysql.connector

from paths import PROCESSED_DIR, INTERIM_DIR


# Establish connection to MySQL database

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root123",
        database="asd_analysis"
    )


# Load processed ASD prevalence dataset from processed directory

def load_data():
    file_path = PROCESSED_DIR / "gbd_asd_prevalence_oecd_processed.csv"

    print("Loading processed dataset from:")
    print(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Processed dataset not found: {file_path}")

    df = pd.read_csv(file_path)
    return df


# Load country-region mapping from interim directory

def load_country_regions():
    file_path = INTERIM_DIR / "country_regions_oecd.csv"

    print("Loading country-region mapping from:")
    print(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Country-region mapping not found: {file_path}")

    regions_df = pd.read_csv(file_path)

    print("Region mapping shape:", regions_df.shape)
    print(regions_df.head())
    print("Unique mapped countries:", regions_df["country"].nunique())

    return regions_df


# Validate processed dataset structure before database load

def validate_dataframe(df):
    print("Shape:", df.shape)
    print("Columns:", df.columns.tolist())

    print("Nulls per column:")
    print(df.isnull().sum())

    print("Unique countries:", df["country"].nunique())


# Validate country-region mapping completeness before loading dim_country

def validate_country_regions(df, regions_df):
    countries = set(df["country"].unique())
    mapped_countries = set(regions_df["country"].unique())

    missing_regions = countries - mapped_countries
    extra_regions = mapped_countries - countries

    print("Countries without region mapping:", missing_regions)
    print("Country-region entries not present in main dataset:", extra_regions)


# Insert or update unique countries into dim_country table with region mapping

def load_dim_country(df, regions_df):
    conn = get_connection()
    cursor = conn.cursor()

    region_mapping = dict(
        zip(
            regions_df["country"],
            regions_df["region"]
        )
    )

    countries = df["country"].drop_duplicates().tolist()

    for country in countries:
        region = region_mapping.get(country, "Unknown")

        cursor.execute(
            """
            INSERT INTO dim_country (country, region)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE
                region = VALUES(region)
            """,
            (country, region)
        )

    conn.commit()
    cursor.close()
    conn.close()


# Insert age ranges into dim_age table with life stage classification

def load_dim_age():
    conn = get_connection()
    cursor = conn.cursor()

    dim_age_data = [
        ("<5", "Childhood"),
        ("5-9", "Childhood"),
        ("10-14", "Adolescence"),
        ("15-19", "Adolescence"),
        ("20-24", "Youth"),
        ("25-29", "Youth"),
        ("30-34", "Adulthood"),
        ("35-39", "Adulthood"),
        ("40-44", "Adulthood"),
        ("45-49", "Adulthood"),
        ("50-54", "Adulthood"),
        ("55-59", "Adulthood"),
        ("60-64", "Senior"),
        ("65-69", "Senior"),
        ("70+", "Senior")
    ]

    cursor.executemany(
        """
        INSERT IGNORE INTO dim_age (age_range, life_stage)
        VALUES (%s, %s)
        """,
        dim_age_data
    )

    conn.commit()
    cursor.close()
    conn.close()


# Load country_id mapping from dim_country table

def get_country_mapping():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT country_id, country FROM dim_country")
    results = cursor.fetchall()

    mapping = {country: country_id for country_id, country in results}

    cursor.close()
    conn.close()

    return mapping


# Map country names to country_id in dataframe

def apply_country_mapping(df, mapping):
    df["country_id"] = df["country"].map(mapping)
    return df


# Validate country_id mapping results

def validate_mapping(df):
    null_ids = df["country_id"].isnull().sum()
    print("Unmapped country_id:", null_ids)


# Validate that all age_range values exist in dim_age

def validate_age_dimension(df):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT age_range FROM dim_age")
    dim_ages = {row[0] for row in cursor.fetchall()}

    df_ages = set(df["age_range"].unique())

    missing = df_ages - dim_ages

    print("Missing age_range in dim_age:", missing)

    cursor.close()
    conn.close()


# Validate that no country remains with Unknown region after loading dim_country

def validate_unknown_regions():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT country, region
        FROM dim_country
        WHERE region = 'Unknown'
        """
    )

    results = cursor.fetchall()

    print("Countries still marked as Unknown:")
    print(results)

    cursor.close()
    conn.close()


# Insert fact records into fact_asd_prevalence table

def load_fact_table(df):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        INSERT IGNORE INTO fact_asd_prevalence
        (year, gender, age_range, prevalence, lower_ui, upper_ui, country_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """

    data = df[
        ["year", "gender", "age_range", "prevalence", "lower_ui", "upper_ui", "country_id"]
    ].values.tolist()

    cursor.executemany(query, data)

    conn.commit()
    cursor.close()
    conn.close()


# Main execution flow for ETL step: load dimension and fact tables

if __name__ == "__main__":
    df = load_data()
    regions_df = load_country_regions()

    validate_dataframe(df)
    validate_country_regions(df, regions_df)

    load_dim_country(df, regions_df)
    load_dim_age()

    mapping = get_country_mapping()

    df = apply_country_mapping(df, mapping)

    validate_mapping(df)
    validate_age_dimension(df)
    validate_unknown_regions()

    load_fact_table(df)