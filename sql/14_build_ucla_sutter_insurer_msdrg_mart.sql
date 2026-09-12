CREATE OR REPLACE VIEW
  `california-hospital-pricing.hospital_pricing.mart_ucla_sutter_insurer_msdrg`

AS

-- ============================================================
-- UCLA vs Sutter matched MS-DRG + insurer-family comparison
--
-- Aggregation hierarchy:
-- raw price -> plan -> hospital location -> health system
--
-- This prevents hospitals/plans with more source rows from
-- receiving disproportionate weight.
-- ============================================================

WITH base AS (

  SELECT
    system_name,
    facility_id,
    mrf_location_name,

    CAST(code_1 AS STRING) AS msdrg_code,
    description,

    payer,
    plan,
    negotiated_dollar,

    CASE
      WHEN REGEXP_CONTAINS(
        UPPER(COALESCE(payer, '')),
        r'ANTHEM'
      )
        THEN 'Anthem'

      WHEN REGEXP_CONTAINS(
        UPPER(COALESCE(payer, '')),
        r'BLUE SHIELD'
      )
        THEN 'Blue Shield'

      WHEN REGEXP_CONTAINS(
        UPPER(COALESCE(payer, '')),
        r'AETNA'
      )
        THEN 'Aetna'

      WHEN REGEXP_CONTAINS(
        UPPER(COALESCE(payer, '')),
        r'CIGNA'
      )
        THEN 'Cigna'

      WHEN REGEXP_CONTAINS(
        UPPER(COALESCE(payer, '')),
        r'UNITEDHEALTHCARE|UHC|UNITED'
      )
        THEN 'UnitedHealthcare'

      WHEN REGEXP_CONTAINS(
        UPPER(COALESCE(payer, '')),
        r'HEALTH NET'
      )
        THEN 'Health Net'

      ELSE NULL
    END AS payer_family,

    UPPER(
      CONCAT(
        COALESCE(payer, ''),
        ' ',
        COALESCE(plan, '')
      )
    ) AS payer_plan_text

  FROM
    `california-hospital-pricing.hospital_pricing.fact_negotiated_price_all_systems`

  WHERE
    system_name IN (
      'UCLA Health',
      'Sutter Health'
    )

    AND UPPER(TRIM(code_1_type)) = 'MS-DRG'

    AND code_1 IS NOT NULL

    AND has_negotiated_dollar = TRUE

    AND negotiated_dollar IS NOT NULL
    AND negotiated_dollar > 0
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
        r'MEDICAID|MEDI-CAL|MEDI CAL|MEDICAL HMO'
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

      -- If this is one of the recognized private insurer
      -- families and was not classified above as a government
      -- program, treat it as Commercial.
      WHEN payer_family IS NOT NULL
        THEN 'Commercial'

      ELSE 'Other / Unclassified'
    END AS payer_category

  FROM base

  WHERE
    payer_family IS NOT NULL
),

-- ------------------------------------------------------------
-- Step 1: one price per individual plan
-- ------------------------------------------------------------

plan_grouped AS (

  SELECT
    system_name,
    facility_id,
    mrf_location_name,

    msdrg_code,
    payer_family,
    payer_category,

    payer,
    plan,

    ARRAY_AGG(
      description
      IGNORE NULLS
      LIMIT 1
    )[SAFE_OFFSET(0)] AS description,

    COUNT(*) AS source_row_count,

    APPROX_QUANTILES(
      negotiated_dollar,
      100
    )[OFFSET(50)] AS plan_median_price

  FROM categorized

  GROUP BY
    system_name,
    facility_id,
    mrf_location_name,
    msdrg_code,
    payer_family,
    payer_category,
    payer,
    plan
),

-- ------------------------------------------------------------
-- Step 2: one price per hospital location
--
-- Each plan receives equal weight within a location.
-- ------------------------------------------------------------

location_grouped AS (

  SELECT
    system_name,
    facility_id,
    mrf_location_name,

    msdrg_code,
    payer_family,
    payer_category,

    ARRAY_AGG(
      description
      IGNORE NULLS
      LIMIT 1
    )[SAFE_OFFSET(0)] AS description,

    COUNT(*) AS plan_count,

    SUM(
      source_row_count
    ) AS source_row_count,

    AVG(
      plan_median_price
    ) AS mean_plan_price,

    APPROX_QUANTILES(
      plan_median_price,
      100
    )[OFFSET(50)] AS median_location_price

  FROM plan_grouped

  GROUP BY
    system_name,
    facility_id,
    mrf_location_name,
    msdrg_code,
    payer_family,
    payer_category
),

-- ------------------------------------------------------------
-- Step 3: one price per health system
--
-- Each hospital location receives equal weight.
-- ------------------------------------------------------------

system_grouped AS (

  SELECT
    system_name,

    msdrg_code,
    payer_family,
    payer_category,

    ARRAY_AGG(
      description
      IGNORE NULLS
      LIMIT 1
    )[SAFE_OFFSET(0)] AS description,

    COUNT(*) AS location_count,

    SUM(
      plan_count
    ) AS plan_count,

    SUM(
      source_row_count
    ) AS source_row_count,

    AVG(
      median_location_price
    ) AS mean_location_price,

    APPROX_QUANTILES(
      median_location_price,
      100
    )[OFFSET(50)] AS median_system_price,

    MIN(
      median_location_price
    ) AS min_location_price,

    MAX(
      median_location_price
    ) AS max_location_price,

    STDDEV(
      median_location_price
    ) AS sd_location_price

  FROM location_grouped

  GROUP BY
    system_name,
    msdrg_code,
    payer_family,
    payer_category
),

-- ------------------------------------------------------------
-- Keep only combinations represented by BOTH systems.
-- ------------------------------------------------------------

matched AS (

  SELECT
    msdrg_code,
    payer_family,
    payer_category,

    COUNT(
      DISTINCT system_name
    ) AS system_count,

    AVG(
      median_system_price
    ) AS pair_mean_price,

    EXP(
      AVG(
        LN(median_system_price)
      )
    ) AS pair_geometric_mean_price

  FROM system_grouped

  WHERE
    median_system_price > 0

  GROUP BY
    msdrg_code,
    payer_family,
    payer_category
)

SELECT
  s.*,

  m.pair_mean_price,
  m.pair_geometric_mean_price,

  SAFE_DIVIDE(
    s.median_system_price,
    m.pair_geometric_mean_price
  ) AS price_index,

  LN(
    s.median_system_price
  ) AS log_price

FROM system_grouped s

JOIN matched m
USING (
  msdrg_code,
  payer_family,
  payer_category
)

WHERE
  m.system_count = 2
  AND s.median_system_price > 0;