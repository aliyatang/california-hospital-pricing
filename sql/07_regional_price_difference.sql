WITH priced AS (
  SELECT
    f.code_1_type,
    f.code_1,
    f.description,
    f.plan AS payer_plan,
    f.facility_id,
    f.mrf_location_name,
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
)

SELECT
  payer_plan,
  COUNT(*) AS procedure_count,

  ROUND(
    AVG(north_price),
    2
  ) AS avg_north_price,

  ROUND(
    AVG(south_price),
    2
  ) AS avg_south_price,

  ROUND(
    AVG(north_price - south_price),
    2
  ) AS avg_absolute_difference,

  ROUND(
    AVG(
      SAFE_DIVIDE(
        north_price,
        south_price
      )
    ),
    3
  ) AS avg_north_to_south_ratio,

  ROUND(
    100 * AVG(
      SAFE_DIVIDE(
        north_price - south_price,
        south_price
      )
    ),
    2
  ) AS avg_pct_difference

FROM paired
WHERE north_price IS NOT NULL
  AND south_price IS NOT NULL
  AND south_price > 0
GROUP BY payer_plan
ORDER BY avg_north_to_south_ratio DESC;