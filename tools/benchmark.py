"""Read-only warm query benchmark. Uses stdin UTF-8 to avoid Windows -c encoding loss."""
import argparse
import json
from pathlib import Path
import platform
import statistics
import subprocess
import os

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--psql',default='psql')
    p.add_argument('--host',default='127.0.0.1')
    p.add_argument('--port',default='55437')
    p.add_argument('--user',default='metro')
    p.add_argument('--database',default='metro_test')
    p.add_argument('--samples',type=int,default=30)
    args=p.parse_args()
    if args.samples<2: p.error('samples must be at least 2')
    cmd=[args.psql,'-h',args.host,'-p',args.port,'-U',args.user,'-d',args.database,'-v','ON_ERROR_STOP=1','-X','-At','-f','-']
    env=dict(os.environ,PGCLIENTENCODING='UTF8')
    def query(sql):
        proc=subprocess.run(cmd,input=sql.encode('utf-8'),capture_output=True,env=env)
        if proc.returncode: raise RuntimeError(proc.stderr.decode('utf-8',errors='replace'))
        return proc.stdout.decode('utf-8').strip()
    spaces=json.loads(query("SELECT json_agg(t) FROM (SELECT relname,pg_relation_size(relid) heap_bytes,pg_indexes_size(relid) index_bytes,pg_total_relation_size(relid) total_bytes FROM pg_stat_user_tables WHERE schemaname='project1' ORDER BY relname)t;"))
    plans={}
    def json_stream(text):
        values=[]
        decoder=json.JSONDecoder()
        while text.strip():
            text=text.lstrip()
            value,end=decoder.raw_decode(text)
            values.append(value)
            text=text[end:]
        return values
    for n,values in [(3,[]),(4,["'Line 5'"]),(5,["'Line 1'"]),(6,["'塘朗%'"]),(7,["'Mawan'","'Line 5'",'5'])]:
        sql=(ROOT/f'sql/q{n}.sql').read_text(encoding='utf-8')
        for value in values:sql=sql.replace('?',value,1)
        # Keep all samples for a query in one session: PL/pgSQL planning caches are session-local.
        batch='EXPLAIN(ANALYZE,BUFFERS,FORMAT JSON) '+sql+'\n'
        batch+=('EXPLAIN(ANALYZE,FORMAT JSON) '+sql+'\n')*args.samples
        samples=json_stream(query(batch))
        if len(samples)!=args.samples+1:raise RuntimeError('Unexpected benchmark result count')
        measured=samples[0][0]
        timings=[r[0]['Execution Time'] for r in samples[1:]]
        plans['Q'+str(n)]={'execution_ms_median':statistics.median(timings),'execution_ms_p95':sorted(timings)[max(0,int(args.samples*0.95+0.999)-1)],'samples':args.samples,'first_explain':measured}
    result={'scope':'Current model only; server EXPLAIN timing with instrumentation. Each query uses one session with first cold call recorded separately, followed by warm samples. No claim of measured speedup vs another schema. Excludes client startup/network time; application opens fresh connections and may pay cold function planning per request. Space includes table/index/TOAST but not database-wide WAL or shared catalogs.',
            'server_version':query('SELECT version();'),'system':platform.platform(),'space':spaces,
            'table_total_bytes':sum(r['total_bytes'] for r in spaces),'queries':plans}
    (ROOT/'generated/benchmark.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'total_relation_bytes':result['table_total_bytes'],'timings':{k:(v['execution_ms_median'],v['execution_ms_p95']) for k,v in plans.items()}},ensure_ascii=False))


if __name__=='__main__':main()
