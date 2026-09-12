CREATE OR REPLACE VIEW
  `california-hospital-pricing.hospital_pricing.dashboard_msdrg_detail`

AS

SELECT
  msdrg_code,
  description,

  payer_category,
  payer_family,

  ROUND(
    ucla_price,
    2
  ) AS ucla_price,

  ROUND(
    sutter_price,
    2
  ) AS sutter_price,

  ROUND(
    absolute_price_difference,
    2
  ) AS absolute_price_difference,

  ROUND(
    ucla_vs_sutter_ratio,
    3
  ) AS ucla_vs_sutter_ratio,

  ROUND(
    ucla_vs_sutter_pct_difference,
    1
  ) AS ucla_vs_sutter_pct_difference,

  ucla_higher,

  ucla_plan_count,
  sutter_plan_count,

  ucla_location_count,
  sutter_location_count

FROM
  `california-hospital-pricing.hospital_pricing.mart_ucla_sutter_paired_differences`;