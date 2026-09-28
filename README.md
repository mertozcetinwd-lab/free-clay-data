# Loam open places: every US state

15,482,799 US businesses and places, across all 50 states and DC, with name, category, phone, website, email, address and location. Free to use, including commercially. It's built from [Overture Maps Places](https://docs.overturemaps.org/guides/places/), release `2026-09-23.0`.

It's the free business database behind the Find leads page in Loam, an open-source Clay alternative. It works without Loam too: open a state in Excel, load it into a database, or search it with a script.

## What's inside

`data/<ST>/<st>-places-N.csv.gz`: one folder per state, gzipped CSV parts of up to about 40 MB each. Rows are sorted by city, then name. `data/manifest.json` lists every file with its size and row count. Rows per state are listed in [STATES.md](STATES.md).

| column | meaning |
|---|---|
| id | Overture's stable place id (GERS) |
| name | business name |
| category | Overture main category, e.g. `roofing`, `plumbing`, `hvac_service`, `dental_clinic` |
| basic_category | Overture's broader category |
| alt_categories | other categories, separated by `;` |
| phone, website, email | first listed of each |
| address, city, state, zip | street address as listed, city, 2-letter state, 5-digit zip |
| lat, lon | location |
| confidence | Overture's confidence that the place exists (0.5 to 1) |
| sources | where the record came from (meta, Microsoft, BrightQuery, Foursquare, AllThePlaces, …) |

Kept: places with a name, confidence of 0.5 or higher and operating status "open", inside the lower 48, Alaska or Hawaii. The state comes from the address. When the address has only a zip, the state is the one most rows with that zip's first three digits belong to. 21,042 places had neither and were left out.

## Licence and credit

The data is Overture Maps Places. Each record carries its source licence, and every licence in this data allows commercial use and redistribution:

- CDLA Permissive 2.0 ([text](https://cdla.dev/permissive-2-0/)): Overture, meta, Microsoft, BrightQuery, DAC, RenderSEO, PinMeTo
- Apache 2.0: Foursquare records
- CC0 1.0: AllThePlaces records

Credit it as: **"Data: Overture Maps Foundation, Overture Places (CDLA Permissive 2.0)"**. See [Overture's attribution guide](https://docs.overturemaps.org/attribution/).

Listings can be out of date or wrong. Check a business before you contact it, and follow the law on marketing messages where you are (CAN-SPAM, TCPA, state telemarketing rules).

## Rebuild it

`build/extract.py` reads the Overture release straight from its public S3 bucket. It downloads only the row groups that touch the US, using four processes, and it can resume after an interruption. `build/merge.py` then writes the per-state files and the manifest.

```
pip install pyarrow requests
python build/extract.py
python build/merge.py
```

Change `REL` in both scripts for a newer Overture release.

## Use it in Loam

In your Loam (free-clay) folder:

```
node dev/get-places.mjs
npx wrangler deploy
```

The first command downloads these files (about 1.2 GB, cached for next time) and builds the map tiles. The second publishes them with the app. Searches are then free and run instantly in the browser. Add `--states FL,GA` to the first command to load only some states.
