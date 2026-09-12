-- ============================================================
-- Matched MS-DRG cross-system price differences
-- ============================================================

WITH paired AS (

  SELECT
    msdrg_code,
    payer_category,

    MAX(
      IF(
        system_name = 'Kaiser Permanente',
        median_system_price,
        NULL
      )
    ) AS kaiser_price,

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
    `california-hospital-pricing.hospital_pricing.mart_msdrg_system_comparison`

  GROUP BY
    msdrg_code,
    payer_category
)

SELECT
  payer_category,

  COUNT(*) AS matched_msdrgs,

  ROUND(
    APPROX_QUANTILES(
      SAFE_DIVIDE(ucla_price, kaiser_price),
      100
    )[OFFSET(50)],
    3
  ) AS median_ucla_vs_kaiser_ratio,

  ROUND(
    APPROX_QUANTILES(
      SAFE_DIVIDE(sutter_price, kaiser_price),
      100
    )[OFFSET(50)],
    3
  ) AS median_sutter_vs_kaiser_ratio,

  ROUND(
    APPROX_QUANTILES(
      SAFE_DIVIDE(sutter_price, ucla_price),
      100
    )[OFFSET(50)],
    3
  ) AS median_sutter_vs_ucla_ratio,

  ROUND(
    100 * (
      APPROX_QUANTILES(
        SAFE_DIVIDE(ucla_price, kaiser_price),
        100
      )[OFFSET(50)] - 1
    ),
    1
  ) AS median_ucla_vs_kaiser_pct,

  ROUND(
    100 * (
      APPROX_QUANTILES(
        SAFE_DIVIDE(sutter_price, kaiser_price),
        100
      )[OFFSET(50)] - 1
    ),
    1
  ) AS median_sutter_vs_kaiser_pct,

  ROUND(
    100 * (
      APPROX_QUANTILES(
        SAFE_DIVIDE(sutter_price, ucla_price),
        100
      )[OFFSET(50)] - 1
    ),
    1
  ) AS median_sutter_vs_ucla_pct

FROM paired

WHERE
  kaiser_price > 0
  AND ucla_price > 0
  AND sutter_price > 0

GROUP BY
  payer_category

ORDER BY
  payer_category;