"""The voice guide: a short spoken explanation of one page, which the listener can interrupt.

Code builds the facts for the page from NASA's tables and records. The
language model turns them into a short script, and code checks that every
number in the script is one of the facts. If the model is not set up or its
script fails the check, code writes a plainer script from the facts itself.

ElevenLabs speaks the script as the first message of a conversation, so the
listener can cut in and ask questions. The agent is given the same facts and
told to answer from them alone. Its spoken answers cannot be checked before
they are heard, so the page checks their numbers as the transcript arrives.

    python -m app.voice        creates the ElevenLabs agent, or updates its prompt
                               once ELEVENLABS_AGENT_ID is in .env (run from backend/)
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from functools import lru_cache

from ignis_ml import api as models
from ignis_ml import raw
from ignis_ml.contract import PredictRequest, SimulateRequest

from . import catalog, conditions, gaps, llm, ranking, store, summaries

ELEVENLABS = "https://api.elevenlabs.io/v1/convai"
MAX_FACT_CHARS = 6000  # what is handed to the agent; the page shows the same list
_NUMBER = re.compile(r"\d+(?:\.\d+)?")

SCRIPT_SYSTEM = """\
You explain one page of a NASA fire safety dashboard out loud to someone new to the subject.

Use only the facts in the user message. Do not use anything you know from elsewhere.

Return JSON only: {"script": "...", "highlights": ["...", "...", "..."]}
- "script": 4 to 6 short sentences to be read aloud, at most 110 words. Say what the page shows, then the two or three things that matter most, in plain words. End by inviting a question.
- "highlights": exactly 3 short phrases, each at most 12 words, each restating one key fact from the script.

Rules:
- Copy any number exactly as written in the facts. Never calculate, round or estimate a number.
- No lists, no headings, no symbols that cannot be read aloud.
- A prediction or a simulation is never a measurement. Say which it is.
- A table row is not always one test. Use the "Number of tests" fact for how many tests there were.
- Do not mention any investigation the facts do not name.
- Never say that something is safe."""

AGENT_PROMPT = """\
You are the voice guide of Flame in Freefall, a dashboard about NASA's microgravity combustion experiments and fire safety in space. You have just read the listener a short explanation of the page they are looking at. Now answer their questions about it.

THE PAGE
{{page}}

THE FACTS
These were computed by code from NASA's tables and records. They are the only things you know.
{{facts}}

RULES
- Answer in one to three short sentences, in plain spoken words.
- Use only the facts above. Copy any number exactly as it appears there. Never calculate, round or estimate a number.
- Write every number in digits, such as 274 and 34%, never in words. The page checks your digits against the facts.
- If the facts do not answer the question, say "That is not in the data on this page" and suggest the Ask page, which searches all the records.
- A prediction or a simulation is never a measurement. Say which it is.
- NASA has no combustion tests in partial gravity, so Moon and Mars gravity are always untested.
- Never say that something is safe.
- The listener may cut in at any moment. When they do, drop what you were saying and answer what they asked. Never go back to finish the explanation unless they ask you to.
- If they only say stop, wait, or that they have a question, reply with just "Go ahead." and listen."""

NOT_COVERED = "That is not in the data on this page. The Ask page searches all the records."


def _env(name: str) -> str:
    """A setting from the environment or the git-ignored .env, or '' when it is not set."""
    found = os.environ.get(name, "")
    env_file = raw.repo_root() / ".env"
    if not found and env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            if key.strip() == name:
                found = value.strip()
    return found


def _points(score: float) -> int:
    return round(score * 100)


def _percent(fraction: float) -> str:
    return f"{fraction * 100:.3g}%"


def _shorten(text: str, limit: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + " (cut short)"


def _entry(psi_id: str) -> dict:
    entry = store.investigations().get(psi_id)
    if entry is None or not entry["in_scope"]:
        raise KeyError(f"{psi_id} is not one of the combustion investigations")
    return entry


def _about(entry: dict, record_chars: int) -> list[str]:
    psi_id = entry["psi_id"]
    pillar, why = catalog.PILLAR_OF[psi_id]
    gravity = "a ground study with no flight tests" if entry["gravity_g"] is None else "microgravity"
    lines = [
        f"{entry['name']} ({psi_id}) is titled: {entry['title']}",
        f"Pillar, which is this project's grouping and not NASA's: {pillar}. {why}",
        f"Gravity of the tests: {gravity}",
    ]
    counted = sum(table["tests_counted"] for table in entry["tables"])
    summary_rows = sum(table["rows"].get("summary", 0) for table in entry["tables"])
    if counted and summary_rows:
        # A summary row stands for several tests, so the row count is not the test count.
        lines.append(f"Number of tests: {counted}, reported in {summary_rows} summary rows that each cover several tests")
    elif counted:
        lines.append(f"Number of tests: {counted}")
    lines += [
        *summaries.facts(entry),
        f"Table cells flagged by this project's checks: {sum(1 for flag in store.flags() if flag['psi_id'] == psi_id)}",
    ]
    for field in ("objective", "research_impacts"):
        if entry.get(field):
            lines.append(f"NASA record, {field.replace('_', ' ')}: {_shorten(entry[field], record_chars)}")
    return lines


def _investigation(params: dict) -> tuple[str, list[str]]:
    entry = _entry(str(params["psi_id"]))
    return f"The page for the investigation {entry['name']}", _about(entry, 500)


def _compare(params: dict) -> tuple[str, list[str]]:
    ids = [psi_id for psi_id in str(params["ids"]).split(",") if psi_id][:3]
    entries = [_entry(psi_id) for psi_id in ids]
    lines = [f"{entry['name']}: {line}" for entry in entries for line in _about(entry, 220)[1:]]
    return "A side by side comparison of " + ", ".join(entry["name"] for entry in entries), lines


def _profile(params: dict) -> tuple[dict, dict]:
    mission = ranking.MISSIONS[str(params["mission"])]
    profile = {key: mission[key] for key in ("o2_mole_fraction", "pressure_kpa", "gravity_g")}
    for key in (*profile, "flow_cm_s"):
        if params.get(key) is not None:
            profile[key] = float(params[key])
    return mission, profile


def _rank(params: dict) -> tuple[str, list[str]]:
    mission, profile = _profile(params)
    fuel, pillar = params.get("fuel_class") or None, params.get("pillar") or "all"
    results = [
        result for result in ranking.rank(profile, ranking.DEFAULT_WEIGHTS)
        if (not fuel or result["fuel_class"] == fuel) and (pillar == "all" or result["pillar"] == pillar)
    ]  # fmt: skip
    habitat = (f"{_percent(profile['o2_mole_fraction'])} oxygen, {profile['pressure_kpa']:.3g} kPa, "
               f"{profile['gravity_g']:g} g")  # fmt: skip
    lines = [
        f"The habitat being ranked for: {mission['label']}, {habitat}"
        + (f", {profile['flow_cm_s']:g} cm/s flow" if "flow_cm_s" in profile else ""),
        "The score is this project's, not a NASA rating. It averages oxygen match, pressure match, fuel type, "
        "gravity and pillar, each from 0 to 100. Oxygen match and fuel type count most.",
        f"Experiments in the list: {len(results)}" + (f", {fuel} fuels only" if fuel else ""),
    ]
    for place, result in enumerate(results[:5], start=1):
        parts = ", ".join(
            f"{factor['label'].lower()} {'not stated' if factor['unknown'] else _points(factor['score'])}"
            for factor in result["factors"]
        )
        lines.append(f"Rank {place}: {result['name']} ({result['fuel_class'] or 'no fuel class'}), "
                     f"score {_points(result['score'])} of 100. Its parts: {parts}")  # fmt: skip
    if results:
        lines += [f"Why {results[0]['name']} is first, {factor['label'].lower()}: {factor['detail']}"
                  for factor in results[0]["factors"]]  # fmt: skip
    if profile["gravity_g"] > 0:
        lines.append("NASA has no combustion tests in partial gravity, so every microgravity result only bounds this habitat.")
    return f"The ranking of experiments for a {mission['label'].lower()}", lines


def _gaps(params: dict) -> tuple[str, list[str]]:
    found = gaps.gap_map(str(params["habitat"]))
    habitat = found["habitat"]
    names = {"solid": "Solid fuels", "droplet": "Liquid droplets", "gas": "Gas flames"}
    lines = [
        f"The habitat: {habitat['label']}, {_percent(habitat['o2_mole_fraction'])} oxygen"
        f"{' or more' if habitat['open_ended'] else ''}, {habitat['pressure_kpa']} kPa{' or less' if habitat['open_ended'] else ''}",
        found["gravity_note"],
        "The map counts NASA's tests in cells of oxygen against pressure, separately for solid fuels, liquid droplets "
        "and gas flames. An empty cell has never been tested.",
    ]
    for fuel in found["classes"]:
        name, nearest = names[fuel["fuel_class"]], fuel["nearest"]
        lines.append(f"{name}: tests fall in {len(fuel['cells'])} cells of the map")
        if nearest:
            pressure = "pressure not stated" if nearest["pressure_kpa"] is None else f"{nearest['pressure_kpa']} kPa"
            lines.append(f"{name}, closest real test to this habitat: {_percent(nearest['o2'])} oxygen, {pressure}, "
                         f"in {nearest['name']} row {nearest['row']}")  # fmt: skip
    for place, s in enumerate(found["suggestions"][:3], start=1):
        tested = "never tested at this oxygen" if s["oxygen_never_tested"] else "tested at this oxygen but not this pressure"
        lines.append(f"Suggested experiment {place}: {names[s['fuel_class']].lower()} at {s['oxygen']} oxygen and "
                     f"{s['pressure']}, {tested}. Score {_points(s['score'])}, which is closeness "
                     f"{_points(s['closeness'])} times fuel relevance {_points(s['relevance'])}. {s['fuel_why']}")  # fmt: skip
    if not found["suggestions"]:
        lines.append("No empty cell lies near this habitat.")
    return f"The gap map for a {habitat['label'].lower()}", lines


def _nearest_lines(tests: list, limit: int = 3) -> list[str]:
    return [
        f"Nearest real test {place}: {test.psi_id} row {test.row}. "
        + ", ".join(f"{name.strip()} {value}" for name, value in list(test.values.items())[:9] if value.strip())
        for place, test in enumerate(tests[:limit], start=1)
    ]


def _prediction(params: dict) -> tuple[str, list[str]]:
    request = PredictRequest(model_id=params["model_id"], inputs=params["inputs"])
    card = next(card for card in models.model_cards() if card.model_id == request.model_id)
    answer = models.predict(request)
    lines = [
        f"The model: {card.title}. It gives {card.target}" + (f" in {card.target_unit}" if card.target_unit else ""),
        "What was asked: " + ", ".join(f"{name} {value}" for name, value in request.inputs.items()),
    ]
    found = answer.prediction
    if answer.status == "withheld":
        lines.append("The model gave no answer, because these conditions are outside what NASA tested.")
    elif answer.status != "ok":
        lines.append(f"The model gave no answer. Status: {answer.status.replace('_', ' ')}")
    elif found and found.value is not None:
        spread = f", likely between {found.low:.3g} and {found.high:.3g}" if found.low is not None and found.high is not None else ""
        lines.append(f"This is a model prediction, not a measurement: {found.value:.3g} {found.unit or ''}{spread}")
    elif found and found.label is not None:
        chances = ", ".join(f"{name} {_points(chance)}%" for name, chance in (found.class_probabilities or {}).items())
        lines.append(f"This is a model prediction, not a measurement: {found.label}" + (f". Chances: {chances}" if chances else ""))
    else:
        lines.append("This model predicts nothing. It finds the real tests closest to what was asked.")
    for violation in answer.out_of_range:
        if violation.tested_min is not None and violation.tested_max is not None:
            tested = f"NASA tested {violation.tested_min:.4g} to {violation.tested_max:.4g}"
        else:
            tested = "NASA tested " + ", ".join(violation.categories or ["no such value"])
        lines.append(f"Outside the tested range: {violation.feature} {violation.value}. {tested}")
    if answer.message:
        lines.append(f"The model's own note: {answer.message}")
    lines += _nearest_lines(answer.nearest_tests)
    for metric in card.evaluation[:2]:
        baseline = f", against {metric.baseline_value:.3g} for {metric.baseline_name}" if metric.baseline_value is not None else ""
        lines.append(f"How the model scored on tests held back from it, {metric.name}: {metric.value:.3g}{baseline}")
    return f"A result from the model {card.title}", lines


def _lab(params: dict) -> tuple[str, list[str]]:
    request = SimulateRequest(**params["request"])
    answer = models.simulate(request)
    asked = [f"oxygen {_percent(request.o2_mole_fraction)}", f"pressure {request.pressure_kpa:g} kPa"]
    asked += [f"carbon dioxide {_percent(request.co2_mole_fraction)}"] if request.co2_mole_fraction else []
    asked += [f"helium {_percent(request.he_mole_fraction)}"] if request.he_mole_fraction else []
    asked += [f"droplet diameter {request.droplet_diameter_mm:g} mm"] if request.droplet_diameter_mm else []
    lines = [f"A simulated {request.fuel} droplet burning in microgravity: " + ", ".join(asked)]
    state = answer.state
    if answer.status != "ok" or state is None:
        lines.append("The engine did not simulate this" + (f": {answer.message}" if answer.message else "."))
    else:
        lines.append("This is simulated, not measured. It is fitted to NASA's FLEX droplet tests.")
        if state.burning_rate_mm2_s is not None:
            lines.append(f"Simulated burning rate: {state.burning_rate_mm2_s:.3g} square millimetres per second")
        if state.burn_time_s is not None:
            lines.append(f"Simulated time the flame lasts: {state.burn_time_s:.3g} seconds")
        if state.d2_curve:
            lines.append(f"Simulated droplet diameter left when the flame goes out: {state.d2_curve[-1].d2_mm2 ** 0.5:.3g} mm")
        if answer.message:
            lines.append(f"The engine's own note: {answer.message}")
        lines += [f"The simulation assumes: {text}" for text in answer.assumptions[:3]]
    lines += _nearest_lines(answer.nearest_tests)
    return "The droplet lab, a simulated burning droplet", lines


def _similar(params: dict) -> tuple[str, list[str]]:
    query = {field: float(params[field]) for field in ranking.TOLERANCE if params.get(field) is not None}
    if not query:
        raise ValueError("Give at least one of oxygen, pressure or flow")
    fuel = params.get("fuel_class") or None
    units = {"o2_mole_fraction": ("oxygen", 100, "%"), "pressure_kpa": ("pressure", 1, " kPa"), "flow_cm_s": ("flow", 1, " cm/s")}
    asked = ", ".join(f"{units[field][0]} {value * units[field][1]:.3g}{units[field][2]}" for field, value in query.items())
    rows = conditions.similar(query, fuel)
    lines = [f"The conditions searched for: {asked}" + (f", {fuel} fuels only" if fuel else "")]
    if not rows or rows[0]["distance"] > 1 or rows[0]["not_stated"]:
        lines.append("No real test is close to these conditions. The nearest rows are listed so the distance can be seen.")
    for place, row in enumerate(rows[:5], start=1):
        stated = ", ".join(
            f"{units[field][0]} {found['min'] * units[field][1]:.3g}{units[field][2]}"
            for field, found in row["values"].items() if found and field in units
        )  # fmt: skip
        lines.append(f"Closest test {place}: {row['name']} row {row['row']}, fuel {row['fuel'] or 'not stated'}, {stated}. "
                     f"Closeness {round(max(0.0, 1 - row['distance']) * 100)} of 100")  # fmt: skip
    return "A search for the real tests closest to a set of conditions", lines


KINDS = {
    "investigation": _investigation,
    "compare": _compare,
    "rank": _rank,
    "gaps": _gaps,
    "prediction": _prediction,
    "lab": _lab,
    "similar": _similar,
}


def check_script(answer: object, facts: list[str]) -> tuple[dict | None, str]:
    """The cleaned script and highlights, or None and the rule the answer broke."""
    if not isinstance(answer, dict) or not isinstance(answer.get("script"), str) or not answer["script"].strip():
        return None, 'the answer must be a JSON object with a "script"'
    script = " ".join(answer["script"].split())
    highlights = [" ".join(item.split()) for item in answer.get("highlights") or [] if isinstance(item, str) and item.strip()]
    if len(script.split()) > 130:
        return None, '"script" is longer than 110 words'
    if not 1 <= len(highlights) <= 4 or any(len(item.split()) > 16 for item in highlights):
        return None, '"highlights" must be 3 phrases of at most 12 words'
    spoken = script + " " + " ".join(highlights)
    invented = sorted(set(_NUMBER.findall(spoken)) - set(_NUMBER.findall(" ".join(facts))))
    if invented:
        return None, f"these numbers are not in the facts: {', '.join(invented)}"
    if re.search(r"\bsafe\b", spoken, re.I):
        return None, "never say that something is safe"
    return {"script": script, "highlights": highlights[:3]}, ""


def plain_script(title: str, facts: list[str]) -> dict:
    """A script written by code, for when the language model is not set up or broke a rule."""
    said = " ".join(line.rstrip(".") + "." for line in facts[:4])
    return {"script": f"{title}. {said} Ask me about anything on this page.", "highlights": [line.rstrip(".") for line in facts[:3]]}


def _parse(reply: str) -> object:
    try:
        return json.loads(reply[reply.find("{") : reply.rfind("}") + 1])
    except ValueError:
        return None


@lru_cache(maxsize=256)
def _brief(kind: str, params_json: str) -> dict:
    title, facts = KINDS[kind](json.loads(params_json))
    while len("\n".join(facts)) > MAX_FACT_CHARS and len(facts) > 4:
        facts = facts[:-1]
    messages = [{"role": "system", "content": SCRIPT_SYSTEM},
                {"role": "user", "content": f"THE PAGE: {title}\n\nFACTS\n" + "\n".join(f"- {line}" for line in facts)}]  # fmt: skip
    written, why = None, ""
    try:
        for _ in range(2):  # one retry, telling the model which rule it broke
            reply = llm.chat(messages, max_tokens=500)
            written, why = check_script(_parse(reply), facts)
            if written:
                break
            messages += [{"role": "assistant", "content": reply},
                         {"role": "user", "content": f"That broke a rule: {why}. Answer again, JSON only."}]  # fmt: skip
    except RuntimeError:
        why = "the language model is not set up"
    except (urllib.error.URLError, TimeoutError, KeyError, ValueError):
        why = "the language model did not answer"
    return {
        "title": title,
        "facts": facts,
        **(written or plain_script(title, facts)),
        "written_by": "model" if written else "code",
        "fallback_reason": None if written else why,
    }


def answer(kind: str, params: dict, question: str, history: list[dict]) -> dict:
    """A typed question answered from the page's facts, for when the ElevenLabs conversation is not in use.

    Unlike a spoken answer, this one is checked before anyone hears it: a
    number that is in neither the facts nor the listener's own words is refused.
    """
    brief = _brief(kind, json.dumps(params, sort_keys=True))
    system = AGENT_PROMPT.replace("{{page}}", brief["title"]).replace("{{facts}}", "\n".join(brief["facts"]))
    turns = [{"role": "assistant" if turn["role"] == "agent" else "user", "content": turn["text"]} for turn in history[-6:]]
    messages = [{"role": "system", "content": system}, {"role": "assistant", "content": brief["script"]},
                *turns, {"role": "user", "content": question}]  # fmt: skip
    asked = " ".join([question, *(turn["text"] for turn in history if turn["role"] == "user")])
    allowed = set(_NUMBER.findall(" ".join(brief["facts"]) + " " + brief["script"] + " " + asked))
    for _ in range(2):  # one retry, telling the model which rule it broke
        reply = " ".join(llm.chat(messages, max_tokens=220).split())
        invented = sorted(set(_NUMBER.findall(reply)) - allowed)
        if reply and not invented and not re.search(r"\bsafe\b", reply, re.I):
            return {"text": reply, "checked": True}
        why = f"these numbers are not in the facts: {', '.join(invented)}" if invented else "never say that something is safe"
        messages += [{"role": "assistant", "content": reply},
                     {"role": "user", "content": f"That broke a rule: {why}. Answer the question again."}]  # fmt: skip
    return {"text": NOT_COVERED, "checked": True}


def conversation_token() -> tuple[str | None, str | None]:
    """A one-conversation token for the ElevenLabs agent, or None and why there is none. The key never leaves the server."""
    key, agent = _env("ELEVENLABS_API_KEY"), _env("ELEVENLABS_AGENT_ID")
    if not key or not agent:
        return None, "The ElevenLabs voice is not set up on this server, so the browser's own voice reads this. Type a question to ask one."
    request = urllib.request.Request(
        f"{ELEVENLABS}/conversation/token?agent_id={urllib.parse.quote(agent)}", headers={"xi-api-key": key}
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read())["token"], None
    except (urllib.error.URLError, TimeoutError, KeyError, ValueError):
        return None, "ElevenLabs did not answer, so the browser's own voice reads this. Type a question to ask one."


def explain(kind: str, params: dict) -> dict:
    brief = _brief(kind, json.dumps(params, sort_keys=True))
    token, note = conversation_token()
    return {**brief, "voice": {"token": token} if token else None, "voice_note": note}


def create_agent() -> int:
    """Create the ElevenLabs agent this module talks to, and print its id for .env."""
    key = _env("ELEVENLABS_API_KEY")
    if not key:
        print("Set ELEVENLABS_API_KEY in .env first (see .env.example).")
        return 1
    body = {
        "name": "Flame in Freefall guide",
        "conversation_config": {
            "agent": {
                # The page's checked script is spoken first. The listener can cut in at any point.
                "first_message": "{{narration}}",
                "language": "en",
                "prompt": {"prompt": AGENT_PROMPT},
                "dynamic_variables": {
                    "dynamic_variable_placeholders": {
                        "narration": "This is the voice guide for Flame in Freefall. Ask me about the page you are on.",
                        "page": "A page of the dashboard",
                        "facts": "No facts were given.",
                    }
                },
            }
        },
        # Conversations need a token from this server, so nobody can use the agent with the id alone.
        "platform_settings": {"auth": {"enable_auth": True}},
    }
    request = urllib.request.Request(
        f"{ELEVENLABS}/agents/create", data=json.dumps(body).encode(),
        headers={"xi-api-key": key, "Content-Type": "application/json"},
    )  # fmt: skip
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            agent_id = json.loads(response.read())["agent_id"]
    except urllib.error.HTTPError as error:
        print(f"ElevenLabs refused ({error.code}): {error.read().decode(errors='replace')[:600]}")
        return 1
    print(f"Created the agent. Add this line to .env and restart the backend:\n\nELEVENLABS_AGENT_ID={agent_id}")
    return 0


def update_agent() -> int:
    """Send the prompt in this file to the agent that already exists, after the prompt was edited."""
    key, agent = _env("ELEVENLABS_API_KEY"), _env("ELEVENLABS_AGENT_ID")
    body = {"conversation_config": {"agent": {"prompt": {"prompt": AGENT_PROMPT}}}}
    request = urllib.request.Request(
        f"{ELEVENLABS}/agents/{urllib.parse.quote(agent)}", data=json.dumps(body).encode(), method="PATCH",
        headers={"xi-api-key": key, "Content-Type": "application/json"},
    )  # fmt: skip
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            saved = json.loads(response.read())
    except urllib.error.HTTPError as error:
        print(f"ElevenLabs refused ({error.code}): {error.read().decode(errors='replace')[:600]}")
        return 1
    stored = saved.get("conversation_config", {}).get("agent", {}).get("prompt", {}).get("prompt")
    print("Updated the agent's prompt." if stored == AGENT_PROMPT else "ElevenLabs answered, but the stored prompt differs from this file.")
    return 0 if stored == AGENT_PROMPT else 1


if __name__ == "__main__":
    # With an agent id in .env the agent exists, so its prompt is updated. Without one, the agent is created.
    sys.exit(update_agent() if _env("ELEVENLABS_AGENT_ID") else create_agent())
