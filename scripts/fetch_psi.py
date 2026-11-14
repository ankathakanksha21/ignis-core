#!/usr/bin/env python3
"""Snapshot the PSI combustion investigations into data/raw/.

Standard library only, so it runs on any machine with Python 3.10+ and no
install step:

    python scripts/fetch_psi.py                 # everything the search returns
    python scripts/fetch_psi.py --only PSI-69   # one investigation

What it writes:

    data/raw/records/<PSI id>.json              the investigation record
    data/raw/tables/<PSI id>/<file name>        each "Experimental table" file,
                                                byte for byte as PSI serves it
    data/raw/manifest.json                      what was fetched, from where,
                                                with sha256, DOI and licence

Nothing in data/raw/ is edited by hand. To refresh the snapshot, re-run this
script and commit the result in a pull request of its own.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://psi.nasa.gov/geode-py/ws"
# size=100 matters: the default page is 25 hits and the search returns 26,
# so without it one investigation is silently dropped.
SEARCH_URL = f"{BASE}/repo/search?term=combustion&source=psi&type=investigation&size=100"
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

# Investigator contact details are public on PSI but the dashboard has no use
# for them, so they are left out of the committed snapshot.
CONTACT_FIELDS_DROPPED = ("email", "phone", "fax", "address")

# These three record fields are PSI's per-file change log (every raw video and
# zip ever added or removed). They run to megabytes per record and say nothing
# about the investigation, so they are left out too.
RECORD_FIELDS_DROPPED = ("added", "removed", "modified")

# Tried in order. Most tables are UTF-8, some with a byte-order mark; FLEX
# (PSI-69) is Windows-1252 and does not decode as UTF-8.
ENCODINGS = ("utf-8-sig", "cp1252")


def http_get(url: str, *, timeout: int = 90, attempts: int = 4) -> bytes:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "psi-snapshot-script"})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
            last_error = error
            if attempt < attempts:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"GET failed after {attempts} attempts: {url}: {last_error}")


def record_url(psi_id: str) -> str:
    return f"{BASE}/repo/investigations/{psi_id}"


def table_url(psi_id: str, file_name: str) -> str:
    query = urllib.parse.urlencode({"source": "datamanager", "file": file_name})
    return f"{BASE}/studies/{psi_id}/download?{query}"


def describe_csv(content: bytes) -> dict:
    """Encoding and row counts of a table, so readers do not have to guess.

    A row is what a spreadsheet shows as one row. `rows` includes the header
    row; `data_rows` leaves out the header and any completely empty rows.
    """
    for encoding in ENCODINGS:
        try:
            text = content.decode(encoding)
        except UnicodeDecodeError:
            continue
        try:
            rows = list(csv.reader(io.StringIO(text, newline="")))
        except csv.Error:
            break
        blank = sum(1 for row in rows if not any(cell.strip() for cell in row))
        header_is_blank = bool(rows) and not any(cell.strip() for cell in rows[0])
        data_rows = max(len(rows) - 1, 0) - (blank - (1 if header_is_blank else 0))
        return {"encoding": encoding, "rows": len(rows), "blank_rows": blank, "data_rows": data_rows}
    return {"encoding": None, "rows": None, "blank_rows": None, "data_rows": None}


def trim_record(record: dict) -> dict:
    for field in RECORD_FIELDS_DROPPED:
        record.pop(field, None)
    for contact in record.get("contacts") or []:
        for field in CONTACT_FIELDS_DROPPED:
            contact.pop(field, None)
    return record


def search_ids() -> list[str]:
    payload = json.loads(http_get(SEARCH_URL))
    hits = payload["hits"]["hits"]
    total = payload["hits"]["total"]
    if len(hits) != total:
        raise RuntimeError(f"search returned {len(hits)} of {total} hits; raise size= in SEARCH_URL")
    return sorted((hit["_source"]["Accession"] for hit in hits), key=lambda a: int(a.split("-")[1]))


def fetch_investigation(psi_id: str) -> dict:
    record = trim_record(json.loads(http_get(record_url(psi_id))))

    records_dir = RAW_DIR / "records"
    records_dir.mkdir(parents=True, exist_ok=True)
    record_path = records_dir / f"{psi_id}.json"
    record_path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    entry = {
        "psi_id": psi_id,
        "acronym": record.get("investigationAcronym") or None,
        "title": record.get("title") or None,
        "doi": record.get("doi") or None,
        "license": record.get("licenseIdentifier") or None,
        "project_type": record.get("projectType") or None,
        "record_modified": record.get("modifiedDate") or None,
        "record_url": record_url(psi_id),
        "record_file": record_path.relative_to(RAW_DIR.parent.parent).as_posix(),
        "tables": [],
        "errors": [],
    }

    for listed in record.get("experimentalTable") or []:
        file_name = listed.get("file_name")
        if not file_name or listed.get("restricted") or listed.get("visible") is False:
            continue
        url = table_url(psi_id, file_name)
        try:
            content = http_get(url)
        except RuntimeError as error:
            entry["errors"].append({"file_name": file_name, "error": str(error)})
            continue
        table_dir = RAW_DIR / "tables" / psi_id
        table_dir.mkdir(parents=True, exist_ok=True)
        table_path = table_dir / file_name
        table_path.write_bytes(content)
        entry["tables"].append(
            {
                "file_name": file_name,
                "path": table_path.relative_to(RAW_DIR.parent.parent).as_posix(),
                "source_url": url,
                "bytes": len(content),
                "listed_bytes": listed.get("file_size"),
                "sha256": hashlib.sha256(content).hexdigest(),
                **describe_csv(content),
            }
        )
    return entry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--only", action="append", metavar="PSI-ID", help="fetch only this id (repeatable)")
    args = parser.parse_args()

    manifest_path = RAW_DIR / "manifest.json"
    existing = {}
    if args.only and manifest_path.exists():
        existing = {e["psi_id"]: e for e in json.loads(manifest_path.read_text(encoding="utf-8"))["investigations"]}

    ids = args.only or search_ids()
    failed = False
    for psi_id in ids:
        try:
            entry = fetch_investigation(psi_id)
        except RuntimeError as error:
            print(f"{psi_id}: FAILED {error}", file=sys.stderr)
            failed = True
            continue
        existing[psi_id] = entry
        tables = ", ".join(f"{t['file_name']} ({t['data_rows']} data rows)" for t in entry["tables"]) or "no table"
        problems = f"  ERRORS: {len(entry['errors'])}" if entry["errors"] else ""
        failed = failed or bool(entry["errors"])
        print(f"{psi_id} {entry['acronym'] or ''}: {tables}{problems}")

    manifest = {
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "search_url": SEARCH_URL,
        "record_fields_dropped": list(RECORD_FIELDS_DROPPED),
        "contact_fields_dropped": list(CONTACT_FIELDS_DROPPED),
        "investigations": sorted(existing.values(), key=lambda e: int(e["psi_id"].split("-")[1])),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {manifest_path}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
