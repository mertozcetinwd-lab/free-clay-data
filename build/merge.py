"""Step 2 of 2: merge the per-worker CSVs into per-state files: one row per id, a state for rows that only have a
zip (learned from rows that have both), sorted by city then name, gzipped in parts under 50 MB."""
import csv, glob, gzip, json, os, collections, sys
csv.field_size_limit(10**7)
HEAD = ['id','name','category','basic_category','alt_categories','phone','website','email','address','city','state','zip','lat','lon','confidence','sources']
REL = '2026-09-23.0'
PART_BYTES = 40 * 10**6
states = sorted({os.path.basename(p)[:-4] for p in glob.glob('raw/*/*.csv')} - {'_unknown'})
zip3 = collections.defaultdict(collections.Counter)
for st in states:
    for p in glob.glob(f'raw/*/{st}.csv'):
        for r in csv.reader(open(p, newline='')):
            if r[11][:3].isdigit(): zip3[r[11][:3]][st] += 1
best = {z: c.most_common(1)[0][0] for z, c in zip3.items()}
extra = collections.defaultdict(list); dropped = 0
for p in glob.glob('raw/*/_unknown.csv'):
    for r in csv.reader(open(p, newline='')):
        st = best.get(r[11][:3]) if r[11][:3].isdigit() else None
        if st: r[10] = st; extra[st].append(r)
        else: dropped += 1
seen = set(); manifest = {'release': f'Overture {REL}', 'rows': 0, 'dropped_no_state': dropped, 'states': {}}
for st in states:
    rows = []
    for p in glob.glob(f'raw/*/{st}.csv'): rows += list(csv.reader(open(p, newline='')))
    rows += extra.get(st, [])
    uniq = []
    for r in rows:
        if r[0] in seen: continue
        seen.add(r[0]); uniq.append(r)
    uniq.sort(key=lambda r: (r[9].lower(), r[1].lower()))
    os.makedirs(f'data/{st}', exist_ok=True)
    files = []; i = 0; k = 0
    while i < len(uniq):
        k += 1; path = f'{st}/{st.lower()}-places-{k}.csv.gz'; full = f'data/{path}'
        raw = open(full, 'wb'); z = gzip.GzipFile(fileobj=raw, mode='wb', compresslevel=9, mtime=0)
        w = csv.writer(__import__('io').TextIOWrapper(z, newline='', write_through=True)); w.writerow(HEAD); n = 0
        while i < len(uniq) and raw.tell() < PART_BYTES:
            w.writerow(uniq[i]); i += 1; n += 1
        z.close(); raw.close()
        files.append({'path': path, 'bytes': os.path.getsize(full), 'rows': n})
    manifest['states'][st] = {'rows': len(uniq), 'files': files}; manifest['rows'] += len(uniq)
    print(st, len(uniq), len(files), 'parts', flush=True)
json.dump(manifest, open('data/manifest.json', 'w'), indent=1)
print('total', manifest['rows'], 'dropped (no state)', dropped)
