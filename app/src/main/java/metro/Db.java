package metro;

import java.sql.*;

public final class Db {
    private final Config config;
    public Db(Config config) { this.config=config; }
    Db forSqlConsole() {
        return new Db(new Config(config.url(),System.getenv().getOrDefault("METRO_SQL_USER","metro_sql_reader"),
            System.getenv().getOrDefault("METRO_SQL_PASSWORD","")));
    }
    public Connection open() throws SQLException {
        Connection c = DriverManager.getConnection(config.url(),config.user(),config.password());
        try (Statement s=c.createStatement()) {
            s.execute("SET search_path TO project1,pg_catalog");
            s.execute("SET statement_timeout TO '15s'");
            s.execute("SET lock_timeout TO '8s'");
        } catch (SQLException e) { c.close(); throw e; }
        return c;
    }
    @FunctionalInterface public interface Work<T> { T run(Connection c) throws SQLException; }
    public <T> T transaction(boolean snapshot, Work<T> work) throws SQLException {
        try(Connection c=open()) {
            if(snapshot) { c.setTransactionIsolation(Connection.TRANSACTION_REPEATABLE_READ); c.setReadOnly(true); }
            c.setAutoCommit(false);
            try { T result=work.run(c); c.commit(); return result; }
            catch(SQLException | RuntimeException e) { c.rollback(); throw e; }
        }
    }
}
