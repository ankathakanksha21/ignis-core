# Problem Statement: Flame in Freefall

Dual entry, NASA Space Apps 2026. Challenge: "Flame in Freefall: SI-Powered Fire Safety Insights from Microgravity Combustion Data".

This document states the problem and the feature set the prototype is built from.

## 1. The challenge in one paragraph

NASA has decades of microgravity combustion experiments, published through the Physical Sciences Informatics (PSI) repository. The results are hard to find, harder to compare, and harder to interpret. The task is an interactive, "super intelligence (SI) powered", web-based dashboard that summarizes, ranks and interprets the combustion investigations to deliver fire safety insights for human space exploration.

## 2. Why this matters

Incidents named in the brief:

- An Artemis II smoke alarm about 80,000 miles from home.
- The Apollo 13 oxygen tank explosion.
- The 1997 Mir fire, caused by an oxygen generator failure.
- The 1967 Apollo 1 pre-launch fire, in an oxygen-filled cabin, which killed the crew.

In microgravity there is no buoyancy, so hot gas does not rise. A candle flame becomes a blue sphere fed by diffusion. Airflow matters a lot.

NASA fire safety has three pillars:

- Prevention: control ignition sources and select materials, which depends on flammability limits.
- Detection.
- Suppression.

Moon base and pressurized rover atmosphere is the harder case. Spacesuits run 100% oxygen at 4.3 psi, while Earth sea level is 14.7 psi at 21% oxygen. To shorten pre-breathing, habitats are expected at 30% oxygen or more and 10.2 psi or less. That is over 40% more oxygen than Earth air, so materials are much more flammable.

## 3. What the brief asks for

Required:

- A web dashboard.
- An SI layer.
- Three verbs: summarize, rank, interpret.

Optional (the brief says "you may consider"):

- Identify investigations most relevant to habitable crew environments: spacecraft, space stations, lunar and Martian surface bases, pressurized rovers.
- Extract data that supports predictive modelling of flammability and fire scenarios. The ask is model-ready data. A trained model is a bonus.
- Highlight research that informs next-generation fire safety controls and equipment.
- Show Earth applications (fine-water-mist extinguishers, smoke detectors, firefighter clothing and air tanks).

Attributes the brief suggests showing per investigation:

- Objectives.
- Fuels (shape and size of samples or burners).
- Test conditions (oxygen concentration, airflow speed).
- Variables (how tests within one investigation differed).
- Sensors or measurement types.
- Similarities and differences between investigations.

Audience: professors, graduate and undergraduate students, aerospace researchers and engineers.

Out of scope: rocket and propellant fire.

The brief points out these relationships, and the dashboard should show them:

- Solid material flammability: BASS, BASS-II, Saffire-I, -II, -III.
- Detection: SAME, SAME-R. One SAME instrument was reused to detect dust in DAFT and DAFT-2.
- Suppression: FLEX (dilution with carbon dioxide and helium).
- ACME BRE burned gaseous fuel but is a materials flammability study in still atmospheres.
- Six ACME experiments share the ACME hardware in the Combustion Integrated Rack (CIR).
- FLEX, FLEX-2 and CFI burned liquid droplets in the Multi-user Droplet Combustion Apparatus (MDCA) in the CIR.
- BASS, BASS-II, SPICE and SLICE ran in the Microgravity Science Glovebox (MSG), using the fan-driven flow duct built for SPICE.
- Highest oxygen in microgravity: ACME CFI-G, up to 85% oxygen from the burner.
- PSI has no partial-gravity combustion data yet. LUCI and FM2 may add it. ACME E-FIELD Flames mimicked partial gravity with an electric field. Microgravity and normal-gravity results could bound intermediate gravity.

## 4. The data (checked 14 Nov 2026 through the PSI API)

> The snapshot committed in `data/raw/` supersedes the counts in this section where they differ. See `data/README.md` for what the snapshot found.

The PSI site has an open JSON API with no login. Searching "combustion" returns 26 investigations. Two are not combustion (PSI-181 solder microstructure, PSI-108 STDCE-1 surface tension convection). Of the 24 left, 19 are flight investigations and 5 are ground studies that reanalyse flight data (PSI-117, PSI-62, PSI-60, PSI-142, PSI-115).

Each investigation record carries: title, acronym, objectives, approach, hypothesis, experiment hardware, research impacts and Earth benefits, publications, related investigations, flight platform, dates, and DOI. PSI-25 is licensed CC0 (other records not yet verified).

Most flight investigations have a small "Experimental table" CSV, one row per test. This is the usable data.

| Investigation | PSI id | Rows | What the columns give |
| --- | --- | --- | --- |
| BASS-II | PSI-25 | 129 | material and sample size, flow settings, initial and final O2, CO2, CO. Initial O2 spans 13.6 to 22.2%. No burn or no-burn outcome column. |
| BASS | PSI-26 | 122 | date, test number, sample, material only. |
| FLEX | PSI-69 | 274 | fuel (methanol 157, heptane 117), pressure, O2, N2, CO2, He mole fractions, droplet diameter, extinction diameter, burning rate, burn time, test end (Extinction 186, Disruption 61, Completion 27). O2 spans 0.12 to 0.34. |
| FLEX-2 | PSI-68 | 8 | fuel, droplet size, gas mixture, O2, pressure, temperature, flow velocity (a test matrix summary). |
| CFI | PSI-39 | 87 | pressure, O2, N2, He, fiber, fuel. |
| ACME CFI-G | PSI-159 | 179 | fuel, cool flame yes or no, O2 before and after, pressure, hot ignition, burn time, self-extinguished or flow terminated. |
| ACME Flame Design | PSI-10 | 207 | fuel, flow rates, initial and final O2, pressure, adiabatic temperature. |
| ACME BRE | PSI-20 | 18 | burner size, fuel, oxygen concentration, flames ignited. |
| ACME CLD Flame | PSI-21 | 32 | fuel and nitrogen flow, flames ignited. |
| ACME E-FIELD Flames | PSI-22 | 32 | mesh polarity, fuel, flames ignited. |
| ACME s-Flame | PSI-23 | 18 | atmosphere, fuel, flames ignited. |
| SPICE | PSI-107 | 469 | fuel, nozzle size, fuel rate, air rate, ignition and flame-off times. |
| SLICE | PSI-106 | not read | a CSV exists, the request timed out. |
| Saffire-I | PSI-98 | 4 | material, dimensions, airflow, O2, ignition power, burn time. |
| Saffire-II | PSI-99 | 15 | same plus burn length in microgravity and at 1 g. |
| Saffire-III | PSI-100 | 2 | material, dimensions, airflow. |
| SAME | PSI-102 | 8 | sample material, airflow, weight loss rate, aging duration. |
| SAME-R | PSI-101 | 109 | sample type, inlet velocity, aging and mixing times. |
| DAFT / DAFT-2 | PSI-47 | 2 | session, hardware, sample material, location. |

The tables total about 1,715 rows across 18 tables. Row counts are non-empty lines minus the header, so a few may include note lines. Exact counts get confirmed at ingest.

Raw data is not usable in a day. BASS-II raw data is about 300 GB (mostly video), and ACME investigations run to 1.4 to 2.2 TB each. The prototype uses the experimental tables and the record metadata, and may add a few PDF reports later.

The same API lists PDF documents per investigation in Reports, Science Documents, Engineering Documents and Presentations folders (for example PSI-25 BASS-II lists 130 PDFs, PSI-101 SAME-R 74, PSI-26 BASS 54, PSI-107 SPICE 39). These are the source for report search with page-level citations. NASA's Technical Reports Server (NTRS) is a second possible source (its public API is not yet verified for this project).

API routes:

```
search: https://psi.nasa.gov/geode-py/ws/repo/search?term=combustion&source=psi&type=investigation
one record: https://psi.nasa.gov/geode-py/ws/repo/investigations/PSI-25
one file: https://psi.nasa.gov/geode-py/ws/studies/PSI-25/download?source=datamanager&file=<file name>
```

Other resources on the challenge Resources tab:

- NASA Glenn combustion science pages.
- "A Researcher's Guide to ISS Combustion Science" (2015, 50+ pages).
- A 2018 ScienceCasts video.
- Apollo 1, Apollo 13 and Mir fire pages.
- Three NASA Spinoff pages (firefighter air tanks, a smoke detector that tells smoke from dust, firefighter clothing).

PSI requires citing each investigation by its DOI.

## 5. What the data cannot say

These limits are the core of the "do not make things up" requirement.

- No partial-gravity (Moon 0.16 g, Mars 0.38 g) combustion data in PSI.
- BASS-II, the main solid-fuel flammability table, stops at 22.2% oxygen. Moon habitats are planned at 30% or more. Saffire oxygen values still need reading at ingest (not yet verified).
- The tests that do reach Moon-like oxygen are liquid droplets (FLEX, up to 34%) and gas flames (CFI-G, up to 85%), which are not cabin materials.
- BASS-II has no outcome column, so a solid-fuel "will it burn" label would have to come from NASA reports, not from the table.
- Data quality: the BASS-II final O2 column ranges from 0.6 to 40.4 while initial O2 is 13.6 to 22.2, so some entries look wrong. Ingest needs validation checks that flag such rows instead of silently using them.
- The FLEX pressure column has a minimum of 0 mmHg, which is not a physical test pressure, so at least one row needs flagging.

## 6. Features

Five feature groups, in the author's priority order.

### 6.1 Mission-relevance dashboard

- Collect the PSI combustion investigations: BASS, BASS-II, FLEX, FLEX-2, CFI, Saffire-I, -II, -III, SAME, SAME-R, DAFT, the ACME set (BRE, CFI-G, E-FIELD Flames, Flame Design, CLD Flame, s-Flame), SPICE, SLICE.
- Organise them by fire safety pillar: prevention, detection, suppression.
- One card per investigation: objective, fuel and sample shape, conditions range, what varied between tests, measurements, hardware, DOI link.
- The user picks a mission (spacecraft, space station, Moon base, Mars base, pressurized rover). The dashboard ranks every investigation with a score computed in code from visible, adjustable factors: atmosphere match (oxygen, pressure), fuel type, gravity, pillar. The score breakdown is shown.
- Compare view: two or three investigations side by side, plus an oxygen versus pressure chart with the chosen habitat marked.
- Each result has an AI summary, written by the language model from that investigation's record and test rows only, with the PSI id cited.
- Similar-conditions search: given a set of conditions, list the nearest real tests across investigations.
- Knowledge-gap map: a grid over oxygen, pressure, flow, fuel class and gravity, coloured by how many tests exist in each cell, with the habitat conditions overlaid so the missing regions are visible.

### 6.2 Exploration atmospheres: test conditions, validation, future experiments

- Habitat profiles defined in code. Moon base and pressurized rover: 30% oxygen or more, 10.2 psi or less, 0.16 g. Spacesuit: 100% oxygen at 4.3 psi. Earth reference: 21% oxygen, 14.7 psi, 1 g. Space station: microgravity with Earth-like air. The brief gives no atmosphere for a Mars base, so its profile (0.38 g with the Moon-base atmosphere) is an assumption, labelled as one and editable.
- For each profile the tool lists which tests come close and which conditions have never been tested.
- Suggested future experiments: the untested grid cells nearest each habitat profile, ranked in code by closeness to the profile and by fuel class relevance. The language model only words the list.
- Source checking: every test row keeps its PSI id, file name and row number. Where the same condition appears in more than one investigation or in a report, the values are compared and disagreements are flagged.
- The dashboard has a data quality view listing flagged rows per investigation, so users can examine data quality themselves.

### 6.3 Predictive modelling (part of 6.2)

- One model per fuel class. Solids, liquid droplets and gas flames follow different physics, so a single model pooled across BASS-II, Saffire, FLEX, CFI and ACME would mix targets that do not mean the same thing.

| Model | Data | Target | Status |
| --- | --- | --- | --- |
| Droplet burning rate | FLEX, 274 tests | burning rate (regression) | labels in the table. |
| Flame extinction | FLEX, 274 tests | test end: extinction, disruption or completion (classification) | labels in the table. |
| Cool flame occurrence | ACME CFI-G, 179 tests | cool flame yes or no, hot ignition | labels in the table. |
| Flame spread on solids | BASS-II 129 tests, Saffire-I, -II, -III 21 tests | burned or did not sustain, spread or burn length | Saffire-II has burn length. BASS-II has no outcome column, so labels must be extracted from NASA reports first. Starts as a nearest-test matcher and becomes a model once labels exist. |

- Algorithm: gradient-boosted trees (XGBoost or scikit-learn gradient boosting, they behave alike at this size) with logistic or ridge regression as the interpretable baseline. Deep networks would overfit a few hundred rows.
- Inputs: oxygen concentration, pressure, airflow velocity, diluent (CO2, He, N2), and material or fuel type, limited to the inputs each table actually contains.
- Outputs: a prediction with class probabilities or a range, the nearest real experiments, and clickable NASA citations (PSI id, DOI, row).
- A warning whenever an input is outside what NASA tested. Outside the tested range the prediction is withheld and the gap is shown.
- Evaluation: cross-validation grouped by test day or fuel so near-duplicate runs do not leak, compared against a majority-class or mean baseline, results reported even if weak.
- Combustion physics engine, used beside the models as a check: the d-squared law for droplets (droplet diameter squared falls linearly with time, the slope is the burning rate constant) calibrated on FLEX burning rates, and a reduced-order flammability boundary for solids with radiative quenching at low flow and blowoff at high flow. The engine is calibrated to PSI tables and labelled as a simplified model.

### 6.4 Interactive combustion lab (research simulation)

- A 2D interactive view where the user changes gravity, pressure, oxygen, nitrogen or other diluent, airflow and fuel material and watches how the flame responds (shape, size, burning rate, whether it sustains or goes out).
- It opens with preset scenarios, then lets the user change the controls freely. Presets: candle on Earth versus in microgravity, a material going from non-flammable to flammable as oxygen rises from 21% to 30%, a droplet extinguished by CO2 or helium dilution, ventilation on versus off in microgravity.
- Driven by the physics engine in 6.3. Where real tests exist near the chosen settings, they are shown beside the simulation.
- Honesty rule: the lab is a teaching model. Its output is labelled "simulated" everywhere and is kept visually separate from NASA measurements. For Moon and Mars gravity it shows the range bounded by microgravity and normal-gravity behaviour and states that PSI holds no partial-gravity data.
- Pattern explorer: plots across the real test table (for example burning rate against oxygen, extinction against diluent fraction) so users can find patterns in measured behaviour, with flagged rows marked.
- A "what would make it safer" control: vary one factor at a time (lower oxygen, lower flow, add diluent) and see which change moves the scenario out of the flammable region, again labelled as simulated.

### 6.5 Question answering

- Retrieval over NASA sources, no fine-tuning (reasons in the approach section).
- The language model reads the question, the system retrieves and ranks the relevant findings, test rows and report passages, and the model writes a short answer using only the top-ranked items.
- Every sentence carries a citation. If the retrieved evidence does not cover the question, the answer says so.
- Numbers in an answer are copied from retrieved rows by code, never produced by the model.

## 7. Rules the tool follows

- Every number comes from code reading NASA tables. The language model never produces a number.
- Every displayed attribute links to its source: PSI id, file name, row.
- The assistant sees only retrieved records. No answer without a citation.
- Outside tested conditions the tool refuses and shows the gap. Partial gravity is always marked untested.
- Missing values show as "not stated". Unknown is never shown as safe.
- Relevance scores are this project's heuristic, labelled as such, and are not NASA ratings.
- Simulated output is always labelled and never mixed into measured data or rankings.
- Model predictions are withheld outside the tested range.
- It is a research and teaching aid, and is not a certified safety tool.

## 8. Approach decisions

### Fine-tuning, RAG or agents

Recommendation: no fine-tuning. Reasons:

- The corpus is tiny (24 investigations, about 1,700 test rows), far too small to fine-tune without the model memorising or drifting.
- Fine-tuning stores knowledge in weights, where it cannot be cited or checked, which works against safety.
- A fine-tuned model still invents numbers and cannot tell you it is outside the data.
- It costs time and money that a one-day build does not have.

Safety here comes from structure. Code computes, the model explains, sources are attached, and refusal is enforced by a range check in code.

Retrieval: structured records and tool calls (look up tests, rank, predict) come first because the whole catalog of 24 investigations fits in a prompt. Passage retrieval with reranking over the PDF reports is added after that, to give page-level citations (features 6.1 and 6.5).

Agents: one agent per investigation family is useful at build time, as an extraction pipeline that fills the structured records and attaches a source to each field, with code checking the result. At run time a single grounded assistant with a few tools is simpler and easier to trust.

### Predictive model

The model plan, targets and evaluation are in 6.3. Gradient-boosted trees are the main algorithm because a few hundred tabular rows with mixed numeric and categorical features is where tree ensembles do well, and they capture interactions such as oxygen with pressure and diluent. Logistic or ridge regression stays as the interpretable baseline. Deep networks would overfit at this size.

## 9. Feature priority

Tiers: core (must exist to submit), second, third.

| Feature | Tier | Note |
| --- | --- | --- |
| Data ingest with validation and source links | core | everything depends on it. |
| Investigation cards by pillar | core | |
| Mission ranking with visible weights | core | |
| Compare view and conditions chart | core | |
| AI summary per investigation | core | this is the minimum SI layer. |
| Knowledge-gap map and suggested experiments | second | computed in code. |
| Similar-conditions search | second | |
| Data quality view | second | reuses the ingest checks. |
| FLEX models (burning rate, extinction) with out-of-range warning | second | |
| Question answering over records | second | |
| CFI-G cool flame model | third | |
| Combustion lab with preset scenarios | third | largest single build. |
| Physics engine calibration | third | needed by the lab. |
| Report search with page-level citations | third | needs PDF download and indexing. |
| Solid flame-spread model | third | blocked on report-mined labels, matcher first. |
| Earth applications panel | third | from the three Spinoff pages. |
| One agent per investigation family | third | build-time extraction only. |

## 11. Stack and Stuff

- App stack: python, FastAPI, React
- Language model provider: mantle endpoint, model `qwen.qwen3-vl-235b-a22b-instruct`, region `us-east-1`. The API key is not in this repository: it goes in a local `.env` file (see `.env.example`).
- Mars base atmosphere: keep the assumed profile from 6.2 or leave Mars base as gravity-only.
