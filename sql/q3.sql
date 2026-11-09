SELECT d.name_en AS district, count(*) AS cnt
FROM project1.station s JOIN project1.district d USING (district_id)
WHERE EXISTS (SELECT 1 FROM project1.line_station ls
              WHERE ls.station_id = s.station_id AND ls.status = 'Operation')
GROUP BY d.district_id, d.name_en ORDER BY d.name_en COLLATE "C";
