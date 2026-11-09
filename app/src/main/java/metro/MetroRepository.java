package metro;

import java.sql.*;
import java.time.LocalTime;
import java.util.*;

/** Owns SQL and mutation transactions; frontends never supply SQL text. */
public final class MetroRepository {
    public record Membership(int stationId, String status, int year, String first, String last) { }
    final Db db;
    public MetroRepository(Db db) { this.db=db; }
    public List<Map<String,Object>> query(String sql,Object... args) throws SQLException {
        try(Connection c=db.open()) { return query(c,sql,args); }
    }
    public static List<Map<String,Object>> query(Connection c,String sql,Object... args) throws SQLException {
        try(PreparedStatement p=c.prepareStatement(sql)) {
            bind(p,args);
            try(ResultSet rs=p.executeQuery()) {
                List<Map<String,Object>> rows=new ArrayList<>();
                ResultSetMetaData meta=rs.getMetaData();
                while(rs.next()) {
                    Map<String,Object> row=new LinkedHashMap<>();
                    for(int i=1;i<=meta.getColumnCount();i++) row.put(meta.getColumnLabel(i),rs.getObject(i));
                    rows.add(row);
                }
                return rows;
            }
        }
    }
    static int update(Connection c,String sql,Object... args) throws SQLException {
        try(PreparedStatement p=c.prepareStatement(sql)) { bind(p,args); return p.executeUpdate(); }
    }
    static void bind(PreparedStatement p,Object[] args) throws SQLException {
        for(int i=0;i<args.length;i++) p.setObject(i+1,args[i]);
    }
    static SQLException invalid(String message) { return new SQLException(message,"22023"); }
    static void requireOne(int changed) throws SQLException { if(changed!=1) throw invalid("目标不存在或已被修改"); }
    // Serializes topology writes before row locks. Parent-row locks remain the per-line invariant.
    // This small network favors reliable multi-line deletion over parallel write throughput.
    static void topologyLock(Connection c) throws SQLException {
        query(c,"SELECT pg_advisory_xact_lock(307,1)");
        update(c,"SET CONSTRAINTS line_station_position_uq DEFERRED");
    }
    static void lineLock(Connection c,int line) throws SQLException {
        if(query(c,"SELECT line_id FROM metro_line WHERE line_id=? FOR UPDATE",line).isEmpty()) throw invalid("线路不存在");
    }
    static void compact(Connection c,int line) throws SQLException {
        update(c,"WITH positions AS (SELECT station_id,row_number() OVER(ORDER BY position)::integer AS p FROM line_station WHERE line_id=?) "
            +"UPDATE line_station ls SET position=p.p FROM positions p WHERE ls.line_id=? AND ls.station_id=p.station_id",line,line);
    }
    public Object saveStation(Integer id,int district,String zh,String en,Integer lon,Integer lat) throws SQLException {
        return db.transaction(false,c->{
            if(id==null) return query(c,"INSERT INTO station(district_id,name_zh,name_en,lon_mdeg,lat_mdeg) VALUES(?,?,?,?,?) RETURNING station_id",district,zh,en,lon,lat);
            requireOne(update(c,"UPDATE station SET district_id=?,name_zh=?,name_en=?,lon_mdeg=?,lat_mdeg=? WHERE station_id=?",district,zh,en,lon,lat,id));
            return query(c,"SELECT station_id FROM station WHERE station_id=?",id);
        });
    }
    public Object saveLine(Integer id,String zh,String en) throws SQLException {
        return db.transaction(false,c->{
            topologyLock(c);
            if(id==null) return query(c,"INSERT INTO metro_line(name_zh,name_en) VALUES(?,?) RETURNING line_id",zh,en);
            requireOne(update(c,"UPDATE metro_line SET name_zh=?,name_en=? WHERE line_id=?",zh,en,id));
            return query(c,"SELECT line_id FROM metro_line WHERE line_id=?",id);
        });
    }
    public Object deleteStation(int station) throws SQLException {
        return db.transaction(false,c->{
            topologyLock(c);
            if(query(c,"SELECT station_id FROM station WHERE station_id=? FOR UPDATE",station).isEmpty()) throw invalid("站点不存在");
            var lines=query(c,"SELECT line_id FROM line_station WHERE station_id=? ORDER BY line_id",station);
            for(var row:lines) lineLock(c,((Number)row.get("line_id")).intValue());
            update(c,"DELETE FROM line_station WHERE station_id=?",station);
            for(var row:lines) compact(c,((Number)row.get("line_id")).intValue());
            requireOne(update(c,"DELETE FROM station WHERE station_id=?",station));
            return Map.of("message","站点及出口已删除，关联线路站序已修复");
        });
    }
    public Object deleteLine(int line) throws SQLException {
        return db.transaction(false,c->{
            topologyLock(c); lineLock(c,line);
            update(c,"DELETE FROM line_station WHERE line_id=?",line);
            requireOne(update(c,"DELETE FROM metro_line WHERE line_id=?",line));
            return Map.of("message","线路已删除；物理站点保留");
        });
    }
    public Object insertStations(int line,int position,List<Membership> members) throws SQLException {
        return db.transaction(false,c->{
            topologyLock(c); lineLock(c,line);
            int size=((Number)query(c,"SELECT count(*) AS n FROM line_station WHERE line_id=?",line).get(0).get("n")).intValue();
            if(position<1 || position>size+1 || members.isEmpty()) throw invalid("插入位置必须在1到站数+1之间，且至少一个站点");
            Set<Integer> unique=new HashSet<>();
            for(Membership m:members) {
                if(!unique.add(m.stationId())) throw invalid("输入包含重复站点");
                if(query(c,"SELECT station_id FROM station WHERE station_id=?",m.stationId()).isEmpty()) throw invalid("站点不存在: "+m.stationId());
                if(!query(c,"SELECT 1 FROM line_station WHERE line_id=? AND station_id=?",line,m.stationId()).isEmpty()) throw invalid("站点已在线路中: "+m.stationId());
            }
            update(c,"UPDATE line_station SET position=position+? WHERE line_id=? AND position>=?",members.size(),line,position);
            int next=position;
            for(Membership m:members) update(c,"INSERT INTO line_station(line_id,station_id,position,status,opening_year,first_train,last_train) VALUES(?,?,?,?,?,?,?)",
                line,m.stationId(),next++,m.status(),m.year(),time(m.first()),time(m.last()));
            return Map.of("message","已插入 "+members.size()+" 个站点","line_id",line);
        });
    }
    static Object time(String value) { return value==null || value.isBlank()?null:LocalTime.parse(value); }
    public Object removeStation(int line,int station) throws SQLException {
        return db.transaction(false,c->{
            topologyLock(c); lineLock(c,line);
            requireOne(update(c,"DELETE FROM line_station WHERE line_id=? AND station_id=?",line,station));
            compact(c,line);
            return Map.of("message","已移出线路，站点保留");
        });
    }
    public Object updateMembership(int line,Membership m) throws SQLException {
        return db.transaction(false,c->{
            topologyLock(c); lineLock(c,line);
            requireOne(update(c,"UPDATE line_station SET status=?,opening_year=?,first_train=?,last_train=? WHERE line_id=? AND station_id=?",
                m.status(),m.year(),time(m.first()),time(m.last()),line,m.stationId()));
            return Map.of("message","线路站点属性已更新");
        });
    }
}
