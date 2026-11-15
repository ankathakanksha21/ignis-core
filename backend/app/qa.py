"""Question answering over NASA's records and the facts computed from its tables.

Code builds a list of evidence items, each with its source. For a question it
picks the most relevant items, the language model answers from those alone,
and code checks the answer: every sentence must cite an item, and every
number in a sentence must appear in the items it cites. A sentence that fails
is dropped, so nothing uncited or invented reaches the page.
"""

from __future__ import annotations

import json
import math
import re
from functools import lru_cache

from . import catalog, conditions, gaps, llm, store, summaries

TOP_ITEMS = 10
RECORD_FIELDS = ("objective", "approach", "hypothesis", "research_impacts")

SYSTEM = """\
You answer questions about NASA's microgravity combustion investigations for a fire safety dashboard.

Use only the numbered evidence in the user message. Do not use anything you know from elsewhere.

Return JSON only: {"sentences": [{"text": "...", "cites": [1, 4]}], "not_covered": null}
- Write at most 4 short, plain sentences. Each must be supported by the evidence items it cites, by number.
- Copy any number exactly as written in the evidence item you cite for it. Never calculate or estimate a number.
- If the evidence says something was not tested or does not exist, that is an answer: say so in a sentence and cite it.
- If the evidence does not answer the question, return {"sentences": [], "not_covered": "one sentence saying what is missing"}.
- If it answers only part, answer that part and say what is missing in "not_covered".
- Never say something is safe. Never mention an investigation the evidence does not name."""

_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_WORD = re.compile(r"[a-z0-9]+")
_STOP = set("a an and are as at be been by did do does for from had has have how in is it its of on or that the "
            "their there these this to was were what when where which who why will with any ever about".split())  # fmt: skip
_ENDINGS = ("ements", "ement", "ments", "ment", "ations", "ation", "ions", "ion", "ings", "ing", "ies", "ed", "es", "s", "e")


def _stem(word: str) -> str:
    """Crude on purpose: measure, measured and measurements all become measur."""
    for ending in _ENDINGS:
        if word.endswith(ending) and len(word) - len(ending) >= 4:
            return word[: -len(ending)]
    return word


def _tokens(text: str) -> list[str]:
    return [_stem(word) for word in _WORD.findall(text.lower()) if word not in _STOP]


# Words a question may use for what the records call something else.
_SAME = [{_stem(word) for word in group.split()} for group in (
    "extinguish extinguishment suppress suppression suppressant extinction",
    "detect detection detector smoke sensor",
    "flammability flammable ignite ignition burn",
    "moon lunar",
    "mars martian",
    "microgravity weightless space",
    "solid material fabric plastic",
    "droplet liquid",
    "highest maximum most largest",
    "lowest minimum least smallest",
)]  # fmt: skip
_FUEL_WORDS = {"solid": "solid solids material materials fabric plastic", "droplet": "droplet droplets liquid", "gas": "gas gases gaseous"}
_FUEL_NAMES = {"solid": "solid fuel", "droplet": "liquid droplets", "gas": "gas flames", "smoke": "smoke from heated material", "dust": "dust"}


def _chunks(text: str, size: int = 500) -> list[str]:
    """Whole sentences grouped into pieces of about `size` characters."""
    pieces, current = [], ""
    for sentence in re.split(r"(?<=[.!?])\s+", " ".join(text.split())):
        if current and len(current) + len(sentence) > size:
            pieces.append(current)
            current = ""
        current = f"{current} {sentence}".strip()
    return pieces + ([current] if current else [])


def _percent(fraction: float) -> str:
    return f"{fraction * 100:.3g}%"


@lru_cache(maxsize=1)
def evidence() -> list[dict]:
    """Everything the model may be shown. Each item says where it comes from."""
    items: list[dict] = []

    def add(text: str, source: str, psi_id: str | None = None, name: str | None = None) -> None:
        items.append({"text": text, "source": source, "psi_id": psi_id, "name": name})

    for psi_id, entry in store.investigations().items():
        if not entry["in_scope"]:
            continue
        name = entry["name"]
        about = name + (f" ({_FUEL_NAMES[entry['fuel_class']]})" if entry["fuel_class"] else " (ground study)")
        for field in RECORD_FIELDS:
            for piece in _chunks(entry.get(field) or ""):
                add(f"{about}, {field.replace('_', ' ')}: {piece}", f"NASA record, {field.replace('_', ' ')}", psi_id, name)
        pillar, why = catalog.PILLAR_OF[psi_id]
        add(f"{about}, {entry['title']}, test table facts: " + ". ".join(summaries.facts(entry))
            + f". Platform: {entry['platform'] or 'not stated'}. Hardware: {entry['hardware'] or 'not stated'}.",
            "computed from the test table", psi_id, name)  # fmt: skip
        add(f"{about} is grouped under {pillar}. {why}", "this project's grouping", psi_id, name)
        if psi_id in catalog.BRIEF_NOTES:
            add(f"{about}: {catalog.BRIEF_NOTES[psi_id]}", "challenge brief", psi_id, name)

    names = {psi_id: entry["name"] for psi_id, entry in store.investigations().items()}
    for pillar, description in catalog.PILLARS.items():
        members = [names[psi_id] for psi_id, (group, _) in catalog.PILLAR_OF.items() if group == pillar]
        add(f"The {len(members)} investigations grouped under {pillar} ({description}) are: {', '.join(members)}.", "this project's grouping")
    for fuel_class, label in _FUEL_NAMES.items():
        members = [e["name"] for e in store.investigations().values() if e["in_scope"] and e["fuel_class"] == fuel_class]
        add(f"The {len(members)} investigations that tested {label} are: {', '.join(members)}.", "computed across all test tables")
    for hardware, members in catalog.HARDWARE_GROUPS.items():
        add(f"These investigations share hardware, the {hardware}: {', '.join(names[m] for m in members)}.", "challenge brief")
    add("Every test in PSI's combustion tables ran in microgravity. PSI holds no combustion test at partial gravity, "
        "such as the Moon's 0.16 g or Mars's 0.38 g. Microgravity and normal-gravity results can only bound it.",
        "computed across all test tables")  # fmt: skip

    for fuel_class in gaps.MAPPED:
        stated = [(entry["condition_ranges"]["o2_mole_fraction"], entry["name"]) for entry in store.investigations().values()
                  if entry["in_scope"] and entry["fuel_class"] == fuel_class and "o2_mole_fraction" in entry["condition_ranges"]]  # fmt: skip
        low, high = min(stated, key=lambda pair: pair[0]["min"]), max(stated, key=lambda pair: pair[0]["max"])
        add(f"Across every {_FUEL_NAMES[fuel_class]} test in PSI, oxygen in the atmosphere runs from {_percent(low[0]['min'])} "
            f"(lowest, in {low[1]}) to {_percent(high[0]['max'])} (highest, in {high[1]}). Investigations with oxygen data: "
            f"{', '.join(name for _, name in stated)}. Oxygen fed through a burner is not counted here.",
            "computed across all test tables")  # fmt: skip

    # Habitats that share an atmosphere share one item, so they do not crowd out other evidence.
    shared: dict[tuple, list[str]] = {}
    for habitat_id, habitat in gaps.HABITATS.items():
        shared.setdefault((habitat["o2_mole_fraction"], habitat["pressure_kpa"], habitat["open_ended"]), []).append(habitat_id)
    for (oxygen, pressure, open_ended), members in shared.items():
        found = gaps.gap_map(members[0])
        closest = []
        for fuel in found["classes"]:
            near = fuel["nearest"]
            if near:
                stated = "pressure not stated" if near["pressure_kpa"] is None else f"{near['pressure_kpa']} kPa"
                closest.append(f"{_FUEL_NAMES[fuel['fuel_class']]}: {near['name']} row {near['row']} at {_percent(near['o2'])} oxygen, {stated}")
        who = ", ".join(
            f"{gaps.HABITATS[m]['label']} ({'gravity not stated' if gaps.HABITATS[m]['gravity_g'] is None else str(gaps.HABITATS[m]['gravity_g']) + ' g'})"
            for m in members
        )
        first = found["suggestions"][0] if found["suggestions"] else None
        add(f"Habitat atmosphere of {who}: {_percent(oxygen)} oxygen{' or more' if open_ended else ''}, "
            f"{pressure} kPa{' or less' if open_ended else ''}. Closest real test by fuel class: {'; '.join(closest)}."
            + (f" Untested nearest it: {_FUEL_NAMES[first['fuel_class']]} at {first['oxygen']} oxygen and {first['pressure']}." if first else ""),
            "computed across all test tables")  # fmt: skip
    return items


@lru_cache(maxsize=1)
def _index() -> tuple[list[list[str]], dict[str, float], float]:
    documents = [_tokens(item["text"]) for item in evidence()]
    seen: dict[str, int] = {}
    for words in documents:
        for word in set(words):
            seen[word] = seen.get(word, 0) + 1
    weight = {word: math.log(1 + (len(documents) - count + 0.5) / (count + 0.5)) for word, count in seen.items()}
    return documents, weight, sum(map(len, documents)) / len(documents)


def _rows_for(question: str) -> list[dict]:
    """One item listing the real test rows nearest any oxygen or pressure the question names."""
    query, asked = {}, []
    if match := re.search(r"(\d+(?:\.\d+)?)\s*(?:%|percent)\s*(?:o2|oxygen)", question, re.I):
        query["o2_mole_fraction"] = float(match[1]) / 100
        asked.append(f"{match[1]}% oxygen")
    if match := re.search(r"(\d+(?:\.\d+)?)\s*(kpa|psi)", question, re.I):
        query["pressure_kpa"] = float(match[1]) * (gaps.PSI_TO_KPA if match[2].lower() == "psi" else 1)
        asked.append(f"{match[1]} {match[2]}")
    if not query:
        return []
    words = set(_WORD.findall(question.lower()))
    fuel_class = next((name for name, group in _FUEL_WORDS.items() if words & set(group.split())), None)
    found = conditions.similar(query, fuel_class, limit=4)
    if not found:
        return []
    listed = []
    for row in found:
        values = row["values"]
        oxygen = f"{_percent(values['o2_mole_fraction']['min'])} oxygen" if "o2_mole_fraction" in values else "oxygen not stated"
        pressure = f"{values['pressure_kpa']['min']:.3g} kPa" if "pressure_kpa" in values else "pressure not stated"
        listed.append(f"{row['name']} row {row['row']} ({_FUEL_NAMES.get(row['fuel_class'], 'fuel')}, {row['fuel'] or 'fuel not stated'}): {oxygen}, {pressure}")
    kind = f"{_FUEL_NAMES[fuel_class]} " if fuel_class else ""
    return [{"text": f"The real {kind}test rows closest to {' and '.join(asked)}, nearest first: {'; '.join(listed)}. "
                     f"No {kind}test row is closer, though others may be about as close.",
             "source": "computed across all test tables", "psi_id": found[0]["psi_id"], "name": found[0]["name"]}]  # fmt: skip


def retrieve(question: str) -> list[dict]:
    """The evidence items most relevant to a question, best first."""
    documents, weight, average = _index()
    asked = set(_tokens(question))
    for group in _SAME:
        if asked & group:
            asked |= group
    named = {entry["psi_id"] for entry in store.investigations().values()
             if entry["acronym"] and re.search(rf"(?<![\w-]){re.escape(entry['acronym'].lower())}(?![\w-])", question.lower())}  # fmt: skip

    scored = []
    for item, words in zip(evidence(), documents):
        score = 0.0
        for word in asked:
            count = words.count(word)
            if count:
                score += weight[word] * count * 2.5 / (count + 1.5 * (0.25 + 0.75 * len(words) / average))
        if item["psi_id"] in named:
            score += 4  # the question names this investigation
        if score > 0:
            scored.append((score, item))
    scored.sort(key=lambda pair: -pair[0])
    rows = _rows_for(question)
    return rows + [item for _, item in scored[: TOP_ITEMS - len(rows)]]


def check(reply: object, items: list[dict]) -> tuple[list[dict], str | None]:
    """Keep only sentences that cite evidence and whose numbers are in it."""
    if not isinstance(reply, dict):
        return [], None
    kept = []
    for sentence in reply.get("sentences") or []:
        if not isinstance(sentence, dict) or not isinstance(sentence.get("text"), str):
            continue
        cites = [n for n in sentence.get("cites") or [] if isinstance(n, int) and 1 <= n <= len(items)]
        if not cites or not sentence["text"].strip():
            continue
        allowed = set(_NUMBER.findall(" ".join(items[n - 1]["text"] for n in cites)))
        if set(_NUMBER.findall(sentence["text"])) <= allowed:
            kept.append({"text": sentence["text"].strip(), "cites": sorted(set(cites))})
    missing = reply.get("not_covered")
    return kept[:4], missing.strip() if isinstance(missing, str) and missing.strip() else None


def ask(question: str) -> dict:
    items = retrieve(question)
    listed = "\n".join(f"[{n}] {item['text']}" for n, item in enumerate(items, 1))
    reply = llm.chat(
        [{"role": "system", "content": SYSTEM},
         {"role": "user", "content": f"EVIDENCE\n{listed}\n\nQUESTION\n{question}"}],
        max_tokens=500,
    )  # fmt: skip
    start, end = reply.find("{"), reply.rfind("}")
    try:
        parsed = json.loads(reply[start : end + 1])
    except ValueError:
        parsed = None
    sentences, missing = check(parsed, items)
    claimed = len(parsed.get("sentences") or []) if isinstance(parsed, dict) else 0
    if not sentences and not missing:
        missing = "The evidence found does not answer this question."
    return {
        "question": question,
        "sentences": sentences,
        "not_covered": missing,
        "dropped": claimed - len(sentences),  # sentences the checks refused
        "evidence": [{"n": n, **item} for n, item in enumerate(items, 1)],
        "model": llm.settings()["LLM_MODEL"],
    }
