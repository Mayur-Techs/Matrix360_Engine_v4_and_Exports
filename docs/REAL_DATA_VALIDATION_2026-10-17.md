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
