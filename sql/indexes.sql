CREATE INDEX line_station_station_idx ON project1.line_station (station_id, line_id);
CREATE INDEX station_english_idx ON project1.station (name_en);
CREATE INDEX landmark_prefix_idx ON project1.exit_landmark (landmark_name text_pattern_ops);
