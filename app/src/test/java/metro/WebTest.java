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
            check(Json.encode(Map.of("input","<script>\n\"\\")).contains("\\n"),"JSON escaping");
        }
        System.out.println("WebTest: homepage, read API, mutation method/token/origin and escaping PASS");
    }
}
