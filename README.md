# Loam open places: Florida

1,178,144 Florida businesses and places with name, category, phone, website, email, address and location. Free to use, including commercially. It's built from [Overture Maps Places](https://docs.overturemaps.org/guides/places/), release `2026-09-23.0`.

It's the free business database behind the Find leads page in Loam, an open-source Clay alternative. It works without Loam too: open it in Excel, load it into a database, or search it with a script.

## What's inside

`data/florida-places-1.csv.gz`, `-2`, `-3`: gzipped CSV, about 30 MB each, 286 MB unzipped. Rows are sorted by city, then name.

| column | meaning |
|---|---|
| id | Overture's stable place id (GERS) |
| name | business name |
| category | Overture main category, e.g. `roofing`, `plumbing`, `hvac_service`, `dental_clinic` |
| basic_category | Overture's broader category |
| alt_categories | other categories, separated by `;` |
| phone, website, email | first listed of each (89% have a phone, 79% a website, 31% an email) |
| address, city, state, zip | street address as listed, city, `FL`, 5-digit zip |
| lat, lon | location |
| confidence | Overture's confidence that the place exists (0.5 to 1) |
| sources | where the record came from (meta, Microsoft, BrightQuery, Foursquare, AllThePlaces, …) |

Kept: places with a name, confidence of 0.5 or higher, operating status "open", in Florida (region FL, zip 32/33/34 when present).

## Licence and credit

The data is Overture Maps Places. Each record carries its source licence, and every licence in this slice allows commercial use and redistribution:

- CDLA Permissive 2.0 ([text](https://cdla.dev/permissive-2-0/)): Overture, meta, Microsoft, BrightQuery, DAC, RenderSEO, PinMeTo
- Apache 2.0: Foursquare records
- CC0 1.0: AllThePlaces records

Credit it as: **"Data: Overture Maps Foundation, Overture Places (CDLA Permissive 2.0)"**. See [Overture's attribution guide](https://docs.overturemaps.org/attribution/).

Listings can be out of date or wrong. Check a business before you contact it, and follow the law on marketing messages where you are (CAN-SPAM, TCPA, Florida's telemarketing rules).

## Rebuild it, or make another state

`build/extract.py` reads the Overture release straight from its public S3 bucket. It downloads only the parts of the files that touch the chosen bounding box (190 MB of the ~11 GB release for Florida). Change the box and the region filter to make another state.

```
pip install pyarrow requests
python build/extract.py
```

## Use it in Loam

In your Loam (free-clay) folder:

```
node dev/get-places.mjs
npx wrangler deploy
```

The first command downloads these files and builds 1,483 map tiles. The second publishes them with the app. Searches are then free and run instantly in the browser.
