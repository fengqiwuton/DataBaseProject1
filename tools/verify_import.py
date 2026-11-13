"""Verify one-click import accuracy against the source CSV model.

Read-only towards the source data; rebuilds project1 from sql/import.sql inside the
target database, then compares every stored value with the model that generated it.

    python tools/verify_import.py --psql "D:/PostgreSQL/bin/psql.exe" \
        --port 55437 --user metro --database metro_test

Exit code 0 only when every check passes.
"""
import argparse
import hashlib
import importlib.util
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
TABLES = ['district', 'station', 'metro_line', 'line_station', 'station_exit', 'exit_landmark']


def load_model():
    spec = importlib.util.spec_from_file_location('gi', ROOT / 'tools/generate_import.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, module.load_model(ROOT / 'source-data/Archive.zip', ROOT / 'config/data-rules.json')


class Psql:
    def __init__(self, exe, host, port, user, database):
        self.base = [exe, '-X', '-h', host, '-p', str(port), '-U', user, '-d', database]
        self.env = dict(os.environ, PGCLIENTENCODING='UTF8')

    def run(self, args):
        return subprocess.run(self.base + args, capture_output=True, env=self.env)

    def rows(self, sql):
        # SQL goes through stdin: Windows argv uses the ANSI code page, which would mangle
        # non-ASCII literals such as 塘朗 before the client encoding applies.
        proc = subprocess.run(self.base + ['-At', '-F', '\t', '-f', '-'],
                              input=sql.encode('utf-8'), capture_output=True, env=self.env)
        if proc.returncode:
            raise RuntimeError(proc.stderr.decode('utf-8', 'replace').strip())
        text = proc.stdout.decode('utf-8')
        return [line.split('\t') for line in text.splitlines()]

    def scalar(self, sql):
        result = self.rows(sql)
        return result[0][0] if result else None

    def must_fail(self, sql):
        proc = self.run(['-q', '-v', 'ON_ERROR_STOP=1', '-c', sql])
        return proc.returncode != 0, proc.stderr.decode('utf-8', 'replace').strip()

    def import_sql(self, path):
        proc = self.run(['-q', '-v', 'ON_ERROR_STOP=1', '-f', str(path)])
        return proc.returncode, proc.stdout.decode('utf-8', 'replace') + proc.stderr.decode('utf-8', 'replace')


class Report:
    def __init__(self):
        self.failed = 0
        self.passed = 0

    def check(self, name, ok, detail=''):
        if ok:
            self.passed += 1
            print(f'PASS  {name}')
        else:
            self.failed += 1
            print(f'FAIL  {name}  {detail}')

    def summary(self):
        total = self.passed + self.failed
        print(f'\n{self.passed}/{total} checks passed, {self.failed} failed')
        return 0 if self.failed == 0 else 1


def expected_rows(model, table):
    r"""Model rows rendered exactly as psql prints them (-A, \N for NULL)."""
    out = []
    for row in model[table]:
        cells = []
        for value in row:
            if value is None:
                cells.append('\\N')
            elif isinstance(value, str) and len(value) == 5 and value[2] == ':':
                cells.append(value + ':00')          # time(0) prints HH:MM:SS
            else:
                cells.append(str(value))
        out.append(cells)
    return out


def db_rows(psql, table, columns):
    cast = ' || chr(9) || '.join(
        f"COALESCE({c}::text,'\\N')" for c in columns)
    sql = f'SELECT {cast} FROM project1.{table}'
    text = psql.run(['-At', '-c', sql]).stdout.decode('utf-8')
    return [line.split('\t') for line in text.splitlines()]


def fingerprint(psql):
    parts = []
    for table in TABLES:
        parts.append(f"COALESCE((SELECT string_agg(t::text,'|' ORDER BY t::text) FROM project1.{table} t),'')")
    return psql.scalar('SELECT md5(concat(' + ','.join(parts) + '))')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--psql', default='psql')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', default='55437')
    parser.add_argument('--user', default='metro')
    parser.add_argument('--database', default='metro_test')
    parser.add_argument('--sql', default=str(ROOT / 'sql/import.sql'))
    parser.add_argument('--skip-rebuild', action='store_true', help='verify the current data without re-importing')
    args = parser.parse_args()

    module, model = load_model()
    psql = Psql(args.psql, args.host, args.port, args.user, args.database)
    report = Report()

    # --- 1. rebuild twice: import must be repeatable and set exactly the documented counts
    if not args.skip_rebuild:
        code, out = psql.import_sql(args.sql)
        report.check('import.sql exits 0', code == 0, out[-400:])
        first = fingerprint(psql)
        code, out = psql.import_sql(args.sql)
        report.check('second import.sql exits 0', code == 0, out[-400:])
        second = fingerprint(psql)
        report.check('repeatable: two imports give identical content', first == second, f'{first} vs {second}')
        print(f'      content md5 = {first}')

    # --- 2. row counts
    for table in TABLES:
        actual = int(psql.scalar(f'SELECT count(*) FROM project1.{table}'))
        report.check(f'count {table} = {len(model[table])}', actual == len(model[table]), f'actual {actual}')

    # --- 3. every stored value against the model
    for table, columns in module.TABLES.items():
        expected = sorted(expected_rows(model, table))
        actual = sorted(db_rows(psql, table, columns))
        if expected == actual:
            report.check(f'values {table} match model row by row', True)
        else:
            missing = [r for r in expected if r not in actual][:2]
            extra = [r for r in actual if r not in expected][:2]
            report.check(f'values {table} match model row by row', False,
                         f'missing={missing} extra={extra}')

    # --- 4. Q1-Q7 as documented in 数据核验摘要.json / the project report
    report.check('Q1 station_count = 439', psql.scalar('SELECT count(*) FROM project1.station') == '439')

    lines = {r[0]: r[2] for r in model['metro_line']}
    stations = {r[0]: r for r in model['station']}
    districts = {r[0]: r[1] for r in model['district']}
    operating = {r[1] for r in model['line_station'] if r[3] == 'Operation'}
    q3 = {}
    for station_id in operating:
        name = districts[stations[station_id][1]]
        q3[name] = q3.get(name, 0) + 1
    actual_q3 = {row[0]: int(row[1]) for row in psql.rows(
        "SELECT d.name_en, count(*) FROM project1.station s JOIN project1.district d USING (district_id) "
        "WHERE EXISTS (SELECT 1 FROM project1.line_station ls WHERE ls.station_id=s.station_id "
        "AND ls.status='Operation') GROUP BY d.district_id, d.name_en")}
    report.check('Q3 operating stations per district', actual_q3 == q3, f'{actual_q3} vs {q3}')

    line5 = [k for k, v in lines.items() if v == 'Line 5'][0]
    q4 = {}
    for row in model['line_station']:
        if row[0] == line5:
            q4[row[4]] = q4.get(row[4], 0) + 1
    actual_q4 = {int(r[0]): int(r[1]) for r in psql.rows(
        "SELECT ls.opening_year, count(*) FROM project1.line_station ls "
        "JOIN project1.metro_line l USING (line_id) WHERE l.name_en='Line 5' GROUP BY 1")}
    report.check('Q4 Line 5 openings by year', actual_q4 == q4, f'{actual_q4} vs {q4}')

    line1 = [k for k, v in lines.items() if v == 'Line 1'][0]
    exits_per_station = {}
    for row in model['station_exit']:
        exits_per_station[row[1]] = exits_per_station.get(row[1], 0) + 1
    members = [r[1] for r in model['line_station'] if r[0] == line1]
    best = max(exits_per_station.get(s, 0) for s in members)
    q5_expected = {stations[s][3] for s in members if exits_per_station.get(s, 0) == best}
    q5 = psql.rows(
        "WITH counts AS (SELECT s.station_id, s.name_en, count(e.exit_id) cnt FROM project1.metro_line l "
        "JOIN project1.line_station ls USING (line_id) JOIN project1.station s USING (station_id) "
        "LEFT JOIN project1.station_exit e USING (station_id) WHERE l.name_en='Line 1' "
        "GROUP BY s.station_id, s.name_en) SELECT name_en, cnt FROM counts WHERE cnt=(SELECT max(cnt) FROM counts)")
    report.check('Q5 Line 1 max exits with ties', {r[0] for r in q5} == q5_expected and
                 all(int(r[1]) == best for r in q5), f'{q5} vs {q5_expected}')

    q6_expected = {(stations[model['station_exit'][eid - 1][1]][2], districts[stations[model['station_exit'][eid - 1][1]][1]],
                    model['station_exit'][eid - 1][2], name)
                   for eid, name in model['exit_landmark'] if name.startswith('塘朗')}
    q6 = {tuple(r) for r in psql.rows(
        "SELECT s.name_zh, d.name_en, e.exit_code, el.landmark_name FROM project1.exit_landmark el "
        "JOIN project1.station_exit e USING (exit_id) JOIN project1.station s USING (station_id) "
        "JOIN project1.district d USING (district_id) WHERE el.landmark_name LIKE '塘朗%'")}
    report.check(f'Q6 塘朗% rows = {len(q6_expected)} with same content', q6 == q6_expected,
                 f'{sorted(q6)} vs {sorted(q6_expected)}')

    q7 = psql.rows("SELECT COALESCE(neighbor,'\\N') FROM project1.get_station_n_neighbor('Mawan','Line 5',5) "
                   "WITH ORDINALITY AS t(neighbor,ord) ORDER BY ord")
    report.check('Q7 Mawan/Line 5/5 = NULL, Linhai', [r[0] for r in q7] == ['\\N', 'Linhai'], str(q7))
    q7b = psql.rows("SELECT COALESCE(neighbor,'\\N') FROM project1.get_station_n_neighbor('Mawan','Line 5',2) "
                    "WITH ORDINALITY AS t(neighbor,ord) ORDER BY ord")
    report.check('Q7 Mawan/Line 5/2 = Liwan, Qianwan', [r[0] for r in q7b] == ['Liwan', 'Qianwan'], str(q7b))

    # --- 5. Q7 edge cases must fail or keep two rows
    ok, _ = psql.must_fail("SELECT * FROM project1.get_station_n_neighbor('Mawan','Line 5',-1)")
    report.check('Q7 negative n raises an error', ok)
    ok, _ = psql.must_fail("SELECT * FROM project1.get_station_n_neighbor('Mawan','Line 5',NULL)")
    report.check('Q7 NULL n raises an error', ok)
    ok, _ = psql.must_fail("SELECT * FROM project1.get_station_n_neighbor('No Such Station','Line 5',1)")
    report.check('Q7 unknown station raises an error', ok)
    ok, _ = psql.must_fail("SELECT * FROM project1.get_station_n_neighbor('Mawan','Line 1',1)")
    report.check('Q7 station not on that line raises an error', ok)
    zero = psql.rows("SELECT COALESCE(neighbor,'\\N') FROM project1.get_station_n_neighbor('Mawan','Line 5',0) "
                     "WITH ORDINALITY AS t(neighbor,ord) ORDER BY ord")
    report.check('Q7 n=0 returns the station twice', [r[0] for r in zero] == ['Mawan', 'Mawan'], str(zero))
    far = psql.rows("SELECT COALESCE(neighbor,'\\N') FROM project1.get_station_n_neighbor('Mawan','Line 5',2147483647) "
                    "WITH ORDINALITY AS t(neighbor,ord) ORDER BY ord")
    report.check('Q7 huge n returns two NULL rows', [r[0] for r in far] == ['\\N', '\\N'], str(far))

    # --- 6. identity sequences continue after the explicitly imported ids
    for table in ['district', 'station', 'metro_line', 'station_exit']:
        column = module.TABLES[table][0]
        seq = psql.scalar(
            "SELECT pg_get_serial_sequence('project1.%s','%s')" % (table, column))
        if not seq:
            report.check(f'sequence exists for {table}.{column}', False)
            continue
        last = int(psql.scalar(f"SELECT last_value FROM {seq}"))
        peak = int(psql.scalar(f'SELECT max({column}) FROM project1.{table}'))
        report.check(f'sequence {table} synced to max id ({peak})', last == peak, f'last_value={last}')

    # --- 7. constraints actually protect the data (each statement must fail)
    negative = [
        ('duplicate station identity', "INSERT INTO project1.station(district_id,name_zh,name_en) "
                                       "SELECT district_id,name_zh,name_en FROM project1.station LIMIT 1"),
        ('blank station name', "INSERT INTO project1.station(district_id,name_zh,name_en) VALUES (1,'  ','X')"),
        ('duplicate exit code on one station', "INSERT INTO project1.station_exit(station_id,exit_code) "
                                               "SELECT station_id,exit_code FROM project1.station_exit LIMIT 1"),
        ('invalid membership status', "INSERT INTO project1.line_station(line_id,station_id,position,status,opening_year) "
                                      "VALUES (1,1,999,'Running',2026)"),
        ('duplicate station position on a line', "INSERT INTO project1.line_station(line_id,station_id,position,status,opening_year) "
                                                 "SELECT line_id, station_id, 1, 'Operation', 2026 FROM project1.line_station "
                                                 "WHERE line_id=1 AND position=30 LIMIT 1"),
        ('orphan landmark', "INSERT INTO project1.exit_landmark(exit_id,landmark_name) VALUES (999999,'x')"),
        ('blank landmark name', "INSERT INTO project1.exit_landmark(exit_id,landmark_name) "
                                "SELECT exit_id,' ' FROM project1.exit_landmark LIMIT 1"),
        ('invalid coordinate range', "INSERT INTO project1.station(district_id,name_zh,name_en,lon_mdeg,lat_mdeg) "
                                     "VALUES (1,'a','a',999999,1)"),
    ]
    for name, sql in negative:
        ok, err = psql.must_fail(sql)
        report.check(f'constraint rejects {name}', ok, err.splitlines()[-1] if err else '')

    after = int(psql.scalar('SELECT count(*) FROM project1.station'))
    report.check('failed statements left the data unchanged', after == len(model['station']), f'count={after}')

    # --- 8. import touches only project1
    if not args.skip_rebuild:
        psql.run(['-q', '-c', 'CREATE SCHEMA IF NOT EXISTS other_work; '
                              'CREATE TABLE IF NOT EXISTS other_work.keep_me(id int primary key); '
                              'INSERT INTO other_work.keep_me VALUES (1) ON CONFLICT DO NOTHING;'])
        code, out = psql.import_sql(args.sql)
        survived = psql.scalar('SELECT count(*) FROM other_work.keep_me')
        report.check('import leaves other schemas untouched', code == 0 and survived == '1',
                     f'exit={code} rows={survived}')
        objects = psql.rows("SELECT relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                            "WHERE n.nspname='project1' AND c.relkind='r' ORDER BY relname")
        report.check('project1 holds exactly the six tables',
                     [r[0] for r in objects] == sorted(TABLES), str(objects))
        functions = psql.rows("SELECT proname FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
                              "WHERE n.nspname='project1'")
        report.check('project1 holds exactly one function (Q7)',
                     [r[0] for r in functions] == ['get_station_n_neighbor'], str(functions))
        psql.run(['-q', '-c', 'DROP SCHEMA other_work CASCADE;'])

    return report.summary()


if __name__ == '__main__':
    sys.exit(main())
