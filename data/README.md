# Data

| Folder | Holds | Written by |
| --- | --- | --- |
| `raw/` | PSI snapshot, exactly as served | `scripts/fetch_psi.py` only |
| `processed/` | Typed, checked tables | ingest: `cd backend && python -m app.ingest` |
| `labels/` | Labels mined from NASA reports, each with its source | the 6.3 work |

## raw

Fetched 14 Nov 2026 from the open PSI API: 26 investigation records and 25 table files. Without the two that are not combustion (PSI-108, PSI-181), that is 22 tables and 2,009 rows.

`raw/manifest.json` lists each file with its URL, sha256, encoding, DOI and licence. Read a table with `ignis_ml.raw.read_raw_table("PSI-69")`. It handles the encoding and adds the `psi_id`, `file_name`, `row` key.

Things that trip a reader:

- FLEX is Windows-1252, not UTF-8.
- FLEX headers lost their subscripts: `O` is O2, `N` is N2, `CO` is CO2.
- Cells are free text: `~ 21.5`, `80 W`, `n/a`, `21; 26.5; 40`.
- Some rows are not tests. Saffire has 13 tests in 21 rows; the rest are file listings and footnotes.
- Six tables list test days or test matrices, not single tests.
- CFI-G and Flame Design each have two tables, one for normal flames and one for inverse flames.
- PSI-10 has no licence field. The other 25 records are CC0-1.0.
- The records leave out PSI's file change log and the investigators' contact details.

## processed

| File | One line per | Holds |
| --- | --- | --- |
| `rows.csv` | raw row | row kind, fuel, fuel class, gravity, lowest and highest value of each condition |
| `conditions.csv` | condition value | value in contract units, how it was written, and the column, row and cell text it came from |
| `quality_flags.csv` | suspicious cell | the check that fired and why |
| `investigations.json` | investigation | record text, DOI, publications, column mapping, ranges |
| `summaries.json` | investigation | AI summary and the instruments named in the record, written by `python -m app.summaries` |

How to read them:

- `row_kind` is `test`, `summary` (several tests in one row) or `other` (not a test). Filter before counting.
- A cell such as `21; 26.5; 40` becomes three `listed` values. Only those three were tested.
- `o2_mole_fraction` is oxygen in the atmosphere. `burner_o2_mole_fraction` is oxygen fed through the burner of an inverse flame, which is not a cabin atmosphere.
- A condition the table does not state has no line. Nothing is filled in.
- An impossible value (pressure of 0, 3400% oxygen) is flagged and left out. Other flagged cells are kept. The thresholds are ours, not NASA's.

Cite each investigation by its DOI, listed in `raw/manifest.json`.
