"""
BigQuery client for Ask the Data (safe stub if google-cloud-bigquery not installed).
"""
from typing import Optional, Dict, Any

try:
    from google.cloud import bigquery  # type: ignore
    HAS_BQ = True
except Exception:
    bigquery = None
    HAS_BQ = False

from .constants import DRY_RUN_MAX_BYTES, ROW_CAP

class BigQueryClient:
    def __init__(self, project_id: Optional[str] = None):
        self.max_bytes = DRY_RUN_MAX_BYTES
        self.row_cap = ROW_CAP
        if not HAS_BQ:
            self.client = None
        else:
            self.client = bigquery.Client(project=project_id)

    def dry_run(self, sql: str) -> Dict[str, Any]:
        if not HAS_BQ or self.client is None:
            return {"success": False, "error": "google-cloud-bigquery not available", "bytes_processed": 0, "within_limits": False}
        job = self.client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False))
        return {
            "success": True,
            "bytes_processed": job.total_bytes_processed,
            "within_limits": job.total_bytes_processed <= self.max_bytes,
        }

    def execute(self, sql: str, dry_run_first: bool = True) -> Dict[str, Any]:
        if not HAS_BQ or self.client is None:
            return {"success": False, "error": "google-cloud-bigquery not available", "rows_returned": 0}
        if dry_run_first:
            dr = self.dry_run(sql)
            if not dr.get("success") or not dr.get("within_limits"):
                return {"success": False, "error": f"Dry-run failed or over cap: {dr}", "rows_returned": 0}
        job = self.client.query(sql)
        df = job.result().to_dataframe()
        if len(df) > self.row_cap:
            df = df.head(self.row_cap)
        return {"success": True, "dataframe": df, "rows_returned": len(df)}

    def test_connection(self) -> bool:
        """Return True if BigQuery client can run a trivial query (or False if library/creds missing)."""
        if not HAS_BQ or self.client is None:
            return False
        try:
            self.client.query("SELECT 1").result()
            return True
        except Exception:
            return False
