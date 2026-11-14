package metro;

import java.nio.file.*;
import java.util.Map;

public final class FareTest {
    public static void main(String[] args) throws Exception {
        Path p=Files.createTempFile("metro-test-fare-",".csv");
        try {
            // Synthetic test fixture only; never packaged as operating fare data.
            Files.writeString(p,"\uFEFForigin_station_id,destination_station_id,amount\n1,2,3.50\n");
            var fare=new FareTable(p);
            if(!fare.lookup(1,2).get("available").equals(true) || !fare.lookup(2,1).get("available").equals(false)) throw new AssertionError("directional fare lookup");
            Files.writeString(p,"origin_station_id,destination_station_id,amount\n1,2,-3\n");
            try { new FareTable(p); throw new AssertionError("negative fare accepted"); }
            catch(java.io.IOException expected) { }
        } finally { Files.deleteIfExists(p); }
        System.out.println("FareTest: external matrix lookup, missing reverse, invalid amount PASS");
    }
}
