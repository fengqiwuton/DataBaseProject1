package metro;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.sql.*;
import java.util.*;

/** Shared business entrypoint for CLI and local browser UI. */
public final class MetroService {
    public static final Set<String> WRITES=Set.of("stationAdd","stationUpdate","stationDelete","lineAdd","lineUpdate","lineDelete","lineInsert","lineRemove","membershipUpdate");
    private final MetroRepository repo;
    private final FareTable fares;
    public MetroService(MetroRepository repo) { this.repo=repo; this.fares=FareTable.fromEnvironment(); }
    public Object execute(String action,Map<String,String> p) throws Exception {
        return switch(action) {
            case "stats" -> repo.query("SELECT (SELECT count(*) FROM station) stations,(SELECT count(*) FROM metro_line) lines,"
                +"(SELECT count(*) FROM station_exit) exits,(SELECT count(*) FROM exit_landmark) landmarks,version() database_version");
            case "districts" -> repo.query("SELECT * FROM district ORDER BY name_en COLLATE \"C\"");
            case "stations" -> stations(p);
            case "lines" -> repo.query("SELECT l.*,(SELECT count(*) FROM line_station ls WHERE ls.line_id=l.line_id) station_count FROM metro_line l ORDER BY l.line_id");
            case "lineStations" -> repo.query("SELECT ls.*,s.name_zh,s.name_en,d.name_en district FROM line_station ls JOIN station s USING(station_id) JOIN district d USING(district_id) WHERE line_id=? ORDER BY position",id(p,"line_id"));
            case "stationDetail" -> Map.of("station",stations(Map.of("station_id",need(p,"station_id"))),
                "memberships",repo.query("SELECT ls.*,l.name_en line_name FROM line_station ls JOIN metro_line l USING(line_id) WHERE station_id=? ORDER BY line_id",id(p,"station_id")),
                "exits",repo.query("SELECT e.exit_code,el.landmark_name FROM station_exit e LEFT JOIN exit_landmark el USING(exit_id) WHERE station_id=? ORDER BY e.exit_code,el.landmark_name",id(p,"station_id")));
            case "stationAdd", "stationUpdate" -> repo.saveStation(action.equals("stationUpdate")?id(p,"station_id"):null,
                id(p,"district_id"),need(p,"name_zh"),need(p,"name_en"),optionalInt(p,"lon_mdeg"),optionalInt(p,"lat_mdeg"));
            case "stationDelete" -> repo.deleteStation(id(p,"station_id"));
            case "lineAdd", "lineUpdate" -> repo.saveLine(action.equals("lineUpdate")?id(p,"line_id"):null,need(p,"name_zh"),need(p,"name_en"));
            case "lineDelete" -> repo.deleteLine(id(p,"line_id"));
            case "lineInsert" -> {
                List<MetroRepository.Membership> members=new ArrayList<>();
                for(String raw:need(p,"station_ids").split(",",-1)) {
                    Map<String,String> member=new HashMap<>(p); member.put("station_id",raw.trim()); members.add(membership(member));
                }
                yield repo.insertStations(id(p,"line_id"),id(p,"position"),members);
            }
            case "lineRemove" -> repo.removeStation(id(p,"line_id"),id(p,"station_id"));
            case "membershipUpdate" -> repo.updateMembership(id(p,"line_id"),membership(p));
            case "landmarks" -> repo.query("SELECT DISTINCT el.landmark_name,s.station_id,s.name_zh,s.name_en,e.exit_code FROM exit_landmark el JOIN station_exit e USING(exit_id) JOIN station s USING(station_id) WHERE strpos(el.landmark_name,?)>0 ORDER BY el.landmark_name,s.station_id,e.exit_code LIMIT 100",p.getOrDefault("search",""));
            case "q1", "q2", "q3" -> repo.query(resource(action));
            case "q4", "q5" -> repo.query(resource(action),need(p,"line_name"));
            case "q6" -> repo.query(resource(action),need(p,"prefix"));
            case "q7" -> repo.query(resource(action),need(p,"station_name"),need(p,"line_name"),integer(p,"n"));
            case "route", "landmarkRoute" -> route(p,action.equals("landmarkRoute"));
            case "fare" -> fare(p);
            default -> throw new IllegalArgumentException("未知操作: "+action);
        };
    }
    private List<Map<String,Object>> stations(Map<String,String> p) throws SQLException {
        String base="SELECT s.*,d.name_en district,(SELECT count(*) FROM station_exit e WHERE e.station_id=s.station_id) exit_count FROM station s JOIN district d USING(district_id) ";
        if(p.containsKey("station_id")) return repo.query(base+"WHERE station_id=?",id(p,"station_id"));
        String text=p.getOrDefault("search","");
        return repo.query(base+"WHERE strpos(s.name_zh,?)>0 OR strpos(lower(s.name_en),lower(?))>0 ORDER BY s.name_en COLLATE \"C\",s.station_id",text,text);
    }
    private MetroRepository.Membership membership(Map<String,String> p) {
        String status=need(p,"status");
        if(!Set.of("Operation","Construction").contains(status)) throw new IllegalArgumentException("status应为Operation或Construction");
        int year=integer(p,"opening_year");
        if(year<1900 || year>2200) throw new IllegalArgumentException("开通年范围1900–2200");
        String first=p.getOrDefault("first_train",""), last=p.getOrDefault("last_train","");
        MetroRepository.time(first); MetroRepository.time(last);
        return new MetroRepository.Membership(id(p,"station_id"),status,year,first,last);
    }
    private Object fare(Map<String,String> p) throws SQLException {
        int start=id(p,"start"),end=id(p,"end");
        if(stations(Map.of("station_id",""+start)).isEmpty() || stations(Map.of("station_id",""+end)).isEmpty()) throw new IllegalArgumentException("票价起终点不存在");
        return fares.lookup(start,end);
    }
    private Object route(Map<String,String> p,boolean landmarks) throws SQLException {
        String mode=p.getOrDefault("mode","stops");
        boolean planned=Boolean.parseBoolean(p.getOrDefault("planned","false"));
        return repo.db.transaction(true,c->{
            Set<Integer> starts=new TreeSet<>(),ends=new TreeSet<>();
            if(landmarks) {
                for(var r:MetroRepository.query(c,"SELECT DISTINCT e.station_id FROM exit_landmark el JOIN station_exit e USING(exit_id) WHERE el.landmark_name=?",need(p,"start_landmark"))) starts.add(((Number)r.get("station_id")).intValue());
                for(var r:MetroRepository.query(c,"SELECT DISTINCT e.station_id FROM exit_landmark el JOIN station_exit e USING(exit_id) WHERE el.landmark_name=?",need(p,"end_landmark"))) ends.add(((Number)r.get("station_id")).intValue());
            } else { starts.add(id(p,"start")); ends.add(id(p,"end")); }
            var allStations=MetroRepository.query(c,"SELECT s.station_id,s.name_zh,s.name_en,d.name_en district FROM station s JOIN district d USING(district_id)");
            Map<Integer,Map<String,Object>> lookup=new HashMap<>();
            for(var r:allStations) lookup.put(((Number)r.get("station_id")).intValue(),r);
            if(starts.isEmpty() || ends.isEmpty() || !lookup.keySet().containsAll(starts) || !lookup.keySet().containsAll(ends)) throw new IllegalArgumentException("找不到起终点；地标须输入候选列表中的完整名称");
            if(!planned) {
                Set<Integer> operating=new HashSet<>();
                for(var r:MetroRepository.query(c,"SELECT DISTINCT station_id FROM line_station WHERE status='Operation'")) operating.add(((Number)r.get("station_id")).intValue());
                starts.retainAll(operating); ends.retainAll(operating);
                if(starts.isEmpty() || ends.isEmpty()) throw new IllegalArgumentException("起终点在运营网络中不存在，请选择包含在建网络或更换车站/地标");
            }
            var adjacent=MetroRepository.query(c,"SELECT a.station_id a,b.station_id b,a.line_id FROM line_station a JOIN line_station b ON a.line_id=b.line_id AND b.position=a.position+1 WHERE ? OR (a.status='Operation' AND b.status='Operation')",planned);
            List<Router.Edge> edges=new ArrayList<>();
            for(var r:adjacent) {
                int a=((Number)r.get("a")).intValue(),b=((Number)r.get("b")).intValue(),line=((Number)r.get("line_id")).intValue();
                edges.add(new Router.Edge(a,b,line)); edges.add(new Router.Edge(b,a,line));
            }
            Router.Result result=Router.route(edges,starts,ends,mode);
            Map<String,Object> response=new LinkedHashMap<>();
            response.put("found",result.found()); response.put("mode",mode); response.put("planned",planned);
            response.put("stops",result.stops()); response.put("transfers",result.transfers());
            response.put("stations",result.stations().stream().map(lookup::get).toList());
            Map<Integer,String> lineNames=new HashMap<>();
            for(var r:MetroRepository.query(c,"SELECT line_id,name_en FROM metro_line")) lineNames.put(((Number)r.get("line_id")).intValue(),r.get("name_en").toString());
            response.put("lines",result.lines().stream().map(lineNames::get).toList());
            response.put("message",result.found()?"按源数据查询成功；不包含步行时间或票价估计":"当前数据网络不连通");
            if(landmarks && result.found()) {
                response.put("start_exits",MetroRepository.query(c,"SELECT e.exit_code,el.landmark_name FROM exit_landmark el JOIN station_exit e USING(exit_id) WHERE station_id=? AND landmark_name=?",result.stations().get(0),need(p,"start_landmark")));
                response.put("end_exits",MetroRepository.query(c,"SELECT e.exit_code,el.landmark_name FROM exit_landmark el JOIN station_exit e USING(exit_id) WHERE station_id=? AND landmark_name=?",result.stations().get(result.stations().size()-1),need(p,"end_landmark")));
            }
            return response;
        });
    }
    private static String resource(String name) throws IOException {
        try(InputStream in=MetroService.class.getResourceAsStream("/sql/"+name+".sql")) {
            if(in==null) throw new IOException("Missing SQL resource: "+name);
            return new String(in.readAllBytes(),StandardCharsets.UTF_8);
        }
    }
    static String need(Map<String,String> p,String key) {
        String value=p.get(key);
        if(value==null || value.isBlank()) throw new IllegalArgumentException("缺少字段: "+key);
        return value.trim();
    }
    static int integer(Map<String,String> p,String key) {
        try { return Integer.parseInt(need(p,key)); }
        catch(NumberFormatException e) { throw new IllegalArgumentException(key+"必须是32位整数"); }
    }
    static int id(Map<String,String> p,String key) {
        int value=integer(p,key);
        if(value<=0) throw new IllegalArgumentException(key+"必须大于0");
        return value;
    }
    static Integer optionalInt(Map<String,String> p,String key) { return p.getOrDefault(key,"").isBlank()?null:integer(p,key); }
}
