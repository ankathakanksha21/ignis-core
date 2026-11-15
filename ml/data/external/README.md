# Outside data

Tests from NASA sources other than the PSI repository. They are not used to train any model. They are used to check a model against an experiment it has never seen.

## NASA-TM-2003-212553_heptane_droplets.csv

| | |
| --- | --- |
| Source | Ackerman and others, "A Treatment of Measurements of Heptane Droplet Combustion Aboard MSL-1", NASA/TM-2003-212553, October 2003 |
| Record | https://ntrs.nasa.gov/citations/20040000941 (NTRS document 20040000941, "Public Use Permitted") |
| What it is | Heptane droplets burned in microgravity on Spacelab in 1997 (flights STS-83 and STS-94): the Droplet Combustion Experiment (DCE) and the Fiber Supported Droplet Combustion experiment (FSDC) |
| Tables copied | Table 1 (report pages 17 and 18, DCE tests 1 to 38) and Table 2 (report page 19, FSDC tests 39 to 53) |
| Rows | 53, one per test |

How it was made: the cells were typed from the report's tables on 15 Nov 2026, then every row was checked by a script against the text extracted from the PDF. All 53 rows matched. Cells are kept as printed, including the report's footnote letters:

- `a` in `footnotes`: an STS-83 test. `h`: a tethered droplet. `b`: the diameter is approximate, from the camcorder view.
- `c` in a burning-rate cell: not reported because it varied little, so the overall value stands for the whole burn.
- `e`: not measurable because the droplet drifted out of view. `f`: no droplet view. `g`: estimated from a very dim view.
- `a` in a Table 2 cell: dimness at the end of the test prevented the measurement.

Columns left out: extinction diameters and drift velocities.

What the report does and does not state:

- Gas bottles held helium-oxygen mixtures, so for a numbered oxygen percentage the rest is helium.
- "Air" is Spacelab cabin air. The report gives no oxygen percentage for it. The loader takes it as 21%.
- Table 1 gives 1.00 bar for the DCE tests in air. Table 2 gives no pressure for the FSDC tests, which ran in the same cabin air. The loader takes it as 1.00 bar.
- The burning-rate constant used is the "Overall" column.

Why it is not training data: pooled with FLEX it made predictions on held-out FLEX tests worse (mean absolute error 0.048 to 0.056 mm²/s). The two experiments used different hardware and report the burning rate in different ways, and a model cannot tell that apart from the inputs it is given.
