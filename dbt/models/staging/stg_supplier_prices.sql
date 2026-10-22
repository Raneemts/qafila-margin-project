WITH source_data AS (
    SELECT
        source_file,
        supplier_id,
        TRIM(sku) AS sku,
        CAST(valid_from AS DATE) AS valid_from,
        raw_cost
    FROM {{ source('raw', 'supplier_prices') }}
),

normalized AS (
    SELECT
        *,
        TRANSLATE(
            REPLACE(
                REPLACE(raw_cost, '٫', '.'),
                ',', '.'
            ),
            '٠١٢٣٤٥٦٧٨٩',
            '0123456789'
        ) AS normalized_cost
    FROM source_data
)

SELECT
    source_file,
    supplier_id,
    sku,
    valid_from,
    raw_cost,
    ROUND(
        TRY_CAST(normalized_cost AS DOUBLE),
        2
    ) AS unit_cost_sar
FROM normalized