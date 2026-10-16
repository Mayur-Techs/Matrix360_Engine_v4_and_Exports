# Large file design

## Current local behavior

The API streams each multipart upload to tenant-scoped disk in 1 MiB chunks and stops at the configured per-file byte limit. The preserved processor reads input rows incrementally, writes Parquet in 10,000-row batches, and builds the DuckDB warehouse outside the HTTP request. The worker generates CSVs row by row and creates the combined workbook in `openpyxl` write-only mode; sheets partition after Excel's 1,048,576-row limit.

The browser never receives the entire dataset: results are queried from the worker CSV with DuckDB and capped at 200 rows per API response.

## Explicit limitations

- **UNVERIFIED:** 100,000 and 500,000 row measurements on this machine.
- **PLANNED:** cloud multipart/resume, file scanning, object storage and durable row-offset checkpoints.
- **REPORTED only:** previous standalone evidence refers to a 500,000-row run; it is not reused as a benchmark for this build.

