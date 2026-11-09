SELECT s.name_zh AS chinese_name, d.name_en AS district,
       e.exit_code AS exit, el.landmark_name AS name
FROM project1.exit_landmark el JOIN project1.station_exit e USING (exit_id)
JOIN project1.station s USING (station_id) JOIN project1.district d USING (district_id)
WHERE el.landmark_name LIKE ?
ORDER BY s.name_en COLLATE "C", s.station_id, e.exit_code COLLATE "C", el.landmark_name COLLATE "C";
