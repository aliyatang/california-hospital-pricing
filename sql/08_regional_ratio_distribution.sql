WITH priced AS (
  SELECT
    f.code_1_type,
    f.code_1,
    f.description,
    f.plan AS payer_plan,
    f.negotiated_dollar,
    CASE
      WHEN d.latitude >= 35 THEN 'North'
      ELSE 'South'
    END AS geographic_group
  FROM `california-hospital-pricing.hospital_pricing.fact_kaiser_negotiated_price` AS f
  JOIN `california-hospital-pricing.hospital_pricing.dim_kaiser_location` AS d
    ON f.facility_id = d.facility_id
    AND f.mrf_location_name = d.mrf_location_name
  WHERE f.price_representation = 'dollar'
    AND f.negotiated_dollar IS NOT NULL
    AND f.code_1 IS NOT NULL
),

regional_prices AS (
  SELECT
    code_1_type,
    code_1,
    description,
    payer_plan,
    geographic_group,
    AVG(negotiated_dollar) AS regional_price
  FROM priced
  GROUP BY
    code_1_type,
    code_1,
    description,
    payer_plan,
    geographic_group
),

paired AS (
  SELECT
    code_1_type,
    code_1,
    description,
    payer_plan,

    MAX(IF(
      geographic_group = 'North',
      regional_price,
      NULL
    )) AS north_price,

    MAX(IF(
      geographic_group = 'South',
      regional_price,
      NULL
    )) AS south_price

  FROM regional_prices
  GROUP BY
    code_1_type,
    code_1,
    description,
    payer_plan
),

ratios AS (
  SELECT
    payer_plan,
    SAFE_DIVIDE(
      north_price,
      south_price
    ) AS north_to_south_ratio
  FROM paired
  WHERE north_price IS NOT NULL
    AND south_price IS NOT NULL
    AND south_price > 0
)

SELECT
  payer_plan,
  COUNT(*) AS procedure_count,

  ROUND(
    APPROX_QUANTILES(
      north_to_south_ratio,
      100
    )[OFFSET(25)],
    3
  ) AS p25_ratio,

  ROUND(
    APPROX_QUANTILES(
      north_to_south_ratio,
      100
    )[OFFSET(50)],
    3
  ) AS median_ratio,

  ROUND(
    APPROX_QUANTILES(
      north_to_south_ratio,
      100
    )[OFFSET(75)],
    3
  ) AS p75_ratio,

  ROUND(
    AVG(north_to_south_ratio),
    3
  ) AS mean_ratio

FROM ratios
GROUP BY payer_plan
ORDER BY median_ratio DESC;