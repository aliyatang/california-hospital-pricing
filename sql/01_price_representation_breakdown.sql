SELECT
  price_representation,
  COUNT(*) AS row_count,
  ROUND(
    100.0 * COUNT(*) / SUM(COUNT(*)) OVER (),
    2
  ) AS percent_of_total
FROM `california-hospital-pricing.hospital_pricing.fact_kaiser_negotiated_price`
GROUP BY price_representation
ORDER BY row_count DESC;