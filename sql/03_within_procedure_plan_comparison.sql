WITH procedure_prices AS (
  SELECT
    code_1_type,
    code_1,
    description,
    plan,
    AVG(negotiated_dollar) AS avg_price
  FROM `california-hospital-pricing.hospital_pricing.fact_kaiser_negotiated_price`
  WHERE price_representation = 'dollar'
    AND negotiated_dollar IS NOT NULL
    AND code_1 IS NOT NULL
  GROUP BY
    code_1_type,
    code_1,
    description,
    plan
),

pivoted AS (
  SELECT
    code_1_type,
    code_1,
    description,
    MAX(IF(plan = 'COMMERCIAL', avg_price, NULL)) AS commercial_price,
    MAX(IF(plan = 'MEDICARE', avg_price, NULL)) AS medicare_price,
    MAX(IF(plan = 'MEDICAID', avg_price, NULL)) AS medicaid_price
  FROM procedure_prices
  GROUP BY
    code_1_type,
    code_1,
    description
)

SELECT
  code_1_type,
  code_1,
  description,
  ROUND(commercial_price, 2) AS commercial_price,
  ROUND(medicare_price, 2) AS medicare_price,
  ROUND(medicaid_price, 2) AS medicaid_price,
  ROUND(commercial_price / medicare_price, 2) AS commercial_to_medicare_ratio,
  ROUND(commercial_price / medicaid_price, 2) AS commercial_to_medicaid_ratio
FROM pivoted
WHERE commercial_price IS NOT NULL
  AND medicare_price IS NOT NULL
  AND medicaid_price IS NOT NULL
  AND medicare_price > 0
  AND medicaid_price > 0
ORDER BY commercial_to_medicare_ratio DESC
LIMIT 50;