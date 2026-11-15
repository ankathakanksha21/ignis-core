# Data

| Folder | What it holds | Who writes it |
| --- | --- | --- |
| `raw/` | The PSI snapshot, exactly as served. | Only `scripts/fetch_psi.py`. Never edited by hand. |
| `processed/` | Cleaned tables and quality flags produced by ingest. | The ingest code (dashboard side). |
| `labels/` | Outcome labels mined from NASA reports, each with its source. | The modelling side (6.3). |

Both halves of the project read `raw/` from day one, so neither waits for the other. The formats of `processed/` and `labels/` are in `docs/CONTRACTS.md`.

## The snapshot in `raw/`

Fetched 14 Nov 2026 from the open PSI API by `scripts/fetch_psi.py`.

- `raw/manifest.json` lists every file with its source URL, sha256, encoding, row counts, DOI and licence.
- `raw/records/PSI-<n>.json` is one investigation record.
- `raw/tables/PSI-<n>/<file name>` is one experimental table, byte for byte.

Read tables with `ignis_ml.raw.read_raw_table("PSI-69")`. It handles the encoding, checks the sha256 and adds the `psi_id`, `file_name`, `row` key columns.

To refresh the snapshot, re-run the script and commit the result in a pull request of its own. Row numbers are citations, so a refresh that changes a table has to be reviewed.

### What the snapshot contains

26 investigation records and 25 table files. Leaving out the two investigations that are not combustion (PSI-108, PSI-181), that is 22 tables across 20 investigations, 2,009 test rows.

### Where it differs from the problem statement

The row counts of every table listed in the problem statement match. These are additional:

| Finding | Detail |
| --- | --- |
| SLICE was read | PSI-106, 12 rows, 2 columns. |
| ACME Flame Design has a second table | PSI-10 "Inverse Flame", 120 rows, beside "Normal Flame" (207). |
| ACME CFI-G has a second table | PSI-159 "Inverse Flames", 154 rows, beside "Normal Flames" (179). The file is 1,016 rows long because 861 of them are empty. |
| A ground study has a table | PSI-142 "Data Summary Table", 8 rows. They point to figures in publications and are not tests. |
| Saffire has 13 tests, not 21 | Saffire-I 2, Saffire-II 9, Saffire-III 2. The other 8 rows are flow-visualisation files and footnotes. |
| Several tables list test days, not tests | ACME BRE, CLD Flame, E-FIELD Flames, s-Flame, SLICE and FLEX-2 give one row per test day or per fuel, often with a count of flames ignited. |
| The search pages at 25 | The default search returns 25 of the 26 hits and drops PSI-101 (SAME-R). The script asks for `size=100`. |
| Licences | 25 records say CC0-1.0. PSI-10 (ACME Flame Design) has an empty licence field. |

### Things that will trip a reader

- **FLEX is not UTF-8.** `PSI-69_Experimental table_FLEX.csv` is Windows-1252. `pandas.read_csv` with default settings fails on it. The manifest records each file's encoding.
- **FLEX headers lost their subscripts and superscripts.** `O initial ambient composition` is O2, `N` is N2, and `CO initial ambient composition` is CO2 (the problem statement lists the FLEX gases as O2, N2, CO2, He). `Burning rate; mm` has lost the rest of its unit. Confirm both against the PSI-69 documents before relying on them.
- **Some headers carry stray spaces**, for example `' XO2 before test'` and `'XO2  after test'` in CFI-G. Headers are kept verbatim.
- **Cells are free text.** Saffire-II has `~ 21.5`, `80 W`, `Insignificant`, `n/a`; BASS-II has `none`. Nothing is numeric until ingest parses it.
- **All files use CRLF line endings**, and four start with a byte-order mark. `.gitattributes` stops Git from converting them.

### What is left out of the records

- The `added`, `removed` and `modified` fields, which are PSI's per-file change log and run to megabytes.
- Investigator `email`, `phone`, `fax` and `address`. Names and affiliations are kept.

The lists of PDF reports per investigation are not in the snapshot. They are needed only for report search (third tier) and can be added to the script then.

## The processed files in `processed/`

Built from `raw/` by ingest. From `backend/`:

```bash
python -m app.ingest
```

The files are committed so a change in ingest shows up as a data diff in review. A test fails if they fall behind the code.

| File | One line per | Holds |
| --- | --- | --- |
| `rows.csv` | raw row | Kind of row, fuel, fuel class, gravity, and the lowest and highest value of each condition. |
| `conditions.csv` | condition value | The value in contract units, how it was written, and the column, row and cell text it came from. |
| `quality_flags.csv` | suspicious cell | The check that fired and why. Format fixed by `docs/CONTRACTS.md`. |
| `investigations.json` | investigation | Record text, DOI, publications, and per table: column mapping, row counts, ranges, flag counts. |

How to read them:

- **Row kinds.** `test` is one test. `summary` stands for several tests (a test day, or one fuel's test matrix); `tests_in_row` gives the count where the table states it. `other` is not a test (a footnote, a continuation line, a file listing). Filter on `row_kind` before counting.
- **Listed values.** A cell such as `21; 26.5; 40` becomes three `listed` values. Only those three were tested; do not treat the row as covering everything from 21 to 40.
- **Approximate values.** A `~` in the cell, or "approx" in the header, sets `approximate`.
- **Two kinds of oxygen.** `o2_mole_fraction` is oxygen in the atmosphere around the flame. `burner_o2_mole_fraction` is oxygen fed through the burner into a fuel atmosphere (the inverse flames). The 85% oxygen in ACME CFI-G is the second kind and is not a cabin atmosphere.
- **Not stated.** A condition the table does not give has no line in `conditions.csv`. Nothing is filled in from general knowledge.
- **Flags.** A value that is physically impossible (pressure of 0, 3400% oxygen) is flagged and left out of `conditions.csv`. Every other flagged cell is kept. The thresholds are this project's judgement, not NASA's.

To add or change a column mapping, edit `backend/app/ingest/specs.py`, rebuild, and commit the code and the data together.

## Citing

PSI asks that each investigation be cited by its DOI. The DOI of every investigation is in `raw/manifest.json`.
