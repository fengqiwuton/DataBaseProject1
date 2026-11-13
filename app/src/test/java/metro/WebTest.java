package metro;

import java.net.*;
import java.net.http.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

public final class WebTest {
    static void check(boolean ok,String text) { if(!ok) throw new AssertionError(text); }
    public static void main(String[] args) throws Exception {
        var service=new MetroService(new MetroRepository(new Db(Config.load())));
        try(WebServer web=new WebServer(service,0)) {
            web.start();
            String base="http://127.0.0.1:"+web.port();
            HttpClient client=HttpClient.newHttpClient();
            var home=client.send(HttpRequest.newBuilder(URI.create(base+"/")).build(),HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
            check(home.statusCode()==200 && home.body().contains("深圳地铁"),"homepage");
            var stats=client.send(HttpRequest.newBuilder(URI.create(base+"/api?action=stats")).build(),HttpResponse.BodyHandlers.ofString());
            check(stats.statusCode()==200 && stats.body().contains("439"),"stats API");
            var blocked=client.send(HttpRequest.newBuilder(URI.create(base+"/api?action=lineDelete&line_id=1")).build(),HttpResponse.BodyHandlers.ofString());
            check(blocked.statusCode()==405,"GET mutation rejected");
            var csrf=client.send(HttpRequest.newBuilder(URI.create(base+"/api")).header("Content-Type","application/x-www-form-urlencoded")
                .POST(HttpRequest.BodyPublishers.ofString("action=lineDelete&line_id=1")).build(),HttpResponse.BodyHandlers.ofString());
            check(csrf.statusCode()==403,"no-token mutation rejected");
            var evil=client.send(HttpRequest.newBuilder(URI.create(base+"/api")).header("Origin","https://example.org")
                .header("X-Metro-Token",web.token()).header("Content-Type","application/x-www-form-urlencoded")
                .POST(HttpRequest.BodyPublishers.ofString("action=lineDelete&line_id=1")).build(),HttpResponse.BodyHandlers.ofString());
            check(evil.statusCode()==403,"cross-origin mutation rejected");
            var search=client.send(HttpRequest.newBuilder(URI.create(base+"/api?action=stations&match=station_id&search=%23347")).build(),HttpResponse.BodyHandlers.ofString());
            check(search.statusCode()==200 && search.body().contains("\"station_id\":347")
                && !search.body().contains("\"station_id\":346"),"search by exact station number");
            var english=client.send(HttpRequest.newBuilder(URI.create(base+"/api?action=stations&match=name_en&search=liYUan")).build(),HttpResponse.BodyHandlers.ofString());
            check(english.statusCode()==200 && english.body().contains("Longgang") && english.body().contains("Luohu"),"English name search preserves same-name stations");
            var invalid=client.send(HttpRequest.newBuilder(URI.create(base+"/api?action=stations&match=station_id&search=Luohu")).build(),HttpResponse.BodyHandlers.ofString());
            check(invalid.statusCode()==400 && invalid.body().contains("编号"),"bad station number shows input guidance");
            var missing=client.send(HttpRequest.newBuilder(URI.create(base+"/api?action=stationDetail&station_id=2147483647")).build(),HttpResponse.BodyHandlers.ofString());
            check(missing.statusCode()==400 && missing.body().contains("找不到站点"),"missing station gives a useful error");

            var console=client.send(HttpRequest.newBuilder(URI.create(base+"/sql")).build(),HttpResponse.BodyHandlers.ofString());
            check(console.statusCode()==200 && console.body().contains("sql-text"),"SQL page");
            var sqlGet=client.send(HttpRequest.newBuilder(URI.create(base+"/api?action=sqlQuery")).build(),HttpResponse.BodyHandlers.ofString());
            check(sqlGet.statusCode()==405,"SQL rejects GET");
            var query=postSql(client,base,web.token(),"-- example\nSELECT 'a;b' AS same, 2 AS same, NULL AS missing;");
            check(query.statusCode()==200 && query.body().contains("\"columns\":[\"same\",\"same\",\"missing\"]")
                && query.body().contains("[[\"a;b\",\"2\",null]]"),"query keeps duplicate labels and nulls: "+query.body());
            var empty=postSql(client,base,web.token(),"SELECT name_zh FROM project1.station WHERE false");
            check(empty.statusCode()==200 && empty.body().contains("\"columns\":[\"name_zh\"]")
                && empty.body().contains("\"rows\":[]"),"empty query keeps its columns");
            var neighbors=postSql(client,base,web.token(),"/* Q7 */ SELECT get_station_n_neighbor('Mawan', 'Line 5', 2);");
            check(neighbors.statusCode()==200 && neighbors.body().contains("Liwan") && neighbors.body().contains("Qianwan"),"Q7 runs through the SQL role");
            var capped=postSql(client,base,web.token(),"SELECT i FROM generate_series(1, 250) AS i");
            check(capped.statusCode()==200 && capped.body().contains("\"truncated\":true"),"result limit");
            var badSql=postSql(client,base,web.token(),"SELECT missing_column FROM project1.station");
            check(badSql.statusCode()==400 && badSql.body().contains("42703") && badSql.body().contains("missing_column"),"PostgreSQL errors are visible");
            var multiple=postSql(client,base,web.token(),"SELECT 1; SELECT 2;");
            check(multiple.statusCode()==400 && multiple.body().contains("一条"),"reject multiple statements");
            var mutation=postSql(client,base,web.token(),"WITH changed AS (UPDATE project1.station SET name_zh = name_zh WHERE false RETURNING *) SELECT * FROM changed");
            check(mutation.statusCode()==400 && mutation.body().contains("25006"),"database enforces read-only");
            check(postSql(client,base,"wrong","SELECT 1").statusCode()==403,"SQL requires token");
            check(Json.encode(Map.of("input","<script>\n\"\\")).contains("\\n"),"JSON escaping");
        }
        System.out.println("WebTest: station search, SQL console, request controls and JSON escaping PASS");
    }
    private static HttpResponse<String> postSql(HttpClient client,String base,String token,String sql) throws Exception {
        return client.send(HttpRequest.newBuilder(URI.create(base+"/api"))
            .header("X-Metro-Token",token).header("Content-Type","application/x-www-form-urlencoded")
            .POST(HttpRequest.BodyPublishers.ofString("action=sqlQuery&sql="+URLEncoder.encode(sql,StandardCharsets.UTF_8)))
            .build(),HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
    }
}
