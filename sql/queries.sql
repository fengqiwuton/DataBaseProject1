-- DataGrip: run after import.sql; q1..q7.sql are the parameterized application versions.

-- Q1
SELECT count(*) AS station_count FROM project1.station;


-- Q2
SELECT count(*) AS line_count FROM project1.metro_line;


-- Q3
SELECT d.name_en AS district, count(*) AS cnt
FROM project1.station s JOIN project1.district d USING (district_id)
WHERE EXISTS (SELECT 1 FROM project1.line_station ls
              WHERE ls.station_id = s.station_id AND ls.status = 'Operation')
GROUP BY d.district_id, d.name_en ORDER BY d.name_en COLLATE "C";


-- Q4
SELECT ls.opening_year AS opening, count(*) AS cnt
FROM project1.line_station ls JOIN project1.metro_line l USING (line_id)
WHERE l.name_en = 'Line 5' GROUP BY ls.opening_year ORDER BY ls.opening_year;


-- Q5
WITH counts AS (
    SELECT s.station_id, s.name_en AS english_name, count(e.exit_id) AS cnt
    FROM project1.metro_line l JOIN project1.line_station ls USING (line_id)
    JOIN project1.station s USING (station_id)
    LEFT JOIN project1.station_exit e USING (station_id)
    WHERE l.name_en = 'Line 1' GROUP BY s.station_id, s.name_en
)
SELECT english_name, cnt FROM counts
WHERE cnt = (SELECT max(cnt) FROM counts) ORDER BY english_name COLLATE "C";


-- Q6
SELECT s.name_zh AS chinese_name, d.name_en AS district,
       e.exit_code AS exit, el.landmark_name AS name
FROM project1.exit_landmark el JOIN project1.station_exit e USING (exit_id)
JOIN project1.station s USING (station_id) JOIN project1.district d USING (district_id)
WHERE el.landmark_name LIKE '塘朗%'
ORDER BY s.name_en COLLATE "C", s.station_id, e.exit_code COLLATE "C", el.landmark_name COLLATE "C";


-- Q7
SELECT neighbor FROM project1.get_station_n_neighbor('Mawan', 'Line 5', 5) WITH ORDINALITY AS t(neighbor, ord)
ORDER BY ord;


-- Q7 original PDF invocation
SELECT project1.get_station_n_neighbor('Mawan','Line 5',2);
