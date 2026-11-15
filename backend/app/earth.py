"""Earth uses of the research, in NASA's words.

Two sources, kept apart. THEMES quotes the research-impacts text of the PSI
records, and the grouping is this project's. SPINOFFS quotes NASA pages on the
four products the brief names. Nothing is paraphrased, and panel() fails if a
PSI quote is no longer in its record.
"""

from . import store

FIELD = "Research impacts and Earth benefits"

# Each quote: the investigations whose record says it, then the text.
THEMES = [
    {
        "id": "confined",
        "label": "Fire safety in sealed and confined places",
        "quotes": [
            (
                ("PSI-98", "PSI-99", "PSI-100"),
                "Studying fire in small, sealed environments such as the Cygnus cargo supply vehicle benefits fire "
                "safety and prevention efforts on Earth, including inside mines, airplanes, or submarines.",
            ),
            (
                ("PSI-69",),
                "On Earth, the insights gained from these experiments have the potential to advance fire safety in "
                "confined and reduced-gravity environments, such as submarines or high-altitude aircraft.",
            ),
            (
                ("PSI-25",),
                "These models can then be used to more accurately study flames on Earth, such as in wildfires, "
                "building fires, energy recapture from waste recycling, and other combustion problems.",
            ),
            (
                ("PSI-62",),
                "On Earth, these advancements could improve combustion modeling by deepening our understanding of "
                "coupled thermal, chemical, and flow processes, which betters fire safety standards.",
            ),
        ],
    },
    {
        "id": "detection",
        "label": "Smoke detection",
        "quotes": [
            (
                ("PSI-102", "PSI-101"),
                "The smoke detectors developed from the results of SAME can also be useful in other extreme "
                "environments on Earth, such as submarines or underwater laboratories.",
            ),
            (
                ("PSI-47",),
                "Additionally, the successful adaptation of the TSI P-Trak for microgravity can inform the design of "
                "instruments for use in other challenging Earth environments, such as submarines or underwater "
                "laboratories where accurate detection of smoke can save lives.",
            ),
        ],
    },
    {
        "id": "suppression",
        "label": "Putting fires out",
        "quotes": [
            (
                ("PSI-69",),
                "The mission's findings on the effectiveness of various fire suppressants, including CO2, He, and "
                "SF6, in microgravity can lead to the development of more efficient and less harmful fire "
                "suppression systems, reducing the risk of toxic byproducts during fire events.",
            ),
            (
                ("PSI-21",),
                "In addition, an understanding of those factors that affect flame extinction in diffusion flames is "
                "critical in the suppression of fires and in improving engine efficiency.",
            ),
        ],
    },
    {
        "id": "engines",
        "label": "Engines and fuel efficiency",
        "quotes": [
            (
                ("PSI-159",),
                "The internal combustion engines used for transportation generally have thermal efficiencies of 38% "
                "or lower because of thermal losses. These efficiencies may increase to 60% if future engines can "
                "take advantage of ultra-lean combustion.",
            ),
            (
                ("PSI-39",),
                "Cool flames play a key role in the development and selection of new fuels and the design of "
                "advanced engines such as clean, high-efficiency Homogeneous Charge Compression Ignition (HCCI) "
                "engines.",
            ),
            (
                ("PSI-69",),
                "Additionally, the study of ''cool flames'' and low-temperature combustion processes observed in "
                "microgravity can inform the design of advanced combustion engines, leading to improved fuel "
                "efficiency and reduced emissions in automotive and industrial applications.",
            ),
            (
                ("PSI-117",),
                "Earth Benefits: Advances low-temperature combustion understanding relevant to engine knock, "
                "efficiency, and emissions; delivers validated CFD tools transferrable to practical combustors.",
            ),
            (
                ("PSI-142",),
                "Since many real engines operate in the 20-40 atm pressure range, therefore, cool flames and warm "
                "flames are relevant and important flame regimes for high-pressure near-limit combustion "
                "applications.",
            ),
            (
                ("PSI-23",),
                "Practically, with diffusion flame burning as the basis in many combustion engines and devices, "
                "understanding the underlying dynamics and chemistry of diffusion flames is important in improving "
                "performance in terms of power, efficiency, pollutant emissions, and reliability.",
            ),
            (
                ("PSI-106",),
                "Findings will inform the development of cleaner, more efficient engines and industrial burners.",
            ),
        ],
    },
    {
        "id": "pollution",
        "label": "Cleaner burning and less pollution",
        "quotes": [
            (
                ("PSI-22",),
                "The use of electric fields to control flames can reduce the production of harmful pollutants in "
                "practical terrestrial combustion.",
            ),
            (
                ("PSI-10",),
                "This project has the potential for improving efficiency and reducing pollutant emissions in "
                "terrestrial combustors. For example, it is contributing to novel designs of future coal power "
                "plants.",
            ),
            (
                ("PSI-68",),
                "Insights gained from these studies can lead to more efficient and cleaner combustion technologies "
                "which are crucial for reducing pollution and greenhouse gas emissions.",
            ),
            (
                ("PSI-60",),
                "On Earth, the insights help reduce pollutant emissions, optimize combustion efficiency, and inform "
                "the design of cleaner energy and industrial systems.",
            ),
        ],
    },
]

# Read on this date. A quote is the page's own text.
CHECKED = "2026-11-15"

SPINOFFS = [
    {
        "product": "Fine-water-mist extinguishers",
        "sources": [
            {
                "title": "Zero-Leak Valve Holds Tight in Demanding Environments",
                "publication": "NASA Spinoff 2020",
                "url": "https://spinoff.nasa.gov/Spinoff2020/ip_5.html",
                "quotes": [
                    "The Colorado School of Mines performed early NASA-funded research on the rudiments of water "
                    "mist technology, culminating in a spaceflight experiment flown aboard space shuttle Columbia.",
                    "The project team established fire test standards for microgravity environments and built a "
                    "technology suitable for use in space and on Earth.",
                ],
            },
        ],
    },
    {
        "product": "Smoke detectors",
        "sources": [
            {
                "title": "FAQ: Smoke detectors?",
                "publication": "NASA Spinoff",
                "url": "https://spinoff.nasa.gov/faq",
                "quotes": [
                    "NASA’s connection with modern smoke detectors is that it made one with adjustable sensitivity "
                    "as a part of a Skylab project. There was a spinoff smoke detector sold by Honeywell for some "
                    "years, but it is no longer available.",
                ],
            },
            {
                "title": "Fire Detector",
                "publication": "NASA Spinoff 1978",
                "url": "https://ntrs.nasa.gov/citations/20070018916",
                "quotes": [
                    "An early warning fire detection sensor developed for NASA's Space Shuttle Orbiter is being "
                    "evaluated as a possible hazard prevention system for mining operations.",
                ],
            },
        ],
    },
    {
        "product": "Firefighter clothing",
        "sources": [
            {
                "title": "Polymer Fabric Protects Firefighters, Military, and Civilians",
                "publication": "NASA Spinoff 2008",
                "url": "https://spinoff.nasa.gov/Spinoff2008/ps_3.html",
                "quotes": [
                    "In 1967, NASA contracted with Celanese Corporation, of New York, to develop a line of PBI "
                    "textiles for use in space suits and vehicles.",
                    "PBI is now used in numerous firefighting, military, motor sports, and other applications.",
                ],
            },
        ],
    },
    {
        "product": "Firefighter air tanks",
        "sources": [
            {
                "title": "Fireman's Air Tanks",
                "publication": "NASA Spinoff 1976",
                "url": "https://spinoff.nasa.gov/node/9582",
                "quotes": [
                    "Together with NASA's Johnson Space Center, A-T-O Inc.'s Scott Aviation has developed "
                    "light-weight firefighter's air tanks. New backpack system weighs only 20 pounds for 30 minute "
                    "air supply, 13 pounds less than conventional firefighting tanks.",
                ],
            },
        ],
    },
]


def _who(entry: dict) -> dict:
    return {"psi_id": entry["psi_id"], "name": entry["name"], "doi": entry["doi"]}


def panel() -> dict:
    known = store.investigations()
    quoted: set[str] = set()
    themes = []
    for theme in THEMES:
        quotes = []
        for psi_ids, text in theme["quotes"]:
            for psi_id in psi_ids:
                if text not in " ".join((known[psi_id]["research_impacts"] or "").split()):
                    raise ValueError(f"The {psi_id} record no longer says: {text[:60]}")
            quoted.update(psi_ids)
            quotes.append({"text": text, "investigations": [_who(known[psi_id]) for psi_id in psi_ids]})
        themes.append({"id": theme["id"], "label": theme["label"], "quotes": quotes})
    return {
        "field": FIELD,
        "themes": themes,
        "not_quoted": [_who(e) for e in known.values() if e["in_scope"] and e["psi_id"] not in quoted],
        "spinoffs": SPINOFFS,
        "spinoffs_checked": CHECKED,
    }
