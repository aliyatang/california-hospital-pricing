CREATE OR REPLACE VIEW
  `california-hospital-pricing.hospital_pricing.mart_ucla_sutter_paired_differences`

AS

WITH paired AS (

  SELECT
    msdrg_code,
    payer_family,
    payer_category,

    ANY_VALUE(description) AS description,

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
    ) AS sutter_price,

    MAX(
      IF(
        system_name = 'UCLA Health',
        plan_count,
        NULL
      )
    ) AS ucla_plan_count,

    MAX(
      IF(
        system_name = 'Sutter Health',
        plan_count,
        NULL
      )
    ) AS sutter_plan_count,

    MAX(
      IF(
        system_name = 'UCLA Health',
        location_count,
        NULL
      )
    ) AS ucla_location_count,

    MAX(
      IF(
        system_name = 'Sutter Health',
        location_count,
        NULL
      )
    ) AS sutter_location_count

  FROM
    `california-hospital-pricing.hospital_pricing.mart_ucla_sutter_insurer_msdrg`

  GROUP BY
    msdrg_code,
    payer_family,
    payer_category
)

SELECT
  *,

  SAFE_DIVIDE(
    ucla_price,
    sutter_price
  ) AS ucla_vs_sutter_ratio,

  100 * (
    SAFE_DIVIDE(
      ucla_price,
      sutter_price
    ) - 1
  ) AS ucla_vs_sutter_pct_difference,

  LN(
    SAFE_DIVIDE(
      ucla_price,
      sutter_price
    )
  ) AS log_price_ratio,

  ucla_price - sutter_price
    AS absolute_price_difference,

  ucla_price > sutter_price
    AS ucla_higher

FROM paired

WHERE
  ucla_price > 0
  AND sutter_price > 0;