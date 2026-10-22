SELECT
    p.source_file,
    p.sku,
    p.valid_from,
    p.raw_cost,
    CASE
        WHEN NOT EXISTS (
            SELECT 1
            FROM {{ source('raw', 'products') }} pr
            WHERE TRIM(pr.sku) = p.sku
        )
        THEN 'unknown_sku'

        WHEN p.unit_cost_sar IS NULL
          OR p.unit_cost_sar <= 0
        THEN 'invalid_cost'
    END AS reason

FROM {{ ref('stg_supplier_prices') }} p

WHERE NOT EXISTS (
    SELECT 1
    FROM {{ source('raw', 'products') }} pr
    WHERE TRIM(pr.sku) = p.sku
)
OR p.unit_cost_sar IS NULL
OR p.unit_cost_sar <= 0