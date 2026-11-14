package metro;

import java.util.*;
import java.util.concurrent.*;

public final class IntegrationTest {
    static void check(boolean value, String message) { if (!value) throw new AssertionError(message); }
    static Map<String,String> p(String... items) {
        Map<String,String> map = new HashMap<>();
        for (int i=0;i<items.length;i+=2) map.put(items[i],items[i+1]);
        return map;
    }
    @SuppressWarnings("unchecked") static List<Map<String,Object>> rows(Object o) { return (List<Map<String,Object>>)o; }
    static int id(Object o, String field) { return ((Number)rows(o).get(0).get(field)).intValue(); }
    public static void main(String[] args) throws Exception {
        MetroService s = new MetroService(new MetroRepository(new Db(Config.load())));
        check(id(s.execute("q1",p()),"station_count")==439,"Q1");
        check(id(s.execute("q2",p()),"line_count")==29,"Q2");
        check(rows(s.execute("q3",p())).stream().mapToLong(r->((Number)r.get("cnt")).longValue()).sum()==350,"Q3");
        var q4=rows(s.execute("q4",p("line_name","Line 5")));
        check(q4.size()==3 && ((Number)q4.get(0).get("cnt")).intValue()==27,"Q4");
        var q5=rows(s.execute("q5",p("line_name","Line 1")));
        check(q5.size()==2 && q5.stream().allMatch(r->((Number)r.get("cnt")).intValue()==10),"Q5 ties");
        check(rows(s.execute("q6",p("prefix","塘朗%"))).size()==6,"Q6");
        var q7=rows(s.execute("q7",p("station_name","Mawan","line_name","Line 5","n","5")));
        check(q7.size()==2 && q7.get(0).get("neighbor")==null && q7.get(1).get("neighbor").equals("Linhai"),"Q7 NULL");
        var huge=rows(s.execute("q7",p("station_name","Mawan","line_name","Line 5","n","2147483647")));
        check(huge.size()==2 && huge.stream().allMatch(r->r.get("neighbor")==null),"Q7 overflow");
        check(rows(s.execute("stations",p("search","梨园"))).size()==2,"same name identity");
        Object fareById=s.execute("fare",p("start","152","end","229"));
        check(fareById.equals(s.execute("fare",p("start","宝安","end","#229"))),"fare accepts Chinese names and #ID");
        check(fareById.equals(s.execute("fare",p("start","bAO'an","end","#229"))),"fare accepts English names case-insensitively");
        try {
            s.execute("fare",p("start","宝安","end","梨园"));
            throw new AssertionError("ambiguous fare station was accepted");
        } catch (IllegalArgumentException expected) {
            check(expected.getMessage().contains("Longgang") && expected.getMessage().contains("Luohu")
                && expected.getMessage().contains("#229") && expected.getMessage().contains("#230"),"fare ambiguity lists both station IDs");
        }
        try {
            s.execute("fare",p("start","宝安","end","龙岗"));
            throw new AssertionError("district name was accepted as a station");
        } catch (IllegalArgumentException expected) {
            check(expected.getMessage().contains("到达站") && expected.getMessage().contains("龙岗"),"missing destination gives a useful error");
        }
        int plannedStation=rows(s.execute("stations",p("search","梨园"))).stream()
            .filter(r->r.get("district").equals("Luohu")).mapToInt(r->((Number)r.get("station_id")).intValue()).findFirst().orElseThrow();
        for(String mode:List.of("stops","transfers")) {
            try {
                s.execute("route",p("start",""+plannedStation,"end",""+plannedStation,"planned","false","mode",mode));
                throw new AssertionError("Construction-only endpoint accepted in operating network");
            } catch(IllegalArgumentException expected) { }
            check(((Map<?,?>)s.execute("route",p("start",""+plannedStation,"end",""+plannedStation,"planned","true","mode",mode))).get("found").equals(true),"planned mode accepts planned endpoint");
        }
        for(String n:List.of("-1","0")) {
            if(n.equals("-1")) {
                try { s.execute("q7",p("station_name","Mawan","line_name","Line 5","n",n)); throw new AssertionError("negative n accepted"); }
                catch(java.sql.SQLException expected) { check(expected.getSQLState().equals("22023"),"clear invalid n error"); }
            } else check(rows(s.execute("q7",p("station_name","Mawan","line_name","Line 5","n",n))).stream().allMatch(r->"Mawan".equals(r.get("neighbor"))),"zero n returns source twice");
        }
        int district=id(s.execute("districts",p()),"district_id");
        List<Integer> stations=new ArrayList<>();
        int line=0;
        try {
            for (int i=0;i<4;i++) stations.add(id(s.execute("stationAdd",p("name_zh","测试站"+i,"name_en","Test's "+i,"district_id",""+district)),"station_id"));
            line=id(s.execute("lineAdd",p("name_zh","测试线路","name_en","Test Line")),"line_id");
            s.execute("lineInsert",p("line_id",""+line,"position","1","station_ids",stations.get(0)+","+stations.get(1),"status","Operation","opening_year","2026"));
            var route=(Map<?,?>)s.execute("route",p("start",""+stations.get(0),"end",""+stations.get(1)));
            check(route.get("found").equals(true) && ((Number)route.get("stops")).intValue()==1,"real database adjacent route");
            s.execute("lineInsert",p("line_id",""+line,"position","2","station_ids",""+stations.get(2),"status","Operation","opening_year","2026"));
            var ordered=rows(s.execute("lineStations",p("line_id",""+line)));
            check(ordered.size()==3 && ((Number)ordered.get(1).get("station_id")).intValue()==stations.get(2),"bulk middle insertion");
            try {
                s.execute("lineInsert",p("line_id",""+line,"position","1","station_ids",stations.get(3)+","+stations.get(0),"status","Operation","opening_year","2026"));
                throw new AssertionError("duplicate insertion accepted");
            } catch (java.sql.SQLException | IllegalArgumentException expected) { }
            check(rows(s.execute("lineStations",p("line_id",""+line))).size()==3,"failed insertion rolled back");
            s.execute("lineRemove",p("line_id",""+line,"station_id",""+stations.get(2)));
            check(((Number)rows(s.execute("lineStations",p("line_id",""+line))).get(1).get("position")).intValue()==2,"remove compacts");
            int lid=line;
            ExecutorService pool=Executors.newFixedThreadPool(2);
            try {
                var futures=pool.invokeAll(List.of(
                    ()->s.execute("lineInsert",p("line_id",""+lid,"position","1","station_ids",""+stations.get(2),"status","Operation","opening_year","2026")),
                    ()->s.execute("lineInsert",p("line_id",""+lid,"position","1","station_ids",""+stations.get(3),"status","Operation","opening_year","2026"))));
                for(var f:futures) f.get(10,TimeUnit.SECONDS);
            } finally { pool.shutdownNow(); }
            ordered=rows(s.execute("lineStations",p("line_id",""+line)));
            check(ordered.size()==4,"concurrent inserts both commit");
            for(int i=0;i<ordered.size();i++) check(((Number)ordered.get(i).get("position")).intValue()==i+1,"contiguous positions");
            s.execute("stationUpdate",p("station_id",""+stations.get(0),"name_zh","改名测试","name_en","Renamed","district_id",""+district));
            check(rows(s.execute("stations",p("search","Renamed"))).size()==1,"station update");
            s.execute("stationDelete",p("station_id",""+stations.get(0)));
            ordered=rows(s.execute("lineStations",p("line_id",""+line)));
            check(ordered.size()==3,"station delete removes memberships");
            for(int i=0;i<ordered.size();i++) check(((Number)ordered.get(i).get("position")).intValue()==i+1,"station deletion compacts");
            check(s.execute("fare",p("start",""+stations.get(1),"end",""+stations.get(2))).toString().contains("available=false"),"no invented fare");
        } finally {
            if(line!=0) s.execute("lineDelete",p("line_id",""+line));
            for(int sid:stations) if(!rows(s.execute("stations",p("station_id",""+sid))).isEmpty()) s.execute("stationDelete",p("station_id",""+sid));
        }
        check(id(s.execute("q1",p()),"station_count")==439,"cleanup restores baseline");
        System.out.println("IntegrationTest: Q1-Q7, CRUD, rollback, concurrency, fare boundary PASS");
    }
}
