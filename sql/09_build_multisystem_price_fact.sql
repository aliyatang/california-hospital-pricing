CREATE OR REPLACE TABLE
  `california-hospital-pricing.hospital_pricing.fact_negotiated_price_all_systems`

CLUSTER BY
  system_name,
  facility_id,
  code_1_type,
  payer

AS

-- ============================================================
-- Kaiser Permanente
-- ============================================================

SELECT
  system_name,
  facility_id,
  mrf_location_name,

  description,

  code_1,
  code_1_type,
  code_2,
  code_2_type,

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

  -- provenance
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

  code_1,
  code_1_type,
  code_2,
  code_2_type,

  all_codes_json,

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

  -- provenance
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
  `california-hospital-pricing.hospital_pricing.fact_ucla_negotiated_price`;