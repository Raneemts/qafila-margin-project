WITH valid_prices AS (
    SELECT
        p.sku,
        p.valid_from,
        p.unit_cost_sar,
        p.source_file
    FROM {{ ref('stg_supplier_prices') }} p
    WHERE p.unit_cost_sar > 0
      AND EXISTS (
          SELECT 1
          FROM {{ source('raw', 'products') }} pr
          WHERE TRIM(pr.sku) = p.sku
      )
),

deduplicated AS (
    SELECT
        sku,
        valid_from,
        unit_cost_sar
    FROM valid_prices
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY sku, valid_from
        ORDER BY source_file DESC
    ) = 1
),

previous_cost AS (
    SELECT
        *,
        LAG(unit_cost_sar) OVER (
            PARTITION BY sku
            ORDER BY valid_from
        ) AS previous_unit_cost
    FROM deduplicated
),

changes_only AS (
    SELECT
        sku,
        valid_from,
        unit_cost_sar
    FROM previous_cost
    WHERE previous_unit_cost IS NULL
       OR previous_unit_cost <> unit_cost_sar
),

history AS (
    SELECT
        sku,
        unit_cost_sar,
        valid_from,
        LEAD(valid_from) OVER (
            PARTITION BY sku
            ORDER BY valid_from
        ) AS valid_to
    FROM changes_only
)

SELECT
    sku,
    unit_cost_sar,
    valid_from,
    valid_to,
    valid_to IS NULL AS is_current
FROM history