"""Cross-check the Task 1 and Task 2 deliverables against the course requirements.

Task 1 (concept E-R diagram, 20%)  -> docs/ER_lecture7/概念ER图_drawio.drawio
Task 2 (database design, 20%)      -> sql/schema.sql plus the live PostgreSQL catalog

Checks that the picture, the DDL, the catalog and the written deliverables agree:
notation and cardinality, figure attributes vs table columns, every foreign key
represented by a relationship, keys / NOT NULL / business UNIQUE / acyclic foreign keys,
field types, and that the field dictionary covers every column. Missing deliverables
(the DataGrip relationship screenshot, per-field prose) are reported as MISSING, not
silently ignored.

    python tools/check_design.py --psql "D:/PostgreSQL/bin/psql.exe"
    python tools/check_design.py --skip-db          # figure + DDL + docs only
"""
import argparse
import os
import pathlib
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIGURE = ROOT / 'docs/ER_lecture7/概念ER图_drawio.drawio'
FIGURE_PNG = ROOT / 'docs/ER_lecture7/E-R_project1.png'
FIGURE_NOTES = ROOT / 'docs/ER_lecture7/概念ER图_drawio说明.md'
ER_DETAIL = ROOT / 'docs/ER_lecture7/ER设计思路与项目要求对应说明.md'
SCHEMA = ROOT / 'sql/schema.sql'
IMPORT_SQL = ROOT / 'sql/import.sql'
PLAN_DOC = ROOT / '项目要求总结与技术实现路线.md'
ER_DOC = ROOT / 'docs/er.md'
DOCS = ROOT / 'docs'

ENTITY_TABLES = {'district': 'district', 'station': 'station',
                 'line': 'metro_line', 'exit': 'station_exit'}
EXPECTED_ATTRS = {
    'district': [('district_id', 'pk'), ('name_en', '')],
    'station': [('station_id', 'pk'), ('name_zh', ''), ('name_en', ''),
                ('lon_mdeg', ''), ('lat_mdeg', '')],
    'line': [('line_id', 'pk'), ('name_zh', ''), ('name_en', '')],
    # exit is a weak entity: identified by its owner plus the partial key exit_code,
    # so it has no key of its own in the concept diagram.
    'exit': [('exit_code', 'partial'), ('{landmark_name}', '')],
}
# exit pulls landmark_name from exit_landmark; the other three map one table each.
EXTRA_COLUMNS = {'exit': ['landmark_name']}
# Foreign-key columns belong to relationships in a concept diagram, not to the entity's
# attribute list; they are therefore expected to be absent from the figure.
FIGURE_EXCLUDE = {'station': {'district_id'}, 'exit': {'station_id'}}
# The weak entity's surrogate id is a physical detail, so the concept diagram omits it.
SURROGATE_OMITTED = {'exit': {'exit_id'}}
WEAK_ENTITIES = {'exit'}
IDENTIFYING_RELATIONSHIPS = {'exit_station'}
FK_RELATIONSHIPS = {
    ('station', 'district'): 'station_district',
    ('station_exit', 'station'): 'exit_station',
    ('line_station', 'station'): 'line_station',
    ('line_station', 'metro_line'): 'line_station',
}
MULTIVALUED_FK = ('exit_landmark', 'station_exit')
DIAMONDS = {'station_district', 'line_station', 'exit_station'}
REL_ATTRS = ['position', 'status', 'opening_year', 'first_train', 'last_train']
ARROWS = {('station_district', 'district'), ('exit_station', 'station')}
DOUBLE_LINES = {('station', 'station_district'), ('exit', 'exit_station')}
REQUIRED_CHECKS = ['status = ANY', '"position" > 0', 'opening_year >= 1900',
                   'btrim(name_zh)', "lon_mdeg >= '-180000'", 'lon_mdeg IS NULL']
TABLES = ['district', 'exit_landmark', 'line_station', 'metro_line', 'station', 'station_exit']


class Report:
    def __init__(self):
        self.counts = {'PASS': 0, 'FAIL': 0, 'WARN': 0, 'MISSING': 0}

    def line(self, status, text, detail=''):
        self.counts[status] += 1
        print(f'{status:7} {text}' + (f'   [{detail}]' if detail else ''))

    def section(self, title):
        print(f'\n== {title} ==')

    def total(self):
        return sum(self.counts.values()), self.counts


def style_map(cell):
    return dict(pair.split('=', 1) for pair in cell.get('style', '').split(';') if '=' in pair)


def geometry(cell):
    g = cell.find('mxGeometry')
    return tuple(float(g.get(key)) for key in ('x', 'y', 'width', 'height'))


def plain(value):
    return re.sub(r'<[^>]+>', '', value or '')


def bare(value):
    """列名去掉后面的（CSV 列名）标注，便于与 DDL 列名比对。"""
    return re.split(r'[（(]', value or '', 1)[0].strip()


# --- Task 1: the figure ---------------------------------------------------------------------
def check_figure(report, columns):
    report.section('Task 1: concept E-R diagram')
    for path, label in [(FIGURE, 'drawio source'), (FIGURE_PNG, 'PNG image')]:
        report.line('PASS' if path.exists() else 'FAIL', f'{label} exists', path.name)

    if not FIGURE.exists():
        return
    try:
        root = ET.parse(FIGURE).getroot()
    except ET.ParseError as error:
        report.line('FAIL', 'drawio XML parses', str(error))
        return
    report.line('PASS', 'drawio XML parses')
    pages = root.findall('.//diagram')
    report.line('PASS' if len(pages) == 1 else 'WARN', 'single diagram page', str(len(pages)))

    cells = {c.get('id'): c for c in root.findall('.//mxCell')}
    edges = [c for c in cells.values() if c.get('edge') == '1']
    report.line('PASS' if not any(e.get('source') not in cells or e.get('target') not in cells
                                  for e in edges) else 'FAIL',
                'every connector is attached to existing shapes')

    # entities, attributes, keys and the weak-entity conventions
    for entity, expected in EXPECTED_ATTRS.items():
        head = cells.get(entity + '_head')
        ok = head is not None and plain(head.get('value')) == entity
        report.line('PASS' if ok else 'FAIL', f'entity box "{entity}" present')
        rows = []
        index = 1
        while f'{entity}_attr_{index}' in cells:
            rows.append(cells[f'{entity}_attr_{index}'].get('value') or '')
            index += 1
        marks = []
        for value in rows:
            if '<u>' in value:
                marks.append((bare(plain(value)), 'pk'))        # 主键：实线下划线
            elif 'dashed' in value:
                marks.append((bare(plain(value)), 'partial'))   # 弱实体部分键：虚线下划线
            else:
                marks.append((bare(plain(value)), ''))
        report.line('PASS' if marks == expected else 'FAIL',
                    f'"{entity}" attributes and key marking', f'{marks}')

    for entity in sorted(WEAK_ENTITIES):
        report.line('PASS' if cells.get(entity + '_frame') is not None else 'FAIL',
                    f'"{entity}" is a weak entity (double rectangle frame present)')

    for diamond in sorted(DIAMONDS):
        cell = cells.get(diamond)
        report.line('PASS' if cell is not None and plain(cell.get('value')) == diamond else 'FAIL',
                    f'relationship diamond "{diamond}"')
    for diamond in sorted(IDENTIFYING_RELATIONSHIPS):
        cell = cells.get(diamond)
        report.line('PASS' if cell is not None and 'double=1' in cell.get('style', '')
                    else 'FAIL', f'"{diamond}" is an identifying relationship (double diamond)')
    for diamond in sorted(DIAMONDS - IDENTIFYING_RELATIONSHIPS):
        cell = cells.get(diamond)
        report.line('PASS' if cell is not None and 'double=1' not in cell.get('style', '')
                    else 'FAIL', f'"{diamond}" stays a single diamond (ordinary relationship)')

    rel_rows = [bare(plain(cells[f'rel_attr_{i}'].get('value'))) for i in range(1, 6)
                if f'rel_attr_{i}' in cells]
    report.line('PASS' if rel_rows == REL_ATTRS else 'FAIL',
                'relationship attributes box holds the five "line_station" columns', str(rel_rows))

    # cardinality: arrows and total-participation double lines
    arrow_edges = [e for e in edges if 'endArrow=classic' in e.get('style', '')]
    arrow_pairs = {(e.get('source', '').replace('_head', '').replace('_body', ''),
                    e.get('target', '').replace('_head', '').replace('_body', ''))
                   for e in arrow_edges}
    report.line('PASS' if len(arrow_edges) == 2 and arrow_pairs == ARROWS else 'FAIL',
                'two arrows mark the "at most one" side', str(sorted(arrow_pairs)))

    pairs = {}
    for edge in edges:
        if 'endArrow=classic' in edge.get('style', '') or 'dashed=1' in edge.get('style', ''):
            continue
        key = (edge.get('source', '').replace('_head', '').replace('_body', ''),
               edge.get('target', '').replace('_head', '').replace('_body', ''))
        pairs[key] = pairs.get(key, 0) + 1
    doubled = {key for key, count in pairs.items() if count == 2}
    report.line('PASS' if doubled == DOUBLE_LINES else 'FAIL',
                'two double lines mark total participation', str(sorted(doubled)))

    dashed = [e for e in edges if 'dashed=1' in e.get('style', '')]
    report.line('PASS' if len(dashed) == 1 and dashed[0].get('source') == 'line_station'
                else 'FAIL', 'relationship attributes attached by one dashed line')

    # orthogonality: recompute endpoints from the stored fractions
    worst = 0.0
    for edge in edges:
        style = style_map(edge)
        sx, sy, sw, sh = geometry(cells[edge.get('source')])
        tx, ty, tw, th = geometry(cells[edge.get('target')])
        ax = sx + float(style['exitX']) * sw
        ay = sy + float(style['exitY']) * sh
        bx = tx + float(style['entryX']) * tw
        by = ty + float(style['entryY']) * th
        worst = max(worst, min(abs(ax - bx), abs(ay - by)))
    report.line('PASS' if worst <= 0.01 else 'FAIL',
                'all connectors horizontal or vertical', f'max deviation {worst:.4f} px')

    # nothing but the diagram: no notes, legend or title inside the picture
    allowed = set(ENTITY_TABLES) | set(DIAMONDS) | set(REL_ATTRS)
    for attrs in EXPECTED_ATTRS.values():
        allowed |= {name for name, _ in attrs} | {name.strip('{}') for name, _ in attrs}
    stray = []
    for cell in cells.values():
        value = bare(plain(cell.get('value')))
        if value and value not in allowed:
            stray.append(value)
    report.line('PASS' if not stray else 'FAIL',
                'no notes, legend or title inside the picture', str(stray))

    # figure attributes vs the DDL columns
    if columns:
        for entity, table in ENTITY_TABLES.items():
            drawing = [bare(plain(cells[f'{entity}_attr_{i}'].get('value'))).strip('{}')
                       for i in range(1, len(EXPECTED_ATTRS[entity]) + 1)
                       if f'{entity}_attr_{i}' in cells]
            allowed = ((set(columns.get(table, []))
                        - FIGURE_EXCLUDE.get(entity, set())
                        - SURROGATE_OMITTED.get(entity, set()))
                       | set(EXTRA_COLUMNS.get(entity, [])))
            report.line('PASS' if set(drawing) == allowed else 'FAIL',
                        f'figure attributes of "{entity}" match table {table}',
                        f'figure={drawing} table={sorted(allowed)}')

    notes = FIGURE_NOTES.read_text(encoding='utf-8') if FIGURE_NOTES.exists() else ''
    report.line('PASS' if ('diagrams.net' in notes or 'draw.io' in notes) else 'MISSING',
                'drawing tool named next to the figure')
    report.line('PASS' if 'metro_line' in notes and 'station_exit' in notes else 'FAIL',
                'concept names mapped to table names in the notes')
    return {plain(cells[d].get('value')) for d in DIAMONDS if d in cells}


# --- Task 2: DDL and catalog ---------------------------------------------------------------
def split_top_level(body):
    """Split a CREATE TABLE body on commas that are not inside parentheses."""
    parts, depth, current = [], 0, ''
    for char in body:
        if char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
        if char == ',' and depth == 0:
            parts.append(current)
            current = ''
        else:
            current += char
    parts.append(current)
    return [part.strip() for part in parts if part.strip()]


def schema_columns_from_file():
    text = SCHEMA.read_text(encoding='utf-8')
    columns = {}
    for match in re.finditer(r'CREATE TABLE project1\.(\w+)\s*\((.*?)\n\);', text, re.S):
        table, body = match.group(1), match.group(2)
        names = []
        for entry in split_top_level(body):
            if entry.split()[0].upper() in ('CONSTRAINT', 'PRIMARY', 'UNIQUE',
                                            'FOREIGN', 'CHECK'):
                continue
            names.append(entry.split()[0])
        columns[table] = names
    return columns


def catalog(psql, conn):
    def rows(sql):
        proc = subprocess.run(psql + conn + ['-At', '-F', '\t', '-f', '-'],
                              input=sql.encode('utf-8'), capture_output=True,
                              env=dict(os.environ, PGCLIENTENCODING='UTF8'))
        if proc.returncode:
            raise RuntimeError(proc.stderr.decode('utf-8', 'replace').strip())
        return [line.split('\t') for line in proc.stdout.decode('utf-8').splitlines()]

    columns = {}
    for table, column, data_type, nullable, identity, precision in rows(
            "SELECT table_name, column_name, data_type, is_nullable, is_identity,"
            " COALESCE(datetime_precision::text,'') FROM information_schema.columns"
            " WHERE table_schema='project1' ORDER BY table_name, ordinal_position"):
        columns.setdefault(table, []).append(column)
    constraints = rows("SELECT conrelid::regclass::text, conname, contype,"
                       " pg_get_constraintdef(oid) FROM pg_constraint"
                       " WHERE connamespace='project1'::regnamespace ORDER BY 1,2")
    sequences = [r[0] for r in rows("SELECT sequencename FROM pg_sequences"
                                    " WHERE schemaname='project1'")]
    detail = rows("SELECT table_name, column_name, data_type, is_nullable, is_identity,"
                  " COALESCE(datetime_precision::text,'') FROM information_schema.columns"
                  " WHERE table_schema='project1'")
    return columns, constraints, sequences, detail


def check_ddl(report):
    report.section('Task 2: standalone DDL file')
    if not SCHEMA.exists():
        report.line('FAIL', 'sql/schema.sql exists')
        return
    text = SCHEMA.read_text(encoding='utf-8')
    report.line('PASS', 'sql/schema.sql exists')
    # 课程要求"单独传一份只含建表语句的 SQL"：schema.sql 只放 CREATE TABLE，
    # 由 import.sql 负责建 schema；因此这里不再要求它自带 CREATE SCHEMA。
    imported = IMPORT_SQL.read_text(encoding='utf-8') if IMPORT_SQL.exists() else ''
    only_tables = not re.search(r'(?m)^\s*CREATE\s+(SCHEMA|INDEX|FUNCTION|VIEW)\b', text)
    report.line('PASS' if only_tables else 'WARN',
                'DDL holds only CREATE TABLE statements (schema/索引/函数在 import.sql 侧)')
    report.line('PASS' if re.search(r'CREATE SCHEMA IF NOT EXISTS project1', imported) else 'FAIL',
                'import.sql creates the schema before the tables')
    creates = re.findall(r'CREATE TABLE project1\.(\w+)', text)
    report.line('PASS' if sorted(creates) == TABLES else 'FAIL',
                'DDL creates exactly the six tables', str(sorted(creates)))
    dirty = re.findall(r'(?im)^\s*(INSERT|COPY|UPDATE|DELETE)\b', text)
    report.line('PASS' if not dirty else 'FAIL', 'DDL carries no data statements', str(dirty))
    meta = [line for line in text.splitlines() if line.strip().startswith('\\')]
    report.line('PASS' if not meta else 'FAIL', 'DDL has no psql meta-commands', str(meta))

    body = re.sub(r'^\s*CREATE SCHEMA IF NOT EXISTS project1;', '', text, count=1).strip()
    report.line('PASS' if body and body in imported else 'FAIL',
                'import.sql embeds this exact DDL (no drift between the two)')

    columns = schema_columns_from_file()
    total = sum(len(value) for value in columns.values())
    report.line('PASS' if total == 23 else 'FAIL', 'DDL defines 23 columns', f'{total}')


def check_catalog(report, psql_bin, conn, figure_diamonds):
    report.section('Task 2: live catalog')
    psql = [psql_bin]
    try:
        columns, constraints, sequences, detail = catalog(psql, conn)
    except Exception as error:
        report.line('MISSING', 'catalog reachable; run without --skip-db to check keys',
                    str(error).splitlines()[0][:80])
        return
    tables = sorted(columns)
    report.line('PASS' if tables == TABLES else 'FAIL',
                'catalog holds exactly the six tables', str(tables))

    by_table = {}
    for table, name, kind, definition in constraints:
        by_table.setdefault(table.split('.')[-1], []).append((name, kind, definition))
    for table in TABLES:
        items = by_table.get(table, [])
        report.line('PASS' if any(k == 'p' for _, k, _ in items) else 'FAIL',
                    f'{table}: primary key')
    non_identity = {table: [row for row in detail
                            if row[0] == table and row[3] == 'NO' and row[4] == 'NO']
                    for table in TABLES}
    report.line('PASS' if all(non_identity[t] for t in TABLES) else 'FAIL',
                'every table has a non-identity NOT NULL business column')
    for table in TABLES:
        kinds = [k for _, k, _ in by_table.get(table, [])]
        if table == 'exit_landmark':
            report.line('PASS' if 'p' in kinds else 'FAIL',
                        'exit_landmark: composite primary key is the business key')
        else:
            report.line('PASS' if 'u' in kinds else 'FAIL', f'{table}: business UNIQUE')

    edges = []
    for child, items in by_table.items():
        for _, kind, definition in items:
            if kind == 'f':
                match = re.search(r'REFERENCES project1\.(\w+)', definition)
                if match:
                    edges.append((child, match.group(1)))
    report.line('PASS' if len(edges) == 5 else 'FAIL', 'five foreign keys', str(sorted(edges)))
    involved = {table for edge in edges for table in edge}
    report.line('PASS' if involved == set(TABLES) else 'FAIL',
                'every table participates in a foreign key', str(set(TABLES) - involved))

    # every foreign key is drawn as a relationship in the Task 1 figure
    if figure_diamonds:
        missing = []
        for edge in edges:
            if edge == MULTIVALUED_FK:
                continue
            diamond = FK_RELATIONSHIPS.get(edge)
            if diamond is None or diamond not in figure_diamonds:
                missing.append(edge)
        report.line('PASS' if not missing else 'FAIL',
                    'every foreign key appears as a relationship in the figure',
                    f'missing={missing}')

    # acyclic test on the child -> parent direction
    direction = {}
    for child, parent in edges:
        direction.setdefault(child, []).append(parent)
    seen, stack = set(), set()

    def acyclic(node):
        if node in stack:
            return False
        if node in seen:
            return True
        seen.add(node)
        stack.add(node)
        for parent in direction.get(node, []):
            if not acyclic(parent):
                return False
        stack.discard(node)
        return True

    report.line('PASS' if all(acyclic(t) for t in TABLES) else 'FAIL',
                'foreign-key direction is acyclic')

    checks = ' | '.join(definition for _, _, kind, definition in constraints if kind == 'c')
    for expectation in REQUIRED_CHECKS:
        report.line('PASS' if expectation in checks else 'FAIL',
                    f'CHECK present: {expectation}')

    report.line('PASS' if len(sequences) == 4 else 'FAIL',
                'four identity sequences', str(sequences))
    report.line('PASS' if not [row for row in detail if row[2] == 'character']
                else 'FAIL', 'no char(n) columns')
    report.line('PASS' if all(row[5] == '0' for row in detail
                              if row[2] == 'time without time zone') else 'FAIL',
                'train times are time(0)')
    report.line('PASS' if any(row[0] == 'line_station' and row[1] == 'opening_year'
                              and row[2] == 'smallint' for row in detail) else 'FAIL',
                'opening_year is smallint')


def check_docs(report):
    report.section('Task 2: written deliverables')
    columns = sum((names for names in schema_columns_from_file().values()), [])
    plan = PLAN_DOC.read_text(encoding='utf-8')
    missing = [column for column in columns if column not in plan]
    report.line('PASS' if not missing else 'FAIL',
                'field dictionary mentions every column', str(missing))
    er = ER_DOC.read_text(encoding='utf-8') + ER_DETAIL.read_text(encoding='utf-8')
    report.line('PASS' if ('3NF' in er or '第三范式' in er) else 'FAIL',
                '3NF argument present in the design notes')
    one = '1NF' in er or '原子' in er
    two = '2NF' in er or '部分依赖' in er or '依赖完整' in er
    report.line('PASS' if one and two else 'WARN',
                '1NF (atomic values) and 2NF (no partial dependency) also argued',
                f'1NF={"yes" if one else "no"} 2NF={"yes" if two else "no"}')

    screenshots = [p.name for p in DOCS.rglob('*')
                   if p.is_file() and p.suffix.lower() in ('.png', '.jpg', '.jpeg')
                   and 'datagrip' in p.name.lower()]
    report.line('PASS' if screenshots else 'MISSING',
                'DataGrip relationship screenshot (Task 2 requires the client to generate it)',
                ', '.join(screenshots) or 'none found under docs/')
    report.line('MISSING', 'per-table per-field explanation prose for the report '
                           '(source material exists, the report section does not)')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--psql', default='psql')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', default='55437')
    parser.add_argument('--user', default='metro')
    parser.add_argument('--database', default='metro_test')
    parser.add_argument('--skip-db', action='store_true')
    args = parser.parse_args()

    report = Report()
    columns = schema_columns_from_file()
    figure_diamonds = check_figure(report, columns)
    check_ddl(report)
    if args.skip_db:
        report.section('Task 2: live catalog')
        report.line('MISSING', 'catalog checks skipped by --skip-db')
    else:
        check_catalog(report, args.psql,
                      ['-X', '-h', args.host, '-p', str(args.port),
                       '-U', args.user, '-d', args.database],
                      figure_diamonds or set())
    check_docs(report)

    total, counts = report.total()
    print(f"\n{counts['PASS']}/{total} checks passed, {counts['FAIL']} failed, "
          f"{counts['WARN']} warnings, {counts['MISSING']} deliverables missing")
    return 0 if counts['FAIL'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
