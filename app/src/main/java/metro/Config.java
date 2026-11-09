package metro;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.Properties;

public record Config(String url, String user, String password) {
    public static Config load() throws IOException {
        Properties p = new Properties();
        Path file = Path.of(System.getenv().getOrDefault("METRO_CONFIG", "config/db.properties"));
        if (Files.exists(file)) try (Reader r = Files.newBufferedReader(file, StandardCharsets.UTF_8)) { p.load(r); }
        return new Config(value("METRO_DB_URL",p,"url","jdbc:postgresql://127.0.0.1:55437/metro_test"),
            value("METRO_DB_USER",p,"user","metro"),value("METRO_DB_PASSWORD",p,"password",""));
    }
    private static String value(String env, Properties p, String key, String fallback) {
        return System.getenv().getOrDefault(env,p.getProperty(key,fallback));
    }
}
