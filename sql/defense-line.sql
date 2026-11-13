-- Task 4 backup: change the one English line name below. Run this query after
-- the web/CLI mutation to verify the selected line's current Num values.
SELECT l.line_id, l.name_zh AS line_zh, l.name_en AS line_en,
       ls.position AS "Num", s.station_id, s.name_zh AS station_zh,
       s.name_en AS station_en, ls.status, ls.opening_year
FROM project1.metro_line AS l
LEFT JOIN project1.line_station AS ls USING (line_id)
LEFT JOIN project1.station AS s USING (station_id)
WHERE l.name_en = 'Demo Line'
ORDER BY ls.position;
