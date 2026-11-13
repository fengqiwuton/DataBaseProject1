-- Run in the project database as the owner, after loading sql/import.sql.
BEGIN;
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'metro_sql_reader') THEN
        CREATE ROLE metro_sql_reader LOGIN;
    END IF;
END $$;
GRANT USAGE ON SCHEMA project1 TO metro_sql_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA project1 TO metro_sql_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA project1 GRANT SELECT ON TABLES TO metro_sql_reader;
COMMIT;
