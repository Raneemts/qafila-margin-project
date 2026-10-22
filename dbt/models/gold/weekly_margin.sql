WITH costed_lines AS (
    SELECT
        l.order_id,
        l.line_no,
        l.city,
        l.category,
        l.order_date,
        l.quantity,
        l.line_revenue,
        h.unit_cost_sar,

        CASE
            WHEN h.sku IS NOT NULL
            THEN l.quantity * h.unit_cost_sar
            ELSE NULL
        END AS line_cost

    FROM {{ ref('stg_order_lines') }} l

    LEFT JOIN {{ ref('product_cost_history') }} h
        ON l.sku = h.sku
        AND l.order_date >= h.valid_from
        AND (
            l.order_date < h.valid_to
            OR h.valid_to IS NULL
        )
)

SELECT
    CAST(WEEKOFYEAR(order_date) AS INTEGER) AS iso_week,
    city,
    category,

    CAST(COUNT(*) AS INTEGER) AS lines,

    CAST(ROUND(SUM(line_revenue), 2) AS DOUBLE) AS revenue_sar,

    CAST(ROUND(SUM(
        CASE
            WHEN unit_cost_sar IS NOT NULL THEN line_revenue
            ELSE 0
        END
    ), 2) AS DOUBLE) AS costed_revenue_sar,

    CAST(ROUND(SUM(
        COALESCE(line_cost, 0)
    ), 2) AS DOUBLE) AS cost_sar,

    CAST(ROUND(
        SUM(
            CASE
                WHEN unit_cost_sar IS NOT NULL THEN line_revenue
                ELSE 0
            END
        ) - SUM(COALESCE(line_cost, 0)),
        2
    ) AS DOUBLE) AS margin_sar,

    CAST(COUNT(*) FILTER (
        WHERE unit_cost_sar IS NULL
    ) AS INTEGER) AS uncosted_lines

FROM costed_lines

GROUP BY
    iso_week,
    city,
    category