"""AI summaries of the investigations, written once and checked by code.

    python -m app.summaries              write data/processed/summaries.json
    python -m app.summaries --only PSI-69

The language model sees one investigation's NASA record and the facts ingest
computed from its test table, and nothing else. Code then checks the answer:
every number must appear in that material, and every measurement must come
with a quote that really is in the record. A summary is shown only while the
material it was written from is unchanged.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date
from functools import lru_cache

from . import llm, store

PATH = store.PROCESSED / "summaries.json"
PROMPT_VERSION = 3
RECORD_FIELDS = ("objective", "approach", "hypothesis", "research_impacts", "hardware")
SHOWN = (
    ("o2_mole_fraction", "Oxygen in the atmosphere", 100, "%"),
    ("burner_o2_mole_fraction", "Oxygen fed through the burner", 100, "%"),
    ("pressure_kpa", "Pressure", 1, "kPa"),
    ("flow_cm_s", "Flow", 1, "cm/s"),
)

SYSTEM = """\
You summarise one NASA microgravity combustion investigation for a fire safety dashboard read by students, researchers and engineers.

Use only the material in the user message. It holds the NASA record and facts that code computed from the investigation's test table. Do not use anything you know from elsewhere. If the material does not say something, leave it out.

Return JSON only, with these keys:
- "one_line": one sentence of at most 25 words saying what the investigation burned or measured, and why.
- "summary": three sentences, at most 80 words in total. Say what was tested and how, what was varied or measured, and what the record says it means for fire safety.
- "measurements": up to 6 instruments or measured quantities that the NASA RECORD section says were used or recorded, such as cameras, radiometers, thermocouples, gas sensors, or the quantity they measured. Each is {"name": a short name, "quote": 3 to 15 consecutive words copied exactly from the NASA RECORD section that show it}. Do not quote the facts list or its column names. Use an empty list if the record names none.

Rules:
- Write plain sentences. No headings, no lists, no sales language.
- Avoid numbers. If you give one, copy it exactly as written in the material.
- Describe what was done in the record's own terms. Say a sample burned only if the record says it burned; smoke from overheated material, dust, and computer modelling are not burning.
- Do not mention any investigation the material does not name.
- Never say an investigation shows that something is safe."""

_NUMBER = re.compile(r"\d+(?:\.\d+)?")


def _range(found: dict, scale: float, unit: str) -> str:
    low, high = (f"{found[end] * scale:.3g}" for end in ("min", "max"))
    return f"{low} {unit}" if low == high else f"{low} to {high} {unit}"


def record_text(entry: dict) -> str:
    return "\n".join(f"{name.replace('_', ' ')}: {entry[name]}" for name in RECORD_FIELDS if entry.get(name))


def facts(entry: dict) -> list[str]:
    """What code computed from the test table, in the units the dashboard shows."""
    if not entry["tables"]:
        return ["This investigation has no test table in PSI."]
    kinds: dict[str, int] = {}
    varied: dict[str, int] = {}
    for table in entry["tables"]:
        for kind, count in table["rows"].items():
            kinds[kind] = kinds.get(kind, 0) + count
        for column in store.columns(entry["psi_id"], table["file_name"]):
            if column["distinct"] > 1:
                varied[column["name"]] = column["distinct"]
    fuels = sorted({r["fuel"] for r in store.rows() if r["psi_id"] == entry["psi_id"] and r["fuel"]})
    lines = [
        "Rows in the test table: " + ", ".join(f"{count} {kind}" for kind, count in kinds.items()),
        f"Fuel class: {entry['fuel_class']}",
        "Fuels or samples: " + (", ".join(fuels[:8]) + (f" and {len(fuels) - 8} more" if len(fuels) > 8 else "")),
    ]
    for field, label, scale, unit in SHOWN:
        found = entry["condition_ranges"].get(field)
        lines.append(f"{label}: {_range(found, scale, unit) if found else 'not stated'}")
    names = sorted(varied, key=varied.get)[:8]
    lines.append("Columns that varied between tests: " + (", ".join(names) or "none"))
    return lines


def material(psi_id: str) -> str:
    entry = store.investigations()[psi_id]
    return (
        f"INVESTIGATION: {entry['name']} ({psi_id}). {entry['title']}\n\n"
        f"NASA RECORD\n{record_text(entry)}\n\n"
        "FACTS COMPUTED FROM THE TEST TABLE\n" + "\n".join(f"- {line}" for line in facts(entry))
    )


def source_hash(text: str) -> str:
    return hashlib.sha256(f"{PROMPT_VERSION}\n{text}".encode()).hexdigest()[:16]


def _flat(text: str) -> str:
    return " ".join(text.lower().split())


def validate(answer: object, source: str, record: str) -> tuple[dict | None, str]:
    """The cleaned summary, or None and the rule the answer broke."""
    if not isinstance(answer, dict):
        return None, "the answer is not a JSON object"
    one_line, summary = answer.get("one_line"), answer.get("summary")
    if not isinstance(one_line, str) or not isinstance(summary, str) or not one_line.strip() or not summary.strip():
        return None, '"one_line" and "summary" must both be text'
    if len(one_line.split()) > 30:
        return None, '"one_line" is longer than 25 words'
    if len(summary.split()) > 95:
        return None, '"summary" is longer than 80 words'

    # Detection studies heat or sample material without burning it.
    if re.search(r"\bburn", one_line + " " + summary, re.I) and not re.search(r"burn|combust|ignit|flame", source, re.I):
        return None, "the material never says anything burned; say what it says was done"

    allowed = set(_NUMBER.findall(source))
    invented = sorted(set(_NUMBER.findall(one_line + " " + summary)) - allowed)
    if invented:
        return None, f"these numbers are not in the material: {', '.join(invented)}"

    measurements = []
    for item in answer.get("measurements") or []:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str) or not isinstance(item.get("quote"), str):
            continue
        quote = item["quote"].strip().strip('"')
        # Kept only when the quote really is in the NASA record.
        if len(quote.split()) >= 3 and _flat(quote) in _flat(record):
            measurements.append({"name": item["name"].strip(), "quote": quote})
    return {"one_line": one_line.strip(), "summary": summary.strip(), "measurements": measurements[:6]}, ""


def _parse(reply: str) -> object:
    start, end = reply.find("{"), reply.rfind("}")
    try:
        return json.loads(reply[start : end + 1])
    except ValueError:
        return None


def generate(psi_id: str) -> tuple[dict | None, str]:
    source = material(psi_id)
    record = record_text(store.investigations()[psi_id])
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": source}]
    error = ""
    for _ in range(2):  # one retry, telling the model which rule it broke
        reply = llm.chat(messages)
        summary, error = validate(_parse(reply), source, record)
        if summary:
            return {**summary, "source_hash": source_hash(source)}, ""
        messages += [{"role": "assistant", "content": reply},
                     {"role": "user", "content": f"That broke a rule: {error}. Answer again, JSON only."}]  # fmt: skip
    return None, error


@lru_cache(maxsize=1)
def _file() -> dict:
    return json.loads(PATH.read_text(encoding="utf-8")) if PATH.exists() else {"summaries": {}}


def model_name() -> str | None:
    return _file().get("model")


def get(psi_id: str) -> dict | None:
    """The stored summary, unless the material it was written from has changed."""
    stored = _file()["summaries"].get(psi_id)
    if stored is None or stored["source_hash"] != source_hash(material(psi_id)):
        return None
    return {key: stored[key] for key in ("one_line", "summary", "measurements")}


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m app.summaries", description="Write the AI summaries.")
    parser.add_argument("--only", action="append", metavar="PSI-ID")
    args = parser.parse_args()

    stored = _file()
    summaries, failed = dict(stored["summaries"]), dict(stored.get("failed", {}))
    wanted = args.only or [psi_id for psi_id, entry in store.investigations().items() if entry["in_scope"]]
    for psi_id in wanted:
        summary, error = generate(psi_id)
        failed.pop(psi_id, None)
        if summary:
            summaries[psi_id] = summary
            print(f"{psi_id}: ok, {len(summary['measurements'])} measurements")
        else:
            summaries.pop(psi_id, None)
            failed[psi_id] = error
            print(f"{psi_id}: REJECTED, {error}", file=sys.stderr)

    out = {
        "model": llm.settings()["LLM_MODEL"],
        "prompt_version": PROMPT_VERSION,
        "written_on": date.today().isoformat(),
        "summaries": summaries,
        "failed": failed,
    }
    PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
