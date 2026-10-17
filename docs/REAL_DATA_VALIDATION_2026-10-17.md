# Real-data validation baseline — 17 October 2026

## Scope and safeguards

The three files in the ignored `Input/` directory were used only in the local
workspace. They were not uploaded, committed, or sent to an AI provider. This
document contains aggregate counts only and no personal data.

## Preserved full-run baseline

The prior local V4 validation workspace processed all three sources with a
reconciled total of **1,016,186** records.

| Source | Retained rows |
| --- | ---: |
| Car Owners workbook | 795,081 |
| Corporate contacts workbook | 58,712 |
| Manufacturing workbook | 162,393 |
| Total | 1,016,186 |

The input and active-record totals matched exactly. The run did not perform
automatic identity merges. It produced 4,189 contact-collision review groups.

| Geography outcome | Records |
| --- | ---: |
| WB confirmed | 27,136 |
| WB possible | 4,660 |
| Outside WB | 582,952 |
| Geography unknown | 401,354 |
| Review required | 84 |

## Client-output investigation

For that preserved baseline, export eligibility means `WB_CONFIRMED` plus a
Q1, Q2, P1, or P2 evidence-bound classification.

| Client | Eligible records | Finding |
| --- | ---: | --- |
| Lakhotia Industrial | 0 | No supported rule signal in the retained WB-confirmed source fields. |
| Shree Heights | 456 | The preserved full run does not support a claim that Shree Heights exported zero records. A reported zero must be tied to a different job, export, or version. |
| Vrindavan Greens | 387 | The preserved full run does not support a claim that only one record was available. One came from the corporate contacts source and 386 from the car-owners source. |
| Unique records across client exports | 842 | Client outputs can overlap; this is not the sum of the three client counts. |

These counts are evidence for the previous run only. They are not a reason to
relax geography or classification rules to increase lead volume.

## Schema correction

Commit `af023a3` adds tested recognition for `Name of the Company`, address
columns 3 through 5, and industry and sub-industry columns. The regression
suite passed after the merge. This correction must be included in the next
full local run before that run's export counts are treated as release evidence.

## Post-correction Lakhotia validation

Rule version 4.1.1 expanded the Lakhotia P2 research-fit vocabulary to the
industrial sectors published by the project's official site: manufacturing,
warehousing and logistics, packaging and plastics, light engineering,
pharmaceuticals, agro-processing, electrical and electronics, and textiles
and garments. The rule still requires a `WB_CONFIRMED` record plus a matching
source company or sector field. It does not infer purchase intent or consent.

A fresh local run of the corporate contacts workbook completed in 58.844
seconds. It reconciled all 58,712 source rows with zero automatic merges.
The corrected mapping populated company for 58,712 rows, address for 58,654,
and sector for 54,110.

| Outcome | Records |
| --- | ---: |
| WB confirmed | 2,095 |
| Lakhotia P2 research candidates | 751 |
| Lakhotia no-fit | 1,344 |
| Lakhotia geography-review queue | 801 |

The local export step produced `Lakhotia.csv` with 751 rows, a combined
workbook, and a JSON manifest. Their SHA-256 checksums are retained in the
ignored local validation workspace, not in Git.

Sector scope source: [Lakhotia Industrial Complex](https://www.lakhotiaindustrialcomplex.com/).

## Fresh-run status

A new isolated run was started after the schema merge. The interactive desktop
environment did not reliably expose its background process state, and two
engine invocations were mistakenly allowed to target the same workspace. Both
were terminated. No report or exports from that workspace are accepted as
evidence. This is not a successful full rerun.

Run the documented Docker or two-terminal local workflow outside the
interactive sandbox to generate the fresh report and exports. Confirm that the
report reconciles, then record the new client counts and artifact checksums
before calling the 19 October candidate ready.
