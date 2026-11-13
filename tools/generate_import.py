"""Deterministic offline CSV -> self-contained PostgreSQL INSERT script.

No database connection and no source mutations. All assumptions live in data-rules.json.
"""
import argparse
import csv
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TABLES = {
    'district': ['district_id', 'name_en'],
    'station': ['station_id', 'district_id', 'name_zh', 'name_en', 'lon_mdeg', 'lat_mdeg'],
    'metro_line': ['line_id', 'name_zh', 'name_en'],
    'line_station': ['line_id', 'station_id', 'position', 'status', 'opening_year', 'first_train', 'last_train'],
    'station_exit': ['exit_id', 'station_id', 'exit_code'],
    'exit_landmark': ['exit_id', 'landmark_name'],
}


def parse_exits(label):
    match = re.fullmatch(r'(\d+)-(\d+)号', label)
    if match:
        a, b = map(int, match.groups())
        if b < a or b - a > 100:
            raise ValueError('Invalid exit range: ' + label)
        return [str(i) + '号' for i in range(a, b + 1)]
    result = [s.strip() for s in re.split('[、/]', label)]
    if not all(result) or len(result) != len(set(result)):
        raise ValueError('Invalid exit list: ' + label)
    return result


def load_model(archive, rules_path):
    rules = json.loads(Path(rules_path).read_text(encoding='utf-8'))
    if rules['coordinate_mapping'] != 'latitude_is_longitude' or rules['exit_count_mode'] != 'atomic':
        raise ValueError('Unsupported mapping mode; update generator and verification together')
    with zipfile.ZipFile(archive) as z:
        raw = {name: z.read(name) for name in rules['expected_sha256']}
    hashes = {k: hashlib.sha256(v).hexdigest() for k, v in raw.items()}
    if hashes != rules['expected_sha256']:
        raise ValueError('Source hashes changed: review mapping and expected assertions before importing')
    stations, exits = [list(csv.DictReader(io.StringIO(raw[n].decode('utf-8-sig'), newline='')))
                       for n in ['shenzhen_stations.csv', 'station_exits.csv']]
    required_s = ['Line Chineses','Line En','Station Name','Station Name EN','Num','District','Status','Opening','Start Time','End Time','latitude','longitude']
    if list(stations[0]) != required_s or list(exits[0]) != ['station_name','station_name_en','exit','landmark']:
        raise ValueError('Unexpected CSV header')
    districts = {name: i for i, name in enumerate(sorted({r['District'] for r in stations}), 1)}
    keys = sorted({(r['Station Name'], r['District']) for r in stations})
    station_ids = {key: i for i, key in enumerate(keys, 1)}
    lines = {}
    for r in stations:
        if r['Line En'] in lines and lines[r['Line En']] != r['Line Chineses']:
            raise ValueError('Conflicting line names')
        lines[r['Line En']] = r['Line Chineses']
    line_ids = {name: i for i, name in enumerate(sorted(lines), 1)}
    model = {k: [] for k in TABLES}
    model['district'] = [(v,k) for k,v in districts.items()]
    model['metro_line'] = [(line_ids[k],lines[k],k) for k in sorted(lines)]
    def coord(value):
        if not value: return None
        n = Decimal(value) * 1000
        if n != n.to_integral_value(): raise ValueError('Coordinate precision exceeds millidegrees')
        return int(n)
    for key in keys:
        rows = [r for r in stations if (r['Station Name'],r['District']) == key]
        def unique_nonempty(col):
            values = {r[col] for r in rows if r[col]}
            if len(values) > 1: raise ValueError(f'Conflicting {col}: {key}')
            return next(iter(values), '')
        model['station'].append((station_ids[key],districts[key[1]],key[0],unique_nonempty('Station Name EN'),
                                 coord(unique_nonempty('latitude')),coord(unique_nonempty('longitude'))))
    smap = {'station_rows': [], 'exit_rows': []}
    for i,r in enumerate(stations,1):
        row = (line_ids[r['Line En']], station_ids[(r['Station Name'],r['District'])], int(r['Num']),
               r['Status'], int(r['Opening']), r['Start Time'] or None, r['End Time'] or None)
        if row[3] not in ('Operation','Construction'): raise ValueError('Unexpected status')
        for t in row[5:]:
            if t is not None and not re.fullmatch(r'\d{2}:\d{2}', t): raise ValueError('Invalid time')
        model['line_station'].append(row)
        smap['station_rows'].append({'source_data_row':i,'source':r,'line_id':row[0],'station_id':row[1]})
    for line in line_ids.values():
        positions = sorted(r[2] for r in model['line_station'] if r[0] == line)
        if positions != list(range(1,len(positions)+1)): raise ValueError('Noncontiguous or duplicate station order')
    raw_exits = []
    for i,r in enumerate(exits,1):
        candidates = [k for k in keys if k[0] == r['station_name']]
        if len(candidates) != 1:
            district = rules['exit_station_district'].get(r['station_name'])
            candidates = [k for k in candidates if k[1] == district]
        if len(candidates) != 1: raise ValueError('Ambiguous or unknown exit station: ' + r['station_name'])
        sid = station_ids[candidates[0]]
        if model['station'][sid-1][3] != r['station_name_en']: raise ValueError('Exit English name mismatch')
        raw_exits.append((i,r,sid,parse_exits(r['exit'])))
    ekeys = sorted((sid,code) for _,_,sid,codes in raw_exits for code in codes)
    if len(ekeys) != len(set(ekeys)): raise ValueError('Repeated atomic exits need explicit source merge policy')
    eids = {k:i for i,k in enumerate(ekeys,1)}
    model['station_exit'] = [(eid,*key) for key,eid in eids.items()]
    links = set()
    for i,r,sid,codes in raw_exits:
        landmarks = [t.strip() for t in r['landmark'].split('，') if t.strip()]
        ids = [eids[(sid,c)] for c in codes]
        for eid in ids:
            links.update((eid,t) for t in landmarks)
        smap['exit_rows'].append({'source_data_row':i,'source':r,'station_id':sid,'exit_ids':ids,'landmarks':landmarks})
    model['exit_landmark'] = sorted(links)
    expected = [10,439,29,567,1304,3271]
    if [len(model[k]) for k in TABLES] != expected: raise ValueError('Unexpected target counts')
    model['sources'] = {'stations':stations,'exits':exits}
    model['source_mapping'] = smap
    model['audit'] = {'source_sha256':hashes,'counts':{k:len(model[k]) for k in TABLES},'rules':rules,
                      'scope':'Offline source/model validation, not a database performance measurement'}
    return model


def literal(value):
    if value is None: return 'NULL'
    if isinstance(value,int): return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def build(output, archive, rules):
    output = Path(output)
    (output/'sql').mkdir(parents=True,exist_ok=True)
    (output/'generated').mkdir(parents=True,exist_ok=True)
    model = load_model(archive,rules)
    # Switch before the first non-ASCII literal, even if psql connects using GBK.
    parts = ['-- Generated by tools/generate_import.py. Rebuilds only project1 objects.',
             'BEGIN;', "SET LOCAL client_encoding = 'UTF8';", 'SET LOCAL standard_conforming_strings = on;']
    # Send the rebuild and load together while keeping ordinary SQL statements inside the block.
    body = ['CREATE SCHEMA IF NOT EXISTS project1;',
            'DROP FUNCTION IF EXISTS project1.get_station_n_neighbor(text,text,integer);']
    body.extend('DROP TABLE IF EXISTS project1.' + table + ';' for table in reversed(TABLES))
    body.append((ROOT/'sql/schema.sql').read_text(encoding='utf-8').strip())
    for table, columns in TABLES.items():
        values = ['(' + ','.join(map(literal, row)) + ')' for row in model[table]]
        body.append(f'INSERT INTO project1.{table} ({",".join(columns)}) VALUES\n' + ',\n'.join(values) + ';')

    sequence_updates = []
    for table in ('district', 'station', 'metro_line', 'station_exit'):
        pk = TABLES[table][0]
        last_id = max(row[0] for row in model[table])
        sequence_updates.append(f"setval(pg_get_serial_sequence('project1.{table}','{pk}'), {last_id}, true)")
    body.append('PERFORM\n    ' + ',\n    '.join(sequence_updates) + ';')
    body.append((ROOT/'sql/indexes.sql').read_text(encoding='utf-8').strip())
    body.append((ROOT/'sql/functions.sql').read_text(encoding='utf-8').strip())
    checks = '\n'.join(
        f"IF (SELECT count(*) FROM project1.{table}) <> {len(model[table])} "
        f"THEN RAISE EXCEPTION 'Invalid count: {table}'; END IF;"
        for table in TABLES
    )
    body.append(checks)
    body.append('ANALYZE ' + ', '.join('project1.' + table for table in TABLES) + ';')
    block = '\n\n'.join(body)
    tag = 'project1_import'
    while f'${tag}$' in block:
        tag += '_'
    parts.append(f'DO ${tag}$\nBEGIN\n{block}\nEND;\n${tag}$;')
    parts.append('COMMIT;')
    (output/'sql/import.sql').write_text('\n\n'.join(parts)+'\n',encoding='utf-8')
    defaults = {4:["'Line 5'"],5:["'Line 1'"],6:["'塘朗%'"],7:["'Mawan'","'Line 5'",'5']}
    queries=['-- DataGrip: run after import.sql; q1..q7.sql are the parameterized application versions.']
    for n in range(1,8):
        sql=(ROOT/f'sql/q{n}.sql').read_text(encoding='utf-8')
        for v in defaults.get(n,[]): sql=sql.replace('?',v,1)
        queries.append(f'-- Q{n}\n'+sql)
    queries += ["-- Q7 original PDF invocation\nSELECT project1.get_station_n_neighbor('Mawan','Line 5',2);"]
    (output/'sql/queries.sql').write_text('\n\n'.join(queries)+'\n',encoding='utf-8')
    for name in ['audit','source_mapping']:
        (output/f'generated/{name}.json').write_text(json.dumps(model[name],ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return model


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path,default=ROOT/'source-data/Archive.zip')
    parser.add_argument('--output',type=Path,default=ROOT)
    parser.add_argument('--rules',type=Path,default=ROOT/'config/data-rules.json')
    args=parser.parse_args()
    result=build(args.output,args.archive,args.rules)
    print(json.dumps(result['audit']['counts'],ensure_ascii=False))
