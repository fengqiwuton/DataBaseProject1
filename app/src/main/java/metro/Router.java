package metro;

import java.util.*;

public final class Router {
    public record Edge(int from,int to,int line) { }
    public record Result(boolean found,List<Integer> stations,List<Integer> lines,int transfers,int stops) { }
    private record State(int station,int line) { }
    private record Cost(int transfers,int stops) implements Comparable<Cost> {
        public int compareTo(Cost o) { int c=Integer.compare(transfers,o.transfers); return c!=0?c:Integer.compare(stops,o.stops); }
    }
    private record Visit(State state,Cost cost) { }
    private record Previous(State state,int line) { }
    private Router() { }
    public static Result route(List<Edge> edges,Set<Integer> starts,Set<Integer> ends,String mode) {
        if(!mode.equals("stops") && !mode.equals("transfers")) throw new IllegalArgumentException("路径模式应为stops或transfers");
        Map<Integer,List<Edge>> graph=new TreeMap<>();
        for(Edge e:edges) graph.computeIfAbsent(e.from(),k->new ArrayList<>()).add(e);
        graph.values().forEach(v->v.sort(Comparator.comparingInt(Edge::line).thenComparingInt(Edge::to)));
        Map<State,Previous> previous=new HashMap<>();
        if(mode.equals("stops")) {
            ArrayDeque<State> queue=new ArrayDeque<>();
            Set<Integer> seen=new HashSet<>();
            for(int start:new TreeSet<>(starts)) { State s=new State(start,0); queue.add(s); seen.add(start); previous.put(s,null); }
            while(!queue.isEmpty()) {
                State current=queue.remove();
                if(ends.contains(current.station())) return reconstruct(current,previous);
                for(Edge e:graph.getOrDefault(current.station(),List.of())) if(seen.add(e.to())) {
                    State next=new State(e.to(),e.line());
                    previous.put(next,new Previous(current,e.line())); queue.add(next);
                }
            }
        } else {
            PriorityQueue<Visit> queue=new PriorityQueue<>(Comparator.comparing(Visit::cost)
                .thenComparingInt(v->v.state().station()).thenComparingInt(v->v.state().line()));
            Map<State,Cost> best=new HashMap<>();
            for(int start:new TreeSet<>(starts)) {
                State s=new State(start,0); Cost cost=new Cost(0,0);
                best.put(s,cost); previous.put(s,null); queue.add(new Visit(s,cost));
            }
            while(!queue.isEmpty()) {
                Visit visit=queue.remove(); State current=visit.state();
                if(!visit.cost().equals(best.get(current))) continue;
                if(ends.contains(current.station())) return reconstruct(current,previous);
                for(Edge e:graph.getOrDefault(current.station(),List.of())) {
                    State next=new State(e.to(),e.line());
                    Cost cost=new Cost(visit.cost().transfers()+(current.line()!=0 && current.line()!=e.line()?1:0),visit.cost().stops()+1);
                    if(!best.containsKey(next) || cost.compareTo(best.get(next))<0) {
                        best.put(next,cost); previous.put(next,new Previous(current,e.line())); queue.add(new Visit(next,cost));
                    }
                }
            }
        }
        return new Result(false,List.of(),List.of(),0,0);
    }
    private static Result reconstruct(State target,Map<State,Previous> previous) {
        LinkedList<Integer> stations=new LinkedList<>(), lines=new LinkedList<>();
        State node=target;
        while(node!=null) {
            stations.addFirst(node.station()); Previous p=previous.get(node);
            if(p==null) break;
            lines.addFirst(p.line()); node=p.state();
        }
        int transfers=0;
        for(int i=1;i<lines.size();i++) if(!lines.get(i).equals(lines.get(i-1))) transfers++;
        return new Result(true,List.copyOf(stations),List.copyOf(lines),transfers,lines.size());
    }
}
