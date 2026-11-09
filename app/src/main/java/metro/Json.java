package metro;

import java.util.*;
import java.lang.reflect.RecordComponent;

public final class Json {
    private Json() { }
    public static String encode(Object value) {
        if(value==null) return "null";
        if(value instanceof Boolean || value instanceof Number) return value.toString();
        if(value instanceof Map<?,?> map) {
            List<String> cells=new ArrayList<>();
            map.forEach((k,v)->cells.add(quote(k.toString())+":"+encode(v)));
            return "{"+String.join(",",cells)+"}";
        }
        if(value instanceof Iterable<?> values) {
            List<String> cells=new ArrayList<>(); for(Object v:values) cells.add(encode(v));
            return "["+String.join(",",cells)+"]";
        }
        return quote(value.toString());
    }
    private static String quote(String text) {
        StringBuilder b=new StringBuilder("\"");
        for(char c:text.toCharArray()) switch(c) {
            case '"' -> b.append("\\\""); case '\\' -> b.append("\\\\");
            case '\n' -> b.append("\\n"); case '\r' -> b.append("\\r"); case '\t' -> b.append("\\t");
            default -> { if(c<32) b.append(String.format("\\u%04x",(int)c)); else b.append(c); }
        }
        return b.append('"').toString();
    }
}
