"""Step 1 of 2: pull every US place from Overture Maps Places into per-worker, per-state CSVs in raw/.

Reads straight from Overture's public S3 bucket with HTTP range requests, and only the row groups
whose bounding box touches the lower 48, Alaska or Hawaii (the files are spatially sorted). Four
processes; resumable: finished row groups are listed in done.txt and skipped on a re-run.
Then run build/merge.py.   pip install pyarrow requests   python build/extract.py
"""
import re, os, sys, csv, requests, pyarrow.parquet as pq
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rangefile import RangeFile
REL = '2026-09-23.0'
B = 'https://overturemaps-us-west-2.s3.us-west-2.amazonaws.com/'
BOXES = [(-125.0, -66.9, 24.3, 49.5), (-180.0, -129.0, 51.0, 71.5), (-161.0, -154.6, 18.8, 22.4)]   # lower 48, Alaska, Hawaii
STATES = {'AL':'Alabama','AK':'Alaska','AZ':'Arizona','AR':'Arkansas','CA':'California','CO':'Colorado','CT':'Connecticut','DE':'Delaware','DC':'District of Columbia',
 'FL':'Florida','GA':'Georgia','HI':'Hawaii','ID':'Idaho','IL':'Illinois','IN':'Indiana','IA':'Iowa','KS':'Kansas','KY':'Kentucky','LA':'Louisiana','ME':'Maine',
 'MD':'Maryland','MA':'Massachusetts','MI':'Michigan','MN':'Minnesota','MS':'Mississippi','MO':'Missouri','MT':'Montana','NE':'Nebraska','NV':'Nevada',
 'NH':'New Hampshire','NJ':'New Jersey','NM':'New Mexico','NY':'New York','NC':'North Carolina','ND':'North Dakota','OH':'Ohio','OK':'Oklahoma','OR':'Oregon',
 'PA':'Pennsylvania','RI':'Rhode Island','SC':'South Carolina','SD':'South Dakota','TN':'Tennessee','TX':'Texas','UT':'Utah','VT':'Vermont','VA':'Virginia',
 'WA':'Washington','WV':'West Virginia','WI':'Wisconsin','WY':'Wyoming'}
BYNAME = {v.upper(): k for k, v in STATES.items()}
COLS = ['id','confidence','websites','emails','phones','addresses','names','sources','operating_status','basic_category','taxonomy','bbox']
keys = re.findall(r'<Key>(.*?)</Key>', requests.get(B+f'?list-type=2&prefix=release/{REL}/theme%3Dplaces/type%3Dplace/').text)

def state_of(region):
    r = (region or '').strip().upper()
    if r.startswith('US-'): r = r[3:]
    return r if r in STATES else BYNAME.get(r)
def stats(rg, name):
    for i in range(rg.num_columns):
        c = rg.column(i)
        if c.path_in_schema == name: return c.statistics
def first(v): return v[0] if v else ''
clean = lambda v: re.sub(r'[ \t]*[\r\n]+[ \t]*', ' ', v).strip() if isinstance(v, str) else v

import pyarrow.compute as pc
from multiprocessing import Pool

def plan():
    """Every (file, row group) whose bbox touches the US, from each file's footer."""
    tasks = []
    for key in keys:
        md = pq.ParquetFile(RangeFile(B + key)).metadata
        for g in range(md.num_row_groups):
            rg = md.row_group(g)
            x0, x1, y0, y1 = stats(rg,'bbox.xmin').min, stats(rg,'bbox.xmax').max, stats(rg,'bbox.ymin').min, stats(rg,'bbox.ymax').max
            if any(x1 >= w and x0 <= e and y1 >= s and y0 <= n for w, e, s, n in BOXES): tasks.append((key, g))
    return tasks

_files = {}; _pf = {}
def work(task):
    for attempt in range(4):
        try: return task, _work(task)
        except Exception as e:
            _pf.pop(task[0], None)
            if attempt == 3: print('FAILED', task, e, flush=True); return task, None
            import time; time.sleep(5 * (attempt + 1))

def _work(task):
    key, g = task
    if key not in _pf: _pf[key] = pq.ParquetFile(RangeFile(B + key))
    t = _pf[key].read_row_group(g, columns=COLS)
    bb = t.column('bbox')
    x = pc.struct_field(bb, 'xmin'); y = pc.struct_field(bb, 'ymin')
    m = None
    for w, e, s, n in BOXES:   # cheap vector filter first; only survivors become Python objects
        k = pc.and_(pc.and_(pc.greater_equal(x, w), pc.less_equal(x, e)), pc.and_(pc.greater_equal(y, s), pc.less_equal(y, n)))
        m = k if m is None else pc.or_(m, k)
    m = pc.and_(m, pc.greater_equal(t.column('confidence'), 0.5))
    t = t.filter(m); n = 0; os.makedirs(f'raw/{os.getpid()}', exist_ok=True)
    for r in t.to_pylist():
        b = r['bbox']; lon, lat = b['xmin'], b['ymin']
        a = first(r['addresses']) or {}
        if (a.get('country') or 'US') != 'US': continue
        name = (r['names'] or {}).get('primary')
        if not name: continue
        if r['operating_status'] and r['operating_status'] != 'open': continue
        tx = r['taxonomy'] or {}
        row = [r['id'], name, tx.get('primary') or r['basic_category'] or '', r['basic_category'] or '', ';'.join(tx.get('alternates') or []),
               first(r['phones']), first(r['websites']), first(r['emails']), a.get('freeform') or '', a.get('locality') or '',
               state_of(a.get('region')) or '', (a.get('postcode') or '')[:5], round(lat, 6), round(lon, 6), round(r['confidence'], 3),
               ';'.join(sorted({s['dataset'] for s in (r['sources'] or []) if s.get('dataset')}))]
        st = row[10] or '_unknown'
        if st not in _files: _files[st] = open(f'raw/{os.getpid()}/{st}.csv', 'a', newline='')
        csv.writer(_files[st]).writerow([clean(v) for v in row]); n += 1
    for fh in _files.values(): fh.flush()
    return n

if __name__ == '__main__':
    tasks = plan(); print('row groups', len(tasks), flush=True)
    finished = set(open('done.txt').read().split()) if os.path.exists('done.txt') else set()
    tasks = [t for t in tasks if f'{t[0][-60:]}#{t[1]}' not in finished]; print('to do', len(tasks), flush=True)
    done = 0; rows = 0; log = open('done.txt', 'a')
    with Pool(4) as pool:
        for task, n in pool.imap_unordered(work, tasks, chunksize=2):
            done += 1
            if n is None: continue
            rows += n; log.write(f'{task[0][-60:]}#{task[1]}\n'); log.flush()
            if done % 25 == 0: print(done, '/', len(tasks), 'groups', rows, 'rows', flush=True)
    print('done', rows, flush=True)
