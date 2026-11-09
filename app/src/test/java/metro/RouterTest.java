package metro;

import java.util.*;

public final class RouterTest {
    static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
    public static void main(String[] args) {
        List<Router.Edge> edges = new ArrayList<>();
        // Short path 1-2-5 changes lines; longer path 1-3-4-5 stays on line 10.
        for (int[] e : new int[][]{{1,2,20},{2,5,30},{1,3,10},{3,4,10},{4,5,10}}) {
            edges.add(new Router.Edge(e[0], e[1], e[2]));
            edges.add(new Router.Edge(e[1], e[0], e[2]));
        }
        Router.Result shortest = Router.route(edges, Set.of(1), Set.of(5), "stops");
        check(shortest.found() && shortest.stops() == 2 && shortest.transfers() == 1, "minimum stops");
        Router.Result transfers = Router.route(edges, Set.of(1), Set.of(5), "transfers");
        check(transfers.stations().equals(List.of(1,3,4,5)) && transfers.transfers() == 0, "minimum transfers");
        check(!Router.route(edges, Set.of(1), Set.of(99), "stops").found(), "disconnected");
        check(Router.route(edges, Set.of(1,5), Set.of(5), "stops").stops() == 0, "multi-source same station");
        List<Router.Edge> ties = List.of(new Router.Edge(1,2,10),new Router.Edge(2,3,10),
            new Router.Edge(3,4,10),new Router.Edge(1,4,20));
        check(Router.route(ties,Set.of(1),Set.of(4),"transfers").stops()==1, "transfer tie uses minimum stops");
        try { Router.route(edges,Set.of(1),Set.of(5),"invalid"); throw new AssertionError("mode accepted"); }
        catch (IllegalArgumentException expected) { }
        System.out.println("RouterTest: 6 scenarios PASS");
    }
}
