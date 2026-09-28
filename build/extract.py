"""Pull the Florida slice of Overture Maps Places, reading only the row groups whose bbox touches Florida.

Run from the repo root: python build/extract.py   (writes data/florida-places-{1,2,3}.csv.gz)
For another state, change the box (W, E, S_, N), the region test in work() and the zip prefixes below."""
import re, sys, csv, requests, pyarrow.parquet as pq, pyarrow.compute as pc
from concurrent.futures import ThreadPoolExecutor
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rangefile import RangeFile
REL = '2026-09-23.0'
B = 'https://overturemaps-us-west-2.s3.us-west-2.amazonaws.com/'
W, E, S_, N = -87.7, -79.8, 24.3, 31.1   # Florida box (lon/lat)
COLS = ['id','confidence','websites','emails','phones','addresses','names','sources','operating_status','basic_category','taxonomy','bbox']
keys = re.findall(r'<Key>(.*?)</Key>', requests.get(B+f'?list-type=2&prefix=release/{REL}/theme%3Dplaces/type%3Dplace/').text)

def stats(rg, name):
    for i in range(rg.num_columns):
        c = rg.column(i)
        if c.path_in_schema == name: return c.statistics
def first(v): return v[0] if v else ''
def work(key):
    f = RangeFile(B + key); p = pq.ParquetFile(f); out = []
    hits = []
    for g in range(p.metadata.num_row_groups):
        rg = p.metadata.row_group(g)
        x0, x1, y0, y1 = stats(rg,'bbox.xmin').min, stats(rg,'bbox.xmax').max, stats(rg,'bbox.ymin').min, stats(rg,'bbox.ymax').max
        if x1 >= W and x0 <= E and y1 >= S_ and y0 <= N: hits.append(g)
    for g in hits:
        for r in p.read_row_group(g, columns=COLS).to_pylist():
            b = r['bbox']; lon, lat = b['xmin'], b['ymin']
            if not (W <= lon <= E and S_ <= lat <= N): continue
            a = first(r['addresses']) or {}
            if (a.get('country') or 'US') != 'US': continue
            if a.get('region') and a['region'].upper() not in ('FL', 'FLORIDA'): continue
            name = (r['names'] or {}).get('primary')
            if not name or (r['confidence'] or 0) < 0.5: continue
            if r['operating_status'] and r['operating_status'] != 'open': continue
            t = r['taxonomy'] or {}
            out.append([r['id'], name, t.get('primary') or r['basic_category'] or '', r['basic_category'] or '',
                        ';'.join(t.get('alternates') or []), first(r['phones']), first(r['websites']), first(r['emails']),
                        a.get('freeform') or '', a.get('locality') or '', 'FL', a.get('postcode') or '',
                        round(lat, 6), round(lon, 6), round(r['confidence'], 3),
                        ';'.join(sorted({s['dataset'] for s in (r['sources'] or []) if s.get('dataset')}))])
    print(key[-60:], len(hits), 'groups', len(out), 'rows', f.bytes//1e6, 'MB', flush=True)
    return out

with ThreadPoolExecutor(4) as ex: parts = list(ex.map(work, keys))

# Clean: no newlines inside fields, 5-digit zips, Florida zips only (32/33/34) when a zip is present,
# one row per id. Sort by city then name, and split into three gzipped parts under GitHub's limits.
import gzip, os
HEAD = ['id','name','category','basic_category','alt_categories','phone','website','email','address','city','state','zip','lat','lon','confidence','sources']
seen, rows = set(), []
for part in parts:
    for r in part:
        r = [re.sub(r'[ \t]*[\r\n]+[ \t]*', ' ', v).strip() if isinstance(v, str) else v for v in r]
        r[11] = r[11][:5]
        if (r[11] and r[11][:2] not in ('32', '33', '34')) or r[0] in seen: continue
        seen.add(r[0]); rows.append(r)
rows.sort(key=lambda r: (r[9].lower(), r[1].lower()))
os.makedirs('data', exist_ok=True)
k = 3; per = -(-len(rows) // k)
for i in range(k):
    with gzip.open(f'data/florida-places-{i+1}.csv.gz', 'wt', newline='', compresslevel=9) as fh:
        w = csv.writer(fh); w.writerow(HEAD); w.writerows(rows[i*per:(i+1)*per])
print('total', len(rows))
