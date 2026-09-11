WITH procedure_hospital_prices AS (
  SELECT
    code_1_type,
    code_1,
    description,
    plan AS payer_plan,
    facility_id,
    mrf_location_name,
    AVG(negotiated_dollar) AS hospital_price
  FROM `california-hospital-pricing.hospital_pricing.fact_kaiser_negotiated_price`
  WHERE price_representation = 'dollar'
    AND negotiated_dollar IS NOT NULL
    AND code_1 IS NOT NULL
  GROUP BY
    code_1_type,
    code_1,
    description,
    plan,
    facility_id,
    mrf_location_name
),

variation AS (
  SELECT
    code_1_type,
    code_1,
    description,
    payer_plan,
    COUNT(*) AS hospital_count,
    MIN(hospital_price) AS min_price,
    MAX(hospital_price) AS max_price,
    AVG(hospital_price) AS avg_price,
    STDDEV(hospital_price) AS price_stddev
  FROM procedure_hospital_prices
  WHERE hospital_price > 0
  GROUP BY
    code_1_type,
    code_1,
    description,
    payer_plan
)

SELECT
  code_1_type,
  code_1,
  description,
  payer_plan,
  hospital_count,
  ROUND(min_price, 2) AS min_price,
  ROUND(max_price, 2) AS max_price,
  ROUND(avg_price, 2) AS avg_price,
  ROUND(max_price - min_price, 2) AS price_range,
  ROUND(price_stddev, 2) AS price_stddev,
  ROUND(SAFE_DIVIDE(price_stddev, avg_price), 3) AS coefficient_of_variation,
  ROUND(SAFE_DIVIDE(max_price, min_price), 2) AS max_to_min_ratio
FROM variation
WHERE hospital_count >= 20
  AND avg_price >= 100
ORDER BY price_range DESC
LIMIT 50;