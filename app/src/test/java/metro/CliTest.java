package metro;

import java.nio.charset.StandardCharsets;
import java.nio.file.Path;

public final class CliTest {
    public static void main(String[] args) throws Exception {
        String java=Path.of(System.getProperty("java.home"),"bin","java.exe").toString();
        Process p=new ProcessBuilder(java,"-Dfile.encoding=GBK","-Dsun.stdout.encoding=GBK","-jar","app/build/metro.jar","--help").start();
        String help=new String(p.getInputStream().readAllBytes(),StandardCharsets.UTF_8);
        if(p.waitFor()!=0 || !help.contains("默认读取")) throw new AssertionError("CLI must output valid Chinese UTF-8 even on a GBK Windows console: "+help);
        System.out.println("CliTest: UTF-8 output under GBK Windows defaults PASS");
    }
}
