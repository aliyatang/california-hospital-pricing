CREATE OR REPLACE VIEW
  `california-hospital-pricing.hospital_pricing.fact_negotiated_price_all_systems`

AS

-- ============================================================
-- Kaiser Permanente
-- ============================================================

SELECT
  system_name,
  facility_id,
  mrf_location_name,

  description,
  CAST(NULL AS STRING) AS billing_class,

  CAST(code_1 AS STRING) AS code_1,
  CAST(code_1_type AS STRING) AS code_1_type,
  CAST(code_2 AS STRING) AS code_2,
  CAST(code_2_type AS STRING) AS code_2_type,
  CAST(NULL AS STRING) AS all_codes_json,

  modifier,
  modifiers,

  CAST(drug_unit_of_measurement AS STRING) AS drug_unit,
  drug_type_of_measurement AS drug_type,

  setting,

  gross_charge,
  discounted_cash_charge,
  minimum_charge,
  maximum_charge,

  additional_generic_notes,

  payer,
  plan,

  negotiated_dollar,
  negotiated_percentage,
  negotiated_algorithm,

  median_amount,
  p10_amount,
  p90_amount,

  negotiated_count,
  methodology,
  additional_payer_notes,

  has_negotiated_dollar,
  has_negotiated_percentage,
  has_negotiated_algorithm,
  has_negotiated_price,

  price_representation,

  'CSV' AS source_format,

  source_row_number,

  CAST(NULL AS INT64) AS source_service_number,
  CAST(NULL AS INT64) AS source_charge_number,
  CAST(NULL AS INT64) AS source_payer_number,
  CAST(NULL AS STRING) AS source_record_id,

  mrf_url,
  source_page_url,

  CAST(NULL AS STRING) AS mrf_hospital_name,
  CAST(NULL AS STRING) AS mrf_address,
  CAST(NULL AS STRING) AS mrf_license_number,
  CAST(NULL AS STRING) AS mrf_type_2_npi,
  CAST(NULL AS STRING) AS mrf_last_updated_on,
  CAST(NULL AS STRING) AS mrf_as_of_date,
  CAST(NULL AS STRING) AS mrf_version

FROM
  `california-hospital-pricing.hospital_pricing.fact_kaiser_negotiated_price`


UNION ALL


-- ============================================================
-- UCLA Health
-- ============================================================

SELECT
  system_name,
  facility_id,
  mrf_location_name,

  description,
  CAST(NULL AS STRING) AS billing_class,

  CAST(code_1 AS STRING) AS code_1,
  CAST(code_1_type AS STRING) AS code_1_type,
  CAST(code_2 AS STRING) AS code_2,
  CAST(code_2_type AS STRING) AS code_2_type,
  CAST(all_codes_json AS STRING) AS all_codes_json,

  modifier,
  modifiers,

  CAST(drug_unit AS STRING) AS drug_unit,
  drug_type,

  setting,

  gross_charge,
  discounted_cash_charge,
  minimum_charge,
  maximum_charge,

  additional_generic_notes,

  payer,
  plan,

  negotiated_dollar,
  negotiated_percentage,
  negotiated_algorithm,

  median_amount,
  p10_amount,
  p90_amount,

  negotiated_count,
  methodology,
  additional_payer_notes,

  has_negotiated_dollar,
  has_negotiated_percentage,
  has_negotiated_algorithm,
  has_negotiated_price,

  price_representation,

  'JSON' AS source_format,

  CAST(NULL AS INT64) AS source_row_number,

  source_service_number,
  source_charge_number,
  source_payer_number,
  source_record_id,

  CAST(NULL AS STRING) AS mrf_url,
  CAST(NULL AS STRING) AS source_page_url,

  mrf_hospital_name,
  mrf_address,
  mrf_license_number,
  mrf_type_2_npi,
  mrf_last_updated_on,
  mrf_as_of_date,
  mrf_version

FROM
  `california-hospital-pricing.hospital_pricing.fact_ucla_negotiated_price`


UNION ALL


-- ============================================================
-- Sutter Health
-- ============================================================

SELECT
  CAST(system_name AS STRING) AS system_name,
  CAST(facility_id AS STRING) AS facility_id,
  CAST(mrf_location_name AS STRING) AS mrf_location_name,

  CAST(description AS STRING) AS description,
  CAST(billing_class AS STRING) AS billing_class,

  CAST(code_1 AS STRING) AS code_1,
  CAST(code_1_type AS STRING) AS code_1_type,
  CAST(code_2 AS STRING) AS code_2,
  CAST(code_2_type AS STRING) AS code_2_type,
  CAST(all_codes_json AS STRING) AS all_codes_json,

  CAST(modifier AS STRING) AS modifier,
  CAST(modifiers AS STRING) AS modifiers,

  CAST(drug_unit AS STRING) AS drug_unit,
  CAST(drug_type AS STRING) AS drug_type,

  CAST(setting AS STRING) AS setting,

  CAST(gross_charge AS FLOAT64) AS gross_charge,
  CAST(discounted_cash_charge AS FLOAT64) AS discounted_cash_charge,
  CAST(minimum_charge AS FLOAT64) AS minimum_charge,
  CAST(maximum_charge AS FLOAT64) AS maximum_charge,

  CAST(additional_generic_notes AS STRING) AS additional_generic_notes,

  CAST(payer AS STRING) AS payer,
  CAST(plan AS STRING) AS plan,

  CAST(negotiated_dollar AS FLOAT64) AS negotiated_dollar,
  CAST(negotiated_percentage AS FLOAT64) AS negotiated_percentage,
  CAST(negotiated_algorithm AS STRING) AS negotiated_algorithm,

  CAST(median_amount AS FLOAT64) AS median_amount,
  CAST(p10_amount AS FLOAT64) AS p10_amount,
  CAST(p90_amount AS FLOAT64) AS p90_amount,

  CAST(negotiated_count AS STRING) AS negotiated_count,
  CAST(methodology AS STRING) AS methodology,
  CAST(additional_payer_notes AS STRING) AS additional_payer_notes,

  CAST(has_negotiated_dollar AS BOOL) AS has_negotiated_dollar,
  CAST(has_negotiated_percentage AS BOOL) AS has_negotiated_percentage,
  CAST(has_negotiated_algorithm AS BOOL) AS has_negotiated_algorithm,
  CAST(has_negotiated_price AS BOOL) AS has_negotiated_price,

  CAST(price_representation AS STRING) AS price_representation,

  CAST('CSV' AS STRING) AS source_format,

  CAST(source_row_number AS INT64) AS source_row_number,

  CAST(NULL AS INT64) AS source_service_number,
  CAST(NULL AS INT64) AS source_charge_number,
  CAST(NULL AS INT64) AS source_payer_number,

  CAST(source_record_id AS STRING) AS source_record_id,

  CAST(NULL AS STRING) AS mrf_url,
  CAST(NULL AS STRING) AS source_page_url,

  CAST(mrf_hospital_name AS STRING) AS mrf_hospital_name,
  CAST(mrf_address AS STRING) AS mrf_address,
  CAST(mrf_license_number AS STRING) AS mrf_license_number,
  CAST(mrf_type_2_npi AS STRING) AS mrf_type_2_npi,
  CAST(mrf_last_updated_on AS STRING) AS mrf_last_updated_on,

  CAST(NULL AS STRING) AS mrf_as_of_date,

  CAST(mrf_version AS STRING) AS mrf_version

FROM
  `california-hospital-pricing.hospital_pricing.fact_sutter_negotiated_price`;