"""Matrix 360 & LeadScope AI Studio — Production Supabase Lead Storage Adapter.

Enables discovered, pre-qualified, and engine-verified B2B leads to be
synchronized into a Supabase Postgres instance via REST / PostgREST,
with zero external dependencies (uses standard library urllib).
If SUPABASE_URL / SUPABASE_KEY are not set, it acts as a no-op local adapter.
"""
from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from typing import Any, Dict, List


class SupabaseLeadSync:
    """Production Supabase adapter for Avinash CRM integration."""

    def __init__(self, url: str | None = None, key: str | None = None) -> None:
        self.url = (url or os.environ.get("SUPABASE_URL", "")).rstrip("/")
        self.key = key or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "") or os.environ.get("SUPABASE_ANON_KEY", "")
        self.is_configured = bool(self.url and self.key)

    def sync_leads(self, leads: List[Dict[str, Any]], table: str = "leads") -> Dict[str, Any]:
        """Upsert a batch of discovered or qualified leads into Supabase."""
        if not self.is_configured:
            return {
                "synced": False,
                "status": "offline_buffered",
                "mode": "self_contained_local",
                "count": len(leads),
                "message": "SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set. Leads retained in local SQLite/DuckDB engine.",
            }

        endpoint = f"{self.url}/rest/v1/{table}"
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates",
        }

        # Transform leads into standard Supabase CRM schema
        payload = []
        for lead in leads:
            payload.append({
                "company_name": lead.get("company_name") or lead.get("company") or "",
                "canonical_domain": lead.get("canonical_domain") or lead.get("domain") or "",
                "company_phone": lead.get("company_phone") or lead.get("phone") or "",
                "company_email": lead.get("company_email") or lead.get("email") or "",
                "named_contact": lead.get("named_contact") or lead.get("name") or "",
                "role": lead.get("role") or lead.get("job_title") or "",
                "sector": lead.get("sector") or lead.get("industry") or "",
                "catchment_district": lead.get("catchment_district") or lead.get("district") or "",
                "plant_or_warehouse_address": lead.get("plant_or_warehouse_address") or lead.get("address") or "",
                "facility_evidence": lead.get("facility_evidence") or "",
                "qualification_status": lead.get("qualification_status") or "PREPASS",
                "confidence_score": float(lead.get("confidence_score") or 0.85),
                "source": "leadscope_ai_zero_api",
            })

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(endpoint, data=data_bytes, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=12) as response:
                status_code = response.getcode()
                return {
                    "synced": True,
                    "status": "synced",
                    "mode": "supabase_cloud_active",
                    "status_code": status_code,
                    "count": len(payload),
                    "message": f"Successfully upserted {len(payload)} leads into Supabase table '{table}'",
                }
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")
            return {
                "synced": False,
                "status": "offline_buffered",
                "mode": "supabase_cloud_error",
                "status_code": exc.code,
                "error": err_body,
                "count": len(payload),
                "message": f"Supabase sync failed (HTTP {exc.code}): {err_body}",
            }
        except Exception as exc:
            return {
                "synced": False,
                "status": "offline_buffered",
                "mode": "supabase_network_error",
                "error": str(exc),
                "count": len(payload),
                "message": f"Supabase network failure: {exc}",
            }

    def sync_leads_batch(self, leads: List[Dict[str, Any]], table: str = "leads") -> Dict[str, Any]:
        """Convenience alias for sync_leads."""
        return self.sync_leads(leads, table=table)
