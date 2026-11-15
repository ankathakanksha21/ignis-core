"""This project's grouping of the investigations. Not NASA's.

Each pillar assignment gives its reason. "The brief" is the Space Apps
challenge text, summarised in docs/PROBLEM_STATEMENT.md section 3.
"""

PILLARS = {
    "prevention": "Which materials burn, and under what conditions.",
    "detection": "Sensing smoke and particles early.",
    "suppression": "Putting a flame out.",
    "science": "Flame behaviour studies the brief ties to no single pillar.",
}

_SOLIDS = "The brief lists it under solid material flammability."
_REUSES = "A ground study. It takes the pillar of the flight data it reanalyses: "

PILLAR_OF = {
    "PSI-25": ("prevention", _SOLIDS),
    "PSI-26": ("prevention", _SOLIDS),
    "PSI-98": ("prevention", _SOLIDS),
    "PSI-99": ("prevention", _SOLIDS),
    "PSI-100": ("prevention", _SOLIDS),
    "PSI-20": ("prevention", "The brief calls it a materials flammability study in still atmospheres."),
    "PSI-62": ("prevention", "A ground study that models flame spread over solids."),
    "PSI-101": ("detection", "The brief lists it under detection."),
    "PSI-102": ("detection", "The brief lists it under detection."),
    "PSI-47": ("detection", "The brief notes it reused a SAME instrument to detect dust."),
    "PSI-115": ("detection", _REUSES + "SAME."),
    "PSI-69": ("suppression", "The brief lists it under suppression: dilution with carbon dioxide and helium."),
    "PSI-117": ("suppression", _REUSES + "FLEX."),
    "PSI-142": ("suppression", _REUSES + "FLEX."),
    "PSI-10": ("science", "Soot limits of spherical gas flames."),
    "PSI-21": ("science", "Structure of weak coflow gas flames."),
    "PSI-22": ("science", "Response of gas flames to an electric field."),
    "PSI-23": ("science", "Structure of spherical gas flames."),
    "PSI-159": ("science", "Conditions under which cool gas flames occur."),
    "PSI-39": ("science", "Cool flames of burning droplets."),
    "PSI-68": ("science", "Droplet burning across fuels, extending FLEX."),
    "PSI-106": ("science", "Structure and lift-off of gas-jet flames."),
    "PSI-107": ("science", "Smoke points of gas-jet flames."),
    "PSI-60": ("science", _REUSES + "SPICE."),
}

# Shared hardware, as the brief states it.
HARDWARE_GROUPS = {
    "ACME hardware in the Combustion Integrated Rack": ["PSI-10", "PSI-20", "PSI-21", "PSI-22", "PSI-23", "PSI-159"],
    "Multi-user Droplet Combustion Apparatus in the Combustion Integrated Rack": ["PSI-39", "PSI-68", "PSI-69"],
    "Microgravity Science Glovebox, with the flow duct built for SPICE": ["PSI-25", "PSI-26", "PSI-106", "PSI-107"],
}

# Things the brief says about one investigation.
BRIEF_NOTES = {
    "PSI-159": "Highest oxygen in microgravity: up to 85% oxygen, fed from the burner.",
    "PSI-22": "Mimicked partial gravity with an electric field.",
    "PSI-20": "Burned gaseous fuel, but is a materials flammability study.",
    "PSI-47": "Used one of the SAME instruments to detect dust.",
}
