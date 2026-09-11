WITH priced AS (
  SELECT
    f.code_1_type,
    f.code_1,
    f.description,
    f.plan,
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

hospital_prices AS (
  SELECT
    code_1_type,
    code_1,
    plan AS payer_plan,
    geographic_group,
    facility_id,
    mrf_location_name,
    AVG(negotiated_dollar) AS hospital_price
  FROM priced
  GROUP BY
    code_1_type,
    code_1,
    plan,
    geographic_group,
    facility_id,
    mrf_location_name
),

regional AS (
  SELECT
    code_1_type,
    code_1,
    payer_plan,
    geographic_group,
    COUNT(*) AS campus_count,
    COUNT(DISTINCT ROUND(hospital_price, 2)) AS distinct_price_count
  FROM hospital_prices
  GROUP BY
    code_1_type,
    code_1,
    payer_plan,
    geographic_group
),

paired AS (
  SELECT
    code_1_type,
    code_1,
    payer_plan,

    MAX(IF(
      geographic_group = 'North',
      campus_count,
      NULL
    )) AS north_campus_count,

    MAX(IF(
      geographic_group = 'South',
      campus_count,
      NULL
    )) AS south_campus_count,

    MAX(IF(
      geographic_group = 'North',
      distinct_price_count,
      NULL
    )) AS north_distinct_prices,

    MAX(IF(
      geographic_group = 'South',
      distinct_price_count,
      NULL
    )) AS south_distinct_prices

  FROM regional
  GROUP BY
    code_1_type,
    code_1,
    payer_plan
),

full_coverage AS (
  SELECT *
  FROM paired
  WHERE north_campus_count = 21
    AND south_campus_count = 16
)

SELECT
  COUNT(*) AS procedure_plan_groups,
  COUNTIF(
    north_distinct_prices = 1
    AND south_distinct_prices = 1
  ) AS fixed_regional_price_groups,

  ROUND(
    100 * SAFE_DIVIDE(
      COUNTIF(
        north_distinct_prices = 1
        AND south_distinct_prices = 1
      ),
      COUNT(*)
    ),
    2
  ) AS pct_fixed_regional_pattern,

  COUNTIF(
    north_distinct_prices > 1
    OR south_distinct_prices > 1
  ) AS groups_with_within_region_variation

FROM full_coverage;