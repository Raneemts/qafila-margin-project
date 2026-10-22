WITH order_data AS (
    SELECT
        order_id,
        store_id,
        CAST(
            CAST(created_at AS TIMESTAMP) + INTERVAL '3 hours'
            AS DATE
        ) AS order_date
    FROM {{ source('raw', 'orders') }}
    WHERE LOWER(TRIM(status)) = 'delivered'
),

order_lines AS (
    SELECT
        o.order_id,
        i.line_no,
        TRIM(p.sku) AS sku,
        p.category,
        s.city,
        o.order_date,
        i.quantity,
        ROUND(
            i.quantity * i.unit_price - i.discount,
            2
        ) AS line_revenue

    FROM order_data o

    JOIN {{ source('raw', 'order_items') }} i
        ON o.order_id = i.order_id

    LEFT JOIN {{ source('raw', 'products') }} p
        ON i.product_id = p.product_id

    LEFT JOIN {{ source('raw', 'stores') }} s
        ON o.store_id = s.store_id

    WHERE i.quantity > 0
      AND o.order_date >= DATE '2026-08-31'
)

SELECT *
FROM order_lines