# ADR 0003: Pydantic JSON instead of Polars ingestion

Accepted. The demo exchanges whole typed network documents under a 10 MiB upload bound and uses NumPy for numerical arrays. Pydantic supplies schema errors with record paths and avoids a second conversion layer. Polars is not required for this workload. Columnar CSV/Parquet ingestion should be added when a measured workload requires it, preserving the same validation/provenance contract.
