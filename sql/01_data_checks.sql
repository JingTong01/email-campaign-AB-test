-- 01_data_checks.sql
-- Data-quality and experiment-health checks on the Hillstrom table `customers`.
-- Written in standard SQL (runs in SQLite and DuckDB). Each query is separated by
-- a "-- name: <query_name>" line so the notebook can run them one by one.

-- name: row_count
SELECT COUNT(*) AS n_rows FROM customers;

-- name: missing_values
SELECT
    SUM(CASE WHEN recency    IS NULL THEN 1 ELSE 0 END) AS recency_null,
    SUM(CASE WHEN history    IS NULL THEN 1 ELSE 0 END) AS history_null,
    SUM(CASE WHEN segment    IS NULL THEN 1 ELSE 0 END) AS segment_null,
    SUM(CASE WHEN visit      IS NULL THEN 1 ELSE 0 END) AS visit_null,
    SUM(CASE WHEN conversion IS NULL THEN 1 ELSE 0 END) AS conversion_null,
    SUM(CASE WHEN spend      IS NULL THEN 1 ELSE 0 END) AS spend_null
FROM customers;

-- name: logical_consistency
-- A conversion without a visit, or spend without a conversion, would indicate tracking errors.
SELECT
    SUM(CASE WHEN conversion = 1 AND visit = 0      THEN 1 ELSE 0 END) AS conversion_without_visit,
    SUM(CASE WHEN spend > 0      AND conversion = 0 THEN 1 ELSE 0 END) AS spend_without_conversion,
    SUM(CASE WHEN conversion = 1 AND spend = 0      THEN 1 ELSE 0 END) AS conversion_with_zero_spend,
    SUM(CASE WHEN spend < 0 OR history < 0          THEN 1 ELSE 0 END) AS negative_values
FROM customers;

-- name: group_sizes
-- Input for the sample-ratio-mismatch test (planned split: 1/3 each).
SELECT segment, COUNT(*) AS n_customers,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM customers), 2) AS pct
FROM customers
GROUP BY segment
ORDER BY segment;

-- name: outcomes_by_group
SELECT segment,
       COUNT(*)                         AS n_customers,
       ROUND(AVG(visit)      * 100, 2)  AS visit_rate_pct,
       ROUND(AVG(conversion) * 100, 2)  AS conversion_rate_pct,
       ROUND(AVG(spend), 3)             AS spend_per_customer,
       ROUND(SUM(spend) / NULLIF(SUM(conversion), 0), 2) AS avg_order_value
FROM customers
GROUP BY segment
ORDER BY segment;

-- name: pre_period_profile_by_group
-- Pre-treatment covariates should look the same in every arm if randomization worked.
SELECT segment,
       ROUND(AVG(recency), 2)  AS avg_recency_months,
       ROUND(AVG(history), 2)  AS avg_history_spend,
       ROUND(AVG(mens), 3)     AS share_bought_mens,
       ROUND(AVG(womens), 3)   AS share_bought_womens,
       ROUND(AVG(newbie), 3)   AS share_newbie
FROM customers
GROUP BY segment
ORDER BY segment;
