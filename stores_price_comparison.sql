-- Count stores WITH exclusions (should match your CSV)
SELECT COUNT(*)
FROM (
    SELECT 
        p.store_code,
        s.storename,
        s.chainname,
        s.subchainname,
        s.storeid,
        s.address,
        s.city,
        s.zipcode,
        s.latitude,
        s.longitude,
        AVG(
            CASE 
                WHEN ap.average_price > 0 THEN 
                    (p.itemprice - ap.average_price) / ap.average_price
                ELSE NULL
            END
        ) AS average_price_diff,
        COUNT(ap.itemcode) AS popular_item_count
    FROM allprices p 
    LEFT JOIN all_stores s ON s.store_code = p.store_code
    LEFT JOIN popular_items_avg_prices ap ON ap.itemcode = p.itemcode
    WHERE p.upload_date = '2026-01-11'
        AND ap.itemcode IS NOT NULL
        AND p.itemprice > 0
        AND p.itemprice IS NOT NULL
        AND s.chainname NOT IN ('סופר פארם', 'Yellow', 'דור אלון')
        AND s.subchainname NOT IN ('Be', 'אונליין')
        AND s.city NOT IN ('unknown')
    GROUP BY 
        p.store_code, 
        s.storename, 
        s.chainname, 
        s.subchainname, 
        s.storeid, 
        s.address, 
        s.city, 
        s.zipcode, 
        s.latitude, 
        s.longitude
) subquery;