CREATE OR REPLACE VIEW
  `california-hospital-pricing.hospital_pricing.mart_comparable_prices`

AS

WITH base AS (

  SELECT
    f.system_name,
    f.facility_id,
    f.mrf_location_name,

    UPPER(TRIM(f.code_1_type)) AS procedure_code_type,
    CAST(f.code_1 AS STRING) AS procedure_code,

    f.description,

    CASE
      WHEN UPPER(TRIM(f.code_1_type)) = 'MS-DRG'
        THEN 'inpatient'

      WHEN LOWER(TRIM(f.setting)) = 'inpatient'
        THEN 'inpatient'

      WHEN LOWER(TRIM(f.setting)) = 'outpatient'
        THEN 'outpatient'

      WHEN LOWER(TRIM(f.setting)) = 'both'
        THEN 'both'

      ELSE 'unknown'
    END AS comparison_setting,

    f.payer,
    f.plan,

    REGEXP_REPLACE(
      UPPER(
        CONCAT(
          COALESCE(f.payer, ''),
          ' ',
          COALESCE(f.plan, '')
        )
      ),
      r'[^A-Z0-9]+',
      ' '
    ) AS payer_plan_text,

    f.negotiated_dollar,

    d.facility_name,
    d.city,
    d.county,
    d.latitude,
    d.longitude,

    d.hospital_type,
    d.hospital_ownership,
    d.overall_rating,
    d.licensed_beds,

    d.census_zcta,
    d.zcta_population,
    d.zcta_median_household_income,
    d.zcta_poverty_rate,
    d.zcta_uninsured_rate,
    d.zcta_unemployment_rate,
    d.zcta_bachelors_or_higher_rate

  FROM
    `california-hospital-pricing.hospital_pricing.fact_negotiated_price_all_systems` f

  LEFT JOIN
    `california-hospital-pricing.hospital_pricing.dim_hospital_location` d

  ON
    f.facility_id = d.facility_id
    AND f.mrf_location_name = d.mrf_location_name

  WHERE
    f.has_negotiated_dollar = TRUE
    AND f.negotiated_dollar IS NOT NULL
    AND f.negotiated_dollar > 0

    AND f.code_1 IS NOT NULL
    AND f.code_1_type IS NOT NULL

    -- Best standardized cross-system overlap
    AND UPPER(TRIM(f.code_1_type)) IN (
      'HCPCS',
      'MS-DRG'
    )
),

categorized AS (

  SELECT
    * EXCEPT(payer_plan_text),

    CASE
      WHEN REGEXP_CONTAINS(
        payer_plan_text,
        r'WORKERS COMP|WORKER COMP'
      )
        THEN 'Workers Compensation'

      WHEN REGEXP_CONTAINS(
        payer_plan_text,
        r'MEDICAID|MEDI CAL|MEDICAL HMO'
      )
        THEN 'Medicaid'

      WHEN REGEXP_CONTAINS(
        payer_plan_text,
        r'MEDICARE'
      )
        THEN 'Medicare'

      WHEN REGEXP_CONTAINS(
        payer_plan_text,
        r'TRIWEST|TRICARE|OTHER GOVERNMENT'
      )
        THEN 'Other Government'

      WHEN REGEXP_CONTAINS(
        payer_plan_text,
        r'COMMERCIAL|PPO|HMO|EPO|INDIVIDUAL|INDEMNITY|SELECT'
      )
        THEN 'Commercial'

      ELSE 'Other / Unclassified'
    END AS payer_category

  FROM
    base
),

location_grouped AS (

  SELECT
    system_name,
    facility_id,
    mrf_location_name,

    procedure_code_type,
    procedure_code,
    comparison_setting,
    payer_category,

    ARRAY_AGG(
      description
      IGNORE NULLS
      LIMIT 1
    )[SAFE_OFFSET(0)] AS description,

    COUNT(*) AS source_row_count,

    COUNT(
      DISTINCT payer
    ) AS raw_payer_count,

    COUNT(
      DISTINCT plan
    ) AS raw_plan_count,

    AVG(
      negotiated_dollar
    ) AS mean_negotiated_price,

    APPROX_QUANTILES(
      negotiated_dollar,
      100
    )[OFFSET(50)] AS median_negotiated_price,

    MIN(
      negotiated_dollar
    ) AS min_negotiated_price,

    MAX(
      negotiated_dollar
    ) AS max_negotiated_price,

    STDDEV(
      negotiated_dollar
    ) AS sd_negotiated_price,

    ANY_VALUE(
      facility_name
    ) AS facility_name,

    ANY_VALUE(city) AS city,
    ANY_VALUE(county) AS county,

    ANY_VALUE(latitude) AS latitude,
    ANY_VALUE(longitude) AS longitude,

    ANY_VALUE(
      hospital_type
    ) AS hospital_type,

    ANY_VALUE(
      hospital_ownership
    ) AS hospital_ownership,

    ANY_VALUE(
      overall_rating
    ) AS overall_rating,

    ANY_VALUE(
      licensed_beds
    ) AS licensed_beds,

    ANY_VALUE(
      census_zcta
    ) AS census_zcta,

    ANY_VALUE(
      zcta_population
    ) AS zcta_population,

    ANY_VALUE(
      zcta_median_household_income
    ) AS zcta_median_household_income,

    ANY_VALUE(
      zcta_poverty_rate
    ) AS zcta_poverty_rate,

    ANY_VALUE(
      zcta_uninsured_rate
    ) AS zcta_uninsured_rate,

    ANY_VALUE(
      zcta_unemployment_rate
    ) AS zcta_unemployment_rate,

    ANY_VALUE(
      zcta_bachelors_or_higher_rate
    ) AS zcta_bachelors_or_higher_rate

  FROM
    categorized

  GROUP BY
    system_name,
    facility_id,
    mrf_location_name,
    procedure_code_type,
    procedure_code,
    comparison_setting,
    payer_category
),

coverage AS (

  SELECT
    procedure_code_type,
    procedure_code,
    comparison_setting,
    payer_category,

    COUNT(
      DISTINCT system_name
    ) AS system_count,

    COUNT(
      DISTINCT CONCAT(
        facility_id,
        '|',
        mrf_location_name
      )
    ) AS location_count

  FROM
    location_grouped

  GROUP BY
    procedure_code_type,
    procedure_code,
    comparison_setting,
    payer_category
)

SELECT
  g.*,

  c.system_count,
  c.location_count,

  c.system_count >= 2
    AS is_cross_system_comparable,

  c.system_count = 3
    AS is_all_three_systems

FROM
  location_grouped g

LEFT JOIN
  coverage c

USING (
  procedure_code_type,
  procedure_code,
  comparison_setting,
  payer_category
);