CREATE OR REPLACE VIEW
  `california-hospital-pricing.hospital_pricing.mart_msdrg_system_comparison`

AS

WITH eligible AS (

  SELECT *
  FROM
    `california-hospital-pricing.hospital_pricing.mart_comparable_prices`

  WHERE
    procedure_code_type = 'MS-DRG'
    AND is_all_three_systems = TRUE
    AND payer_category IN (
      'Commercial',
      'Medicare'
    )
),

system_grouped AS (

  SELECT
    system_name,
    procedure_code AS msdrg_code,
    payer_category,

    ARRAY_AGG(
      description
      IGNORE NULLS
      LIMIT 1
    )[SAFE_OFFSET(0)] AS description,

    COUNT(*) AS location_observations,

    COUNT(
      DISTINCT CONCAT(
        facility_id,
        '|',
        mrf_location_name
      )
    ) AS location_count,

    AVG(
      median_negotiated_price
    ) AS mean_location_price,

    APPROX_QUANTILES(
      median_negotiated_price,
      100
    )[OFFSET(50)] AS median_system_price,

    MIN(
      median_negotiated_price
    ) AS min_location_price,

    MAX(
      median_negotiated_price
    ) AS max_location_price,

    STDDEV(
      median_negotiated_price
    ) AS sd_location_price

  FROM eligible

  GROUP BY
    system_name,
    procedure_code,
    payer_category
),

matched AS (

  SELECT
    msdrg_code,
    payer_category,

    COUNT(DISTINCT system_name) AS system_count,

    APPROX_QUANTILES(
      median_system_price,
      100
    )[OFFSET(50)] AS matched_group_median_price,

    AVG(
      median_system_price
    ) AS matched_group_mean_price

  FROM system_grouped

  GROUP BY
    msdrg_code,
    payer_category
)

SELECT
  s.*,

  m.matched_group_median_price,
  m.matched_group_mean_price,

  SAFE_DIVIDE(
    s.median_system_price,
    m.matched_group_median_price
  ) AS price_index,

  LN(
    s.median_system_price
  ) AS log_price

FROM system_grouped s

JOIN matched m
USING (
  msdrg_code,
  payer_category
)

WHERE
  m.system_count = 3;