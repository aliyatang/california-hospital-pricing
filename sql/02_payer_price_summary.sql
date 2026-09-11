SELECT
  plan,
  COUNT(*) AS row_count,
  ROUND(AVG(negotiated_dollar), 2) AS avg_negotiated_price,
  ROUND(APPROX_QUANTILES(negotiated_dollar, 100)[OFFSET(50)], 2) AS median_negotiated_price,
  ROUND(MIN(negotiated_dollar), 2) AS min_negotiated_price,
  ROUND(MAX(negotiated_dollar), 2) AS max_negotiated_price
FROM `california-hospital-pricing.hospital_pricing.fact_kaiser_negotiated_price`
WHERE price_representation = 'dollar'
  AND negotiated_dollar IS NOT NULL
GROUP BY plan
ORDER BY avg_negotiated_price DESC;