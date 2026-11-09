SELECT neighbor FROM project1.get_station_n_neighbor(?, ?, ?) WITH ORDINALITY AS t(neighbor, ord)
ORDER BY ord;
