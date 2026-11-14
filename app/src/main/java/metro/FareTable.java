package metro;

import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.io.IOException;
import java.util.*;

/** Optional externally approved fare matrix. Never derives fares from stop counts. */
public final class FareTable {
    private final Map<String,BigDecimal> pairs;
    private final boolean configured;
    public FareTable(Path path) throws IOException {
        Map<String,BigDecimal> rows=new HashMap<>();
        List<String> lines=Files.readAllLines(path,StandardCharsets.UTF_8);
        String header=lines.isEmpty()?"":lines.get(0);
        if(header.startsWith("\uFEFF")) header=header.substring(1);
        if(!header.equals("origin_station_id,destination_station_id,amount")) throw new IOException("票价CSV表头无效");
        for(int i=1;i<lines.size();i++) {
            if(lines.get(i).isBlank()) continue;
            String[] cells=lines.get(i).split(",",-1);
            if(cells.length!=3) throw new IOException("票价CSV应为三列，行"+(i+1));
            try {
                int a=Integer.parseInt(cells[0].trim()),b=Integer.parseInt(cells[1].trim());
                BigDecimal amount=new BigDecimal(cells[2].trim()).setScale(2,java.math.RoundingMode.UNNECESSARY);
                if(a<=0 || b<=0 || amount.signum()<0 || amount.compareTo(new BigDecimal("9999.99"))>0 || rows.putIfAbsent(a+":"+b,amount)!=null) throw new IllegalArgumentException();
            } catch(IllegalArgumentException | ArithmeticException e) { throw new IOException("票价CSV非法值或重复方向对，行"+(i+1),e); }
        }
        pairs=Map.copyOf(rows);
        configured=true;
    }
    private FareTable() { pairs=Map.of(); configured=false; }
    static FareTable fromEnvironment() {
        String file=System.getenv("METRO_FARE_CSV");
        if(file==null || file.isBlank()) return new FareTable();
        try { return new FareTable(Path.of(file)); }
        catch(IOException e) { throw new IllegalArgumentException("无法加载指定票价数据: "+e.getMessage(),e); }
    }
    public Map<String,Object> lookup(int start,int end) {
        if(!configured) return Map.of("available",false,"message","尚未配置票价数据。请设置 METRO_FARE_CSV 并重启程序。");
        BigDecimal value=pairs.get(start+":"+end);
        if(value==null) return Map.of("available",false,"message","已加载票价 CSV，但没有这个出发站到到达站的记录。");
        return Map.of("available",true,"amount",value,"currency","CNY","source","用户配置的票价矩阵");
    }
}
