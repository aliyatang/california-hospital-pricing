-- ============================================================
-- UCLA vs Sutter matched insurer-family MS-DRG differences
-- ============================================================

WITH paired AS (

  SELECT
    msdrg_code,
    payer_family,
    payer_category,

    MAX(
      IF(
        system_name = 'UCLA Health',
        median_system_price,
        NULL
      )
    ) AS ucla_price,

    MAX(
      IF(
        system_name = 'Sutter Health',
        median_system_price,
        NULL
      )
    ) AS sutter_price

  FROM
    `california-hospital-pricing.hospital_pricing.mart_ucla_sutter_insurer_msdrg`

  GROUP BY
    msdrg_code,
    payer_family,
    payer_category
),

ratios AS (

  SELECT
    *,

    SAFE_DIVIDE(
      ucla_price,
      sutter_price
    ) AS ucla_vs_sutter_ratio

  FROM paired

  WHERE
    ucla_price > 0
    AND sutter_price > 0
)

SELECT
  payer_family,
  payer_category,

  COUNT(*) AS matched_msdrgs,

  ROUND(
    APPROX_QUANTILES(
      ucla_price,
      100
    )[OFFSET(50)],
    2
  ) AS median_ucla_price,

  ROUND(
    APPROX_QUANTILES(
      sutter_price,
      100
    )[OFFSET(50)],
    2
  ) AS median_sutter_price,

  ROUND(
    APPROX_QUANTILES(
      ucla_vs_sutter_ratio,
      100
    )[OFFSET(25)],
    3
  ) AS p25_ratio,

  ROUND(
    APPROX_QUANTILES(
      ucla_vs_sutter_ratio,
      100
    )[OFFSET(50)],
    3
  ) AS median_ucla_vs_sutter_ratio,

  ROUND(
    APPROX_QUANTILES(
      ucla_vs_sutter_ratio,
      100
    )[OFFSET(75)],
    3
  ) AS p75_ratio,

  ROUND(
    100 * (
      APPROX_QUANTILES(
        ucla_vs_sutter_ratio,
        100
      )[OFFSET(50)] - 1
    ),
    1
  ) AS median_ucla_vs_sutter_pct,

  ROUND(
    100 * SAFE_DIVIDE(
      COUNTIF(ucla_price > sutter_price),
      COUNT(*)
    ),
    1
  ) AS pct_msdrgs_ucla_higher

FROM ratios

GROUP BY
  payer_family,
  payer_category

ORDER BY
  payer_category,
  median_ucla_vs_sutter_ratio DESC;