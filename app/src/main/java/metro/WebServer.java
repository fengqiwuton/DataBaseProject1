package metro;

import com.sun.net.httpserver.*;
import java.net.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;

/** Loopback-only UI. All writes require a per-process token and same-origin requests. */
public final class WebServer implements AutoCloseable {
    private final HttpServer server;
    private final ExecutorService executor=Executors.newFixedThreadPool(4);
    private final MetroService service;
    private final String token=UUID.randomUUID().toString();
    public WebServer(MetroService service,int port) throws IOException {
        this.service=service;
        server=HttpServer.create(new InetSocketAddress("127.0.0.1",port),0);
        server.createContext("/",this::handle); server.setExecutor(executor);
    }
    public int port() { return server.getAddress().getPort(); }
    String token() { return token; }
    public void start() { server.start(); }
    public void close() { server.stop(0); executor.shutdownNow(); }
    private boolean localAuthority(String host) {
        return host!=null && (host.equals("127.0.0.1:"+port()) || host.equals("localhost:"+port()));
    }
    private void handle(HttpExchange x) throws IOException {
        try {
            if(!localAuthority(x.getRequestHeaders().getFirst("Host"))) { send(x,403,Map.of("error","仅允许本地访问")); return; }
            String path=x.getRequestURI().getPath();
            if(path.equals("/api")) { api(x); return; }
            if(!x.getRequestMethod().equals("GET")) { send(x,405,Map.of("error","不支持的方法")); return; }
            String file=switch(path) { case "/", "/sql" -> "index.html"; case "/app.js" -> "app.js"; case "/style.css" -> "style.css"; default -> null; };
            if(file==null) { send(x,404,Map.of("error","未找到页面")); return; }
            try(InputStream in=WebServer.class.getResourceAsStream("/web/"+file)) {
                if(in==null) { send(x,500,Map.of("error","界面资源缺失，请重新构建")); return; }
                String content=new String(in.readAllBytes(),StandardCharsets.UTF_8);
                if(file.equals("index.html")) content=content.replace("__METRO_TOKEN__",token);
                bytes(x,200,content,file.endsWith("css")?"text/css":file.endsWith("js")?"text/javascript":"text/html");
            }
        } catch(Exception e) { send(x,500,Map.of("error","请求失败，请检查服务状态")); }
        finally { x.close(); }
    }
    private void api(HttpExchange x) throws Exception {
        String method=x.getRequestMethod();
        if(!method.equals("GET") && !method.equals("POST")) { send(x,405,Map.of("error","仅支持GET/POST")); return; }
        Map<String,String> p=decode(x.getRequestURI().getRawQuery());
        if(method.equals("POST")) {
            String origin=x.getRequestHeaders().getFirst("Origin");
            if(!token.equals(x.getRequestHeaders().getFirst("X-Metro-Token")) || (origin!=null && !origin.equals("http://127.0.0.1:"+port()) && !origin.equals("http://localhost:"+port()))) {
                send(x,403,Map.of("error","请求来源或令牌无效")); return;
            }
            String contentType=x.getRequestHeaders().getFirst("Content-Type");
            if(contentType==null || !contentType.startsWith("application/x-www-form-urlencoded")) { send(x,415,Map.of("error","不支持的内容类型")); return; }
            byte[] body=x.getRequestBody().readNBytes(65537);
            if(body.length>65536) { send(x,413,Map.of("error","请求过大")); return; }
            p.putAll(decode(new String(body,StandardCharsets.UTF_8)));
        }
        String action=p.getOrDefault("action","stats");
        if(action.equals("sqlQuery")) {
            if(!method.equals("POST")) { send(x,405,Map.of("error","SQL 查询必须使用 POST")); return; }
            try { send(x,200,Map.of("data",service.sqlQuery(p.get("sql")))); }
            catch(IllegalArgumentException e) { send(x,400,Map.of("error",e.getMessage())); }
            catch(java.sql.SQLException e) {
                String state=e.getSQLState();
                if(state==null || state.startsWith("08") || state.startsWith("28")) send(x,503,Map.of("error","SQL 查询账号无法连接数据库，请确认 PostgreSQL 和只读账号配置。"));
                else if(state.equals("57014")) send(x,400,Map.of("error","查询超时，请缩小查询范围。"));
                else send(x,400,Map.of("error","PostgreSQL "+state+" · "+e.getMessage()));
            }
            return;
        }
        if(MetroService.WRITES.contains(action) && !method.equals("POST")) { send(x,405,Map.of("error","修改操作必须使用POST")); return; }
        try { send(x,200,Map.of("data",service.execute(action,p))); }
        catch(IllegalArgumentException | java.time.DateTimeException e) { send(x,400,Map.of("error",e.getMessage())); }
        catch(java.sql.SQLException e) {
            String state=e.getSQLState();
            String message=state!=null && state.startsWith("23")?"操作违反唯一键、外键或数据约束，请检查重复名称、站点引用和字段范围":state!=null && state.startsWith("22")?e.getMessage():"数据库操作失败，请检查连接或稍后重试";
            send(x,400,Map.of("error",message));
        }
    }
    static Map<String,String> decode(String raw) {
        Map<String,String> p=new HashMap<>();
        if(raw==null || raw.isBlank()) return p;
        for(String part:raw.split("&")) {
            String[] pair=part.split("=",2);
            p.put(URLDecoder.decode(pair[0],StandardCharsets.UTF_8),pair.length==2?URLDecoder.decode(pair[1],StandardCharsets.UTF_8):"");
        }
        return p;
    }
    private static void send(HttpExchange x,int status,Object body) throws IOException { bytes(x,status,Json.encode(body),"application/json"); }
    private static void bytes(HttpExchange x,int status,String content,String type) throws IOException {
        x.getResponseHeaders().set("Content-Type",type+"; charset=utf-8");
        x.getResponseHeaders().set("Cache-Control","no-store");
        x.getResponseHeaders().set("X-Content-Type-Options","nosniff");
        x.getResponseHeaders().set("Content-Security-Policy","default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'");
        byte[] data=content.getBytes(StandardCharsets.UTF_8); x.sendResponseHeaders(status,data.length);
        x.getResponseBody().write(data);
    }
}
