SELECT ls.opening_year AS opening, count(*) AS cnt
FROM project1.line_station ls JOIN project1.metro_line l USING (line_id)
WHERE l.name_en = ? GROUP BY ls.opening_year ORDER BY ls.opening_year;
