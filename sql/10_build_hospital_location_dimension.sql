CREATE OR REPLACE TABLE
  `california-hospital-pricing.hospital_pricing.dim_hospital_location`

CLUSTER BY
  system_name,
  facility_id

AS

-- ============================================================
-- Kaiser Permanente
-- One row per actual MRF location/campus
-- ============================================================

SELECT
  'Kaiser Permanente' AS system_name,

  k.facility_id,
  k.mrf_location_name,

  -- MRF identity
  k.mrf_hospital_name,
  k.mrf_address,
  k.mrf_license_number,
  k.mrf_type_2_npi,

  CAST(NULL AS STRING) AS mrf_last_updated_on,
  CAST(NULL AS STRING) AS mrf_as_of_date,
  CAST(NULL AS STRING) AS mrf_version,

  -- CMS / general hospital identity
  f.cms_facility_name AS facility_name,

  CAST(NULL AS STRING) AS address,
  k.hcai_city AS city,
  'CA' AS state,
  k.hcai_zip AS zip_code,
  CAST(NULL AS STRING) AS county,
  CAST(NULL AS STRING) AS telephone_number,

  f.hospital_type,
  f.hospital_ownership,
  f.emergency_services,
  f.overall_rating,

  TRUE AS analysis_eligible,

  -- HCAI
  k.hcai_id,
  k.hcai_facility_name_dim AS hcai_facility_name,
  k.hcai_address_dim AS hcai_address,
  k.hcai_city,
  k.hcai_zip AS hcai_zip_code,

  k.longitude,
  k.latitude,

  k.license_type,
  k.license_category,
  k.facility_level,
  k.er_service_level,
  k.licensed_beds,
  k.facility_status,

  -- Matching
  k.match_method,
  k.combined_score AS match_score,

  -- ACS / ZCTA
  k.zcta AS census_zcta,
  k.zcta_name AS census_zcta_name,
  k.population AS zcta_population,
  k.median_household_income AS zcta_median_household_income,
  k.poverty_rate AS zcta_poverty_rate,
  k.uninsured_rate AS zcta_uninsured_rate,
  k.unemployment_rate AS zcta_unemployment_rate,
  k.bachelors_or_higher_rate AS zcta_bachelors_or_higher_rate,

  CAST(NULL AS STRING) AS zcta_match_method,

  k.zcta IS NOT NULL AS census_acs_matched

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
-- One eligible MRF location per CMS facility
-- ============================================================

SELECT
  u.system_name,

  u.facility_id,
  m.mrf_location_name,

  -- MRF identity
  m.mrf_hospital_name,
  m.mrf_address,
  m.mrf_license_number,
  m.mrf_type_2_npi,
  m.mrf_last_updated_on,
  m.mrf_as_of_date,
  m.mrf_version,

  -- CMS / general hospital identity
  u.facility_name,
  u.address,
  u.city,
  u.state,
  u.zip_code,
  u.county,
  u.telephone_number,

  u.hospital_type,
  u.hospital_ownership,
  u.emergency_services,
  u.overall_rating,

  u.analysis_eligible,

  -- HCAI
  u.hcai_id,
  u.hcai_facility_name,
  u.hcai_address,
  u.hcai_city,
  u.hcai_zip_code,

  u.longitude,
  u.latitude,

  CAST(NULL AS STRING) AS license_type,
  u.license_category,
  u.facility_level,
  u.er_service_level,
  u.licensed_beds,
  u.facility_status,

  -- Matching
  u.match_method,
  u.match_score,

  -- ACS / ZCTA
  u.census_zcta,
  u.census_zcta_name,
  u.zcta_population,
  u.zcta_median_household_income,
  u.zcta_poverty_rate,
  u.zcta_uninsured_rate,
  u.zcta_unemployment_rate,
  u.zcta_bachelors_or_higher_rate,

  u.zcta_match_method,
  u.census_acs_matched

FROM
  `california-hospital-pricing.hospital_pricing.dim_ucla_location` u

LEFT JOIN (
  SELECT
    facility_id,
    mrf_location_name,

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
    facility_id,
    mrf_location_name
) m
USING (facility_id);