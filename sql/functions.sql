CREATE OR REPLACE FUNCTION project1.get_station_n_neighbor(
    station_name text, line_name text, n integer
) RETURNS SETOF text
LANGUAGE plpgsql STABLE
SET search_path = pg_catalog, project1
AS $$
DECLARE
    target_line integer;
    target_position integer;
    matches integer;
BEGIN
    IF n IS NULL OR n < 0 THEN
        RAISE EXCEPTION 'n must be a nonnegative integer' USING ERRCODE = '22023';
    END IF;
    SELECT l.line_id INTO target_line FROM project1.metro_line l WHERE l.name_en = line_name;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Line not found: %', line_name USING ERRCODE = '22023';
    END IF;
    SELECT count(*), min(ls.position) INTO matches, target_position
    FROM project1.line_station ls
    JOIN project1.station s ON s.station_id = ls.station_id
    WHERE ls.line_id = target_line AND s.name_en = station_name;
    IF matches <> 1 THEN
        RAISE EXCEPTION 'Station must match exactly once on this line (found %): %', matches, station_name
            USING ERRCODE = '22023';
    END IF;
    RETURN QUERY SELECT (
        SELECT s.name_en FROM project1.line_station ls
        JOIN project1.station s ON s.station_id = ls.station_id
        WHERE ls.line_id = target_line AND ls.position::bigint = target_position::bigint - n::bigint
    );
    RETURN QUERY SELECT (
        SELECT s.name_en FROM project1.line_station ls
        JOIN project1.station s ON s.station_id = ls.station_id
        WHERE ls.line_id = target_line AND ls.position::bigint = target_position::bigint + n::bigint
    );
END;
$$;
