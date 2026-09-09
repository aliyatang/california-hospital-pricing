# California Hospital Pricing

End-to-end data engineering and data science project analyzing hospital price variation across California using hospital price transparency data, CMS hospital information, California HCAI data, and U.S. Census socioeconomic data.

## Project Goals

- Build a scalable pipeline for discovering and ingesting hospital machine-readable pricing files
- Standardize hospital pricing data across common healthcare procedure codes
- Integrate hospital characteristics and socioeconomic data
- Analyze variation in negotiated healthcare prices across California hospitals
- Identify hospital, payer, and socioeconomic factors associated with price variation
- Develop visualizations for geographic and demographic pricing patterns

## Data Sources

### CMS
[Hospital General Information](https://data.cms.gov/provider-data/dataset/xubh-q36u) — CMS Provider Data Catalog dataset containing Medicare-registered hospitals, facility IDs, locations, hospital types, ownership, and overall ratings.

### Hospital Price Transparency
[CMS Hospital Price Transparency](https://www.cms.gov/priorities/key-initiatives/hospital-price-transparency/hospitals) — Hospitals publish machine-readable files containing gross charges, discounted cash prices, payer-specific negotiated charges, and other standard charge information.

### California HCAI
[Hospital Financials](https://hcai.ca.gov/data/cost-transparency/hospital-financials/) — California hospital financial, utilization, ownership, bed, revenue, and payer data.

[Healthcare Facility Attributes](https://hcai.ca.gov/data/data-resources/healthcare-facility-attributes/) — Facility-level information and licensed healthcare facility listings for California hospitals.

### U.S. Census ACS
[2024 American Community Survey 5-Year Data](https://www.census.gov/data/developers/data-sets/acs-5year/2024.html) — Socioeconomic and demographic data including household income, poverty, insurance coverage, education, and population.

## Project Structure

```text
california-hospital-pricing/
├── config/
├── data/
│   ├── raw/
│   ├── interim/
│   └── processed/
├── notebooks/
├── src/
│   ├── ingest/
│   ├── transform/
│   ├── analysis/
│   └── utils/
├── sql/
├── tableau/
└── tests/