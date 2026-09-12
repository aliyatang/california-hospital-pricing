CREATE OR REPLACE VIEW
  `california-hospital-pricing.hospital_pricing.dashboard_category_summary`

AS

SELECT
  payer_category,

  COUNT(*) AS matched_pairs,

  COUNT(
    DISTINCT msdrg_code
  ) AS unique_msdrgs,

  COUNT(
    DISTINCT payer_family
  ) AS insurer_families,

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
  ) AS median_ratio,

  ROUND(
    APPROX_QUANTILES(
      ucla_vs_sutter_ratio,
      100
    )[OFFSET(75)],
    3
  ) AS p75_ratio,

  ROUND(
    EXP(
      AVG(log_price_ratio)
    ),
    3
  ) AS geometric_mean_ratio,

  ROUND(
    100 * (
      EXP(
        AVG(log_price_ratio)
      ) - 1
    ),
    1
  ) AS geometric_mean_pct_difference,

  ROUND(
    100 * AVG(
      CAST(ucla_higher AS INT64)
    ),
    1
  ) AS pct_ucla_higher,

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
  ) AS median_sutter_price

FROM
  `california-hospital-pricing.hospital_pricing.mart_ucla_sutter_paired_differences`

GROUP BY
  payer_category;