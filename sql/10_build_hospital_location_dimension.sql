CREATE OR REPLACE TABLE
  `california-hospital-pricing.hospital_pricing.dim_hospital_location`

CLUSTER BY
  system_name,
  facility_id

AS

-- ============================================================
-- Kaiser Permanente
-- ============================================================

SELECT
  CAST('Kaiser Permanente' AS STRING) AS system_name,

  CAST(k.facility_id AS STRING) AS facility_id,
  CAST(k.mrf_location_name AS STRING) AS mrf_location_name,

  CAST(k.mrf_hospital_name AS STRING) AS mrf_hospital_name,
  CAST(k.mrf_address AS STRING) AS mrf_address,
  CAST(k.mrf_license_number AS STRING) AS mrf_license_number,
  CAST(k.mrf_type_2_npi AS STRING) AS mrf_type_2_npi,

  CAST(NULL AS STRING) AS mrf_last_updated_on,
  CAST(NULL AS STRING) AS mrf_as_of_date,
  CAST(NULL AS STRING) AS mrf_version,

  CAST(f.cms_facility_name AS STRING) AS facility_name,

  CAST(k.hcai_address_dim AS STRING) AS address,
  CAST(k.hcai_city AS STRING) AS city,
  CAST('CA' AS STRING) AS state,
  CAST(k.hcai_zip AS STRING) AS zip_code,

  CAST(NULL AS STRING) AS county,
  CAST(NULL AS STRING) AS telephone_number,

  CAST(f.hospital_type AS STRING) AS hospital_type,
  CAST(f.hospital_ownership AS STRING) AS hospital_ownership,
  CAST(f.emergency_services AS STRING) AS emergency_services,
  CAST(f.overall_rating AS FLOAT64) AS overall_rating,

  CAST(TRUE AS BOOL) AS analysis_eligible,

  CAST(k.hcai_id AS STRING) AS hcai_id,
  CAST(k.hcai_facility_name_dim AS STRING) AS hcai_facility_name,
  CAST(k.hcai_address_dim AS STRING) AS hcai_address,
  CAST(k.hcai_city AS STRING) AS hcai_city,
  CAST(k.hcai_zip AS STRING) AS hcai_zip_code,

  CAST(k.longitude AS FLOAT64) AS longitude,
  CAST(k.latitude AS FLOAT64) AS latitude,

  CAST(k.license_type AS STRING) AS license_type,
  CAST(k.license_category AS STRING) AS license_category,
  CAST(k.facility_level AS STRING) AS facility_level,
  CAST(k.er_service_level AS STRING) AS er_service_level,
  CAST(k.licensed_beds AS FLOAT64) AS licensed_beds,
  CAST(k.facility_status AS STRING) AS facility_status,

  CAST(k.match_method AS STRING) AS match_method,
  CAST(k.combined_score AS FLOAT64) AS match_score,

  CAST(k.zcta AS STRING) AS census_zcta,
  CAST(k.zcta_name AS STRING) AS census_zcta_name,
  CAST(k.population AS FLOAT64) AS zcta_population,
  CAST(k.median_household_income AS FLOAT64) AS zcta_median_household_income,
  CAST(k.poverty_rate AS FLOAT64) AS zcta_poverty_rate,
  CAST(k.uninsured_rate AS FLOAT64) AS zcta_uninsured_rate,
  CAST(k.unemployment_rate AS FLOAT64) AS zcta_unemployment_rate,
  CAST(k.bachelors_or_higher_rate AS FLOAT64) AS zcta_bachelors_or_higher_rate,

  CAST(NULL AS STRING) AS zcta_match_method,

  CAST(k.zcta IS NOT NULL AS BOOL) AS census_acs_matched

FROM
  `california-hospital-pricing.hospital_pricing.dim_kaiser_location` k

LEFT JOIN (
  SELECT
    facility_id,
    ANY_VALUE(cms_facility_name) AS cms_facility_name,
    ANY_VALUE(hospital_type) AS hospital_type,
    ANY_VALUE(hospital_ownership) AS hospital_ownership,
    ANY_VALUE(emergency_services) AS emergency_services,
    ANY_VALUE(overall_rating) AS overall_rating

  FROM
    `california-hospital-pricing.hospital_pricing.fact_kaiser_negotiated_price`

  GROUP BY
    facility_id
) f

USING (facility_id)


UNION ALL


-- ============================================================
-- UCLA Health
-- ============================================================

SELECT
  CAST(u.system_name AS STRING) AS system_name,

  CAST(u.facility_id AS STRING) AS facility_id,
  CAST(m.mrf_location_name AS STRING) AS mrf_location_name,

  CAST(m.mrf_hospital_name AS STRING) AS mrf_hospital_name,
  CAST(m.mrf_address AS STRING) AS mrf_address,
  CAST(m.mrf_license_number AS STRING) AS mrf_license_number,
  CAST(m.mrf_type_2_npi AS STRING) AS mrf_type_2_npi,
  CAST(m.mrf_last_updated_on AS STRING) AS mrf_last_updated_on,
  CAST(m.mrf_as_of_date AS STRING) AS mrf_as_of_date,
  CAST(m.mrf_version AS STRING) AS mrf_version,

  CAST(u.facility_name AS STRING) AS facility_name,
  CAST(u.address AS STRING) AS address,
  CAST(u.city AS STRING) AS city,
  CAST(u.state AS STRING) AS state,
  CAST(u.zip_code AS STRING) AS zip_code,
  CAST(u.county AS STRING) AS county,
  CAST(u.telephone_number AS STRING) AS telephone_number,

  CAST(u.hospital_type AS STRING) AS hospital_type,
  CAST(u.hospital_ownership AS STRING) AS hospital_ownership,
  CAST(u.emergency_services AS STRING) AS emergency_services,
  CAST(u.overall_rating AS FLOAT64) AS overall_rating,

  CAST(u.analysis_eligible AS BOOL) AS analysis_eligible,

  CAST(u.hcai_id AS STRING) AS hcai_id,
  CAST(u.hcai_facility_name AS STRING) AS hcai_facility_name,
  CAST(u.hcai_address AS STRING) AS hcai_address,
  CAST(u.hcai_city AS STRING) AS hcai_city,
  CAST(u.hcai_zip_code AS STRING) AS hcai_zip_code,

  CAST(u.longitude AS FLOAT64) AS longitude,
  CAST(u.latitude AS FLOAT64) AS latitude,

  CAST(NULL AS STRING) AS license_type,
  CAST(u.license_category AS STRING) AS license_category,
  CAST(u.facility_level AS STRING) AS facility_level,
  CAST(u.er_service_level AS STRING) AS er_service_level,
  CAST(u.licensed_beds AS FLOAT64) AS licensed_beds,
  CAST(u.facility_status AS STRING) AS facility_status,

  CAST(u.match_method AS STRING) AS match_method,
  CAST(u.match_score AS FLOAT64) AS match_score,

  CAST(u.census_zcta AS STRING) AS census_zcta,
  CAST(u.census_zcta_name AS STRING) AS census_zcta_name,
  CAST(u.zcta_population AS FLOAT64) AS zcta_population,
  CAST(u.zcta_median_household_income AS FLOAT64) AS zcta_median_household_income,
  CAST(u.zcta_poverty_rate AS FLOAT64) AS zcta_poverty_rate,
  CAST(u.zcta_uninsured_rate AS FLOAT64) AS zcta_uninsured_rate,
  CAST(u.zcta_unemployment_rate AS FLOAT64) AS zcta_unemployment_rate,
  CAST(u.zcta_bachelors_or_higher_rate AS FLOAT64) AS zcta_bachelors_or_higher_rate,

  CAST(u.zcta_match_method AS STRING) AS zcta_match_method,

  CAST(u.census_acs_matched AS BOOL) AS census_acs_matched

FROM
  `california-hospital-pricing.hospital_pricing.dim_ucla_location` u

LEFT JOIN (
  SELECT
    facility_id,

    ANY_VALUE(mrf_location_name) AS mrf_location_name,
    ANY_VALUE(mrf_hospital_name) AS mrf_hospital_name,
    ANY_VALUE(mrf_address) AS mrf_address,
    ANY_VALUE(mrf_license_number) AS mrf_license_number,
    ANY_VALUE(mrf_type_2_npi) AS mrf_type_2_npi,
    ANY_VALUE(mrf_last_updated_on) AS mrf_last_updated_on,
    ANY_VALUE(mrf_as_of_date) AS mrf_as_of_date,
    ANY_VALUE(mrf_version) AS mrf_version

  FROM
    `california-hospital-pricing.hospital_pricing.fact_ucla_negotiated_price`

  GROUP BY
    facility_id
) m

USING (facility_id)


UNION ALL


-- ============================================================
-- Sutter Health
-- ============================================================

SELECT
  CAST(s.system_name AS STRING) AS system_name,

  CAST(s.facility_id AS STRING) AS facility_id,
  CAST(m.mrf_location_name AS STRING) AS mrf_location_name,

  CAST(m.mrf_hospital_name AS STRING) AS mrf_hospital_name,
  CAST(m.mrf_address AS STRING) AS mrf_address,
  CAST(m.mrf_license_number AS STRING) AS mrf_license_number,
  CAST(m.mrf_type_2_npi AS STRING) AS mrf_type_2_npi,
  CAST(m.mrf_last_updated_on AS STRING) AS mrf_last_updated_on,
  CAST(NULL AS STRING) AS mrf_as_of_date,
  CAST(m.mrf_version AS STRING) AS mrf_version,

  CAST(s.facility_name AS STRING) AS facility_name,
  CAST(s.address AS STRING) AS address,
  CAST(s.city AS STRING) AS city,
  CAST(s.state AS STRING) AS state,
  CAST(s.zip_code AS STRING) AS zip_code,
  CAST(s.county AS STRING) AS county,
  CAST(s.telephone_number AS STRING) AS telephone_number,

  CAST(s.hospital_type AS STRING) AS hospital_type,
  CAST(s.hospital_ownership AS STRING) AS hospital_ownership,
  CAST(s.emergency_services AS STRING) AS emergency_services,
  CAST(s.overall_rating AS FLOAT64) AS overall_rating,

  CAST(s.analysis_eligible AS BOOL) AS analysis_eligible,

  CAST(s.hcai_id AS STRING) AS hcai_id,
  CAST(s.hcai_facility_name AS STRING) AS hcai_facility_name,
  CAST(s.hcai_address AS STRING) AS hcai_address,
  CAST(s.hcai_city AS STRING) AS hcai_city,
  CAST(s.hcai_zip_code AS STRING) AS hcai_zip_code,

  CAST(s.longitude AS FLOAT64) AS longitude,
  CAST(s.latitude AS FLOAT64) AS latitude,

  CAST(NULL AS STRING) AS license_type,
  CAST(s.license_category AS STRING) AS license_category,
  CAST(s.facility_level AS STRING) AS facility_level,
  CAST(s.er_service_level AS STRING) AS er_service_level,
  CAST(s.licensed_beds AS FLOAT64) AS licensed_beds,
  CAST(s.facility_status AS STRING) AS facility_status,

  CAST(s.match_method AS STRING) AS match_method,
  CAST(s.match_score AS FLOAT64) AS match_score,

  CAST(s.census_zcta AS STRING) AS census_zcta,
  CAST(s.census_zcta_name AS STRING) AS census_zcta_name,
  CAST(s.zcta_population AS FLOAT64) AS zcta_population,
  CAST(s.zcta_median_household_income AS FLOAT64) AS zcta_median_household_income,
  CAST(s.zcta_poverty_rate AS FLOAT64) AS zcta_poverty_rate,
  CAST(s.zcta_uninsured_rate AS FLOAT64) AS zcta_uninsured_rate,
  CAST(s.zcta_unemployment_rate AS FLOAT64) AS zcta_unemployment_rate,
  CAST(s.zcta_bachelors_or_higher_rate AS FLOAT64) AS zcta_bachelors_or_higher_rate,

  CAST(s.zcta_match_method AS STRING) AS zcta_match_method,

  CAST(s.census_acs_matched AS BOOL) AS census_acs_matched

FROM
  `california-hospital-pricing.hospital_pricing.dim_sutter_location` s

LEFT JOIN (
  SELECT
    facility_id,

    ANY_VALUE(mrf_location_name) AS mrf_location_name,
    ANY_VALUE(mrf_hospital_name) AS mrf_hospital_name,
    ANY_VALUE(mrf_address) AS mrf_address,
    ANY_VALUE(mrf_license_number) AS mrf_license_number,
    ANY_VALUE(mrf_type_2_npi) AS mrf_type_2_npi,
    ANY_VALUE(mrf_last_updated_on) AS mrf_last_updated_on,
    ANY_VALUE(mrf_version) AS mrf_version

  FROM
    `california-hospital-pricing.hospital_pricing.fact_sutter_negotiated_price`

  GROUP BY
    facility_id
) m

USING (facility_id);