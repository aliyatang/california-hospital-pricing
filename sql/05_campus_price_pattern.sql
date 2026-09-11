SELECT
  f.facility_id,
  f.mrf_location_name,
  d.hcai_city,
  d.latitude,
  ROUND(AVG(f.negotiated_dollar), 2) AS avg_price
FROM `california-hospital-pricing.hospital_pricing.fact_kaiser_negotiated_price` AS f
JOIN `california-hospital-pricing.hospital_pricing.dim_kaiser_location` AS d
  ON f.facility_id = d.facility_id
  AND f.mrf_location_name = d.mrf_location_name
WHERE f.price_representation = 'dollar'
  AND f.code_1_type = 'MS-DRG'
  AND f.code_1 = '18'
  AND f.plan = 'COMMERCIAL'
GROUP BY
  f.facility_id,
  f.mrf_location_name,
  d.hcai_city,
  d.latitude
ORDER BY
  d.latitude DESC;