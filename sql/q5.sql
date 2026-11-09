WITH counts AS (
    SELECT s.station_id, s.name_en AS english_name, count(e.exit_id) AS cnt
    FROM project1.metro_line l JOIN project1.line_station ls USING (line_id)
    JOIN project1.station s USING (station_id)
    LEFT JOIN project1.station_exit e USING (station_id)
    WHERE l.name_en = ? GROUP BY s.station_id, s.name_en
)
SELECT english_name, cnt FROM counts
WHERE cnt = (SELECT max(cnt) FROM counts) ORDER BY english_name COLLATE "C";
