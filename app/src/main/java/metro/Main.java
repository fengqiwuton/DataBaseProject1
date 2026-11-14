package metro;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.CountDownLatch;

public final class Main {
    private record Command(String label,String action,String[] fields) { }
    private static final List<Command> MENU=List.of(
        command("查询车站（中文/英文，可留空列出全部）","stations","search"),
        command("新增车站","stationAdd","name_zh","name_en","district_id","lon_mdeg?","lat_mdeg?"),
        command("修改车站（完整字段；空坐标会清空）","stationUpdate","station_id","name_zh","name_en","district_id","lon_mdeg?","lat_mdeg?"),
        command("删除车站及出口，并修复线路","stationDelete","station_id"),
        command("查询全部线路","lines"),command("新增线路","lineAdd","name_zh","name_en"),
        command("修改线路","lineUpdate","line_id","name_zh","name_en"),command("删除线路（保留物理站点）","lineDelete","line_id"),
        command("查询线路站序","lineStations","line_id"),
        command("插入一站或多站（ID用英文逗号隔开，统一属性）","lineInsert","line_id","position","station_ids","status","opening_year","first_train?","last_train?"),
        command("将站点移出线路","lineRemove","line_id","station_id"),
        command("修改线路站点状态/年份/时刻","membershipUpdate","line_id","station_id","status","opening_year","first_train?","last_train?"),
        command("Q7 前后第n站","q7","station_name","line_name","n"),
        command("两站路径（使用站点ID）","route","start","end","mode?","planned?"),
        command("查找地标候选","landmarks","search"),
        command("两地标路线（完整名称）","landmarkRoute","start_landmark","end_landmark","mode?","planned?"),
        command("两站票价（支持站名或编号）","fare","start","end"),
        command("车站详情/出口/所属线路","stationDetail","station_id"),
        command("Q1 车站总数","q1"),command("Q2 线路总数","q2"),command("Q3 运营站分区统计","q3"),
        command("Q4 按开通年统计","q4","line_name"),command("Q5 出口最多站","q5","line_name"),
        command("Q6 地标LIKE查询（如塘朗%）","q6","prefix"),command("行政区ID列表","districts")
    );
    private static Command command(String label,String action,String... fields) { return new Command(label,action,fields); }
    public static void main(String[] args) {
        System.setOut(new PrintStream(System.out,true,StandardCharsets.UTF_8));
        System.setErr(new PrintStream(System.err,true,StandardCharsets.UTF_8));
        try { run(args); }
        catch(Exception e) { System.err.println("运行失败："+e.getMessage()+"\n首次使用请先配置连接并执行sql/import.sql；详见README。"); System.exit(1); }
    }
    private static void run(String[] args) throws Exception {
        if(args.length>0 && args[0].equals("--help")) {
            System.out.println("Metro CLI | --web [port] | --action <action> key=value ...\n默认读取config/db.properties或METRO_DB_URL/USER/PASSWORD环境变量。");
            return;
        }
        MetroService service=new MetroService(new MetroRepository(new Db(Config.load())));
        service.execute("stats",Map.of());
        if(args.length>0 && args[0].equals("--action")) {
            if(args.length<2) throw new IllegalArgumentException("缺少action");
            Map<String,String> p=new HashMap<>();
            for(int i=2;i<args.length;i++) { String[] pair=args[i].split("=",2); if(pair.length!=2) throw new IllegalArgumentException("参数格式key=value"); p.put(pair[0],pair[1]); }
            System.out.println(Json.encode(service.execute(args[1],p))); return;
        }
        if(args.length>0 && args[0].equals("--web")) {
            try(WebServer server=new WebServer(service,args.length>1?Integer.parseInt(args[1]):8088)) {
                server.start(); System.out.println("浏览器打开 http://127.0.0.1:"+server.port()+" ，Ctrl+C停止。");
                Runtime.getRuntime().addShutdownHook(new Thread(server::close));
                new CountDownLatch(1).await();
            }
            return;
        }
        if(args.length>0) throw new IllegalArgumentException("未知启动参数，使用--help");
        try(Scanner input=new Scanner(System.in,StandardCharsets.UTF_8)) {
            WebServer web=null;
            try {
                System.out.println("深圳地铁数据管理 | 开始前可选择25查看行政区ID，或1/5查看站点/线路ID");
                while(true) {
                    for(int i=0;i<MENU.size();i++) System.out.println((i+1)+". "+MENU.get(i).label());
                    System.out.println("26. 启动浏览器界面\n0. 退出\n请输入操作编号：");
                    if(!input.hasNextLine()) break;
                    String choice=input.nextLine().trim(); if(choice.equals("0")) break;
                    try {
                        int number=Integer.parseInt(choice);
                        if(number==26) {
                            if(web==null) { web=new WebServer(service,8088); web.start(); }
                            System.out.println("浏览器打开 http://127.0.0.1:8088"); continue;
                        }
                        if(number<1 || number>MENU.size()) throw new IllegalArgumentException("无效菜单编号");
                        Command command=MENU.get(number-1); Map<String,String> p=new HashMap<>();
                        for(String field:command.fields()) {
                            boolean optional=field.endsWith("?"); String key=field.replace("?","");
                            if(command.action().equals("fare")) {
                                String station=key.equals("start")?"出发站":"到达站";
                                System.out.println("请输入"+station+"（完整中文站名、英文站名或编号，如 152 或 #152）：");
                            } else {
                                System.out.println("请输入 "+key+(optional?"（可空；mode默认stops，可选transfers；planned默认false）":"")+"：");
                            }
                            if(!input.hasNextLine()) return;
                            String value=input.nextLine().trim();
                            if(!optional || !value.isBlank()) p.put(key,value);
                        }
                        if(MetroService.WRITES.contains(command.action()) && command.action().endsWith("Delete")) {
                            System.out.println("确认删除请输入 DELETE：");
                            if(!input.hasNextLine() || !input.nextLine().equals("DELETE")) { System.out.println("已取消"); continue; }
                        }
                        System.out.println(Json.encode(service.execute(command.action(),p)));
                    } catch(Exception e) { System.out.println("操作失败："+e.getMessage()); }
                }
            } finally { if(web!=null) web.close(); }
        }
    }
}
