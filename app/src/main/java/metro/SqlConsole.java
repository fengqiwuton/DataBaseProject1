package metro;

import java.sql.*;
import java.util.*;
import org.postgresql.core.Parser;

final class SqlConsole {
    private static final int MAX_ROWS = 200;
    private static final int MAX_CELL_LENGTH = 2000;
    private static final int MAX_RESULT_LENGTH = 250_000;
    private static final Set<String> QUERY_COMMANDS = Set.of("SELECT", "WITH", "SHOW", "EXPLAIN", "VALUES", "TABLE");

    private SqlConsole() {}

    static Map<String, Object> query(Db db, String input) throws SQLException {
        if (input == null || input.isBlank()) {
            throw new IllegalArgumentException("请输入一条 SQL 查询。");
        }
        var queries = Parser.parseJdbcSql(input, true, false, true, false, false);
        if (queries.size() != 1) {
            throw new IllegalArgumentException("每次请输入一条 SQL 查询。");
        }
        String sql = queries.get(0).nativeSql;
        if (!QUERY_COMMANDS.contains(firstKeyword(sql))) {
            throw new IllegalArgumentException("请输入只读查询，例如 SELECT、WITH、SHOW 或 EXPLAIN。");
        }
        return db.forSqlConsole().transaction(true, connection -> {
            try (Statement statement = connection.createStatement()) {
                statement.execute("SET TRANSACTION READ ONLY");
                try (ResultSet role = statement.executeQuery(
                        "SELECT NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE "
                        +"(rolsuper OR rolcreaterole OR rolcreatedb OR rolreplication OR rolbypassrls OR "
                        +"rolname IN ('pg_read_server_files','pg_write_server_files','pg_execute_server_program','pg_signal_backend')) "
                        +"AND pg_catalog.pg_has_role(current_user, oid, 'MEMBER'))")) {
                    role.next();
                    if (!role.getBoolean(1)) throw new IllegalArgumentException("SQL 控制台需要配置专用的低权限数据库账号。");
                }
                statement.execute("SET LOCAL standard_conforming_strings = on");
                statement.execute("SET LOCAL statement_timeout = '5s'");
                statement.setEscapeProcessing(false);
                statement.setFetchSize(50);
                statement.setMaxRows(MAX_ROWS + 1);
                try (ResultSet results = statement.executeQuery(sql)) {
                    return readResults(results);
                }
            }
        });
    }

    private static String firstKeyword(String sql) {
        char[] text = sql.toCharArray();
        int i = 0;
        while (i < text.length) {
            if (Character.isWhitespace(text[i])) i++;
            else if (sql.startsWith("--", i)) i = Parser.parseLineComment(text, i) + 1;
            else if (sql.startsWith("/*", i)) i = Parser.parseBlockComment(text, i) + 1;
            else break;
        }
        int start = i;
        while (i < text.length && Character.isLetter(text[i])) i++;
        return sql.substring(Math.min(start, text.length), Math.min(i, text.length)).toUpperCase(Locale.ROOT);
    }

    private static Map<String, Object> readResults(ResultSet results) throws SQLException {
        ResultSetMetaData metadata = results.getMetaData();
        int count = metadata.getColumnCount();
        List<String> columns = new ArrayList<>();
        for (int i = 1; i <= count; i++) columns.add(metadata.getColumnLabel(i));
        List<List<String>> rows = new ArrayList<>();
        int remaining = MAX_RESULT_LENGTH;
        boolean clipped = false;
        boolean truncated = false;
        while (results.next()) {
            if (rows.size() == MAX_ROWS || remaining < count * 16) {
                truncated = true;
                break;
            }
            List<String> row = new ArrayList<>();
            int cellLimit = Math.min(MAX_CELL_LENGTH, remaining / count);
            for (int i = 1; i <= count; i++) {
                String value = results.getString(i);
                if (value != null && value.length() > cellLimit) {
                    int end = Character.isHighSurrogate(value.charAt(cellLimit - 1)) ? cellLimit - 1 : cellLimit;
                    value = value.substring(0, end) + "…";
                    clipped = true;
                }
                row.add(value);
                remaining -= value == null ? 4 : value.length();
            }
            rows.add(row);
        }
        return Map.of("columns", columns, "rows", rows, "truncated", truncated, "clipped", clipped);
    }
}
