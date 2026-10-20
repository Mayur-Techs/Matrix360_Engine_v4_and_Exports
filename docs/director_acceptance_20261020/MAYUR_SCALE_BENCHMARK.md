# Local scale benchmark — measured values only

| Input rows | Completed rows | Engine seconds | Rows/sec | Reconciled | Output SHA-256 | Notes |
| ---: | ---: | ---: | ---: | --- | --- | --- |
| 100 | 100 | 0.407 | 245.7 | yes | `8212348CF2B01FFFAE948301D46A55E260179A1380F0A3A8BA166BA69816B811` | synthetic CSV, V4.1.2 |
| 100,000 | 100,000 | 73.484 | 1,360.8 | yes | `F776F40DD4B5D034EA0950221FEBA421D403176E36F50F86D8F2B499752B5ECE` | synthetic CSV, V4.1.2 |

Peak memory and CPU telemetry: **NOT MEASURED** on Windows by the existing benchmark helper. Export timing was not measured separately. The engine reported zero rejected rows, zero failed files, zero duplicate-review groups, and zero automatic merges for both synthetic workloads.

500,000 and 2,500,000 rows: **NOT TESTED**. They were not extrapolated to a three-crore capability. The current core restarts an interrupted file from the beginning; that limitation remains documented.
